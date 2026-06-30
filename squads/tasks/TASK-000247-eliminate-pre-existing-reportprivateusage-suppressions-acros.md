---
id: TASK-000247
sequence_id: 247
type: task
title: Eliminate pre-existing reportPrivateUsage suppressions across service mixins
status: Draft
author: tech-lead
priority: low
description: 'Tech-debt: replace ~20 cross-module private reach-ins with public APIs/accessors'
created_at: '2026-06-30T08:51:11Z'
updated_at: '2026-06-30T08:51:11Z'
---
<!-- sq:body -->
Decision (Pierre, 2026-06-30): we stop suppressing pyright's reportPrivateUsage. Modules stay private (leading-underscore), but cross-module code must not reach into another module's private names behind a '# pyright: ignore'. Where an inner name is genuinely needed across a boundary, make it public or expose a public accessor.

FEAT-000209's own suppressions (Group A: _active_spec reach-ins, _BUNDLED_SPEC, Workflow._from_machine) were already cleaned in that feature via active_spec()/bundled_spec()/Workflow.from_machine. THIS task covers the pre-existing Group B, unrelated to that feature.

Group B sites (~20): the dominant one is self.store._log(...) called from the service mixins (_items, _base, _refs, _retype, _collab, _subentities, _maintenance) — likely wants a public logging method on IndexStore. Plus: _cli/_common.py discussion._status_badge / discussion._SUMMARY_COLS / svc._role_item|_skill_item|_operator_item; _cli/_workflow_cmd.py + _cli/_main.py common._active_dir; _cli/_role.py _is_full_id_shape import. Do as ONE focused pass; pyright must stay at 0/0 with all reportPrivateUsage suppressions removed (or the rule made an error, not an ignore).

Tech-lead to design the public surface (esp. the store logging API) before implementation.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 247 add-subtask "<title>"`; track with `sq task 247 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
