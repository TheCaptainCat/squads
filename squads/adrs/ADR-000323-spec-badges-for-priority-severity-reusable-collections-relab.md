---
id: ADR-323
sequence_id: 323
type: decision
title: 'Spec badges for priority/severity: reusable collections + relabeling fields'
status: Accepted
author: architect
refs:
- ADR-322:depends-on
- ADR-214
- ADR-232
- ADR-1007
created_at: '2026-07-07T10:00:07Z'
updated_at: '2026-10-25T21:23:54Z'
---
<!-- sq:body -->
## Context

The loaded workflow spec is the sole vocabulary authority for item types and statuses (ADR-322).
Priority and severity are the flat presentation axes beside them: closed scales with an emoji per
value, carried by some types and some sub-entity kinds (severity on `bug` items and on findings,
priority on work items). Hardcoding them as enums with emoji maps and a per-type
"has severity" flag repeats the shape ADR-322 removed for types.

Two operator constraints shape the model:

1. **Status is not part of it.** A status is a badge **plus a state machine**; status badges are
   spec-declared (`StatusSpec.badge`, resolved by `status_badge()`) and stay that way. This model
   covers only the **flat** axes: priority, severity, and any a squad adds.
2. **Badges are first-class, reusable spec vocabulary**, defined once and referenced by many.

## Decision

**A three-level badge model in the spec: Badge, Collection, Field.** Priority and severity are two
bundled collections bound by per-type and per-sub-entity-kind fields; nothing about them is
special-cased in code.

### 1. The three levels

- **Badge** (`Badge` in `_workflow/_models.py`): `{ code, label, emoji }`. `code` is the stored
  identity, `label` the display, `emoji` presentation.
- **Collection** (`[collections.<code>]`): a reusable, named library `{ label, ordered, default?,
  badges }`, identified by its key. **Badges are used as-is**: nothing can tweak a badge's own
  `label` or `emoji`. Different badges mean a new collection.
- **Field**: a type's or sub-entity kind's binding `{ code, label, collection, required, default? }`.
  The field **`code`** is the storage and interaction identity (the frontmatter key and the
  `sq <type> <n> update --set <code>=<value>` and filter key); the field **`label`** is display only and **relabels the
  collection** for that use, so one collection can surface as "Impact" and "Urgency" on one type.
  Badges still render verbatim.

```toml
[collections.priority]
label = "Priority"
ordered = true
badges = [
  { code = "urgent", label = "Urgent", emoji = "🔴" },
  { code = "high",   label = "High",   emoji = "🟠" },
  { code = "medium", label = "Medium", emoji = "🟡" },
  { code = "low",    label = "Low",    emoji = "🟢" },
]

[collections.severity]
label = "Severity"
ordered = true
default = "medium"
badges = [
  { code = "critical", label = "Critical", emoji = "🔴" },
  { code = "high",     label = "High",     emoji = "🟠" },
  { code = "medium",   label = "Medium",   emoji = "🟡" },
  { code = "low",      label = "Low",      emoji = "🟢" },
  { code = "info",     label = "Info",     emoji = "🔵" },
]

[items.bug]
fields = [
  { code = "priority", label = "Priority", collection = "priority" },
  { code = "severity", label = "Severity", collection = "severity", required = false, default = "medium" },
]

[subentity_kinds.finding]
fields = [ { code = "severity", label = "Severity", collection = "severity", required = true, default = "medium" } ]

# Reuse: two fields off one collection, each relabeled
# [items.incident]
# fields = [
#   { code = "impact",  label = "Impact",  collection = "level" },
#   { code = "urgency", label = "Urgency", collection = "level" },
# ]
```

Every bundled non-roster type declares a `priority` field; only `bug` and the finding kind declare
`severity`. Whether a type carries an axis is "does it declare a field with that code"
(`WorkflowSpec.fields_for(type)`).

### 2. `required` and `default` live on the field

The same collection can be required on one owner and optional on another. A collection may carry
a fallback `default`; a field's `default` overrides it.

### 3. Collections are ordered

Order is sort order and drives threshold filtering. The `ordered` flag is reserved in the schema
for a future unordered kind; spec load refuses `ordered = false` until that kind is designed.

