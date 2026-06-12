---
id: TASK-000068
sequence_id: 68
type: task
title: 'Per-role working-agreement lines: reviewer files findings as sub-entities'
status: Done
author: manager
assignee: python-dev
priority: medium
refs:
- REV-000067:addresses
created_at: '2026-06-12T13:31:43Z'
updated_at: '2026-06-12T13:37:48Z'
---
<!-- sq:body -->
**Why.** REV-000067 retro: the reviewer wrote findings as body prose because nothing in the text he reliably re-reads (his role file) says findings are sub-entities; the sq-review skill says it but skills are loaded on demand. Operator picked the behavioral remedy: put one line in the reviewer's working agreements.

**Mechanism.** The role template renders working agreements uniformly; role-specific lines need data. Add an optional per-role agreements field: list of strings on the catalog RoleDef (and the matching ExtraKey, stored in item extra like responsibilities/skills), rendered as extra bullets in the '## Working agreements' intro block of role.md.j2 (before the regime sections). Empty for all roles except reviewer for now.

**Reviewer's line (the payload):** File review findings as tracked sub-entities — sq review <n> add-finding with severity, statuses updated as they close — never as body prose; finding-scoped comments, statuses, and dossier panes all depend on the structure.

**Acceptance.** sq sync regenerates the reviewer role file with the line (other roles unchanged); test asserts the reviewer role body carries it and a non-reviewer role does not; gates clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 68 add-subtask "<title>"`; track with `sq task 68 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T13:37:48Z] Elias Python:
  - Implemented per-role working-agreement lines (TASK-000068). Four files changed.
  - ExtraKey.AGREEMENTS added to src/squads/_models/_extras.py.
  - RoleDef gained an optional agreements tuple in src/squads/_roles/_catalog.py; to_extra/from_extra carry it through. Reviewer populated with the findings-as-sub-entities line from the task body; all other roles default to empty.
  - role.md.j2 renders agreements as extra bullets between the opening 'Operate as...' sentence and the 'Track all work...' line, only when the list is non-empty.
  - sync() now calls _refresh_catalog_extra() per role before regenerating the body. This merges any new catalog-defined fields (like agreements) into existing items' frontmatter — so rolling out a new RoleDef field never requires manual item edits; sq sync is sufficient.
  - Two new tests in tests/test_skills.py: reviewer body carries add-finding / never as body prose; tech-writer body does not.
  - Gates: 357 passed, 1 skipped; pyright 0 errors; ruff clean; sq check no issues.
<!-- sq:discussion:end -->
