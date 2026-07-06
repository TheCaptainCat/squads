---
id: TASK-310
sequence_id: 310
type: task
title: Strip squad-item refs from bundled TOML comments
status: Done
parent: FEAT-237
author: tech-lead
assignee: python-dev
priority: medium
subentities:
- local_id: ST1
  title: Strip refs from TOML structural comments
  status: Done
  story: US1
created_at: '2026-07-06T12:55:26Z'
updated_at: '2026-07-06T13:21:32Z'
---
<!-- sq:body -->
SRC WAVE. Scope: the structural comments in the three bundled package-data TOMLs — src/squads/_workflow/default_workflow.toml, src/squads/_roles/roles.toml, src/squads/_interactions/playbook.toml. Blast radius: small (~10 ref-hits, 3 files). Strip-only, no restyle/rewording of the data. Disjoint files from all other tasks — parallel-safe. Done when: zero squad-item refs remain in the comments of these three files; the files still parse and load (sq init/sync unaffected); tests green and unchanged.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 310 add-subtask "<title>"`; track with `sq task 310 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Strip refs from TOML structural comments | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Strip refs from TOML structural comments

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — Code comments carry no squad-item references
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Stripped squad-item refs from the structural comments in default_workflow.toml, roles.toml, and playbook.toml (ADR-000214/ADR-000221/ADR-000226/ADR-000232 citations removed, reworded to plain descriptions). Data/keys untouched; the --story US1 CLI-syntax example line in playbook.toml is a legitimate illustrative payload and was left as-is. Files still parse; full suite green.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-06T13:21:31Z] Elias Python:
  - Stripped squad-item refs from the structural comments in default_workflow.toml, roles.toml, playbook.toml. Data/keys unchanged; files still parse (sq init/sync unaffected).
  - Full suite green (shared run with TASK-308: 1641 passed, 1 skipped, 0 failed).
<!-- sq:discussion:end -->
