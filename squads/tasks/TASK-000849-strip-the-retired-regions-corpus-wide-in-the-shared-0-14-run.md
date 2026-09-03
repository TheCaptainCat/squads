---
id: TASK-849
sequence_id: 849
type: task
title: Strip the retired regions corpus-wide in the shared 0.14 runner
status: Ready
parent: FEAT-694
author: tech-lead
priority: high
refs:
- ADR-776:implements
- TASK-847:depends-on
- TASK-848:depends-on
- TASK-813
description: 'One more deterministic step inside the existing 0.11 to 0.14 runner:
  remove the summary and head marker regions and the role Skills block from every
  file already carrying them'
subentities:
- local_id: ST1
  title: Strip the summary and head marker regions corpus-wide
  status: Todo
  story: US4
- local_id: ST2
  title: Strip the role Skills block and skills frontmatter key
  status: Todo
  story: US4
- local_id: ST3
  title: Correct the runner docstring, registry summary and MANUAL
  status: Todo
  story: US4
- local_id: ST4
  title: Prove the step on the frozen corpus fixtures
  status: Todo
  story: US4
- local_id: ST5
  title: Strip this repository's own squad corpus
  status: Todo
  story: US4
created_at: '2026-09-01T08:04:14Z'
updated_at: '2026-09-01T08:08:50Z'
---
<!-- sq:body -->
## Scope

FEAT-694 US4: strip the retired regions from every file that already carries them, as one more
deterministic step inside the release's **existing** 0.11 → 0.14 runner.

## This authors no runner and no bump

`_migrations/_v0_11_to_v0_14.py` and its single registry entry (`version="0.14.0"`,
`from_schema="0.11"`, `to_schema="0.14"`) already ship, carrying the contract and milestone types
(verified in `_migrations/_registry.py`). TASK-813 is the release's one runner, and its own
acceptance says it cannot close on partial delivery: this feature is its third claimant and
**its acceptance grows to include this work rather than a second registry entry appearing**.

So: extend `migrate()` with one more step, extend the shared `MANUAL` with one more section,
widen the registry `summary` line. There is **no** second `from_schema`/`to_schema` pair, no
second runner module, no second `SCHEMA_VERSION` call, and no new corpus fixture (a fixture is
owed per *schema bump*, and this adds none — the standing rule in
`tests/fixtures/corpus/README.md` is already satisfied by `v0_14`).

This is tracked as its own task under FEAT-694, not as a subtask of TASK-813, because the work
maps to this feature's US4 and TASK-813 is parented to a different feature whose stories it
cannot map to. TASK-813 carries a `depends-on` edge to this task so the board shows it cannot
close first; the module it edits is TASK-813's, and that is a shared artifact, not shared
ownership.

## What the step removes

Corpus-wide, from every `.md` file under the squad directory:

1. the `sq:summary` marker region (open marker through close marker, and the blank line the
   region was inserted with);
2. every `sq:<kind>:<local-id>:head` marker region;
3. a role body's `## Skills` block;
4. the `skills` key from a role's frontmatter extra.

Everything else stays byte-for-byte: the authored `:body` and `:discussion` regions inside each
sub-entity block, the `### ST1 — title` headings, the container regions, the rest of each role
body, and every other frontmatter key.

Scale on this repository's own corpus, measured: 630 files carry a `sq:summary` region, 433 carry
at least one `:head`, 10 role files carry a `## Skills` block. Expect a large but wholly
mechanical diff.

## How to find the regions, without reading live vocabulary

The head tag embeds the sub-entity kind and local id, so an adopter-declared kind must be handled
too. **Match the marker tags by shape, not by enumerating declared kinds**: scan for
`<!-- sq:<tag>:head -->` / its close, and for the fixed `sq:summary` pair. A shape scan is
vocabulary-blind, works for a kind a project declared and later dropped, and keeps the runner
frozen against the live spec — which is the point of the discipline, not an incidental benefit.

`tests/meta/test_migrations_never_import_a_vocabulary_folded_primitive.py` forbids importing an
id/ref/padding **wire-encoding** primitive from `_models`. That guard's own docstring names what
stays importable, and the `_markers` section-tag constants are on that list explicitly. So
`markers.SUMMARY` and the marker open/close helpers are fine; do not import `_discussion`'s
private `_head_tag`, and do not read `spec.subentity_kinds` to build the tag set.

Removal must be **marker-safe**: cut from the open marker through the close marker using the
section machinery, never a line-range guess, and never a regex that could span from one region's
opener to a different region's closer. A block whose `:head` is absent, or a file whose summary
region is already gone, is a no-op — the step is idempotent and runs clean twice.

## The role `## Skills` block

