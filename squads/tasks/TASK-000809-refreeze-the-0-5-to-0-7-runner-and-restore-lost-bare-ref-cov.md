---
id: TASK-809
sequence_id: 809
type: task
title: Refreeze the 0.5-to-0.7 runner and restore lost bare-ref coverage
status: Done
parent: FEAT-790
author: tech-lead
assignee: python-dev
priority: urgent
refs:
- ADR-775:implements
- REV-808:addresses
- TASK-806
description: Give the 0.5-to-0.7 migration runner its own frozen ref handling, re-derive
  the migration import guard's rule, and restore the two coverage legs the structural
  change removed
subentities:
- local_id: ST1
  title: Freeze the 0.5-to-0.7 runner's own ref handling
  status: Done
  story: US1
- local_id: ST2
  title: Re-derive the migration import guard's rule
  status: Done
  story: US1
- local_id: ST3
  title: Repad fixture legs for spelled ref kinds
  status: Done
  story: US1
- local_id: ST4
  title: Restore the bare leg of width-tolerant ref severing
  status: Done
  story: US1
created_at: '2026-08-25T17:54:46Z'
updated_at: '2026-08-25T23:39:56Z'
---
<!-- sq:body -->
## Scope

ADR-775 amendment A1 and §2, on FEAT-790 US1. The second migration runner still borrows the
live ref primitives, so its on-disk output moved when `make_ref` became structural — the exact
invariant the first runner's refreeze established and declared closed. Plus the two coverage
legs that the same structural change quietly removed.

Four surfaces, one root cause: `make_ref` stopped collapsing the declared default kind to the
bare wire form. Everything that depended on that collapse moved, and nothing in the suite
noticed.

## 1. The runner's output moved retroactively

`_migrations/_v0_5_to_v0_7.py` imports `make_ref` and `split_ref` from `_models._item`
(lines 48-52, verified) and uses them in `_unpad_ref` (lines 117-128, verified):

```
rid, kind = split_ref(ref)
...
return make_ref(format_item_id(prefix, int(digits), DISPLAY_ID_PADDING), kind)
```

Both primitives changed meaning: the old `split_ref` resolved a bare ref to the default kind
and the old `make_ref` collapsed that kind back to bare; the current pair is structural. So the
same input yields different bytes at different squads versions:

| Input | Before the structural change | Now |
| --- | --- | --- |
| `TASK-000007:related` | `TASK-7` | `TASK-7:related` |
| `TASK-000007` | `TASK-7` | `TASK-7` |
| `TASK-000007:blocks` | `TASK-7:blocks` | `TASK-7:blocks` |
| `TASK-000007:` | `TASK-7` | `TASK-7` |
| `TASK-000007:scopes` | `TASK-7:scopes` | `TASK-7:scopes` |
| `not-an-id` | `not-an-id` | `not-an-id` |

The spelled-default row is the only one that moved, and it is the one that matters: two adopters
running the same 0.5-to-0.7 schema transform at different squads versions get different files,
and the newer one writes a spelled default kind onto disk — the encoding A1 forbids outright.
A squad that meets it lands in the false-skew state the review's F3 describes, which is the
architect's to settle separately; this task stops the runner producing it.

The remedy is the one the first runner already took: the runner carries its own frozen ref
handling, beside the frozen type table it already carries. Frozen means a private copy inside
the runner, not a shared helper the next refactor can move underneath it. The frozen default
kind for this schema version is `related`, the same literal the first runner froze.

## 2. The guard's rule is false as written, and re-deriving it is half the work

`tests/meta/test_migrations_never_import_a_vocabulary_folded_primitive.py` scans `_migrations/`
for imports of one name (`_VOCAB_FOLDED_PRIMITIVES`, line 26) and carries a test at line 84,
`test_the_scan_does_not_flag_the_purely_mechanical_ref_primitives`, pinning `split_ref` and
`make_ref` as permanently allowed. Its stated ground (lines 21-25) is that they are "structural
— no vocabulary of their own".

That ground is the property this change created. They were not structural before; becoming
structural is what moved this runner's bytes. So the guard exempts, by name and on a stated
rationale, the precise import that carries the defect it exists to prevent.

