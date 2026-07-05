---
id: TASK-290
sequence_id: 290
type: task
title: Unpadded display IDs, filename-seam divergence, golden regen
status: Done
parent: FEAT-283
author: tech-lead
refs:
- ADR-282
subentities:
- local_id: ST1
  title: id_padding becomes constant 0; every surface renders unpadded
  status: Done
  story: US1
- local_id: ST2
  title: Format padded filenames from sequence_id at rename/retype seams
  status: Done
  story: US2
- local_id: ST3
  title: 'Pin lookup tolerance: FEAT-283 and FEAT-000283 both resolve'
  status: Done
  story: US4
- local_id: ST4
  title: Regenerate managed artifacts + goldens; verify managed-section diff
  status: Done
  story: US5
created_at: '2026-07-04T20:45:37Z'
updated_at: '2026-07-04T22:20:34Z'
---
<!-- sq:body -->
## Scope

Land the display-unpadding half of the feature as one green PR: `Item.id` (and every
human-facing surface) renders unpadded (`FEAT-283`), the on-disk filename stays padded
(`FEAT-000283-slug.md`), the two path-builders that break get fixed, lookup tolerance is
pinned, and every managed artifact + golden that embeds an ID is regenerated. No schema
bump and no migration runner here — that is the sibling migration task, which depends on
this one. Authoritative design: ADR-282; acceptance in FEAT-283 US1/US2/US4/US5.

## Display unpadding

- Make `Item.id_padding` a fixed constant `0`, not a persisted/configurable `Field`. Today
  it is `id_padding: int = Field(default=DEFAULT_ID_PADDING, exclude=True, ...)` in
  `_models/_item.py`; `Item.id` (`@computed_field`) formats `prefix + sequence_id` at
  `self.id_padding` via `format_item_id`. Drive `Item.id` at width `0` so it renders
  `FEAT-283`.
- `SquadsDB._propagate_padding` (`_models/_index.py:59`) must stamp `0` onto each item's
  `id_padding` instead of the stored `SquadsDB.padding`. `SquadsDB.padding` stays exactly
  what it is (derived/cached filename width in `.squads.json`); only its display consumer
  goes away.
- Remove/adjust every `id_padding=db.padding` kwarg now that it is a constant: `_base.py:311`
  (create), `_maintenance.py:231/262/336`, and the historical `_v0_4_to_v0_5.py:231` runner.
  If `id_padding` is no longer a settable field, passing it as a kwarg will raise — audit all
  construction sites (`grep id_padding src/`) and update them.

`format_item_id(prefix, seq, padding)` already takes width as a parameter — this is the same
formatter called with two widths: `0` for display, the stored `padding` for filenames. No new
formatting path.

## Filename-seam divergence (the load-bearing part)

Under the new model `item.id` is `FEAT-283` but the file must stay `FEAT-000283-slug.md`.
Audit findings — the sites that break and the sites already safe:

- BREAKS — `_services/_items.py:137` (`_rename`): `f"{item.id}-{new_slug}.md"`. Replace with
  an explicit padded name from the sequence number:
  `format_item_id(item.prefix, item.sequence_id, db.padding)` + `-{new_slug}.md`.
- BREAKS — `_services/_retype.py:142`: builds `new_rel` from `new_id = item.id`. Same fix —
  format the padded stem from `item.sequence_id` and `db.padding`, not the computed id.
- SAFE (leave as-is, but verify) — the create path `_base.py:288`
  (`filename = f"{item_id}-{slug}.md"`) uses `item_id = db.allocate_id(...)`, which formats via
  `db.padding` and stays padded; the renumber path `_maintenance.py:528`
  (`format_item_id(file_prefix, seq, new_padding)`); the skill renames `_maintenance.py:246/320`
  (`f"...{seq:0{db.padding}d}..."`). Confirm each still emits a padded stem after the change.
- `item_file()` (`_index/_resolver.py:18`) resolves via the stored `item.path` (persisted padded
  relative path), not by reconstructing from id — so the read side is unaffected. Note this in
  the audit.

Add a clarifying comment at each filename-building call site stating the filename stem is the
padded form and is deliberately NOT the displayed `item.id` (footgun for "stem == id").

## Tests expected

