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
created_at: '2026-07-18T19:56:06Z'
updated_at: '2026-08-03T15:36:39Z'
---
<!-- sq:body -->
## Context

`squads` is a generic workflow engine. Its vocabulary — item types, statuses, and badge
collections — is spec data loaded from the active `WorkflowSpec` (ADR-214), not hardcoded names.
The badge model itself (a `collection` of `badge`s, bound to a type/kind by a `field` that may
relabel it) is settled by ADR-323; the semantic-status marker `StatusSpec.role` (currently only
`role="superseded"`, consumed by one `sq check` rule) is part of that spec. ADR-459 gave the first
machine-readable projection of this vocabulary — `sq workflow types --json`, a bare-array catalog
of the type vocabulary — and explicitly scoped the status/lifecycle catalog *out*, as a separate,
larger surface for a later decision. This ADR is that decision, extended to also cover the
collection vocabulary.

The engine layer is already generic. `Item.badge_value(code)` / `set_badge_value(code, value)`
reach any spec-declared field (bundled `priority`/`severity` are dedicated attributes, custom axes
live in `extra`); `WorkflowSpec.fields_for(type)` and `badges.resolve_collection` resolve a type's
actual axes from the spec; `WorkflowSpec.status_role(status)` already reads the semantic role. The
gap is at the **machine surface**, which still leaks the bundled default names instead of
reflecting the active spec:

- `sq tree --json` emits a literal `"priority": it.priority` per node and nothing else — no
  severity, no custom collection. A spec that renames priority, drops it, or adds `impact` is
  misrepresented.
- `sq list --json` / `sq show --json` are closer (custom axes ride in `extra`) but still split the
  *bundled* names (top-level `priority`/`severity`) from *custom* ones (buried in `extra`) — not a
  uniform, spec-driven view.
- No surface exposes a status's semantic `role`, so a client wanting to style "work in flight"
  distinctly is forced to key on the literal status string (`status == "InProgress"`) — which
  breaks the moment a spec renames or adds a working state.
- No surface exposes the collection **vocabulary** (code → label → emoji), so a client that wants
  to render the real badge (`🟠 High`) must hardcode the emoji set.

The principle (op-pierre, REV-448 F20): "squads is a generic workflow engine. All collections
should be surfaced. If only priority is, that means priority is hardcoded." F26 is the same lesson
on the status axis: style by a spec-declared semantic role, never by the literal status name.
These are two vocabularies (badge collections; status roles) but **one surface-projection
decision** — reflect the active spec generically, never the bundled names — so they are decided
together here.

One surface already does the collection half correctly and is the shape precedent: `sq graph
--json` (`GraphNode.to_dict`) emits a generic `badges` map keyed by field code — `{"priority":
"high"}`, or `{"impact": "high", "urgency": "low"}` for a custom axis — built by `_resolve_badges`
iterating `spec.fields_for(item.type)` and reading `item.badge_value(f.code)`, kept *alongside* the
legacy `priority` key. This ADR generalizes that shipped pattern.

Note the asymmetry with ADR-459's "don't repeat per-type facts on every node" principle: a type's
`order`/`prefix` are per-*type* facts and rightly live only in the catalog, never on each item; but
a badge **value** (`priority=high`) and a **status** are per-*item* facts and belong on the item.
So this ADR splits each vocabulary in two: per-item **values** on the item surfaces, and the
per-spec **vocabulary** (labels/emoji/role/terminal) in catalog surfaces.

Downstream consumers already exist as stories: FEAT-471 US7 (the collection surface, F20; blocks
F19's client badge hover) and US9 (the status-role surface, F26; blocks the client's green
"active" coloring). Both consume the surface this decision defines and are sequenced after it.

## Decision

### Part A — Collection vocabulary on the surface (F20)

**A1. Every item-bearing `--json` surface emits a generic `badges` map** of per-item values, keyed
by field code:

```json
"badges": { "priority": "high" }
```

built with the shipped `_resolve_badges` shape (iterate `spec.fields_for(item.type)`, include a
field only when `item.badge_value(code)` is non-null). Applies to:

- `sq tree --json` — each node gains `"badges"` (today: only `"priority"`).
- `sq list --json` — each row gains `"badges"`, unifying the bundled/`extra` split.
- `sq show --json` — the payload gains a top-level `"badges"`, and **each `subentities` entry**
  gains its own `"badges"` (a sub-entity carries fields too, e.g. severity on a finding — built
  from `spec.fields_for(kind)` + `sub.badge_value`).

