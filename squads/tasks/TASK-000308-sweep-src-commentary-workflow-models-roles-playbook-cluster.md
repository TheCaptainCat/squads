---
id: TASK-308
sequence_id: 308
type: task
title: 'Sweep src/ commentary: workflow/models/roles/playbook cluster'
status: Done
parent: FEAT-237
author: tech-lead
assignee: python-dev
priority: medium
subentities:
- local_id: ST1
  title: Strip refs from comments/docstrings
  status: Done
  story: US1
- local_id: ST2
  title: 'Restyle: terse + history-free'
  status: Done
  story: US2
- local_id: ST3
  title: Remove refs from any user-facing strings here
  status: Done
  story: US4
created_at: '2026-07-06T12:55:24Z'
updated_at: '2026-07-06T13:21:30Z'
---
<!-- sq:body -->
SRC WAVE (part 1 of 2). Scope: all Python under src/squads/_workflow, _interactions, _roles, _models. Blast radius: ~161 ref-hits across these subpackages, PLUS every comment/docstring in them for the restyle pass (the restyle touches more than just ref-bearing lines). Disjoint file set from the part-2 task, so the two can run in parallel with no collision. Combines ref-strip (US1), terse/history-free restyle (US2), and CLI/output-string ref-removal for strings emitted from these files (US4) into ONE owner per file. Done when: zero squad-item refs remain in these files' comments/docstrings/strings; commentary is terse and history-free; any user-facing strings had real refs removed without rewording; full test suite passes UNCHANGED and green; pyright + ruff clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 308 add-subtask "<title>"`; track with `sq task 308 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Strip refs from comments/docstrings | US1 |
| ST2 | Done |  | Restyle: terse + history-free | US2 |
| ST3 | Done |  | Remove refs from any user-facing strings here | US4 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Strip refs from comments/docstrings

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — Code comments carry no squad-item references
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Removed every squad-item reference (FEAT/TASK/ADR/REV/BUG/EPIC, US/ST numbers, bare §N) from comments and docstrings in src/squads/_workflow, _interactions, _roles, _models. Load-bearing refs were restated on the code's own terms (e.g. section-number checks became plain descriptions); illustrative TASK-0000NN example IDs were reworded to PREFIX-000NN placeholders since they're not real citations. Verified via grep: zero hits across the .py files in scope.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Restyle: terse + history-free

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — Src comments describe current behavior, not history
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Restyled the same files' commentary to be terse and history-free: dropped 'F1/F2/F3' wave labels, 'formerly in __init__.py', 'AC#5', schema-version narration, and other archaeology; comments now describe current behavior/contract only. Full suite green and unchanged.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Remove refs from any user-facing strings here

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US4 — User-facing content carries no squad-item references
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Checked help/error/console strings emitted from these files for real-citation squad-item refs; none were present needing removal beyond the doc/comment sweep in ST1. The one CLI-syntax example in playbook.toml (--story US1) is a legitimate illustrative shape per the FEAT-237 carve-out and was left as-is (playbook.toml itself is TASK-310's file, not TASK-308's).
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-06T13:21:30Z] Elias Python:
  - Swept src/squads/_workflow, _interactions, _roles, _models: zero squad-item refs remain in comments/docstrings (verified by grep, including the exact final-verify pattern against the diff); commentary restyled terse/history-free; no real-citation refs found in user-facing strings from these files.
  - pyright + ruff check + ruff format --check all clean.
  - Full suite: 1641 passed, 1 skipped, 0 failed/errored (exit 0).
<!-- sq:discussion:end -->
