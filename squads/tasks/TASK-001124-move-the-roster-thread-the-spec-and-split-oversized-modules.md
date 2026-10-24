---
id: TASK-1124
sequence_id: 1124
type: task
title: Move the roster, thread the spec and split oversized modules
status: Ready
parent: FEAT-1092
author: tech-lead
priority: medium
refs:
- REV-956:addresses
- TASK-1123:depends-on
- TASK-1106:depends-on
- TASK-1077:depends-on
description: 'Behaviour-free moves for REV-956 F3, F5-F10, F12: roster, interactions
  init, spec threading, loaders, file splits.'
subentities:
- local_id: ST1
  title: Extract the roster projection into a collaborator
  status: Todo
  story: US1
- local_id: ST2
  title: Move the interactions init into named modules
  status: Todo
  story: US1
- local_id: ST3
  title: Prune bundled shims and make spec parameters required
  status: Todo
  story: US2
- local_id: ST4
  title: Load the three spec documents through one descriptor
  status: Todo
  story: US2
- local_id: ST5
  title: Split registries, validity checks and ordering out of models
  status: Todo
  story: US3
- local_id: ST6
  title: Share the corpus walk and move check into its own mixin
  status: Todo
  story: US3
- local_id: ST7
  title: Move the view tag engine and remedy builders out of views
  status: Todo
  story: US3
- local_id: ST8
  title: Replace bundled sub-entity tags with one generic helper
  status: Todo
  story: US3
created_at: '2026-10-24T21:53:25Z'
updated_at: '2026-10-24T21:55:43Z'
---
<!-- sq:body -->
## Goal

Move engine code to where it belongs, with no change to what `sq` does: the roster projection leaves `ServiceCore`, `_interactions/__init__.py` empties into named modules, every spec and playbook parameter is required, the three spec loaders share one load path, and the three oversized modules are split along the seams REV-956 measured. Findings F3, F5, F6, F7, F8, F9, F10 and F12.

## Re-measured on 2026-10-24 (working tree, read)

| subject | review | now |
|---|---|---|
| roster cluster in `ServiceCore` | 19 methods, about 400 lines | 20 methods, `src/squads/_services/_base.py:1531-1938` |
| `_interactions/__init__.py` | 810 lines | 822 lines; bundled playbook loaded at import (`:111`); 25 `src/` modules import it |
| None-defaulted spec, playbook or catalog parameters | 41 | 41 (`_badges.py` 10, `_discussion.py` 9, `_services/_base.py` 3, `_paths.py` 3, `_backends/_base.py` 2, ...) |
| production `bundled_spec()` calls outside `_workflow/__init__.py` and `_migrations/` | 36 | 38 in 17 files |
| bundled shims in `_workflow/__init__.py` | 22 | 28 module-level names, 248 lines |
| `_workflow/_models.py` | 3434 lines | 3544 lines; validator name registries from `:149`, 29 `_check_*`/`_clause_*` checks (`:1236-2700`), lifecycle ordering (`:2758-2860`), `WorkflowSpec` at `:2864` |
| `_services/_maintenance.py` | 3769 lines | 3722 lines; `sync` `:980`, `_iter_item_files` `:1980`, `_rebuild_index_from_disk` `:2335`, `repair` `:2550`, `check` `:3118`, `_scan_for_check` `:3574` |
| `_views.py` | 1199 lines | 1271 lines; command builders `:735`, `:749`; tag text engine `:759-1240`; stale `insert_view`/`remove_view` at `_views.py:29` and `_services/_base.py:1502` |
| sub-entity literals | as reported | `STORIES`/`SUBTASKS`/`FINDINGS` and `story_tag`/`subtask_tag`/`finding_tag` in `_models/_markers.py:22-47`; legacy branch `_services/_collab.py:631-635` |

The other FEAT-1101 tasks are still editing some of these files, so re-measure at the start of each subtask.

## Approach, in subtask order

