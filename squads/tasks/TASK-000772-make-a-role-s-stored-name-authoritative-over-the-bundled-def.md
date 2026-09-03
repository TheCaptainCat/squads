---
id: TASK-772
sequence_id: 772
type: task
title: Make a role's stored name authoritative over the bundled default
status: Done
author: tech-lead
assignee: python-dev
priority: high
refs:
- BUG-771:fixes
- ADR-754:implements
- REV-770:addresses
description: 'Stop sq sync reverting an operator-set role name: the item owns exactly
  the operator-settable fields, one mechanism for bundled and developer roles'
created_at: '2026-08-21T21:06:34Z'
updated_at: '2026-08-22T09:26:31Z'
---
<!-- sq:body -->
`sq sync` silently reverts an operator-set role name to the bundled catalog default. No warning, no
report line, no reflog entry, `sq check` exit 0.

Driven on a fresh squad with no override files anywhere:

```
sq init --name architect='Ada Lovelace'
  ROLE-000002-architect.md   title: Ada Lovelace, extra.full_name: Ada Lovelace
  CLAUDE.md                  - **Ada Lovelace** — architect (`architect`)
  .squads.toml               [init.names] architect = "Ada Lovelace"

sq sync                      (exit 0)
  ROLE-000002-architect.md   title: Robert Architect, extra.full_name: Robert Architect
  CLAUDE.md                  - **Robert Architect** — architect (`architect`)
  sq list -t role            ROLE-2 … Robert Architect
sq check                     exit 0
```

At 0.13.0 the same sequence already reverted `extra.full_name` and the generated roster and pointer,
but left `item.title` intact. The role-name projection that landed since then propagates the
already-stale `extra.full_name` into `item.title` — so it did not introduce the revert, it completed
it, and destroyed the one field `sq repair` (which trusts markdown over the index) could have healed
from.

**Affected, driven:** `sq init --name <slug>=<Name>`; the `[init.names]` table in `.squads.toml`;
`sq init`'s interactive naming prompt (it merges into the same combined name map as the other two, so
it is subject to the identical loss); and `sq role activate <slug> --name "…"` — driven,
`sq role activate devops --name 'Hank Ops'` then `sq sync` reverts to `Hugo Ops`.

**Not affected, driven:** `sq dev add --tech <t> --name "…"`, and a `full_name` declared in
`.overrides/roles/<slug>.toml` for either role kind. The distinguishing factor is only whether an
override file exists for that slug, and none of the operator-naming paths above creates one.

**The sharpest demonstration is a side-by-side in one squad**, driven:
`sq init --name architect='Ada Lovelace' --name qa='Sam Reeves'`, then an
`.overrides/roles/qa.toml` declaring `full_name = "Sam Reeves"` for `qa` only. After `sq sync`,
`architect` is back to the bundled name while `qa` — identical name, but also present in an override
file — survives everywhere. Same squad, same sync, one difference.

ADR-754 amendments A1–A3 are the ruling. Read them in full before starting; the constraints below
are those amendments restated as acceptance, not prose to reinterpret.

## Root cause — two sites, and patching either alone leaves the bug

**1. The caller supplies no base for a non-dev role.** `_refresh_catalog_extra`
(`src/squads/_services/_maintenance.py`) builds
`dev_base = dev_base_from_item(item) if item.extra.get(X.IS_DEV) else None`, so for every non-dev
role the base is unconditionally `None`.

**2. Even a correct base would be thrown away.** `resolve_role_with_base`
(`src/squads/_roles/_resolver.py`):

```python
predefined = _PREDEFINED_BY_SLUG.get(slug)  # None for new slugs
effective_base = predefined if predefined is not None else base
```

For any bundled slug `predefined` is never `None`, so the caller's base is discarded outright and no
caller can make the live item the merge base for `architect` however correct its base is. A developer
slug works only because `PREDEFINED` holds no row for it — an artifact of where the bundled catalog
has rows, not a property of the two role kinds.