### 4. Storage

**An item stores only the badge code, under the field's code, as a top-level frontmatter key**:
`priority: high`, `severity: critical`, `impact: high`. A sub-entity's entry in its parent's
frontmatter carries `severity` in its own slot and any other declared field under its code in the
entry's `extra` mapping. Label and emoji resolve from the collection at render time,
with a neutral fallback when no spec is available, so a file reads its own codes without a spec.
ADR-1007 owns the flat frontmatter shape: a field code may not collide with a core key, an
attribute of the same type, a key `--json` adds to an item row, `path`, `prefix` or `extra`, and a
value is validated by collection membership.

### 5. The CLI derives everything from declared fields

Setting a value, list/show/tree columns (headed by the field `label`), badges, filters and sort are
derived from the fields a type declares, through one parser and one renderer
(`parse_badge_code`, `badge_render`, with the helpers in `_badges.py`):

- `sq <type> <n> update --set <code>=<value>` sets any declared field; `--priority` is a dedicated
  setter for the bundled axis on create and update.
- `sq list` and `sq tree` filter with `--badge CODE=VALUE` (exact) and `--min-badge CODE=VALUE`
  (threshold on an ordered collection), both repeatable, and sort with `--sort CODE`.
  `--priority` and `--min-priority` are sugar for the bundled priority field.

Per-field flags (`--impact`, `--min-urgency`) are not generated: Typer options are fixed at import
while the active spec is per invocation, so the generic `CODE=VALUE` surface is the one that works
for every squad.

## Consequences

- No priority or severity vocabulary, emoji map or per-type severity flag exists in code; a squad
  can add, relabel or replace flat axes in its override.
- Backward compatibility rests on the bundled collections and fields: same codes, labels, emoji,
  severity default `medium`.
- Comparisons against badge codes are `str == str`; spec-load validation and tests guard them.
- Migration runners inline frozen point-in-time vocabulary, never the live collections.
- The relabel-versus-verbatim boundary (relabel the collection, never a badge) is documented for
  spec authors.
- Item types and sub-entity kinds share one field mechanism (`SubentityKindSpec.fields`), not a
  fork.

Spec load fails closed on: duplicate field codes on one owner, a field code shadowing a reserved
key, a field naming an undeclared collection, a field- or collection-level `default` that is not
a badge of that collection, and a required field with no resolvable default.

## Options considered

- **Three-level Badge/Collection/Field (chosen).** Reusable collections, relabeling fields that own
  `required`/`default`, verbatim badges.
- **Per-type inline badge lists.** Rejected: no reuse, the vocabulary duplicated across every type.
- **Collections without a field layer.** Rejected: one scale cannot surface under two names on one
  type without a near-duplicate collection per name.
