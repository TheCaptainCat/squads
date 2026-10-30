---
id: TASK-1245
sequence_id: 1245
type: task
title: Fix listing option validation and three messages
status: Done
author: tech-lead
refs:
- BUG-1193:fixes
- BUG-1194:fixes
- BUG-1195:fixes
- BUG-1196:fixes
- BUG-1197:fixes
- BUG-1200:fixes
- MILE-1241:targets
description: list/tree/reflog/graph refuse unknown values; clean unknown-option, memory
  search and import messages
subentities:
- local_id: ST1
  title: Print the unknown-option suggestion without a tuple repr
  status: Cancelled
- local_id: ST2
  title: Refuse an unknown --sort field on list and tree
  status: Done
- local_id: ST3
  title: Refuse an unknown badge code or value in list/tree filters
  status: Done
- local_id: ST4
  title: Refuse an unknown reflog --op
  status: Done
- local_id: ST5
  title: Refuse a negative --depth on tree and graph
  status: Done
- local_id: ST6
  title: Show a memory search hit once when body equals summary
  status: Done
- local_id: ST7
  title: Name an unknown import op in squads' own words
  status: Done
created_at: '2026-10-29T16:27:29Z'
updated_at: '2026-10-29T20:41:13Z'
priority: low
---
<!-- sq:body -->
## Goal

Listing and log options refuse a value they cannot apply instead of answering with an empty or unsorted result, and three error and output messages read cleanly. Seven bugs, one subtask each: `list`/`tree` `--sort` and badge filters (BUG-1193, BUG-1194), `reflog --op` (BUG-1195), `tree`/`graph --depth` (BUG-1196), the unknown-option suggestion (BUG-1192), `memory search` (BUG-1197) and the `import` unknown-op message (BUG-1200).

## Files

- `src/squads/_cli/_main.py`: `_badge_rank`, `_parse_badge_pairs`, `_build_badge_filters` (list and tree) and the `reflog` `--op` option.
- `src/squads/_cli/_common.py`: `depth_option` (tree and graph) and `parse_filter_badge_code`, reused for the badge validation.
- `src/squads/_index/_reflog.py`: `REFLOG_OPS`, read for the refusal (no change expected).
- `src/squads/_memory/_store.py`: `search`.
- `src/squads/_services/_import_model.py`: the validation-error message (around line 365).
- Tests: `tests/cli/test_list.py`, `tests/cli/test_tree.py`, `tests/cli/test_graph.py`, `tests/cli/test_reflog.py`, `tests/cli/test_memory.py`, `tests/cli/test_import.py`, `tests/cli/test_root_options.py`.

`src/squads/_cli/_main.py` also holds `init`/`adopt`, which the setup task deliberately leaves alone; this task owns the module.

## Tests

CLI surface tests per ADR-1172, one per behaviour, declared with `@pytest.mark.covers(...)`, observed through `sq` itself. Expected new tests: 7, one per bug; BUG-1200 updates `test_a_refused_line_leaves_the_valid_events_before_it_unapplied`, which pins the faulty message today. Falsify each by hand before handoff: revert the fix, watch the test go red, restore, watch it go green, and report both.

## Changelog

Every bug here except BUG-1192 changes adopter-visible behaviour (a refusal where there was exit 0, or a corrected message). Report each change and why in the handoff so the tech writer adds a line under the 0.19.0 section of `CHANGELOG.md`; do not edit `CHANGELOG.md` yourself.

## Gates

`uv run --all-extras pyright`, `uv run --all-extras ruff check .`, `uv run --all-extras ruff format --check .`, the test modules above plus `tests/meta` and `tests/cli` (the floor for a change under `_cli/`), and `sq check` clean for this task.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1245 add-subtask "<title>"`; track with `sq task 1245 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Print the unknown-option suggestion without a tuple repr

<!-- sq:subtask:ST1:body -->
Fixes BUG-1192.

**Expected.** An unknown-option error prints its suggestion as `No such option: --slug (Possible options: --as)`, with no tuple repr. The defect is in typer 0.26.7 (`NoSuchOption.format_message`); typer 0.27.3 formats it correctly, verified on the released tool. TASK-1243 moves the lock to typer 0.27.3, so squads needs no error hook of its own.

