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
updated_at: '2026-07-04T20:29:02Z'
---
<!-- sq:body -->
## Context

Every item ID is rendered with a hard-coded 6-digit zero pad (`FEAT-000210`, `TASK-000030`).
That width serves exactly one purpose that actually matters: **on-disk filenames sort
lexicographically** (`features/FEAT-000001-…` before `FEAT-000010-…`). Everywhere a human reads
an ID — the frontmatter `id:`, refs, ID mentions in body prose, CLI output, tables — the padding
is pure noise. `FEAT-210` is the JIRA-style form people say and type; `FEAT-000210` is the form
the tool insists on echoing back.

The padding is already a single, well-factored knob:

- `format_item_id(prefix, sequence_id, padding=DEFAULT_ID_PADDING=6)` in `_models/_item.py` is
  the one canonical formatter; every `:0Nd` rendering routes through it.
- `Item.id` is a computed field that formats `prefix + sequence_id` at `self.id_padding`, which
  `SquadsDB._propagate_padding` stamps squad-wide from the stored `SquadsDB.padding`.
- Identity is already width-independent. `ref_id_matches` (`_item.py:62`) compares on
  `(prefix, integer sequence_id)`, not the string, and the index is keyed by the int
  `sequence_id`. So `FEAT-210` and `FEAT-000210` already resolve to the same item — correctness
  never depended on the string width. `sq migrate repad` (FEAT-27) exists precisely because
  the width is meant to be changeable squad-wide.

The single thing the current design conflates is that **filename width and display width are the
same number** (`SquadsDB.padding`). Decoupling them is the whole decision.

This refines ADR-104: the corpus-derived floor mechanism it established (the padding stored as a
floor in the index, `repair` recomputing it from the observed filename width, `repad` widening it on
counter overflow) is preserved exactly — only the stored `padding` parameter's consumer narrows,
from "all ID formatting" to "filename formatting only."

## Decision

**Add no config knob for padding.** The change collapses to exactly two things:

1. **Every human-facing surface renders unpadded** — the frontmatter `id:`, refs, prose ID
   mentions, CLI output, and tables all read `FEAT-210`. Display padding is simply a fixed **0**;
   `id_padding` becomes a constant `0`, not a stored or configurable field.
   `format_item_id(prefix, seq, 0)` yields `FEAT-210`.
2. **The existing index-stored `padding` is reinterpreted as the *filename* width** and consumed
   only at the filename-building seam — never for display.

There is **no new config surface, no second stored field, and no `.squads.toml` change.** Filename
padding is *not* user-configurable and does not appear in `.squads.toml`. It lives only in
`.squads.json` (the index) exactly as `SquadsDB.padding` already does today: a derived/cached value
that `sq repair` re-computes from disk (`max(stored_padding, max observed filename width)`, keyed off
`max sequence_id`) and that `repad` widens when the counter would overflow the current width.
Invariant #1 holds unchanged — the width is fully reconstructable from the on-disk files, so nothing
irreproducible is stored in the index.

Concretely: `_propagate_padding` stamps a constant `0` onto each `Item.id_padding` so
`Item.id` renders unpadded, and the filename layer reads `SquadsDB.padding` (now understood as the
filename width) directly. `format_item_id` already takes the width as a parameter, so this is not a
new formatting path — it is the *same two call sites* passing two different widths: `0` for display,
the stored `padding` for filenames.

**The crux of the implementation** is that the on-disk filename will no longer string-match the
frontmatter `id`. Today `_services/_items.py:137` builds a filename by concatenating the computed
`item.id`:

```python
new_rel = self.paths.squad_relative(item.type, f"{item.id}-{new_slug}.md", spec=self.spec)
```

Under the new model `item.id` is `FEAT-210` but the file must remain `FEAT-000210-slug.md`. Every
site that locates or creates a file by concatenating `item.id + slug` must instead format the
**padded** rendering explicitly from the sequence number —
`format_item_id(item.prefix, item.sequence_id, db.padding)`, using the index-stored `padding` as
the filename width. That divergence (padded on disk, unpadded in content) is the load-bearing
change; there is nothing else to thread — no config field, no second stored value.

**CLI input stays lenient for free.** Lookups already run through `ref_id_matches` /
sequence-keyed resolution, so `sq show FEAT-210` and `sq show FEAT-000210` both resolve whether
or not the caller matches the stored width. No input-parsing change is needed; only *output*
narrows to the unpadded form.

**Migration (structural + prose), gated on a schema bump.** Ship a `sq migrate` step (new
`SCHEMA_VERSION`, compared via `schema_tuple`, with a `Migration` record + `_vN_to_vM.py` runner)
that:

1. Rewrites each frontmatter `id:` and every ref to the unpadded form (structural — deterministic,
   driven by `sequence_id`).
