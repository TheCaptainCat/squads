---
id: ADR-646
sequence_id: 646
type: decision
title: Adopter-facing display labels per item type
status: Accepted
author: architect
description: Optional per-type labels table (four independent named forms, derivation
  fallback) + a label_for resolver so clients render pretty type names; acronym-safe,
  additive, no schema bump.
created_at: '2026-07-24T11:41:24Z'
updated_at: '2026-07-24T11:43:47Z'
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
mirrored in the bundled `default_workflow.toml` only where it improves a built-in:

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
  custom types need no config, and the bundled `default_workflow.toml` pins forms only where
  derivation is wrong or ugly.

# Consequences

- One resolver (`label_for`) becomes the single authority for a type's display name; ad-hoc
  `type.capitalize()`/`.title()` display derivations are retired in favour of calling it.
- Acronym and irregular-plural types render correctly across every client.
- No new reserved surface, no closed vocabulary, no migration — the field is optional and
  self-describing, and `extra="forbid"` guards typos.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-24T11:43:31Z] Pierre Chat:
  - The four forms are independent (not lowercase-derived from the capitalized) specifically to spell acronym/initialism types right: 'ADR'.lower() is 'adr', which is wrong in running prose. Named forms over a positional list so a misordered override can't silently mean the wrong thing.
<!-- sq:discussion:end -->
