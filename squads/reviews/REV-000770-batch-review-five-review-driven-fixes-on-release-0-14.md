---
id: REV-770
sequence_id: 770
type: review
title: 'Batch review: five review-driven fixes on release/0.14'
status: Approved
author: reviewer
refs:
- TASK-762
- TASK-763
- TASK-764
- TASK-765
- TASK-767
- BUG-755
- BUG-756
- BUG-758
- BUG-760
- BUG-761
- REV-757
- ADR-753
- ADR-766
description: 'Batch review of the five commits that closed BUG-755/756/758/760/761:
  role-field projection, once-per-invocation cross-check, advisory soft-wrap sweep
  plus its class guard, blank-override refusal, and the raise-path read-scope test.'
subentities:
- local_id: F1
  title: sq sync silently discards an operator-set role name
  status: Fixed
  severity: high
- local_id: F2
  title: Soft-wrap sweep missed --at; CHANGELOG says it is fixed
  status: Fixed
  severity: medium
- local_id: F3
  title: Class guard is blind to the common.<console>.print form
  status: Fixed
  severity: medium
- local_id: F4
  title: Blank-field refusal does not cover the --name flag
  status: WontFix
  severity: medium
- local_id: F5
  title: Interrupted projection no longer self-heals on the next sync
  status: WontFix
  severity: low
- local_id: F6
  title: Interrupted-write test skips the shape it is named for
  status: WontFix
  severity: low
- local_id: F7
  title: Reconciled-key table's stated justification is false
  status: WontFix
  severity: low
- local_id: F8
  title: resolved_spec contract misnames its callers in three places
  status: WontFix
  severity: low
created_at: '2026-08-21T20:52:11Z'
updated_at: '2026-08-22T09:46:17Z'
---
<!-- sq:body -->
## Scope

Five commits on `release/0.14`, plus the two documentation commits that record them, reviewed as
one increment. Each fix closes a bug produced by the previous batch review (REV-757).

| commit | change | items |
|---|---|---|
| `3fadd44` | read-scope invalidation pinned on the transaction raise path (test-only) | BUG-761, TASK-765 |
| `472e7b6` + `f65bdf4` | blank/whitespace-only role-override fields refused, then the message cleaned of pydantic internals | BUG-760, TASK-764 |
| `9ebcf6d` | 33 single-line CLI advisory prints soft-wrapped, plus an AST class guard | BUG-755, TASK-762 |
| `ac0bebb` | the workflow index cross-check runs once per invocation | BUG-758, TASK-763, ADR-753 A4 |
| `03c0802` | a role's resolved `full_name`/`mission` projected onto the item's own `title`/`description` | BUG-756, TASK-767, ADR-766 |
| `fe8bf1b`, `bcde26b`, `bf235b3` | the adopter-facing record of the above | — |

## Method

Attacked input shapes, not the designs. Every claim is labelled **driven** (reproduced against a
real `sq` invocation or an in-process probe), **read** (traced in source or by AST scan without
executing the failing path), or **inferred**.

Harnesses used: a counter around `SquadsDB.model_validate_json` with a call-site trace (whole-index
parses per invocation); a counter around `IndexStore._atomic_write` (index commits per sync); the
class guard's own `_unwrapped_marker_hits` walk driven over both the real tree and planted trees;
and a git worktree at the parent commit `ac0bebb`, so every "this is new" claim is a measured
before/after rather than an assumption.

Throwaway squads under a scratch directory. Targeted test runs only — the suite was reported green
and was not re-run.

## What holds up

Verified working, recorded so it is not re-derived:

- **The projection converges and never moves a file.** Driven across three renames in one sync
  (a bundled role, a dev role, an archived role), plus a rename removed again: markdown and index
  agree on `title`/`description` afterwards on every surface, the filename keeps the *role* slug
  (`ROLE-000002-architect.md`), `item.slug` stays `architect`, `sq check` is clean and `sq repair`
  is a stable no-op. `item.path`/`item.slug` are derived from the filename at load
  (`_frontmatter_payload`), never persisted, and the projection assigns `title` directly rather
  than through `_rename` — so the "path is unchanged" claim is structurally true, not just
  test-true.
- **The no-op gate really skips the write.** Driven with a counter around
  `IndexStore._atomic_write`: a sync with nothing to change performs **0** index commits, so the
  `if not previous_extra and not previous_fields` gate sits before the transaction, not after it.
- **No index-ahead-of-markdown state on any projection path.** `update_frontmatter` runs inside
  the transaction body, before `db.add`, and `transaction()` reaches `_atomic_write` only on the
  success path — so a raise anywhere between the frontmatter write and the commit leaves markdown
  ahead, the direction invariant 8 sanctions. The `SquadsError` rollback restores the two
  top-level fields as well as `extra`, and the loop's later writers reuse the same rolled-back
  object (`roster_roles` holds one deep copy per role, shared by both refresh calls), so no seam
  writes a half-updated item.