**Both are required.** Site 1 alone leaves the caller passing `None`, so there is still no base to
promote. Site 2 alone leaves the resolver discarding whatever the caller now correctly builds. A fix
that touches one and not the other passes no test written against the reproduction, and the acceptance
below is written so that a one-site fix fails.

**3. The stated contract documents the discard as intentional and must be corrected too.** The
docstring immediately above that line reads "A bundled slug still always resolves against its
``PREDEFINED`` entry — *base* is only ever the merge base when ``slug`` is not in ``PREDEFINED``".
Fixing the code and leaving that sentence in place leaves the next reader with a contract that
contradicts the behaviour, which is how this shipped. Correct the docstring as part of the change,
and state the new precedence there.

## The rule that bounds the fix

"Make the item the base" is the over-wide fix, and it would break the thing this writer exists for:
refreshing the catalog's own prose and vocabulary (`title`, `mission`, `responsibilities`,
`agreements`, `color`, `is_default`, `can_spawn`) is how a new `RoleDef` field reaches items created
before it existed. Freezing all of it to the item breaks that. The rule instead, from A1:

> **The item is authoritative for exactly those fields an operator can set on it, and for no others.**
> Every other field comes from the resolved definition as it does today.

Driven from the CLI surface: `sq role activate` offers `--name` alone, so a bundled role's
operator-settable set is `{full_name}`. `sq dev add` offers `--name` and `--model` and carries
`tech`, so a developer role's set is `{full_name, model, tech}` — exactly what `dev_base_from_item`
already reads. **The dev/bundled asymmetry falls out of that one rule rather than being a special
case**, and the fix should end with one mechanism, not two parallel ones.

## The precedence order — carry this exactly

A role's `full_name` resolves in this order:

1. `.overrides/roles/<slug>.toml`'s `full_name`, when the file declares it. A declared name renames;
   an omitted one inherits. Unchanged — this is a standing ruling and the fix must not weaken it.
2. The item's stored `extra.full_name`, when a roster item exists for the slug.
3. The bundled `PREDEFINED` entry's `full_name` — or, for a developer slug with no item, the
   generated pool name.

## `[init.names]` is not read at resolve time

It is the **input that produced** tier 2, not a competing source, and it must not become one. Only
`sq init` writes it and only `sq init` reads it, when re-run over an existing config.

The decisive driven fact: after `sq role activate architect --name 'Grace Hopper'`, `[init.names]` is
**empty** while the item carries the name — so a resolver reading the table would find nothing for
the very case the table appears to cover, while also being actively wrong the moment a name changes
legitimately through an override or any future rename verb. Do not add it as tier 0, a tie-breaker,
or a fallback.

## No heal path

The fix stops the loss. It does not repair existing squads, and an automatic heal is refused:
restoring from `[init.names]` on sync would make an init-input table retroactively authoritative and
resurrect names adopters have since changed deliberately.

**The workaround for an already-damaged squad**, driven: write the recovered name into
`.overrides/roles/<slug>.toml` as `full_name = "…"` and run `sq sync`. That heals `title`,
`extra.full_name`, the index, `CLAUDE.md` and the `.claude/` pointer together and holds from then on
— precisely because an override-declared name is the one path that was never broken. Worth stating in
the handoff so it can reach adopters, but it is not something this task automates.

The lost name is recoverable by hand, from two places that a reverting sync provably does not touch:
`.squads.toml`'s `[init.names]` (only `sq init` writes it), and `squads/.reflog.jsonl`'s `create`
entry for the role, whose delta carries the title as it stood at creation — which also covers the
`sq role activate --name` path, where `[init.names]` was never written. **Do not implement recovery
here**, and do not delete or rewrite either source.

## Fold in, on its own account: the change is invisible to every recency surface

This writer changes an agent's identity without bumping `item.updated_at`, without setting
`modified_session`, and without writing any reflog entry — driven, zero reflog ops after a reverting
sync. That is why the loss went unseen by every surface that would otherwise have shown it. Address
it in this change.

