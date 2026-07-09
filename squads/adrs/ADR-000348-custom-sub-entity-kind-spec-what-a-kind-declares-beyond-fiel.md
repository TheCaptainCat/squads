---
id: ADR-348
sequence_id: 348
type: decision
title: 'Custom sub-entity kind spec: what a kind declares beyond fields'
status: Accepted
author: architect
refs:
- FEAT-212
- ADR-323:depends-on
- ADR-274
- REV-337:addresses
created_at: '2026-07-09T21:18:55Z'
updated_at: '2026-07-09T21:22:56Z'
---
<!-- sq:body -->
## Context

Post-EPIC-325 the sub-entity system is only *partially* spec-driven. `WorkflowSpec.subentity_kinds:
dict[str, SubentityKindSpec]` exists, but `SubentityKindSpec` carries **only `fields`** (the ADR-323
badge bindings). Everything else about a sub-entity kind is still hardwired to the three built-ins
(story/subtask/finding) by naming convention or by static per-kind tables:

- **Machine binding is a naming convention.** `WorkflowSpec.subentity_workflow/initial/
  can_transition/subentity_completion` all do `self.lifecycles[kind]` — the machine must be a
  lifecycle *named after the kind*. This is undocumented magic and forces the story/subtask machine
  to be **duplicated** verbatim in `default_workflow.toml` (`[lifecycles.story]` == `[lifecycles.
  subtask]`). Contrast the type axis, where `ItemSpec.lifecycle` names the machine explicitly (epic/
  feature/task all → `"work"`).
- **Completion binds by a global per-status-NAME flag.** `StatusSpec.completion` (TASK-330) marks the
  done-toggle target. `_check_completion_status` requires exactly one `completion` status reachable in
  each kind's machine. REV-337 **F3** flagged this as the wrong shape for custom kinds: the flag is
  keyed by status *name* across all lifecycles, so two kinds that share a status name but want
  different completion semantics (or a kind reusing `Done` for a non-completion meaning) is
  unrepresentable. F3 is an explicit forward-note to this feature.
