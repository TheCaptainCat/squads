---
id: ADR-738
sequence_id: 738
type: decision
title: 'Complete the sq workflow catalog family: one catalog per spec map'
status: Accepted
author: architect
refs:
- BUG-732:addresses
- ADR-323:depends-on
- ADR-348:depends-on
- ADR-459
- ADR-474
- REV-736
- TASK-737
description: 'Closes the sq workflow --json catalog family at one command per declared
  WorkflowSpec map: adds subentity-kinds and lifecycles under a single row grammar,
  plus two reference keys on ADR-459''s type row.'
created_at: '2026-08-03T15:34:51Z'
updated_at: '2026-10-25T21:46:29Z'
---
<!-- sq:body -->
## Context

Two gaps in the `sq workflow` catalog family answer one question: which part of the workflow spec
is machine-readable, and in what shape.

- **BUG-732** — a type's lifecycle (initial state, state set, edges) needs a `--json` surface; the
  data (`WorkflowSpec.machine_for`, `lifecycle_states_in_order`, `lifecycle_edges`) is otherwise
  reachable only as a mermaid diagram inside `sq workflow show`, so a client wanting a status
  quick-pick would scrape markdown or parse a refusal string.
- **REV-736 F23** — a client rendering a sub-entity's field needs the field's declared *label*. The
  value is on `sq show --json`'s per-sub-entity `badges` map, but the label lives on
  `SubentityKindSpec.fields`, which needs its own surface (the type catalog's `fields` are the
  item's, not the kind's), as do `plural` and `local_prefix`.

The family's grammar was established by ADR-459 (`types`), generalized by ADR-474 (`collections`,
`statuses`) and extended by ADR-604 (`roles`): a
dedicated sub-command per catalog, a human Rich table by default and a bare JSON array under
`--json`, one row per declared entry in a deterministic order, a module-level frozen field-set
constant, every key present on every row, and cross-references carried **by name** so a client joins
catalogs rather than receiving denormalized copies.

Two facts make these one question rather than two adjacent ones. Both gaps are declared
`WorkflowSpec` maps without a catalog. And both bind the *same* value: `ItemSpec.lifecycle` and `SubentityKindSpec.lifecycle` name entries in the one
`lifecycles` map, so any design that inlines a machine into type rows must inline it a second time,
in a second shape, for kinds — which is precisely the divergence two separately-designed surfaces
would produce.

ADR-459 scoped a lifecycle catalog out, as a separate surface for a later decision; this is that
decision.

## Decision

### 1. The rule: one catalog command per declared spec map

The `sq workflow <catalog>` family is the machine surface for the workflow spec's declared
vocabulary, and it is **complete when every top-level declared map on `WorkflowSpec` has exactly one
catalog command**. Derived reverse indexes (`prefix_to_type`, `alias_to_type`) are excluded: they are
inversions any client can compute, and invariant 4 forbids publishing an inversion as though it were
declared.

The family is `types`, `collections`, `statuses`, `roles`, `subentity-kinds` (§3) and
`lifecycles` (§4), plus the catalogs later spec maps brought under the same rule: `ref-kinds`
(ADR-775) and `views` (ADR-1109). A spec map added later arrives with an obligation to publish a
catalog in this grammar; it does not get to invent a shape.

### 2. The row grammar every catalog follows

1. A dedicated sub-command. Human Rich table by default, `--json` emits a bare array.
2. One row per declared entry, in a documented deterministic order.
3. A module-level frozen field-set tuple, drift-tested against the model and golden-locked.
4. Every key present on every row — `null` for absent, never omitted.
5. **The identity key is the spec's own name for the thing, and every reference to it from another
   row uses that identical key name** (`status.role` joins `role.role`; `field.collection` joins
   `collection.collection`).
6. A reference carries a name, never an inlined copy of the target row. It names the identity key
   of the row it joins, and the target must be a declared spec map owed a catalog under rule 1, so a
   reference never names a target unresolvable in principle. Until its catalog exists a reference
   reads as a grouping key: equal values mean the same target.
7. Nested structure is an **array of fixed-key objects** — never a positional tuple, never a map
   keyed on adopter-declared vocabulary. A per-item payload may key on declared codes (the `badges`
   map does, legitimately); a catalog row may not, because a frozen key set is what makes it a
   contract and a strictly-typed client cannot type an adopter-controlled key space.

The type catalog's identity key `type` (for the `items` map) is the one historical exception to
rule 5. It is not a pattern to copy.