- Invariant test (behaviour, not ID-named): for both create and rename/retype, assert the file
  exists on disk at the padded name while the item's frontmatter `id:` reads unpadded.
- Lookup-tolerance test: both `FEAT-283` and `FEAT-000283` resolve to the same item (input
  parsing unchanged — resolution still keys off prefix + int sequence_id via `ref_id_matches`
  / the sequence-keyed index).
- Regenerate every golden fixture that embeds an ID (per-type `sq-<type>` skills, `squads`/
  `greeting` skills, CLAUDE.md/AGENTS.md managed sections, `sq workflow`, roster/roadmap prose)
  and run the managed-section diff check the way we do on item-type changes; the diff must come
  back clean and purely mechanical.
- Full suite green; `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean;
  `sq check` green.

## Out of scope

Schema bump, migration record/runner, and the migration test — those live in the sibling
migration task (depends on this). No `.squads.toml` change, no new stored field, no filename
renames.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 290 add-subtask "<title>"`; track with `sq task 290 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | id_padding becomes constant 0; every surface renders unpadded | US1 |
| ST2 | Done |  | Format padded filenames from sequence_id at rename/retype seams | US2 |
| ST3 | Done |  | Pin lookup tolerance: FEAT-283 and FEAT-283 both resolve | US4 |
| ST4 | Done |  | Regenerate managed artifacts + goldens; verify managed-section diff | US5 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — id_padding becomes constant 0; every surface renders unpadded

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — IDs read unpadded on every human-facing surface (frontmatter, refs, prose, CLI, tables)
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Make Item.id_padding a fixed constant 0 (not a persisted/configurable Field) so Item.id computes to the unpadded form (FEAT-283) via format_item_id at width 0. Change SquadsDB._propagate_padding (_models/_index.py:59) to stamp 0 onto each item's id_padding instead of the stored SquadsDB.padding. SquadsDB.padding itself is unchanged (it stays the derived filename-width cache in .squads.json); only its display consumer is removed. Then fix every construction site that passes id_padding=db.padding as a kwarg (it will break once the field is constant): _base.py:311, _maintenance.py:231/262/336, and _v0_4_to_v0_5.py:231 — grep id_padding src/ to catch them all. Acceptance: frontmatter id:, refs, prose mentions, and all CLI surfaces (show/list/tree/tables/JSON) read unpadded; id_padding is not stored or configurable.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Format padded filenames from sequence_id at rename/retype seams

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — Files stay padded and lexicographically sorted on disk while the id is unpadded
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Fix the two path-builders that break once item.id is unpadded but the file must stay padded (FEAT-283-slug.md). _rename (_services/_items.py:137) currently does f"{item.id}-{new_slug}.md"; _retype (_services/_retype.py:142) builds new_rel from new_id = item.id. Both must format the padded stem explicitly from the sequence number: format_item_id(item.prefix, item.sequence_id, db.padding). Verify the already-safe sites stay padded (create path _base.py:288 via db.allocate_id; renumber _maintenance.py:528; skill renames _maintenance.py:246/320) and note that item_file (_index/_resolver.py:18) resolves via the stored item.path, so the read side is unaffected. Add a clarifying comment at each filename-building site: the stem is the padded form, deliberately NOT the displayed item.id. Acceptance: an invariant test asserts, for both create and rename/retype, the file exists at the padded name while frontmatter id: is unpadded.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Pin lookup tolerance: FEAT-283 and FEAT-283 both resolve

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US4 — CLI lookup stays width-tolerant: FEAT-283 and FEAT-283 both resolve
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Pin that CLI lookup stays width-tolerant: add a test asserting FEAT-283 and FEAT-283 both resolve to the same item, for a representative command/type. No input-parsing change is made — resolution already keys off (prefix, int sequence_id) via ref_id_matches (_item.py:62) and the sequence-keyed index; only output narrows to unpadded. This subtask is guardrail-only: confirm both widths still resolve after the display change and lock it with the test.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Regenerate managed artifacts + goldens; verify managed-section diff

<!-- sq:subtask:ST4:head -->
**Status:** 🟢 Done
**Implements:** US5 — Managed artifacts and goldens regenerate to unpadded; managed-section diff verified clean
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
Regenerate every managed artifact and golden fixture that embeds an ID so shipped content and this repo's working tree do not lag the new display rule. In scope: per-type sq-<type> skills, the squads/greeting core skills, the CLAUDE.md/AGENTS.md managed sections, the sq workflow cheatsheet, and roster/roadmap prose citing real IDs (e.g. FEAT-27, EPIC-12). Run the managed-section diff check the way we do on item-type changes (the 'verify .claude artifacts' discipline) and confirm the diff is clean and purely mechanical. Acceptance: all affected goldens regenerated and reviewed as one mechanical diff; managed-section diff clean; sq check green; uv run pyright && uv run ruff check . && uv run ruff format --check . clean.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-04T20:47:34Z] Olivia Lead:
  - Sequencing: this is the core, land it first. TASK-000291 (schema bump + migration) depends on it. Golden/managed-artifact regen is folded in here (ST4) because the display flip breaks goldens in the same change — no separate green PR is possible.
- [2026-07-04T22:08:52Z] Elias Python:
  - Done. ST1 (US1): Item.id_padding removed as a stored/settable field; added module constant DISPLAY_ID_PADDING=0 in _models/_item.py, Item.id now always formats at width 0. Removed SquadsDB._propagate_padding (no longer needed) and stripped every id_padding=db.padding construction kwarg (_base.py create, _maintenance.py seed_bundled_skills/seed_custom_skills, _v0_4_to_v0_5.py). SquadsDB.padding/format_id/allocate_id unchanged (still filename width).
  - ST2 (US2): fixed the two BREAKING filename-seam sites — _services/_items.py _rename (now threads db through and formats format_item_id(item.prefix, item.sequence_id, db.padding) for the stem) and _services/_retype.py retype (same fix, keeps new_id=item.id unpadded for content/refs, new_stem padded for the path). Also found and fixed a THIRD site the audit missed: _maintenance.py _renumber_plan/_renumber — it was feeding the same minted id into both the rename target (needs padded) and the rewrite_ids remap that patches frontmatter/refs/prose (needs unpadded); now mints new_padded and new_display separately. Added clarifying ADR-282 comments at every filename-building call site (_base.py create, _items.py rename, _retype.py, _maintenance.py seed/renumber/repad).
  - ST3 (US4): added test_unpadded_and_padded_ids_resolve_to_same_item (test_cli.py) pinning FEAT-2/FEAT-000002 resolve identically via resolve_item_id_typed, resolve_item_id_any, and db.get — no input-parsing change, confirmed.
  - ST4 (US5): regenerated tests/goldens/*.json (list/tree/show/graph/refs/blocked/inbox/search/skill/role/operator), tests/goldens/agents_md_section.txt, and squads/agents/skills/SKILL-192 (greeting) + SKILL-200 (squads) via sq sync — fixed 3 templates that hard-coded padded example IDs (squads_skill.md.j2, greeting_skill.md.j2, agents_md/agents_section.md.j2). Also fixed padded examples in CLI --help/epilog text (_cli/_skill.py, _cli/_role.py, _cli/_main.py reflog/graph/show help). Regenerated the v0.6.0 template manifest (scripts/gen_template_manifest.py — only the 3 edited templates' hashes changed, other frozen version entries untouched). sq workflow output has no embedded IDs, unaffected. Did NOT touch src/ code-comment ADR-/TASK- references (out of scope — that's the separate FEAT-237 sweep).
  - Invariant test added: test_rename_and_retype_keep_filename_padded_while_id_unpadded (test_service.py) — asserts padded filename stem + unpadded frontmatter id: for both rename and retype, alongside the existing test_create_allocates_id_and_writes_file for create. Live-repo evidence: ran a scratch sq init + create/update --title/retype cycle — filename stayed e.g. BUG-000003-renamed-task.md throughout while frontmatter id: and CLI panel both read BUG-3; sq bug BUG-3 show and sq bug BUG-000003 show resolved to the same item; sq check clean.
  - Full suite: 1589 passed, 1 skipped, 0 failed. uv run pyright: 0 errors. ruff check + format --check: clean.
  - Left the working tree for review — did not commit, did not self-review, did not start TASK-291 (schema bump/migration is out of scope here; this repo's own item files stay on padded on-disk frontmatter until that migration runs, as expected).
  - @reviewer please review. @manager FYI — TASK-290 is InReview, all 4 subtasks Done.
<!-- sq:discussion:end -->
