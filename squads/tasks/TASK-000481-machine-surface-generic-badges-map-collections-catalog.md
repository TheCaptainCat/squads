---
id: TASK-481
sequence_id: 481
type: task
title: 'Machine surface: generic badges map + collections catalog'
status: Done
parent: FEAT-471
author: tech-lead
assignee: python-dev
priority: high
description: 'Core: ADR-474 Part A collections + type-catalog fields (US7/F20)'
created_at: '2026-07-18T20:10:47Z'
updated_at: '2026-07-18T20:37:05Z'
---
<!-- sq:body -->
Story: US7 (REV-448 F20, High). **Discipline: CORE / Python** (machine surfaces + spec code). Implements ADR-474 Part A (collections) and A3 (type-catalog field binding).

Authored as one cohesive core task because A1/A2/A3 are one surface subfamily (the collection vocabulary) touching the same `_cli` machine-surface and `WorkflowSpec`/`badges` code, and the story maps 1:1 to US7. US9 (Part B, status roles) is a separate task — a distinct axis (spec TOML edit + a catalog-only status surface, no item-payload change) mapping to a different story, so keeping them apart keeps each task's acceptance crisp and independently reviewable.

## Scope

- **A1 — generic `badges` map on every item-bearing `--json` surface**, keyed by field code, built with the shipped `_resolve_badges` shape (iterate `spec.fields_for(item.type)`, include a field only when `item.badge_value(code)` is non-null). Apply to:
  - `sq tree --json` — each node gains `badges` (today: literal `priority` only).
  - `sq list --json` — each row gains `badges`, unifying the bundled/`extra` split.
  - `sq show --json` — top-level `badges`, and each `subentities` entry gains its own `badges` (built from `spec.fields_for(kind)` + `sub.badge_value`).
- **A2 — new `sq workflow collections --json`**: bare JSON array, one object per declared collection: `{collection, label, ordered, default, badges:[{code, label, emoji}]}`. Items emit codes only; glyph/label live once here.
- **A3 — field→collection binding on the type catalog**: each `sq workflow types --json` row gains `fields:[{code, label, collection}]` (additive to ADR-459's catalog; a new key on each row, no removal/rename).

## Constraints

- **Additive superset — no break.** Keep legacy keys alongside: `sq tree`/`sq graph` keep `priority`; `sq list`/`sq show` keep top-level `priority`/`severity` + `extra`. No frontmatter change, no `.squads.json` change, no schema bump, no migration.
- Zero hardcoded collection names anywhere on the surface — everything derives from the active `WorkflowSpec`.

## Acceptance

- `sq tree`/`list`/`show --json` each carry a spec-driven `badges` map; `show` sub-entities each carry `badges`; a spec that renames/drops/adds a collection is faithfully represented.
- `sq workflow collections --json` emits the bare array per spec; new golden fixture matches; a field-set-vs-model drift test guards its frozen key set (ADR-459 treatment).
- `sq workflow types --json` rows gain `fields`; the `workflow_types.json` golden and its drift test are updated for the new key.
- Additive only: no existing key renamed/removed; no schema/migration.
- Full Python suite green; pyright strict + ruff clean; service-level + CLI-smoke tests per new/changed surface.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 481 add-subtask "<title>"`; track with `sq task 481 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-18T20:26:44Z] Elias Python:
  - Done: shared badges.resolve_badges (moved out of _refs._resolve_badges, delegates now) gives sq tree/list/show --json + show's subentities a generic badges map (additive, priority/severity/extra untouched). New sq workflow collections --json (COLLECTION_CATALOG_FIELDS) + sq workflow types --json fields[] (A3, TYPE_CATALOG_FIELDS extended). Goldens: workflow_collections.json + workflow_statuses.json new, workflow_types/list/list_feature/tree/tree_feat/feature_show/task_show additive-diffed (verified key-add only). Tests: test_generic_badge_map_resolution, test_item_json_badges_map, test_workflow_collections_cli, extended test_workflow_types_cli. pyright/ruff clean, sq check clean.
- [2026-07-18T20:37:05Z] Elias Python:
  - Fix-back: stripped stray ADR-474/ADR-459 ticket-ID tokens from src/ docstrings (_badges.py, _cli/_workflow_cmd.py, _cli/_common.py, _services/_refs.py) and test docstrings (test_generic_badge_map_resolution, test_workflow_collections_cli, test_workflow_types_cli, test_item_json_badges_map) — rationale kept, ID pointer dropped per repo convention. Meta ticket-ref gate + full targeted suite green.
<!-- sq:discussion:end -->
