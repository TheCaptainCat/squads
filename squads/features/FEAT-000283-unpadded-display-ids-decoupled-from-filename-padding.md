---
id: FEAT-000283
sequence_id: 283
type: feature
title: Unpadded display IDs, decoupled from filename padding
status: Draft
parent: EPIC-000012
author: product-owner
refs:
- ADR-000282:implements
- FEAT-000027
subentities:
- local_id: US1
  title: IDs read unpadded on every human-facing surface (frontmatter, refs, prose,
    CLI, tables)
  status: Todo
- local_id: US2
  title: Files stay padded and lexicographically sorted on disk while the id is unpadded
  status: Todo
- local_id: US3
  title: 'An existing squad migrates cleanly: structural id/refs + bounded prose rewrite,
    code fences untouched'
  status: Todo
- local_id: US4
  title: 'CLI lookup stays width-tolerant: FEAT-283 and FEAT-000283 both resolve'
  status: Todo
- local_id: US5
  title: Managed artifacts and goldens regenerate to unpadded; managed-section diff
    verified clean
  status: Todo
created_at: '2026-07-02T09:36:33Z'
updated_at: '2026-07-02T09:37:25Z'
---
<!-- sq:body -->
## Problem

Every item ID is rendered with a hard-coded 6-digit zero pad (`FEAT-000283`, `TASK-000030`). That
width exists for **one** reason that matters: on-disk filenames sort lexicographically. Everywhere a
human reads an ID — frontmatter `id:`, refs, ID mentions in body prose, CLI output, tables — the
padding is pure noise. `FEAT-283` is the JIRA-style form people say and type; `FEAT-000283` is the
form the tool insists on echoing back. This decouples the two: display goes unpadded, the filename
width stays. Authoritative design: **ADR-000282** (Proposed). Sibling of **FEAT-000027**, which owns
the stored padding + `repad` migration this feature reinterprets.

## Scope — exactly two changes (no config knob)

1. **Every human-facing surface renders unpadded.** Frontmatter `id:`, refs, prose ID mentions, CLI
   output, and tables all read `FEAT-283`. Display padding becomes a fixed **0**: `Item.id_padding`
   is a constant `0` (not a stored or configurable field), and `_propagate_padding` stamps `0`
   squad-wide so `Item.id` → `format_item_id(prefix, seq, 0)` → `FEAT-283`.
2. **The existing index-stored `SquadsDB.padding` is reinterpreted as the *filename width only*.**
   It is consumed exclusively at the filename-building seam, never for display. **No new config
   surface, no second stored field, no `.squads.toml` change.** It stays a derived/cached value in
   `.squads.json` exactly as today: `sq repair` re-derives it from disk (`max(stored, max observed
   filename width)`); `sq migrate repad` widens it on counter overflow. Invariant #1 holds — the
   width is fully reconstructable from the `.md` files, so nothing irreproducible is stored.

## The filename-seam crux (the one load-bearing divergence)

Under the new model `item.id` is `FEAT-283` but the file must stay `FEAT-000283-slug.md`. Today the
filename is built by concatenating the computed `item.id` — the crux site is
`src/squads/_services/_items.py:137` (`_rename`):

```python
new_rel = self.paths.squad_relative(item.type, f"{item.id}-{new_slug}.md", spec=self.spec)
```

Every site that **locates or creates a file** by concatenating `item.id + slug` must instead format
the **padded** name explicitly from the sequence number:
`format_item_id(item.prefix, item.sequence_id, db.padding)` — the index-stored `padding` as the
filename width. Audit all such path-builders (rename/create, `item_file` resolution, any
retype/renumber path). This is a footgun for anyone assuming "filename stem == id": it needs a
**comment at each such call site** and an **invariant test** (assert the file exists at the padded
name while the frontmatter carries the unpadded id).

`format_item_id` already takes the width as a parameter (`_models/_item.py:26`), so this is not a new
formatting path — it is the *same* formatter called with two widths: `0` for display, stored
`padding` for filenames.

## CLI input stays lenient for free

Lookups already resolve via `ref_id_matches` (`_item.py:62`, matches on `(prefix, int sequence_id)`)
and the sequence-keyed index, so `sq show FEAT-283` and `sq show FEAT-000283` both resolve regardless
of stored width. **No input-parsing change** — only *output* narrows to unpadded. Keep a test that
both widths resolve.

## Migration — structural + prose, gated on a schema bump

`SCHEMA_VERSION` is `"0.5"` today; bump it (compare via `schema_tuple`) and add a `Migration` record
+ `_vN_to_vM.py` runner to `_migrations/_registry.py`. The root callback already hard-stops on a
schema mismatch until `sq migrate up` runs. The runner:

1. **Structural (deterministic):** rewrite each frontmatter `id:` and every ref to the unpadded form,
   driven by `sequence_id`.
