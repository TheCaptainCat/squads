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
- ADR-738
- ADR-1007
created_at: '2026-07-09T21:18:55Z'
updated_at: '2026-10-25T21:25:33Z'
---
<!-- sq:body -->
## Context

A sub-entity kind (story, subtask, finding, or one a squad declares) needs more than the badge
fields ADR-323 gives it: a state machine, a done-toggle target, CLI vocabulary (its list verb and
local-id prefix), scaffold prose, and summary columns. Hardwiring those to the three bundled kinds
takes the form of naming conventions (a machine looked up as the lifecycle named after the kind,
which forces identical story and subtask machines to be declared twice), a completion flag keyed by
status *name* across every lifecycle (REV-337 F3: two kinds sharing a status name with different
completion meanings are unrepresentable), static per-kind tables (plural, columns, container
marker, local-id prefix, placeholder), and hand-written per-kind CLI verbs. The type side already
carries the forward edge type→kind (`ItemSpec.subentity_kind`).

The goal (FEAT-212 / EPIC-280): a custom type `incident` declares an `action` kind with its own
machine and summary table, and `sq incident <n> add-action "…"` works with **no code change**.

## Decision

`SubentityKindSpec` carries the declarations a kind genuinely needs, everything else is
**derived**, and the CLI, rendering and service run generically off the spec. The field mechanism stays exactly
ADR-323's — sub-entity fields are the same `Field`/`Collection`/`Badge` model, resolved through the
same `_badges.py` helpers, never a fork.

### 1. `SubentityKindSpec` schema — what is stored vs. derived

Stored (each earns its place — none is derivable from existing structure):

| Field | Type | Purpose |
|---|---|---|
| `fields` | `list[Field]` | ADR-323 badge bindings |
| `lifecycle` | `str` | Explicit machine reference, mirroring `ItemSpec.lifecycle` |
| `completion` | `str` | The done-toggle target status *within this kind's machine* |
| `plural` | `str` | CLI list verb **and** the container marker name |
| `local_prefix` | `str` | Local-id prefix (`US`/`ST`/`F`/…) |
| `placeholder` | `str \| None = None` | Optional scaffold prose; a generic one derived from the kind name otherwise |
| `maps_parent_story` | `bool = False` | Capability: this kind maps to a parent story (drives `--story` + the `Story` column) |

