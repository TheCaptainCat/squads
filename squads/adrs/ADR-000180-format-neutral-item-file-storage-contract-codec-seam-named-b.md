---
id: ADR-000180
sequence_id: 180
type: decision
title: 'Format-neutral item-file storage contract: codec seam + named body/prose regions'
status: Proposed
author: architect
refs:
- FEAT-000177:addresses
- ADR-000179
description: Split the store into a format-agnostic locator and a pluggable codec;
  define body regions as named fields, not text spans, so the two invariants hold
  across markdown/JSON/XML
created_at: '2026-06-23T12:59:22Z'
updated_at: '2026-06-23T12:59:42Z'
---
<!-- sq:body -->
## Context

`FEAT-000177` wants `format = json | xml | markdown` in `.squads.toml`. The feature names two engine
invariants this collides with and routes the resolution to this ADR.

**Invariant 1 — frontmatter is the source of truth.** Today the per-item `.md` file is authoritative
and `.squads.json` is a rebuildable index (`sq repair` proves it). "Frontmatter" is a markdown-ism:
in `_sections.py` it is the leading `---`-delimited YAML block, parsed by `split_frontmatter` and
mapped to/from the model by `_itemfile.py` (`from_frontmatter` / `to_frontmatter_dict`). The durable
truth is not *YAML* specifically — it is **the structured field set + the body regions** that the
model round-trips. `.squads.json` keys items by integer `sequence_id` and reconstructs everything
from those files.

**Invariant 2 — marker-safe edits only.** `_sections.py` only ever edits content *between* a
section's open/close marker (the `sq:tag` open and `sq:tag:end` close comment tags), leaving the marker lines and
the surrounding agent-authored prose verbatim (`replace_section`, `append_to_section`). This is the
mechanism that lets `sq` rewrite managed regions while never clobbering an agent-authored body. The
comment-tag machinery is **markdown-specific**; in JSON/XML there are no comment lines to delimit a
span — body and prose regions naturally become **named fields/elements**.

The real invariant underneath both is therefore *format-independent*:

> The item file is the source of truth; `sq` may rewrite the **structured fields** and the
> **managed sub-regions of each named body/prose region**, but must never destroy or wholesale-
> rewrite the **agent-authored content** within those regions.

The job of this ADR is to state that invariant format-neutrally and define the contract each codec
must satisfy so the invariant holds for JSON and XML exactly as it does for markdown.

## Decision

**1. Separate the store into a format-agnostic *locator* and a pluggable *codec*.** This is the
same `ItemStore` seam introduced in the `FEAT-000176` ADR (cross-reference). The locator (identity +
path) is format-neutral; the **codec** is the new pluggable piece this feature adds:

```
ItemCodec:
    parse(bytes|str)                  -> (fields: dict, regions: dict[str, BodyRegion])
    serialize(item, regions)          -> bytes|str          # full-file (re)write
    set_region(file, name, new_inner) -> file               # managed-region edit, agent prose intact
    list_markers(file)                -> set[str]            # for repair/lint parity
    file_suffix                       -> ".md" | ".json" | ".xml"
```

The markdown codec wraps today's `_sections.py` verbatim (frontmatter ↔ fields, `replace_section` ↔
`set_region`). JSON and XML codecs implement the same surface.

**2. Define body/prose regions as a format-neutral model, not as text spans.** A `BodyRegion` is a
**named region with an agent-authored payload plus optional managed sub-regions** — the
generalization of "the text between the `sq:body` open tag and its close". The markers move from being
*delimiters in a text stream* to being *keys in a structured container*:

- **Markdown:** region name = the marker tag; payload = the span between open/close markers;
  managed sub-regions = nested marker pairs. (Unchanged from today.)
- **JSON:** region name = a field key; payload = a string field; managed sub-regions = a nested
  object. e.g. `{"fields": {...}, "regions": {"body": {"prose": "...", "managed": {...}}}}`.
