---
id: REV-292
sequence_id: 292
type: review
title: 'Review: TASK-290 unpadded display IDs'
status: Approved
author: reviewer
refs:
- TASK-290:addresses
- FEAT-283
created_at: '2026-07-04T22:19:00Z'
updated_at: '2026-07-04T22:19:48Z'
---
<!-- sq:body -->
Independent read-only review of the working-tree diff implementing the display-unpadding half of the feature (unpadded `Item.id` everywhere, padded on-disk filename stem). Authoritative design: ADR-282; acceptance in FEAT-283 US1/US2/US4/US5. Schema bump + migration are intentionally out of scope (sibling task) and their absence was not treated as a defect.

## Verdict: Approved — no findings

The implementation is correct, complete, well-commented, and adequately tested. Independently verified against the tree, not off the dev's summary.

### What I checked

1. **Display unpadding is complete.** `Item.id` computes at the new `DISPLAY_ID_PADDING = 0` constant, unconditionally — so frontmatter `id:`, refs, prose, CLI (`show`/`list`/`tree`/tables/`--json`), and error hints all read unpadded. Grepped the whole of `src/` for `zfill` / `:06d` / `:0{...}d` / `id_padding`: every surviving width-formatting site is a *filename* seam (`_index.format_id`, `_maintenance` skill-seed names, `_v0_4` convention name) or the capacity check (`10**self.padding`), all correctly keyed to the filename width per the ADR. The three CLI error-hint sites in `_common.py` were correctly flipped to `DISPLAY_ID_PADDING`.

2. **Filename seam — the load-bearing invariant.** All file-building sites format the padded stem from `sequence_id` via `format_item_id(prefix, sequence_id, db.padding)`, never by concatenating the now-unpadded `item.id`: `_items._rename` (threads `db` in), `_retype.retype`, and the third site the original audit missed — `_maintenance._renumber_plan`, which now correctly mints `new_padded` (rename target) and `new_display` (the `rewrite_ids` remap target, unpadded content) separately. Create (`_base`) and repad/seed stay padded via `allocate_id`/`:0{db.padding}d`. Every seam carries an ADR-282 clarifying comment. The invariant test `test_rename_and_retype_keep_filename_padded_while_id_unpadded` asserts padded stem + unpadded frontmatter `id:` for rename and retype; create is covered by `test_create_allocates_id_and_writes_file` (also updated to assert both).

3. **`id_padding` fully removed as stored/configurable state.** The `Item.id_padding` field and `SquadsDB._propagate_padding` are gone; no construction site passes it; nothing reads it (the lone `_v0_4:149 fm.get("id_padding")` is a legacy frontmatter-key read, pre-existing and untouched — that field was always `exclude=True` so it never persisted, defaulting to 6 as before). No `.squads.toml` change, no second stored field. `SquadsDB.padding` is unchanged and now documented as filename-only.

4. **Entangled areas — no regressions.** `_index` capacity check keys off filename padding (correct per ADR). The `_v0_4_to_v0_5` edit is only the kwarg removal + a comment; display/filename are not conflated there. `rewrite_ids` uses `\bOLD\b` whole-word substitution, which is boundary-safe even for the shorter unpadded IDs (`FEAT-2` does not match `FEAT-20`), so the renumber path's unpadded remap is safe. New `SquadsDB` import in `_items.py` keeps the import graph acyclic (services → models).

5. **Golden / template / manifest churn is legitimate and purely mechanical.** Spot-checked goldens, the two regenerated skills (SKILL-192/200), and the three edited templates: every diff is padded→unpadded example IDs and nothing else. The manifest touched only the `0.6.0` entry — and `v0.6.0` is *not* tagged (latest tag is `v0.5.0`), so `0.6.0` is the current in-development version and its entry is the live one; the frozen `0.4.0`/`0.5.0` entries are untouched. No release-manifest gotcha.

6. **Project rules.** `uv run pyright` (0 errors), `ruff check` (clean), `ruff format --check` (clean). Targeted test subset (service/cli/retype/index/migrations/tree/prefix_resolver) green; dev reports full suite 1589 passed / 1 skipped. No sq/task IDs in source or test filenames (new tests live in behaviorally-named existing files). Marker lines untouched.

### Observation (not a finding)

This repo's own `.squads.json` now serializes unpadded computed `id` values (e.g. `"FEAT-13"`) while the dogfood `.md` frontmatter and stored `refs`/`parent` remain padded until TASK-000291's migration runs. This is harmless — `id` in the index is a computed/redundant field; identity and edges resolve by `sequence_id`, and `sq repair`/the migration reconcile it — and it is the expected transient state given the deferred migration. Flagging only so it is not mistaken for drift when the working tree is committed.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 292 add-finding "…" --severity high`; track with `sq review 292 finding <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:findings -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-04T22:19:47Z] Paul Reviewer:
  - Approved — no findings. Independently verified the diff against the tree (not off the dev's handoff): display unpadding is complete (Item.id at DISPLAY_ID_PADDING=0, all CLI/frontmatter/refs/hints unpadded), the filename seam holds at all four sites (create/rename/retype/renumber) with padded stems formatted from sequence_id and clarifying ADR-282 comments, id_padding is gone as stored/config state, and the golden/skill/manifest churn is purely mechanical (manifest touched only the live 0.6.0 entry; v0.6.0 is untagged). pyright/ruff clean, targeted tests green. Migration/schema absence is expected (TASK-291).
  - @python-dev @manager clean pass. One informational note in the review body: this repo's .squads.json now carries unpadded computed ids while frontmatter/refs stay padded pending TASK-291 — expected transient state, not drift.
<!-- sq:discussion:end -->