- **The cross-check still runs, once.** Driven on an override-carrying squad: `sq list`,
  `sq check`, `sq sync`, `sq <type> <n> show --json` and `sq show <id> --json` each perform
  exactly **2** whole-index parses (one cross-check, one real read); with no override, 1. The
  custom-type dispatch path — the one place a spec is resolved before the root callback runs —
  also stays at 2, so `sq incident 23 show --json` does not pay a second bind.
- **Neither direction of the cross-check bypass is lost.** Driven: a re-prefixing override against
  a non-empty corpus makes `sq list` exit 1 with the cross-check message (the refusal survives the
  memo); `sq check` degrades to a clean `workflow config invalid` issue; `sq repair` reaches its
  own guard rather than the cached refusal. With a *broken* override, `sq list` exits 1,
  `sq check` exits 3 cleanly and `sq repair` exits 0 — the cached `spec_error` is raised as a
  `SquadsError`, which is exactly what `get_service_bypassing_index_cross_check` catches.
- **The blank-field check covers the field set it claims.** All four required strings, both
  optional strings with `None` kept distinct from `""` (the `is not None and not value.strip()`
  guard), and both list fields per element. `slug` is excluded correctly: `_apply_override`
  overwrites it from the filename (`merged["slug"] = slug`) after refusing any disagreeing
  declaration, so a declared blank slug can never survive. `_apply_override` is genuinely the only
  place a `RoleSpec` is built from adopter-editable text — `load_role_catalog` reads the bundled
  `roles.toml` only, and enforces the same non-blank rule itself in `_check_slugs` — so moving the
  check off the model in `f65bdf4` cost no coverage on any path that exists today.
- **The wrong-type leak boundary is the right call.** A wrong-*type* value still surfaces pydantic
  text, pinned by a test that says so. Acceptable: the two checks now live in different layers, and
  the docstring states the consequence (a future `RoleSpec` field gets type-checking but not
  blank-checking automatically) rather than hiding it.
- **The raise-path test is a real falsifier.** It asserts the read after a raising transaction sees
  a *second* store's committed value, so moving the `snapshots.pop` onto the success path reddens
  it. The sibling test that pins the scope's own binding across a normal and an error exit is a
  genuine addition, not a restatement.
- **The `PERMITTED_EXTRA_SKEW` pin is the right shape.** `test_permitted_extra_skew_membership_is_pinned_exactly`
  asserts the literal key set rather than re-deriving it from `RoleDef.extra_keys()`, so appending
  a field to `_EXTRA_FIELD_KEYS` instead of `_RECONCILED_EXTRA_KEYS` — the unsafe direction —
  reddens it. That is the class-level assertion this file was asked for, and it delivers.

## Did any fix treat the symptom and leave the cause?

Yes — one, and it is F1. BUG-756 reported a role item whose record "disagrees with itself":
`extra.full_name` tracked a declared rename while the item's own `title` did not. The fix resolves
that disagreement in one direction unconditionally — the resolved catalog definition always wins,
and is now written onto the item's own fields.

For the input BUG-756 drove (an override file declaring `full_name`) that direction is right: the
override is the durable declaration and the item was the stale copy. But the *same* disagreement
arises from a second input with the opposite correct answer — a name the operator supplied with
`sq init --name` / `sq role activate --name`, where the item is the only record and the bundled
catalog is the stale side. `resolve_role` has no equivalent of `dev_base_from_item` for a non-dev
role, so nothing feeds the operator's declared name back into resolution. That is the root cause
BUG-756 was a symptom of, and it is untouched; the projection now overwrites the last copy of that
name instead of the disagreement being visible. See F1 for the driven before/after.

The other four fixes address their causes. `ac0bebb` removes a redundant call rather than
suppressing its cost. `472e7b6`/`f65bdf4` refuse at the one construction seam instead of hardening
renderers — though the seam is narrower than the bug's verdict assumed (F4). `9ebcf6d` adds a
property-level scan rather than another hand list, which is the right instinct; the scan's
predicate is what falls short (F3). `3fadd44` pins the behaviour the bug named, with no source
change.

## Verdict

**ChangesRequested**, on F1 alone. It silently destroys operator-supplied data on a routine
command, `sq check` is clean throughout, and the adopter documentation states the opposite
guarantee. F2/F3/F4 are worth fixing in this increment but none of them loses data.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 770 add-finding "…" --severity medium`; track with `sq review 770 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟠 high | Fixed |  | sq sync silently discards an operator-set role name |
| F2 | 🟡 medium | Fixed |  | Soft-wrap sweep missed --at; CHANGELOG says it is fixed |
| F3 | 🟡 medium | Fixed |  | Class guard is blind to the common.<console>.print form |
| F4 | 🟡 medium | WontFix |  | Blank-field refusal does not cover the --name flag |
| F5 | 🟢 low | WontFix |  | Interrupted projection no longer self-heals on the next sync |
| F6 | 🟢 low | WontFix |  | Interrupted-write test skips the shape it is named for |
| F7 | 🟢 low | WontFix |  | Reconciled-key table's stated justification is false |
| F8 | 🟢 low | WontFix |  | resolved_spec contract misnames its callers in three places |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — sq sync silently discards an operator-set role name

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
**driven**, with the before/after measured on a git worktree at the parent commit `ac0bebb`.

