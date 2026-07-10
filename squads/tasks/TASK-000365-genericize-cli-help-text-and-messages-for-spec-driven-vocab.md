---
id: TASK-365
sequence_id: 365
type: task
title: Genericize CLI help text and messages for spec-driven vocab
status: Draft
parent: FEAT-336
author: tech-lead
created_at: '2026-07-10T02:00:09Z'
updated_at: '2026-07-10T02:02:36Z'
---
<!-- sq:body -->
## Scope

Surface 1 of the REV-360 audit: CLI `--help` text, command docstrings, next-step hints,
and the `sq <kind> show` display pane. Make every enumerated value/vocab reference derive
from the active spec (or drop the misleading enumeration) so help and enforcement agree.
Files: `_cli/_items.py`, `_cli/_create.py`, `_cli/_main.py`, `_cli/_override.py`,
`_cli/_common.py`. Independent of the other FEAT-336 tasks (disjoint files).

## Covered REV-360 findings

- MEDIUM — `_cli/_items.py:262-266` — retype NEW-TYPE help hardcodes
  "epic|feature|task|bug|decision|review|guide"; validation two lines away derives
  targets from `get_active_spec().work_types()`. Make help agree.
- MEDIUM — `_cli/_items.py:168` (+ siblings `_create.py:63`, `_create.py:243`,
  `_main.py:358` & `415` list/tree `--priority`, `_main.py:360` & `417`
  `--min-priority`) — `--priority` help hardcodes "urgent|high|medium|low"; value is
  validated via `parse_badge_code("priority", …)` against the active spec.
- MEDIUM — `_cli/_items.py:545` (+ `_items.py:618-619` finding update) —
  `add-finding --severity` help hardcodes "critical|high|medium|low|info".
- LOW — `_cli/_items.py:496` (add_story) `:522` (add_subtask) `:552` (add_finding)
  docstrings hardcode the parent type name ("on this feature/task/review").
- LOW — `_cli/_main.py:307` — `sq init` success hint hardcodes `sq create task "…"`.
- LOW — `_cli/_main.py:865` (reflog `--item` "e.g. TASK-<n>") and `_override.py:50`
  ("e.g. 'items/task.md.j2'") — illustrative example prefixes bake in `task`.
- ADDED (see REV-360 comment) — `_cli/_common.py:384` `print_subentity` hardcodes a
  severity-only meta line in the `sq <kind> show` pane; it won't display any other
  declared field on a custom sub-entity kind. Derive the displayed field(s) from the
  kind's declared fields.

## Guidance

- Prefer deriving the enumerated values from the active spec collection/`work_types()`;
  where a help string can't easily interpolate spec data, drop the hardcoded enumeration
  in favour of a spec-pointing phrasing rather than lying about accepted values.
- Illustrative-example prefixes (reflog/override) are LOW: acceptable to keep a generic
  phrasing rather than a specific bundled prefix.

## Acceptance

- No CLI help/docstring enumerates bundled type/priority/severity values as the fixed
  grammar where the underlying validation is spec-driven.
- `print_subentity` shows all declared fields for the sub-entity kind, not just severity.
- Full gate green (pytest/pyright/ruff check/ruff format).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 365 add-subtask "<title>"`; track with `sq task 365 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