Keyed by **field code**, not collection code: the field code is the frontmatter/CLI identity a
consumer already sees, and a field may rebind/relabel its collection.

**A2. Collection vocabulary reaches clients via a catalog, not glued onto items.** Item surfaces
emit **codes** (`high`), never rendered glyphs (`🟠 High`) — the code is the stable,
spec-authoritative value; emoji/label are presentation and belong in the vocabulary catalog once
per spec, not duplicated onto every item. New surface, mirroring `sq workflow types --json`:

`sq workflow collections --json` — a bare JSON array, one object per declared collection:

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

A client joins the two: read `badges: {"priority": "high"}` off an item, resolve field code →
collection, look up `high` in that collection's vocabulary for glyph + label.

**A3. The field-code → collection binding is surfaced on the type catalog.** The item `badges` map
is keyed by *field* code; the collections catalog (A2) is keyed by *collection* code. For the
bundled axes these coincide (field `priority` → collection `priority`), but a relabeled or custom
field (field `impact` → collection `severity`) needs the binding to be spec-driven too. Each `sq
workflow types --json` row gains a `fields` array so a client resolves field → collection from the
type catalog, then collection → vocabulary from the collections catalog:

```json
{
  "type": "bug",
  "order": 40,
  "prefix": "BUG",
  "reserved": false,
  "fields": [
    { "code": "priority", "label": "Priority", "collection": "priority" },
    { "code": "severity", "label": "Severity", "collection": "severity" }
  ]
}
```

This is an **additive** extension to ADR-459's type catalog — a new key on each row, no removal or
rename — and is therefore explicitly permitted by ADR-459's own additive-only evolution clause. It
references ADR-459, it does not amend it. The `workflow_types.json` golden fixture and the
field-set-vs-model drift test are updated to include the new `fields` key.

### Part B — Status semantic-role on the surface (F26)

**B1. Spec vocabulary.** `default_workflow.toml` gains `role = "active"` on `[statuses.InProgress]`
(work-item working state) and `[statuses.Active]` (roster working state). Both are already
`terminal = false`; `role` and `terminal` are orthogonal fields (Superseded already carries both),
so this is purely additive and clashes with nothing. `StatusSpec.role` stays `str | None` (one
optional role per status).
*The path is now `src/squads/_specs/workflow.toml`. B1's reference survives — one optional role per
status — but its referent changed: a role is no longer a bare marker string, it is a catalogued
`RoleSpec` object the status name resolves through (ADR-604/696). The orthogonality argument expired
with `terminal`; see B2.*

**B2. Status vocabulary on the surface via a catalog** (the ADR-459 pattern applied to statuses —
the surface that ADR explicitly deferred). New surface:

`sq workflow statuses --json` — a bare JSON array, one object per declared status:

```json
[
  { "status": "InProgress", "terminal": false, "role": "active",      "badge": "🟡" },
  { "status": "Done",       "terminal": true,  "role": null,          "badge": "🟢" },
  { "status": "Superseded", "terminal": true,  "role": "superseded",  "badge": null }
]
```

Fields: `status` (name), `terminal` (bool), `role` (str|null), `badge` (emoji|null). A client joins
an item's `status` string to this catalog to read `role`/`terminal`/`badge`, then styles by
`role == "active"` generically — never by the literal status name (the F20 anti-pattern).

*Narrowed 2026-08-03: `terminal` was dropped from this catalog by ADR-604 §5 and the frozen field
set is `("status", "role", "badge")`. A client reads terminality from the role it joins to — a
consequence of this part's own argument, not a reversal of it: once a role carries behaviour, a
separate `terminal` column is a second answer to the same question. The join-and-style-by-role rule,
and the anti-pattern it forbids, are exactly as decided. See the amendment note.*

**B3. Catalog-only — no per-item role field.** The semantic role is exposed *only* via the status
catalog; item surfaces (tree/list/show) do **not** gain a per-item `role`/`is_active` field. The
client joins `status → role` through the catalog, exactly as the type catalog is joined by type
name. This deliberately does **not** propagate the tree surface's per-node `is_open` convenience to
the role axis — `is_open` stays the lone per-item derived-status exception by design (a
constantly-used boolean for the primary open/closed axis), and role is not given the same
treatment. Keeping role catalog-only avoids duplicating a per-status fact onto every item.

### Shared contract for both parts

