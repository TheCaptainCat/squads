---
id: TASK-1116
sequence_id: 1116
type: task
title: Close the rebuild and measure per-OS CI against the targets
status: Cancelled
parent: FEAT-1096
author: tech-lead
assignee: devops
priority: high
refs:
- TASK-1113:depends-on
- TASK-1114:depends-on
- TASK-1115:depends-on
description: Old root retired, new root renamed to tests/, ledger complete, one CI
  run per OS against the targets.
subentities:
- local_id: ST1
  title: Retire the rest of the old root and rename the new one to tests/
  status: Todo
  story: US9
- local_id: ST2
  title: Record one CI run per OS against the binding targets
  status: Todo
  story: US10
- local_id: ST3
  title: Delete the per-kind sub-entity service wrappers
  status: Todo
  story: US9
created_at: '2026-10-24T13:42:20Z'
updated_at: '2026-10-27T20:16:27Z'
---
<!-- sq:body -->
Close the rebuild: retire what is left of the old root, rename the new one, finish the parity record (US9), and measure CI per OS against the binding targets (US10).

**Binding targets** (op-pierre, 2026-10-24): every CI test job under 10 minutes; Windows up to 15. Pytest step on the 0.16 suite: Windows 53 min, macOS 14, Ubuntu 8 on the 2026-10-17 push to `main` (run 39020459902); Windows 39 to 59 min, macOS 11 to 13, Ubuntu 15 to 16 on the two 2026-10-24 pull-request runs (40116628420, 40116638095). The inventory task records the baseline on the suite as it stands when the rebuild starts, and that baseline is the one compared here.

**What is left in the old root after the three areas.** Files that cover entries in more than one area, the shared helpers (`_helpers.py`, `_roster_squad.py`, `_gate_layouts.py` and the others at the root), `tests/conftest.py`, `tests/CONVENTIONS.md`, and any golden or fixture no area ported. Each remaining test file's entries are proven red in the new root before it is deleted, as in the area tasks.

**Acceptance**

- No file remains under the old root; `tests_next/` is renamed to `tests/` and is the only `testpaths` entry; every path that names either root is updated: `pyproject.toml` (pytest, pyright `include` and execution environment, ruff per-file ignores, markers), the CI workflows, `CLAUDE.md`, `CONTRIBUTING.md`, and the conventions document and ledger themselves.
- `uv run --all-extras pytest`, pyright, ruff and `sq check` are clean.
- The ledger shows every entry with an owner and a recorded red, or a recorded gap in the old suite.
- At least two CI runs per OS after the rename are recorded in a comment: per run, wall time, worker count, test count and run link, compared to the targets and to the inventory baseline. A target is met on an OS only when every one of those runs is under it. There is no test-count ceiling; CI time is the bound. Every job is under 10 minutes and Windows at most 15; a miss is reported with its `--durations` profile and is not closed as met.
- Windows runs the full suite, as macOS and Ubuntu do; no subset or new marker split buys it its time (the `slow` scale tests stay skipped by default on every OS, as today).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1116 add-subtask "<title>"`; track with `sq task 1116 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Retire the rest of the old root and rename the new one to tests/

<!-- sq:subtask:ST1:body -->
Prove the entries of every test file still under the old root red in the new root, then delete the rest of the old root (cross-area files, root helpers, `conftest.py`, `CONVENTIONS.md`, unported goldens and fixtures). Rename `tests_next/` to `tests/` with `git mv`, make it the only `testpaths` entry, and update every path that names either root: `pyproject.toml`, the CI workflows, `CLAUDE.md`, `CONTRIBUTING.md`, the conventions document and the ledger. Check the ledger has an owner and a recorded red (or a recorded gap) for every entry.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Record one CI run per OS against the binding targets

<!-- sq:subtask:ST2:body -->
Run the full suite in the CI test job at least twice per OS, Windows included, after the rename and record per run wall time, worker count, test count and the run link against the binding targets and the inventory baseline. A target is met on an OS only when every one of those runs is under it; one run alone does not settle it. Report any miss with its `--durations` profile.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Delete the per-kind sub-entity service wrappers

<!-- sq:subtask:ST3:body -->
Once the last old test file is deleted, remove the per-kind sub-entity wrappers on `SubentitiesMixin` (`add_story`, `add_subtask`, `add_finding`, `list_stories`, `set_subtask_status`, `update_finding` and the rest, in `src/squads/_services/_subentities.py`) that only the old suite called, and their entries in `pyproject.toml`'s vulture `ignore_names`. Check first that nothing in `src/` or the new root calls them. New tests use the generic block surface. This closes the remainder of REV-956 F7.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T19:48:48Z] `tech-lead` Olivia Lead:
  - Re-read for Ready on 2026-10-24: ST1 now deletes what the areas leave behind (cross-area files, helpers, conftest) and updates every path naming either root. Dropped the unruled local-run proposals (60 s full, 30 s default, 12 min Windows design target): the CI targets are the only bound. Moved to Ready.
- [2026-10-24T21:56:21Z] `tech-lead` Olivia Lead:
  - Added ST3: delete the per-kind sub-entity service wrappers once the old suite is gone, carrying the rest of REV-956 F7 from FEAT-1092.
<!-- sq:discussion:end -->
