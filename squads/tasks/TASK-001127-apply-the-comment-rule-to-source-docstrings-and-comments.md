---
id: TASK-1127
sequence_id: 1127
type: task
title: Apply the comment rule to source docstrings and comments
status: Done
parent: FEAT-1092
author: tech-lead
priority: medium
refs:
- REV-956:addresses
- TASK-1126:depends-on
description: 'REV-956 F18: per-package prose sweep of src/ against the comment rule,
  plus a release-version guard.'
subentities:
- local_id: ST1
  title: Re-run the comment scan and add the version guard
  status: Done
  story: US6
- local_id: ST2
  title: Sweep the services package
  status: Done
  story: US6
- local_id: ST3
  title: Sweep workflow, overrides, index, models and migrations
  status: Done
  story: US6
- local_id: ST4
  title: Sweep the CLI and TUI, leaving help docstrings
  status: Done
  story: US6
- local_id: ST5
  title: Sweep the remaining packages and report the after-count
  status: Done
  story: US6
created_at: '2026-10-24T21:54:04Z'
updated_at: '2026-10-28T12:46:06Z'
---
<!-- sq:body -->
## Goal

Bring the docstrings and comments under `src/squads/` within the project comment rule: a docstring is one or two sentences of what and why, a comment that restates the code is deleted, and there are no release versions, ticket ids or history outside migration runners. Finding F18. Test prose (F19) is not swept here: it rides the test-suite rebuild, which writes the new suite to the rule from the start (TASK-1112).

## Measure first

REV-956's docstring check counted 627 docstrings over five non-blank lines in 95 of 137 files on 2026-10-17. ST1 re-runs the review's mechanical scan on the tree as it stands. The scan uses `ast` plus `tokenize` over whole docstrings and comment runs with whitespace collapsed, so a line-wrapped token is not missed. Its checks: a docstring over five non-blank lines, a comment run over three lines, a release version outside `_migrations/`, a ticket-id shape, history phrasing. The re-run per-file table is the worklist and is posted as a comment here. The review's table (largest first: `_services/`, `_workflow/`, `_cli/`, `_interactions/`) is only the seed.

## Approach

- One pass per package group (ST2 to ST5), largest first, not one item per file.
- The rewrite is a judgement, not a truncation. Every long docstring holds a real constraint somewhere, so keep that constraint in one or two present-tense sentences and drop the rest. Apply the board's stranger test per sentence: if only someone who had just made the edit could have written it, it goes. Design history, rejected alternatives, citations of test paths, and names of methods that do not exist move out of the code; the commit message carries anything worth keeping.
- **Out of the sweep:** Typer command callbacks under `src/squads/_cli/`, whose docstrings are the `--help` text adopters read. Changing them is a CLI output change, owned by the writer and pinned by help goldens, so they are left alone here. Migration runners keep their version references. Jinja templates are not in scope.
- After rewriting a recurring claim, grep a distinctive fragment of the old wording across `src/` to close its copies.

## Tests

- **One `tests/meta` guard:** no release-version string (`0.N`, `v0.N.N`) in a comment or docstring outside `src/squads/_migrations/`. It uses the same `ast` plus `tokenize` scan, has a liveness row that plants a version and sees it fail, and lands after the hits are cleared, with no allowlist. The ticket-id guard already exists.
- No docstring-length guard yet: with today's counts it would only be an allowlist. Report the after-count so the operator can decide whether a ceiling earns a guard.
- The suite, pyright and ruff stay clean. No assertion is edited, since prose changes no behaviour.

## Generated output

None. Help text is excluded, so no CLI output changes, and no template is touched.

## CHANGELOG substance

None for adopters; report that to the writer.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1127 add-subtask "<title>"`; track with `sq task 1127 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Re-run the comment scan and add the version guard