`sq init --name <slug>=<Name>` and `sq role activate <slug> --name "…"` are documented ways to
choose an agent's name. `sq sync` reverts them to the bundled catalog name — in the item's own
frontmatter, in the index, in `sq list`, and in the generated `CLAUDE.md`/`AGENTS.md` roster and
`.claude/` pointer. No warning, no report line, `sq check` clean, exit 0.

Reproduced on a fresh squad, no override files anywhere:

    sq init --name architect=Rob --name qa=Sam
      ROLE-000002-architect.md   title: Rob
      ROLE-000005-qa.md          title: Sam
      CLAUDE.md                  - **Rob** — architect (`architect`)
      sq list -t role            ROLE-2 … Rob     ROLE-5 … Sam

    sq sync                       (exit 0, no skipped lines, no warning)
      ROLE-000002-architect.md   title: Robert Architect
      ROLE-000005-qa.md          title: Mara Tester
      CLAUDE.md                  - **Robert Architect** — architect (`architect`)
      sq list -t role            ROLE-2 … Robert Architect
      extra.full_name            Robert Architect
    sq check                      exit 0

**What this commit changed, measured rather than assumed.** The same scenario driven on `ac0bebb`
(the parent) reverts `extra.full_name` and therefore the generated roster and pointer — that half
is pre-existing — but leaves `title: Rob` in the frontmatter and `Rob` in `sq list`. So before this
commit the operator's name survived in the item's own record; after it, nothing on disk remembers
it. The projection did not introduce the revert, it completed it, and removed the copy `sq repair`
could have rebuilt from.

**Root cause, and why the fix is the same shape as the one already shipped.** For a developer role
`_refresh_catalog_extra` resolves through `dev_base_from_item`, which reads *this item's own*
stored tech/name/model, so a dev's `--name` is durable — driven: a `python-dev` renamed by an
override keeps the new name after the override file is deleted. A non-dev role has no equivalent:
`resolve_role(slug, squad_dir)` layers only `.overrides/roles/<slug>.toml` over the bundled
definition, and consults neither the item nor the `[init.names]` table `sq init` itself persists.
That table is on disk and is unread:

    squads/.squads.toml
    [init.names]
    architect = "Rob"
    qa = "Sam"

**Why this is high, not medium.** `docs/overrides.md` ("Agent naming" → "How names flow into your
squad") tells the adopter the opposite in as many words: "The chosen name is stored in the ROLE
item's frontmatter (`extra.full_name`). Everything downstream reads from there: the Agent roster in
your `CLAUDE.md` (generated by `sq sync`) …". Driven false. The same section also documents the
`[init.names]` config table and interactive naming prompts as first-class, so the input that loses
data is the one the docs steer an adopter towards, and the loss lands on every generated file an
agent reads as its own identity.

Two smaller observations from the same seam, recorded here rather than as their own findings:

- the projection does not bump `item.updated_at` or set `modified_session`, so a rename is
  invisible to any recency surface and to the reflog. Pre-existing for the `extra` half of this
  writer; new for the item's own fields.
- once the projection has written a dev role's overridden name into `extra.full_name`, deleting the
  override file no longer reverts it (driven) — correct per the partial-dev-override change's own
  changelog entry, but worth knowing it makes an override's effect on a dev role one-way.

**Direction of fix (not prescriptive).** Give a non-dev role the same treatment a dev role already
gets: build the merge base from the item's own stored identity (or from `[init.names]` when there
is no item yet) so a declared override still wins over the bundled default, while the operator's
own name wins over the bundled default too. Whatever the direction chosen, it needs a driven test
on the `--name`-then-`sync` sequence: the current test file covers the override input only, so a
projection that discards `--name` passes it.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-08-21T20:58:34Z] Catherine Manager:
  - Confirmed independently, and the pre-existing/new split is now measured. On a fresh squad at 0.13.0 (ea891a6, in a throwaway worktree): sq init --name architect=Ada Lovelace then sq sync leaves sq list showing Ada Lovelace while extra.full_name has already reverted to Robert Architect. So 0.13.0 shipped half of this - the extra copy and the generated roster already lost the operator-set name on the first sync. On release/0.14 the same sequence now reverts the item title and the frontmatter too, so the last surviving correct copy is gone and sq list shows the bundled name. sq check exits 0 in both cases.
  - Accepting this as ChangesRequested on F1. It is silent loss of an operator-set name, the docs promise the opposite in so many words, and the remedy is a shape already shipped for dev roles. Treating it as its own bug rather than reopening BUG-756, whose reported defect is genuinely fixed and verified.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Soft-wrap sweep missed --at; CHANGELOG says it is fixed

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
**driven** (the wrap), **read** (the two `sq import` sites, proven by AST scan rather than by
running an import).