This one is **not** a marker region — it is plain markdown inside the `sq:body` region (verified:
`role.md.j2` renders `## Skills` between `## Responsibilities` and `## Working agreements`). So it
comes out by heading boundary: from the `## Skills` line to the next `## `-level heading, scoped
**inside** the `sq:body` region only, so a `## Skills` heading someone wrote in the discussion is
never touched.

An adopter with an overridden `roles/role.md.j2` may have a differently-shaped block. Do not try
to be clever: remove the block when the heading is found at body level, and note in `MANUAL` that
a project with an overridden role template should run `sq sync`, which re-renders role bodies
from the template regardless. The frontmatter `skills` key is removed unconditionally.

## The docstring is now false and must be corrected

`_v0_11_to_v0_14.py`'s module docstring currently states "No existing item data is rewritten:
every write this runner performs is either creating a path that did not exist, or replacing a
body region this same runner is the first-ever author of." Once this step lands that is wrong in
both clauses. Rewrite the paragraph to say what the runner now does — a corpus-wide removal of
two retired marker regions and one role body block — rather than appending a contradicting
sentence beneath it.

The registry entry's `summary` line is what `sq migrate help` prints; it currently names only the
two new types and must name the region retirement too.

## Ordering inside a full replay

A squad replaying from 0.1 runs `_v0_1_to_v0_2` (which calls `ensure_summary`) and
`_v0_2_to_v0_3` (which calls `set_head`) before reaching this runner, so the regions get written
and then stripped inside the same `sq migrate up` invocation. That is wasteful and correct, and
the registry order already guarantees it. Do not "optimise" it by editing a frozen runner.

## Stripping this repository's own squad — the trap

**This repository's squad is already stamped schema 0.14** (verified:
`squads/.squads.json` reads `"schema_version": "0.14"`, and `.squads.toml` carries the same
stamp), because TASK-813's halves already landed. So `sq migrate up` here is a no-op and the new
step will never run on our own corpus through the ordinary path. A dev who does not know this
will report the migration "verified" against a corpus it never touched.

0.14 is unreleased, so the only squads at 0.14 are development ones — this repo and the frozen
`v0_14` fixture. Every real adopter is at 0.11 or below and gets the step normally.

For this repository, perform the strip as a deliberate, reviewable one-off: rewind the schema
stamp in `squads/.squads.toml` and `squads/.squads.json` to `"0.11"`, run `uv run sq migrate up`,
and commit the resulting corpus diff. Replaying the whole 0.11 → 0.14 runner is safe — its folder
creation, surface regeneration and skill seeding are all documented and verified idempotent, and
a squad already carrying that content sees no further writes at either step. Verify the diff
before committing: only region removals and role `skills:`/`## Skills` removals, nothing else.

Do this **after** the two sibling tasks have landed. If the live write path still calls
`ensure_summary`/`set_head`, the very next mutation re-materialises what the strip just removed.

## The `v0_14` fixture

Leave it frozen. It is a capture of a real squad at 0.14 and it will migrate to current as a
no-op, still carrying its regions, and still pass `sq check` — which is itself worth asserting,
because it is the same tolerance an un-migrated adopter file needs. The step is genuinely
exercised by the `v0_1` … `v0_11` fixtures, which all migrate forward through this runner. Add
the absence assertions there.

## Acceptance

- The region strip is one more deterministic step inside `_v0_11_to_v0_14.migrate()`, behind the
  existing single registry entry. No new runner module, no new `Migration` record, no
  `SCHEMA_VERSION` change, no new corpus fixture. `scripts/bump_version.py` was not run.
- Migrating each of the `v0_1` … `v0_11` corpus fixtures to current leaves **no** `sq:summary`
  region, **no** `:head` region, **no** role `## Skills` block and **no** role `skills`
  frontmatter key anywhere in the result — asserted per fixture, not spot-checked.
- The authored content is provably untouched: for at least one fixture, every `:body` and
  `:discussion` region's bytes, every sub-entity heading, every container region and every other
  frontmatter key are compared before and after and are identical.
- The step is idempotent: running the runner twice over the same corpus produces no second diff.
- A file that carries no summary region, and a block that carries no `:head`, are no-ops rather
  than errors.
- A head region belonging to an **adopter-declared** sub-entity kind is stripped too, proven with
  a fixture or a constructed corpus carrying one — the shape scan, not a declared-kind list.
- `sq check` and `sq repair` are clean on every migrated corpus, and the frozen `v0_14` fixture
  still migrates and checks clean while carrying its regions.
- `sq migrate help` lists one step whose summary names the region retirement alongside the two
  types; `sq migrate chlog` prints one manual entry covering all of it, including the `sq sync`
  note for a project with an overridden role template.