2. **Prose (bounded):** rewrite padded ID mentions in body prose to unpadded — same class of edit as
   the renumber path's `rewrite_ids` (`_itemfile.py:45`, `\bOLD\b → NEW`). **Bound it to the exact
   old-form strings the migration already knows** (iterate the index's `{padded → unpadded}` map per
   item); never a blind "collapse any run of zeros" pattern, which could maul unrelated text. **Skip
   fenced code blocks / inline code** where an ID may be a literal example, matching how
   `retype`/renumber scope their mention rewrites.
3. **Filenames untouched** — already width-6, stay width-6. No renames → no git-rename churn, no path
   rewrite beyond `repair`.
4. `.squads.json` rebuilt by the trailing `repair`, re-deriving both widths from disk.

The `manual` runbook should note the prose rewrite is best-effort and worth an eyeball on
mention-heavy bodies.

## Golden churn (mechanical but broad)

Managed artifacts embed example / real item IDs: the `sq-<type>` skills, the `squads`/`greeting`
skills, the CLAUDE.md / AGENTS.md managed sections, and `sq workflow`. Roster/roadmap prose cites
real IDs (`FEAT-000027`, `EPIC-000012`). All of these shift to unpadded → **regenerate every golden
fixture** and run the **managed-section diff check** the way we do on item-type changes (see the
"verify .claude artifacts on item-type changes" discipline). Expect a sizeable but purely mechanical
golden diff in the implementing PR.

## Acceptance criteria

- `Item.id` renders unpadded (`FEAT-283`) in frontmatter `id:`, refs, and every CLI surface
  (show/list/tree/tables/JSON); `id_padding` is a fixed constant `0`, not stored or configurable.
- On disk, files remain padded (`FEAT-000283-slug.md`) and stay lexicographically sorted; the
  index-stored `padding` is understood as filename width and is consumed **only** at path-builder
  seams via `format_item_id(prefix, sequence_id, db.padding)`.
- An invariant test asserts: file exists at the padded name **while** its frontmatter `id:` is
  unpadded — for create *and* rename/retype paths. Each such call site carries a clarifying comment.
- `sq show`/lookup resolves both `FEAT-283` and `FEAT-000283` (input tolerance unchanged; a test
  pins both).
- No `.squads.toml` change; no new stored field. `sq repair` re-derives the filename width from disk;
  `sq migrate repad` still widens it; the capacity/overflow check keys off the same stored padding.
- Schema bumped from `0.5`; `sq migrate up` runs the structural (id/refs) + prose (bounded,
  code-fence-skipping) rewrite; filenames untouched; trailing `repair` rebuilds `.squads.json`.
  A migration test covers a mixed fixture (padded frontmatter/refs/prose + a code fence that must be
  left alone) and asserts it lands unpadded and idempotent.
- Golden fixtures regenerated; managed-section diff verified clean; `sq check` green;
  `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean.

## Out of scope / non-goals

- No user-configurable display width — display is fixed unpadded, full stop.
- No filename renames (widths unchanged); no `repad` retarget.
- No change to identity, the global counter, or ref resolution — `sequence_id` stays the identity.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 283 add-story "As a <role>, I want … so that …"`; track with `sq feature 283 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | IDs read unpadded on every human-facing surface (frontmatter, refs, prose, CLI, tables) |
| US2 | Todo |  | Files stay padded and lexicographically sorted on disk while the id is unpadded |
| US3 | Todo |  | An existing squad migrates cleanly: structural id/refs + bounded prose rewrite, code fences untouched |
| US4 | Todo |  | CLI lookup stays width-tolerant: FEAT-283 and FEAT-000283 both resolve |
| US5 | Todo |  | Managed artifacts and goldens regenerate to unpadded; managed-section diff verified clean |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — IDs read unpadded on every human-facing surface (frontmatter, refs, prose, CLI, tables)

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
_Write the user story (e.g. “As an <role>, I want … so that …”) and its acceptance criteria here — free-form paragraphs or bullet lists._
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Files stay padded and lexicographically sorted on disk while the id is unpadded

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
_Write the user story (e.g. “As an <role>, I want … so that …”) and its acceptance criteria here — free-form paragraphs or bullet lists._
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — An existing squad migrates cleanly: structural id/refs + bounded prose rewrite, code fences untouched

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
_Write the user story (e.g. “As an <role>, I want … so that …”) and its acceptance criteria here — free-form paragraphs or bullet lists._
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — CLI lookup stays width-tolerant: FEAT-283 and FEAT-000283 both resolve

<!-- sq:story:US4:head -->
**Status:** ⚪ Todo
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
_Write the user story (e.g. “As an <role>, I want … so that …”) and its acceptance criteria here — free-form paragraphs or bullet lists._
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Managed artifacts and goldens regenerate to unpadded; managed-section diff verified clean

<!-- sq:story:US5:head -->
**Status:** ⚪ Todo
<!-- sq:story:US5:head:end -->

<!-- sq:story:US5:body -->
_Write the user story (e.g. “As an <role>, I want … so that …”) and its acceptance criteria here — free-form paragraphs or bullet lists._
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