The sweep fixed 33 sites. It missed `src/squads/_cli/__init__.py:267` — the `--at` timestamp
refusal — which was one of the four sites the previous review named explicitly, and which the
0.14.0 CHANGELOG now claims is fixed.

Driven at `COLUMNS=80`, stderr piped, `$` marking the newline Rich inserted:

    sq --at nope list
      error: invalid --at timestamp 'nope' (use ISO 8601, e.g. 2024-01-15 or $
      2024-01-15T09:30:00Z)$

    sq reflog --since nope          (the sibling this sweep did fix, for contrast)
      error: invalid --since timestamp 'nope' (use ISO 8601, e.g. 2026-01-15 or 2026-01-15T09:30:00Z)$

The CHANGELOG entry as it now stands claims both: "The same now holds for every other single-line
advisory `sq` prints: … an invalid `--at` or `sq reflog --since` timestamp …". Half of that
sentence is false, and it is adopter-facing — the same defect class the previous review's F13
raised about the previous version of this same entry.

Two further unwrapped sites in the same class, found by AST scan and not driven through the CLI:

- `_cli/_import.py:95` — `[yellow]warning:[/yellow] {warning}`, one line per importer warning.
  Marker-matching, no `soft_wrap`.
- `_cli/_import.py:74` — `[red]line {n}:[/red] {message}`, one line per pre-pass issue; carries
  file paths and ids that exceed 80 columns. Not marker-matching either, because `MARKERS` holds
  the literal `[red]error` and this reads `[red]line`.

All three share one property with each other and with nothing that was fixed: their receiver is
`common.err_console` / `common.console`, not a bare `console` name — which is exactly why the new
guard cannot see them (F3). Fixing the sweep and fixing the guard are the same job.

Not filed higher because nothing is lost — the text is all still there, just reflowed — but a
CHANGELOG that names a specific command as fixed when it is not is what an adopter benchmarks
against and files a bug on.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-08-21T21:43:31Z] Catherine Manager:
  - Confirmed both halves. Drove sq --at nope list piped at 80 columns: the ISO example still splits across a newline, while sq reflog --since nope is intact - so the sweep genuinely missed the root callbacks --at parser. The CHANGELOG sentence claiming --at was fixed was mine, not the developers; I have corrected it so the adopter-facing text no longer overclaims, and named --at explicitly as still unchanged. The code half stands open as this finding.
- [2026-08-22T09:23:52Z] Catherine Manager:
  - Both halves closed. The code half landed in 04945d2 and I drove it: sq --at nope list piped at 80 columns keeps the ISO example on one line and the exit code stays 2. The CHANGELOG sentence is corrected back - --at is now listed among the fixed sites rather than the exceptions.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Class guard is blind to the common.<console>.print form

<!-- sq:finding:F3:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
**driven**, by running the guard's own walk over both the real tree and planted trees.

`tests/meta/test_single_line_advisory_prints_stay_soft_wrapped.py` resolves a print's receiver with

    def _receiver_name(func: ast.expr) -> str | None:
        if isinstance(func, ast.Name):
            return func.id
        return None

so only a bare `console` / `err_console` / `target` name is ever in scope. A module-qualified
receiver — `common.console.print(...)`, `common.err_console.print(...)`, an `ast.Attribute` — is
not merely unmatched, it is never collected as a candidate at all. Two files in `_cli/` use that
form exclusively: `_cli/__init__.py` and `_cli/_import.py`.

Driven, calling the module's own `_unwrapped_marker_hits` (the same helper the real assertion runs):

    over src/squads/_cli, keyed at repo root   -> {}          (guard reports zero hits)
    over a planted tree containing a verbatim copy of
    _cli/__init__.py:267 with a `common.err_console` receiver -> {}   (still zero)

Meanwhile a direct AST scan of the same tree, differing only in accepting an `ast.Attribute`
receiver, finds two marker-matching, unwrapped calls: `_cli/__init__.py:267` and
`_cli/_import.py:95` (see F2). So the guard's green is not evidence the property holds — it is
evidence the property was not checked on those files.

The module's four plant tests all plant a bare `console` receiver, so none of them can catch this;
`test_the_allowlist_has_no_stale_entry` cannot either, because the allowlist is empty. The guard's
own docstring makes the claim this falsifies: "a new site added tomorrow — in a file nobody was
looking at when they wrote it — is caught the same way a regression at an existing site would be."
It is not, if that file imports the console the way two existing files already do.

