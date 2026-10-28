---
id: TASK-1111
sequence_id: 1111
type: task
title: 'Inventory the old suite: parity ledger and falsification audit'
status: Cancelled
parent: FEAT-1096
author: tech-lead
assignee: qa
priority: high
refs:
- TASK-1110:depends-on
- TASK-1098:depends-on
- TASK-1103:depends-on
- TASK-1104:depends-on
- TASK-1105:depends-on
- TASK-1106:depends-on
- TASK-1107:depends-on
- TASK-1123:depends-on
- TASK-1124:depends-on
- TASK-1125:depends-on
- TASK-1126:depends-on
- TASK-1127:depends-on
- TASK-1165:depends-on
- BUG-1167:depends-on
description: Parity ledger, per-module falsification audit and per-OS CI baseline;
  read-only on tests and src.
subentities:
- local_id: ST1
  title: Build the parity ledger from regression classes, bugs and findings
  status: Todo
  story: US1
- local_id: ST2
  title: Run the falsification audit per source module on the old suite
  status: InProgress
  story: US2
- local_id: ST3
  title: Record the per-OS CI baseline with durations and worker counts
  status: Done
  assignee: devops
  story: US10
created_at: '2026-10-24T13:42:12Z'
updated_at: '2026-10-27T20:16:22Z'
---
<!-- sq:body -->
Inventory what the old suite protects before any of it is rebuilt: the parity ledger (US1), the falsification audit (US2) and the per-OS CI baseline every later increment is measured against (US10). Read-only on `tests/` and `src/`: no old test is deleted or edited here. The one file this task adds to the repo is the ledger, `tests_next/LEDGER.md`, which starts the new root; the rest of that root is set up by the next task.

The task starts after the queue ahead of it has landed (TASK-1110, TASK-1098, the FEAT-1101 tasks TASK-1103 to TASK-1107, and TASK-1123 to TASK-1126, all Done on 2026-10-26), and runs last in the 0.17 release (op-pierre, 2026-10-26), so the suite it inventories is the one the rebuild replaces. It also waits on TASK-1127, TASK-1165 and BUG-1167 (depends-on refs), the 0.17 work still open on 2026-10-26.

**Measured on 2026-10-26** at `release/0.17` 9b79babd (`pytest --collect-only -n0`, one directory at a time; `gh run view` on the latest `test` workflow runs):

- 15,636 tests in 821 files. Per directory: `tests/service` 5,388 (256 files); `tests/cli` 4,451 (232); `tests/unit` 3,979 (164); `tests/integration` 1,243 (97); `tests/meta` 492 (60); `tests/tui` 77 (11); `tests/test_scale.py` 6 (the only `slow` tests, skipped in CI). That is 1,705 more than the 13,931 counted on 2026-10-24, 1,068 of them in `tests/cli`; the largest new tables are `tests/cli/test_a_damaged_override_is_a_clean_error_cli.py` (402), `tests/cli/test_each_spec_document_is_loaded_at_most_once_per_invocation.py` (145) and `tests/cli/test_every_item_edit_verb_takes_an_optional_as_cli.py` (100).
- From the 2026-10-24 count (13,816 tests), not re-measured: 4,975 test functions; 9,605 parametrised rows (70%) from 760 parametrised functions; the 20 largest functions hold 3,811 tests (28%), the 100 largest 6,283 (45%).
- CI pytest step, all on the 0.16 suite (13,816 collected): the 2026-10-17 push to `main` (run 39020459902) took 3,190 s on Windows, 852 s on macOS and 480 s on Ubuntu. The two 2026-10-24 dependency-bump pull requests took 2,319 s and 3,516 s on Windows (run 40116628420, passed; run 40116638095, one TUI test failed), 635 s and 796 s on macOS, 885 s and 954 s on Ubuntu. That is 168 to 255 ms per test on Windows, 46 to 58 on macOS and 64 to 69 on Ubuntu; Ubuntu is already over its 10-minute target. `release/0.17` has never run the `test` workflow, which triggers only on pushes and pull requests to `main`. Worker counts are not in the `-q` log.
- A filename heuristic put about 8,100 tests in 509 files on a fresh `init` per test, against 1,500 tests in 33 files that copy a shared squad (`tests/_roster_squad.py` pattern), on 2026-10-24. This is an estimate from static reads, to be confirmed by the profile.

The queue ahead adds tests, so ST2 and ST3 re-count at the start and the ledger and baseline cite that count, not these figures.

**What makes an edge case a ledger entry.** An entry is kept when it falls in one of these sources, and only then:

1. The regression classes seeded in the FEAT-1096 body.
2. A Verified or Fixed bug (140 Verified, 5 Fixed on 2026-10-26) whose fix added or changed a test: found from the bug's refs, the fixing commit and `git log -S` on the test name.
3. A defect-severity review finding (critical, high, medium; Verified or Fixed), REV-706 F1, F10, F11 and F12 included.
4. An old test that the audit shows is the only one red for some break of its seam (a unique kill). A row that only ever goes red together with its siblings is redundant; a row that never goes red is not protective. Neither becomes an entry.

Each entry names the seam (module and function), the user-visible behaviour, the area that owns it (integrity core, engine/services/CLI, or backend/skills/rendering/TUI, matching the three area tasks), the owning layer in the new suite, the old test ids that cover it today, and the break used to prove it (a small described patch to `src/`). The area tasks later fill in the new owner test and the recorded red.

**Order.** ST2 runs first: sources 1 to 3 of ST1 can be gathered alongside it, but source 4 comes from the audit.

**Acceptance**

- `tests_next/LEDGER.md` exists with every entry carrying the fields above; every seeded class and every qualifying bug and finding is either an entry or listed as not reproducible with a reason.
- The audit report, posted as a comment on this task, states per `src/` module how many sampled old tests stayed green under a break of their seam, and names the worst tables and fixtures. The 30 largest parametrised functions are all in the sample, and every `tests/meta` guard is broken once against its target.
- The CI baseline is two runs per OS on the 0.17 suite, taken before the rebuild starts and recorded in a comment: per run, test count, wall time, worker count, the top 50 `--durations` with setup and call split, and the run link.
- Mutations are applied only in a scratch worktree, never in the shared tree, and only the selected test ids are run per break, never the full suite.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1111 add-subtask "<title>"`; track with `sq task 1111 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Build the parity ledger from regression classes, bugs and findings

<!-- sq:subtask:ST1:body -->
Build `tests_next/LEDGER.md` from the four sources in the task body: the seeded regression classes, the Verified and Fixed bugs whose fixes touched tests, the defect-severity review findings, and the unique kills ST2 finds. Each entry: seam, behaviour, owning area, owning layer, old test ids, the break that proves it, with empty slots for the new owner test and its recorded red that the area tasks fill. Classes that cannot be traced to a test are listed with the reason, so the rebuild knows to write them rather than port them.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Run the falsification audit per source module on the old suite

<!-- sq:subtask:ST2:body -->
Re-count the suite first (`pytest --collect-only --run-slow`) and cite that count. For each `src/` module, break its seams one at a time in a scratch worktree and run only the old tests that target it. Record per test: red, green, or red only with all its siblings. Cover the 30 largest parametrised functions in full, starting with `tests/cli/test_c_runs_exactly_as_cd_into_the_folder_would.py` (477 rows: layouts by command by schema direction), `tests/unit/test_place_view_tags_fuzz_idempotence_and_invertibility.py` (1,001 rows) and `tests/service/test_a_check_reports_only_on_the_types_that_select_it.py` (488 rows: check by type by level). Break each `tests/meta` guard once against its target. Post the report as a comment on this task: the share that stayed green per module, the rows that carry the information in each large table, and the guards that stayed green.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-10-26T16:15:01Z] `qa` Mara Tester:
  - Re-count at release/0.17 3189c90d (collect-only -n0 --run-slow, one dir at a time, per-file counts summed): 15,768 tests in 830 files. service 5,472 (260); cli 4,464 (235); unit 3,988 (165); integration 1,243 (97); meta 518 (61); tui 77 (11); test_scale 6 (1).