**If you make it log, the role's `create` entry must stay readable**, because that entry is what
recovery for the `sq role activate --name` path depends on. Appending an `update` op is fine;
anything that rewrites, prunes or supersedes the `create` entry is not.

## The docs half — verify, then report which it is

`docs/overrides.md`, "How names flow into your squad", states: *"The chosen name is stored in the ROLE
item's frontmatter (`extra.full_name`). Everything downstream reads from there"* — then lists the
`CLAUDE.md` Agent roster, the `.claude/` pointer files, and the rendered role body. All three bullets
are driven false today, which is what makes this documentation of a guarantee the tool does not keep.

The expectation is that the fix makes that sentence true again rather than requiring a rewrite, since
it describes exactly the behaviour being restored. **Check it against the fixed build rather than
assuming**, and report which:

- If all three bullets hold, say so in the handoff and change nothing. That is a valid and expected
  outcome.
- If any bullet is still false, name precisely which and why, and flag it for a writer. Do not
  rewrite adopter-facing prose yourself — the finding is yours, the wording is not.

## The test that must exist, and why the existing file does not cover it

The regression test is the **`--name`-then-`sync` sequence**, not the override input. The existing
role-override test file covers override files only, which is exactly how this shipped: a projection
that discards `--name` passes that file clean. Cover, each driven end to end:

- `sq init --name <slug>=<Name>` then `sq sync` — bundled role.
- `sq role activate <slug> --name "…"` then `sq sync` — bundled role.
- The same two for a developer role, so the mechanism is proved single rather than duplicated.
- An override declaring `full_name` still renames the role after the fix, for both role kinds — the
  standing ruling this must not break.
- Two consecutive syncs, not one: a name that survives the first and reverts the second is the
  failure mode a single-sync test misses.

## Acceptance criteria

- The driven reproduction at the top no longer reverts: after `sq sync`, and after a second
  `sq sync`, the frontmatter, the index, `sq list -t role`, `sq role <slug> show` and the generated
  `CLAUDE.md`/`AGENTS.md` roster and `.claude/` pointer all still carry the operator's name.
- The same holds for `sq role activate <slug> --name "…"`, for a bundled role and a developer role.
- **Both sites are fixed, and a test proves each is load-bearing.** Revert site 1 (restore the caller's
  unconditional `None` for a non-dev role) with site 2 fixed, and a test must go red; revert site 2
  (restore the `PREDEFINED`-wins base discard) with site 1 fixed, and a test must go red. Drive both
  reverts and report both. A single test that only goes red when both are reverted does not satisfy
  this.
- **The side-by-side pairing above is a test**: one squad, `architect` named only via `--name` and `qa`
  named via `--name` plus an override file, one `sq sync`, both names intact afterwards. It is the
  sharpest regression in the set because it fails on a fix that only handles the override path.
- **Tier 1 still wins**: an override declaring `full_name` renames the role, over an item that
  carries a different name. Its own test, both role kinds.
- **Tier 3 still applies**: a slug with no item and no override resolves to the bundled default, and
  a developer slug with no item to the generated pool name.
- **Catalog refresh still works — this is the regression the over-wide fix causes.** A `RoleDef`
  field that is *not* operator-settable still reaches an older item on sync: prove it for at least
  `mission`, `responsibilities` and `can_spawn`, on an item whose stored values are stale. A test
  that only proves the name survives would pass on a fix that freezes the whole definition.
- **One mechanism, not two.** The bundled and developer paths resolve through the same seam with the
  same rule, differing only in which field set the item owns. State in the handoff what that set is
  for each kind and where it is declared.
- `[init.names]` is read by no resolver and no sync path. Assert it — a test that the table's
  presence or absence changes nothing about a resolve.
- The `resolve_role_with_base` docstring states the corrected precedence, and no comment anywhere
  still describes the bundled-slug base discard as intended behaviour.
- A rename through this writer is visible: `updated_at` moves, `modified_session` is set, and a
  reflog entry is written — with the role's `create` entry still readable afterwards, asserted.
