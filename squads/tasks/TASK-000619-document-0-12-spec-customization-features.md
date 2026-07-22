---
id: TASK-619
sequence_id: 619
type: task
title: Document 0.12 spec-customization features
status: Done
author: tech-writer
created_at: '2026-07-22T20:05:21Z'
updated_at: '2026-07-22T20:35:48Z'
---
<!-- sq:body -->
Document two spec-customization features that shipped without docs:

1. Custom records-category item types: How adopters declare their own durable-reference item type with category = "records" in a workflow override.

2. Status roles: How statuses reference a role catalog entry that controls terminal/hidden/color display attributes.

Update docs/overrides.md and/or docs/workflow.md with adopter-facing examples grounded in the bundled spec.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 619 add-subtask "<title>"`; track with `sq task 619 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T20:07:19Z] Theo Writer:
  - Documented two 0.12 spec-customization features in adopter-facing docs:
  - **Custom records-category item types:** Updated docs/overrides.md and docs/workflow.md with sections explaining how adopters can declare durable-reference item types (like postmortems, contracts) with category="records". Records never have parents, live in their own folders, and aren't tracked in sq inbox. Includes TOML examples grounded in the bundled spec.
  - **Status roles:** Documented the role catalog and how each status references a role to govern its terminal/hidden/color attributes. Added a bundled role reference table, showed how to define custom roles, and updated all TOML examples in both docs to use role references instead of the earlier terminal field. sq workflow roles command documented for querying the catalog.
  - All examples verified against bundled default_workflow.toml. sq check passes. Ready for manager review.
<!-- sq:discussion:end -->
