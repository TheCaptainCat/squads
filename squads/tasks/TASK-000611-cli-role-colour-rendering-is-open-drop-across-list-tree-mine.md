---
id: TASK-611
sequence_id: 611
type: task
title: CLI role-colour rendering + is_open drop across list/tree/mine/workload
status: Draft
parent: FEAT-605
author: tech-lead
priority: medium
refs:
- ADR-604
created_at: '2026-07-22T15:37:25Z'
updated_at: '2026-07-22T15:37:25Z'
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
<!-- sq:discussion:end -->