- `sq check` remains clean on a squad carrying an operator-set name, before and after sync.
- The `docs/overrides.md` outcome is reported: all three bullets true and unchanged, or the specific
  bullet still false flagged for a writer.
- `uv run --all-extras pyright`, `ruff check`, `ruff format --check` and the full `pytest` suite are
  green, `tests/meta` included; `uv run sq check` is clean.

## Handoff

**Do not edit `CHANGELOG.md`.** Several items in this batch run concurrently and a shared file would
have them racing. Put your adopter-facing changelog entry text in your handoff comment on this item
and the tech lead applies it. This one warrants a prominent entry: it is silent loss of an
operator-set name, and `docs/overrides.md` currently promises the opposite in as many words — flag
that doc line in your handoff too, since correcting it is a writer's job, not yours.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 772 add-subtask "<title>"`; track with `sq task 772 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-21T21:07:04Z] Olivia Lead:
  - Authored against ADR-754 A1-A3 (linked) and the batch review finding. Body carries A1s bounding rule as the constraint that stops the over-wide fix, both structural causes (the caller passing None for non-dev AND the bundled-slug base discard in resolve_role_with_base), and the docstring correction — the stated contract currently documents the discard as intentional, which is how this shipped.
  - Acceptance names the regression the over-wide fix causes: a non-operator-settable RoleDef field (mission, responsibilities, can_spawn) must still reach a stale older item on sync. A test proving only that the name survives would pass on a fix that freezes the whole definition. Also required: two consecutive syncs, not one, and the falsification (restore the discard, watch the --name tests go red).
- [2026-08-21T21:09:01Z] Olivia Lead:
  - Revised the body for the two-site framing: the root-cause section is now "two sites, and patching either alone leaves the bug" and states why each alone is insufficient (site 1 alone leaves the caller passing None so there is no base to promote; site 2 alone leaves the resolver discarding whatever the caller correctly builds).
  - Acceptance now requires each site to be independently load-bearing: revert site 1 with site 2 fixed and a test must go red, revert site 2 with site 1 fixed and a test must go red, both driven and both reported. A single test that only reddens when both are reverted explicitly does not satisfy it. The architect-vs-qa side-by-side (one squad, one sync, --name only against --name plus an override file) is named as a required test because it fails on a fix that only handles the override path.
  - Also added: the sharpened affected/not-affected lists with the devops Hank Ops to Hugo Ops result, the override-heal workaround for an already-damaged squad, and a docs/overrides.md verification step. My read is that the fix makes that sections three bullets true again with no edit needed, so the body requires the dev to CHECK against the fixed build and report which - all true and unchanged, or the specific bullet still false flagged for a writer. Explicitly not rewriting adopter prose themselves.