- **Static per-kind code tables**, all keyed by the three literal kinds:
  `_cli/_items.py::_SUBENTITY_PLURAL` (kind→plural; the last per-type vocabulary artifact, whose
  retirement FEAT-212 owns), `_cli/_items.py::_SUB_COLS` and `_discussion.py::_SUMMARY_COLS` +
  `_summary_cells` (list/summary columns — and the two disagree today: the CLI story table shows a
  `Story` column the body summary doesn't), `_services/_base.py::SUBENTITY_CONTAINER` (kind→marker),
  `_discussion.py::_LOCAL_ID_PREFIX` (kind→`US`/`ST`/`F`) and `_PLACEHOLDER` (kind→scaffold prose).
- **CLI verbs are hand-written per kind.** `_register_add`/`_register_update` are three closures with
  kind-specific flags (story: none; subtask: `--story`; finding: `--severity`), each calling a named
  `svc.add_story/add_subtask/add_finding`; the list/get/body verbs `getattr` the per-kind
  `list_<plural>`/`get_<kind>`/`set_<kind>_body` wrappers.
- **Parent binding already exists** on the type side: `ItemSpec.subentity_kind: str | None` is the
  forward edge type→kind (1:1). `SUBENTITY_PARENT`/`SUBENTITY_KIND` are built by *inverting* it — but
  pinned to the **bundled** spec, so a project-declared kind is invisible to them.

The goal (FEAT-212 / EPIC-280): a custom type `incident` declares an `action` kind with its own
machine and a summary table, and `sq incident <n> add-action "…"` works with **no code change**.

## Decision

Give `SubentityKindSpec` the declarations a kind genuinely needs, make everything else **derived**,
and drive the CLI/rendering/service generically off the resolver. The field mechanism stays exactly
ADR-323's — sub-entity fields are the same `Field`/`Collection`/`Badge` model, resolved through the
same `_badges.py` helpers, never a fork.

### 1. `SubentityKindSpec` schema — what is stored vs. derived

Stored (each earns its place — none is derivable from existing structure):

| Field | Type | Purpose | Retires |
|---|---|---|---|
| `fields` | `list[Field]` | ADR-323 badge bindings (already present) | — |
| `lifecycle` | `str` | Explicit machine reference, mirroring `ItemSpec.lifecycle` | the kind-name==lifecycle-name convention |
| `completion` | `str` | The done-toggle target status *within this kind's machine* | global `StatusSpec.completion` (resolves REV-337 F3) |
| `plural` | `str` | CLI list verb **and** the container marker name | `_SUBENTITY_PLURAL`, `SUBENTITY_CONTAINER` |
| `local_prefix` | `str` | Local-id prefix (`US`/`ST`/`F`/…) | `_LOCAL_ID_PREFIX` |
| `placeholder` | `str \| None = None` | Optional scaffold prose; generic fallback derived from the kind name | `_PLACEHOLDER` |
| `maps_parent_story` | `bool = False` | Capability: this kind maps to a parent story (drives `--story` + the `Story` column) | the `kind == "subtask"` literal branches |

**Deliberately NOT stored — derived instead** (questioning each per "don't store what you can
derive"):

- **Singular / kind name** = the `subentity_kinds` dict key. The `add-<kind>` verb and "operate on a
  `{kind}`" help both use the key. No `singular` field.
- **Initial status** = `lifecycle.initial`. No stored default.
- **Container marker name** = `plural`. Today's markers are literally `stories`/`subtasks`/`findings`
  — identical to the plurals — so one field serves both the list-verb name and the container tag.
- **Parent type(s)** = *inversion* of `ItemSpec.subentity_kind` (invariant #4, forward edges only).
  `SUBENTITY_PARENT`/`SUBENTITY_KIND` stop being pinned to the bundled spec and are computed from the
  **active** spec. No `carried_by`/`parents` list on the kind.
- **Summary / list columns** = a fixed base (`local_id`, Status, Assignee, Title) + **one column per
  declared `field`** (headed by the field `label`, e.g. Severity) + a `Story` column iff
  `maps_parent_story`. Not a stored column list — this is exactly ADR-323's "derive columns from
  declared fields" applied to the sub-entity axis, and it unifies the CLI/body column drift noted
  above onto one derivation.

### 2. Machine + completion move onto the kind (retire the conventions)

Bind the machine with an explicit `lifecycle` field, symmetric with `ItemSpec.lifecycle`. The
lifecycle name is a genuine binding choice (not derivable — `ItemSpec` stores it for the same reason),
so this is not redundant storage; the kind-name==lifecycle-name convention was the anomaly. Benefit:
the bundled default may collapse the duplicated story/subtask machines onto one lifecycle
(behaviour-identical), and `WorkflowSpec.subentity_*` accessors read `lifecycles[kind_spec.lifecycle]`
instead of `lifecycles[kind]`.

Move the completion designation from a global `StatusSpec.completion` flag to a per-kind
`completion: str` naming the done-target status *inside that kind's own machine*. This directly
resolves **REV-337 F3**: completion becomes per-machine, so a shared status name can mean "done" in
one kind and not another, and `Done` can be reused freely. `subentity_completion(kind)` becomes an
O(1) `subentity_kinds[kind].completion` lookup instead of a scan for the flagged status.
`StatusSpec.completion` and the "exactly one completion status per machine" scan are retired; the
new invariant is "`completion` names a reachable, non-initial state of the kind's `lifecycle`"
(see §6). Bundled default: `[subentity_kinds.subtask].completion = "Done"`,
`.story.completion = "Done"`, `.finding.completion = "Fixed"` — same targets TASK-330 encoded, just
relocated. This is a deliberate, ADR-blessed refinement of TASK-330's interim mechanism, which
REV-337 F3 explicitly anticipated; it is a spec-schema move only (no item-data migration).

### 3. Fields are ADR-323's `Field`, unforked

Sub-entity fields reuse ADR-323's `Field`/`Collection`/`Badge` model as-is (already true for
`SubentityKindSpec.fields`). Resolution goes through the same `_badges.py` primitives
(`resolve_collection`, `badge_render`, `parse_badge_code`) the item axis uses. The finding
`severity` column is simply the generic field column for the `severity` field bound to the `severity`
collection — no `severity`-special-casing survives in the sub-entity renderers. A custom kind may bind
any collection under any field code, relabeled per ADR-323's field-`label` mechanism.

### 4. Storage & round-trip

`SubEntity` keeps its typed `severity` slot as the byte-identical storage for the finding `severity`
field (frontmatter round-trips unchanged), and gains a generic field-code→badge-code store for any
*other* declared field on a custom kind — the direct analog of Item's ADR-323 `badge_value`/
`set_badge_value` (which store the attribute for priority/severity and `extra[code]` for other
fields). No parallel storage model: the same badge-code-is-the-authoritative-stored-value discipline
(ADR-323 §4), so `--json`/no-spec reads work and label/emoji resolve at render time with the graceful
`_DEFAULT_BADGE` fallback.

### 5. Dynamic CLI derivation (approach)

`build_item_app(item_type)` already resolves the active spec at call time and is invoked lazily per
type by `_CustomTypeGroup.get_command` (custom types) and statically for built-ins. Extend it so the
sub-entity surface is built from `spec.item_subentity_kind(item_type)` → the kind's
`SubentityKindSpec`:

- **`add-<kind>`** — base flags (title, `--assignee`, `-m/--message`, `--file`, `--json`) + one
  `--<field-code>` option per declared field (ADR-323-derived, same as the item-level field flags) +
  `--story` iff `maps_parent_story`. Replaces the three hand-written `_register_add` closures.
- **`<plural>`** list verb + the nested `<kind> <n> …` subgroup (show/update/body/comment) built the
  same generic way; `update` derives its `--<field-code>` flags identically.
- All verbs call **kind-parameterized generic service methods** (the existing `_add_block`/
  `_list_blocks`/`_get_block`/`_update_block`/`_set_block_body`/`_set_block_status`, promoted to a
  public kind-taking surface) instead of `getattr(svc, f"…{kind}")` on per-kind wrappers. The
  per-kind named wrappers (`add_story`, `get_finding`, …) and the `vulture` `ignore_names` entries
  that cover their dynamic dispatch are no longer needed for CLI dispatch.
- `_LOCAL_ID_PREFIX`/`_PLACEHOLDER`/`SUBENTITY_CONTAINER`/`_SUB_COLS`/`_SUMMARY_COLS`/
  `_SUBENTITY_PLURAL` all read from the resolver (`local_prefix`, `placeholder`, `plural`, derived
  columns) — the last static per-type vocabulary artifact is deleted, per Catherine's ownership note
  and ADR-266's resolver pattern.

### 6. Validation / `sq workflow lint` (AC5)

Spec-load validation (run identically by `sq workflow lint`, which surfaces every error) already
enforces via `_check_lifecycle_statuses` that a lifecycle's initial/transition statuses are all
declared — so a kind's machine can never reference an undeclared status. Extend the per-kind checks:

- The kind's `lifecycle` names a declared lifecycle (mirrors `ItemSpec.lifecycle` validation).
- `completion` names a status that is a **reachable, non-initial** state of that lifecycle — the
  rewritten `_check_completion_status`, now iterating declared `subentity_kinds` rather than deriving
  kinds from `ItemSpec.subentity_kind`. This is the AC5 catch: a custom kind whose done-target (or
  any machine status) falls outside its own machine's status vocabulary fails closed at load.
- Field-code uniqueness/reserved-key and field→collection referential integrity already cover
  sub-entity kinds (`_iter_field_owners` yields them) — unchanged.
- `plural` and `local_prefix` are non-empty and unique across kinds (a duplicate `plural` would
  collide the list verb / container marker; a duplicate `local_prefix` would collide local ids).

### 7. Story-mapping stays a bounded built-in

The subtask→user-story mapping (`SubEntity.story`, `--story`, the `Story` column,
`_validate_subtask_story`'s check against the grandparent feature's stories) is a deep structural
relation specific to the feature→task→story spine. Generalizing it to arbitrary custom kinds is a
**non-goal this pass**. It is gated by the declared `maps_parent_story` capability flag (bundled:
true for `subtask` only) so the CLI/columns derive `--story`/`Story` from a declared capability rather
than a `kind == "subtask"` literal — but its *semantics* (validation against the mapped story) are
unchanged and remain wired to the built-in story kind.

## Blast radius

- **`_workflow/_models.py`** — `SubentityKindSpec` gains `lifecycle`/`completion`/`plural`/
  `local_prefix`/`placeholder`/`maps_parent_story`; `StatusSpec.completion` removed;
  `_check_completion_status` rewritten (per-kind, reachable-non-initial); new lifecycle-ref +
  plural/local_prefix uniqueness checks; `subentity_workflow/initial/can_transition/completion` read
  `kind_spec.lifecycle`.
- **`default_workflow.toml`** — `[subentity_kinds.*]` gains the new keys; the two `completion = true`
  flags move out of `[statuses.*]`; story/subtask lifecycles may dedupe. Golden regenerates
  (structure additive; runtime behaviour byte-identical).
- **`_services/_base.py`** — `SUBENTITY_PARENT`/`SUBENTITY_KIND` computed from the active spec;
  `SUBENTITY_CONTAINER` derived from `plural`.
- **`_services/_subentities.py`** — generic `_*` methods become the public kind-taking surface;
  per-kind wrappers dropped from the CLI path; `subentity_completion` O(1).
- **`_cli/_items.py`** — `_SUBENTITY_PLURAL`/`_SUB_COLS` deleted; `_register_add`/`_register_update`/
  the list+subgroup builders become generic field-driven.
- **`_discussion.py`** — `_LOCAL_ID_PREFIX`/`_PLACEHOLDER`/`_SUMMARY_COLS`/`_summary_cells` become
  resolver/field-driven column derivation.
- **`vulture` config** — the per-kind `add_*/get_*/…` `ignore_names` entries drop out with the
  wrappers.

## Migration & compatibility

A no-override squad behaves identically (AC4): same machines, same columns, same local-id prefixes,
same scaffold prose, same finding-severity storage. The only change is **spec-schema** (the
`[subentity_kinds.*]` keys + the `completion` relocation) — no `.md` item-data migration is required,
so this rides the existing 0.8 schema line without an item-file migration step (assess whether the
spec-schema addition alone warrants a `SCHEMA_VERSION` touch; item frontmatter is untouched). Custom
per-field values on custom kinds serialize exactly as ADR-323 already defined for items.

## Risks

- **Churn on recently-approved code.** Retiring `StatusSpec.completion` removes TASK-330 code + its 5
  regression tests (REV-337 F1). Mitigated: REV-337 F3 explicitly deferred this decision here, and
  the per-kind model is strictly more expressive; the tests re-home onto the per-kind validator. This
  is the single decision that touches blessed work — called out for the reviewer/operator.
- **`plural` doubling as the container marker** couples the CLI list-verb name to the on-disk marker
  tag. Acceptable: they are identical today and a marker rename would be a data migration anyway;
  documented so authors know the plural names a persisted marker.
- **Golden churn** on `default_workflow.toml` structure (not behaviour) — expected and covered by the
  golden-lock regeneration, same as every prior spec-schema addition.

## Options considered

- **Recommended (above)** — explicit `lifecycle` + per-kind `completion` + minimal stored vocab
  (`plural`/`local_prefix`/optional `placeholder`/`maps_parent_story`), everything else derived
  (singular/initial/container/parents/columns/field-flags). Symmetric with the type axis, resolves
  F3, kills every static per-kind table, byte-identical bundled behaviour.
- **Rejected — keep the kind-name==lifecycle convention** (no `lifecycle` field): saves one field but
  keeps undocumented magic, forces the story/subtask machine duplication, and is asymmetric with
  `ItemSpec`. The name is a genuine binding choice, so making it explicit is correct, not redundant.
- **Rejected — keep global `StatusSpec.completion`**: leaves the per-status-name coupling REV-337 F3
  flagged; a custom kind reusing a status name for a different completion meaning is unrepresentable.
- **Rejected — store the column list / singular / parent-types on the kind**: redundant with derivable
  structure (fields drive columns, the dict key is the singular, `ItemSpec.subentity_kind` is the
  forward parent edge). Violates "don't store what you can derive."
- **Rejected — generalize story-mapping to arbitrary kinds now**: out of scope (FEAT-212 non-goal);
  its semantics are tied to the feature→task→story spine and would balloon this feature.

## Relationships

- **Consumes ADR-323** (badge collections/fields) — sub-entity fields are the same model + `_badges.py`
  helpers, unforked; addresses ADR-323's own risk note that the sub-entity field mechanism must not be
  forked from the item one.
- **Resolves REV-337 F3** — per-machine completion designation replaces the global per-status-name flag.
- **Implements ADR-274** (F6 split) scope for the custom-sub-entity-kinds half, including the
  `_SUBENTITY_PLURAL` retirement via the ADR-266 resolver pattern.
- **Follows ADR-322** — applies the "spec is the sole vocabulary" + dynamic-CLI-from-spec discipline
  to the sub-entity axis; leaves `Status` structure untouched.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-09T21:22:56Z] Pierre Chat:
  - Accepted. The StatusSpec.completion retirement (churning TASK-330's blessed code onto the per-kind completion validator) is explicitly approved — per-kind completion is the right shape and REV-337 F3 deferred exactly this decision here. Proceed on the recommended design.
<!-- sq:discussion:end -->