- [2026-10-26T17:35:10Z] `qa` Mara Tester:
  - Falsification audit, increment 1: tests/meta guards and the integrity core. Run at release/0.17 3189c90d in a scratch worktree (one described patch to src/ per break, reverted after each run, only the selected test files run, -n 4). 226 break runs (plus 16 baseline runs); raw per-break results (patch, tests run, red ids) are in `/tmp/claude-1000/-home-pchat-projects-squads/13d208f8-5631-413c-beca-18eeca47958b/scratchpad/raw.tsv` and `.../results/<break>.json` (one file per break with every test's red/green). Measured: red/green of each selected test under each break. Not measured: anything outside the selections below; "green" means green in the sample, a wider sample can still find a killer (it did, 5 times: marked "wide").
    
    **Method note.** "Share green" = sampled tests that were red under none of the module's breaks. A table that goes 400/400 red under one break and green under the next carries one mechanism; "redundant rows" = red tests whose break set equals a sibling row's.
    
    ## tests/meta (US2 acceptance: every guard broken once)
    - All 60 guards were broken once against their target (planted violation, drifted table, or broken target) and all 60 went red. guard runs include 3 misaimed first attempts.
    - Guards that stayed green on my first break and why (all went red on a corrected break):
      - `test_bundled_templates_carry_no_operator_identity`: a first-name leak ("Pierre") in a bundled template stayed GREEN. Real blind spot: the guard reads `full_name:` from `squads/operators/*.md`, which carry the name under `title:`, so it only ever scans for the slug `op-pierre`. Only the slug leak goes red.
      - `test_documented_commands_resolve_against_cli`: an indented, unfenced dead verb in docs stayed green (the extractor needs a fence or inline code; the fenced one went red). Not a defect, extractor scope.
      - `test_bundled_toml_packaging`: green under a docs-force-include break (not its target); red 3/3 when the wheel excludes `*.toml`.
      - `test_bundled_documents_are_splat_ref_addressable`: a non-ASCII bundled key never reaches the guard, the spec loader refuses it first at import (collection error). The `$(` half goes red alone. So the bare-key half is not independently falsifiable.
    - Sub-tests that stayed green while their guard went red: `test_a_backend_does_not_import_the_index` (reads the recorded EDGES table, not the tree: a real `_backends -> _index` import is caught only by `test_the_tree_imports_exactly_the_recorded_edges`); `test_the_scan_*` self-tests (plant in tmp, never see a break of the real tree, by design).
    - Most guards are one assertion: 51 of 63 meta breaks were killed by exactly one test function (the single scan test). The other tests in those files are the guard's self-tests.
    
    ## Integrity core, per module (break runs; sampled tests; share green)
    | module | breaks | sampled | share green | breaks no sampled test caught |
    |---|---|---|---|---|
    | `_index/_store.py` | 12 (+3 wide) | 820 | 84.0% | 3 in the 239-test sample (counter raise, reflog swallow, undecodable index); each is killed by exactly one test in the wide sample |
    | `_index/_reflog.py` | 9 | 85 | 81.2% | `ensure_ascii` flip; missing-file guard (equivalent mutant: FileNotFoundError is already an OSError) |
    | `_index/_reconcile.py` | 10 | 302 | 91.4% | 5: id/sequence_id mismatch accepted; prior entry claimed while its file exists; stored counter dropped; stored padding dropped; dot-dirs walked |
    | `_sections.py` | 22 (+6 wide) | 3,282 | 92.0% | 11: unclosed region read to end; `remove_section` blank-line and trailing-newline absorption (695 remove/sub-entity tests, none sees it); `has_section` close marker; `frontmatter_block_end`; CRLF frontmatter eol; non-ASCII escaping; key order; non-mapping frontmatter |
    | `_itemfile.py` | 11 | 773 | 89.4% | 4: missing-file conversion; skew guard inside `update_frontmatter`; line-ending conform in `write_text`; whole-word id remap |
    | `_paths.py` | 9 (+3 wide) | 1,281 | 98.3% | 5 narrow, `abspath` guard 3 of them (see below); `number_for_id` first-hyphen split; `path_from_process_dir` absolute |
    | `_aio.py` | 10 | 717 | 30.4% | 1: `path_unlink` ignoring `missing_ok` |
    | `_migrations/` (registry, 0.1-0.2, 0.14-0.15, 0.15-0.16, 0.16-0.17) | 11 (+6 wide) | 645 | 92.9% | 5: 0.14-0.15 `updated_at` bump; 0.15-0.16 spelled-default fold; 0.16-0.17 stale definition key, description on a template role; `_wrap_sync` count |
    | `_services/_maintenance.py` repair/renumber/repad | 14 | 284 | 90.8% | 0 |
    | `_duplicate_ids.py`, `_corpus_files.py` | 14 | 418 | 57.7% | 4: stored `extra.slug`; slugless name number; `read_id` malformed file; renamed copy found by number |
    
    (`_aio` share is low because `mkdir` ignoring `parents` reddens 484 rows: the module is thinly broken, widely exercised.)
    
    ## Unique kills (the only test red for a break; feed ST1 source 4)
    Test ids are `tests/<dir>/<file>::<test>`.
    - `_store` s6: `unit/test_read_scope::test_transaction_never_serves_a_stale_snapshot_over_a_newer_index`; break: `transaction()` reads through `load()` (scoped cache) instead of the disk.
    - `_store` s9: `unit/test_read_scope::test_overwrite_also_invalidates_the_scope`; break: `overwrite` stops dropping the read-scope snapshot.
    - `_store` s10: `unit/test_index_allocation::test_a_failure_between_the_temp_write_and_the_replace_leaves_the_index_intact`; break: index write is a plain truncating write.
    - `_store` wide: `integration/test_repair_integrity::test_a_hand_regressed_counter_is_corrected_on_the_next_write` (load stops raising a trailing counter); `service/test_reflog_emission_and_resilience::test_a_failed_reflog_append_does_not_roll_back_the_committed_mutation` (reflog failure propagates); `cli/test_undecodable_squad_files_fail_cleanly::test_an_undecodable_index_reports_the_corrupt_index_message_with_its_repair_remedy` (undecodable index unwrapped).
    - `_reflog` r3, r4: `unit/test_reflog_line_persistence::test_read_lines_skips_a_truncated_trailing_line_without_warning`; `::test_read_lines_warns_on_an_interior_malformed_line_but_returns_the_rest`.
    - `_reconcile` e10: `service/test_index_reconcile_entry_rules::test_a_file_with_no_timestamps_keeps_its_indexed_ones[with-entry]` (indexed timestamps not carried forward).
    - `_sections`: `unit/test_strip_marker_lines_shared_line_prose` two tests (lone-line and shared-line marker removal); `unit/test_sections_keep_the_files_line_endings` (one function each for replace_section padding, append_to_section CRLF, region_lines).
    - `_itemfile` i8: `service/test_custom_type_lifecycle::test_repair_is_a_stable_noop_for_a_squad_holding_a_custom_type_item` is the only test that notices `write_new` no longer creating the parent folder. i11: `service/test_rename_type_writes_each_file_once` (6 rows, one function) is the only caller of a multi-pair id remap.
    - `_paths` p4/p7: `service/test_backend_reconciled_per_entry_pointers::test_orphaned_skill_type_pointer_is_not_reported` is the only test red for the config walk-up and for the root derivation. p5: `unit/test_read_text_decode_and_not_found_guards::test_load_config_raises_squads_error_on_undecodable_bytes`.
    - `abspath` traversal guard: only `service/test_search_and_inbox_degrade_per_file` (6 tests: traversal and symlink-outside-squad rows for search and inbox) goes red; nothing on the write paths (board, resolver, migrations) checks it.
    - `_aio` a5, a6, a7: `unit/test_atomic_write_primitive` (temp cleanup, pid+thread temp name, in-place write).
    - `_maintenance` q1: `unit/test_renumber_offset_plan::test_offset_plan_onto_computes_the_minimal_safe_offset_above_both_ranges`; q6: `integration/test_repair_integrity::test_repair_renumber_resolves_a_sequence_collision` (which file keeps the number); q9: `service/test_repair_and_renumber_hold_the_index_lock_while_they_rewrite::test_a_retype_during_repad_waits` (repad pre-scan); q11: `integration/test_repair_cli_output::test_repair_cli_holds_the_padding_floor_after_file_loss`; q14: `service/test_renumber_service::test_renumber_with_a_by_offset_records_by_and_leaves_onto_null_in_the_reflog`.
    - `_duplicate_ids`/`_corpus_files`: d8 `service/test_check_does_not_report_a_file_renamed_during_the_scan_as_a_duplicate`; c3 `service/test_unreadable_files_degrade_per_file::test_every_command_gives_a_broken_symlink_the_same_diagnosis`.
    - Not killed by any sampled test, so ledger entries must be written, not ported: reconcile counter/padding floors (the repair path has tests, the migrate-time reconcile does not); `remove_section` whitespace; `abspath` on write paths.
    
    ## Redundant rows and never-red tests
    - Redundant rows (red only with siblings, same break set): `_sections` 184, `_aio` 239, `_duplicate_ids/_corpus_files` 78, `_itemfile` 59, `_migrations` 25, `_reconcile` 13, `_store` 9, `_paths` 7, `_maintenance` 3, `_reflog` 0.
    - Never-red tests in a module's sample: `_paths` 1,259 of 1,281, `_migrations` 599 of 645, `_sections` 3,020 of 3,282, `_itemfile` 691 of 773, `_store` 689 of 820. Most are tests that import the module as a fixture helper, not tests of its seams; they are the ones a rebuild should not port without a break.
    
    ## Largest parametrised functions that target these modules (5 of the 30)
    - `cli/test_c_runs_exactly_as_cd_into_the_folder_would` (468 rows, 477 in the file): 5 `_paths` breaks. `client_cwd` ignored: 477/477 red (one mechanism, every row). Walk-up: 30 rows red. Root derivation: 2 rows red. `squad_dir` base and `path_from_process_dir`: 0 red. So under these breaks the information sits in the 30 walk-up rows, the 2 migrate rows and one row's worth of the rest; the other rows repeat the `client_cwd` mechanism.
    - `service/test_a_write_removes_only_the_keys_it_targets` (195): dropping the last key reddens 196/197; key order, non-ASCII, line-ending conform, skew guard and body newline breaks all stay green. One mechanism.
    - `service/test_type_invalid_frontmatter_load_boundary` (198 in a 386-test file): green under store vocabulary validation, malformed frontmatter and non-mapping frontmatter. It targets `Item.from_frontmatter`, not the integrity core; audited with the models/engine area.
    - `unit/test_conform_line_endings` (60+60 functions in a 194-test file): identity break 119 red, edited-in-place break 108 red, dominant-ending breaks 6 to 8 red. Mostly redundant between the two big breaks.
    - `unit/test_place_view_tags_fuzz_idempotence_and_invertibility` (400+400+200, 1,001 in the file): marker-regex break 1,001/1,001 red, replace_section leading and trailing padding 0 red. One mechanism.
    The other 25 of the 30 target other modules (check validators, override loading, CLI gate, console escaping, comment splice) and are for the next increment.
    
    ## Done and remaining
    Done: re-count (15,768 tests, previous comment); all 60 `tests/meta` guards; `_index/_store`, `_reflog`, `_reconcile`; `_sections`; `_itemfile`; `_paths`; `_aio`; `_migrations` registry and the 0.1-0.2, 0.14-0.15, 0.15-0.16, 0.16-0.17 runners; `_maintenance` repair/renumber/repad; `_duplicate_ids` (identity/shared-number/confirm, not the renumber helpers); `_corpus_files`.
    Remaining: `_migrations` runners 0.2-0.3 through 0.11-0.14 plus `_config_text`, `_meta_compat`, `_legacy_extra`; `_maintenance` sync/seed/migration driver/body sweep (`_converge_body_tag`, retired-region strip); `_duplicate_ids` renumber helpers; `_index/_resolver`; the other 25 large parametrised functions; every module outside the integrity core (engine/services/CLI and backend/skills/rendering/TUI areas).
- [2026-10-26T19:08:28Z] `qa` Mara Tester:
  - Audit increment 2, part 1 (re-posted from the run transcript after a WSL crash wiped the raw result files; the counts below are the printed outputs of each break run, the per-test red lists are lost). Sampled = the test files selected for that module; "not caught" = breaks no sampled test noticed.
    
    ## Integrity core, remainder
    - `_migrations` old runners and helpers (0.2-0.3 through 0.11-0.14, `_config_text`, `_meta_compat`, `_legacy_extra`), 645 sampled tests: 35 breaks, 22 caught, 13 not caught. Not caught: 0.2-0.3 story badge drops its title; 0.5-0.7 longest-id-first ordering; 0.4-0.5 skill file name unpadded; 0.8-0.10 re-stamp of a tracked sq-memory and clobbered description; 0.11-0.14 folder created for a dropped type and retired operators listed; config stamp accepting several matching lines; config compare `1 == True`; meta block without a status; `read_flat` keeping the nested key; legacy heading title padding; legacy first body line takes a placeholder. Single-test kills (the only red test): 0.2-0.3 assignee name badge and review findings (`integration/test_migrations::test_v0_2_to_v0_3_lifts_meta_to_frontmatter_and_backfills_the_head`, which is also the only test for the `:meta` removal on its own), 0.7-0.8 severity overwrite and extra-key drop (`unit/test_bug_severity_migration`, two tests), 0.5-0.7 filename-tail, code-span skip and sub-entity title rewrite (all `integration/test_unpadded_id_migration::test_migration_unpads_frontmatter_and_prose_but_skips_code_spans_and_filenames`), 0.4-0.5 stale `path` key in two branches (`integration/test_skill_migration`), 0.11-0.14 re-seed idempotence (`integration/test_new_item_type_migration_surface_parity::test_migrate_is_idempotent_on_an_already_current_squad`), config compare of `nan`, `init.names` report and non-bool display report (one `unit/test_migration_config_text_...` row each), pre-2 upgrade idempotence (`unit/test_legacy_meta_compat`).
    - `_maintenance` sync, seeding and body sweep, 307 sampled tests: 16 breaks, 8 caught, 8 not caught. Not caught: a covering `*.tmp` gitignore pattern; gitignore append gluing onto the last line; unbalanced retired region cut through; reinstated body region corrupted; role-key sweep applied to non-role items; sweep rewriting the whole frontmatter instead of only the retired keys; roster body tag addressed by number; sync notices not deduplicated. Caught: stale ref encoding (2 tests), retired head regions (4), body convergence over author prose (11), adopter-declared role attribute (3), pointer drift report (11), custom skill seeding (3), unindexed skill bodies (9), blocked restamp (2).
    - `_duplicate_ids` renumber helpers and `_index/_resolver`, 418 sampled tests: 13 breaks, 10 caught, 3 not caught (readable-by-index-scan name check; padded-spelling references list; `require_item` returning None, killed in one unrelated-named test only: `service/test_bulk_import_preflights_a_drifted_target::test_a_drifted_target_issue_coexists_with_an_unrelated_validation_issue`, found in the 1,612 ref-named tests). Single-test kills: same-slug refusal (`test_duplicate_item_ids_are_reported::...[padded-and-unpadded-spelling]`), identical-copy refusal (`...[identical-copy-renamed]`), indexed file keeps the id (`test_duplicate_id_guard_identity_and_renumber::test_the_indexed_file_keeps_the_id_even_when_another_name_sorts_first`), shared new number (`...[three-files-all-different]`), id lines counted as references, comment label, list-valued references, first-name-kept ordering (`...::test_with_no_index_the_first_name_is_kept_whatever_the_scan_order`).
    
    ## Engine area so far
    - `_specmerge.py`, 717 sampled tests (44 files named for override and merge), 13 breaks, 12 caught, 1 not caught (`$(self)` at a scalar position). Single-test kills: unanchored token match (`test_a_token_with_trailing_whitespace_is_malformed_not_resolved[$(items)\n]`), spread of a non-list, spread outside a list, aliasing of an override array (`test_an_override_supplied_array_in_the_merged_result_is_independent_of_the_override`). Breaking array replacement into array merge reddens 71 rows, the largest single mechanism.
    - `_workflow/_validity.py` and `_models.py`: first sample 1,214 tests (82 files) for 6 validity breaks, 4 caught (reachability 4, unclosable lifecycle 3, parent cycle 2, duplicate prefix 3); not caught: duplicate alias, a type shadowing a built-in verb. Second sample 692 tests (no cli, no tui): 12 breaks, 5 caught (roster R2 2 tests, completion-equals-initial 1, transition direction 1, any parent type allowed 1, live_initial 1), 7 not caught in that sample (missing fallback role, undeclared initial, `hidden_by_default`, `is_open`, first dropped status, `is_delivered`, `statuses_with_role`). Widened with `-k`: `hidden_by_default` 4 red, `is_open` 1 red (`test_category_aware_default_visibility::test_hidden_by_default_matches_is_open_inverse_except_for_the_in_force_role`), `is_delivered` 6 red; still not caught: first dropped status, `statuses_with_role`, fallback role, undeclared initial.
    - `_workflow/_loader.py`, 1,383 sampled tests (82 files): 8 breaks, all caught. Single-test kills: adding a roster type (1), folder spelling normalisation (1). Others 2 to 8 tests.
    - `_overrides/` (`_service`, `_manifest`, `_stamp`), 717 sampled tests: 10 breaks, 7 caught, 3 not caught: an old stamp always reading as drifted, role-slug escape check (redundant with the earlier `..` guard except for symlinks), bundled hash not CRLF-normalised, double stamp on re-stamp. Single-test kills: unstamped override reads current, update re-stamps a broken override, scaffold clobber (2).
    - `_services/_validators.py` and `_check.py`, 1,552 sampled tests (75 files): 12 breaks, 10 caught, 2 not caught: gate refusing on a warn finding, duplicate marker needing three copies. Single-test kills: `item_title_max` is not single; timestamps reported at error (1), member run twice (2), `blocked_has_blocker` incoming edge (3). Level override ignored reddens 257 tests.
    - Large table `service/test_a_check_reports_only_on_the_types_that_select_it` (488 tests in the file, 384+96 rows): `_resolved_level` break 96 rows red (the level shape rows); `item_title_max` boundary 36 rows; `description_present` whitespace-only and member run twice: 0 rows red. The table plants an empty description, never a whitespace one, and selects each member once. Mechanisms the 384 rows exercise: selection resolved per type, level per shape, each member's planted offender. One break per mechanism reddens one member's rows only, so the member x type rows repeat the same code path per type.
- [2026-10-26T19:38:54Z] `qa` Mara Tester:
  - Falsification audit, backend/skills/rendering/TUI area, partial 1: `_backends/` and `_tui/`. Run at release/0.17 ac1b89a1 (a first pass was lost to the WSL crash and redone), scratch worktree, one described patch per break reverted after each run, `-n 3`, only the selected files, tests/meta excluded. Raw per-break results (patch, tests, red/green): `.../scratchpad/audit-backend/results/<break>.json`, breaks in `c_*.json`. Measured: red/green per test per break. Not measured: tests outside the selection ("green" = green in the sample). Baseline of each selection was green. One run (cc6) was first 238 red, then 6 red on two reruns; I discarded the 238 as an infra flake (concurrent suite and tmp cleanup), so treat any wildly different count as suspect.
    
    ## _backends (`_managed_region`, `_claude_code`, `_frontmatter`, `_agents_md`, `_registry`)
    Selection 477 tests in 48 files (direct imports plus pointer/claude_md/agents_md/backend/sync/managed names). 31 breaks: 84.5% of sampled tests (403/477) red under no break. 74 red rows collapse to 59 distinct (function, break-set).
    - Breaks no sampled test caught (10): `mr7` start marker without end treated as a region; `cc1` settings merge adds no default allow rules to an existing settings.json; `cc8` double quotes kept in the quoted YAML description; `cc9` skill kept for a dropped item type; `cc11` skill body with a lost sq:body region not restored; `cc12` startup commands lose `sq inbox`; `cc14` system skill pointer description taken from the stale item; `am2` AGENTS.md reports live roles' files as orphans; `am4` AGENTS.md example assignee ignores developers; `rg1` unknown backend name surfaces a raw KeyError. Ledger entries must be written, not ported.
    - Unique kills (the only test function red): `mr1` warning stamp dropped: `integration/test_claude_code_backend::test_init_creates_claude_pointers_and_managed_files`. `mr2` replace discards hand-written content: `integration/test_backend_scaffold_warnings::test_a_second_sync_over_an_already_managed_file_warns_only_once_and_never_moves_it`. `mr4` CRLF conformance dropped: `service/test_a_write_keeps_the_files_line_endings::test_a_crlf_managed_region_file_keeps_its_endings`. `mr5` new file loses header: `integration/test_backend_scaffold_warnings::test_agents_md_warns_only_of_content_present_before_init`. `cc4` every skill dir an orphan: `integration/test_backend_scaffold_warnings::test_a_fresh_init_reports_no_orphan_warnings`. `cc6` model passed through: `service/test_a_model_the_host_cannot_render_is_reported_not_dropped::test_every_unrenderable_shape_is_both_dropped_and_reported` (6 rows, one function). `cc15` view tag seeded for an undeclared view: `service/test_skill_creation_seeds_no_tag_for_an_undeclared_view::test_a_newly_created_system_skill_under_a_dropped_view_leaves_the_body_empty`. `cc18` pointer never carries disallowedTools: `service/test_backend_entry_currency_detection::test_a_missing_restriction_on_a_leaf_role_is_an_error`. `am3` also-creatable list includes roster types: `unit/test_managed_section_and_cheatsheet_goldens::test_the_agents_md_managed_section_body_matches_its_pinned_golden`.
    - Two to three killers: `mr3` (5 tests, 2 files), `mr6` (2), `cc2` restriction inverted (3, one file), `cc7` (2), `cc16` default role (2), `am1` legacy role file (2). Broad: `cc10` 19, `cc19` 18, `cc13` 11.
    - Pointer completeness after reactivation and the has_dev roster gate (`developer_roles`, `delegate_example_slugs`) are in partial 2 (roles/interactions).
    
    ## _tui
    Selection 113 tests in 15 files (tests/tui plus direct importers). 15 breaks: 82.3% green (93/113). 11 of 15 breaks no sampled test caught: sequence sort no-op (`u1`), unset badge sort position (`u2`), case-sensitive title sort (`u3`), sort not recursing (`u4`), branch expand (`u6`), `roster_identity_slugs` including skill nodes (`u7`), coarsest age unit (`u9`), sub-entity head story (`u11`), filter field first-wins (`u13`), filter screen dropping the badge filter (`u14`), unknown status intent (`u15`). Unique kill: `u12` reader discussion edited mark: `cli/test_comment_hash_on_every_surface::test_the_reader_tab_puts_the_short_hash_first_in_every_comment`. `u10` assignee in the reader header: 2 tests. `u8` tree root expand: 15 tests. TUI tests are thin on sort/filter logic: 11 of 15 seams go unprotected in the sample.
    
    Done: `_backends`, `_tui`. Remaining: `_interactions` + `_roles`, `_rendering` (engine, templates), `_badges`, `_discussion`.
- [2026-10-26T19:39:11Z] `qa` Mara Tester:
  - Audit increment 2, part 2: services and CLI spine, measured after the crash on a fresh worktree at ac1b89a1 (`-n 3`, targeted files, one break per run). "Not caught" = no sampled test went red. Raw per-break results are in the scratchpad `audit/results/`; the per-test red lists for part 1 are gone.
    
    | module (sample) | breaks | caught | not caught |
    |---|---|---|---|
    | `_services/_items.py` (581 tests, 38 files) | 7 | 4 | renamed file stem unpadded; `link` skipping its own parent-type check (the validator gate behind it still refuses, so the direct check is redundant in this sample); unlink reflog losing the old parent |
    | `_services/_refs.py` (1,154 tests, 76 files) | 8 | 7 | re-adding a ref duplicates it |
    | `_services/_subentities.py` (453 tests, 44 files) | 9 | 8 | marker text accepted in a sub-entity title (the guard that covers it is `service/test_marker_injection_guard`, outside this sample) |
    | `_services/_retype.py` (80 tests, 7 files) | 8 | 7 | status carried across different workflows |
    | `_services/_rename.py` (78 tests, 10 files) | 4 | 4 | none |
    | `_cli/_common.py` spine, `-C`, gate, exit codes, address resolution (1,119 tests, 23 files) | 11 | 8 | absolute `-C` value not replacing the base; `handle_errors` exiting 2 instead of 1; a full id with the wrong prefix accepted |
    
    Single-test kills (the only red test for the break):
    - `_refs`: `service/test_ref_management_guards::test_add_ref_rejects_a_self_reference`; `::test_rm_ref_with_a_kind_leaves_a_different_kind_edge_to_the_same_target_in...` (kind filter); `service/test_dependency_blocking::test_a_closed_dependent_is_never_reported_as_blocked_even_with_an_open_block`.
    - `_subentities`: one test carries two breaks, `service/test_a_deferred_finding_names_the_item_that_carries_the_work::test_the_pointer_is_given_refused_moved_...` (carrier cleared on leaving a deferred status, and an item carrying its own work).
    - `_retype`: `service/test_retype` has one test per refusal (sub-entities, child parent, own parent, no-op, incoming refs); nothing else covers them. `_rename`: `integration/test_rename` for the child-parent and invalid-status refusals.
    - Several of the services breaks reach 1 to 3 tests only; the exit-code, gate and `-C` breaks reach 45 to 190.
    
    Notes: a first run of the `_refs` batch overlapped a cleanup of the shared pytest temp dirs and showed 3 reds for the duplicate-ref break; the re-run showed 0, which is the figure above. `_items` breaks 1 to 4 ran in the same window; their red counts (10, 2, 4, 7) are plausible, and the green ones cannot be inflated by it.
- [2026-10-26T19:47:56Z] `qa` Mara Tester:
  - Audit increment 2, part 3: import, view tags, roster, the large tables, and the share-green figures for part 2. Same method and safety rules, worktree at ac1b89a1, `-n 3`.
    
    **Share of sampled tests that stayed green under every break of the module** (parts 2 and 3): `_items` 96.2% of 581; `_refs` 97.8% of 1,152; `_subentities` 89.4% of 453; `_retype` 65.0% of 80; `_rename` 91.0% of 78; `_cli/_common.py` spine 72.2% of 1,117; `_services/_import.py` 66.3% of 101 (and 100% of a further 295 tests selected by `-k`); `_view_tags.py` 62.4% of 242; `_services/_roster.py` 92.9% of 141. For parts 1 figures see the first increment-2 comment (counts of breaks caught, not shares).
    
    | module (sample) | breaks | caught | not caught |
    |---|---|---|---|
    | `_services/_import.py` (101 tests, 18 files; 295 more by `-k`) | 8 | 3 | a sub-entity handle belonging to another parent, an unknown ref kind, the default kind spelled out, badge-code case, pydantic errors collected as issues. None of these 5 is caught by any of the 295 `-k "handle or import or jsonl or event"` tests either. |
    | `_view_tags.py` (242 tests, 22 files, fuzz table excluded) | 8 | 7 | the out-of-region refusal naming any view instead of the asked one |
    | `_services/_roster.py` (141 tests, 15 files) | 8 | 5 | the duplicate-role check ignoring the legacy slug; default designation on a non-role; `mine` listing roster items; `mine` ignoring `include_closed` |
    
    Single-test kills: `_view_tags` duplicate tag reads as settled (`service/test_view_tag_placement`, two tests) and CRLF region (`unit/test_view_tag_placement_ignores_the_regions_line_endings`, 3); `_roster` the role-already-exists refusal (`cli/test_roles_are_created_through_activate_add_and_dev_add_cli`, 2 rows), the cleared-holders report and the move reporting a change (`service/test_default_role_designation_move`, 2 tests), non-live default (3).
    
    ## Large tables, one break per mechanism
    - `service/test_a_selected_check_loads_or_is_refused_on_every_type_row` (140 cells): refusal of a work policy on a roster type 24 cells red; `ref_rule_target_typed` without a target 11; `blocked_has_blocker` without a blocked status 7; `assignee_present` without a live status 2. The cells are one refusal per mechanism repeated per type row; 117 of 141 tests stay green under the roster break, so the roster mechanism owns 24 cells and the rest belong to other mechanisms.
    - `cli/test_the_gate_lets_past_by_command_and_direction` and its sibling (291 tests in the file): gate direction inverted 142 red; a grant covering both directions 14 red. The two large tables in the file are redundant with each other for the direction mechanism.
    - `unit/test_place_view_tags_fuzz_idempotence_and_invertibility` (1,001 tests, 400+400+200 rows): CRLF-normalisation removal 0 red; append replacing the prose 0 red. Both breaks are caught by smaller tests elsewhere (3 red each), so the 1,001 fuzz rows do not carry these two mechanisms; in the first increment the marker-regex break reddened all 1,001, so the table is one mechanism.
    - `service/test_a_check_reports_only_on_the_types_that_select_it`, `cli/test_c_runs_exactly_as_cd_into_the_folder_would`: see the earlier comments.
    
    ## Status of increment 2
    Done: integrity core remainder (migration runners and helpers, `_maintenance` sync/sweep, `_duplicate_ids` renumber helpers, `_index/_resolver`); engine area: `_workflow` validity/models/loader, `_specmerge`, `_overrides`, `_services` check/validators, items, refs, subentities, retype, rename, import, roster, `_view_tags`, `_cli/_common.py` spine, plus the large tables above.
    Remaining for the engine area: top-level `_views.py` and `_services/_views.py`; `_workflow/_validator_names.py`; the rest of `_cli/` (command modules); `_services/_collab.py`, `_base.py`, `_memory.py`, `_board.py`; rename-status rollback; the other 20 of the 30 largest tables. The backend/rendering/TUI packages are the other QA run's.
    Gaps worth a ledger entry (not caught by any sampled test): import handle/ref-kind/badge-code validation; absolute `-C`; `handle_errors` exit code; full-id wrong-prefix; ref re-add dedup; retype status carry; item `link` parent check and file-stem padding; the roster breaks above; migration idempotence and description-clobber edges; whitespace-only description in the check table.
- [2026-10-26T19:58:20Z] `qa` Mara Tester:
  - Falsification audit, backend/skills/rendering/TUI area, partial 2: `_badges.py` and `_discussion.py`. Same method and commit as partial 1 (ac1b89a1, scratch worktree, `-n 3`, tests/meta excluded). Raw results: `.../scratchpad/audit-backend/results/<break>.json`. Not measured: tests outside the selection.
    
    Selection 1,660 tests in 82 files (importers of the two modules plus badge/discussion/comment/head/mention/summary/subentity names). 18 breaks (9 per module). 92.8% of sampled tests (1,541/1,660) red under no break. 119 red rows collapse to 33 distinct (function, break-set): the comment-hash and format tables are wide and carry few mechanisms.
    - Breaks no sampled test caught (5): `bd3` first_ordered_field ignores the collection's `ordered` flag; `bd4` field default ignored in field_default; `bd5` field_badge_codes does not de-duplicate; `bd9` resolve_collection loses its same-name fallback; `ds9` mentions not lowercased. Ledger entries must be written.
    - Unique kills: `bd1` status badge default emoji: `unit/test_custom_status_badge_resolution::test_a_custom_status_with_no_declared_badge_renders_a_graceful_default`. `ds2` empty author name falls back to slug: `unit/test_comment_header_grammar::test_a_written_header_reads_back_as_the_same_timestamp_slug_and_name` (2 rows).
    - Two to three killers: `ds3` slug refusal (2 tests in 2 files), `ds5` short-hash widening (2), `ds6` hash-token minimum (2), `ds7` ambiguous prefix (2, one file), `ds8` hash in another scope (3 across cli/service/unit), `ds10` comment body indent (2), `ds1` continuation indent (3 functions). Broad: `ds1` 50 rows, `ds10` 23, `ds4` comment hash scope 15.
    
    Done: `_badges`, `_discussion`. Remaining: `_interactions` + `_roles`, `_rendering`.
- [2026-10-26T20:18:53Z] `qa` Mara Tester:
  - Falsification audit, backend/skills/rendering/TUI area, partial 3: `_rendering/` (engine and templates), 16 of 19 planned breaks. Same method and commit as partial 1 (ac1b89a1). Raw results: `.../scratchpad/audit-backend/results/<break>.json` (`en*` engine, `t*` templates).
    
    Selection 1,804 tests in 99 files (engine importers plus render/template/golden names). Share green: 15.9% of sampled tests (287/1,804) red under no break, but that is dominated by `en1` (StrictUndefined replaced by lenient Undefined), which reddens 1,517 tests as one mechanism; without `en1`, see the figure below. Red rows 1,517 collapse to 580 distinct (function, break-set) pairs.
    - Breaks no sampled test caught (3): `en5` an unreadable template override no longer refused; `t1` pointer template `disallowedTools` condition inverted (the pointer-restriction break `cc18` is caught only by the backend test, no test checks the rendered pointer text for this); `t9` bug scaffold heading renamed. Ledger entries must be written.
    - Unique kills: `en2` LRU refresh on cache hit: `unit/test_rendering_env_cache_eviction::test_re_touching_an_entry_marks_it_most_recently_used_so_it_survives_eviction`. `en8` scaffold_body returns None for an unrenderable template: `service/test_template_failures_translate_to_a_clean_error::test_pristine_body_still_swallows_a_broken_template_and_returns_none`. `t4` sub-entity head Assignee label: `unit/test_subentity_head_and_summary_rendering::test_set_head_renders_status_assignee_and_story_badges_into_a_region_it_creates`. `t7` AGENTS.md example assignee ignores developers: `unit/test_managed_section_and_cheatsheet_goldens::test_the_agents_md_managed_section_body_matches_its_pinned_golden` (the one golden carries this).
    - Two to three killers: `en3` cache eviction (3, one file), `en9` item attributes as template fields (3), `t3` skill pointer invocable flag (2, one file), `t6` claude section delegate examples (2, one is the golden). Broad: `en4` default-template fallback 61, `en11` override precedence 31, `t3` 22, `en6` 17, `en7` 15.
    - The golden `test_managed_section_and_cheatsheet_goldens` is the unique or one of two killers for three template breaks (`t6`, `t7`, `am3`), a single point of protection for the managed sections.
    
    Done: `_rendering/_engine.py` and 6 of 8 templates. Not run: `t10` (sub-entity block heading), `t11` (settings.json default allow rule). The has_dev gate input (`developer_roles`) and pointer completeness after reactivation sit in `_interactions`/`_roles`, not run.
    
    Remaining (not started, work stopped by the operator): `_interactions` (playbook, skills, cheatsheet, role guidance) and `_roles` (catalog, loader, resolver, templates, projection): 22 breaks generated in `c_roles_inter_*.json` plus a 3,008-test selection `S_roles_inter.txt`, none run.
- [2026-10-26T20:19:00Z] `qa` Mara Tester:
  - Correction to partial 3: the figure promised for _rendering without en1 is 92.2% green (1,664 of 1,804 sampled tests red under none of the other 15 breaks).
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Record the per-OS CI baseline with durations and worker counts

<!-- sq:subtask:ST3:body -->
The CI test job runs on demand through the manual `workflow_dispatch` trigger on `test.yml` (`gh workflow run test.yml --ref release/0.17`); the later increments reuse it. Make that job print `--durations=50` with worker counts (it runs with `-q` and prints neither). Run it twice per OS on the 0.17 suite before the rebuild starts, and record per run test count, wall time, the worker count `-n auto` got, and the top offenders with their setup and call split. TASK-1095 is cancelled and this subtask carries its profiling. Windows runs the full suite, so its profile is the one that steers the rebuild. Check whether Windows Defender scans the temp directory on the hosted runner. Record what was measured and what was inferred.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-10-26T14:04:03Z] `devops` Hugo Ops:
  - Added a bare workflow_dispatch trigger to .github/workflows/test.yml (no inputs; push and pull_request triggers unchanged, no step gated on event_name). YAML parses; actionlint not installed. Uncommitted. After commit and push, trigger the full 3-OS matrix plus lint with: gh workflow run test.yml --ref release/0.17