**On whether the guard is worth keeping.** Yes, and the AST/literal-text framing is the right one:
restricting to `ast.Constant`/`ast.JoinedStr` first arguments excludes every `Table`/`Panel`/bound-prose
render by construction rather than by allowlist, which is what makes an empty allowlist honest. The
two weaknesses are in the predicate, not the idea, and both are a few lines:

1. accept an `ast.Attribute` receiver whose trailing attribute name is in `_CONSOLE_RECEIVERS`
   (`common.err_console` → `err_console`), and add a plant test for that shape;
2. the documented hole — a print whose marker is computed at runtime — is real but narrower than
   feared. I scanned every unwrapped, interpolated console print under `_cli/` for a
   runtime-computed advisory prefix and found exactly one, `_cli/_main.py:1577`
   (`f"[{color}]{i.level}[/{color}]…"`, the `sq check` issue line), which the sweep did fix by
   hand. Nothing else in the package builds its `error`/`warning` word at runtime. A guard that
   forbids a *computed* style tag on a console print (rather than trying to read it) would close
   that class too, at the cost of one allowlist entry for the site that legitimately does it.

Filed medium rather than low because the guard's stated purpose is to make the hand list
unnecessary, and it currently certifies as clean a tree that contains the exact defect it was
written to prevent.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-08-22T09:23:55Z] Catherine Manager:
  - Fixed in 04945d2 and it proved itself: the widened predicate flagged the --at site on the live tree before any fix was applied, so the guard caught a real defect rather than only a planted one. An attribute-form plant test now pins the hole shut, and the dev declined two tempting widenings with reasoning recorded in the module docstring - growing the marker list to [red]line (too generic a Rich tag) and the forbid-computed-style-tag rule (one site, already wrapped).
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Blank-field refusal does not cover the --name flag

<!-- sq:finding:F4:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟡 Medium
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
**driven** on two commands and all four generated surfaces.

BUG-760's verdict was to refuse the blank string once, "where the override is parsed/merged", on the
grounds that this "closes it for every current and future render site in one place". It does not:
the refusal lives in `_apply_override`, and the `--name` flag never goes through it. `dev_role` /
`dc_replace` build a `RoleDef` directly, so a whitespace-only name reaches `create` unchallenged —
`Item.title` is `min_length=1`, which `"   "` satisfies.

Driven, fresh squads:

    sq dev add --tech go --name "   "
      added     (`go-dev`) ROLE-21                                       exit 0
      CLAUDE.md                  - **   ** — Go developer (`go-dev`)
      .claude/agents/go-dev.md   You are **   **, the Go developer on this project.
      sq role go-dev show --json "full_name": "   "
      frontmatter                title: '   '
      sq check                   ✓ no issues                              exit 0

    sq role activate architect --name "   "
      activated     (ROLE-12)                                            exit 0
      CLAUDE.md                  - **   ** — architect (`architect`)
      sq check                   exit 0

    # the same value declared in the override file, for contrast — refused correctly
    .overrides/roles/architect.toml:  full_name = "   "
    sq sync
      error: invalid role override …/architect.toml: field(s) blank or whitespace-only
      (omit the key instead to inherit): full_name                       exit 1

That is BUG-760's own reproduction, symptom for symptom — including the pointer file's identity
sentence, which the bug called "the worst instance, because it is prose an agent reads as its own
identity" — reachable through a documented flag rather than an override file, with `sq check` silent.

`--name ""` (empty rather than whitespace) is harmless by accident: it is falsy, so it falls through
to the pool/bundled name. Only the whitespace form lands. That inconsistency is worth closing in the
same pass: `""` should refuse rather than be silently ignored, for the same reason the override path
refuses it.