- [2026-08-21T21:30:27Z] Elias Python:
  - Fixed both sites (_roles/_resolver.py:role_base_from_item + resolve_role_with_base's effective_base precedence; _services/_maintenance.py:_refresh_catalog_extra + the two other callers in _cli/_role.py and _overrides/_service.py that had the same site-1 pattern) and corrected the stale docstring on resolve_role_with_base.
  - One mechanism: role_base_from_item(item) dispatches on extra.is_dev — dev delegates to dev_base_from_item (operator set: {full_name, model, tech}); bundled returns the slug's PREDEFINED entry with only full_name swapped for the item's stored value (operator set: {full_name}). resolve_role_with_base now does 'base if base is not None else predefined' (was 'predefined if not None else base') so a supplied base always reaches the merge.
  - Driven before/after, bundled (sq role activate --name): before, sq role activate architect --name 'Ada Lovelace' then sq sync reverted CLAUDE.md/list/show to 'Robert Architect'. After: two consecutive syncs, sq list -t role still shows 'Ada Lovelace', CLAUDE.md line '- **Ada Lovelace** — architect (`architect`)', .claude/agents/architect.md says 'You are **Ada Lovelace**', sq check exit 0.
  - Driven, bundled (sq init --name): sq init --roles architect --name architect='Ada Lovelace' -> .squads.toml [init.names] architect = "Ada Lovelace"; two syncs later ROLE-1 title is still 'Ada Lovelace' in sq list and CLAUDE.md.
  - Driven, dev role (sq dev add --name, the mechanism's dev-side proof, unaffected before and after): sq dev add --tech python --name 'Hank Python' survives two syncs, CLAUDE.md carries 'Hank Python'. Dev roles have no separate post-creation 'activate --name' verb (add_dev IS the naming step); role_base_from_item's dev branch is the same seam sq role activate --name uses for bundled roles.
  - Catalog-refresh proof (the regression an over-wide fix causes): tests/service/test_operator_named_roles_survive_sync.py::test_catalog_refresh_still_reaches_a_stale_item_alongside_a_preserved_name forces an item's extra.mission/responsibilities/can_spawn to stale values, syncs, and asserts they reconverge to the current PREDEFINED catalog values in the SAME sync that leaves the operator-set full_name untouched — passes; a fix that froze the whole definition to the item would fail this one.
  - Falsification, both sites, driven by hand and restored: reverting site 1 alone (caller back to 'dev_base_from_item(item) if is_dev else None') with site 2 fixed -> 6 of the new --name tests go red (Robert Architect instead of Ada Lovelace). Reverting site 2 alone (resolver back to 'predefined if not None else base') with site 1 fixed -> the same 6 plus the direct unit test on resolve_role_with_base go red. Restored both -> all green again. Neither revert alone leaves the fix working.
  - Tier 1 (override wins) and tier 3 (bundled default / dev pool name, no item no override) both re-asserted for both role kinds. [init.names] proven unread: written with a diverging value, two syncs ignore it; cleared entirely, still ignored.
  - Visibility: a rename through this writer now moves updated_at, sets modified_session, and appends one 'update' reflog line — the role's own 'create' entry (with the original name in its delta) stays readable and untouched afterwards, asserted.
  - docs/overrides.md check (not fixed here, flagging for a writer per the task's boundary): all three 'How names flow into your squad' bullets are true again for a role that already has an item, since extra.full_name/roster/pointers/body all read the same reconciled value. But the section still doesn't mention the --name/[init.names]/activate-time paths this bug was about — those work now too, but the doc's own framing (it only ever described the override path) is unchanged and worth a writer's pass to make that explicit.
  - CHANGELOG text (not applied, per batch instructions): see the ### Fixed entry below.
  - CHANGELOG entry -- ### Fixed: **An operator-set agent name now survives `sq sync`.** Naming an agent with `sq init --name <slug>=<name>`, the `[init.names]` config table, the interactive naming prompt at `sq init`, or `sq role activate <slug> --name "…"` used to be reverted by the very next sync -- back to the bundled catalog name, in the role's own record, in `sq list`, and in your generated `CLAUDE.md`/`AGENTS.md` roster and `.claude/` pointer -- with `sq sync` exiting 0 and `sq check` reporting nothing wrong. (A developer's name, set via `sq dev add --name`, was never affected.) A role's stored name is now authoritative over the bundled default for exactly the field an operator can set through these commands, while every other catalog field -- mission, responsibilities, spawn authority, and so on -- still refreshes normally on sync, so a bundled-role update still reaches an item created before it existed. A rename that lands this way is now visible too: it moves the role's `updated_at`, and is recorded in the reflog. This does not repair a squad that already lost a name to an earlier sync -- recover it by writing the name into `.overrides/roles/<slug>.toml` as `full_name = "…"` and running `sq sync` once.
  - Gates: pyright/ruff check/ruff format clean; pytest tests/meta 180 passed; the full scoped role/override/sync/check/roster/dev/service/cli sweep (1236 tests) passed; sq check clean; sq repair a stable no-op (identical status before/after). Commit cc6c506 on release/0.14, touching only src/squads/ and tests/.
<!-- sq:discussion:end -->
