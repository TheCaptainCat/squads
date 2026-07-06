---
id: ADR-323
sequence_id: 323
type: decision
title: 'Spec badges for priority/severity: reusable collections + relabeling fields'
status: Proposed
author: architect
refs:
- ADR-322:depends-on
- ADR-214
- ADR-232
created_at: '2026-07-07T10:00:07Z'
updated_at: '2026-07-07T12:40:16Z'
---
<!-- sq:body -->
## Context

ADR-322 makes the loaded workflow spec the **sole vocabulary authority** for item *types* and
*statuses* (both enums removed; the engine is generic over `spec.items` / `spec.workflow_for`). Two
flat presentation axes are still hardcoded in exactly the way those vocabularies used to be:

- **`src/squads/_models/_enums.py`** — `Priority` `StrEnum` (`urgent`/`high`/`medium`/`low`, lines
  81–95) with `PRIORITY_EMOJI`; `Severity` `StrEnum` (`critical`/`high`/`medium`/`low`/`info`, lines
  98–114) with `SEVERITY_EMOJI`; `DEFAULT_SEVERITY = Severity.MEDIUM` (line 116). Closed, code-defined
  vocabularies with a hardcoded emoji per code — the same shape as the retired `RESERVED_PREFIX` map.
- **`src/squads/_workflow/_models.py`** — `ItemSpec.severity_field: bool` (lines 130–131, "today: bug
  only") + `item_has_severity()` (lines 464–466) encode "which types carry severity" as a single
  boolean, and priority is not represented in the spec at all (implicitly global).

The operator wants these generalized into **reusable, spec-defined badge vocabulary** — the same
"spec is the sole vocabulary" philosophy applied to the last two hardcoded axes.

### Two settled operator constraints

1. **`Status` is NOT part of this model — leave it exactly as-is.** A status is a badge **plus a
   state machine**; the lifecycle is a real structural difference. Status badges are already
   spec-declared (`StatusSpec.badge`, resolved via `WorkflowSpec.status_badge()` with a graceful
   `_DEFAULT_BADGE` fallback) and the `Status` enum's removal is owned by ADR-322. This ADR
   generalizes only the **flat** axes (priority, severity, future custom ones).
2. **Badges are first-class, reusable spec vocabulary** — defined once, referenced by many.

### Where priority/severity are wired today (grep `priorit|severit` across `src/` — 21 files)

| Cluster (files) | What it does today |
|---|---|
| `_models/_enums.py` | `Priority`/`Severity` enums, `*_EMOJI` maps, `DEFAULT_SEVERITY` |
| `_models/_item.py` | `Item.priority: Priority \| None` (top-level, optional, every work type); `priority:` frontmatter key stores `.value` |
| `_models/_subentity.py` | `SubEntity.severity: Severity \| None` (findings); `severity:` key in the sub-entity frontmatter block |
| `_models/_metadata.py` | item-level severity as an **extra** field: `Kind` literal `"severity"`, `"bug": (Field(X.SEVERITY, "severity"),)`, coercion against `Severity` |
| `_workflow/_models.py` | `ItemSpec.severity_field`, `item_has_severity()` |
| `_cli/_common.py` | `parse_priority`/`parse_severity`, `priority_badge`, item-level severity render (`extra[X.SEVERITY]` gated by `item_has_severity`), sub-entity severity badge |
| `_cli/_main.py` | `--priority` create/list/tree filter, `Priority` column, `priority_badge` in list/tree/`--json` |
| `_cli/_items.py` | finding `--severity` (add default `"medium"`, update), finding `Severity` column |
| `_discussion.py` | `_severity_badge`, finding summary/head `Severity` column via `SEVERITY_EMOJI` |
| `_services/*`, `_migrations/*` | thread priority/severity through create/update/list/results; historical handling |

Two facts shape the model: **severity lives in two places** — item-level on `bug` (in
`extra[X.SEVERITY]`, opt-in via `severity_field`) and sub-entity-level on findings
(`SubEntity.severity`) — so both `Item` and `SubEntity` must carry these fields. And **priority is
global-optional**, severity is opt-in — a split this ADR subsumes declaratively.

## Decision

**Introduce a three-level badge model in the spec — *Badge*, *Collection*, *Field*. Priority and
severity become two bundled default collections carried by per-type/per-sub-entity-kind fields — not
special-cased code. Remove the `Priority`/`Severity` enums, the `*_EMOJI` maps, `DEFAULT_SEVERITY`,
and `ItemSpec.severity_field`; the CLI derives `--<field>` filters, sort, `--min-<field>`, and badge
rendering generically from the fields a type declares.** This applies ADR-322's "spec is the sole
vocabulary" move to the last two flat axes. Status is untouched (Constraint 1).

### 1. The three levels

- **Badge** — one entry: `{ code, label, emoji, …extras }`. The atomic value. `code` is the stored
  identity; `label` is the front-facing display; `emoji` (and any future extras) are presentation.
- **Collection** — a reusable, named library: `{ code, label, ordered list of badges }`. Its own
  `code` names it (referenced by fields) and its `label` is its default display name. **Badges are
  used AS-IS**: an item or field can never tweak a badge's own `label` or `emoji`. To get different
  badges, you define a **new collection** — there is no per-use badge override.
- **Field** — a type's or sub-entity-kind's binding to a collection:
  `{ code, label, collection: <collection-code>, required: bool, default?: <badge-code> }`. A field
  references a collection **by code** and provides **its own front-facing `label`**, which
  **relabels the collection for this field's use** — the same `level` collection can surface as
  "Priority" on one type and "Severity" on another. The collection's badges still render verbatim;
  only the collection-level display name is relabeled, never individual badges.

**A field carries a `code` AND a `label`, and they are distinct** — mirroring the collection's own
`code`/`label`. The field **`code`** is the storage + interaction identity: it is the frontmatter key
(`<code>: <badge-code>`) and the CLI flag (`--<code>`, `--min-<code>`). The field **`label`** is
display only (list/show/tree column header, the relabeled axis name). Two fields on one type must
therefore have distinct `code`s (see risks).

```toml
# --- Collections: reusable libraries (bundled defaults, byte-identical to today) ---
[collections.priority]
label = "Priority"
ordered = true                       # order = sort order; enables --min-<field>
badges = [
  { code = "urgent", label = "Urgent", emoji = "🔴" },
  { code = "high",   label = "High",   emoji = "🟠" },
  { code = "medium", label = "Medium", emoji = "🟡" },
  { code = "low",    label = "Low",    emoji = "🟢" },
]

[collections.severity]
label   = "Severity"
ordered = true
default = "medium"                   # collection's FALLBACK default badge (a field may override)
badges = [
  { code = "critical", label = "Critical", emoji = "🔴" },
  { code = "high",     label = "High",     emoji = "🟠" },
  { code = "medium",   label = "Medium",   emoji = "🟡" },
  { code = "low",      label = "Low",      emoji = "🟢" },
  { code = "info",     label = "Info",     emoji = "🔵" },
]

# --- Fields: per-type / per-sub-entity-kind bindings ---
[items.task]
fields = [ { code = "priority", label = "Priority", collection = "priority" } ]   # optional

[items.bug]
fields = [
  { code = "priority", label = "Priority", collection = "priority" },
  { code = "severity", label = "Severity", collection = "severity", required = false, default = "medium" },
]

[subentity_kinds.finding]
fields = [ { code = "severity", label = "Severity", collection = "severity", required = true, default = "medium" } ]

# --- Reuse (custom): two fields off ONE collection, each relabeled ---
# [items.incident]
# fields = [
#   { code = "impact",  label = "Impact",  collection = "level" },
#   { code = "urgency", label = "Urgency", collection = "level" },
# ]
```

This subsumes today's global-vs-opt-in split declaratively: **"global priority"** = every bundled
work type carries a `priority` field; **severity opt-in** (today's `severity_field`) = only the
types/kinds that declare a `severity` field carry it. `item_has_severity(t)` becomes "does type `t`
declare a field with code `severity`" — a generic `fields_for(type)` lookup.

### 2. `default` and `required` live on the FIELD

`required` is per-field (the same `severity` collection is `required=true` on findings,
`required=false` on bug; priority optional everywhere). `default` is per-field too; a collection MAY
carry a fallback `default`, and the field's `default` overrides it. Each type thus sets its own
default (bundled severity fields default to the `medium` badge; priority has no default).

### 3. Ordered-only this pass

Ship only **ordered** collections — both bundled defaults are ordered scales, and ordering drives
sort + `--min-<field>` threshold filtering. The `ordered` flag is reserved in the collection schema
so an unordered flat set could be added later (exact-match filter, no sort/threshold) without a
breaking change — but the unordered kind is **not designed now**.

### 4. Storage & round-trip (mirrors ADR-322's `prefix` discipline)

**The item stores only the badge `code`; label/emoji resolve from the spec.** One frontmatter key per
field, keyed by the field **`code`**: `priority: high`, `severity: critical`, (`impact: high`). The
two bundled default fields have `code = priority`/`severity`, so **existing frontmatter round-trips
byte-identically** — the familiar keys fall out of the general rule with no special-casing.

Round-trip-without-a-spec (ADR-322 §3) holds because the **badge code is the authoritative, stored
value** — a file always reads its own codes without a spec. Unlike `prefix` (part of the durable id,
must be present), the label/emoji are pure **presentation**, resolved from the collection at render
time with the same graceful neutral fallback status badges already use when no spec is loaded
(`_discussion._DEFAULT_BADGE`). So `--json`/code reads need no spec; only the decorative badge does,
and it degrades gracefully.

### 5. CLI derives everything from declared fields

`--<field-code>` filters, the create/update setters, list/show/tree columns (headed by the field
`label`), badges, sort, and (all collections being ordered this pass) `--min-<field-code>` are
**derived generically** from the fields a type declares — the dynamic-CLI-from-spec move ADR-322
makes for types. `parse_priority`/`parse_severity` collapse into one `parse_badge_code(field, code,
spec)`; `priority_badge` / `_severity_badge` into one `badge_render(field, code, spec)`.

### 6. Model changes

`Item` and `SubEntity` carry a field-code→badge-code mapping (codes validated against the bound
collection at the `IndexStore.load()` boundary — the same seam type/status use, keeping `_models`
spec-decoupled), while preserving the flat `priority:`/`severity:` frontmatter keys. `DEFAULT_SEVERITY`
moves to the field/collection `default`. `_metadata.py`'s `"severity"` field kind becomes a generic
badge-code kind.

## Blast radius / consequences

- **`_enums.py`** — `Priority`, `Severity`, `PRIORITY_EMOJI`, `SEVERITY_EMOJI`, `DEFAULT_SEVERITY`
  deleted. (With ADR-322 removing `ItemType`/`Status`, `_enums.py` is left essentially empty of
  vocabulary.)
- **`_workflow/_models.py`** — `ItemSpec.severity_field`/`item_has_severity` replaced by a `fields`
  list on `ItemSpec` (+ a sub-entity-kind `fields` list) and `fields_for()`/`collection()`
  accessors; new `Badge`/`Collection`/`Field` models + a `WorkflowSpec.collections` map with
  validation (see risks).
- **Item-level bug severity migrates storage.** Today in `extra[X.SEVERITY]`; under the uniform field
  model it serializes as a top-level `severity:` key like priority — a bounded, **bug-only one-time
  `sq migrate`** (`extra.severity` → `severity:`), plus dropping the `_metadata.py` special-case.
  Priority (already top-level) and finding severity (already `severity:` in the sub-entity block) are
  **unchanged**.
- **CLI** — `parse_priority`/`parse_severity`, `priority_badge`, the `--priority`/`--severity`
  options and the `Priority`/`Severity` columns across `_cli/_common.py`, `_main.py`, `_items.py`
  become field-generic (headers from the field `label`); ordered fields gain `--min-<code>`/sort.
- **Discussion / sub-entity rendering** — `_severity_badge` and the finding severity column resolve
  emoji/label from the bound collection (graceful fallback) instead of `SEVERITY_EMOJI`.
- **Pyright-strict fallout** — removing two more `StrEnum`s flips every `Priority`/`Severity`
  annotation to `str`; checked comparisons lose static typo-protection, so codes are guarded by
  spec-load validation + tests (identical to ADR-322's inversion).
- **Migrations** — historical severity/priority handling in `_meta_compat.py` / the `_vN` runners
  inline **frozen point-in-time constants**, never tracking the live collections (same caution as
  ADR-322).

## Tests, migration & compatibility

- **Test rework rides the FEAT-231 generic-first rebuild** — enum-pinned priority/severity goldens
  dissolve and are rebuilt against the bundled default collections/fields; **not** a blocker.
- **Backward-compat rests entirely on the bundled default spec** declaring the `priority`/`severity`
  **collections** and the per-type/kind **fields** identically to today — same badge codes, labels,
  emoji, severity default `medium`, priority global-optional, severity on bug + finding. A no-override
  squad behaves identically. This is the surviving runtime invariant.
- **Schema / migration** — spec-schema additions (`[collections.*]`, per-type/kind `fields`, removal
  of `severity_field`); the only item-file data change is the bug-severity `extra → top-level` move,
  owned by a small `sq migrate` step (assess `SCHEMA_VERSION`). Everything else round-trips
  byte-identical.

## New risks from the first-class-field / relabel model

- **Field-code uniqueness per type.** A field's `code` is a frontmatter key + CLI flag, so two fields
  on one type (the `impact`/`urgency`-off-one-collection reuse case) **must have distinct codes** —
  validate uniqueness per type/kind at spec load (fail-closed), else a second field silently shadows
  the first's frontmatter key.
- **Field code must not collide with reserved frontmatter keys.** A field named `type`/`status`/`id`/
  `prefix`/`parent`/`refs`/… would clash with core item frontmatter. Spec-load validation must reject
  field codes that shadow reserved keys.
- **Collection-code referential validation.** Every field's `collection` must name a **declared**
  collection; every `default` (field-level and collection-level) must be a badge `code` **present in
  that collection**; a `required` field with no resolvable default is rejected. All fail-closed at
  spec load — mirroring ADR-214's spec validation discipline.
- **Relabel-vs-verbatim boundary is a documentation/UX risk.** The model deliberately allows
  relabeling only the collection's front-facing name, never individual badge labels/emoji (to change
  badges → new collection). This must be stated plainly in the workflow-spec docs so authors don't
  expect per-field badge overrides.
- **Sub-entity `fields` intersect EPIC-280** (custom sub-entity kinds): the field mechanism must be
  the **same** for item types and sub-entity kinds, not forked — coordinate so the two efforts share
  one schema.

## Options considered

- **Recommended — three-level Badge/Collection/Field model** (above): collections are reusable
  libraries; fields are first-class per-type bindings that relabel a collection and own
  `required`/`default`; badges render verbatim. Fully generic, explicit reuse (two fields → one
  collection), subsumes global-vs-opt-in declaratively, keeps round-trip byte-identical, matches
  ADR-322's philosophy and mechanisms.
- **Rejected — per-type inline badge lists** (each type re-declares its own `{code,label,emoji}`
  set): no reuse; duplicates a vocabulary across every type that carries it — the exact duplication
  ADR-322 removed for prefixes.
- **Rejected — collections but no relabeling field layer** (a type just names a collection, display
  name == collection label): cannot surface one shared ordered scale under two names on one type
  (`impact`/`urgency`), and forces a near-duplicate collection per display name — the reuse the field
  layer is designed to enable.
- **Rejected — keep priority/severity special-cased, externalize only the emoji map**: leaves two
  hardcoded vocabularies + the `severity_field` boolean; does not deliver "spec is the sole
  vocabulary" and blocks custom flat axes.

### Recommendation

Adopt the three-level model: reusable **collections** of verbatim **badges**, referenced by
first-class **fields** that relabel the collection and carry `code`+`label`+`required`+`default`.
Ship `priority` and `severity` as byte-identical bundled default collections with matching bundled
fields; store only the badge code under the field's frontmatter key; resolve label/emoji from the
spec with graceful fallback; derive CLI filters/sort/badges generically. Ordered-only this pass, with
the `ordered` flag reserved. Sequence **after ADR-322** (depends on its generic-engine and spec-load
validation seam). Enforce field-code uniqueness, reserved-key avoidance, and collection/default
referential integrity at spec load.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-07T10:01:51Z] Robert Architect:
  - Companion to ADR-322 (sequenced after it, depends-on). Generalizes the last two hardcoded flat axes — Priority and Severity — into named, ordered, reusable BADGE COLLECTIONS in the spec, applying ADR-322's 'spec is the sole vocabulary' move. Status is explicitly OUT of scope per the operator: status = badge + state machine (its badge is already spec-declared via StatusSpec.badge); this ADR touches only flat axes.
  - Recommended shape: a [badges.<name>] collection = ordered list of {code,label,emoji}; types and sub-entity kinds declare axis bindings { name, collection, required }; priority + severity ship as byte-identical bundled defaults (subsuming today's global-priority / severity_field opt-in split declaratively); the item stores only the CODE under a flat per-axis frontmatter key (priority:/severity: unchanged → byte-identical round-trip), label/emoji resolve from the spec with the same graceful fallback status badges already use; CLI derives --<axis> filters, sort, --min-<axis>, and badges generically. Removes Priority/Severity StrEnums + *_EMOJI + DEFAULT_SEVERITY + ItemSpec.severity_field.
  - Top risks: (1) severity lives in TWO places today — item-level on bug (in extra[X.SEVERITY]) and sub-entity on findings (SubEntity.severity); the uniform axis model migrates item-level bug severity from extra to a top-level severity: key — a bounded bug-only sq migrate rewrite (finding severity + priority are unchanged). (2) same pyright-strict fallout as ADR-322: two more StrEnums removed, comparisons lose static typo-protection → codes guarded by spec-load validation + tests. (3) sub-entity axes intersect EPIC-280's custom-sub-entity-kinds work — the axis mechanism should be shared, not forked.
  - Three open questions need your call, @manager (details in body): (1) axis-name vs collection-name — I recommend name defaults to collection but is distinct so a collection can be reused under different axis names; (2) where default/required live — default on the collection, required per axis binding; (3) ordered-only now vs also unordered — I recommend ordered-only this pass, schema left open for unordered later. Proposed, no code/tasks.
- [2026-07-07T12:40:16Z] Robert Architect:
  - REVISED: the operator settled the badge model, so the three former open questions are now DECIDED, folded into the Decision, and the design is restructured around three explicit levels.
  - Final model — Badge / Collection / Field: (1) Badge = one entry {code, label, emoji, ...extras}, the atomic value, rendered AS-IS. (2) Collection = reusable named library {code, label, ordered list of badges}; to get different badges you define a NEW collection — no per-use badge override. (3) Field = a type's or sub-entity-kind's binding {code, label, collection:<code>, required, default?}; it references a collection by code and provides its OWN front-facing label that RELABELS the collection for this field's use (the same 'level' collection can surface as Priority on one type and Severity on another), while the collection's individual badges still render verbatim. A field carries a code (frontmatter key + --<code> CLI flag) AND a distinct label (display) — mirroring the collection's own code/label.
  - Decisions locked: (1) fields are first-class and relabel their collection — one type may carry TWO fields off ONE collection (impact + urgency -> level), reuse is explicit. (2) default and required live on the FIELD (severity required on findings, optional on bug; priority optional everywhere; each type sets its own default); a collection may carry a fallback default the field overrides. (3) ordered-only this pass — ship only ordered collections (drives sort + --min-<field>), reserve an 'ordered' flag for a future unordered kind, don't design it now. Priority + severity ship as two byte-identical bundled default COLLECTIONS with matching bundled FIELDS -> keys/flags/round-trip unchanged.
  - NEW risks introduced by the first-class-field/relabel model (all fail-closed at spec load): (1) field-code uniqueness per type — two fields on one type must have distinct codes or the second silently shadows the first's frontmatter key. (2) field codes must not collide with reserved frontmatter keys (type/status/id/prefix/parent/refs/...). (3) collection-code referential integrity — every field.collection must name a declared collection, and every default (field- and collection-level) must be a badge code present in that collection; a required field needs a resolvable default. (4) relabel-vs-verbatim boundary is a docs/UX risk — authors must not expect per-field badge overrides (change badges = new collection). (5) sub-entity fields must share ONE schema with item-type fields, coordinated with EPIC-280's custom-sub-entity-kinds work, not forked.
  - Recommendation unchanged in spirit, sharpened to the three-level model; sequenced after ADR-322. Still Proposed, no code/tasks. @manager
<!-- sq:discussion:end -->