- The runner's module docstring no longer claims that no existing item data is rewritten.
- `tests/meta/test_migrations_never_import_a_vocabulary_folded_primitive.py` passes over the
  runner unchanged — no new carve-out.
- This repository's own squad carries no `sq:summary` region, no `:head` region and no role
  `## Skills` block or `skills:` frontmatter key, and `sq check` is clean on it.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite are clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 849 add-subtask "<title>"`; track with `sq task 849 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Strip the summary and head marker regions corpus-wide | US4 |
| ST2 | Todo |  | Strip the role Skills block and skills frontmatter key | US4 |
| ST3 | Todo |  | Correct the runner docstring, registry summary and MANUAL | US4 |
| ST4 | Todo |  | Prove the step on the frozen corpus fixtures | US4 |
| ST5 | Todo |  | Strip this repository's own squad corpus | US4 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Strip the summary and head marker regions corpus-wide

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US4 — Migrate the corpus to remove the retired regions
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Add one more deterministic step to `_migrations/_v0_11_to_v0_14.migrate()` that removes the two
retired marker regions from every `.md` file under the squad directory:

- the fixed `sq:summary` region;
- every `sq:<kind>:<local-id>:head` region.

**Find them by tag shape, not by declared vocabulary.** Scan for marker tags ending in `:head` and
for the fixed summary pair. A shape scan is vocabulary-blind, so it also strips a head belonging to
a sub-entity kind a project declared and later dropped, and it keeps the runner frozen against the
live spec — which is the discipline, not an incidental benefit. Do not import `_discussion`'s
private `_head_tag`, and do not read `spec.subentity_kinds` to build the tag set.

`tests/meta/test_migrations_never_import_a_vocabulary_folded_primitive.py` forbids importing an
id/ref/padding **wire-encoding** primitive from `_models`; its own docstring names the `_markers`
section-tag constants as explicitly importable, so `markers.SUMMARY` and the marker open/close
helpers are fine. No new carve-out is needed and none may be added.

Removal must be **marker-safe**: cut from a region's own open marker through its own close marker
using the section machinery, plus the blank line the region was inserted with. Never a line-range
guess, and never a regex that could run from one region's opener to a different region's closer.

Everything else stays byte-for-byte: the authored `:body` and `:discussion` regions inside each
sub-entity block, the `### ST1 — title` headings, the container regions, and every frontmatter key.

Idempotent: a file with no summary region, or a block with no `:head`, is a no-op; a second run
produces no diff.

Done when the step strips both region kinds across a corpus, leaves every other byte untouched
(proven by a before/after comparison of the authored regions on at least one fixture), is a no-op
on a second run, and the migration import guard passes over the runner unchanged.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Strip the role Skills block and skills frontmatter key

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US4 — Migrate the corpus to remove the retired regions
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
In the same step, strip the role-side residue from every role file:

1. the `## Skills` block from the role body;
2. the `skills` key from the role's frontmatter extra.

The Skills block is **not** a marker region — verified, `role.md.j2` renders `## Skills` as plain
markdown inside the `sq:body` region, between `## Responsibilities` and `## Working agreements`. So
it comes out by heading boundary: from the `## Skills` line to the next `## `-level heading (or the
end of the body region), scoped **inside `sq:body` only**, so a `## Skills` heading someone wrote
in a discussion comment is never touched.

An adopter with an overridden `roles/role.md.j2` may have a differently-shaped block. Do not try to
be clever about it: remove the block when the heading is found at body level, and let `MANUAL` note
that a project overriding the role template should run `sq sync`, which re-renders role bodies from
the template regardless. The frontmatter `skills` key is removed unconditionally — it is a
re-derivable cache, never hand-authored.

Measured on this repository's corpus: 10 role files carry the block.

Done when a migrated corpus has no role `## Skills` block and no role `skills` frontmatter key,
the rest of each role body is byte-identical, and the step is idempotent.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Correct the runner docstring, registry summary and MANUAL

<!-- sq:subtask:ST3:head -->
**Status:** ⚪ Todo
**Implements:** US4 — Migrate the corpus to remove the retired regions
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Update the runner's own prose and the registry entry it ships behind. No second entry, no second
bump.

- **The module docstring is now false.** `_v0_11_to_v0_14.py` currently states "No existing item
  data is rewritten: every write this runner performs is either creating a path that did not exist,
  or replacing a body region this same runner is the first-ever author of." Both clauses stop being
  true. Rewrite the paragraph to describe what the runner now does — a corpus-wide removal of two
  retired marker regions and one role body block, alongside the two types' folders and generated
  surface. Do not append a contradicting sentence beneath the old one.
- **The registry `summary` line** is what `sq migrate help` prints; it names only the two new types
  today and must name the region retirement too. Verified: `version="0.14.0"`,
  `from_schema="0.11"`, `to_schema="0.14"` — none of those change.
