---
id: TASK-45
sequence_id: 45
type: task
title: Clear pre-existing lint/format debt on the release branch (F401 + format drift)
status: Done
author: tech-lead
assignee: tech-lead
priority: low
created_at: '2026-06-11T12:49:16Z'
updated_at: '2026-06-11T12:50:45Z'
---
<!-- sq:body -->
Pre-existing branch debt, unrelated to TASK-42/43/44 (those files are unmodified in git status). CLAUDE.md requires clean lint/format gates.

Scope (surgical):
- 12 ruff F401 unused-import errors: 11 in src/squads/_services/_items.py, 1 in src/squads/_cli/__init__.py (ItemType). Same 12 also reported by pyright as reportUnusedImport — they are the SAME underlying unused imports, not separate issues (resolves the manager's 'conflicting pyright reports' confusion: 0 errors on the TASK-42/43/44 changed files; 12 pre-existing on these two untouched files).
- format drift in src/squads/_discussion.py (ruff format would reformat).

Fix: ruff check --fix on the F401s + ruff format src/squads/_discussion.py, then re-run full gates.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 45 add-subtask "<title>"`; track with `sq task 45 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-11T12:50:45Z] Olivia Lead:
  - Done. Pre-existing branch debt cleared surgically: ruff --fix removed 11 unused imports from _services/_items.py + manually removed the unused ItemType import from _cli/__init__.py (WORK_TYPES on the same line is used, kept); ruff format reformatted _discussion.py. All four gates now clean: pytest green, pyright 0 errors, ruff check passes, ruff format clean. None of TASK-42/43/44's files were touched.
<!-- sq:discussion:end -->
