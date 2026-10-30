---
id: TASK-1124
sequence_id: 1124
type: task
title: Move the roster, thread the spec and split oversized modules
status: Done
parent: FEAT-1092
author: tech-lead
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
  status: Done
  maps_to: US1
- local_id: ST2
  title: Move the interactions init into named modules
  status: Done
  maps_to: US1
- local_id: ST3
  title: Prune bundled shims and make spec parameters required
  status: Done
  maps_to: US2
- local_id: ST4
  title: Load the three spec documents through one shared path
  status: Done
  maps_to: US2
- local_id: ST5
  title: Split registries, validity checks and ordering out of models
  status: Done
  maps_to: US3
- local_id: ST6
  title: Share the corpus walk and move check into its own mixin
  status: Done
  maps_to: US3
- local_id: ST7
  title: Move the view tag engine and remedy builders out of views
  status: Done
  maps_to: US3
- local_id: ST8
  title: Replace bundled sub-entity tags with one generic helper
  status: Done
  maps_to: US3
created_at: '2026-10-24T21:53:25Z'
updated_at: '2026-10-28T12:46:03Z'
priority: medium
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

Re-measure at the start of each subtask.

## Approach

Each subtask is its own commit and leaves the full suite, pyright, ruff and `sq check` clean.

1. **Roster collaborator (ST1, F3).** Move the cluster into one class in its own service-layer module, for example `src/squads/_services/_roster_projection.py`. It is built from `paths`, `spec`, `playbook`, `store` and the backends, and held as a field on `ServiceCore`. The six mixins that use it call the field. Methods the CLI, the TUI or tests call on the service (`roster`, `roster_all`, `operators`, `author`, `resolved_skills_for_role`, `refresh_managed`, ...) stay on the façade as one-line delegates, so no caller changes.
2. **Empty the interactions init (ST2, F5).** Split along the consumers that already exist: playbook data, the bundled-playbook accessor, lanes, `authoring_owners`, `parent_chain` and orphan-guide detection go to `_interactions/_playbook.py`; skill naming, descriptions, slug vocabularies and origins go to `_interactions/_skills.py`; cheatsheet anchoring goes to `_interactions/_cheatsheet.py`; `is_live_roster_entry` goes to `_roles/`. The view-name constants go beside the code that writes and repairs those views; the import-edge table decides the module. Load the bundled playbook on first use (a cached function), not at import. Update every importer, with no re-export. Leave the init empty and drop it from CLAUDE.md's non-empty-init list; the import-edge guard (`inits_with_code`) and the mutable-state allowlist (`tests/meta/test_no_unallowlisted_module_level_mutable_state.py`) follow the moved names.
3. **Required documents (ST3, F6).** Delete the bundled shims in `_workflow/__init__.py` that have no production caller; tests that use them call `bundled_spec().<method>` instead. Make all 41 parameters required, starting with `ServiceCore.__init__` and `BackendContext`, and let pyright list the sites. A site that wants the bundled document passes it explicitly. That includes today's four `Service(...)` constructions without a playbook (`_cli/_common.py:1623`, `:1632`, `_cli/_main.py:1544`, `:1551`): they pass the bundled playbook explicitly, which is today's behaviour. Each remaining production `bundled_spec()` call is either threaded or listed in the commit as a deliberate bundled read (fail-soft help fallback, migrations). Test constructions of `Service` (381 in 136 files) go through one helper in `tests/_helpers.py` rather than being edited one by one.
4. **One load path (ST4, F8).** Write one document descriptor (bundled file name, override file name, top-level keys, selected sections, build function, caching rule) and one `load(document, squad_dir)` that owns the bundled read, the override read, error wrapping and the unreachable-merge guard. It replaces the three copies of `_read_bundled_bytes`/`_bundled_raw`/`bundled_<doc>_toml_text`/`_read_raw_override` in `_workflow/_loader.py`, `_roles/_loader.py` and `_interactions/_loader.py`. Each loader keeps its own validation and its exact user-facing messages; the roles loader's raise-versus-tuple contract is unified behind the descriptor without changing what the user reads. The new module's place, for example a top-level `src/squads/_specload.py` beside `_specmerge.py`, is a row in the import-edge table.
5. **Split `_workflow/_models.py` (ST5, F9).** The validator name registries go to `_workflow/_validator_names.py`, the load-time validity checks to `_workflow/_validity.py`, and lifecycle ordering to `_workflow/_lifecycle_order.py`. `WorkflowSpec._validate` calls the validity module through a function-local import, the cycle break this file already uses. The models' public surface and methods stay.
6. **Split `_services/_maintenance.py` (ST6, F10).** First lift the per-file classification both loops write (item, unreadable, unparseable, missing id, legacy skill body, vanished) into one corpus-reading primitive that yields a tagged record per file. Build `_rebuild_index_from_disk` and `_scan_for_check` on it, and fold in `ServiceCore._all_item_files` (`_services/_base.py:1077`) and the ad-hoc folder globs where they walk the same set. Then move `check`, its drift-confirmation methods and its own helpers into a `CheckMixin` in `src/squads/_services/_check.py`, added to `Service`'s bases. Break `sync` into named steps in place. Update CLAUDE.md's mixin count and MRO list.
7. **Split `_views.py` (ST7, F12).** The tag placement and expansion engine goes next to `_sections.py`, as `src/squads/_view_tags.py`. `view_placement_invocation` and `clear_roster_body_cmd` build remedy text for `_services/_validators.py`, `_services/_maintenance.py` and `_services/_base.py`, so they move to a remedy module in `_services/`. Fix the two stale method names to `ViewsMixin.add_view`/`disable_view`, after verifying those names. `_views.py` keeps source resolution, projection, rendering and view data.
8. **Bundled sub-entity literals (ST8, F7).** Add `subentity_tag(kind, local_id)` to `_models/_markers.py` and use it in both branches of `CollabMixin._discussion_tag`. Delete the three per-kind tag functions. Inline `STORIES`/`SUBTASKS`/`FINDINGS` into the one migration runner that reads them; its behaviour stays identical. Add a `tests/meta` guard, shaped like the ref-kind literal guard, that keeps bundled sub-entity kind literals out of `src/` outside the spec and migrations. The per-kind `SubentitiesMixin` wrappers are out of scope.

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
### ST4 — Load the three spec documents through one shared path