### 3. `sq workflow subentity-kinds --json`

One row per entry of `spec.subentity_kinds`, ascending kind name:

```json
{
  "subentity_kind": "finding",
  "lifecycle": "finding",
  "plural": "findings",
  "local_prefix": "F",
  "container_heading": "Findings",
  "completion": "Fixed",
  "maps_parent_story": false,
  "fields": [{"code": "severity", "label": "Severity", "collection": "severity"}]
}
```

- **`subentity_kind`** is the identity key — the map key, named as the spec names it, so the type
  row's reference (§5) is the same key name per rule 5. Not `kind`: `kind` already means ref-kind
  wherever a client sees `refs` (`"ID:kind"`), and in the `ref-kinds` catalog.
- **`fields`** reuses the type row's entry shape verbatim (`{code, label, collection}` — the same
  frozen entry tuple, not a parallel one). ADR-323 and ADR-348 both require that the sub-entity field
  mechanism is the item one unforked; the published shape is part of that requirement, and this is
  the field that carries the label a client renders.
- **`plural`** is the CLI list verb and the persisted container-marker name (ADR-348). A client that
  invokes the list verb or reads the marker must read it rather than guess a pluralization.
- **`local_prefix`** is the local-id prefix (`US`/`ST`/`F`). A client that renders or parses a local
  id needs it rather than hardcoding the grammar.
- **`container_heading`** is the resolved `## <heading>` above the kind's container block
  (`subentity_container_heading`): a bundled special-case table — "User Stories", which
  `"stories".title()` does not produce — falling back to title-cased `plural`. Published because a
  client that title-cases `plural` itself renders a heading that disagrees with the markdown sq
  writes into the file.
- **`completion`** is the done-target status inside this kind's own lifecycle — what a "mark done"
  action targets instead of hardcoding `Done`/`Fixed`. ADR-348 rules it declared, not derivable.
- **`maps_parent_story`** completes the column derivation. ADR-348 derives a kind's roll-up columns
  as a fixed base, plus one column per declared field, plus a story column iff this flag. A client
  handed `fields` but not the flag can build every column but the last, and would hardcode that one.
- **`placeholder` is not published.** Scaffold prose is content the engine writes into a file, not
  vocabulary a client resolves.

### 4. `sq workflow lifecycles --json`

One row per entry of `spec.lifecycles`, ascending lifecycle name:

```json
{
  "lifecycle": "work",
  "initial": "Draft",
  "states": ["Draft", "Ready", "InProgress", "Cancelled", "Blocked", "InReview", "Done"],
  "transitions": [{"from": "Draft", "to": "Ready"}, {"from": "Draft", "to": "InProgress"}]
}
```

- **`states`** is `lifecycle_states_in_order()` — BFS discovery order from `initial`, then any
  unreached state appended sorted. Its *membership* is derivable from `initial` plus `transitions`;
  its **order** is what the field adds, and the order is the contract. `Lifecycle.states` is a
  `frozenset`, so a client left to compute its own list gets a hash-seed-dependent order that
  reshuffles between runs and disagrees with sq's own diagram.
- The published order is **not** `linearize_lifecycle`'s spine-then-side-states ordering, which reads
  better to a human. That ordering canonicalizes side states through `_SIDE_PRIORITY`, a table keyed
  on **bundled status names**; publishing it would freeze a bundled-name-dependent ordering into a
  contract and degrade silently to something else for an adopter's own status names. A published
  order must be vocabulary-agnostic.
- **`transitions`** is one object per edge, in `lifecycle_edges()` order. Not `[[src, dst]]`: a
  positional pair cannot grow a named key, and this family's additive promise is made entirely of
  named keys. Not `{src: [dst, …]}`, which is how the spec stores it: that keys a catalog row's
  object on adopter-declared status names, which rule 7 forbids.
- The row does **not** carry which types or kinds bind it — that is the inversion of a forward edge
  (invariant 4) — and it does not carry per-state terminality, which is `role.settled` one join away
  and which this contract already states is deliberately duplicated nowhere.

### 5. Two reference fields on the type catalog

A decision adding a key to a catalog says so in its own body and names the catalog it extends
(ADR-459): this decision adds two keys to **ADR-459's `sq workflow types --json` row**, additively.

