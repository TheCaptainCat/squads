---
id: TASK-352
sequence_id: 352
type: task
title: 'Discussion rendering: resolver/field-driven prefixes, placeholders, columns'
status: Draft
parent: FEAT-212
author: tech-lead
refs:
- TASK-349:depends-on
subentities:
- local_id: ST1
  title: Summary table renders from declared columns (base + fields + Story)
  status: Todo
  story: US1
created_at: '2026-07-09T21:31:32Z'
updated_at: '2026-07-09T21:33:44Z'
---
<!-- sq:body -->
ADR-348 §5 rendering half: retire the static per-kind tables in _discussion.py so local-id prefixes, scaffold prose, and summary columns all derive from the resolved SubentityKindSpec + its ADR-323 fields.

## Scope

Replace `_LOCAL_ID_PREFIX` (kind->US/ST/F) with `kind_spec.local_prefix`; `local_id_for`/`next_local_id` resolve via the active spec.

Replace `_PLACEHOLDER` (and the three _*_PLACEHOLDER strings) with `kind_spec.placeholder`, falling back to a generic kind-name-derived scaffold line when the kind declares none; `body_placeholder`/`build_block` resolve via spec.

Replace `_SUMMARY_COLS`/`_summary_cells` with a field-driven derivation: fixed base (local_id, Status, Assignee, Title) + one column per declared `field` (headed by the field label, e.g. Severity, resolved through _badges.py — no severity special-casing) + a Story column iff `maps_parent_story`. `render_summary` builds rows from this derivation.

Establish this as the single column-derivation shared with the CLI list table (TASK-353 consumes it) — this unifies the current CLI-vs-body column drift the ADR notes (the CLI story table shows a Story column the body summary omits). Put the shared derivation where both callers can reach it (e.g. a helper in _discussion.py or _badges.py).

## Files owned

- src/squads/_discussion.py (_LOCAL_ID_PREFIX/_PLACEHOLDER/_SUMMARY_COLS/_summary_cells retired; local_id_for/next_local_id/body_placeholder/build_block/render_summary spec-driven; shared column-derivation helper)

## Acceptance

- Built-in story/subtask/finding blocks render byte-identical local ids, placeholders, and summary tables (AC4) — modulo the intended drift fix (Story column now consistent between CLI and body).

- A custom kind with a declared field renders its column headed by the field label; severity is just the generic field column.

- Full suite green.

## Depends on

TASK-349 (local_prefix/placeholder/plural/fields/maps_parent_story on kind_spec). Runs in parallel with TASK-351 (disjoint files); TASK-353 depends on the shared column-derivation landed here.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 352 add-subtask "<title>"`; track with `sq task 352 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Summary table renders from declared columns (base + fields + Story) | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Summary table renders from declared columns (base + fields + Story)

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — As a project admin, I want to define custom sub-entity kinds for my custom types in TOML
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
