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
updated_at: '2026-10-25T21:37:18Z'
---
<!-- sq:body -->
# Context

A client needs a human-readable name for each item type: "Decisions", not the raw
`decision`; "ADRs", not `adr`. Without a single authority, every client derives one ad hoc
(`type.capitalize()`, or the bare lowercase type key), and no ad-hoc derivation can spell an
acronym type correctly (`"ADR".lower()` → `"adr"` is wrong in running prose). `ItemSpec` carries per-type vocabulary already (`prefix`, `folder`,
`aliases`); a display name is the missing piece of that same vocabulary.

# Decision

Each item type takes an OPTIONAL nested `labels` table, in a project's `.overrides/workflow.toml`
or in the bundled spec (`src/squads/_specs/workflow.toml`), declared only where derivation would
get a form wrong (no bundled type needs one):

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

**Schema binding.** A frozen `LabelSpec` value object (`model_config` frozen +
`extra="forbid"`, matching its siblings) with the four `str | None = None` fields, added as
`ItemSpec.labels: LabelSpec | None = None`, optional with a default; `ItemSpec`'s
`extra="forbid"` already rejects a misspelled sub-key. Direct precedent on the sibling axis:
`SubentityKindSpec.plural` is a CLI/display-vocabulary field alongside its behavioural
fields — a display name belongs in the same schema, not bolted on elsewhere.

**Resolver seam.** Resolution needs the type name (it is the fallback source), so it cannot
live on the value object alone. One authoritative resolver sits beside `prefix_for(type_str,
spec)` in `_models/_vocab.py` (the seam ADR-266 established):

```
label_for(type_str: str, form: str, spec) -> str
```

where `form` is one of `singular` / `plural` / `singular_lower` / `plural_lower`. It reads
`spec.items[type_str].labels`, returns the pinned form when present, else the computed
fallback for that form (`_fallback_label`, the one place the formula lives). An undeclared type
or a missing spec is not an error: a display label is always derivable from the type name. Python
consumers (templates, the TUI) route through `label_for` instead of calling `.capitalize()`
themselves; machine clients read all four resolved forms from the `labels` key of each
`sq workflow types --json` row, a key this decision adds to ADR-459's catalog.

**No schema bump.** The table is workflow-spec vocabulary, never item data, so it carries no
`SCHEMA_VERSION` change and no migration.

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

- One resolver (`label_for`) is the single authority for an **item type's** display name; no
  consumer derives a *type* label itself. Other labels (a category label, for one) are not item
  types and are outside this resolver.
- Acronym and irregular-plural types render correctly across every client.
- No new reserved surface, no closed vocabulary, no migration — the field is optional and
  self-describing, and `extra="forbid"` guards typos.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-24T11:43:31Z] `op-pierre` Pierre Chat:
  - The four forms are independent (not lowercase-derived from the capitalized) specifically to spell acronym/initialism types right: 'ADR'.lower() is 'adr', which is wrong in running prose. Named forms over a positional list so a misordered override can't silently mean the wrong thing.
- [2026-08-03T08:47:17Z] `architect` Robert Architect:
  - Verified in force mechanically (`LabelSpec`, `ItemSpec.labels`, `label_for` beside `prefix_for` in `_models/_vocab.py`, four independent forms with derivation fallback). Two prose fixes and the structural one.
  - The structural finding: this decision shipped with no refs at all, the only one in its generation, so it was invisible from the reference graph in both directions while standing on three neighbours — it parallels ADR-323s `Field.label` one axis over, cites ADR-348s `SubentityKindSpec.plural` in prose as its precedent, and silently extended ADR-459/474s frozen type-catalog row with `labels`. Edges added to all four. Worth stating as a general point: an empty ref set makes an ADR unreviewable for exactly the overlaps this audit exists to find, because nothing leads a reader to it.
  - Scoped the retire-ad-hoc-`.capitalize()` consequence to item-type labels. As written it read as a blanket retirement of `.capitalize()` in display code, which the tree contradicts — a category label is not an item type and is still derived that way. Not a violation, an over-claim. Bundled spec path corrected in two places.
- [2026-10-25T21:37:18Z] `architect` Robert Architect:
  - 2026-10-25 audit: partly stale, targeted present-tense edits; the decision (optional four-form labels, label_for resolver) is unchanged. Removed the "today no authority" context and the consumer list naming _backend.py and VS Code calling label_for (the client reads the resolved labels from sq workflow types --json; label_for is used by templates and the TUI); recorded that the labels key extends ADR-459's catalog; no bundled type pins labels; dropped the SCHEMA_VERSION "0.11" snapshot. Folded the 2026-08-03 scoping and removed the amendment note (its refs stand).
<!-- sq:discussion:end -->