The order follows the feature: the roster extraction comes first because it informs the DI decision, and spec threading comes before the splits that touch the same signatures. Each subtask is its own commit and leaves the full suite, pyright, ruff and `sq check` clean.

1. **Roster collaborator (ST1, F3).** Move the cluster into one class in its own service-layer module, for example `src/squads/_services/_roster_projection.py`. It is built from `paths`, `spec`, `playbook`, `store` and the backends, and held as a field on `ServiceCore`. The six mixins that use it call the field. Methods the CLI, the TUI or tests call on the service (`roster`, `roster_all`, `operators`, `author`, `resolved_skills_for_role`, `refresh_managed`, ...) stay on the façade as one-line delegates, so no caller changes.
2. **Empty the interactions init (ST2, F5).** Split along the consumers that already exist: playbook data, the bundled-playbook accessor, lanes, `authoring_owners`, `parent_chain` and orphan-guide detection go to `_interactions/_playbook.py`; skill naming, descriptions, slug vocabularies and origins go to `_interactions/_skills.py`; cheatsheet anchoring goes to `_interactions/_cheatsheet.py`; `is_live_roster_entry` goes to `_roles/`. The view-name constants go beside the code that writes and repairs those views; the import-edge table decides the module. Load the bundled playbook on first use (a cached function), not at import. Update every importer, with no re-export. Leave the init empty and drop it from CLAUDE.md's non-empty-init list; the import-edge guard (`inits_with_code`) and the mutable-state allowlist (`tests/meta/test_no_unallowlisted_module_level_mutable_state.py`) follow the moved names.
3. **Required documents (ST3, F6).** Delete the bundled shims in `_workflow/__init__.py` that have no production caller; tests that use them call `bundled_spec().<method>` instead. Make all 41 parameters required, starting with `ServiceCore.__init__` and `BackendContext`, and let pyright list the sites. A site that wants the bundled document passes it explicitly. That includes today's four `Service(...)` constructions without a playbook (`_cli/_common.py:1623`, `:1632`, `_cli/_main.py:1544`, `:1551`): they pass the bundled playbook explicitly, which is today's behaviour, and the composition-root task revisits them. Each remaining production `bundled_spec()` call is either threaded or listed in the commit as a deliberate bundled read (fail-soft help fallback, migrations). Test constructions of `Service` (381 in 136 files) go through one helper in `tests/_helpers.py` rather than being edited one by one.
4. **One load path (ST4, F8).** Write one document descriptor (bundled file name, override file name, top-level keys, selected sections, build function, caching rule) and one `load(document, squad_dir)` that owns the bundled read, the override read, error wrapping and the unreachable-merge guard. It replaces the three copies of `_read_bundled_bytes`/`_bundled_raw`/`bundled_<doc>_toml_text`/`_read_raw_override` in `_workflow/_loader.py`, `_roles/_loader.py` and `_interactions/_loader.py`. Then add one function that resolves the three documents for a squad together, which absorbs `resolve_playbook` (`_services/_service.py:57`). Each loader keeps its own validation and its exact user-facing messages; the roles loader's raise-versus-tuple contract is unified behind the descriptor without changing what the user reads. The new module's place, for example a top-level `src/squads/_specload.py` beside `_specmerge.py`, is a row in the import-edge table.
5. **Split `_workflow/_models.py` (ST5, F9).** The validator name registries go to `_workflow/_validator_names.py`, the load-time validity checks to `_workflow/_validity.py`, and lifecycle ordering to `_workflow/_lifecycle_order.py`. `WorkflowSpec._validate` calls the validity module through a function-local import, the cycle break this file already uses. The models' public surface and methods stay.
6. **Split `_services/_maintenance.py` (ST6, F10).** First lift the per-file classification both loops write (item, unreadable, unparseable, missing id, legacy skill body, vanished) into one corpus-reading primitive that yields a tagged record per file. Build `_rebuild_index_from_disk` and `_scan_for_check` on it, and fold in `ServiceCore._all_item_files` (`_services/_base.py:1077`) and the ad-hoc folder globs where they walk the same set. Then move `check`, its drift-confirmation methods and its own helpers into a `CheckMixin` in `src/squads/_services/_check.py`, added to `Service`'s bases. Break `sync` into named steps in place. Update CLAUDE.md's mixin count and MRO list.
7. **Split `_views.py` (ST7, F12).** The tag placement and expansion engine goes next to `_sections.py`, as `src/squads/_view_tags.py`. `view_placement_invocation` and `clear_roster_body_cmd` build remedy text for `_services/_validators.py`, `_services/_maintenance.py` and `_services/_base.py`, so they move to a remedy module in `_services/`. Fix the two stale method names to `ViewsMixin.add_view`/`disable_view`, after verifying those names. `_views.py` keeps source resolution, projection, rendering and view data.
8. **Bundled sub-entity literals (ST8, F7).** Add `subentity_tag(kind, local_id)` to `_models/_markers.py` and use it in both branches of `CollabMixin._discussion_tag`. Delete the three per-kind tag functions. Inline `STORIES`/`SUBTASKS`/`FINDINGS` into the one migration runner that reads them; its behaviour stays identical. Add a `tests/meta` guard, shaped like the ref-kind literal guard, that keeps bundled sub-entity kind literals out of `src/` outside the spec and migrations. The per-kind `SubentitiesMixin` wrappers stay: their test callers are ported by the test rebuild, and TASK-1114 deletes them.

