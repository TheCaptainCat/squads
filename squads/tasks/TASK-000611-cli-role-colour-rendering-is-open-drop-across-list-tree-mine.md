---
id: TASK-611
sequence_id: 611
type: task
title: CLI role-colour rendering + is_open drop across list/tree/mine/workload
status: Done
parent: FEAT-605
author: tech-lead
priority: medium
refs:
- ADR-604
created_at: '2026-07-22T15:37:25Z'
updated_at: '2026-07-22T16:57:00Z'
---
<!-- sq:body -->
Implements FEAT-605 US3. Render status colour across the CLI surfaces keyed on the role's `color` intent, and drop `is_open` from every `--json` item payload. Depends on the US1 model + US2 catalog.

## Scope (per ADR-604 §6, "CLI")
- Colour rendering keyed on `role.color` intent -> a concrete `rich` colour, with a neutral fallback for an unrecognised intent, in: `sq list`, `sq tree`, `sq mine`, `sq workload`, and the row colour in the `sq workflow statuses` catalog table.
- `_rendering/templates/workflow.md.j2` cheatsheet: replace the `.terminal` check with a `role.settled` check via a spec helper exposed to the template; key row colour on `role.color`.
- Drop `is_open` from the `--json` payloads that carry it: `sq tree` (2 emits), `sq list`, and `sq mine` (filter reads `not role.settled`; the field is removed from the payload).
- `sq workload` open/closed counts read `role.settled`.
- `sq list` visible filter + hidden count: call site unchanged (`hidden_by_default` re-derives).

## Acceptance
- Each surface colours a status by its role intent; an off-catalog/unknown intent renders neutral, never errors.
- No `--json` item payload emits `is_open`; `sq mine`'s open filter still selects the same items.
- Cheatsheet renders settled-ness from role, not `terminal`.
- CLI smoke tests for the colour mapping + the dropped `is_open` field.

## Gates
`uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check . && uv run --all-extras pytest`. Leave `sq check` clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 611 add-subtask "<title>"`; track with `sq task 611 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T16:47:33Z] Elias Python:
  - Implemented: intent->rich colour map + status_style/status_text helpers in src/squads/_cli/_common.py (positive=green, danger=red, warning=yellow, info=cyan, muted=bright_black, neutral='' — total map, unrecognised intent falls back to neutral, no crash).
  - Applied via Rich's style= param (Text objects), never markup interpolation: _item_table's Status column (shared by sq list/sq mine), sq tree's node label (parens dim, status coloured), and sq workflow statuses' Status cell.
  - sq workload has no per-status cell (aggregated open/closed counts only, already role-derived via spec.is_open from increment 1) — no colour site there; noting this since the task listed it among surfaces.
  - Dropped is_open from --json payloads: sq list (_cli/_main.py list_items), sq tree (node()), sq mine — 3 sites. mine's own open-filter logic (spec.is_open(i.status)) is unchanged, only the emitted field is gone.
  - Regenerated + verified goldens: tests/goldens/list.json, list_feature.json, tree.json, tree_feat.json (each lost only its is_open lines, nothing else diffed). mine_manager.json unaffected (empty array in that fixture).
  - Targeted gates green: uv run --all-extras pytest tests/cli/test_json_output_shape.py tests/cli/test_workflow_statuses_cli.py tests/cli -q -k 'list or tree or mine or workload or json or workflow' (all pass, 1 skip). Repo-wide pyright/ruff check/ruff format --check clean. sq check clean. Ticket-ID hygiene guard clean.
<!-- sq:discussion:end -->
