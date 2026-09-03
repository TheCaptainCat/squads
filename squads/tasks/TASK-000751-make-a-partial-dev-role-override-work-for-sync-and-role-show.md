---
id: TASK-751
sequence_id: 751
type: task
title: Make a partial dev-role override work for sync and role show
status: Done
author: tech-lead
assignee: python-dev
priority: medium
refs:
- BUG-744:fixes
- ADR-754:implements
description: Fix the dev-role resolution seam without renaming live dev roles
created_at: '2026-08-21T12:42:59Z'
updated_at: '2026-08-21T18:36:59Z'
---
<!-- sq:body -->
A partial dev-role override is a documented, supported shape: `.overrides/roles/<tech>-dev.toml` merges
field-wise over a base, `sq dev add` honours exactly that shape, and `docs/overrides.md` promises the
merge for any `roles/<slug>.toml`. Two other consumers do not honour it, because they resolve through
`resolve_role`, which treats a `<tech>-dev` slug as an unknown slug with no base.

Reproduction, driven on a fresh squad:

```
sq init --default-names
sq dev add --tech python
# write .overrides/roles/python-dev.toml containing only:
#   title = "Senior Python developer"
sq role python-dev show   # exit 1
sq sync                   # exit 1
sq check                  # exit 3
```

All three report `role override for new slug 'python-dev' is missing required fields: full_name,
description, mission`.

ADR-754 settles the design. Read it in full before starting; the rules below are its decisions restated
as acceptance, not a summary to re-derive. Link: `ref add ADR-754 --kind implements`. The full
diagnostic analysis is on REV-736 finding F49.

## Why this is not a widening of `resolve_role`

Two facts, both driven, that the implementation has to respect:

- **The generated base is not a function of the slug.** `dev_role(tech, name=None, seq=0)` synthesises
  a name from `DEV_NAME_POOL` indexed by `seq`, and `seq` is the count of existing dev roles *at
  creation time* — derived, consumed, never stored. A squad whose second developer is `Ada Typescript`
  (pool index 1) gets `Elias Typescript` back from `dev_role("typescript")` at the default `seq=0`.
  `dev_role` is a name **generator**, correct exactly once, at creation.
- **That regenerated name would be persisted.** `_refresh_catalog_extra` merges
  `resolve_role(...).to_extra()` onto the live item and mirrors it into the index in the same
  transaction, and `to_extra()` includes `full_name`. A naive widening does not merely display a wrong
  name — it writes one to frontmatter and index.

The same function carries a second defect: its docstring says dev roles are skipped, and implements
that by catching `RoleNotFoundError`, which fires only when **no** override file exists. A partial file
makes `resolve_role` raise a plain `SquadsError` that nothing catches, so the documented skip is a path
that stays unreachable until an adopter writes the file the docs invite.

## Design constraints — required, not optional

- **`resolve_role(slug, squad_dir)` is untouched** — same signature, same behaviour, same bundled and
  new-slug paths. A sibling entry point takes the base:
  `resolve_role_with_base(slug, squad_dir, *, base: RoleDef | None) -> RoleDef`. `base=None` is exactly
  today's `resolve_role`; a supplied base is the merge base whenever `slug` is not in `PREDEFINED`.
  Nothing infers a dev base inside the resolver — it does not hold the information a correct one needs.
- **Two base builders, because there are two different questions.**
  - `dev_base_from_item(item)` — for a role that exists. Reads the item's own stored facts:
    `dev_role(item.extra[X.TECH], name=item.extra[X.FULL_NAME], model=item.extra[X.MODEL])`. The live
    name is passed in, so it is **inherited, never regenerated**, and `seq` is never consulted.
    `X.IS_DEV`/`X.TECH` sit outside `RoleDef.to_extra()`, so no merge can erase the marker this branch
    reads.
  - `dev_base_for_slug(slug)` — for a `<tech>-dev` file with no roster entry. Falls back to the
    generated pool name, safe here for the reason it is unsafe above: there is no live identity to
    overwrite, and the caller only asks whether the document loads.
  - Precedence: a stored fact first (`extra.is_dev` when an item is in hand), the naming convention
    (`_interactions.is_dev_slug`) only when there is no item.
- **`sq sync` branches on `X.IS_DEV`, not on catching an exception.** `_refresh_catalog_extra` tests
  `item.extra.get(X.IS_DEV)` and passes `dev_base_from_item(item)`. The `RoleNotFoundError` catch
  narrows to the case it is honest about — a slug with neither a catalog entry nor an override, i.e. an
  orphaned custom role item. With no override file the merged definition equals the base equals the
  item's own values, so the diff loop finds nothing and returns `None`: the skip becomes a **no-op
  rather than an exception catch**, and "no file" and "a file that changes nothing" reach the same
  answer by the same path.