- [2026-10-26T14:04:58Z] `manager` Catherine Manager:
  - Two 0.17 baseline runs dispatched on release/0.17 at 41a4d8f6: runs 40336251100 and 40336286733 (test.yml, workflow_dispatch). Record per-OS durations from both when they finish.
- [2026-10-26T15:09:14Z] `manager` Catherine Manager:
  - 0.17 baseline on release/0.17 at 41a4d8f6, pytest step only. Windows: 45m48s and 53m04s (18 failed, 15508 passed, 150 skipped — the same 18 path-separator test failures in both runs, being fixed). macOS: job 13m24s and 18m07s. Ubuntu: job 14m36s and 14m18s. Every OS is over its target on both runs.
- [2026-10-26T15:11:06Z] `python-dev` Elias Python:
  - Windows CI: the 18 failures were test-side. The tests hard-coded POSIX separators against text the code builds from native Paths. Fixed: the grammar-refusal test now expects str(Path(".overrides") / "roles.toml"); the activate remedy test now expects path_from_process_dir(file), the same helper the message uses. The message is unchanged: .overrides/roles/<slug>.toml in the first half is squad-relative display text with "/", and the remedy half is a process-relative shell path, native by design. Other .overrides/ literal assertions are against that display text or were not in CI failures, so left alone.
