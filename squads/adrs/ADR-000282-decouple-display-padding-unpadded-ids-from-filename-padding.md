---
id: ADR-282
sequence_id: 282
type: decision
title: Decouple display padding (unpadded IDs) from filename padding
status: Accepted
author: architect
refs:
- FEAT-27
- EPIC-12
- ADR-104
description: Decouple display/canonical ID padding (unpadded, JIRA-style) from filename
  zero-padding (width 6, on-disk sort only); needs a schema bump + structural-and-prose
  migration.
created_at: '2026-07-02T09:28:28Z'
updated_at: '2026-10-25T21:18:11Z'
---
<!-- sq:body -->
## Context

An item number's zero padding serves one purpose that matters: on-disk filenames sort
lexicographically (`features/FEAT-000001-…` before `FEAT-000010-…`). Everywhere a human reads an
id (the frontmatter `id:`, refs, mentions in prose, CLI output, tables) padding is noise:
`FEAT-210` is the form people say and type.

Identity never depended on the string width. `ref_id_matches` compares on `(prefix, integer
sequence_id)` and the index is keyed by the integer `sequence_id`, so `FEAT-210` and `FEAT-000210`
resolve to the same item. `format_item_id(prefix, sequence_id, padding)` in `_models/_item.py` is
the one formatter, and `sq migrate repad` exists because the width is meant to change squad-wide.
The only thing to decide is that filename width and display width are different numbers.

This refines ADR-104: the corpus-derived floor it established (the padding stored as a floor in
the index, recomputed by `repair` from the observed filename width, widened by `repad`) is
preserved; only the stored padding's consumer narrows, from all id formatting to filenames.

## Decision

**There is no padding config knob.** Two things hold:

1. **Every human-facing surface renders unpadded.** `Item.id` formats at
   `DISPLAY_ID_PADDING = 0`, a constant in `_models/_item.py`: there is no padding field on `Item`
   and nothing stamps one. Frontmatter `id:`, refs, prose mentions, CLI output and tables all read
   `FEAT-210`.
2. **The index-stored `SquadsDB.padding` is the filename width**, consumed only at the
   filename-building seam: `SquadsDB.format_id` / `allocate_id` produce the padded stem
   (`FEAT-000210`) a file is named with.

Filename padding is not configurable and does not appear in `.squads.toml`. It lives only in
`.squads.json`, as a derived value `sq repair` recomputes from disk (no file's own number or digit
width can make it regress) and `repad` widens when the counter would overflow. Invariant #1 holds:
the width is reconstructable from the files.

**The filename no longer string-matches the frontmatter `id`.** Any code that locates or creates a
file must format the padded stem from the sequence number and the stored padding, never
concatenate `item.id` with a slug. That divergence, padded on disk and unpadded in content, is
confined to that one seam.

**Input stays lenient.** Lookups run through sequence-keyed resolution and `ref_id_matches`, so
`sq show FEAT-210` and `sq show FEAT-000210` both resolve. Only output is unpadded.

**Squads written with padded ids are converted by `sq migrate up`** (schema 0.5 → 0.7). The
migration rewrites each frontmatter `id:`, every ref and every `parent:` to the unpadded form, and
rewrites padded id mentions in body prose and sub-entity titles, matched whole-word against the
exact ids it knows (never a blind "collapse zeros" pattern), skipping fenced code, inline code and
filename references. It leaves filenames untouched, and the trailing `repair` rebuilds the index.

## Consequences

- Ids read `FEAT-210` everywhere; identity, uniqueness, the global counter and ref resolution are
  unchanged.
- "Filename stem == id" is false. New code that needs a filename must use the padded stem; tests
  assert a file exists at the padded name while its frontmatter carries the unpadded id.
- `repad` and the "index is full at width N" capacity check key off the stored filename width.
  Display has no capacity concern.
- The prose rewrite of the migration is best-effort, so its manual step advises an eyeball on
  mention-heavy bodies.
- Trade-off accepted: the filename no longer spells the exact `id` string, in exchange for clean
  ids on every surface people read.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-04T20:18:38Z] `architect` Robert Architect:
  - Finalized for acceptance review (no body edit needed — verified complete, correct, and internally consistent; a rewrite would only churn updated_at).
  - Verified all five cited call-sites against the current tree: format_item_id (_models/_item.py:26, DEFAULT_ID_PADDING=6 at :23), ref_id_matches (_item.py:62), the filename seam in _rename (_services/_items.py:137 — the quoted squad_relative line matches exactly), rewrite_ids (_itemfile.py:45), and _propagate_padding (_index.py:59). All accurate.
  - Scrubbed for status/lifecycle prose: none present. status: Proposed lives only in frontmatter; the body carries no 'if/once accepted' banner. Decision is stated decisively; ADR shape is standard (Context / Decision / Consequences+trade-offs, with the config-knob alternative and the lost 'filename==id' convenience argued inline).
  - Reconciled against FEAT-283 — they agree on every load-bearing point: padding reinterpreted as filename width only, id_padding a fixed constant 0 (not stored/configurable), schema bump + structural(id/refs)+bounded prose migration with code-fence skipping, no .squads.toml change and no second stored field, and input tolerance unchanged (FEAT-283/FEAT-283 both resolve via ref_id_matches). No divergence to flag.
  - Refs correct: relates to FEAT-27 (sibling — stored padding + repad) and EPIC-12 (Road to 1.0); FEAT-283 links back with kind 'implements'. Forward-edges-only respected (no back-ref stored on the ADR).
  - @manager @op-pierre Recommend acceptance. Status is unchanged at Proposed — leaving the Accepted transition to Pierre's own read, per the gate. Once accepted this unblocks promoting FEAT-283 to Ready.
- [2026-07-04T20:29:02Z] `op-pierre` Pierre Chat:
  - Accepted. Read the full ADR myself — the decision is sound and internally consistent, it agrees with FEAT-283 on every load-bearing point (no config knob, id_padding constant 0, padding reinterpreted as filename width only, schema bump + bounded prose migration, input tolerance unchanged), and it correctly refines ADR-104 without weakening the corpus-derived-floor mechanism. Approved for implementation.
- [2026-08-03T08:51:23Z] `architect` Robert Architect:
  - One symbol name corrected, and the divergence is in this decisions favour: there is no `id_padding` field on `Item` at all — the constant is inlined and `_propagate_padding` no longer stamps it. Same behaviour, one fewer field, and consistent with this decisions own "no second stored field" rule. Verified live: an unpadded display id with a width-6 filename, which is exactly the divergence the Crux section is about.
- [2026-10-25T21:18:11Z] `architect` Robert Architect:
  - 2026-10-25 audit: partly stale, body rewritten in the present tense; the decision (unpadded display, stored padding is the filename width, no knob) is unchanged. Removed the false claim that _propagate_padding stamps Item.id_padding = 0 (no such field or pass exists; DISPLAY_ID_PADDING is a constant) and the italic note that said so, replaced the pre-implementation _items.py:137 citation with the format_id/allocate_id seam, restated the migration as the shipped 0.5 to 0.7 runner (adds parent:, sub-entity titles and filename-reference skipping), and dropped the EPIC-12 homing recommendation.
<!-- sq:discussion:end -->