**Do not just add two names to the frozenset.** The rule has to be re-derived so its rationale
is true of whatever it permits. The property that actually matters is not "does this helper
resolve vocabulary" but "can the live tree change what this helper makes a frozen runner
write". Whatever rule is chosen must be stated in the module docstring in those terms and must
hold against every import a runner actually carries, not only the two the review named.

Two consequences follow, and both are in scope:

- **The first runner holds the same import.** `_migrations/_v0_1_to_v0_2.py:21` imports
  `make_ref` and `split_ref`, and its docstring at line 44 restates the same falsified
  rationale. Its output is byte-identical today (independently driven in the review), so this
  is not a live defect there — but it is the same import under the re-derived rule, and the
  rule cannot be true while one runner is exempted by hand. Freeze it and correct that
  docstring sentence.
- **The padding constant is the same class and nobody has looked at it.** The 0.5-to-0.7
  runner also imports `DISPLAY_ID_PADDING` and `format_item_id` from `_models._item`, and
  `DISPLAY_ID_PADDING` is a live module constant (`_models/_item.py:34`, currently `0`) whose
  value *is* the runner's output width. A change to display padding moves this frozen runner's
  bytes exactly the way `make_ref` just did. Judge it under the re-derived rule and freeze what
  the rule says to freeze; do not leave it unexamined because the review did not name it.

## 3. No fixture anywhere feeds a repad path a spelled default kind

`tests/integration/test_unpadded_id_migration.py` exercises `refs` with bare ids only — its
`_devolve_to_padded` helper pads `refs` entries through `_pad`, which does
`int(digits)` on the id's trailing digit run and would raise on a `PREFIX-000007:related`
entry. So the helper cannot express the case even if a test wanted it, and no fixture in the
tree ever hands this runner a spelled ref. That is why both runners slipped through.

Make `_pad` ref-aware and add the spelled-default and spelled-non-default legs alongside the
bare one, so the integration path covers what the unit assertion covers.

## 4. Width-tolerant ref severing lost its bare leg

`tests/service/test_remove.py:93` (verified) plants its plated ref as
`make_ref(old_width_id, "blocks")`, commented "non-default: stays spelled on disk". It used to
plant `make_ref(old_width_id, "related")`, which collapsed to a **bare** old-width ref. The
fixture had to change — with the default kind it now plants a spelled default on both sides,
which the fold correctly treats as skewed — but swapping the leg rather than adding one dropped
the bare form from coverage, and the bare form is the on-disk shape of the majority of edges.

The severing predicate is kind-agnostic (`ref_id_matches(split_ref(r)[0], …)`,
`_services/_items.py:652-656`), so this is a coverage regression rather than a live bug. The fix
is the one the skew-guard test in the same commit already applies: parametrize over both legs.
Keep the `blocks` leg; get the bare leg back.

## Traps

- **A behavioural test on a loaded model cannot distinguish the two encodings.** The runner's
  output has to be asserted on the bytes it writes.
- **The re-derived rule must not swallow the frozen literals a runner is entitled to.** A
  migration reads the vocabulary of the schema version it transforms; the frozen `_TYPES` table
  and a frozen default-kind literal are correct and must stay. The rule is about reaching into
  the live tree, not about naming a kind.
- **This does not collide with the ref-kind literal scan.** That scan excludes `_migrations/`
  by construction, for the reason above; this guard covers the axis that exclusion leaves open.
  They are complementary and must both keep passing — do not merge them.
- **No schema bump and no new runner.** Freezing a runner's own helpers changes no schema.
- **No bundled template is touched**, so no manifest regeneration, and
  `scripts/bump_version.py` must not be run.

## Acceptance

- `_migrations/_v0_5_to_v0_7.py` imports no ref-encoding primitive from `_models` and carries
  its own frozen handling; the same holds for `_migrations/_v0_1_to_v0_2.py`.
- `_unpad_ref`'s output is asserted **on bytes** for every input row in the table above, and
  the spelled-default row collapses to bare.