The blank check itself is correct where it runs (see the review body). What is wrong is the claim
about its reach. Direction of fix: validate the operator-supplied name at the two roster entry
points (`activate_role`, `add_dev`) with the same message `_refuse_blank_strings` produces, or move
the name through a seam both paths share.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-08-22T09:35:38Z] Mara Tester:
  - Re-driven independently: sq dev add --tech go --name "   " and sq role activate architect --name "   " both land the whitespace-only name everywhere (frontmatter, CLAUDE.md, the .claude pointer's identity sentence), sq check silent, exit 0 on both; the override path refuses the identical value on the same squad. Also confirmed --name "" is harmless only by accident (falsy, falls through to a pool name) -- a separate small inconsistency worth closing in the same pass.
  - Not fixed in this review's scope -- tracked on BUG-778. WontFix here means homed elsewhere, not declined.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Interrupted projection no longer self-heals on the next sync

<!-- sq:finding:F5:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
**driven**, on both this commit and its parent.

`title` and `description` are ordinary top-level frontmatter keys, so `frontmatter_skew` compares
them at every write seam — `_without_permitted_extra_skew` structurally cannot exempt a top-level
field, which the commit's own docstring notes. The consequence is that an interrupted catalog
refresh (markdown written, index commit not reached — the state invariant 8 explicitly sanctions)
stops `sq sync` from converging on that role until `sq repair` runs.

Driven, by rolling the index back on ROLE-2 to simulate the interrupt while markdown stayed ahead:

    sq sync
      warning: ROLE-2: on-disk frontmatter has diverged from the index (description, title)
               — run `sq repair` before mutating ROLE-2 again
      warning: ROLE-2: on-disk frontmatter has diverged from the index (description, title)
               — run `sq repair` before mutating ROLE-2 again
      synced managed files to this squads version                    exit 0
      index title:    'Rob'          markdown title: 'Ada Lovelace'   (unchanged, both)
    sq check                                                         (no mention of it)

The same simulated interrupt on the parent commit `ac0bebb`, rolled back on `extra.full_name`
instead, self-heals silently: `sq sync` exits 0 with no warning and the index picks the markdown
value up, because those keys are in `PERMITTED_EXTRA_SKEW`. So the projection converts a
previously self-healing state into one that needs an explicit repair.

This is defensible — it is the guard doing its job, and the docstring says so ("an interrupted
refresh leaves the sanctioned one-sided skew `sq repair` heals"). Filed low, for three reasons
worth someone's judgement rather than a code change decided here:

- the role is now stuck for *both* refresh writers, so its `extra.skills` cache and its rendered
  body stop refreshing too, not only the catalog merge;
- the same message is printed twice per affected role (once per writer), which reads as two
  problems;
- `sq check` has no frontmatter-skew rule at all, so the only signal is a transient sync warning.
  A state the tool itself says requires `sq repair` is invisible to the command whose job is to say
  whether the squad is healthy.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-08-22T09:35:53Z] Mara Tester:
  - Re-driven, and the regression-vs-pre-existing question settled by direct comparison, not inferred: simulated the interrupt on release/0.14 (index rolled back on title/description) -- warning prints twice, sync exits 0, no convergence, sq check silent, sq repair heals it. Re-drove the same simulated interrupt on the parent commit ac0bebb (git worktree) rolling back extra.full_name instead: no warning at all, and the sync silently reconverges both sides in one pass, because that key sits in PERMITTED_EXTRA_SKEW. This IS a regression introduced by the projection landing title/description as ordinary top-level keys the skew guard already polices -- not a pre-existing gap the projection merely inherited.
  - Not fixed in this review's scope -- tracked on BUG-779 together with F6 (one subject: the behaviour and the test meant to pin it). WontFix here means homed elsewhere, not declined.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Interrupted-write test skips the shape it is named for

<!-- sq:finding:F6:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F6:head:end -->

<!-- sq:finding:F6:body -->
**read** (the test), **driven** (the behaviour it does not cover — see F5).

`tests/service/test_role_projects_resolved_name_and_mission_onto_item_fields.py::test_repair_and_a_further_sync_are_unaffected_by_the_interrupted_role_write`
patches `maintenance.update_frontmatter` to raise on its first call. The raise happens *inside*
`update_frontmatter`, so `_aio.atomic_write_text` is never reached and the markdown file is never
touched. The state left behind is "nothing written on either side", not the interrupted write the
name promises — markdown written, index commit not reached.

Two consequences:

- the test never calls `svc.repair()` despite `repair` being the first word of its name;
- its assertion `assert not second_sync` is true only for the shape it actually creates. In the
  shape it is named for, a further sync does **not** heal: it reports the divergence (twice) and
  leaves both sides unchanged until `sq repair` runs. Driven — see F5.

The test is not worthless: it is a genuine falsifier for the in-memory rollback, because without
the rollback the still-mutated item would be written to markdown by the *next* writer in the same
loop, and the second sync would then refuse. But it does not pin what its name claims, and the
behaviour it would have found is F5.

Two smaller notes on the same file, both fine as they stand and recorded so they are not
re-derived:

- the monkeypatch on `maintenance.update_frontmatter` deliberately does not reach
  `_refresh_role_skills_extra` (which holds its own reference in `_services/_base.py`). That is
  what makes `skipped == ["simulated write failure"]` a single-element list, and it is the right
  scoping for this test — but it is also why the real double-report in F5 is invisible here.
- the file's opening claim, that every assertion checks the declared string rather than agreement
  between the top-level field and its `extra` copy, holds throughout. That is the right shape and
  it is worth keeping; F1 is not a hole in it but a missing *input* (a `--name`-supplied name),
  which no test in the file exercises.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-08-22T09:36:01Z] Mara Tester:
  - Confirmed by reading update_frontmatter directly: its own last statement is the atomic_write_text call, so the test's monkeypatch (replacing the whole function to raise) means that write is never reached at all -- nothing written on either side, not the markdown-written/index-not-committed shape the test's own name promises. Confirmed the test never calls svc.repair() and that assert not second_sync is true only because the retry starts from an untouched state, not because a genuinely torn state healed.
  - Not fixed in this review's scope -- tracked on BUG-779 together with F5 (one subject). WontFix here means homed elsewhere, not declined.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Reconciled-key table's stated justification is false

