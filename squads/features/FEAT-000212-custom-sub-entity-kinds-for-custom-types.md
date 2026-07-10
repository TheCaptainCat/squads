---
id: FEAT-212
sequence_id: 212
type: feature
title: Custom sub-entity kinds for custom types
status: Done
parent: EPIC-280
author: product-owner
refs:
- FEAT-210:depends-on
- FEAT-211:depends-on
- FEAT-327:depends-on
subentities:
- local_id: US1
  title: As a project admin, I want to define custom sub-entity kinds for my custom
    types in TOML
  status: Todo
- local_id: US2
  title: As a project admin, I want sq migrate rename-type to safely rename a built-in
    type across my whole squad
  status: Cancelled
created_at: '2026-06-25T13:21:20Z'
updated_at: '2026-07-10T00:26:05Z'
---
<!-- sq:body -->
## What this delivers

Today a type's `subentity_kind` is a single field selecting one of three
built-in kinds (story/subtask/finding). This feature lets a custom type
declare a **brand-new** sub-entity kind with its own state machine and
summary columns, mirroring F2's de-typing but on the sub-entity axis.

A team that adds an `incident` type will be able to declare an `action`
sub-entity kind with its own `Open → InProgress → Resolved` machine, and get
`sq incident <n> add-action "…"` plus a summary table rendered from the
declared columns — without any code change.

## Scope

- Extend `WorkflowSpec` with `subentity_kinds: dict[str, SubentityKind]` —
  each kind declares its machine, summary columns, and the parent type(s)
  that carry it.
- Make the `_cli/_items.py` / `_common.py` `_SUBENTITY` map spec-driven;
  `add-<kind>` CLI verbs are built dynamically from the spec for each type
  that declares a custom sub-entity kind.
- `_discussion.py` summary rendering and `_print_subentity_summary` read
  column definitions from the spec instead of hardcoded per-kind logic.
- All sub-entity mutations (`update`, `body`, `comment`) route through the
  spec for kind resolution.
- **Owns retiring `_SUBENTITY_PLURAL`** (`_cli/_items.py`) — the last static
  per-type vocabulary artifact. ADR-266 established the `Item.prefix` +
  reserved-vocab resolver pattern and retired the prefix/folder/alias/meta
  statics in the FEAT-210 corrective; `_SUBENTITY_PLURAL` was deliberately
  deferred to this feature because it needs this feature's `subentity_kinds`
  schema addition (sub-entity plural vocab lives there now). Add a
  `subentity_plural` accessor to the resolver and delete `_SUBENTITY_PLURAL`.
  op-pierre confirmed this boundary.

## Dependencies

Requires F4 (FEAT-210, Done) for custom types and F5 (FEAT-211,
InProgress) for custom statuses — a custom sub-entity kind's machine needs
the same custom-status plumbing as a top-level type's machine. Do not start
until F5 lands.

## Non-goals

- Rich per-role playbook sections for custom sub-entity kinds (stretch goal
  beyond this feature).

## Acceptance criteria

1. A custom type can declare a new sub-entity kind with its own machine;
   `sq <type> <n> add-<kind> "…"` works; the summary table renders with the
   declared columns.
2. Sub-entity mutation verbs (`update`, `body`, `comment`) resolve the kind
   from the spec for both built-in and custom sub-entity kinds.
3. `_SUBENTITY_PLURAL` is deleted; plural vocabulary for every sub-entity
   kind (built-in and custom) comes from the `subentity_plural` resolver
   accessor.
4. The F1 golden test and all existing tests remain green (built-in
   story/subtask/finding kinds unchanged).
5. `sq workflow lint` catches a custom sub-entity kind whose machine
   references a status not in the type's status vocabulary.

## Provenance