<!-- sq:subtask:ST1:body -->
Re-run REV-956's mechanical comment scan (`ast` plus `tokenize`, whitespace collapsed) over `src/squads/` on the tree as it stands. Checks: docstrings over five non-blank lines, comment runs over three lines, versions outside `_migrations/`, ticket ids, history phrases. Post the per-file table as a comment here as the worklist, then add the release-version guard once ST2 to ST5 have cleared its hits.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-10-26T12:05:13Z] `python-dev` Elias Python:
  - Scan run and worklist posted on the task; version guard follows once the version hits are cleared.
- [2026-10-26T12:31:05Z] `python-dev` Elias Python:
  - ST1 handoff. Scan re-run and worklist posted above (before counts: 595 docstrings over five non-blank lines and 227 comment runs over three lines in 113 files; 12 release-version hits outside `_migrations/`, ticket ids 0, history phrasing 80 raw hits, most false positives such as "no longer declares").
    
    Version guard landed: `tests/meta/test_source_comments_and_docstrings_name_no_release_version.py`. It scans comments (tokenize) and whole docstrings (ast, whitespace collapsed) under `src/squads/` outside `_migrations/`, with no allowlist, and has liveness rows that plant a version in a module docstring, function docstring, wrapped docstring, trailing comment and comment line and see each caught (plus negative rows for string literals and other numbers). I cleared all 12 hits first, in `_index/_reflog.py`, `_models/_schema.py`, `_overrides/_manifest.py`, `_overrides/_stamp.py`, `_rendering/_engine.py`, `_util.py` and `_services/_results.py`: prose only, AST identical.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Sweep the services package

<!-- sq:subtask:ST2:body -->
Sweep `src/squads/_services/` against the comment rule using the ST1 worklist: one or two present-tense sentences per docstring, no restating comments, no history or versions. Apply the stranger test per sentence.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-10-26T12:31:06Z] `python-dev` Elias Python:
  - ST2 handoff. `src/squads/_services/` swept (24 files); docstrings and comments only.
    
    Before (ST1 scan) vs after, for `_services/`: docstrings over five non-blank lines 195 -> 15; comment runs over three lines 73 -> 0; release versions 1 -> 0; ticket ids 0 -> 0; history-phrase hits 20 -> 9, all remaining false positives describing present state ("no longer declares", "used to attribute").
    
    Remaining 15 over-five docstrings each hold several real constraints (6 to 20 lines): `_rebuild_index_from_disk` (18), `_scan_for_check`, `backend_entry_drift`, `_reject_unwritable_body`, `sync`, `_renumber_held`, `graph`, `GraphNode`, `update_role`, `set_default_role`, `workload`, `project_item`, `remove_block`, `_validators` module, `_parent_acyclic`. Left as is rather than truncating a constraint. A ceiling guard of 20 lines would pass today without an allowlist; one of 5 would need those 15.
    
    Dropped: design history, rejected alternatives, test-file citations, restatements. Kept as shortened present-tense constraints: skew/crash direction, confirm-round semantics, unlink delta scoping, rename atomicity, injective Mermaid escape, third-state files.
    
    Verification: AST of every changed file equals HEAD with docstrings stripped (no code change, 29 files); pyright 0 errors, ruff check and format clean; pytest at -n 4 per directory: meta 502, unit 3977, service 5402, integration 1235, cli 4450, tui 77, all passed (skips as before); no test assertion edited; `sq check` clean. Not committed.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Sweep workflow, overrides, index, models and migrations