- [2026-10-26T16:14:31Z] `devops` Hugo Ops:
  - Profiling hook added to `.github/workflows/test.yml` (uncommitted until pushed): a `workflow_dispatch` boolean input `durations` (default false). Push and PR runs are unchanged. With it on, the test job runs `pytest --durations=50 --durations-min=0` after printing `os.process_cpu_count()`.
    
    Trigger, once per run (two per OS: the matrix covers all three):
    
        gh workflow run test.yml --ref release/0.17 -f durations=true
    
    Reading a run, `gh run view <id> --log` (add `--job <job-id>` per OS):
    - Worker count: the log line `CPU count seen by -n auto: N` in the "pytest (profile)" step. `-n auto` resolves to that value in xdist, but the worker count itself is inferred, not printed, because `-q` in addopts hides the xdist "created: N/N workers" header.
    - Test count and wall time: the final summary line, `N passed ... in Xs`.
    - Durations: the `slowest 50 durations` block. Setup, call and teardown are separate rows, labelled in the second column. Pytest does this by default, so no `-vv` is needed.
- [2026-10-26T16:15:15Z] `manager` Catherine Manager:
  - Profiling runs dispatched at 3189c90d with durations=true: 40357268518 and 40357294168. Record count, wall time, worker count and top-50 durations from both per OS when they finish.
