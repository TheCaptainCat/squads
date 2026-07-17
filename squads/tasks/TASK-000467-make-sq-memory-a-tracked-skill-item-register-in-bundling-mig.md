---
id: TASK-467
sequence_id: 467
type: task
title: Make sq-memory a tracked SKILL item (register in bundling + migrate)
status: Draft
author: manager
created_at: '2026-07-17T15:47:40Z'
updated_at: '2026-07-17T15:47:42Z'
---
<!-- sq:body -->
sq-memory is the only bundled skill NOT tracked as a SKILL item: plain squads/agents/skills/sq-memory.md, absent from .squads.json, while the other 9 (including the transversal 'greeting') are SKILL-NNN items. Transversal/cross-role is not the reason (greeting is transversal AND tracked). Fix: (1) register sq-memory as a tracked bundled SKILL in the skill-creation/bundling flow so fresh init/sync allocates it an id and indexes it like the others; (2) a migration for existing squads — rename to SKILL-000NNN-sq-memory.md, allocate the next global-counter id, add the index entry, repoint the .claude pointer. Architect to confirm the migration approach and whether it warrants an ADR before implementation.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 467 add-subtask "<title>"`; track with `sq task 467 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-17T15:47:42Z] Pierre Chat:
  - Transversal skills must be tracked items too — greeting is transversal and tracked, so cross-role is no excuse. Make sq-memory an item.
<!-- sq:discussion:end -->