- **Keep priority and severity special-cased, externalize only the emoji.** Rejected: two hardcoded
  vocabularies remain and no custom flat axis is possible.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-07T10:01:51Z] `architect` Robert Architect:
  - Companion to ADR-322 (sequenced after it, depends-on). Generalizes the last two hardcoded flat axes — Priority and Severity — into named, ordered, reusable BADGE COLLECTIONS in the spec, applying ADR-322's 'spec is the sole vocabulary' move. Status is explicitly OUT of scope per the operator: status = badge + state machine (its badge is already spec-declared via StatusSpec.badge); this ADR touches only flat axes.
  - Recommended shape: a [badges.<name>] collection = ordered list of {code,label,emoji}; types and sub-entity kinds declare axis bindings { name, collection, required }; priority + severity ship as byte-identical bundled defaults (subsuming today's global-priority / severity_field opt-in split declaratively); the item stores only the CODE under a flat per-axis frontmatter key (priority:/severity: unchanged → byte-identical round-trip), label/emoji resolve from the spec with the same graceful fallback status badges already use; CLI derives --<axis> filters, sort, --min-<axis>, and badges generically. Removes Priority/Severity StrEnums + *_EMOJI + DEFAULT_SEVERITY + ItemSpec.severity_field.
  - Top risks: (1) severity lives in TWO places today — item-level on bug (in extra[X.SEVERITY]) and sub-entity on findings (SubEntity.severity); the uniform axis model migrates item-level bug severity from extra to a top-level severity: key — a bounded bug-only sq migrate rewrite (finding severity + priority are unchanged). (2) same pyright-strict fallout as ADR-322: two more StrEnums removed, comparisons lose static typo-protection → codes guarded by spec-load validation + tests. (3) sub-entity axes intersect EPIC-280's custom-sub-entity-kinds work — the axis mechanism should be shared, not forked.
  - Three open questions need your call, @manager (details in body): (1) axis-name vs collection-name — I recommend name defaults to collection but is distinct so a collection can be reused under different axis names; (2) where default/required live — default on the collection, required per axis binding; (3) ordered-only now vs also unordered — I recommend ordered-only this pass, schema left open for unordered later. Proposed, no code/tasks.
- [2026-07-07T12:40:16Z] `architect` Robert Architect:
  - REVISED: the operator settled the badge model, so the three former open questions are now DECIDED, folded into the Decision, and the design is restructured around three explicit levels.
  - Final model — Badge / Collection / Field: (1) Badge = one entry {code, label, emoji, ...extras}, the atomic value, rendered AS-IS. (2) Collection = reusable named library {code, label, ordered list of badges}; to get different badges you define a NEW collection — no per-use badge override. (3) Field = a type's or sub-entity-kind's binding {code, label, collection:<code>, required, default?}; it references a collection by code and provides its OWN front-facing label that RELABELS the collection for this field's use (the same 'level' collection can surface as Priority on one type and Severity on another), while the collection's individual badges still render verbatim. A field carries a code (frontmatter key + --<code> CLI flag) AND a distinct label (display) — mirroring the collection's own code/label.
  - Decisions locked: (1) fields are first-class and relabel their collection — one type may carry TWO fields off ONE collection (impact + urgency -> level), reuse is explicit. (2) default and required live on the FIELD (severity required on findings, optional on bug; priority optional everywhere; each type sets its own default); a collection may carry a fallback default the field overrides. (3) ordered-only this pass — ship only ordered collections (drives sort + --min-<field>), reserve an 'ordered' flag for a future unordered kind, don't design it now. Priority + severity ship as two byte-identical bundled default COLLECTIONS with matching bundled FIELDS -> keys/flags/round-trip unchanged.
  - NEW risks introduced by the first-class-field/relabel model (all fail-closed at spec load): (1) field-code uniqueness per type — two fields on one type must have distinct codes or the second silently shadows the first's frontmatter key. (2) field codes must not collide with reserved frontmatter keys (type/status/id/prefix/parent/refs/...). (3) collection-code referential integrity — every field.collection must name a declared collection, and every default (field- and collection-level) must be a badge code present in that collection; a required field needs a resolvable default. (4) relabel-vs-verbatim boundary is a docs/UX risk — authors must not expect per-field badge overrides (change badges = new collection). (5) sub-entity fields must share ONE schema with item-type fields, coordinated with EPIC-280's custom-sub-entity-kinds work, not forked.
  - Recommendation unchanged in spirit, sharpened to the three-level model; sequenced after ADR-322. Still Proposed, no code/tasks. @manager
- [2026-07-07T14:35:18Z] `manager` Catherine Manager:
  - Accepted as-is at the design-gate review (op-pierre deciding). Full three-level Badge/Collection/Field model confirmed: a field references a collection and carries its own label; the collection holds ordered badges; each badge = code + label + emoji. Sequenced after ADR-322.
- [2026-10-25T21:23:54Z] `architect` Robert Architect:
  - 2026-10-25 audit: partly stale, body rewritten in the present tense; the three-level model is unchanged. Restated §5 as the shipped CLI grammar: --badge/--min-badge CODE=VALUE, --sort CODE, --priority/--min-priority sugar and update --set, not generated per-field --<code> flags (REV-346 F3, WontFix: Typer options are fixed at import). §3 now says spec load refuses ordered = false. Folded the dated ADR-1007 note into §4 and named where sub-entity fields are stored. Removed the pre-implementation grep table, enum line numbers, the bug-severity migration plan and the FEAT-231 test note.
<!-- sq:discussion:end -->
