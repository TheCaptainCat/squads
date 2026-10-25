---
id: ADR-474
sequence_id: 474
type: decision
title: 'Spec-vocabulary machine surface: generic collections + status roles'
status: Accepted
author: architect
refs:
- REV-448:addresses
- FEAT-471:addresses
- ADR-323
- ADR-459
- ADR-214
- EPIC-99
- ADR-604
- ADR-738
- ADR-1007
created_at: '2026-07-18T19:56:06Z'
updated_at: '2026-10-25T21:29:28Z'
---
<!-- sq:body -->
## Context

`squads` is a generic workflow engine: item types, statuses and badge collections are spec data
from the active `WorkflowSpec`, not hardcoded names. ADR-323 settles the badge model (collections of
badges, bound to a type or kind by a field that may relabel it); each status names a semantic role
(ADR-604). ADR-459 gave the first machine-readable projection of that vocabulary,
`sq workflow types --json`, and left the status catalog to a separate decision. This is that
decision, extended to the collection vocabulary.

A machine surface that leaks the bundled names misrepresents any other spec. Emitting a literal
`priority` key and nothing else hides a renamed, dropped or added axis; splitting bundled axes
from custom ones makes the view non-uniform; exposing no status role forces a client to style by
the literal status string (`status == "InProgress"`), which breaks when a spec renames a working
state; exposing no badge vocabulary forces it to hardcode the emoji set.

The principle (op-pierre, REV-448 F20): "squads is a generic workflow engine. All collections
should be surfaced. If only priority is, that means priority is hardcoded." F26 is the same lesson
on the status axis: style by a spec-declared role, never by a status name. Badge collections and
status roles are two vocabularies but one projection decision, so they are decided together.

A type's `order`/`prefix` are per-*type* facts and live only in the catalog (ADR-459), while a badge
**value** (`priority=high`) and a **status** are per-*item* facts and belong on the item. Each
vocabulary is therefore split in two: per-item **values** on the item surfaces, and the per-spec
**vocabulary** (labels, emoji, role) in catalogs.

## Decision

### Part A — Collection vocabulary on the surface

**A1. Every item-bearing `--json` surface emits a generic `badges` map** of per-item values, keyed
by field code:

```json
"badges": { "priority": "high" }
```

built by iterating `spec.fields_for(item.type)` and including a field only when the item stores a
value for it. It is on each `sq tree --json` node, each `sq list --json` row, each `sq graph --json`
node, the `sq show --json` payload, and each entry of its `subentities` (built from
`spec.fields_for(kind)`). It is keyed by **field** code, the frontmatter and CLI identity a consumer
already sees, not by collection code.

**A2. Collection vocabulary comes from a catalog, never glued onto items.** Item surfaces emit
**codes** (`high`), never rendered glyphs; label and emoji are presentation and live once per spec
in `sq workflow collections --json`, a bare array with one row per declared collection:

```json
[
  {
    "collection": "priority",
    "label": "Priority",
    "ordered": true,
    "default": null,
    "badges": [
      { "code": "urgent", "label": "Urgent", "emoji": "🔴" },
      { "code": "high",   "label": "High",   "emoji": "🟠" },
      { "code": "medium", "label": "Medium", "emoji": "🟡" },
      { "code": "low",    "label": "Low",    "emoji": "🟢" }
    ]
  }
]
```

**A3. The field → collection binding is on the type catalog.** Each `sq workflow types --json` row
carries a `fields` array of `{ code, label, collection }`, so a client resolves field code →
collection there and collection → vocabulary from A2. This adds a key to ADR-459's catalog under
its additive rule.

### Part B — Status semantic role on the surface

**B1. Spec vocabulary.** Every status names one role. The bundled working states
(`InProgress`, `InReview`, `ChangesRequested`, the finding's `Fixed`, and the roster's `Active`)
name the `active` role. A role is a catalogued object (ADR-604, ADR-696), not a bare
marker string.

**B2. Status vocabulary on the surface via a catalog.** `sq workflow statuses --json` is a bare
array with one row per declared status:

```json
[
  { "status": "InProgress", "role": "active",     "badge": "🟡" },
  { "status": "Done",       "role": "done",       "badge": "🟢" },
  { "status": "Superseded", "role": "superseded", "badge": null }
]
```

The frozen key set is `("status", "role", "badge")`. A client joins an item's `status` to this row,
then the role to `sq workflow roles --json` (ADR-604) for settled, hidden and colour intent, and
styles by the role, never by the literal status name. Terminality is read from the role, so the
status row carries no `terminal` column.

**B3. Catalog-only — no per-item role field.** Item surfaces carry no per-item `role`, `is_active`
or `is_open` field; a client joins `status → role` through the catalogs, exactly as the type catalog
is joined by type name. Duplicating a per-status fact onto every item is refused.

### Shared contract

- **A `sq workflow <catalog> --json` family.** `types`, `collections` and `statuses` are sibling
  catalogs: bare JSON arrays, one row per declared entry, a stable key set per row, each with a
  module-level key-set constant, a JSON golden and a drift test. ADR-738 completes the family (one
  catalog per declared spec map) and ADR-604 adds `roles`.
- **Additive.** The `badges` map is layered alongside the existing keys: `sq tree --json` and
  `sq graph --json` keep `priority`, and `sq list --json` / `sq show --json` keep each stored field
  top-level under its code (ADR-1007). This is JSON output and spec data only; it touches no
  frontmatter and no index.
- **Values on items, vocabulary in catalogs**, once per spec.