- **`sq role <slug> show`** passes `dev_base_from_item(it)` when the item exists (it already resolves
  it) and `dev_base_for_slug(slug)` when it does not.
- **`sq check`** (`check_override_issues` in `_overrides/_service.py`) passes `dev_base_for_slug(slug)`
  for a dev-shaped slug with no roster entry and `dev_base_from_item` when there is one. Its report for
  the partial-dev shape is retired in the same change that makes the shape load — leaving it would flag
  a file that now works.
- **`_itemfile._exempt_extra_keys` does not widen.** A dev role keeps exactly `{X.SKILLS}`. The
  comment's premise ("a dev role never goes through `_refresh_catalog_extra`") becomes false and the
  **comment gets corrected**; the set does not change. The conclusion still holds —
  `_refresh_catalog_extra` writes markdown first and mirrors into the index inside one transaction, so
  no permanent index lag is introduced for dev roles and nothing needs exempting. Widening it would
  reopen the loss class that comment names: an interrupted `--set model=haiku` on a dev role, then an
  edit through another seam, silently overwritten by a stale index value.
- **`resolve_dev_role` keeps its `sq dev add` call site** and its assignment semantics for `name`. It is
  not the general seam and does not become one.

## One rule is still open, and it is not the implementation's to choose

Whether a file that **declares** `full_name` renames a live dev role is with op-pierre. Both branches
are implementable and their tests have opposite expectations, so it decides test content, not just a
line of code. Take the resolved rule from ADR-754; do not pick a side in the code. What is already
settled either way: a name the adopter never wrote is never invented, so omitting `full_name` always
preserves the live name.

## Acceptance criteria

- The reproduction above exits 0 at all three commands, with the overridden field taking the override's
  value and every unspecified field coming from the live role's stored values.
- **The rename is the risk, so it is the first test**: a squad with two developers, a partial override on
  the *second* one, then `sq sync` — that developer's `full_name` unchanged in **both** frontmatter and
  index, across two consecutive syncs. Make the base regenerate instead of inherit and this test must go
  red naming the pool name. Report that red-then-green, not just the green.
- A partial override that omits `full_name` and one that declares it are **separate tests with opposite
  expectations**, matching whatever ADR-754 settles. One test covering whichever branch got written
  covers neither rule.
- **File shapes, not just fields** — a partial dev override, a complete one, one for a tech with no
  roster entry, one whose `slug` key disagrees with its filename, and one with an invalid value (an
  off-whitelist `model`). The last must still refuse, at all three consumers.
- Remove the narrowed `RoleNotFoundError` catch and the orphaned-custom-role test must go red — i.e. the
  no-override case demonstrably takes the no-op path rather than the raising one.
- `sq check` is clean on a squad carrying a partial dev override, and still exits non-zero on one
  carrying a broken dev override.
- A live dev role's `sq role <slug> show` renders the full card — title, model, spawn, create lane,
  mission, responsibilities — instead of today's three-line item fallback.
- Every path that materialises a dev role runs its definition through the typed `RoleSpec` validation
  and the shared merge engine, so a truthy `can_spawn = "false"`, an off-whitelist `model`, a non-string
  `color` and a typo'd key are all caught for dev overrides too.
- A non-dev role's resolution, and its `missing required fields` error for a genuinely incomplete
  override, are both unchanged.
- Tests at both levels: service-level per bullet above, plus a CLI smoke test for `sq sync` and
  `sq role <slug> show` against the partial override.
- `docs/overrides.md` gains the paragraph ADR-754 names: what a `<tech>-dev.toml` merges onto, and what
  omitting versus declaring `full_name` does.
- `uv run --all-extras pyright`, `ruff check`, `ruff format --check` and the full `pytest` suite are
  green; `uv run sq check` is clean.
- `CHANGELOG.md` carries an adopter-facing entry in the unreleased section.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 751 add-subtask "<title>"`; track with `sq task 751 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-21T12:56:53Z] Olivia Lead:
  - Rewrote the body against ADR-754 (linked, implements): resolve_role untouched plus a resolve_role_with_base sibling, the two base builders, sync branching on X.IS_DEV instead of catching RoleNotFoundError, and _itemfile._exempt_extra_keys explicitly NOT widening (comment corrected, set unchanged). Its falsification list is now acceptance.
  - Dispatch note, as of today: ADR-754 is Proposed, not Accepted — whether a file that declares full_name renames a live dev role is open with op-pierre, and it decides test content rather than one line of code. Not dispatchable until that lands. Kept out of the body deliberately: a self-status banner there goes stale the moment the ADR moves.