- Byte equality is asserted against what the runner produced before `make_ref` became
  structural — the pre-change collapse behaviour, encoded as expected values in the test rather
  than as a reference to a commit.
- The meta guard's rule is restated so its rationale is true of everything it permits, the
  module docstring says what the rule is and why, and the test asserting `split_ref`/`make_ref`
  are permanently allowed is gone or replaced by one that matches the new rule.
- The guard fails on a planted runner that reaches into `_models` for a primitive the new rule
  forbids, and passes on a runner carrying its own frozen copies.
- `DISPLAY_ID_PADDING` and `format_item_id` are judged under the re-derived rule, with the
  outcome stated in the guard's docstring either way.
- `tests/integration/test_unpadded_id_migration.py` carries a repad leg whose `refs` hold a
  spelled default-kind ref and a spelled non-default ref, and its `_pad` helper handles a
  `ID:kind` entry without raising.
- `tests/service/test_remove.py`'s width-tolerant severing test is parametrized over a bare
  ref and a spelled non-default ref, both severed.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite are clean; `sq check` is clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 809 add-subtask "<title>"`; track with `sq task 809 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Freeze the 0.5-to-0.7 runner's own ref handling

<!-- sq:subtask:ST1:body -->
Give `_migrations/_v0_5_to_v0_7.py` its own frozen ref handling, beside the frozen `_TYPES`
table it already carries, and assert its output on bytes.

Today it imports `make_ref` and `split_ref` from `_models._item` (lines 48-52) and calls them in
`_unpad_ref` (lines 117-128). Both changed meaning when `make_ref` became structural: the old
pair collapsed a default-kind ref back to the bare wire form, the current pair spells it. So the
runner's on-disk output moved retroactively — `TASK-000007:related` unpadded to `TASK-7` before
and unpads to `TASK-7:related` now.

The frozen default kind for this schema version is `related`, the same literal the 0.1-to-0.2
runner froze. Frozen means a private copy inside the runner, not a shared helper the next
refactor can move underneath it, and never re-derived from the active spec: a migration is a
point-in-time snapshot of the schema version it transforms, and an adopter is free to rename
their default kind.

Assert on **bytes**, one row per input, with the expected values written out in the test:

| Input | Expected |
| --- | --- |
| `TASK-000007:related` | `TASK-7` |
| `TASK-000007` | `TASK-7` |
| `TASK-000007:blocks` | `TASK-7:blocks` |
| `TASK-000007:` | `TASK-7` |
| `TASK-000007:scopes` | `TASK-7:scopes` |
| `not-an-id` | `not-an-id` |

Only the first row moved; it is the row that matters. A behavioural assertion on a loaded model
would not distinguish the two encodings — the point is what reaches the file.

Encode the expected values in the test rather than pointing at a commit that produced them.

Done when the runner imports no ref-encoding primitive from `_models`, every row above is
asserted on bytes, and the spelled-default row collapses to bare.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Re-derive the migration import guard's rule

<!-- sq:subtask:ST2:body -->
Re-derive the rule `tests/meta/test_migrations_never_import_a_vocabulary_folded_primitive.py`
enforces, so its rationale is true of everything it permits.

As written, the scan looks for one name (`_VOCAB_FOLDED_PRIMITIVES`, line 26) and
`test_the_scan_does_not_flag_the_purely_mechanical_ref_primitives` (line 84) pins `split_ref`
and `make_ref` as permanently allowed, on the stated ground (lines 21-25) that they are
"structural — no vocabulary of their own". Their being structural is exactly the change that
moved a frozen runner's bytes, so the guard exempts by name, and on a written rationale, the
import that carries the defect it was created to prevent recurring.

**Adding two names to the frozenset is not the fix.** The property that matters is not "does
this helper resolve vocabulary" but "can the live tree change what this helper makes a frozen
runner write". State the chosen rule in the module docstring in those terms, and make it hold
against every import a runner actually carries.

Two things the re-derived rule has to answer, rather than leave to the next reader:

- **The 0.1-to-0.2 runner holds the same import.** `_migrations/_v0_1_to_v0_2.py:21` imports
  `make_ref` and `split_ref`, and its docstring at line 44 restates the same falsified ground.
  Its output is byte-identical today, so it is not a live defect there — but it is the same
  import, and the rule cannot be true while one runner is exempted by hand. Freeze it and
  correct that docstring sentence.
- **`DISPLAY_ID_PADDING` is the same class.** The 0.5-to-0.7 runner imports it and
  `format_item_id` from `_models._item`; `DISPLAY_ID_PADDING` is a live module constant
  (`_models/_item.py:34`, currently `0`) and its value *is* the width the runner writes. A
  change to display padding moves that runner's bytes the way `make_ref` just did. Judge it
  under the rule and record the outcome in the docstring either way — freezing it, or saying
  plainly why the rule does not reach it.

Keep what a runner is entitled to: a migration reads the vocabulary of the schema version it
transforms, so a frozen type table and a frozen default-kind literal are correct. The rule is
about reaching into the live tree, not about naming a kind.

This guard does not merge with the bundled ref-kind literal scan, which excludes `_migrations/`
by construction for that same reason. The two cover complementary axes; both keep passing.

Done when the rule is restated with a rationale true of what it permits, the guard fails on a
planted runner reaching into `_models` for a forbidden primitive, passes on runners carrying
their own frozen copies, and no test asserts the retired exemption.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Repad fixture legs for spelled ref kinds

<!-- sq:subtask:ST3:body -->
No fixture in the tree ever feeds a repad path a spelled default-kind ref, which is why both
runners' output could move unnoticed.

`tests/integration/test_unpadded_id_migration.py` exercises `refs` with bare ids only. Its
`_devolve_to_padded` helper rewrites `fm["refs"] = [_pad(r) for r in refs]`, and `_pad` does
`int(digits)` on the id's trailing digit run — so a `PREFIX-000007:related` entry raises rather
than migrating. The helper cannot express the case even if a test wanted it.

Make `_pad` ref-aware (split the entry into id and kind, pad the id, reassemble), then add the
missing legs to the migration fixture: a `refs` entry carrying a spelled default kind, and one
carrying a spelled non-default kind, alongside the existing bare one.

This is the end-to-end complement to the byte assertion on the runner's helper: the unit
assertion proves the helper, this proves the file the runner actually writes.

Done when the migration fixture carries bare, spelled-default and spelled-non-default `refs`
legs, the default leg lands bare on disk, the non-default leg stays spelled, and `_pad` handles
an `ID:kind` entry without raising.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Restore the bare leg of width-tolerant ref severing

<!-- sq:subtask:ST4:body -->
Restore the bare-ref leg to the width-tolerant severing test.

`tests/service/test_remove.py:93` plants its ref as `make_ref(old_width_id, "blocks")`,
commented "non-default: stays spelled on disk". It previously planted
`make_ref(old_width_id, "related")`, which collapsed to a **bare** old-width ref, so the test
covered severing a bare ref at a narrower width. After the swap it covers only the spelled form.

The fixture genuinely had to change: with the default kind it now plants a spelled default
consistently on index and disk, which the fold correctly treats as skewed. Swapping the leg was
a reasonable way to unblock; keeping only one leg was not. The default kind is always written
bare, so the bare form is the on-disk shape of the majority of edges in any corpus, and that is
the leg no longer covered.

The severing predicate is kind-agnostic (`ref_id_matches(split_ref(r)[0], …)`,
`_services/_items.py:652-656`), so this is a coverage regression rather than a live bug.

Parametrize over both legs rather than swapping one for the other — the same treatment the
skew-guard test in the same change already received. Keep the `blocks` leg.

