---
id: ADR-646
sequence_id: 646
type: decision
title: Adopter-facing display labels per item type
status: Accepted
author: architect
refs:
- ADR-323
- ADR-348
- ADR-459
- ADR-474
description: Optional per-type labels table (four independent named forms, derivation
  fallback) + a label_for resolver so clients render pretty type names; acronym-safe,
  additive, no schema bump.
created_at: '2026-07-24T11:41:24Z'
updated_at: '2026-08-03T08:47:17Z'
---
<!-- sq:body -->
# Context

A client needs a human-readable name for each item type: "Decisions", not the raw
`decision`; "ADRs", not `adr`. Today no single authority yields that string — clients
derive one ad-hoc (`_backends/_claude_code/_backend.py` renders a section title via
`item_type.capitalize()`) or fall back to the bare lowercase type key, and none of the
ad-hoc paths can spell an acronym type correctly (`"ADR".lower()` → `"adr"` is wrong in
running prose). `ItemSpec` carries per-type vocabulary already (`prefix`, `folder`,
`aliases`); a display name is the missing piece of that same vocabulary.

# Decision

Add an OPTIONAL nested `labels` table to each item type in `.overrides/workflow.toml`,
mirrored in the bundled spec (`src/squads/_specs/workflow.toml`) only where it improves a built-in:

```toml
[items.decision.labels]
singular       = "Decision"
plural         = "Decisions"
singular_lower = "decision"
plural_lower   = "decisions"

[items.adr.labels]        # acronym: every form pinned, no derivation
singular       = "ADR"
plural         = "ADRs"
singular_lower = "ADR"     # stays capitalized in prose — why all four are independent
plural_lower   = "ADRs"
```

The four forms are **named and independent**, each individually optional, and the whole
`labels` table is optional. Every omitted form falls back to a value **computed from the
type-name string** (the dict key in `WorkflowSpec.items`):

- `singular` ⇐ `type.capitalize()`
- `singular_lower` ⇐ `type.lower()`
- `plural` ⇐ `singular + "s"` (naive)
- `plural_lower` ⇐ `singular_lower + "s"`

So a regular type needs zero config; an acronym or irregular type pins only the forms
derivation would get wrong.

**Schema binding.** A new frozen `LabelSpec` value object (`model_config` frozen +
`extra="forbid"`, matching its siblings) with the four `str | None = None` fields, added as
`ItemSpec.labels: LabelSpec | None = None`. Purely additive with a default; `ItemSpec`'s
`extra="forbid"` already rejects a misspelled sub-key. Direct precedent on the sibling axis:
`SubentityKindSpec.plural` is a CLI/display-vocabulary field alongside its behavioural
fields — a display name belongs in the same schema, not bolted on elsewhere.

**Resolver seam.** Resolution needs the type name (it is the fallback source), so it cannot
live on the value object alone. Add one authoritative resolver beside the existing
`prefix_for(type_str, spec)` in `_models/_vocab.py` — that module's own docstring already
anticipates a sibling accessor of exactly this shape:

```
label_for(type_str: str, form: str, spec) -> str
```

where `form` is one of `singular` / `plural` / `singular_lower` / `plural_lower`. It reads
`spec.items[type_str].labels`, returns the pinned form when present, else the computed
fallback for that form. (A small `labels_for(type_str, spec) -> LabelSpec`-shaped result may
back it if a caller wants all four at once, but `label_for` is the single call site
consumers use — the fallback logic lives in exactly one place.) Consumers route through it
instead of calling `.capitalize()`/`.title()` themselves: the Claude Code backend's per-type
section titles (`_backend.py`), the VS Code tree/list views, and any CLI per-type grouping
header. Their internals are out of scope here; this ADR fixes only the vocabulary + the
resolver they call.

**No schema bump.** An additive optional field with defaults reconstructs identically from a
spec that omits it, so `SCHEMA_VERSION` stays `"0.11"` — no migration.

# Rationale

- **Named forms over a positional `labels: list[str]`.** No magic index; a misordered
  override cannot silently mean the wrong thing, and a partial override reads unambiguously.
- **Four independent forms, not a lowercase derived from the capitalized one.** An acronym /
  initialism must keep its caps in running prose — deriving `singular_lower` by lowercasing
  `singular` would corrupt `ADR` → `adr`. Independence is what lets the spec represent those
  types correctly; it is the core reason for the shape.
- **Fallback-to-derivation** keeps this a pure, opt-in additive field: built-in and regular
  custom types need no config, and the bundled spec pins forms only where derivation is wrong or
  ugly.

# Consequences

- One resolver (`label_for`) becomes the single authority for an **item type's** display name; ad-hoc
  `type.capitalize()`/`.title()` derivations of a *type* label are retired in favour of calling it.
  *Scoped 2026-08-03: as first written this read as a blanket retirement of `.capitalize()` in display
  code. It is not — a category label, for one, is not an item type and is still derived that way. The
  claim is about type labels, which is the only thing this resolver knows how to answer.*
- Acronym and irregular-plural types render correctly across every client.
- No new reserved surface, no closed vocabulary, no migration — the field is optional and
  self-describing, and `extra="forbid"` guards typos.

## Amendment note

**2026-08-03 — refs added, and one consequence scoped to what it actually claims.** Mechanically verified
in force: `LabelSpec`, `ItemSpec.labels`, and `label_for(type_str, form, spec)` sitting beside `prefix_for`
in `_models/_vocab.py` exactly as the resolver-seam section specifies, with four independent forms and
derivation fallback.

This decision shipped with **no refs at all** — the only one in its generation to do so — which left it
invisible from the reference graph in both directions despite standing on three neighbours: it parallels
ADR-323's `Field.label` (the same "a code the engine keys on, a label the human reads" split, one axis
over), it cites `SubentityKindSpec.plural` (ADR-348) in prose as its precedent for a declared plural, and
it silently extended the frozen type-catalog row (ADR-459, as extended by ADR-474) with `labels`. Edges
added to all four. The lesson generalises past this decision: an ADR with an empty ref set is
unreviewable for exactly the overlaps this audit exists to find, because nothing leads a reader to it.

The bundled spec path is corrected in two places, and the retire-ad-hoc-`.capitalize()` consequence is
scoped to item-type labels, which is all the resolver can answer for.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-24T11:43:31Z] Pierre Chat:
  - The four forms are independent (not lowercase-derived from the capitalized) specifically to spell acronym/initialism types right: 'ADR'.lower() is 'adr', which is wrong in running prose. Named forms over a positional list so a misordered override can't silently mean the wrong thing.
- [2026-08-03T08:47:17Z] Robert Architect:
  - Verified in force mechanically (`LabelSpec`, `ItemSpec.labels`, `label_for` beside `prefix_for` in `_models/_vocab.py`, four independent forms with derivation fallback). Two prose fixes and the structural one.
  - The structural finding: this decision shipped with no refs at all, the only one in its generation, so it was invisible from the reference graph in both directions while standing on three neighbours — it parallels ADR-323s `Field.label` one axis over, cites ADR-348s `SubentityKindSpec.plural` in prose as its precedent, and silently extended ADR-459/474s frozen type-catalog row with `labels`. Edges added to all four. Worth stating as a general point: an empty ref set makes an ADR unreviewable for exactly the overlaps this audit exists to find, because nothing leads a reader to it.
  - Scoped the retire-ad-hoc-`.capitalize()` consequence to item-type labels. As written it read as a blanket retirement of `.capitalize()` in display code, which the tree contradicts — a category label is not an item type and is still derived that way. Not a violation, an over-claim. Bundled spec path corrected in two places.
<!-- sq:discussion:end -->