2. Rewrites padded ID mentions in **body prose** to unpadded. This is the same class of edit as
   the renumber path's `rewrite_ids` (`_itemfile.py:45`), which does a `\bOLD\b → NEW` whole-word
   substitution. **False-match risk:** a bare `\bFEAT-000210\b → FEAT-210` regex is safe (the old
   padded token is highly specific), but the substitution must be **anchored to real IDs the
   migration already knows** (iterate the index's `{padded → unpadded}` map per item), never a
   blind "collapse any run of zeros" pattern — that could maul unrelated text. Bound it to the
   exact old-form strings and skip fenced code blocks / inline code where an ID may be a literal
   example, matching how `retype`/renumber already scope their mention rewrites.
3. **Leaves filenames untouched** — they were already width-6 and stay width-6. No renames, so no
   git-rename churn and no path-index rewrite beyond what `repair` does.
4. `.squads.json` is rebuilt by the trailing `repair`, which re-derives both widths from disk.

The `manual` runbook should note the prose rewrite is best-effort and worth an eyeball on
mention-heavy bodies.

## Consequences

- **Reads improve everywhere; identity is unchanged.** IDs read `FEAT-210` in frontmatter, refs,
  prose, and every CLI surface. The integer `sequence_id` remains the identity; nothing about
  uniqueness, the global counter, or ref resolution changes.
- **The padded/unpadded divergence must be respected at exactly one seam — the filename layer.**
  Any *new* code that reaches for a filename must format the padded form from `sequence_id`, not
  reuse `item.id`. This is a small, testable invariant (assert the file exists at the padded name
  while the frontmatter carries the unpadded id) but it is a footgun for anyone who assumes
  "filename stem == id" — worth a comment at the filename-building call site and a test.
- **Generated / managed artifacts need regen and golden updates.** Skills, the `CLAUDE.md` /
  `AGENTS.md` managed sections, and `sq workflow` embed example item IDs; the roster and roadmap
  prose cite real IDs (e.g. `FEAT-000027`, `EPIC-000012`). Any of these that render or hard-code a
  padded ID will shift to unpadded and their **golden fixtures must be regenerated**. This is
  mechanical but broad — expect a sizeable golden churn in the implementing PR, and verify the
  managed-section diff the way we do on item-type changes.
- **Migration is one-way in practice and needs a schema bump** (hard-stop in the root callback
  until `sq migrate up` runs). Existing squads get the prose rewrite once; the false-match bound
  above is what keeps it safe.
- **`repad` and the capacity check are unchanged.** `sq migrate repad` already operates on the
  index-stored `padding`, which is now simply understood as the filename width — it needs no new
  target. The "index full at width N" capacity check likewise keys off that same stored `padding`
  (the on-disk limit). Display never has a capacity concern (unpadded is width-independent).
- **Trade-off accepted:** we give up the convenience that "the filename tells you the exact `id`
  string." In exchange every human-facing surface reads cleanly. Given identity already lives in
  `sequence_id` and lookups are width-tolerant, that convenience was never load-bearing.

## Recommendation

Home the implementing feature under **EPIC-12 (Road to 1.0)**. This is a durable-`.md`-format
and CLI-grammar change — precisely the surfaces EPIC-12's stability promise governs — and it is a
sibling of FEAT-27 (padding + repad migration), which already lives there. Landing it
pre-1.0, behind a schema bump, is the right window; doing it after we freeze the format would make
it a breaking change instead of a settling one.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-04T20:18:38Z] Robert Architect:
  - Finalized for acceptance review (no body edit needed — verified complete, correct, and internally consistent; a rewrite would only churn updated_at).
  - Verified all five cited call-sites against the current tree: format_item_id (_models/_item.py:26, DEFAULT_ID_PADDING=6 at :23), ref_id_matches (_item.py:62), the filename seam in _rename (_services/_items.py:137 — the quoted squad_relative line matches exactly), rewrite_ids (_itemfile.py:45), and _propagate_padding (_index.py:59). All accurate.
  - Scrubbed for status/lifecycle prose: none present. status: Proposed lives only in frontmatter; the body carries no 'if/once accepted' banner. Decision is stated decisively; ADR shape is standard (Context / Decision / Consequences+trade-offs, with the config-knob alternative and the lost 'filename==id' convenience argued inline).
  - Reconciled against FEAT-283 — they agree on every load-bearing point: padding reinterpreted as filename width only, id_padding a fixed constant 0 (not stored/configurable), schema bump + structural(id/refs)+bounded prose migration with code-fence skipping, no .squads.toml change and no second stored field, and input tolerance unchanged (FEAT-283/FEAT-283 both resolve via ref_id_matches). No divergence to flag.
  - Refs correct: relates to FEAT-27 (sibling — stored padding + repad) and EPIC-12 (Road to 1.0); FEAT-283 links back with kind 'implements'. Forward-edges-only respected (no back-ref stored on the ADR).
  - @manager @op-pierre Recommend acceptance. Status is unchanged at Proposed — leaving the Accepted transition to Pierre's own read, per the gate. Once accepted this unblocks promoting FEAT-283 to Ready.
- [2026-07-04T20:29:02Z] Pierre Chat:
  - Accepted. Read the full ADR myself — the decision is sound and internally consistent, it agrees with FEAT-283 on every load-bearing point (no config knob, id_padding constant 0, padding reinterpreted as filename width only, schema bump + bounded prose migration, input tolerance unchanged), and it correctly refines ADR-104 without weakening the corpus-derived-floor mechanism. Approved for implementation.
<!-- sq:discussion:end -->
