---
id: TASK-340
sequence_id: 340
type: task
title: Add Collection/Badge/Field spec schema; bundle priority/severity
status: Draft
parent: FEAT-327
author: tech-lead
refs:
- ADR-323
description: 'Additive: 3-level badge schema + bundled default priority/severity collections/fields
  + fail-closed validation; byte-identical'
subentities:
- local_id: ST1
  title: Add Collection/Badge/Field schema + bundle byte-identical priority/severity
  status: Todo
  story: US1
- local_id: ST2
  title: 'Fail-closed validation: field-code uniqueness, reserved-key, collection
    integrity'
  status: Todo
  story: US4
created_at: '2026-07-09T08:19:59Z'
updated_at: '2026-07-09T08:21:05Z'
---
<!-- sq:body -->
## Scope

Land the additive foundation of ADR-323's badge model: add the three-level
`Collection`/`Badge`/`Field` schema to the workflow spec, declare `priority`
and `severity` as **bundled default collections + fields** byte-identical to
today's `Priority`/`Severity` enum values, and add the fail-closed spec-load
validation for the new field declarations. This task is **purely additive and
behavior-preserving**: the `Priority`/`Severity` enums, `*_EMOJI` maps, and
`ItemSpec.severity_field` all still exist and still drive runtime — this task
only introduces the parallel spec vocabulary and validates it. Deleting the
enums and switching the runtime onto the spec fields is the next task.

Covers US1 (the schema + bundled-defaults half) and US4 (fail-closed
validation). A no-override squad must be byte-identical after this task.

## Areas / files

- `_workflow/_models.py` — add the three pydantic models:
  - `Badge` — `{ code, label, emoji, ...extras }` (the extras channel is
    reserved for future presentation keys; only `emoji` used this pass).
  - `Collection` — `{ code, label, ordered: bool, default: str | None,
    badges: list[Badge] }`. `ordered` drives sort + threshold filtering; ship
    **ordered-only** this pass but keep the flag in the schema (ADR-323 §3).
  - `Field` — `{ code, label, collection: str, required: bool = False,
    default: str | None = None }`.
  - `WorkflowSpec.collections: dict[str, Collection]` (keyed by collection
    code); `fields: list[Field]` on both `ItemSpec` and the sub-entity-kind
    spec model. Add `fields_for(type_or_kind) -> list[Field]` and a
    `collection(code) -> Collection` accessor.
- `_workflow/_loader.py` — parse `[collections.<code>]` (with its ordered
  `badges` list) and the `.fields` list on `[items.<type>]` /
  `[subentity_kinds.<kind>]` from TOML into the new models.
- Bundled default spec (the packaged default `.toml`) — declare the
  `priority` and `severity` collections and wire the fields, **byte-identical
  to today**:
  - `priority` collection: ordered, badges `urgent`/`high`/`medium`/`low`
    with labels `Urgent`/`High`/`Medium`/`Low` and emoji
    `🔴`/`🟠`/`🟡`/`🟢`, no collection default (priority is optional
    everywhere).
  - `severity` collection: ordered, collection `default = "medium"`, badges
    `critical`/`high`/`medium`/`low`/`info` with labels
    `Critical`/`High`/`Medium`/`Low`/`Info` and emoji `🔴`/`🟠`/`🟡`/`🟢`/`🔵`.
  - `priority` field (`code=priority`, `label=Priority`, `collection=priority`)
    on **every bundled work type** (the seven: epic/feature/task/bug/decision/
    review/guide) — matching today's global-optional priority.
  - `severity` field (`code=severity`, `label=Severity`,
    `collection=severity`, `required=false`, `default=medium`) on `bug`
    item-level and on the `finding` sub-entity-kind (finding is `required`
    per ADR-323's table).
  - Cross-check the exact codes/labels/emoji/defaults against the current
    `_models/_enums.py` `Priority`/`Severity`/`PRIORITY_EMOJI`/`SEVERITY_EMOJI`/
    `DEFAULT_SEVERITY` so the bundled collections reproduce them exactly.
- **Fail-closed spec-load validation** (in `WorkflowSpec._validate`, the same
  seam ADR-322's type/status validation uses):
  1. **Field-code uniqueness** within one type/kind — two fields on the same
     type/kind with the same `code` is a load error (a field `code` is a
     frontmatter key + CLI flag; a dup would silently shadow).
  2. **Reserved-key collision** — a field `code` may not shadow a reserved
     item/sub-entity frontmatter key (`type`, `status`, `id`, `sequence_id`,
     `prefix`, `parent`, `refs`, `assignee`, `title`, `description`, … —
     enumerate the exact reserved set from the current `Item`/`SubEntity`
     frontmatter models; do not hand-copy a stale list).
  3. **Collection referential integrity** — every field's `collection` must
     name a declared collection; every `default` (field-level and
     collection-level) must be a badge `code` present in that collection; a
     `required` field with no resolvable default is rejected.
  Each failure raises `SquadsError` with a clear, actionable message.

## Done criteria

- `Collection`/`Badge`/`Field` exist in `_workflow/_models.py`;
  `[collections.*]` and `.fields` on `[items.*]`/`[subentity_kinds.*]` parse
  and round-trip through the loader.
- The bundled default spec declares `priority`/`severity` collections + fields
  reproducing today's enum codes/labels/emoji/defaults exactly.
- Spec load fails closed with a clear error on: a duplicate field `code`
  within a type/kind, a field `code` colliding with a reserved key, and a
  field whose `collection` (or a `default` badge code) doesn't resolve.
- A no-override squad is **byte-identical** — the enums still drive runtime;
  this task adds the spec vocabulary alongside without switching onto it.
- `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean;
  full suite green.

## Sequencing note

First on the feature — the additive foundation the other three build on. No
intra-feature dependency. Do NOT delete the enums or repoint runtime here;
that is deliberately deferred so this task stays byte-identical and trivially
bisectable. The Field schema landed here is the **shared** schema FEAT-212
(custom sub-entity kinds) will consume — keep it kind-agnostic (identical
mechanism for item types and sub-entity kinds, not forked).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 340 add-subtask "<title>"`; track with `sq task 340 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Add Collection/Badge/Field schema + bundle byte-identical priority/severity | US1 |
| ST2 | Todo |  | Fail-closed validation: field-code uniqueness, reserved-key, collection integrity | US4 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add Collection/Badge/Field schema + bundle byte-identical priority/severity

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — Priority/severity become spec badge collections
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Add Collection/Badge/Field pydantic models + collections map + fields on ItemSpec/subentity-kind + fields_for()/collection() accessors; parse [collections.*] and .fields in the loader; declare bundled priority/severity collections+fields reproducing today's enum codes/labels/emoji/defaults exactly. Enums still drive runtime — additive only.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Fail-closed validation: field-code uniqueness, reserved-key, collection integrity

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US4 — Spec load fails closed on bad field decls
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
In WorkflowSpec._validate: reject a duplicate field code within one type/kind, a field code shadowing a reserved item/sub-entity frontmatter key, and a field whose collection (or default badge code) doesn't resolve — each a clear SquadsError.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