<!-- sq:subtask:ST4:body -->
Replace the three copies of the bundled-read, override-read and error-wrapping code in `_workflow/_loader.py`, `_roles/_loader.py` and `_interactions/_loader.py` with one document descriptor and one load path in `src/squads/_specload.py`: bundled read, override read, merge and the unreachable-merge guard. Validation and user-facing messages stay per loader and unchanged. Record the new module's edges in the import-edge table.
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
Add `subentity_tag(kind, local_id)` to `_models/_markers.py`, use it in both branches of `CollabMixin._discussion_tag`, and delete `story_tag`/`subtask_tag`/`finding_tag`. Inline `STORIES`/`SUBTASKS`/`FINDINGS` into the migration runner that reads them. Add a `tests/meta` guard, with a liveness row, that keeps bundled sub-entity kind literals out of `src/` outside the spec and migrations. The per-kind service wrappers are out of scope.
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T03:41:31Z] `python-dev` Elias Python:
  - ST4 is partly delivered: the descriptor and shared load path (src/squads/_specload.py) now carry the three loaders' bundled read, override read, error wrapping, merge and unreachable-merge guard, messages unchanged. Not done: the one function resolving workflow spec, role catalog and playbook together (absorbing resolve_playbook). open_service does not read the role catalog today, so loading it there would make a malformed roles override a new hard stop for every command: a behaviour change, so it needs a decision (@tech-lead) before I do it.