Split from the former FEAT-212 ("Custom sub-entity kinds + vocabulary
rename migrations") per ADR-274 (Accepted) — this feature keeps the
custom-sub-entity-kinds half; the rename-migrations half moved to a new
sibling feature under EPIC-280.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 212 add-story "As a <role>, I want … so that …"`; track with `sq feature 212 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a project admin, I want to define custom sub-entity kinds for my custom types in TOML |
| US2 | Cancelled |  | As a project admin, I want sq migrate rename-type to safely rename a built-in type across my whole squad |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a project admin, I want to define custom sub-entity kinds for my custom types in TOML

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a project admin, I want to declare a custom sub-entity kind (e.g. `action` on an `incident` type) in `.overrides/workflow.toml` with its own machine and summary columns, so that my custom types can have structured nested work items beyond reusing the built-in story/subtask/finding kinds.

**Acceptance:** `sq incident <n> add-action "…"` works for a type that declares `subentity_kind = 'action'`; the summary table renders with declared columns; `add-action` CLI verb is built dynamically from the spec.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a project admin, I want sq migrate rename-type to safely rename a built-in type across my whole squad

<!-- sq:story:US2:head -->
**Status:** ⚫ Cancelled
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
**Moved.** This story's scope (safe rename migrations for built-in types/statuses) moved to a new sibling feature under EPIC-280, per ADR-274's F6 split. See that feature's US1 for the current spec of this work. Cancelled here, not deleted, to preserve history.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-01T08:27:49Z] Catherine Manager:
  - Ownership note (from the FEAT-210/REV-265/ADR-266 work): FEAT-212 owns retiring _SUBENTITY_PLURAL (_cli/_items.py) — the last static per-type vocabulary artifact. ADR-266 established the Item.prefix + reserved-vocab resolver pattern and retired the prefix/folder/alias/meta statics in the FEAT-210 corrective; _SUBENTITY_PLURAL was deliberately deferred here because it needs FEAT-212's subentity_kinds schema addition (sub-entity plural vocab). When scoped, add a subentity_plural accessor to the resolver and delete _SUBENTITY_PLURAL. op-pierre confirmed this boundary.
- [2026-07-07T14:40:07Z] Nina Product:
  - Must be re-baselined against the post-322/323 world before dispatch (see EPIC-325): specifically it should consume ADR-323's shared Field schema for sub-entity fields (FEAT-327) rather than fork its own field model. Scope otherwise unchanged for now.
- [2026-07-09T21:13:56Z] Catherine Manager:
  - Design pass kicked off before dispatch (op-pierre greenlit): SubentityKindSpec currently carries only `fields` — the machine + summary-columns half needed for a genuinely custom kind isn't in the model yet. Robert to draft an ADR on what a custom sub-entity kind must declare (schema shape + dynamic add-<kind> derivation + _SUBENTITY_PLURAL retirement), re-baselined on ADR-323's Field schema. Implementation stays gated on that ADR.
- [2026-07-09T21:20:56Z] Robert Architect:
  - Design ADR drafted: ADR-348 (Proposed) — what a custom sub-entity kind must declare beyond ADR-323 fields. Headlines: (1) SubentityKindSpec gains explicit `lifecycle` (mirror ItemSpec, retires the kind-name==lifecycle magic + the story/subtask machine dup) + per-kind `completion` status (retires global StatusSpec.completion — resolves REV-337 F3) + `plural`/`local_prefix`/optional `placeholder`/`maps_parent_story`. (2) Everything else is DERIVED, not stored: singular=dict key, initial=machine.initial, container marker=plural, parent-types=inversion of ItemSpec.subentity_kind, and summary/CLI columns + --<field> flags = ADR-323 fields (severity column is just the generic field column). (3) _SUBENTITY_PLURAL + _SUB_COLS/_SUMMARY_COLS + _LOCAL_ID_PREFIX + SUBENTITY_CONTAINER all retire; CLI verbs derive generically in build_item_app via kind-parameterized generic service methods. AC5 lint: extend _check_completion_status (per-kind, reachable-non-initial) + lifecycle-ref check. Left Proposed for op-pierre to read before accepting. One flag for you: it retires TASK-330's StatusSpec.completion (blessed/tested work) — deliberate per F3, called out in the ADR risks.
- [2026-07-10T00:25:41Z] Catherine Manager:
  - FEAT-212 complete. All tasks landed and committed: TASK-349 (SubentityKindSpec schema foundation), 350 (per-kind completion, resolving REV-337 F3), 351 (service-layer spec-derived maps + public kind-taking surface), 352 (spec/field-driven discussion rendering + F1 container-heading fix), 353 (generic CLI surface, _SUBENTITY_PLURAL deleted, custom-kind end-to-end), 361 (ADR-348 §4 generic sub-entity field store — the breakdown gap), 354 (vulture reconcile + AC5 lint + dead-code deletion). Realizes ADR-348 in full. Reviewer sign-off: acceptance-complete and byte-identical for built-ins; custom kinds work end-to-end with settable custom fields, no code change. Two display-only deferrals tracked on REV-360 (print_subentity severity-only meta line) for the FEAT-336 pass. US2 was already Cancelled (moved to FEAT-281).
<!-- sq:discussion:end -->