<!-- sq:subtask:ST3:body -->
Sweep `src/squads/_workflow/`, `_specmerge.py`, `_overrides/`, `_index/`, `_models/` and `_migrations/` against the comment rule. Migration runners keep their version references.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-10-26T13:36:54Z] `python-dev` Elias Python:
  - ST3 handoff. Swept `_workflow/`, `_specmerge.py`, `_overrides/`, `_index/`, `_models/` and `_migrations/` (37 files); docstrings and comments only.
    
    Counts (docstrings over five non-blank lines / comment runs over three lines): before 173 / 76 in 47 files, after 105 / 48. Release-version hits outside `_migrations/` stay at 0 under the guard, and runners keep their version references. The remaining long ones each hold several contracts: `_index/_store.py` module docstring (49 lines: lock order, the skew-direction rule with its table and exemptions, request-scoped reads, failure model), `_index/_reflog.py`, `_specmerge.py` module, `_workflow/_loader.py` phases, `_workflow/_validator_names.py` floor comment, `_overrides/_manifest.py`, and the migration runner module docstrings.
    
    Constraints kept on purpose: three-lock order and release-in-reverse, markdown-ahead skew table and exemptions, transaction never reads the read scope, reflog never-raise and buffer-time snapshot, ContextVar store-ownership caveat, marker-family has no close marker, splat/token-territory rules, collect-all versus fail-fast, version-qualified unknown-key menu, ref-kind and badge alignment plane attribution, validator-floor reasons, frozen-vocabulary rules in runners, and mid-chain skew in the 0.14 to 0.15 runner. Dropped: design history, rejected alternatives, restatements and a false "module-level singleton" claim on `WorkflowSpec` (the spec is carried by the caller). Two comments carried a removal trigger (`is_meta` shim dropped at 1.0) and kept it.
    
    Verification: AST of all 37 changed files equals HEAD with docstrings stripped; pyright 0 errors; ruff check and format clean; pytest at -n 4 per directory: meta 518, unit 3977, service 5402, integration 1235, cli 4450, tui 77, all passed. Not committed.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Sweep the CLI and TUI, leaving help docstrings