- [2026-10-25T04:33:58Z, edited 2026-10-25T04:34:29Z] `python-dev` Elias Python:
  - Handoff, working tree only (nothing committed). Gates: pyright 0 errors, ruff check and format clean, tests/meta, unit, integration, cli, service all green on the last run except one stray-reference meta test I then fixed and re-ran (then tests/meta alone, 458 passed); sq check clean. Generated output: a scratch squad (all roles, claude_code and agents_md) synced before and after, diffed with timestamps normalised: CLAUDE.md, AGENTS.md, .claude pointers, skills, help and check output byte-identical. No CHANGELOG substance: internal restructuring, no behaviour change.
    
    **ST1 Done.** RosterProjection in src/squads/_services/_roster_projection.py (494 lines, held as ServiceCore.roster_projection); _base.py 1938 to 1567. The public entry points stay as one-line delegates; mixins call the field for the helpers. Private helpers became public names on the collaborator (pyright).
    **ST2 Done.** _interactions/__init__.py is empty (was 869 lines): _playbook.py, _skills.py, _cheatsheet.py; bundled playbook loads on first use (cached). Deviations: is_live_roster_entry lives in _roster_projection.py, not _roles/ (it needs _interactions skill naming and _interactions already imports _roles at top, so _roles -> _interactions would join the cycle; every caller is in _services). The view-name constants went to _views.py beside roster_body_view_name, the one derivation the writers and checks share. PLAYBOOK and TITLE_ADVISORY_MAX are gone (bundled_item_playbooks(), DEFAULT_SUBENTITY_TITLE_MAX).
    **ST3 Done.** Workflow shims and constants deleted (the package keeps bundled_spec and dropped_via_selected). Spec and playbook parameters required on ServiceCore, BackendContext, IndexStore, ValidatorEngine, SquadGlobalContext, load_playbook, managed_item_types, authoring_owners, _badges, _discussion, _paths. Service constructions go through tests/_helpers.make_service. The four playbook-less Service constructions pass get_playbook_spec() explicitly. Remaining None-able spec or playbook parameters (14 lines), none a silent bundled fallback except the first two: _engine._badge and _engine._authoring_owners (template-facing, keep an adopter template that omits the argument rendering; bundled read); ItemFilter.spec and item_skill_role_sections(playbook) (None disables a dimension); _context.active_spec, open_service(resolved_spec), and the CLI helpers that fall back to the request-scoped get_active_spec(). Remaining production bundled_spec() reads (22 calls, 11 files, migrations excluded): CLI static registration and epilog (_cli/__init__, _create, _items), fail-soft fallbacks (_cli/_common, _cli/_main), _services/_service (init, bundled fast path), _services/_items (attributes the bundled spec declares), _services/_maintenance (legacy folder comparison), _workflow dropped_via_selected, _interactions/_loader, the two template wrappers above.
    **ST4 InProgress, first half done.** src/squads/_specload.py: SpecDocument descriptor, bundled_raw/bundled_text, read_override, load_override (read, check hook, merge, unreachable-merge guard); the three loaders use it, messages unchanged (workflow and playbook keep their fix hints; roles its UTF-8 case). Not done: the single function resolving workflow spec, role catalog and playbook together and absorbing resolve_playbook. open_service does not read the role catalog today, so loading it there makes a malformed roles override a hard stop for every command, a behaviour change. Needs a ruling (@tech-lead). Tests: ignoring the override turns 566 loader and override tests red; the unreadable-override wording survived mutation, so tests/unit/test_spec_override_read_errors.py adds those rows (red when the wording is broken).
    **ST5 Done.** _workflow/_models.py 3544 to 1464: _validator_names.py (559), _validity.py (1512, entry points renamed public, called through a function-local import in _validate), _lifecycle_order.py (147).
    **ST6 Done.** src/squads/_services/_corpus_files.py: read_corpus_file returns one tagged record (Vanished, Unreadable, Unparseable, MissingId, LegacySkillBody, Parsed); both _rebuild_index_from_disk and _scan_for_check consume it; tests/unit/test_corpus_file_tags.py, one row per shape, each seam mutated to red. CheckMixin in _services/_check.py (1072 lines; it subclasses MaintenanceMixin since the scan shares its skill helpers), added to Service bases (13); _maintenance.py 3722 to 2571. sync is broken into named steps in place. The corpus globs: ServiceCore._type_folders is the one ordered enumeration behind _all_item_files, _iter_item_files and _id_carriers (identical order on the bundled spec; it can only reorder duplicate-group reports for a custom spec whose declared order differs from (order, name)).
    **ST7 Done.** _view_tags.py (493) holds the placement and expansion engine; _views.py 1271 to 826 keeps sources, projection, rendering and view_data. view_placement_invocation and clear_roster_body_cmd are in src/squads/_view_remedies.py at the top level, not _services/, because place_view_tags composes the same text. Stale names fixed to ViewsMixin.add_view/disable_view. Side effect on the layering table: _views left the module-top cycle (CLAUDE.md now says six packages; _overrides imports _view_tags locally).
    **ST8 Done.** markers.subentity_tag used in both _discussion_tag branches; story_tag, subtask_tag, finding_tag and STORIES/SUBTASKS/FINDINGS deleted (the three constants are private to _migrations/_v0_1_to_v0_2.py). Guard tests/meta/test_no_bundled_subentity_kind_literal_outside_the_spec_layer.py with a per-file allowlist (the existing legacy sites, each with a reason) and a planted-literal liveness row; red when a literal is planted in _base.py.
    
    Test edits: signature changes only through make_service and explicit specs; deleted tests whose subject no longer exists (the module-level shims, a Service without a spec, a BackendContext without documents); moved patch targets and table rows. Import-edge table, mutable-state allowlist, CLAUDE.md (architecture, mixins, inits) updated.
- [2026-10-25T04:36:19Z] `tech-lead` Olivia Lead:
  - Ruling on ST4: option (a). The joint resolver (spec, role catalog, playbook; absorbs resolve_playbook) moves to TASK-1125 as a composition-root step, with the role catalog resolved lazily so no command gains a hard stop. ST4 now describes the delivered load path and is Done.
- [2026-10-25T04:43:08Z] `python-dev` Elias Python:
  - TUI follow-up: fixed the moved expand_view_tags patch target and the Service construction in tests/tui; tests/tui green, pyright and ruff clean.
- [2026-10-25T05:19:46Z] `python-dev` Elias Python:
  - REV-1133 F1-F5 fixed in the working tree (not committed); targeted run plus tests/tui green (the whole fast set ran, 14092 passed), pyright and ruff clean.
- [2026-10-25T05:29:44Z] `manager` Catherine Manager:
  - Accepted: REV-1133 Approved (F1-F5 Verified, F6 tracked as BUG-1134); full suite green at 56c8efb4; no adopter-visible change, so no CHANGELOG line.
<!-- sq:discussion:end -->