- [2026-10-26T17:36:12Z, edited 2026-10-26T17:36:28Z] `devops` Hugo Ops:
  - Baseline from runs 40357268518 (run 1) and 40357294168 (run 2), both at 3189c90d, both green. The raw job logs are in `/tmp/claude-1000/-home-pchat-projects-squads/13d208f8-5631-413c-beca-18eeca47958b/scratchpad/ci-profile/` as win1, win2, lin1, lin2, mac1 and mac2 (`.log`).
    
    Measured, per OS and run. Wall time is pytest's own summary line, which covers the pytest step only. The workers column is `os.process_cpu_count()` printed before the run, so the worker count is inferred from it (xdist's own header is hidden by `-q`). The top-50 sum is the sum of the 50 listed durations, counted across all workers.
    
    | OS | run | tests | wall | workers | top-50 sum |
    |---|---|---|---|---|---|
    | ubuntu | 1 | 15752 passed, 16 skipped | 779.8s (13:00) | 4 | 222s, 50 call |
    | ubuntu | 2 | 15752 passed, 16 skipped | 857.3s (14:17) | 4 | 230s, 50 call |
    | macos | 1 | 15752 passed, 16 skipped | 723.5s (12:04) | 3 | 159s, 48 call + 2 setup |
    | macos | 2 | 15752 passed, 16 skipped | 945.9s (15:46) | 3 | 209s, 48 call + 2 setup |
    | windows | 1 | 15618 passed, 150 skipped | 3737.8s (62:18) | 4 | 440s, 32 call (325s) + 18 setup (115s) |
    | windows | 2 | 15618 passed, 150 skipped | 2855.0s (47:35) | 4 | 408s, 27 call (244s) + 23 setup (163s) |
    
    Run-to-run spread on the same code: ubuntu 10%, macos 31%, windows 31%. Treat the walls as plus or minus a third.
    
    Top 15 durations, Windows run 1 (the full 50 rows are in win1.log). Seconds, phase, test module::test:
    - 22.6 call meta/test_the_process_directory_is_only_read_at_two_sites::test_every_shape_goes_red_when_injected_into_a_copy_of_the_real_tree
    - 20.0 to 22.2, 8 calls, meta/test_override_manifest_and_stamp_freshness: the content-store rebuild tests
    - 14.0 call meta/test_no_bundled_subentity_kind_literal_outside_the_spec_layer::test_every_allowed_pair_is_still_produced_by_the_scan
    - 12.2 call cli/test_every_tree_form_returns_on_a_cyclic_corpus_cli
    - 9.7 and 9.1 call meta/test_the_commands_past_the_gate_are_the_commands_that_declare_a_grant (2 params)
    - 8.9, 8.5 and 7.6 setup cli/test_every_item_edit_verb_takes_an_optional_as, test_clearing_an_assignee, ...operator update-system (setup alone)
    - 8.0 setup cli/test_a_line_separator_in_a_message_cannot_forge_a_header (the same test appears 3 times in the top 50 at 8.0, 6.8 and 6.6s of setup)
    
    Windows run 2, the same offenders at 14 to 17.5s for the 8 rebuild tests and the process-directory test, plus 5 to 15.6s of setup in cli/test_content_writes_on_a_generated_role_or_skill_are_refused (7 entries), cli/test_a_write_restores_the_region_it_needs (3 entries at 5 to 7.8s), cli/test_human_output_prints_names_with_pronouns (3 entries, 5 to 12.5s) and cli/test_service_memo_bypass_isolation (2 entries, 6 to 11.5s). Setup rows are 18 of the top 50 on win1 and 23 on win2, but only 0 (ubuntu) and 2 (macos) on the others.
    
    Top of the Linux and macOS lists: the process-directory meta test is first on both (34.7s ubuntu run 1, 12.9s macos run 1), then the subentity-kind-literal scan (23.4s and 9.3s), then the cyclic-corpus tree tests (10.4s and 5.6s). Below those, ubuntu has about 30 entries of 2.8 to 3.1s from one module, `test_each_spec_document_is_loaded_at_most_once_per_invocation` (it spawns CLI processes); macos has the same module at 1.3 to 1.7s.
    
    What the durations say (the reading, not a measurement of a cause):
    1. Windows time is spread thin, not concentrated. The top 50 are 408 to 440s of roughly 15000 worker-seconds (4 workers times 3700s), about 3 percent. Removing every listed offender would save a few minutes of the 47 to 62 minutes. A rebuild that only fixes slow tests does not help Windows.
    2. Per-test cost is the driver. Windows spends 0.73 to 0.96 s of worker time per test (4 workers times wall, divided by 15618 tests). Ubuntu is 0.20 to 0.22 s and macOS about 0.14 to 0.18 s. That makes Windows roughly 3.5 to 4.5 times slower per test on the same 4 CPUs, on the same suite. The most likely source, inferred and not isolated, is per-test fresh squad setup plus subprocess spawn and file I/O (tmp_path squad init, git, `uv`, process starts), which are each several times dearer on Windows.
    3. Fixture setup is where Windows differs. Only on Windows do `setup` rows enter the top 50 (18 to 23 entries, 5 to 15.6s each), all on `cli/` tests that build a squad per test or per parametrised case. On Linux and macOS no cli fixture is slow enough to appear. The Windows setup rows (per-test squad init in parametrised cli modules, repeating 3 to 7 times each) are the specific targets.
    4. A handful of whole-tree meta tests dominate the call phase on every OS: the process-directory scan (13 to 35s), the subentity-kind-literal scan (9 to 23s), the 8 override-manifest content-store rebuild tests (8s on macOS, 14 to 22s on Windows; each rebuilds from git tags) and the cyclic-corpus tree tests (6 to 12s). These are worth restructuring in the rebuild (one scan shared instead of repeated per test) but are small against the Windows total.
    5. Test counts differ by OS because 134 more tests are skipped on Windows (150 against 16); the same suite otherwise.
    
    Not measured and so not claimed: Windows Defender scanning of the temp directory (no CI step queried Defender; the logs do not mention it), whether xdist actually started 4 workers on Windows and 3 on macOS (inferred from the CPU count), and the Windows per-operation split between process spawn and file I/O (no profile at that level). Check Defender separately with `Get-MpPreference` (exclusions and real-time monitoring) in a dispatch run if the rebuild needs to know. One more caveat: the 31% spread on macOS and Windows means a 10 to 20% change in a later run is inside the noise.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T19:48:41Z] `tech-lead` Olivia Lead:
  - Re-read for Ready on 2026-10-24: recounted the suite (13,931 tests, 751 files), set the ledger at tests_next/LEDGER.md and the audit report as a comment here, added the meta-guard audit, the ST2-before-ST1 order and an on-demand CI run with durations (ST3). Moved to Ready.