- **`MANUAL` gains one more section**, inside the same shared runbook string: the sub-entity
  roll-up table and badge line no longer live in the file (they are computed on every read), a
  role's skills list is now shown by `sq role <slug> show`, and a project that overrides
  `roles/role.md.j2` should run `sq sync` so its role bodies are re-rendered from the template.
  Nothing about ref encoding belongs here — that remains ruled out.

There is **no** new corpus fixture: a fixture is owed per schema bump and this adds none. The
standing rule in `tests/fixtures/corpus/README.md` is already satisfied by `v0_14`.

Done when `sq migrate help` lists one step naming both the two types and the region retirement,
`sq migrate chlog` prints one manual entry covering all of it, the docstring matches what the
runner does, and the registry still holds exactly one 0.14 record.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Prove the step on the frozen corpus fixtures

<!-- sq:subtask:ST4:head -->
**Status:** ⚪ Todo
**Implements:** US4 — Migrate the corpus to remove the retired regions
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
Prove the step on the frozen corpus fixtures.

The step is exercised by `v0_1` … `v0_11`, which all migrate forward through this runner. Assert per
fixture, after migrating to current:

- no `sq:summary` region anywhere;
- no `:head` region anywhere;
- no role `## Skills` block and no role `skills` frontmatter key;
- `sq check` and `sq repair` clean.

For at least one fixture, also compare the authored content before and after: every `:body` and
`:discussion` region's bytes, every sub-entity heading, every container region and every other
frontmatter key identical. That is the clause that actually proves "no authored content moves"; an
absence assertion alone does not.

Add a case with an **adopter-declared** sub-entity kind carrying a head region — constructed, since
no frozen fixture has one — to prove the shape scan rather than a declared-kind list.

**Leave `tests/fixtures/corpus/v0_14` frozen.** It is a capture of a real squad at 0.14; it
migrates to current as a no-op, still carries its regions, and must still pass `sq check`. Assert
that explicitly — it is the same tolerance an un-migrated adopter file needs, and it is why
`markers.SUMMARY` stays in `_validators`' structural tag set.

A full replay from 0.1 writes these regions via `_v0_1_to_v0_2` (`ensure_summary`) and
`_v0_2_to_v0_3` (`set_head`) and then strips them here, in the same `sq migrate up` invocation.
Wasteful and correct; the registry order guarantees it. Do not edit a frozen runner to avoid it.

Done when every fixture case asserts the four absences, one asserts authored-content identity, the
adopter-kind case passes, and the `v0_14` no-op case passes while still carrying its regions.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Strip this repository's own squad corpus

<!-- sq:subtask:ST5:head -->
**Status:** ⚪ Todo
**Implements:** US4 — Migrate the corpus to remove the retired regions
<!-- sq:subtask:ST5:head:end -->

<!-- sq:subtask:ST5:body -->
Strip this repository's own squad corpus. **This is the step a dev will otherwise skip while
reporting the migration verified.**

Verified: `squads/.squads.json` reads `"schema_version": "0.14"` and `.squads.toml` carries the
same stamp, because TASK-813's halves already landed. So `uv run sq migrate up` here is a **no-op**
and the new step never runs on our own corpus through the ordinary path. 0.14 is unreleased, so the
only squads at 0.14 are development ones; every real adopter is at 0.11 or below and gets the step
normally.

Do the strip as a deliberate, reviewable one-off:

1. Land the two sibling tasks first. If the live write path still calls `ensure_summary`/`set_head`,
   the next mutation re-materialises what the strip just removed.
2. Rewind the schema stamp in `squads/.squads.toml` and `squads/.squads.json` to `"0.11"`.
3. Run `uv run sq migrate up`. Replaying the whole 0.11 → 0.14 runner is safe — its folder
   creation, surface regeneration and skill seeding are documented and verified idempotent, and a
   squad already carrying that content sees no further writes at either step.
4. Read the diff before committing. Measured scale: 630 files carry a `sq:summary` region, 433
   carry at least one `:head`, 10 role files carry a `## Skills` block. The diff must contain
   **only** region removals plus role `skills:`/`## Skills` removals — nothing else. Any other
   change is a defect in the step, not something to accept because the tests pass.
5. Confirm `sq check` clean, `sq repair` clean, and the schema stamped back at `"0.14"`.

Stage the corpus diff narrowly (`squads/`) and separately from the source change, so the review can
read the mechanical diff apart from the logic.

Done when this repository's squad carries no `sq:summary` region, no `:head` region and no role
`## Skills` block or `skills:` frontmatter key, `sq check` is clean, and the diff was read rather
than assumed.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