**Test.** In `tests/cli/test_root_options.py`: one case running a command with a misspelt option that has a suggestion, asserting the clean form and the absence of `('`. It passes only once the lock carries typer 0.27.3: land it after TASK-1243 merges, or rebase onto it. If TASK-1243 has not merged when the rest of this task is done, leave this subtask open and say so in the handoff.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-10-29T16:42:51Z] `manager` Catherine Manager:
  - Moved to TASK-1243 per op-pierre on BUG-1192 (2026-10-29).
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Refuse an unknown --sort field on list and tree

<!-- sq:subtask:ST2:body -->
Fixes BUG-1193.

**Expected.** `list --sort CODE` and `tree --sort CODE` refuse a code that is not a declared ordered badge field, exit 1, listing the valid codes, the same shape as `--priority ghost`. A valid code sorts as today.

**Test.** In `tests/cli/test_list.py` (`@pytest.mark.covers("list", "--sort")`): `--sort ghost` exits 1 naming the valid codes. The validation is shared with `tree`, so one case in `tests/cli/test_tree.py` (`@pytest.mark.covers("tree", "--sort")`) only if the coverage guard requires the pair.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Refuse an unknown badge code or value in list/tree filters

<!-- sq:subtask:ST3:body -->
Fixes BUG-1194.

**Expected.** `--badge CODE=VALUE` and `--min-badge CODE=VALUE` on `list` and `tree` validate CODE against the declared badge fields and VALUE against that field's collection, refusing either with the same message and exit code as `--priority ghost`. A valid pair filters as today.

**Test.** In `tests/cli/test_list.py` (`@pytest.mark.covers("list", "--badge")`, `("list", "--min-badge")`): one parametrised case over `priority=ghost`, `ghost=x` and `--min-badge priority=ghost` asserting exit 1 and the valid values in the message.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Refuse an unknown reflog --op

<!-- sq:subtask:ST4:body -->
Fixes BUG-1195.

**Expected.** `reflog --op NAME` refuses a name not in `REFLOG_OPS`, exit 1, listing the valid operations. A valid name filters as today, including when it matches no entry.

**Test.** In `tests/cli/test_reflog.py` (`@pytest.mark.covers("reflog", "--op")`): `--op ghost` exits 1 and names at least one valid operation.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Refuse a negative --depth on tree and graph

<!-- sq:subtask:ST5:body -->
Fixes BUG-1196.

**Expected.** `--depth` on `tree` and `graph` refuses a negative value (a `min=0` bound on `depth_option` in `_cli/_common.py`, so both commands get it). `--depth 0` still shows only the root.

**Test.** In `tests/cli/test_tree.py` (`@pytest.mark.covers("tree", "--depth")`): `--depth -1` is refused with a non-zero exit. One case in `tests/cli/test_graph.py` only if the coverage guard requires the pair.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Show a memory search hit once when body equals summary

<!-- sq:subtask:ST6:body -->
Fixes BUG-1197.

**Expected.** `memory <role> search` shows each matching line once: when a body line equals the summary, the repeat is dropped. A body line distinct from the summary still shows as a hit.

**Test.** In `tests/cli/test_memory.py` (`@pytest.mark.covers("memory search")`): add a memory whose body defaults to its summary, search for a word in it, assert the summary text appears exactly twice in the output (the slug line and one hit line).
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Name an unknown import op in squads' own words

<!-- sq:subtask:ST7:body -->
Fixes BUG-1200.

**Expected.** An import event with an unknown `op` is reported as `line N: unknown op 'nope'; valid ops: create, status, ...`, in squads' own words, with no leading `: `. Any other validation error with an empty location also drops the separator.

**Test.** Update `test_a_refused_line_leaves_the_valid_events_before_it_unapplied` in `tests/cli/test_import.py`, which pins the faulty line today, to assert the new message; it keeps its existing `covers` declaration. No new test.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T16:48:17Z] `python-dev` Elias Python:
  - Handback: commit 387eaf31 on branch worktree-agent-ad810b7e21b457c45. ST2-ST7 done, bugs 1193-1197 and 1200 Fixed, ST1 stays Cancelled. New tests fail without the fix. Side effect: min=0 on --depth changes the type-error wording to "not a valid integer range". @manager
- [2026-10-29T20:41:12Z] `manager` Catherine Manager:
  - Reviewed and verified in REV-1247 (Approved 2026-10-29); full suite green at a56413b4. Accepted Done under the operator delegation for this drive.
<!-- sq:discussion:end -->
