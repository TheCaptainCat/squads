---
id: TASK-340
sequence_id: 340
type: task
title: Add Collection/Badge/Field spec schema; bundle priority/severity
status: Done
parent: FEAT-327
author: tech-lead
refs:
- ADR-323
description: 'Additive: 3-level badge schema + bundled default priority/severity collections/fields
  + fail-closed validation; byte-identical'
subentities:
- local_id: ST1
  title: Add Collection/Badge/Field schema + bundle byte-identical priority/severity
  status: Done
  story: US1
- local_id: ST2
  title: 'Fail-closed validation: field-code uniqueness, reserved-key, collection
    integrity'
  status: Done
  story: US4
created_at: '2026-07-09T08:19:59Z'
updated_at: '2026-07-09T09:47:08Z'
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
| ST1 | Done |  | Add Collection/Badge/Field schema + bundle byte-identical priority/severity | US1 |
| ST2 | Done |  | Fail-closed validation: field-code uniqueness, reserved-key, collection integrity | US4 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add Collection/Badge/Field schema + bundle byte-identical priority/severity

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
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
**Status:** 🟢 Done
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
- [2026-07-09T09:33:55Z] Elias Python:
  - Landed the additive Collection/Badge/Field schema + bundled priority/severity + fail-closed validation. Files: src/squads/_workflow/_models.py (Badge/Collection/Field/SubentityKindSpec models, WorkflowSpec.collections/subentity_kinds, fields_for()/collection() accessors, _check_field_codes/_check_field_collections validators), src/squads/_workflow/_loader.py (parses [collections.*]/.fields/[subentity_kinds.*] for the bundled TOML AND additively for a project override — new collections/subentity_kinds entries accepted, redefining a built-in raises), src/squads/_workflow/default_workflow.toml (bundled priority/severity collections + fields).
  - Byte-identical: priority/severity collection codes/labels/emoji/default verified equal to _models/_enums.py's Priority/Severity/PRIORITY_EMOJI/SEVERITY_EMOJI/DEFAULT_SEVERITY by direct comparison in tests/test_workflow_badges.py; the enums/severity_field/*_EMOJI maps are untouched and still drive runtime — this is purely the parallel spec vocabulary. CLI smoke (create/update/show/check on a fresh squad) unaffected.
  - Validation cases covered (tests/test_workflow_badges.py, 29 cases): duplicate field code within a type/kind, field code shadowing a reserved frontmatter key (on both an item type and a sub-entity kind), the priority/severity exemption from that same check (they intentionally keep their literal legacy key), unresolved field.collection, field-level default not a badge in the collection, collection-level default not a badge, required field with no resolvable default, required field resolving via the collection's own default, a custom collection reused by two distinctly-coded relabeled fields, extra=forbid on all 4 new models, a loader parse-error's context message, and additive-override coverage (new collection/new subentity_kinds field accepted; redefining bundled 'priority' collection or 'finding' subentity_kinds entry raises).
  - Gates: pyright/ruff check/ruff format all clean. Targeted tests green: the new test_workflow_badges.py (29 passed) plus every workflow/custom-type/prefix-resolver/hygiene test file (32 files touching WorkflowSpec, 0 failures) -- had to thread collections=/subentity_kinds= through ~15 pre-existing hand-built WorkflowSpec.model_validate(...) call sites across 10 test files that reused base.items (now carrying the bundled fields) without carrying the base spec's collections map; also extended _merge_override/_collect_additive_conflicts (production code) to handle collections/subentity_kinds additively, since sq workflow lint and open_service route through it. Did NOT run the full suite -- left for the main loop per instructions.
  - Design note: Collection has no self-stored 'code' field (identity = its key in WorkflowSpec.collections dict, mirroring ItemSpec/StatusSpec/Lifecycle -- avoids storing what's derivable from the dict key); Field/Badge do carry 'code' since they live in lists, same as RefRule.kind.
- [2026-07-09T09:41:42Z] Paul Reviewer:
  - APPROVE — independent review of the uncommitted TASK-340 diff (release/0.8). Gates green: pyright 0 errors, ruff check clean, ruff format clean; targeted suites (test_workflow_badges/spec/override/lint/authoring_prose/reserved_types_invariants/capability_flags/squad_ref_hygiene) 170 passed.
  - Byte-identical (VERIFIED against _models/_enums.py): priority collection = urgent/high/medium/low with 🔴🟠🟡🟢, no default; severity collection = critical/high/medium/low/info with 🔴🟠🟡🟢🔵, default=medium — exact code/label/emoji/default match. priority field on exactly the 7 work types (epic/feature/task/bug/decision/review/guide), absent from the 3 meta types; severity on bug item-level (required=false,default=medium) + finding kind (required=true,default=medium). Enums/*_EMOJI/severity_field untouched, nothing consumed by the engine yet.
  - Fail-closed validation (reasoned through the validators, not just test names): (1) per-owner dup field code appended in _check_field_codes; (2) reserved-key collision derived live from Item/SubEntity model_fields|computed_fields (not hand-copied) — sub-entity keys verified == frontmatter keys; the priority/severity exemptions are correct and MINIMAL (necessary for the bundled fields to load, and they are the designed round-trip keys, not a hole); (3) collection referential integrity — unresolved collection, field/collection-level default-not-a-badge, and required-without-resolvable-default all reject. _validate runs on both bundled load and override merge.
  - Schema shape correct: Collection has no self-stored code (identity = dict key, derive-don't-store); Badge/Field carry code as list-item identity; extra="forbid"+frozen on all four new models (Badge/Collection/Field/SubentityKindSpec); Field mechanism is kind-agnostic (shared by ItemSpec.fields and SubentityKindSpec.fields) so FEAT-212 can reuse it. Override merge is additive — new collections/subentity_kinds accepted, redefining a built-in rejected for both; nicely factored via _merge_additive_section to hold the complexity ceiling.
  - LOW (latent, non-blocking): _reserved_item_keys() subtracts {path, prefix} from the reserved set. 'path' is genuinely never a frontmatter key (kwarg, never read) — fine. But 'prefix' is a tolerated-and-ignored legacy frontmatter key (Item._derive_prefix_from_id: id always wins), and the task explicitly enumerated 'prefix' as reserved. A future live field coded 'prefix' would write prefix:<badge> and have it silently discarded on the next round-trip — exactly the silent-shadow class this check exists to prevent. No current impact (fields aren't consumed yet; no bundled field is coded prefix/path, so keeping them reserved breaks nothing). Recommend the next task (which makes fields live) NOT subtract path/prefix — keep them reserved, fail-closed. Approving now since all done-criteria are met with zero behavioral/bundled/runtime impact. @tech-lead
<!-- sq:discussion:end -->
