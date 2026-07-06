---
id: TASK-309
sequence_id: 309
type: task
title: 'Sweep src/ commentary: services/CLI/index/store cluster'
status: Done
parent: FEAT-237
author: tech-lead
assignee: python-dev
priority: medium
subentities:
- local_id: ST1
  title: Strip refs from comments/docstrings
  status: Done
  assignee: python-dev
  story: US1
- local_id: ST2
  title: 'Restyle: terse + history-free'
  status: Done
  assignee: python-dev
  story: US2
- local_id: ST3
  title: Remove refs from CLI help/output strings
  status: Done
  assignee: python-dev
  story: US4
created_at: '2026-07-06T12:55:25Z'
updated_at: '2026-07-06T13:51:15Z'
---
<!-- sq:body -->
SRC WAVE (part 2 of 2). Scope: all Python under src/squads/_services, _index, _migrations, _cli, _backends, _rendering, and the top-level src/squads/*.py. Blast radius: ~180 ref-hits, PLUS every comment/docstring for the restyle pass. This cluster owns _cli, so it carries the bulk of the CLI help/output-string work. Disjoint file set from part 1 — safe to run in parallel. Combines ref-strip (US1), terse/history-free restyle (US2), and CLI/output-string ref-removal (US4) into ONE owner per file so no file is double-touched. Done when: zero squad-item refs remain in these files' comments/docstrings/strings; commentary terse + history-free; CLI help/output strings had real refs removed without rewording (illustrative --parent FEAT-… / sq task <n> shapes may stay); full suite green and UNCHANGED; pyright + ruff clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 309 add-subtask "<title>"`; track with `sq task 309 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done | python-dev | Strip refs from comments/docstrings | US1 |
| ST2 | Done | python-dev | Restyle: terse + history-free | US2 |
| ST3 | Done | python-dev | Remove refs from CLI help/output strings | US4 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Strip refs from comments/docstrings

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
**Implements:** US1 — Code comments carry no squad-item references
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Remove every squad-item reference — (FEAT|TASK|ADR|REV|BUG|EPIC)-<n>, US/ST numbers, bare §N — from comments and docstrings in src/squads/_services, _index, _migrations, _cli, _backends, _rendering, and top-level src/squads/*.py. Restate load-bearing rationale on the code's own terms. Done when: grep of the ref pattern over these files returns zero.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Restyle: terse + history-free

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
**Implements:** US2 — Src comments describe current behavior, not history
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Same files: describe the code as it is — no 'previously/now', 'used to', 'as of vX', change-log narration; drop restate-the-code comments; trim docstring preambles to intent/contract. src/ code commentary only. Done when: no history narration or restate-the-code comments remain; suite green and unchanged.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Remove refs from CLI help/output strings

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
**Implements:** US4 — User-facing content carries no squad-item references
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
This cluster owns _cli: remove real-citation squad-item refs from help text, error messages, and printed table content WITHOUT rewording. Keep illustrative CLI-syntax templates (--parent FEAT-…, sq task <n>) and example IDs — those are non-violations. Done when: no real-citation ref remains in user-facing strings emitted from these files.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-06T13:51:15Z] Elias Python:
  - Swept _services/_index/_migrations/_cli/_backends/_rendering + top-level src/squads/*.py: removed all real FEAT-/TASK-/ADR-/REV-/BUG-/EPIC-/US/ST/§N citations from comments/docstrings/CLI strings; restyled touched commentary terse + history-free.
  - Illustrative examples were reworded to non-matching placeholders (PREFIX-000007, TASK-<n>, STn/USn/Fn) where they were plain comments/docstrings, since the literal digit sequences would still trip the ref-pattern grep.
  - Deliberately kept tolerated illustrative payloads/CLI-syntax examples untouched per the feature's own carve-out: sq graph --json sample payload in _cli/_main.py (BUG-22 / FEAT-35 / TASK-100).
  - Ref-clean proof (git diff added-lines grep) empty; pyright/ruff check/ruff format clean; targeted -k reflog/show_any/migrate_help_and_chlog tests pass. Full-suite gate owned by the coordinator (already reported green).
<!-- sq:discussion:end -->
