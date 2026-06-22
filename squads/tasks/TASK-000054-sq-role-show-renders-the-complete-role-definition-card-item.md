---
id: TASK-000054
sequence_id: 54
type: task
title: sq role show renders the complete role definition (card + item body)
status: Done
parent: FEAT-000041
author: tech-lead
assignee: python-dev
priority: high
subentities:
- local_id: ST1
  title: Render active role body below the catalog card in sq role show
  status: Done
  story: US1
created_at: '2026-06-12T07:52:37Z'
updated_at: '2026-06-23T09:58:02Z'
---
<!-- sq:body -->
## Goal
`sq role show <slug>` must show the **complete** role definition — the catalog card it prints today *plus* the active role item's body (mission, responsibilities, skills list, working agreements). Today it resolves only via `role_by_slug(slug)` (bundled catalog) and never touches the tracked item, so the working agreements (the part an agent needs to behave correctly) are invisible from the CLI. FEAT-000040 just landed and `sq sync` re-renders the role item body via `_services/_maintenance.py::_regen_role_body` from `agents/role.md.j2` — this task must surface that *new, complete* body.

## Where
- `src/squads/_cli/_role.py::show_role` — currently builds a Panel from `RoleDef` fields only. Needs to also fetch and render the active role item's body.
- Service/roster: a slug to role-item resolver already exists at `src/squads/_services/_base.py` (~line 232, matching ItemType.ROLE and X.SLUG). Reuse it; do not add a parallel lookup.
- Body extraction: read the item file and pull the body region via `_sections.get_section(text, markers.BODY)` (BODY = 'body'). Render it below the card.

## Behaviour
- If the role is **active** (tracked item exists): show card + item body.
- If only **bundled** (no active item): degrade gracefully to today's card and hint to activate. Decide+document the exact fallback.
- Honor FEAT-000026 conventions (panes, --raw, piped) only if it has landed; otherwise keep current Panel rendering and leave a note. Do not block on FEAT-000026.

## Acceptance (US1)
- Output contains the working agreements and skills, matching the item body (`sq role show tech-lead` shows the Working agreements section).
- Covered by a test asserting the agreements text is present in the output.

## Tests
- Service-level: a method returning the complete definition for a slug (card + body).
- CLI smoke: `sq role show <slug>` output contains a working-agreements marker phrase.
- Keep `uv run pyright && ruff check && ruff format --check` clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 54 add-subtask "<title>"`; track with `sq task 54 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Render active role body below the catalog card in sq role show | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Render active role body below the catalog card in sq role show

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — As an agent adopting my persona, I want sq role show to give me the complete definition including working agreements, so that I never open the file to learn my job
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Render active role item body (working agreements + skills) below the catalog card in sq role show, with a test asserting the agreements are present.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