<!-- sq:finding:F7:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F7:head:end -->

<!-- sq:finding:F7:body -->
**read**, with the history checked.

`RoleDef._RECONCILED_EXTRA_KEYS`' comment justifies keeping `description` out of `extra_keys()`
(and so out of `PERMITTED_EXTRA_SKEW`) like this:

> ``description`` carries no such legacy corpus: before this table existed, nothing ever wrote
> ``extra.description``, so there is no lagging index to forgive …

That premise is false. `_services/_roster.py` has written `X.DESCRIPTION: role.description` at
role-create time since `5c74a73` — both in `activate_role` and in `add_dev`, and it is present in
`ea891a6` (the 0.13.0 release commit) at lines 56 and 87. Every role item in every existing squad
already carries `extra.description`.

The *conclusion* survives, for a different reason than the one given: create writes that key inside
its own transaction, so markdown and index have never disagreed on it, and no exemption is owed.
The corresponding test docstring in `tests/unit/test_role_def_extra_keys.py` states it correctly
("no legacy corpus that ever wrote `extra.description` **outside a transaction**") — it is the code
comment that overreaches.

Worth correcting rather than shrugging at, because the comment ends by offering a rule for the next
field: "A field belongs here, not in `_EXTRA_FIELD_KEYS`, exactly when adding it there would be a
pure widening of the guard's exemption with no legacy case to justify it." A reader applying the
stated test ("was it ever written before?") gets the wrong answer for `description` itself. The
rule that actually holds is "was it ever written to markdown *outside* a transaction", which is the
property `PERMITTED_EXTRA_SKEW` exists for.

Same commit, same table, a second small consequence: now that `to_extra()` carries `X.DESCRIPTION`,
the explicit `X.DESCRIPTION: role.description` in both create sites (`_roster.py:55` and `:86`) is a
redundant second declaration of the same mapping — the value is already in the dict being splatted.
Harmless today because the two agree; a change to the `_RECONCILED_EXTRA_KEYS` getter would
silently not apply at create. Deleting the two keys makes the table the single source it claims to
be.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-08-22T09:36:11Z] Mara Tester:
  - Confirmed against history: git show ea891a6:src/squads/_services/_roster.py already writes X.DESCRIPTION: role.description at both create sites (lines 56 and 87, unchanged today) -- predates the table whose comment claims no such legacy write ever happened. The conclusion (no exemption owed) still holds, for the reason the test docstring already states correctly (never written outside a transaction); only the code comment's premise is false. Also confirmed the explicit X.DESCRIPTION assignment at both create sites is now redundant with to_extra()'s own output.
  - Not fixed in this review's scope -- tracked on BUG-780 together with F8 (one subject: stale in-code justifications in this seam). WontFix here means homed elsewhere, not declined.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — resolved_spec contract misnames its callers in three places

<!-- sq:finding:F8:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F8:head:end -->

<!-- sq:finding:F8:body -->
**read**, with the no-consequence claim driven.

`open_service`'s new `resolved_spec` docstring says:

> The CLI's root callback … is the one caller that supplies it … Every other caller — direct test
> calls, ``sq ui``, the cross-check-bypassing fallback path — leaves this ``None``.

Two of the three named exceptions do supply it:

- **`sq ui`.** `_cli/_ui.py` calls `get_service()`. `sq ui` is not `command`-wrapped, so
  `_READ_SCOPE_META_KEY` is absent and `get_service` falls through to `_build_plain_service()` —
  which passes `resolved_spec=ctx.active_spec` like every other caller. `sq ui` opts out of the
  read scope and the `Service` memo, not out of this.
- **the bypass path.** `get_service_bypassing_index_cross_check` step 1 *is* `get_service()`, so it
  supplies it too. Only steps 2/3 (`_build_bypass_fallback_service`) construct a `Service`
  directly, and those never call `open_service` at all.