### Out of scope

- **More than one role per status.** One role per status keeps this additive; a multi-role model is
  its own model and schema decision if a second co-resident role ever appears.
- **Deprecating the bundled per-item keys** (`priority` on tree and graph rows). Kept; a
  deprecation is its own call.

## Consequences

- A client renders badges from the `badges` map plus a catalog lookup and colours statuses by role,
  with no hardcoded names or emoji on either axis.
- A spec that renames priority, adds `impact`, renames a working status or adds one is represented
  faithfully with zero client changes.
- Item payloads grow by a small per-item map (and per sub-entity on `show`); the catalogs are
  read-only and derived from the active spec.

## Alternatives considered

- **Rendered glyphs (`"🟠 high"`) on items.** Rejected: presentation baked into the contract, the
  vocabulary duplicated onto every item.
- **A per-item status role on every surface.** Rejected (B3): a per-status fact derivable through
  the catalog.
- **Replacing `priority` with `badges` as a breaking change.** Rejected: the additive layer costs
  nothing.
- **Amending ADR-459 to add these catalogs.** Rejected: ADR-459 scoped the status catalog out as a
  separate surface; this is a new, referencing decision.
- **Keying `badges` by collection code, or a dedicated fields surface.** Rejected in favour of A3:
  the field code is the identity consumers already see, and the binding fits the existing type
  catalog.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-18T19:57:45Z] `architect` Robert Architect:
  - Addresses REV-448 F20 (generic collections surface, root of F19) and F26 (status_role + role=active). F19 is the client consumer that motivates the collection half; it renders whatever this surface emits. Consuming stories: FEAT-471 US7 (F20) and US9 (F26).
  - Folded F20+F26 into one ADR: same principle (project the spec vocabulary generically, never the bundled names) and one sq workflow <catalog> --json family (types [ADR-459] + collections + statuses). Does NOT amend ADR-459 — it delivers the status/lifecycle catalog ADR-459 deliberately deferred. Split into two later if the status half (which carries the role=active spec-data change + the deferred multi-role widening) warrants its own record.
  - Open questions before implementation (in the body): (1) how the field-code->collection binding is surfaced for relabeled/custom fields — recommend extending sq workflow types --json rows with each type's fields[]; (2) catalog-only status role vs. also a per-item convenience field; (3) one ADR vs two. Deferred (do not design in): widening StatusSpec.role str|None -> list[str].
- [2026-07-18T20:02:16Z] `op-pierre` Pierre Chat:
  - Rulings on the three open questions (op-pierre): (1) Field→collection binding — yes, extend sq workflow types --json rows with fields: [{code, label, collection}]. Additive per ADR-459's additive-only clause. (2) Status role — Option A, catalog-only: no per-item role/is_active field; the client joins status→role via the statuses catalog (same as the type-catalog pattern). Do not propagate is_open's per-node convenience. (3) One ADR — keep it consolidated as drafted, do not split.
- [2026-07-18T20:06:07Z] `op-pierre` Pierre Chat:
  - Accepted after reading the finalized body. Rulings baked in correctly; one consolidated ADR, references (does not amend) ADR-459/323/214. Proceed to implementation via FEAT-471.
- [2026-08-03T08:45:42Z] `architect` Robert Architect:
  - Narrowed B2 in place: `terminal` was dropped from the status catalog by ADR-604 section 5 and the frozen field set is `("status", "role", "badge")`. B2s example row still showed `"terminal": false`. A1, A2 and A3 verified live (generic `badges` map, `sq workflow collections --json`, per-type `fields` on the type catalog).
  - This is the cleanest case in the whole audit of a decision being completed rather than contradicted, and I wrote it up that way. B1 introduced the role as an optional marker beside `terminal` and argued the two were orthogonal; once ADR-604 made the role a first-class object carrying `settled`, `hidden` and a colour intent, `terminal` became a second answer to a question the role already answers. Removing it follows from B1s own reasoning. B1s reference survives with a changed referent — one optional role per status, now a catalogued object rather than a bare marker string.
  - The rule that actually mattered is untouched: a client joins on the status string and styles by the role, never by a literal status name. Path corrected to `src/squads/_specs/workflow.toml`. Added the reciprocal `related` edge to ADR-604, whose own edge here was one-directional.
- [2026-08-03T15:36:39Z] `architect` Robert Architect:
  - Narrowed in place, not superseded: the Consequences claim that three catalogs "project the whole spec vocabulary" was an overclaim. Six declared maps, four published — `lifecycles` and `subentity_kinds` had no machine surface at all.
  - ADR-738 sets the completeness rule (one catalog command per declared spec map) and adds the two missing catalogs. This decision stays in force: its shared contract — bare arrays, one row per declared entry, frozen key sets, per-item values vs per-spec vocabulary — is what ADR-738 generalizes into a row grammar. Linked `related` both ways.
- [2026-10-25T21:29:28Z] `architect` Robert Architect:
  - 2026-10-25 audit: partly stale, body rewritten in the present tense; Parts A and B are unchanged. Folded the 2026-08-03 terminal narrowing (status row is status, role, badge; terminality from the role) and the dated ADR-1007 note (no extra key on item rows). B1 now states that every status names a catalogued role. B3 corrected: is_open is gone from tree/list/mine --json (ADR-604, FEAT-605), so there is no per-item derived status flag left. Replaced the "whole spec vocabulary" overclaim with ADR-738 completing the catalog family, and removed the pre-implementation surface description and the FEAT-471 sequencing.
<!-- sq:discussion:end -->