- **A `sq workflow <catalog> --json` family.** `types` (ADR-459), `collections` (A2), and
  `statuses` (B2) are three sibling catalog surfaces: bare JSON arrays, one row per declared
  vocabulary entry, every row carrying a stable frozen key set. Each new surface gets the ADR-459
  treatment: a module-level frozen field-set constant, a JSON golden fixture, and a
  field-set-vs-model drift test, plus service + CLI-smoke coverage.
- **Additive superset — no break.** No existing key is renamed, removed, or deprecated. `sq
  tree`/`sq graph` keep `"priority"`; `sq list`/`sq show` keep top-level `priority`/`severity` and
  `extra`; the `badges` map is layered alongside them, exactly as `sq graph --json` already does.
  Adding `role="active"` changes no existing consumer (only `Superseded` set a role before). All of
  this is JSON output / spec-TOML data only: no frontmatter change, no `.squads.json` change, no
  schema-version bump, no migration.
- **Per-item values vs. per-spec vocabulary.** Values (badge codes, status names) live on the item
  surfaces; vocabulary (labels, emoji, ordered/default, role, terminal) lives in the catalogs, once
  per spec — never duplicated onto every item.

### Explicitly deferred

- **Widening `StatusSpec.role` from `str | None` to `list[str]`.** A status could legitimately carry
  more than one semantic role; deferring the multi-role model keeps this increment additive. Revisit
  as its own decision (a model/schema change) if and when a second co-resident role appears.
- **Deprecating the legacy bundled keys** (`priority` on tree/graph; top-level
  `priority`/`severity` on list/show). Kept indefinitely here; a future deprecation is its own call.

## Consequences

- REV-448 F20 (root) and the F26 status-role gap are fixed at the surface. F19 (client badge hover)
  becomes a straight render of the generic `badges` map plus a catalog vocabulary lookup; the
  client's green "active" coloring (F26) becomes a straight `role == "active"` check — no hardcoded
  names, no hardcoded emoji, on either axis.
- The client stays fully spec-driven: a spec that renames priority, adds `impact`, renames the
  working status, or adds a working state is faithfully represented with zero client changes.
- Purely additive: existing consumers are untouched; no schema bump, no migration.
- Item payloads grow by a small per-item map (and per-sub-entity on `show`); the two new catalog
  surfaces are read-only and derived entirely from the active spec.
- Three coherent catalog surfaces (`types`/`collections`/`statuses`) now project the whole spec
  vocabulary, each contract-frozen and drift-tested.
  *Narrowed 2026-08-03: "the whole spec vocabulary" was an overclaim. `WorkflowSpec` declares six
  vocabulary maps; these three covered three of them, `roles` was added by ADR-604, and `lifecycles`
  and `subentity_kinds` had no machine surface at all. The completeness rule — one catalog command per
  declared spec map, no map left unpublished — is set by ADR-738, which adds the two missing catalogs.
  The shared contract this part defines (bare arrays, one row per declared entry, frozen key sets,
  values on items and vocabulary in catalogs) is unchanged and is what ADR-738 generalizes.*

## Alternatives considered

- **Emit rendered glyphs (`"🟠 high"`) on items.** Rejected: bakes presentation into the machine
  contract, couples every consumer to the emoji set, and duplicates the vocabulary on every item
  instead of once in a catalog.
- **Emit `status_role` (and label/emoji) per item on every surface instead of a status catalog.**
  Rejected (decision B3): the same per-item duplication — `role`/`terminal`/`badge` are per-status
  facts, derivable from the item's `status` via the catalog. The tree surface's existing per-node
  `is_open` stays the lone deliberate exception; the role axis is not given the same per-item
  convenience.
- **Rename/replace `priority` with `badges`, or the bundled split, as a breaking change.** Rejected:
  the additive superset costs nothing and matches the shipped `sq graph --json` precedent; the
  bundled/custom split *is* the F20 hardcoding, and a uniform generic map is the whole point.
- **Amend ADR-459 to add the status/collection catalogs.** Rejected: ADR-459 deliberately scoped the
  status/lifecycle catalog out as a separate surface; these are a new, referencing decision, not an
  edit to an accepted one.
- **Widen `StatusSpec.role` to a list now.** Deferred (above) — out of scope for this additive
  increment.
- **Key the item `badges` map by collection code, or ship a dedicated fields surface.** Rejected in
  favour of A3: the field code is the frontmatter/CLI identity a consumer already sees, and folding
  the binding into the existing type catalog reuses the ADR-459 surface rather than adding a fourth.

## Amendment note

**2026-08-03 — B2's `terminal` column is gone; everything else stands.** A1, A2 and A3 are verified live:
the generic `badges` map, `sq workflow collections --json`, and per-type `fields` on the type catalog.