- **`subentity_kind`** — the declared kind this type hosts, or `null`. Without it the kind catalog is
  unjoinable: a sub-entity object in `sq show --json` carries no kind of its own, and the client is
  handed the item's `type`, so type→kind is the link in the resolution chain
  (`item.type` → type row → `subentity_kind` → kind row → `fields[].label`, keyed by the code the
  sub-entity's `badges` map carries). Forward edge per invariant 4; the kind row carries no
  reciprocal `parents` in return.
- **`lifecycle`** — the machine this type binds, joining §4's catalog. A declared binding choice, not
  derivable from anything else on the row.

### 6. When a derivable-looking field is legitimate

The family already carries one field that is pure redundancy: `reserved` is exactly
`category == "roster"`, and a client fetches it, shape-guards it and never reads it. The test that
separates it from `labels` (also recomputable, and rightly published) and from §4's `states`:

> **A catalog field is legitimate when re-deriving it would require a client to reimplement an engine
> algorithm that may change. It is redundant when a client could recompute it with a stable one-line
> rule over fields on the same row.**

`reserved` fails that test. `labels`, `container_heading`, and `states`' ordering pass it: each is an
engine derivation with special-case behaviour, and a client that re-derives it drifts from sq's own
output — the exact failure this family exists to prevent. No field is added to any catalog on
redundancy grounds.

### 7. What stays unpublished

`ItemSpec.folder`, `aliases`, `parents`, `parent_required`, `ref_rules`, `validators`, and
`SubentityKindSpec.placeholder` are declared vocabulary with no published field (a type's declared
`attributes` are published on its row, ADR-1007). Because the
family is additive-only, publishing any of them is a decision under §2's grammar and §6's test — not
a free extension. A frozen row that grows on convenience stops being a contract and becomes a spec
dump, and each key is permanent once shipped.

### 8. Stability tier

**Tier 2** for the grammar: one new `sq workflow` sub-command each, additive to the CLI surface. The
exit-code table is the family's — 0 on success, 1 when the spec refuses to load.

**Tier 3** for the payloads: additive-only. At 1.0 that commits us, per catalog, to: the command keeps
existing; every key keeps its name, type, presence and meaning; every row keeps every key, `null`
rather than omitted; the documented row order and the `states`/`transitions` orders hold; and a
reference field keeps naming the identity key of the row it points at. Growth is new keys only, each
one justified under §6. ADR-1025 qualifies what a key freezes: a key whose value is not a fixed
squads format is marked vocabulary, open set or display (in `ref-kinds`, `kind` is vocabulary,
`role` an open set, `label` and `hint` display), and moving a key to a looser class takes a decision
that names the shape. `docs/stability.md`'s Tier 3 table carries a row per catalog, and the joins
are documented in `docs/workflow.md`.

### 9. Delivery: by consumer for commands, by row for keys

Catalog **commands** may land separately, following the consumer that needs them. A row's **keys**
do not: a row ships whole, and a design that adds several keys to one existing row adds them in one
landing. An adopter reading a row experiences a key set, not a delivery plan, and every touch of a
row is a permanent Tier-3 event, so splitting one design's keys across landings costs two of
everything Tier 3 requires and shows the row growing twice for one design. Deferring a key buys
optionality only if it might still change. A key that references a catalog not yet published is
permitted under rule 6, and the adopter-facing docs say plainly that it has no catalog to join yet.

## Consequences

- A client resolves a sub-entity field's label from the kind row and its value from the `badges`
  map the payload carries: no client-side label map, no field-code literal.
- A lifecycle's initial state, state set, ordering and edges are machine-readable, and each machine is
  published once rather than copied onto every type that binds it (`work` is bound by three types,
  `subentity` by two kinds).
- The family is closed and auditable: one catalog per declared map, one grammar. A reviewer checks
  completeness by listing `WorkflowSpec`'s map fields.
- Each catalog is a pinned shape under the golden and drift-test discipline, the intended cost of a
  contract.
- `SubentityKindSpec.plural` has three consumers: CLI list verb, persisted container marker, and a
  published catalog value (ADR-348 records the coupling).
- A client can resolve which kind a type hosts, its local-id prefix, what its declared axes are
  called and its done-target status, instead of hardcoding them.

## Alternatives considered

- **Inline the machine on each type row** (`{initial, states, transitions}` per type — BUG-732's own
  first fix direction). Rejected: it denormalizes one machine onto every type that binds it, and it
  cannot serve sub-entity kinds, which bind lifecycles too and have no type row — so the machine ends
  up published twice in two shapes. That is the divergence this decision exists to prevent.
- **One combined `sq workflow spec --json`, or a `--json` on `show`.** Rejected: ADR-459 rejected
  overloading the cheatsheet callback — one command emitting two unrelated payloads — and a single
  nested document abandons the one-row-per-declared-entry grammar the catalogs teach a client to
  expect.
- **`transitions` as `{status: [status, …]}`**, mirroring `Lifecycle.transitions`. Rejected per
  rule 7: keyed on adopter-declared status names, it has no frozen key set, forces index signatures on
  a strictly-typed client, and cannot carry a future per-edge attribute.
- **Publish `states` and let clients derive the edges.** Rejected: the edges are the question BUG-732
  asks — "from Draft, what next?" — and no derivation over a state list produces them.
- **Publish the kind row's `fields` only**, the minimum a label needs. Rejected under §9: one design
  that makes an adopter watch one row grow keys twice is the additive promise being used as a
  substitute for deciding the row.
- **Hand-maintain a label map in the client as a stopgap.** Rejected: it is the same class of defect
  as the literal being removed.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T15:37:04Z] `architect` Robert Architect:
  - Authored on Olivia's commission: BUG-732 and REV-736 F23's label half answer one question, so they are one decision. The frame holds, with a refinement — "one decision" is not "one surface": the deliverable is the rule (one catalog command per declared `WorkflowSpec` map, under a fixed row grammar) and the two gaps are its first two applications. Two separately designed payloads was the risk; one design landing in two increments is not.
  - Shape checked against what the four shipped catalogs actually emit (`_cli/_workflow_cmd.py`), not against the ADRs alone. Row grammar §2 is descriptive of `types`/`collections`/`statuses`/`roles`, with one addition: nested structure is an array of fixed-key objects, never a map keyed on adopter-declared vocabulary — which is why `transitions` is `[{from,to}]` and not the `{src:[dst]}` shape the spec stores.
  - Release call: `subentity-kinds` + the type row's `subentity_kind` is 0.13, because F23's label half needs exactly that and nothing more, and TASK-737 ST3 already owns it. `lifecycles` + the type row's `lifecycle` is 0.14, the release BUG-732 assigns itself — no shipped consumer waits on it. F23 therefore has no residue: both halves land in 0.13.
  - Type-row `subentity_kind` is load-bearing, not a convenience: a sub-entity object in `sq show --json` carries no kind of its own and `SqShowJson` hands the client the item `type` only, so without it the kind catalog is unjoinable and F23's label lookup has no starting point. Verified by reading `build_subentity_json`, `_models/_subentity.py` and `clients/vscode/src/types.ts`.
  - Amended at the other end, both clause-level, neither superseded: ADR-474's "three catalogs project the whole spec vocabulary" is narrowed in place (overclaim), and ADR-348's `plural` risk note is widened in place (third consumer). ADR-459 needed no body edit — its own carried-forward rule (a decision adding a key to a frozen catalog says so in its body and names the catalog) is complied with in §5. `related` refs both ways on all three.
  - @tech-lead @op-pierre — left Proposed for the operator to read before accepting. The two judgement calls worth a second opinion: publishing `states` at all (§6's derivable-vs-legitimate test — membership is derivable, the ordering is not), and shipping the kind row whole in 0.13 rather than only its `fields` (§9).
- [2026-08-06T19:02:07Z] `op-pierre` Pierre Chat:
  - Accepted. Publish states -- a client computing its own order off a frozenset gets something that reshuffles between runs and disagrees with the diagram sq itself draws, and an unstable order in a published contract is worse than a field that looks redundant.
  - Ship the kind row whole in 0.13. Growing one row key by key across two landings costs two of everything Tier 3 requires and teaches adopters nothing except that we had not finished deciding.
- [2026-08-06T20:59:10Z] `architect` Robert Architect:
  - **Ruling (2026-08-06) on the §5/§9 fork: keep.** Both `subentity_kind` and `lifecycle` land on the type row in 0.13, and §9 is corrected in place to say so. §5 was right; §9's split was over-applied, and the contradiction was internal to §9 — its first paragraph accepts touching the frozen type row twice, and its second paragraph rejects exactly that pattern for the kind row ("costs two of everything Tier 3 requires and shows an adopter one row growing keys twice for a single design"). The second paragraph carries the principle; the first was the unreconciled one.
  - What settled it is that this decision **already ships a dangling `lifecycle` reference in 0.13** — deliberately, with reasoning: the kind row goes out whole, `lifecycle` included, and §9 calls that value "a usable grouping key" that "resolves to a catalog row once §4 lands". So the question was never whether an unjoinable lifecycle name is acceptable in this family; it was already answered yes. It was only whether the type row gets the same treatment as the kind row, and every reason given for the kind row applies with more force to ADR-459's older, more-consumed, already-frozen row.
  - On rules 5 and 6 specifically, since that was the part in doubt: neither is violated, and neither is engaged the way the fork assumed. Rule 5 constrains a reference's **key name** — that it matches the identity key of the row it points at — not the publication order of the target. Rule 6 forbids **inlining** the target row; a name with no published target is the most rule-6-compliant thing there is. And rule 1 is not breached from the other direction: `spec.lifecycles` is a declared map owed a catalog whether or not the type row names it, so the key neither creates that gap nor widens it. Rule 6 now states the general case, so the next contributor does not re-derive it: a reference may ship ahead of its target catalog, reading as a grouping key until the target lands, provided the target is a declared spec map already owed a catalog under rule 1 — a forward reference against a debt the family has taken on, never a name resolvable only on a maybe.
  - One correction to the premise, and it is the reason the amendment carries an obligation rather than just a permission: an adopter **cannot** cross-reference the value against `sq workflow statuses` in 0.13. That payload is a flat `{status, role, badge}` vocabulary with no lifecycle field, so nothing in the 0.13 surface exposes lifecycle membership at all. The value is a grouping key (equal values mean the same machine) and nothing more. §9 therefore now requires 0.13's adopter-facing entry and `docs/workflow.md`'s join table to say the reference has no catalog to join yet — a documented forward reference instead of an adopter hunting a command that does not exist. That doc line is the only new work this ruling creates; without it, "keep" really would teach the wrong thing.
  - Recorded as a clause-level correction in place: rule 6 extended, §5's `lifecycle` bullet annotated, §9 rewritten. No `supersedes` edge — nothing in another decision is narrowed, and ADR-459's row is extended additively exactly as §5 already declared. **No revert**: the shipped payload is correct as it stands, and the golden entry stays.
- [2026-08-06T21:06:25Z] `tech-writer` Theo Writer:
  - ADR-738 §9s adopter-facing condition is discharged for the 0.13 landing. The forward-reference caveat is stated in three places, in the same terms: the 0.13.0 CHANGELOG entry, `docs/workflow.md` § "Joining the catalogs", and `docs/stability.md`s Tier-3 catalog table. Each says lifecycle is a grouping key and nothing more, that equal values mean the same machine, and that no other --json surface exposes lifecycle membership — naming `sq workflow statuses` flat `{status, role, badge}` shape as the reason, which I verified rather than quoting.
  - Deliberately written without a roadmap: no surface says "0.14", "coming", "planned" or "not yet". The docs describe the key as it behaves today and tell the reader to stop looking for a resolver, which is the behaviour §9 asks for without committing the release the ADR assigns.
  - Two things I extended beyond the two files I was asked for, both because an exhaustive-looking list would otherwise have been wrong. `docs/stability.md`s Tier-3 catalog table listed four catalogs and a types row missing `subentity_kind`/`lifecycle` — a reader building against it would conclude the keys do not exist. It now carries the subentity-kinds row and the corrected types row, every field list checked key-for-key and in order against the live payload, plus §2 rule 4 (every key on every row, null not omitted) and rule 5 (a reference carries the target identity key name) stated where a client will look for them. @architect flagging in case §8s "gains a row per catalog" was meant to wait for the second landing — the row is accurate for what ships now either way.
- [2026-10-16T11:18:11Z] `architect` Robert Architect:
  - 2026-10-16: one dated note added after section 8 for ADR-1025 (ref-kinds row discharged; value classes); nothing else in the body changed.
- [2026-10-25T21:46:29Z] `architect` Robert Architect:
  - 2026-10-25 audit: partly stale, targeted present-tense edits; the rule, row grammar and the two catalogs are unchanged. §1 now lists the family as it stands, including ref-kinds (ADR-775) and views (ADR-1109) added under the same rule; §7 no longer lists extra_fields as unpublished (attributes is on the type row, ADR-1007); folded the ADR-1025 note into §8; §9 states the by-consumer/by-row delivery rule without the 0.13/0.14 plan; Consequences drop the F22/F23 closure narrative and the stale 8-lifecycles/10-types count.
<!-- sq:discussion:end -->