- [2026-10-24T21:56:19Z] `tech-lead` Olivia Lead:
  - Added depends-on TASK-1123 (startup, FEAT-916) and TASK-1124, TASK-1125, TASK-1126 (FEAT-1092 structure). The ledger's seam fields and the audit's break patches name modules and functions those tasks move, so this inventory runs on the code as it will stay. The queue in the body's second paragraph now includes them.
- [2026-10-27T19:54:56Z] `qa` Mara Tester:
  - Falsification audit, backend area, partial 4A (status after the machine reboot; nothing from the lost run is claimed beyond what is listed here).
    
    Context: the run for `_interactions/` and `_roles/` (plus the roster projection for pointer completeness after reactivation, and the two unrun template breaks t10/t11) was at about 93 of 122 breaks when the reboot wiped the tmpfs scratchpad (per-break JSONs, scripts, worktree). Nothing was posted before. Results are being persisted under `/home/pchat/.cache/squads-audit/backend/` from now on.
    
    Kept from the transcript (printed runner output that I saw, NOT re-measured, no per-test red lists):
    - Baseline of the 3,535-test union selection (219 files, `--collect-only`): 3,526 passed, 0 red, 9 not passed-or-failed (skipped), `-n 3`, at 70b56716.
    - 122 breaks were defined and each patch was dry-checked to apply exactly once: `_role_guidance` 20, `_playbook` 10, `_cheatsheet` 5, `_skills` 16, `_interactions/_loader` 8, `_roles/_catalog` 12, `_roles/_resolver` 20, `_roles/_templates` 9, `_roles/_loader` 11, `_services/_roster_projection` 9 (pointer completeness, retire/reactivate), t10, t11. Definitions were in the lost scratchpad and are being rewritten from my own transcript.
    - Per-module selections (tests collected): guidance 349, playbook 749, cheatsheet 76, skills 933, interactions loader 232, catalog 793, resolver 554, templates 604, projection 209; breaks ran on unions of these (about 1,000 tests each); t10/t11 on 1,090 tests in 89 backend/golden/settings/sub-entity files.
    - Break counts seen in the log (red / passed in that break's selection): ig1 32/1104, ig2 30/1106, ig20 0/1136, ip1 5/938, ip2 3/940, ic5 1/803, is1 0/1060, is2 26/1034, is3 57/1003, is4 0/1060, is5 2/1058. Reading: ig20 (a mapping role's `capabilities` dropped in `role_like`), is1 (`skill_description` for a non-`sq-` slug returns empty) and is4 (`item_type_for_skill_slug` matching roster types) went red under no sampled test; I stand behind these three as "no sampled test caught" only after re-measure, so they are re-run too.
    
    Not reconstructible: every other break's result, the share green per module, unique kills, the killers and the broad ones. All 122 breaks must be re-run. Re-run now, a comment per module group follows.