- [2026-08-21T15:58:06Z] Elias Python:
  - Implemented per ADR-754. resolve_role untouched; added sibling resolve_role_with_base(slug, squad_dir, *, base) in _roles/_resolver.py — base=None reproduces resolve_role exactly, a bundled slug's PREDEFINED entry always wins over a supplied base. Two base builders alongside it: dev_base_from_item(item) reads item.extra[tech/full_name/model] (seq never consulted), dev_base_for_slug(slug) falls back to the generated pool name.
  - sq sync (_refresh_catalog_extra): branches on item.extra.get(X.IS_DEV) to build dev_base_from_item, calls resolve_role_with_base; RoleNotFoundError catch narrowed to its honest case (orphaned custom-role item, no catalog entry, no override) — verified red by temporarily removing the catch and watching the orphaned-role test fail, then restored.
  - sq role <slug> show (_cli/_role.py): same dev-base construction (dev_base_from_item when the item exists, dev_base_for_slug otherwise), both --json and text paths; extracted _role_json_payload to keep branch-count under the complexity gate.
  - sq check (_check_role_override_resolves): now takes role_items_by_slug (built once in Service.check from the loaded index) and resolves the same way; the partial-dev-shape report is retired by the fix itself, not by special-casing.
  - _itemfile._exempt_extra_keys / PERMITTED_EXTRA_SKEW: set left at {X.SKILLS} exactly, only the comment's premise corrected (a dev role does now go through _refresh_catalog_extra, but writes markdown+index in one transaction so nothing new needs exempting).
  - Op-pierre's rule (declare full_name -> renames; omit -> preserves) implemented as the omit/declare pair, two tests with opposite expectations.
  - Rename-risk test (two devs, partial override on the second, two syncs) verified red-then-green: reverted dev_base_from_item to drop name= and reran — failed 'Elias Typescript' != 'Ada Typescript'; restored, green.
  - Driven before/after in a throwaway squad (sq dev add --tech python, then squads/.overrides/roles/python-dev.toml with only title=): before this branch, role show/sync exit 1 and check exit 3 with 'missing required fields: full_name, description, mission'. After: role show exit 0 (full card, overridden title, live full_name Elias Python unchanged), sync exit 0, check exit 0 (only the usual unstamped-override warn). Also drove: tech with no roster entry (resolves via pool-name base), slug/filename mismatch and off-whitelist model (both still refuse at all three consumers), orphaned custom-role item after its override file is deleted (sync no-ops, doesn't crash).
  - show fallback fixed: sq role <dev-slug> show now renders the full card (title/model/can-spawn/creates/mission/responsibilities) instead of the old three-line item fallback, confirmed for a live dev role with no override file at all.
  - Gates: pyright 0 errors; ruff check/format clean; targeted pytest (role/override/sync/check modules + 4 new test files, 445 tests) all green; tests/meta (165 tests, incl. the no-ticket-ID scan) green; sq check clean on this repo.
  - Scope note: docs/overrides.md's owed paragraph (acceptance criterion) was NOT added — the dispatch boundary said touch only src/squads/, tests/, CHANGELOG.md, so I left docs untouched rather than widen scope. Flagging so tech-writer or a follow-up can add it.
  - Commit fb92ef5 on release/0.14, unpushed. BUG-744 left InProgress for QA to verify.
- [2026-08-21T17:29:36Z] Elias Python:
  - Batch review REV-757 came back ChangesRequested with 3 findings on the dev-role fix, all one root cause: fb92ef5 gated the dev merge base on the -dev slug suffix at two of the three consumers instead of ADR-754's stored-fact-first order, and read item.extra[X.TECH] with a bare subscript.
  - F1 (high, crash) fixed: an activated non-dev -dev-suffixed role (e.g. data-dev) no longer KeyErrors at sq role show / sq check — both now check item.extra.is_dev before building a dev base, falling to the -dev naming convention only when there is no item. F2 (medium) fixed: an unactivated -dev slug's preview no longer prints a fabricated pool name that sq dev add later contradicts — --json returns full_name: null, the text card marks it '(unassigned — run sq dev add --tech <tech>)'; a declared full_name still shows through. F3 (medium) addressed: the half that was a real gap (an activated non-dev -dev role's incomplete override silently/crashily bypassing validation) is closed by the same fix; the remaining no-roster-entry preview leniency is the ADR-754/docs-sanctioned pre-activation-preview feature, tested and pinned as intentional rather than further restricted — flagged for the architect if that should change.
  - All three driven red-then-green (reverted each fix, confirmed the exact reported crash/contradiction, restored, confirmed green) — details on each finding's own comment.
  - Gates: pyright 0 errors; ruff check/format clean; targeted pytest (role/override/sync/check modules + 4 new test files, 462 tests) green; tests/meta (165 tests) green; sq check clean.
  - No CHANGELOG entry added — this whole feature is still unreleased/under review, so there is no shipped regression to describe; the existing 0.14.0 entry for the dev-role-override fix already covers the adopter-visible behaviour, and these are correctness refinements to that same not-yet-released surface. Didn't touch docs/ either, per the review-response boundary.
  - Commit 1d1cd19 on release/0.14, unpushed.
<!-- sq:discussion:end -->