## Tests

The existing suite is the net for every move, and no assertion is edited to fit one. Signature changes in tests, made through the helper, are allowed. The type gate is the test for the required parameters. New tests exist only where a break would otherwise leave the suite green:

- **Corpus-reading primitive (ST6):** one table of file shapes with these rows only: valid item, undecodable bytes, unparseable frontmatter, missing id, legacy skill body, file vanished between listing and read. Each row checks the tagged record. Both loops consume the primitive, so no rebuild-level or check-level duplicate is added. `tests/meta/test_corpus_walking_reads_degrade_per_file.py` stays; whether it is now redundant is the rebuild's call.
- **Descriptor load (ST4):** first break the descriptor (say, ignore the override) and run the existing loader and override tests. Add rows only for what stays green: override absent (the cached bundled object), override present (merged), override unreadable (that loader's existing error).
- **Literal guard (ST8):** the guard plus a liveness row that plants a literal and sees it fail.
- The import-edge table (`tests/meta/test_package_import_edges_match_the_recorded_table.py`) changes in the same commit as each new edge, and the write-once guard stays green throughout.

Falsify each new test once by breaking its seam, and record the red in the handoff.

## Generated output

None should change. Before ST1 and after ST8, init a scratch squad outside this repository on a pinned roster with the dev tree, run `sync`, and diff CLAUDE.md, AGENTS.md, the `.claude/` pointers and the skills: they must be byte-identical. The template manifest and content store are unchanged.

## CHANGELOG substance

No adopter-visible change. Report "internal restructuring, no behaviour change" to the writer, who decides whether it earns a line. Contributor docs change in CLAUDE.md (architecture section: modules, mixins, non-empty inits) and `docs/internals.md` where it names moved modules.

## Order

This task starts after the FEAT-916 task and TASK-1106 (which adds a mention-token resolver under `_interactions/`), and after TASK-1077 (validator wording in `_maintenance.py` and `_workflow/_models.py`). It precedes the composition-root task, the check-rule task, and the test-rebuild inventory (TASK-1111): the rebuild's ledger names seams by module and function, so the modules move before the ledger is written.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1124 add-subtask "<title>"`; track with `sq task 1124 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Extract the roster projection into a collaborator

<!-- sq:subtask:ST1:body -->
Move the roster projection (`src/squads/_services/_base.py:1531-1938`, 20 methods) into one collaborator class in its own service-layer module, held as a field on `ServiceCore` and built from paths, spec, playbook, store and backends. The six mixins call the field. Public service methods stay as one-line delegates. Re-measure the cluster first.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Move the interactions init into named modules

<!-- sq:subtask:ST2:body -->
Move the 822 lines of `src/squads/_interactions/__init__.py` into named modules: `_interactions/_playbook.py` (data, bundled accessor, lanes, authoring owners, parent chain, orphan guides), `_interactions/_skills.py` (skill naming, slugs, origins), `_interactions/_cheatsheet.py`, and `_roles/` for roster liveness. The view-name constants go beside the code that writes and repairs those views. Load the bundled playbook on first use. Update every importer, leave the init empty, and update CLAUDE.md's non-empty-init list and the mutable-state allowlist.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Prune bundled shims and make spec parameters required

<!-- sq:subtask:ST3:body -->
Delete the `_workflow/__init__.py` shims that have no production caller. Make the 41 None-defaulted spec, playbook and catalog parameters required, starting with `ServiceCore.__init__` and `BackendContext`. Sites that want the bundled document pass it explicitly, including the four playbook-less `Service(...)` constructions in `_cli/_common.py` and `_cli/_main.py`. List the deliberate remaining `bundled_spec()` reads in the commit. Tests build services through one helper in `tests/_helpers.py`.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Load the three spec documents through one descriptor

<!-- sq:subtask:ST4:body -->
Replace the three copies of the bundled-read, override-read and error-wrapping code in `_workflow/_loader.py`, `_roles/_loader.py` and `_interactions/_loader.py` with one document descriptor and one `load(document, squad_dir)`. Then add one function that resolves all three documents for a squad and absorbs `resolve_playbook` from `_services/_service.py`. Validation and user-facing messages stay per loader and unchanged. Record the new module's edges in the import-edge table.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Split registries, validity checks and ordering out of models

<!-- sq:subtask:ST5:body -->
Split `src/squads/_workflow/_models.py` (3544 lines) by file, not by class: validator name registries to `_workflow/_validator_names.py`, the 29 load-time `_check_*`/`_clause_*` functions to `_workflow/_validity.py` (called from `WorkflowSpec._validate` through a function-local import), and lifecycle ordering to `_workflow/_lifecycle_order.py`. The models and their methods stay.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Share the corpus walk and move check into its own mixin

<!-- sq:subtask:ST6:body -->
Lift the per-file classification that `_rebuild_index_from_disk` and `_scan_for_check` each write into one corpus-reading primitive yielding a tagged record per file, and fold `ServiceCore._all_item_files` and the ad-hoc globs into it where they walk the same set. Move `check`, its drift confirmation and its helpers into `CheckMixin` in `src/squads/_services/_check.py`. Break `sync` into named steps in place. Add the file-shape table for the primitive and update CLAUDE.md's mixin list.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Move the view tag engine and remedy builders out of views

<!-- sq:subtask:ST7:body -->
Move the view tag placement and expansion engine out of `src/squads/_views.py` into `src/squads/_view_tags.py` beside `_sections.py`. Move `view_placement_invocation` and `clear_roster_body_cmd`, whose callers are all in `_services/`, to a remedy module there. Fix the stale `insert_view`/`remove_view` names in `_views.py` and `_services/_base.py`. `_views.py` keeps source resolution, projection, rendering and view data.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — Replace bundled sub-entity tags with one generic helper

<!-- sq:subtask:ST8:body -->
Add `subentity_tag(kind, local_id)` to `_models/_markers.py`, use it in both branches of `CollabMixin._discussion_tag`, and delete `story_tag`/`subtask_tag`/`finding_tag`. Inline `STORIES`/`SUBTASKS`/`FINDINGS` into the migration runner that reads them. Add a `tests/meta` guard, with a liveness row, that keeps bundled sub-entity kind literals out of `src/` outside the spec and migrations. The per-kind service wrappers stay for the test rebuild to delete.
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
