---
id: ADR-266
sequence_id: 266
type: decision
title: 'Spec-derived per-type vocabulary: retire the static PREFIX/FOLDER/alias tables;
  stamp the prefix onto Item'
status: Accepted
author: architect
refs:
- FEAT-210:addresses
- REV-265:addresses
- ADR-322
created_at: '2026-07-01T07:40:18Z'
updated_at: '2026-10-25T21:16:52Z'
---
<!-- sq:body -->
## Context

A custom type declared with `prefix = "INC"` must get ids and files named `INC-19`, not a guess
derived from the type name. The `_models` layer is spec-unaware by convention: it never imports
`_workflow` (the layering and acyclic-import invariants, ADR-249), so `Item` cannot look up a
spec-declared prefix itself.

The failure that prompted this decision (REV-265 F1) was a family, not a line: the id was
formatted from a static type-keyed prefix table with a `type.upper()` fallback at three separate
sites (the computed `Item.id`, `SquadsDB.format_id` building the create-time filename, and a CLI
display path), and other ref and service paths indexed the same table directly and crashed on a
custom type. Every static per-type table (prefix, reverse prefix, folder, aliases, roster
membership) was a copy of what the spec already declares.

## Decision

**The resolved prefix is handed to the `Item` as a value; `Item.id` formats from it and never
looks anything up.**

1. **`Item.prefix` is a plain field** (`_models/_item.py`), excluded from the JSON dump. `Item.id`
   is `format_item_id(prefix, sequence_id)` at display width: no map lookup and no `type.upper()`.
   The model stores a string it was given; it does not derive vocabulary.
2. **One resolver answers "what is this type's prefix".** `prefix_for(type_str, spec)` in
   `_models/_vocab.py` is the single authority every call site uses (create, retype, the CLI, the
   service base, maintenance and skill-file paths). It reads the spec for every type and raises
   on an undeclared one (ADR-322 §1). `label_for` sits beside it on the same argument (ADR-646).
3. **The prefix is set where a spec is in hand, and recovered where it is not.**
   - Create resolves it with `prefix_for` before allocation and passes it to
     `SquadsDB.allocate_id`/`format_id`, so the filename stem and `Item.id` agree.
   - Retype re-stamps `item.prefix` from the target type.
   - Every read path (`from_frontmatter`, the JSON index) re-derives it from the persisted `id`
     (ADR-322 §3), so loading a file needs no spec.
4. **No call site reads a type-keyed vocabulary table.** Ref and id paths that hold an `Item` use
   `item.prefix`; everything else goes through the resolver, `spec.prefix_to_type`,
   `SquadPaths.folder_for` or `ItemSpec.aliases`. A sub-entity kind's plural is answered by the
   spec (`WorkflowSpec.subentity_plural`), not by this resolver.

## Alternatives considered

- **Inject a spec or resolver into `Item.id` / `from_frontmatter`.** Rejected: it couples the
  model to the spec, and a pydantic computed field cannot take an argument, so the spec handle
  would have to live on the model.
- **Have the model read an ambient, invocation-scoped spec.** Rejected: a pure data model would
  depend on global state, and the same file could render a different id depending on context.
  Context-bound spec resolution belongs to the CLI paths that run before the callback (ADR-263).
- **A built-in prefix map as the resolver's default, with the spec required only for custom
  types.** Rejected: an optional spec means a hardcoded answer for the names that skip it, which
  is a reservation of the built-in vocabulary. A file's spec-free round-trip is met by deriving
  the prefix from its own `id` instead.

## Consequences

- A custom type's id, filename and refs all carry its declared prefix and round-trip through
  `sq <type> <id> show`.
- The resolver seam let every static vocabulary table be deleted without touching a caller; the
  spec is the only vocabulary (ADR-322).
