---
id: TASK-342
sequence_id: 342
type: task
title: CLI derives --<field> filter/sort/badges generically
status: Draft
parent: FEAT-327
author: tech-lead
refs:
- ADR-323
- TASK-341:depends-on
description: One parse_badge_code/badge_render for all axes; --<field>/--min-<field>/sort/columns
  from fields_for(); custom-axis verified
subentities:
- local_id: ST1
  title: Generic parse_badge_code/badge_render; --<field>/--min-<field>/sort/columns
    from fields
  status: Todo
  story: US2
- local_id: ST2
  title: Verify full CLI surface against a custom badge axis beyond priority/severity
  status: Todo
  story: US2
created_at: '2026-07-09T08:20:10Z'
updated_at: '2026-07-09T10:40:41Z'
---
<!-- sq:body -->
## Scope

Make the CLI derive its badge surface **generically from the fields a type or
sub-entity-kind declares** — the `--<field-code>` value/filter options,
`--min-<field-code>` (ordered collections only), sort, and the badge columns
all come from `fields_for(type_or_kind)`, with no hand-written per-axis
`parse_priority`/`parse_severity`/`priority_badge`/`_severity_badge` pairs
left. Delivers US2, including verification against a **custom** badge axis
beyond the two bundled ones.

## Areas / files

- `_cli/_common.py` — collapse `parse_priority`/`parse_severity` into one
  `parse_badge_code(field, code, spec)` and `priority_badge`/`_severity_badge`
  into one `badge_render(field, code, spec)`; validate the given code against
  the field's bound collection, error clearly on an unknown code (listing the
  collection's codes). Column headers come from the field `label`.
- `_cli/_main.py` — `--<field>` create/list/tree filter and the badge column
  in list/tree/`--json` derive from the declared fields of the type being
  listed/created, not a hardcoded `--priority`/`Priority` pair. `--min-<field>`
  threshold filter and sort are offered **only** when the field's collection
  is `ordered` (both bundled defaults are). Options are generated per the
  active spec's fields.
- `_cli/_items.py` — finding `--severity` (create default + update) and the
  finding `Severity` column derive from the `finding` kind's declared fields;
  same generic path as item-level fields.
- `_discussion.py` — the finding summary/head `Severity` column and any
  badge rendering resolve emoji/label from the bound collection via the shared
  `badge_render`, with the graceful raw-code fallback (no `SEVERITY_EMOJI`).
- Any per-type CLI option generation must stay deterministic and handle a type
  that declares **zero** fields (no badge option/column) and a type that
  declares a **non-bundled** field.

## Done criteria

- No hand-written per-axis parse/render pairs remain: `grep -rn
  'parse_priority\|parse_severity\|priority_badge\|_severity_badge'
  src/squads/_cli src/squads/_discussion.py` is empty; the generic
  `parse_badge_code`/`badge_render` (or equivalently named) helpers drive all
  axes.
- `--<field>`, `--min-<field>` (ordered only), sort, and badge columns work
  for **any** field declared in the spec — proven by a test spec that declares
  a custom badge axis (e.g. an `impact` field off a custom `level` collection,
  and/or the ADR-323 `impact`/`urgency`-off-one-collection reuse case) and
  exercises create/update/filter/sort/column for it, not just priority and
  severity.
- A no-override squad's CLI surface (options, columns, filters, sort order) is
  identical to before the feature.
- `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean;
  full suite green.

## Sequencing note

Depends-on the enum-deletion/generic-storage task — the CLI consumes
`fields_for()` and the generic badge-code storage/render that task establishes,
and the old `parse_*`/`*_badge` helpers it replaces are removed there or here
in one sweep. Independent of the migration task (can land before or after it);
the CLI reads the badge code regardless of which on-disk location severity
currently sits in.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 342 add-subtask "<title>"`; track with `sq task 342 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Generic parse_badge_code/badge_render; --<field>/--min-<field>/sort/columns from fields | US2 |
| ST2 | Todo |  | Verify full CLI surface against a custom badge axis beyond priority/severity | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Generic parse_badge_code/badge_render; --<field>/--min-<field>/sort/columns from fields

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US2 — CLI derives filter/sort/badges from fields
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Collapse parse_priority/parse_severity into parse_badge_code and priority_badge/_severity_badge into badge_render; generate --<field>/--min-<field> (ordered only)/sort/columns per the type-or-kind's declared fields across _common/_main/_items/_discussion.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Verify full CLI surface against a custom badge axis beyond priority/severity

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US2 — CLI derives filter/sort/badges from fields
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Add a test spec declaring a custom badge axis (e.g. impact off a custom 'level' collection, incl. the impact/urgency-off-one-collection reuse case) and exercise create/update/filter/min/sort/column for it — proving the surface isn't hardwired to priority/severity.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-09T10:40:41Z] Catherine Manager:
  - Carry-over from TASK-341 review (REV-344, LOW/F1): collapse the duplicate emoji-resolution logic between _cli/_common.py::_badge_emoji and _discussion.py::_severity_emoji/_severity_badge as part of this task's generic CLI derivation — the per-axis parse/badge pairs (parse_priority/parse_severity, the two emoji resolvers) should become one spec-field-driven path.
<!-- sq:discussion:end -->