<!-- sq:subtask:ST4:body -->
Sweep `src/squads/_cli/` and `_tui/` against the comment rule, except Typer command callbacks, whose docstrings are `--help` text and stay as they are.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-10-26T14:48:20Z] `python-dev` Elias Python:
  - - ST4 handoff. Swept `src/squads/_cli/` and `_tui/` (15 files with ST5's); docstrings and comments only, by hand.
    
      Counts (docstrings over five non-blank lines / comment runs over three lines, same scanner before and after, classes and modules included): `_cli/` 88 / 38 -> 52 / 2, `_tui/` 6 / 1 -> 3 / 0. Combined 94 / 39 -> 55 / 2. What remains in `_cli/`: the Typer callbacks left alone (`list_items`, `tree`, `renumber`, `search`, `graph`, `import_events`, `scaffold`, `diff`, `role_catalog`, `update_role`, `comment`, plus the other callbacks that were already under the limit), the module grammar listings (role, skill, memory, board, operator), the `sq workflow` catalog docstrings (13 to 16 lines each, one line per published JSON key), and a dozen contract docstrings in `_common.py` (`command`, `get_service*`, `spec_aware_command_cls`, `bind_active_spec`, ...) at 6 to 11 lines.
    
      Constraints kept in one or two sentences: the root-context marker shared by the two `command` bridge calls (one read scope, one `Service`); fail-soft help paths versus refusing answer paths; stale-alias and dropped-type "advertise vs dispatch" split (why `get_command` must not hide a dropped name); the override-failed refusal at the root group; `--parent ""` is-not-None rule; `live_only` on slug resolution; `--json` key meanings and join keys in the catalog docstrings; exit 3 versus 1 for applied-with-errors import; the `sq check` fallback-mode table.
    
      Dropped: byte-identical claims, "mirrors the previous implementation", incident narratives behind each guard, restated call-site lists. Fixed one fresh false claim along the way (`from_extra_or_item` named in a rewritten docstring does not exist; `RoleDef.from_item` does).
    
      Verification: docstring-stripped AST of every changed file equals HEAD (50 files, tree-wide with ST5); control-character scan finds only the intentional `\f` in `tree`, `role_catalog`, `role_list`, `set_default_role`, and no Typer callback docstring changed; pyright 0 errors; ruff check and format clean; pytest at -n 4 per directory: meta 518, unit 3984 (2 skipped), cli 4451 (1 skipped), service 5402, integration 1235 (8 skipped), tui 77, all passed, zero FAILED. `sq check` clean. Not committed.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Sweep the remaining packages and report the after-count

<!-- sq:subtask:ST5:body -->
Sweep the remaining packages and top-level modules (`_interactions/`, `_roles/`, `_backends/`, `_rendering/`, `_views.py`, `_discussion.py`, `_badges.py`, `_sections.py`, `_itemfile.py` and the rest) against the comment rule. Post the after-count of docstrings over five lines.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
- [2026-10-26T14:48:21Z] `python-dev` Elias Python:
  - - ST5 handoff. Swept the remaining packages and top-level modules: `_views`, `_discussion`, `_badges`, `_sections`, `_view_tags`, `_itemfile`, `_aio`, `_actor`, `_context`, `_errors`, `_paths`, `_specload`, `_interactions/`, `_roles/`, `_backends/`, `_rendering/`, `_memory/`, `_board/`; prose only, by hand.
    
      Counts for this scope (docstrings over five non-blank lines / comment runs over three lines): 133 / 39 -> 98 / 10. Per package: top-level modules 69 / 15 -> 46 / 5; `_backends` 19 / 13 -> 17 / 3; `_interactions` 29 / 7 -> 25 / 2; `_roles` 12 / 2 -> 9 / 1; `_rendering` 4 / 5 -> 3 / 2; `_memory` 5 / 0 -> 3 / 0; `_board` 4 / 0 -> 4 / 0.
    
      Whole tree after ST2 to ST5 (same scanner, classes and modules included, so the numbers differ from the ST1 table's method): 350 / 127 before ST4 and ST5, 276 / 61 after. Per package after: top-level 46 / 5, `_backends` 17 / 3, `_board` 4 / 0, `_cli` 52 / 2, `_index` 9 / 2, `_interactions` 25 / 2, `_memory` 3 / 0, `_migrations` 19 / 6, `_models` 12 / 5, `_overrides` 8 / 4, `_rendering` 3 / 2, `_roles` 9 / 1, `_services` 18 / 1, `_tui` 3 / 0, `_workflow` 48 / 28. The 28 comment runs left in `_workflow/` and 6 in `_migrations/` are the largest block still over three lines, untouched by this increment.
    
      Constraints kept: the position-blind marker scan and `reject_markers` as the real guard (`find_markers`); atomic-write contract and the regenerable-versus-data write split (`_aio`); the five per-host backend questions and the non-abstract-default rationale; the skew ordering rule (`_itemfile`); the strict versus rendering-only collection resolvers; the playbook override's no-deselect and coverage rules plus the known guide-prose limitation; who-wrote-the-guide exemption for dropped playbook guides; bundled-blind skill-slug primitives; the engine cache's not-thread-safe constraint; the retire/activate remedy distinction.
    
      Dropped: design history, rejected alternatives, test-path citations, restated call sites. Fixed stale names found while rewriting: `ServiceCore._project_roster_item` (now `RosterProjection.project_item`, also in `_roster_projection.py`), `RoleDef.from_extra_or_item`; also removed three history phrases left in ST2/ST3 text (`_specmerge.py`, `_subentities.py`, "today" in two docstrings).
    
      Ceiling guard recommendation (operator decides): the longest docstrings now are 59 lines (a migration runner), 49 (`_index/_store.py`), 35 (`AgentBackend`), 32 and 30 (loader and merge module docstrings). Offenders by ceiling: over 50 lines 1, over 30 lines 4, over 25 lines 10, over 20 lines 11, over 15 lines 25, over 10 lines 72. A ceiling of 60 passes with no allowlist but only catches runaway growth; 25 needs ten allowlisted contract docstrings, which is the allowlist ST1 warned against. I would not add a docstring-length guard; the release-version guard already covers the mechanical regression, and length without judgement just invites padding or truncation of real constraints. A comment-run guard is worse for the same reason.
    
      Verification (covers ST4 as well): AST of every changed file equals HEAD with docstrings stripped (50 files); control characters only in the four untouched `\f` callbacks; stale-name resolution over every backticked identifier in the added prose done against `src/`; release-version guard green; pyright 0 errors; ruff check and format clean; pytest at -n 4 per directory: meta 518, unit 3984, cli 4451, service 5402, integration 1235, tui 77, all passed, zero FAILED. `sq check` clean. Not committed.
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-26T12:05:03Z] `python-dev` Elias Python:
  - ST1 worklist: mechanical scan (ast + tokenize, whitespace collapsed) over src/squads, before any edit. Checks: docstring >5 non-blank lines, comment run >3 lines, release version outside _migrations/, ticket id shape, history phrasing. Counts are occurrences per file.
    
    | file | docs>5 | runs>3 | ver | tid | hist |
    |---|---|---|---|---|---|
    | _services/_maintenance.py | 28 | 19 | 0 | 0 | 7 |
    | _cli/_common.py | 33 | 5 | 0 | 0 | 5 |
    | _workflow/_loader.py | 22 | 12 | 0 | 0 | 6 |
    | _workflow/_models.py | 27 | 10 | 0 | 0 | 0 |
    | _services/_validators.py | 23 | 6 | 0 | 0 | 2 |
    | _services/_base.py | 17 | 9 | 0 | 0 | 0 |
    | _specmerge.py | 18 | 3 | 0 | 0 | 2 |
    | _services/_check.py | 16 | 5 | 0 | 0 | 1 |
    | _views.py | 17 | 5 | 0 | 0 | 0 |
    | _index/_store.py | 12 | 5 | 0 | 0 | 2 |
    | _models/_item.py | 13 | 6 | 0 | 0 | 0 |
    | _services/_results.py | 14 | 3 | 1 | 0 | 1 |
    | _cli/_main.py | 10 | 8 | 0 | 0 | 0 |
    | _services/_items.py | 10 | 6 | 0 | 0 | 2 |
    | _cli/_items.py | 6 | 5 | 0 | 0 | 5 |
    | _overrides/_service.py | 13 | 3 | 0 | 0 | 0 |
    | _workflow/_validator_names.py | 3 | 13 | 0 | 0 | 0 |
    | _workflow/_validity.py | 11 | 5 | 0 | 0 | 0 |
    | _cli/_create.py | 8 | 6 | 0 | 0 | 1 |
    | _services/_subentities.py | 9 | 4 | 0 | 0 | 2 |
    | _interactions/_loader.py | 8 | 4 | 0 | 0 | 2 |
    | _rendering/_engine.py | 4 | 5 | 3 | 0 | 2 |
    | _services/_refs.py | 10 | 4 | 0 | 0 | 0 |
    | _cli/__init__.py | 4 | 6 | 0 | 0 | 3 |
    | _cli/_workflow_cmd.py | 10 | 3 | 0 | 0 | 0 |
    | _services/_roster_projection.py | 12 | 0 | 0 | 0 | 1 |
    | _backends/_claude_code/_backend.py | 4 | 7 | 0 | 0 | 0 |
    | _migrations/_v0_14_to_v0_15.py | 5 | 5 | 0 | 0 | 1 |
    | _discussion.py | 8 | 1 | 0 | 0 | 1 |
    | _interactions/_role_guidance.py | 7 | 1 | 0 | 0 | 2 |
    | _services/_import.py | 8 | 2 | 0 | 0 | 0 |
    | _backends/_base.py | 6 | 3 | 0 | 0 | 0 |
    | _interactions/_skills.py | 7 | 1 | 0 | 0 | 1 |
    | _roles/_resolver.py | 5 | 2 | 0 | 0 | 2 |
    | _services/_config_integrity.py | 6 | 3 | 0 | 0 | 0 |
    | _badges.py | 8 | 0 | 0 | 0 | 0 |
    | _cli/_role.py | 4 | 2 | 0 | 0 | 2 |
    | _itemfile.py | 8 | 0 | 0 | 0 | 0 |
    | _services/_retirement.py | 6 | 2 | 0 | 0 | 0 |
    | _services/_roster.py | 6 | 0 | 0 | 0 | 2 |
    | _backends/_agents_md/_backend.py | 6 | 1 | 0 | 0 | 0 |
    | _interactions/_playbook.py | 5 | 0 | 0 | 0 | 2 |
    | _migrations/_v0_11_to_v0_14.py | 4 | 2 | 0 | 0 | 1 |
    | _services/_rename.py | 5 | 2 | 0 | 0 | 0 |
    | _services/_retype.py | 3 | 4 | 0 | 0 | 0 |
    | _services/_service.py | 4 | 3 | 0 | 0 | 0 |
    | _aio.py | 5 | 1 | 0 | 0 | 0 |
    | _index/_reflog.py | 2 | 1 | 3 | 0 | 0 |
    | _models/_markers.py | 3 | 2 | 0 | 0 | 1 |
    | _services/_collab.py | 5 | 0 | 0 | 0 | 1 |
    | _tui/_tree.py | 4 | 1 | 0 | 0 | 1 |
    | _migrations/_v0_1_to_v0_2.py | 3 | 1 | 0 | 0 | 1 |
    | _migrations/_v0_4_to_v0_5.py | 4 | 0 | 0 | 0 | 1 |
    | _roles/_loader.py | 3 | 0 | 0 | 0 | 2 |
    | _sections.py | 4 | 1 | 0 | 0 | 0 |
    | _services/_corpus_files.py | 5 | 0 | 0 | 0 | 0 |
    | _workflow/_lifecycle_order.py | 4 | 1 | 0 | 0 | 0 |
    | _backends/_managed_region.py | 2 | 1 | 0 | 0 | 1 |
    | _cli/_import.py | 4 | 0 | 0 | 0 | 0 |
    | _cli/_migrate.py | 2 | 2 | 0 | 0 | 0 |
    | _context.py | 1 | 2 | 0 | 0 | 1 |
    | _memory/_store.py | 4 | 0 | 0 | 0 | 0 |
    | _migrations/_v0_5_to_v0_7.py | 1 | 3 | 0 | 0 | 0 |
    | _migrations/_v0_8_to_v0_10.py | 2 | 1 | 0 | 0 | 1 |
    | _models/_index.py | 4 | 0 | 0 | 0 | 0 |
    | _services/_views.py | 3 | 1 | 0 | 0 | 0 |
    | _view_tags.py | 3 | 1 | 0 | 0 | 0 |
    | _board/_store.py | 3 | 0 | 0 | 0 | 0 |
    | _cli/_override.py | 3 | 0 | 0 | 0 | 0 |
    | _cli/_skill.py | 1 | 1 | 0 | 0 | 1 |
    | _index/_reconcile.py | 1 | 1 | 0 | 0 | 1 |
    | _interactions/_cheatsheet.py | 2 | 0 | 0 | 0 | 1 |
    | _migrations/_v0_15_to_v0_16.py | 2 | 0 | 0 | 0 | 1 |
    | _models/_schema.py | 1 | 0 | 2 | 0 | 0 |
    | _models/_vocab.py | 3 | 0 | 0 | 0 | 0 |
    | _overrides/_manifest.py | 1 | 1 | 1 | 0 | 0 |
    | _overrides/_stamp.py | 1 | 1 | 1 | 0 | 0 |
    | _actor.py | 2 | 0 | 0 | 0 | 0 |
    | _backends/_claude_code/_frontmatter.py | 1 | 1 | 0 | 0 | 0 |
    | _errors.py | 2 | 0 | 0 | 0 | 0 |
    | _migrations/_meta_compat.py | 1 | 0 | 0 | 0 | 1 |
    | _migrations/_v0_16_to_v0_17.py | 1 | 0 | 0 | 0 | 1 |
    | _migrations/_v0_2_to_v0_3.py | 1 | 0 | 0 | 0 | 1 |
    | _models/_metadata.py | 1 | 0 | 0 | 0 | 1 |
    | _models/_omission.py | 2 | 0 | 0 | 0 | 0 |
    | _roles/_catalog.py | 2 | 0 | 0 | 0 | 0 |
    | _services/_import_model.py | 2 | 0 | 0 | 0 | 0 |
    | _util.py | 0 | 0 | 1 | 0 | 1 |
    | _workflow/__init__.py | 1 | 0 | 0 | 0 | 1 |
    | _board/_model.py | 1 | 0 | 0 | 0 | 0 |
    | _cli/_board.py | 1 | 0 | 0 | 0 | 0 |
    | _cli/_memory.py | 1 | 0 | 0 | 0 | 0 |
    | _cli/_operator.py | 1 | 0 | 0 | 0 | 0 |
    | _interactions/_models.py | 0 | 1 | 0 | 0 | 0 |
    | _memory/_model.py | 1 | 0 | 0 | 0 | 0 |
    | _migrations/_legacy_extra.py | 0 | 0 | 0 | 0 | 1 |
    | _migrations/_outcome.py | 1 | 0 | 0 | 0 | 0 |
    | _migrations/_registry.py | 1 | 0 | 0 | 0 | 0 |
    | _migrations/_v0_10_to_v0_11.py | 1 | 0 | 0 | 0 | 0 |
    | _migrations/_v0_3_to_v0_4.py | 1 | 0 | 0 | 0 | 0 |
    | _migrations/_v0_7_to_v0_8.py | 1 | 0 | 0 | 0 | 0 |
    | _models/_subentity.py | 1 | 0 | 0 | 0 | 0 |
    | _paths.py | 0 | 1 | 0 | 0 | 0 |
    | _roles/_projection.py | 1 | 0 | 0 | 0 | 0 |
    | _roles/_templates.py | 1 | 0 | 0 | 0 | 0 |
    | _services/_board.py | 1 | 0 | 0 | 0 | 0 |
    | _services/_corpus_fit.py | 1 | 0 | 0 | 0 | 0 |
    | _services/_duplicate_ids.py | 0 | 0 | 0 | 0 | 1 |
    | _services/_memory.py | 1 | 0 | 0 | 0 | 0 |
    | _specload.py | 1 | 0 | 0 | 0 | 0 |
    | _transform.py | 1 | 0 | 0 | 0 | 0 |
    | _tui/_browse.py | 1 | 0 | 0 | 0 | 0 |
    | _tui/_reader.py | 1 | 0 | 0 | 0 | 0 |
    TOTAL files 113 {'long_doc': 595, 'long_run': 227, 'hist': 80, 'ver': 12}
- [2026-10-26T13:43:12Z] `reviewer` Paul Reviewer:
  - ST3 reviewed in REV-1166: six findings (one medium), left InReview.
- [2026-10-26T15:01:28Z] `manager` Catherine Manager:
  - ST1–ST5 delivered (62518566 through 02a68345); REV-1164, REV-1166 and REV-1169 Approved; prose only, docstring-stripped AST unchanged at every increment. Ceiling guard: not added, per dev and reviewer recommendation; the operator decides on a stale-name guard instead. Accepted under the operator's delegation.
- [2026-10-26T15:37:09Z] `op-pierre` Pierre Chat:
  - No docstring-length ceiling guard and no stale-name guard.
<!-- sq:discussion:end -->