- [2026-10-27T19:58:49Z] `qa` Mara Tester:
  - Audit increment 2, part 4, partial A (recovery note). A machine reboot wiped the tmpfs scratchpad (raw per-break JSONs, scripts, worktree) before anything was posted. Everything below is reconstructed from tool output I saw in the run transcript, not from persisted files, unless marked "re-measured". All scripts, break definitions and results now live under `/home/pchat/.cache/squads-audit/engine/` (worktree `wt` there, release/0.17 70b56716, `-n 3`, targeted files only). Per-module comments follow as each group finishes.
    
    ## Large-table list (re-derived by collect-only, before the reboot; measured)
    Collect-only per directory, grouped by function id without params: 15,250 `::` lines for service/cli/unit/integration/tui (service 5,472, cli 4,464, unit 3,988, integration 1,243, tui 77 match the earlier 15,768 total minus tests/meta 518, which my grep did not list). The 10 already covered in parts 1 to 3: `cli/test_c_runs_exactly_as_cd...` (468), the three `unit/test_place_view_tags_fuzz...` functions (400+400+200), `service/test_a_check_reports_only_on_the_types_that_select_it` (384+96), `service/test_type_invalid_frontmatter_load_boundary` (198), `service/test_a_write_removes_only_the_keys_it_targets` (195), `unit/test_conform_line_endings` (60+60), `service/test_a_selected_check_loads_or_is_refused_on_every_type_row` (140), the gate tables in `cli/test_the_gate_lets_past_by_command_and_direction` (120+108).
    The 20 still to audit (rows): `cli/test_a_damaged_override_is_a_clean_error_cli` (400), `unit/test_console_escape_round_trip` (168 + 78), `unit/test_comment_splice_by_line_span` (162 + 162), `cli/test_each_spec_document_is_loaded_at_most_once_per_invocation` (144), `cli/test_content_writes_on_a_generated_role_or_skill_are_refused_cli` (136), `service/test_body_written_reports_exactly_what_a_first_body_write_would_replace` (108), `service/test_item_title_max_selected_at_error_refuses_exactly_what_check_reports` (96 + 96), `service/test_description_present_reads_each_summary_shape` (96), `service/test_a_check_reports_only_on_the_types_that_select_it::test_selecting_the_check_on_another_type_leaves_this_type_silent` (96), `service/test_item_title_max_counts_characters_against_the_declared_number` (72), `cli/test_a_line_separator_in_a_message_cannot_forge_a_header_cli` (66), `cli/test_roster_body_verb_by_shape_cli` (64), `unit/test_the_gate_runs_only_the_members_that_can_refuse` (60), `service/test_a_role_declares_capabilities_that_resolve_onto_the_role` (60), `service/test_a_skills_operator_invocable_resolves_from_stored_value_else_declared_default` (54), `cli/test_pronouns_are_set_and_cleared_through_the_verbs_cli` (51), `service/test_settled_requires_discussion_reads_the_settled_flag_and_the_items_own_comments` (49). None of the table breaks were run yet (they were queued after the module groups), so no table result is claimed here.
    
    ## Reconstructed results (seen in output, not persisted; marked for re-run)
    `_views.py` + `_services/_views.py`, sample 1,040 tests (70 files selected by `squads._views|_services._views|workflow view|view_tag|resolve_source|render_view`), baseline green (1,040 of 1,040):
    - v1 ref source ignoring the default ref kind: 2 red. v2 ref source in index order: 0 red (not caught). v3 subtree source not filtered by declared type: 1 red.
    - sv7 `disable_view` skipping the out-of-region refusal: 8 red. sv8 `add_view` addressing roster hosts by number: 0 red (not caught). sv9 `disable_view` never reinstating a missing body region: 0 red (not caught). sv11 `render_view` ignoring a declared transform: 14 red. v15 role view classification ignoring whether the view is declared: 5 red.
    That is 8 of about 26 planned `_views` breaks seen; the rest ran but their counts were not displayed to me. These 8 are the only figures I can stand behind from before the reboot; the other `_views` runs and all other groups are re-run, so no share-green figure for `_views` is claimed yet. The earlier wider baselines (collab and validator-name selections of about 3,000 tests) were green but are superseded by narrower selections now.
    
    ## Break definitions
    Defined and persisted (re-created from the transcript after the reboot, apply-checked against HEAD, 0 bad): `_views.py` 14 + 6, `_services/_views.py` 10, `_workflow/_validator_names.py` 17, `_services/_collab.py` 34, `_services/_base.py` 30, `_services/_memory.py` 5, `_services/_board.py` 3, rename-status rollback 10. Written but not yet re-created on disk: 156 `_cli/` command-module breaks and 79 large-table breaks (re-created before their groups run).
    
    ## Done and remaining
    Done: re-derivation of the 20 remaining large tables; break definitions and harness persisted. Remaining (all of the scope): re-run `_views`, rename rollback, memory, board, `_base`, `_collab`, `_validator_names`, then the 20 tables and the `_cli/` modules. The engine area is not complete.
<!-- sq:discussion:end -->