- **XML:** region name = an element; payload = its text/CDATA; managed sub-regions = child elements
  with a reserved `sq` namespace prefix.

The contract requirement: `set_region(name, inner)` replaces **only** the managed portion of the
named region and round-trips the agent-authored payload byte-for-byte. Whether that is enforced by
marker-span editing (markdown) or by structured-field replacement (JSON/XML) is the codec's private
business. Invariant 2 is then *satisfiable* in every format, not silently dropped.

**3. Restate "source of truth" per format.** The authoritative artifact is **the item file in the
active format**; `.squads.json` is its index regardless of codec. `sq repair`:

- discovers files by the **active codec's suffix** (and the locator's layout), then
- `codec.parse` each → `(fields, regions)` → rebuild the index.

The conformance requirement (already in the feature's acceptance): for any supported codec, the
round-trip `parse → serialize → parse` is identity over fields + region payloads, and `repair`
rebuilds an index byte-identical to the pre-repair index. This is the test that *proves* invariant 1
holds for non-markdown formats.

**4. One active format per squad; cross-format is a migration, not a live mix.** `format` selects the
codec for the whole squad. Reading a *foreign*-format file is supported only by `sq repair`/a
`sq migrate` converter (the feature asks for "repair can ingest any supported format and rebuild"),
so a team can convert markdown→JSON deterministically and reversibly. We do **not** support a squad
with mixed-format files in steady state — that multiplies the discovery + uniqueness surface for no
stated value.

## Relationship to FEAT-000176 (shared seam)

The two ADRs share the `ItemStore` abstraction and must stay consistent:

- **`FEAT-000176` ADR — locator half:** id-string (prefix) + path (layout). Format-agnostic.
- **This ADR — codec half:** serialize/parse + `BodyRegion` contract. Layout-agnostic.

They compose on two axes: a JSON squad can be flat or nested with a custom prefix, because the codec
never sees the path and the locator never sees the bytes. Recommendation: land `FEAT-000176`'s
locator + the markdown codec (a no-op refactor that wraps `_sections.py`) **first** as the
characterization baseline; then JSON and XML codecs are added against a green conformance suite.

## Consequences

- **Markdown stays the default and is unaffected** — the markdown codec is today's behavior behind a
  new seam; existing squads need no migration (matches acceptance).
- **`_sections.py` is no longer touched directly by services.** All body edits route through
  `codec.set_region`; the marker functions become the markdown codec's implementation. This is a
  real refactor of the service layer's body-edit calls and must be done before any second codec, or
  invariant 2 leaks.
- **The "marker" vocabulary generalizes to "managed region."** `find_markers`/`list_markers`,
  `has_section`, and `sq check`'s marker-integrity rules need a codec-provided equivalent so
  `sq check` stays meaningful in JSON/XML (e.g. "every required region present and well-formed").
- **Schema/format are independent.** `schema_version` (field shape) and `format` (serialization) are
  orthogonal; a format swap is not a schema migration and must not bump `SCHEMA_VERSION`.
- **Human-readability trade-off is explicit per the feature's own framing:** JSON/XML squads lose the
  on-GitHub readability that motivated markdown; that is the team's opt-in choice via config.

## Alternatives considered

- **Keep markers literally in every format (e.g. embed the `sq:body` comment-tag strings inside a JSON
  value).** Rejected: defeats the point of a structured format, fragile to JSON/XML escaping, and
  forces a markdown parser to live inside the JSON codec.
- **Drop invariant 2 for structured formats ("the whole file is managed, rewrite freely").**
  Rejected: agents author prose in `body`/`discussion`; wholesale rewrite would clobber it. The
  named-region contract preserves the guarantee cheaply.
- **Per-file format (mixed squad).** Rejected: multiplies discovery/uniqueness surface with no stated
  value; conversion is handled by repair/migrate instead.

## Status

Proposed — drafting only. No implementation, tasks, or feature transition until accepted.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