- Frozen migration runners keep their own literal vocabulary of their era; they are exempt by
  design.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-01T07:41:47Z] `architect` Robert Architect:
  - @manager @tech-lead ADR-266 (Proposed) decides how spec-derived per-type vocabulary reaches the spec-unaware _models layer and resolves REV-265 F1.
  - Decision: stamp a resolved prefix onto the Item as a stored-but-derived field (Item.prefix), and format Item.id from that field — never from a type-keyed lookup. Built-in prefixes come from ONE reserved-vocab resolver (the default); custom types get their prefix from spec.items[t].prefix, stamped at create/retype/load where the spec is already in hand (create already carries self.spec). Item stays spec-decoupled (ADR-249 Finding 1 preserved): it stores a string handed to it, it does not derive vocab. Rejected injecting a spec into Item.id (re-couples the model; computed_field can't take args) and an ambient contextvar the model reads (breaks frontmatter-as-truth).
  - F1 is NOT a one-liner: the SAME buggy PREFIX_BY_TYPE.get(type, type.upper()) is at THREE sites — _item.py:162 (Item.id), _index.py:74 (format_id → the create-time FILENAME, so the file is ALSO misnamed), and _common.py:557; plus _refs.py/_items.py use bracket PREFIX_BY_TYPE[type] which KeyErrors on custom types. Fixing only line 162 leaves the filename wrong and the ref paths crashing. Fix converges all sites on item.prefix / the resolver.
  - Retires (call-site reads): PREFIX_BY_TYPE, TYPE_BY_PREFIX, FOLDER_BY_TYPE (all fold into the single resolver's built-in defaults), the TYPE_ALIASES shim (consumers move to ItemSpec.aliases/spec.alias_to_type), and _META_NAMES. STAYS: the reserved built-in vocab map (resolver default + EPIC-206 reserved-type invariant); _KIND_BY_TYPE in _migrations/_v0_2_to_v0_3.py (frozen migration, exempt).
  - Feature boundary (recommendation, not a scope change): land prefix/folder/type-by-prefix/meta/alias-shim retirement + Item.prefix + resolver + the 3 format-site conversions + ref-path fix WITHIN the FEAT-210 corrective (this is exactly what makes INC-000019 round-trip and unblocks F1/F2). DEFER _SUBENTITY_PLURAL to FEAT-212 (subentity_kinds schema) — do NOT pull it forward; instead design the resolver so FEAT-212 reuses it (add a subentity_plural accessor when the field lands). Keep _SUBENTITY_PLURAL as the built-in fallback until then.
- [2026-07-01T08:27:48Z] `manager` Catherine Manager:
  - Accepted after reading the full Decision + Alternatives. Operator (op-pierre) confirmed the feature boundary: FEAT-210 corrective retires PREFIX_BY_TYPE / TYPE_BY_PREFIX / FOLDER_BY_TYPE / the TYPE_ALIASES shim / _META_NAMES via the Item.prefix + reserved-vocab resolver pattern; _SUBENTITY_PLURAL is DEFERRED to FEAT-212 (kept as built-in fallback), with the resolver designed so FEAT-212 adds a subentity_plural accessor when the subentity_kinds schema lands. Verified the three-site finding (_index.py:74 filename, _common.py:557, _refs.py bracket-KeyError) — the corrective is broader than REV-265 F1's single line.
- [2026-08-03T08:43:02Z] `architect` Robert Architect:
  - Section 2 marked withdrawn by ADR-322, which names this decision; sections 1 and 4 verified in force (`Item.prefix` as a field, `Item.id` formatting from it with no map lookup, `prefix_for` as the single resolver at `_models/_vocab.py:36` called from every site). Nothing retired.
  - The reversal is visible in the codes own words — `_vocab.py`s docstring now says the loaded spec is the sole vocabulary authority and there is no reserved prefix/folder map — so this was the easiest of the set to confirm and the least excusable to leave unrecorded.
  - Separated the two halves of section 2 in the note, because this decision was right about one and wrong about the other. The resolver seam was the durable contribution: one place answering "what is this types prefix", which is exactly what let the map behind it be deleted without touching a caller, and what `label_for` later joined (ADR-646). The optional spec was the part that encoded the reservation this arc existed to remove — an optional spec means a hardcoded answer for the names it does not need the spec for.
  - The constraint the optional spec was protecting — a file round-tripping its own id without a spec — is met better by ADR-322 section 3 as corrected, deriving the prefix from the persisted `id`. So nothing was lost by making the spec mandatory, which is the fact that makes this a clean narrowing rather than a trade.
- [2026-10-25T21:16:52Z] `architect` Robert Architect:
  - 2026-10-25 audit: partly stale, body rewritten in the present tense; the decision (stamp the resolved prefix on Item, format Item.id from it, one resolver) is unchanged. Removed the withdrawn §2 built-in prefix map and the amendment note, folding in ADR-322: prefix_for reads the spec for every type, and Item.prefix is not written to frontmatter but re-derived from the persisted id on read (the body still said a prefix line is written). Dropped the file:line citations, the retirement inventory of tables that no longer exist and the FEAT-210 sequencing section; noted that sub-entity plurals live on WorkflowSpec.subentity_plural.
<!-- sq:discussion:end -->