The same misattribution appears twice more, in
`tests/cli/test_workflow_cross_check_once_per_invocation.py`:
`test_open_service_direct_call_ignores_an_unrelated_ambient_spec` ("exactly what a test, `sq ui`,
or a second `IndexStore` … makes") and `test_resolved_spec_is_the_documented_opt_in_kwarg_default`
("every existing direct caller (tests, `sq ui`, the bypass fallback) is unaffected"). Both tests
themselves are sound — they exercise a genuine direct `open_service` call — it is only their stated
example that is wrong.

**No behavioural consequence today, driven.** `sq ui` builds exactly one `Service` at startup and
hands it to the TUI, which never rebuilds one (`grep open_service|get_service src/squads/_tui/` is
empty), so the cross-check runs once either way, microseconds apart. The bypass path still catches
the `SquadsError` `_build_plain_service` raises from the cached `spec_error`, which I drove: with a
re-prefixing override against a non-empty corpus, `sq list` exits 1 with the cross-check message
while `sq repair` exits 0 through its own guard.

Filed anyway, low, because the enumeration is the safety argument. "One caller supplies the
shortcut, everyone else validates independently" is what makes the memo defensible; if the real
answer is "every CLI caller supplies it, and only non-CLI callers validate independently", that is
a different and larger claim, and the docstring should be the one that says so.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-08-22T09:36:19Z] Mara Tester:
  - Traced the call graph directly: sq ui's root callback populates ctx.active_spec for every invocation; since sq ui never crosses command's async bridge, get_service() falls to _build_plain_service(), which unconditionally passes resolved_spec=ctx.active_spec -- non-None. So sq ui DOES supply resolved_spec, contradicting the docstring naming it as an exception; same for the bypass path's step 1 (a direct get_service() call). Confirmed no behavioural consequence (TUI never rebuilds a Service; grep for open_service/get_service under _tui/ is empty).
  - Not fixed in this review's scope -- tracked on BUG-780 together with F7 (one subject). WontFix here means homed elsewhere, not declined.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-21T20:56:43Z] Paul Reviewer:
  - Recommended verdict: ChangesRequested on F1 alone. sq init --name architect=Rob then sq sync silently renames the role back to Robert Architect in the frontmatter, the index, sq list, CLAUDE.md, AGENTS.md and the .claude pointer, with no warning and sq check clean. Driven on a fresh squad with no override files, and measured against the parent commit: extra.full_name and the generated roster already reverted before this commit, so what 03c0802 added is the loss of the last surviving copy (the item title). docs/overrides.md states the opposite guarantee in as many words.
  - Yes, one fix treated a symptom. BUG-756 reported the item disagreeing with itself; the projection resolves that disagreement by always letting the resolved catalog win. Right for the override input it was driven on, wrong for the --name input, where the item is the only record. The cause is that resolve_role has no dev_base_from_item equivalent for a non-dev role and never reads the [init.names] table sq init itself persists into .squads.toml. The dev-role half of the same function already does this correctly, so the fix is the shape that is already shipped.
  - On the class guard: worth keeping, and the AST literal-text framing is right - it excludes Table/Panel/bound-prose renders by construction, which is what makes an empty allowlist honest. Its predicate is what falls short: _receiver_name only accepts an ast.Name, so every common.console / common.err_console call is never even a candidate. Driven - the guard reports zero hits on a tree that has two, one of them the --at refusal the CHANGELOG now claims is fixed (F2, F3). The documented runtime-computed hole is narrower than feared: I scanned the package and found exactly one such site, the sq check issue line, which was fixed by hand.
  - What holds up, so it is not re-derived: the projection never moves the role file (path and slug are filename-derived, title is assigned directly, never through _rename); the no-op gate performs 0 index writes on a no-change sync; no path produces index-ahead-of-markdown, including the rollback; the cross-check runs exactly once per invocation (2 whole-index parses with an override, 1 without, including the custom-type dispatch path) and neither its refusal nor the repair/check bypass is lost; the blank-field check covers every string-bearing field with None kept distinct from empty, and _apply_override really is the only adopter-editable RoleSpec construction site; the raise-path test is a real falsifier.
  - @python-dev F1 first - it is data loss and it needs a driven test on the --name-then-sync sequence, which no test in the projection file exercises. F2 and F3 are one job: fix the guard predicate to accept an attribute receiver and the two sites it cannot see fall out. F4 is the same refusal applied at the two roster entry points. @tech-writer F2 also needs the 0.14.0 error-wrap entry narrowed again - it names --at as fixed and --at still reflows.
  - Process note for the coordinator, not a finding: this tree had uncommitted work by another agent while I reviewed (QA verification comments on BUG-755/756/758/760/761 plus an untracked BUG-769). I touched none of it; all my driving ran in throwaway squads under a scratch directory and a git worktree I removed afterwards.
- [2026-08-22T09:46:16Z] Catherine Manager:
  - Closing this review. All eight findings are dispositioned: F1, F2 and F3 fixed and driven; F4, F5, F6, F7 and F8 homed on BUG-778, BUG-779 and BUG-780, which op-pierre has now scheduled for fixing rather than deferring. F1 was the one that mattered - silent loss of an operator-set name that every gate passed - and the fix turned out to touch four sites plus a stale docstring rather than the two this review identified.
  - Recording my own process miss: I closed the findings as they landed but left the review item at ChangesRequested, and op-pierre had to ask. Same class as leaving BUG-755 in InProgress after verifying its fix. The item status is part of the disposition, not bookkeeping after it.
<!-- sq:discussion:end -->