ADR-604 §5 drops `terminal` from the status catalog, leaving `STATUS_CATALOG_FIELDS = ("status", "role",
"badge")`, and derives terminality from the role object instead (`terminal = role.settled`). B2's example
row, which shows `"terminal": false`, is therefore no longer the frozen shape.

This is the cleanest instance in the set of a decision being completed rather than contradicted. B1
introduced the role as an optional marker beside `terminal` and argued the two were orthogonal; B2 put
both on the wire. Once ADR-604 made the role a first-class object carrying `settled`, `hidden` and a
colour intent, `terminal` became a second answer to a question the role already answers — so removing it
follows from this part's own reasoning. What survives untouched is the rule that actually mattered: a
client joins on the status string and styles by the role, never by a literal status name.

Also corrected: the bundled spec path is `src/squads/_specs/workflow.toml`.

ADR-604 refs this decision but the edge was one-directional; a reciprocal `related` edge is added.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-18T19:57:45Z] Robert Architect:
  - Addresses REV-448 F20 (generic collections surface, root of F19) and F26 (status_role + role=active). F19 is the client consumer that motivates the collection half; it renders whatever this surface emits. Consuming stories: FEAT-471 US7 (F20) and US9 (F26).
  - Folded F20+F26 into one ADR: same principle (project the spec vocabulary generically, never the bundled names) and one sq workflow <catalog> --json family (types [ADR-459] + collections + statuses). Does NOT amend ADR-459 — it delivers the status/lifecycle catalog ADR-459 deliberately deferred. Split into two later if the status half (which carries the role=active spec-data change + the deferred multi-role widening) warrants its own record.
  - Open questions before implementation (in the body): (1) how the field-code->collection binding is surfaced for relabeled/custom fields — recommend extending sq workflow types --json rows with each type's fields[]; (2) catalog-only status role vs. also a per-item convenience field; (3) one ADR vs two. Deferred (do not design in): widening StatusSpec.role str|None -> list[str].
- [2026-07-18T20:02:16Z] Pierre Chat:
  - Rulings on the three open questions (op-pierre): (1) Field→collection binding — yes, extend sq workflow types --json rows with fields: [{code, label, collection}]. Additive per ADR-459's additive-only clause. (2) Status role — Option A, catalog-only: no per-item role/is_active field; the client joins status→role via the statuses catalog (same as the type-catalog pattern). Do not propagate is_open's per-node convenience. (3) One ADR — keep it consolidated as drafted, do not split.
- [2026-07-18T20:06:07Z] Pierre Chat:
  - Accepted after reading the finalized body. Rulings baked in correctly; one consolidated ADR, references (does not amend) ADR-459/323/214. Proceed to implementation via FEAT-471.
- [2026-08-03T08:45:42Z] Robert Architect:
  - Narrowed B2 in place: `terminal` was dropped from the status catalog by ADR-604 section 5 and the frozen field set is `("status", "role", "badge")`. B2s example row still showed `"terminal": false`. A1, A2 and A3 verified live (generic `badges` map, `sq workflow collections --json`, per-type `fields` on the type catalog).
  - This is the cleanest case in the whole audit of a decision being completed rather than contradicted, and I wrote it up that way. B1 introduced the role as an optional marker beside `terminal` and argued the two were orthogonal; once ADR-604 made the role a first-class object carrying `settled`, `hidden` and a colour intent, `terminal` became a second answer to a question the role already answers. Removing it follows from B1s own reasoning. B1s reference survives with a changed referent — one optional role per status, now a catalogued object rather than a bare marker string.
  - The rule that actually mattered is untouched: a client joins on the status string and styles by the role, never by a literal status name. Path corrected to `src/squads/_specs/workflow.toml`. Added the reciprocal `related` edge to ADR-604, whose own edge here was one-directional.
- [2026-08-03T15:36:39Z] Robert Architect:
  - Narrowed in place, not superseded: the Consequences claim that three catalogs "project the whole spec vocabulary" was an overclaim. Six declared maps, four published — `lifecycles` and `subentity_kinds` had no machine surface at all.
  - ADR-738 sets the completeness rule (one catalog command per declared spec map) and adds the two missing catalogs. This decision stays in force: its shared contract — bare arrays, one row per declared entry, frozen key sets, per-item values vs per-spec vocabulary — is what ADR-738 generalizes into a row grammar. Linked `related` both ways.
<!-- sq:discussion:end -->
