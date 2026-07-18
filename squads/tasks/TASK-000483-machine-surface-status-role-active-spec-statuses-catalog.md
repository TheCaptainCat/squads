---
id: TASK-483
sequence_id: 483
type: task
title: 'Machine surface: status role=active spec + statuses catalog'
status: Done
parent: FEAT-471
author: tech-lead
assignee: python-dev
priority: medium
description: 'Core: ADR-474 Part B status roles (US9/F26 core)'
created_at: '2026-07-18T20:10:48Z'
updated_at: '2026-07-18T20:37:06Z'
---
<!-- sq:body -->
Story: US9 (REV-448 F26 machine-surface half, Medium). **Discipline: CORE / Python** (spec TOML + machine surface). Implements ADR-474 Part B (status roles).

Separate from US7 (Part A) by design: this axis is a spec-TOML edit plus a catalog-only status surface with **no** item-payload change, mapping to a different story — keeping it apart from the collections task keeps each task's acceptance crisp and independently reviewable.

## Scope

- **B1 — spec**: `default_workflow.toml` gains `role = "active"` on `[statuses.InProgress]` (work-item working state) and `[statuses.Active]` (roster working state). Both are already `terminal = false`; `role`/`terminal` are orthogonal (Superseded already carries both), so this is purely additive. `StatusSpec.role` stays `str | None`.
- **B2 — new `sq workflow statuses --json`**: bare JSON array, one object per declared status: `{status, terminal, role (str|null), badge (emoji|null)}`. A client joins an item's `status` to this catalog to read `role`/`terminal`/`badge`.
- **B3 — catalog-only**: do NOT add a per-item `role`/`is_active` field to tree/list/show. The role reaches clients only via the status catalog (the `is_open` per-node convenience is deliberately not extended to the role axis).

## Constraints

- **Additive superset — no break.** Adding `role="active"` changes no existing consumer (only `Superseded` set a role before). Spec-TOML + JSON output only: no frontmatter change, no `.squads.json` change, no schema bump, no migration.
- Explicitly out of scope (deferred by ADR-474): widening `StatusSpec.role` from `str | None` to `list[str]`.

## Acceptance

- `default_workflow.toml` InProgress and Active carry `role = "active"`; Superseded unchanged.
- `sq workflow statuses --json` emits the bare array per spec; new golden fixture matches; a field-set-vs-model drift test guards its frozen key set (ADR-459 treatment).
- No per-item `role`/`is_active` field added to any item surface.
- Additive only: no schema/migration.
- Full Python suite green; pyright strict + ruff clean; service-level + CLI-smoke tests for the new surface + the spec edit.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 483 add-subtask "<title>"`; track with `sq task 483 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-18T20:26:46Z] Elias Python:
  - Done: default_workflow.toml InProgress/Active gain role="active" (orthogonal to terminal; Superseded unchanged). New sq workflow statuses --json (STATUS_CATALOG_FIELDS: status/terminal/role/badge) + human table; golden workflow_statuses.json. Catalog-only per B3 — proved negatively (no role/is_active on show/list/tree). Tests: test_status_semantic_role_active, test_workflow_statuses_cli. pyright/ruff clean, sq check clean.
- [2026-07-18T20:37:06Z] Elias Python:
  - Fix-back: stripped stray ADR-474 tokens from test_status_semantic_role_active.py + test_workflow_statuses_cli.py docstrings. Updated the stale test_type_spec_capability_flags::test_superseded_carries_a_role_no_other_bundled_status_carries (renamed to test_exactly_superseded_inprogress_and_active_carry_a_bundled_role) to the new spec truth: Superseded->superseded, InProgress/Active->active, everything else->None. Meta ticket-ref gate + capability-flags test + full targeted suite green.
<!-- sq:discussion:end -->
