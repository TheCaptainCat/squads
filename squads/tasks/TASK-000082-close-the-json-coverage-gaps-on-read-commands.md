---
id: TASK-000082
sequence_id: 82
type: task
title: Close the --json coverage gaps on read commands
status: Done
parent: FEAT-000015
author: tech-lead
assignee: python-dev
priority: high
refs:
- REV-000086:addresses
subentities:
- local_id: ST1
  title: Add --json to check and sub-entity list commands
  status: Done
  story: US1
created_at: '2026-06-12T15:27:47Z'
updated_at: '2026-06-12T20:42:47Z'
---
<!-- sq:body -->
## Goal
Close the *real* gaps so every read command accepts `--json` and emits a documented shape (US1).

## Audit correction — the body's gap list is mostly stale
A code audit of `src/squads/_cli/` shows five of the six commands named in FEAT-000015's body **already have** `--json` today:
- `blocked` (_main.py:286), `mine` (_main.py:351), `workload` (_main.py:321), `inbox` (_main.py:240), `refs` (_items.py:216) — all already emit JSON via `console.print_json(...)`.
- `check` (_main.py:445) — **genuinely lacks `--json`.** This is the only one of the six that is correct.

So US1's actual surface to close is much smaller than the body implies.

## Scope — confirmed by op-pierre's ruling (2026-06-12)
The surface to close, with the scope boundary settled by product:
1. **`check`** (_main.py:443-459) — add `--json` emitting one object per issue: `{level, item, message}`. Note `check` exits **3** when any error-level issue exists (distinct exit code, ruled 2026-06-12 — see TASK-000083); `--json` must preserve that exit behaviour (emit the array, then still `raise typer.Exit(3)`).
2. **Sub-entity `list` commands** (stories / subtasks / findings) — `list_sub` in _items.py:309-314 has no `--json` path; it only prints `_sub_table`. Add `--json` emitting the sub-entity blocks (id/status/assignee/severity/story/title as applicable per kind).
3. **Role / skill / operator catalog viewers** — **added to scope by op-pierre's ruling (2026-06-12).** These catalog viewers get `--json` (overrides my earlier table-only recommendation). Emit the catalog rows in a documented shape.

## Out of scope — ruled (2026-06-12)
- `repair`, `docs`, and `workflow` stay **table-only** — not state reads in the script-author sense. Confirmed out-of-scope by op-pierre.

## Notes
- Reuse the existing emission pattern (`console.print_json(...)`); consider a small `emit_json` helper in _common.py only if it reduces real boilerplate — not required.
- Every shape touched here is contract material (see US3 golden tests + the FEAT-000013 deferral). Settle field names deliberately.

## Done when
- `check`, the three sub-entity `list` commands, and the role/skill/operator catalog viewers all accept `--json` and emit a documented shape.
- A service- or CLI-level test parses each new `--json` output.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 82 add-subtask "<title>"`; track with `sq task 82 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Add --json to check and sub-entity list commands | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add --json to check and sub-entity list commands

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a script author, I want --json on every read command (blocked, mine, workload, inbox, check, refs included), so that I can parse squad state without scraping tables
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
- [2026-06-12T20:36:46Z] Elias Python:
  - Implementation complete. All read commands that were in scope now accept `--json`.
  - Commands that gained `--json` and their emitted shapes:
  - - `check --json` → array of `{level, item, message}` objects. Exit behaviour preserved: still raises Exit(3) when any error-level issue is present (per the 2026-06-12 ruling; the table/exit-code doc path is tracked in TASK-000083).
  - - `task <n> subtasks --json` / `feature <n> stories --json` / `review <n> findings --json` → array of `{local_id, title, status, assignee, severity, story}` (fields inapplicable to a kind are null).
  - - `role catalog --json` → array of `{slug, full_name, title, is_default}`.
  - - `role <addr> show --json` → `{slug, id, activated, full_name, title, mission, model, is_default, responsibilities}`.
  - - `skill <addr> show --json` → `{id, slug, title, status, description, when_to_use, allowed_tools, file}`.
  - - `operator <addr> show --json` → `{id, slug, full_name, status, file}`.
  - 11 new tests cover each shape. Gate: 387 passed, pyright 0 errors, ruff clean.
  - @manager ready for review. @reviewer please verify the JSON shapes are correct and consistent before we finalise them as contract material (US3 golden tests).
- [2026-06-12T20:39:56Z] Paul Reviewer:
  - @manager review REV-000086 → ChangesRequested. Behaviour is correct and tests are green; two medium contract-surface findings to settle before TASK-000084 freezes the shapes:
  - F1: `show --json` uses "file" where siblings use "path" — rename for consistency.
  - F2: `check` table path still exits 1 vs `check --json` exits 3 — align the pair (here or via TASK-000083).
  - Details in REV-000086 finding bodies.
<!-- sq:discussion:end -->