Done when the test runs over a bare old-width ref and a spelled non-default old-width ref, and
both are found and severed.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-25T18:00:44Z] Olivia Lead:
  - Authored from REV-808 F1, and I verified every cited line before writing rather than folding off the report: the live make_ref/split_ref imports at _v0_5_to_v0_7.py:48-52 and their use in _unpad_ref:117-128; the guard allowlisting those two names at tests/meta/test_migrations_never_import_a_vocabulary_folded_primitive.py:26 with the falsified rationale at :21-25 and the pinning test at :84; test_remove.py:93 planting the blocks ref; and the repad helper in tests/integration/test_unpadded_id_migration.py, whose _pad does int(digits) and so cannot even express a spelled ref.
  - Two things the review did not name, found while verifying, both in scope. The 0.1-to-0.2 runner holds the SAME live import at _v0_1_to_v0_2.py:21 with the same falsified rationale in its docstring at :44 - its bytes are unchanged today, but a re-derived rule cannot be true while one runner is exempted by hand. And that runner also imports DISPLAY_ID_PADDING, a live module constant (_models/_item.py:34) whose value IS the width it writes - a display-padding change moves its bytes exactly the way make_ref just did. ST2 makes the rule answer both.
  - Sequencing: this goes FIRST among the open FEAT-790 tasks, ahead of TASK-797 and TASK-807. It is the only one where an adopter running sq migrate up today gets a forbidden encoding written to their corpus; the others are capability work. It depends on neither: the runner must not consult the live spec at all, so the exactly-one-default floor is irrelevant to it. File isolation is clean - it touches _migrations/ plus three test files, while 797 is in _services/_workflow and 807 is in _services/_refs.py - so it can run in parallel with either.
  - Deliberately NOT a depends-on to TASK-806: the guard and the first runner refreeze it builds on are already in the tree at 958974c, so this is not waiting on that item closing. Recorded as related instead, to keep sq blocked honest.
- [2026-08-25T20:09:24Z] Elias Python:
  - Both runners refrozen: _v0_5_to_v0_7.py and _v0_1_to_v0_2.py no longer import make_ref/split_ref/format_item_id/DISPLAY_ID_PADDING from _models -- each carries private _split_ref/_make_ref (+_format_item_id/_DISPLAY_ID_PADDING for the 0.5-0.7 runner) frozen to the pre-structural collapse behaviour.
  - Byte-verified _unpad_ref against a worktree at be080c7 (958974c^) for all 6 table rows -- identical output; TASK-000007:related collapses to TASK-7 as before.
  - Guard rule re-derived (tests/meta/test_migrations_never_import_a_vocabulary_folded_primitive.py): flipped from 'exempt split_ref/make_ref by name because they look structural' to a category ban -- any wire-encoding primitive (format/parse/default an id or ref literal) is forbidden regardless of current implementation shape, constants included. _WIRE_ENCODING_PRIMITIVES now covers fold_legacy_kinds, make_ref, split_ref, format_item_id, DISPLAY_ID_PADDING, DEFAULT_ID_PADDING. Model/schema definitions (Item, SubEntity, _markers) stay importable -- new test proves it.
  - DISPLAY_ID_PADDING and format_item_id: both judged in scope and frozen locally in _v0_5_to_v0_7 -- 'purely mechanical today' was exactly make_ref's failed defense, so neither gets a pass on that basis.
  - ST3: _pad in test_unpadded_id_migration.py is now ref-aware (splits kind, pads id, reassembles); added an end-to-end repad test with a spelled-default and spelled-non-default ref leg.
  - ST4: test_remove.py's width-tolerant severing test is parametrized over bare and spelled-non-default legs (both severed) instead of the one-for-one swap.
  - Targeted: tests/meta (14 passed incl. 5 in the re-derived guard file), tests/integration/test_migrations.py + test_unpadded_id_migration.py, tests/service/test_remove.py, tests/unit/test_legacy_ref_kinds_folding.py + test_migration_registry.py, tests/service/test_v0_3_migration_chain_reaches_current_schema.py: 208 passed. 15 unrelated failures in tests/meta/test_generated_agent_text_names_no_bundled_vocabulary.py and test_source_and_new_test_tree_have_no_stray_ticket_references.py trace to _workflow/_models.py and _services/_refs.py -- TASK-797's in-flight files, untouched by me.
  - pyright/ruff/ruff format clean on every file I touched (0 errors there); the 18 pyright errors + 3 ruff findings in the full run are all in _services/_refs.py, _services/_retirement.py, _workflow/_models.py -- TASK-797's territory. sq check clean.
<!-- sq:discussion:end -->