**Deliberately NOT stored — derived instead** (questioning each per "don't store what you can
derive"):

- **Singular / kind name** = the `subentity_kinds` dict key. The `add-<kind>` verb and "operate on a
  `{kind}`" help both use the key. No `singular` field.
- **Initial status** = `lifecycle.initial`. No stored default.
- **Container marker name** = `plural` (`stories`/`subtasks`/`findings`), so one field serves both
  the list-verb name and the container tag.
- **Parent type(s)** = *inversion* of `ItemSpec.subentity_kind` (invariant #4, forward edges only),
  computed from the **active** spec. No `carried_by`/`parents` list on the kind.
- **Summary / list columns** = a fixed base (`local_id`, Status, Assignee, Title) + **one column per
  declared `field`** (headed by the field `label`, e.g. Severity) + a `Story` column iff
  `maps_parent_story`. Not a stored column list — ADR-323's "derive columns from declared fields"
  applied to the sub-entity axis, one derivation shared by the CLI table and the body summary.

### 2. Machine and completion live on the kind

The machine is bound by an explicit `lifecycle` field, symmetric with `ItemSpec.lifecycle`. The
lifecycle name is a genuine binding choice, not derivable, so this is not redundant storage. The
bundled story and subtask kinds share one `subentity` lifecycle, and the `WorkflowSpec.subentity_*`
accessors read `lifecycles[kind_spec.lifecycle]`.

Completion is a per-kind `completion: str` naming the done-target status *inside that kind's own
machine*, so a shared status name can mean "done" in one kind and not another. No status carries a
completion flag and there is no "exactly one completion status per machine" rule: two kinds sharing
a lifecycle may name different targets. `subentity_completion(kind)` is an O(1)
`subentity_kinds[kind].completion` lookup. The invariant is that `completion` names a reachable,
non-initial state of the kind's `lifecycle` (§6). Bundled: story and subtask complete at `Done`,
finding at `Fixed`.

### 3. Fields are ADR-323's `Field`, unforked

Sub-entity fields reuse ADR-323's `Field`/`Collection`/`Badge` model as-is
(`SubentityKindSpec.fields`). Resolution goes through the same `_badges.py` primitives
(`resolve_collection`, `badge_render`, `parse_badge_code`) the item axis uses. The finding
`severity` column is the generic field column for the `severity` field bound to the `severity`
collection — no `severity`-special-casing survives in the sub-entity renderers. A custom kind may bind
any collection under any field code, relabeled per ADR-323's field-`label` mechanism.

### 4. Storage & round-trip

`SubEntity` keeps a typed `severity` slot for the finding `severity` field and stores any *other*
declared field's badge code in its `extra` mapping, keyed by field code. (On an item, every field is
a top-level frontmatter key under its code, per ADR-1007.) The discipline is ADR-323 §4's: the badge
code is the authoritative stored value, so `--json` and no-spec reads work and label/emoji resolve
at render time with a neutral fallback.

### 5. Dynamic CLI derivation

`build_item_app(item_type)` resolves the spec at call time and is invoked statically for bundled
types and lazily by `_CustomTypeGroup.get_command` for override-added ones (ADR-263). It builds the
sub-entity surface from `spec.item_subentity_kind(item_type)` → the kind's `SubentityKindSpec`:

- **`add-<kind>`** — base flags (title, `--assignee`, `--status`, `--deferred-to`,
  `-m/--message`, `--file`, `--json`) + one `--<field-code>` option per declared field (the kind is
  known when its type's app is built, so these flags are generated) + `--story` iff
  `maps_parent_story`.
- **`<plural>`** list verb + the nested `<kind> <n> …` subgroup (show/update/body/comment) built the
  same generic way; `update` derives its `--<field-code>` flags identically.
- All verbs call the **kind-parameterized service surface** (`add_block`/`list_blocks`/
  `get_block`/`update_block`/`set_block_body`/`set_block_status`). The per-kind named wrappers
  (`add_story`, `update_finding`, …) are thin delegators kept for test call sites, not used by the
  CLI.
- Local-id prefixes, placeholders, container markers, columns and plurals all come from the kind's
  declaration; no static per-kind table exists in code.

### 6. Validation / `sq workflow lint` (AC5)

Spec-load validation (run identically by `sq workflow lint`, which surfaces every error) enforces
that a lifecycle's initial and transition statuses are all declared, so a kind's machine can never
reference an undeclared status. The per-kind checks add:

- The kind's `lifecycle` names a declared lifecycle (mirrors `ItemSpec.lifecycle` validation).
- `completion` names a status that is a **reachable, non-initial** state of that lifecycle
  (`check_completion_status`, iterating the declared `subentity_kinds`). This is the AC5 catch: a
  custom kind whose done-target (or any machine status) falls outside its own machine's status
  vocabulary fails closed at load.
- Field-code uniqueness/reserved-key and field→collection referential integrity already cover
  sub-entity kinds (`_iter_field_owners` yields them).
- `plural` and `local_prefix` are non-empty and unique across kinds (a duplicate `plural` would
  collide the list verb / container marker; a duplicate `local_prefix` would collide local ids).

### 7. Story-mapping stays a bounded built-in

The subtask→user-story mapping (`SubEntity.story`, `--story`, the `Story` column,
`_validate_subtask_story`'s check against the grandparent feature's stories) is a deep structural
relation specific to the feature→task→story spine. Generalizing it to arbitrary custom kinds is a
**non-goal**. It is gated by the declared `maps_parent_story` capability flag (bundled:
true for `subtask` only) so the CLI/columns derive `--story`/`Story` from a declared capability rather
than a `kind == "subtask"` literal — but its *semantics* (validation against the mapped story) are
unchanged and remain wired to the built-in story kind.

## Compatibility

A no-override squad behaves as the bundled kinds declare: same machines, columns, local-id
prefixes, scaffold prose and finding-severity storage. The kind schema is spec vocabulary only;
item files carry no part of it, so it needs no item-data migration. Custom field values on a
custom kind serialize as §4 states.

## Risks

- **`plural` has three consumers**: the CLI list verb, the on-disk container marker tag, and the
  `sq workflow subentity-kinds --json` catalog (ADR-738), which publishes it with `local_prefix`,
  `completion`, `maps_parent_story`, the resolved container heading and the kind's `fields` so a
  client reads the list verb and marker name instead of guessing a pluralization. Renaming a
  `plural` renames a persisted marker (a data migration) and changes a published catalog value a
  client may join on; the spec-author and catalog docs say so. `plural` remains the single declared
  name.

## Options considered

- **Recommended (above)** — explicit `lifecycle` + per-kind `completion` + minimal stored vocab
  (`plural`/`local_prefix`/optional `placeholder`/`maps_parent_story`), everything else derived
  (singular/initial/container/parents/columns/field-flags). Symmetric with the type axis, resolves
  F3, no static per-kind table, bundled behaviour unchanged.
- **Rejected — the kind-name==lifecycle convention** (no `lifecycle` field): saves one field but is
  undocumented magic, forces duplicated story/subtask machines, and is asymmetric with `ItemSpec`.
- **Rejected — a global per-status completion flag**: the per-status-name coupling REV-337 F3
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
- **Implements ADR-274** (F6 split) scope for the custom-sub-entity-kinds half; a kind's plural is
  answered by `WorkflowSpec.subentity_plural(kind)`.
- **Follows ADR-322** — applies the "spec is the sole vocabulary" + dynamic-CLI-from-spec discipline
  to the sub-entity axis; leaves `Status` structure untouched.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-09T21:22:56Z] `op-pierre` Pierre Chat:
  - Accepted. The StatusSpec.completion retirement (churning TASK-330's blessed code onto the per-kind completion validator) is explicitly approved — per-kind completion is the right shape and REV-337 F3 deferred exactly this decision here. Proceed on the recommended design.
- [2026-08-03T08:48:38Z] `architect` Robert Architect:
  - Verified in force with nothing owed on substance: `SubentityKindSpec` carries `lifecycle`/`plural`/`local_prefix`/`placeholder`/`maps_parent_story`/`completion`, `StatusSpec.completion` is gone, `_check_completion_status` is per kind and called from `_validate`, and `maps_parent_story` is the one derivation for the Story column in both renderers.
  - Corrected three `default_workflow.toml` citations to the bundled spec at `src/squads/_specs/workflow.toml`. Section 2 already records its own end of the completion move properly, which is why this decision needed nothing more — it is the model the ADR-322 narrowing points back at.
- [2026-08-03T15:36:48Z] `architect` Robert Architect:
  - Widened in place, not narrowed: the risk note on `plural` doubling as the container marker now names a third consumer. ADR-738 publishes it on `sq workflow subentity-kinds --json` alongside `local_prefix`, `completion`, `maps_parent_story`, the resolved container heading and this kind's `fields`.
  - Nothing in this decision's model changes — `plural` is still the single declared name, and the derived-vs-stored split holds. What changes is reach: a rename now also moves a published catalog value. `placeholder` is deliberately left unpublished (content the engine writes, not vocabulary a client resolves). Linked `related` both ways.
- [2026-10-25T21:25:33Z] `architect` Robert Architect:
  - 2026-10-25 audit: partly stale, body edited to the present tense; the kind schema is unchanged. Context now states the problem instead of the pre-implementation code (StatusSpec.completion, _SUBENTITY_PLURAL and the other static tables no longer exist). §2 states the shipped result (story and subtask share the subentity lifecycle). §5 corrected: the per-kind service wrappers are kept as test-only delegators and stay in vulture ignore_names (the body said they drop out). Folded the dated ADR-1007 note into §4 and the 2026-08-03 ADR-738 widening into Risks. Removed the Blast radius section, the TASK-330 churn risk and the schema-line planning.
<!-- sq:discussion:end -->
