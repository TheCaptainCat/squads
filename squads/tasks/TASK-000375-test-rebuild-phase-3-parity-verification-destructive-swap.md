---
id: TASK-375
sequence_id: 375
type: task
title: 'Test rebuild Phase 3: parity verification + destructive swap'
status: Ready
parent: FEAT-231
author: tech-lead
subentities:
- local_id: ST1
  title: Verify ledger parity before deleting the old suite
  status: Todo
  story: US4
created_at: '2026-07-10T04:48:20Z'
updated_at: '2026-07-10T13:17:15Z'
---
<!-- sq:body -->
## Phase 3 — Parity verification + destructive swap

Fourth phase of the FEAT-231 rebuild. **This is the one task that deletes the safety net.** It
verifies the new four-pillar battery has full coverage parity against the Phase-0 ledger, runs the
old and new suites together as the final cross-check, and ONLY THEN removes the old flat
`tests/test_*.py` files.

### REQUIRES OPERATOR SIGN-OFF
This task **requires operator sign-off on the Phase-0 coverage ledger before execution — do not
dispatch without it.** The deletion is irreversible relative to the working tree's safety net; the
operator must confirm the ledger is complete and every row is accounted for before the old suite is
torn down.

### Scope
- For every row in the Phase-0 coverage ledger, confirm a **green** test exists in the new suite at
  its planned home. No row may be unmapped or red. Produce a parity report (ledger row → new test
  id → pass).
- Run old + new suites **together** one last time (full sweep incl. `-m slow`) and confirm green.
- Only after parity is confirmed and the operator has signed off on the ledger: delete the old flat
  `tests/test_*.py` files (the ~80 files) and any now-orphaned helpers (`tests/_helpers.py` if fully
  superseded). Keep `tests/fixtures/corpus/*` (frozen), `tests/goldens/*` still in use, and the new
  layered tree.
- Confirm no dev-archaeology names or ticket-ID filenames remain anywhere under `tests/`.

### Dependencies
Depends on Phase 2 (the new battery must be complete + green) AND on operator sign-off on the
Phase-0 ledger. Blocks Phase 4. This is the destructive step — sequence strictly after Phase 2; do
not run concurrently with any authoring.

### Acceptance
- Parity report shows every ledger row mapped to a green new-suite test.
- Operator has signed off on the coverage ledger (record the sign-off as a comment on FEAT-231).
- Old flat suite deleted; `uv run pytest` (default, `-m 'not slow'`) green and < 30s; `-m slow`
  green; `uv run sq check` clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 375 add-subtask "<title>"`; track with `sq task 375 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Verify ledger parity before deleting the old suite | US4 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Verify ledger parity before deleting the old suite

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US4 — Coverage ledger preserves previously-caught bugs
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-10T13:17:15Z] Mara Tester:
  - FEAT-231 Phase 3 deletion manifest (non-destructive: nothing deleted/modified). VERDICT: BLOCK. 78/80 old flat test_*.py files are SAFE TO DELETE; test_scale.py is KEEP; test_cli.py is BLOCK (real unhomed coverage, see below). Do not run the destructive swap until test_cli.py's gaps are resolved.
  - SUPERSEDED (delete, 78 files): every old test_*.py except test_scale.py and test_cli.py. Cross-referenced against every COVERAGE_LEDGER.md row (all 159 cited) plus a docstring/content spot-check on the new side — each old file's ledger rows map cleanly onto tests/{unit,service,cli,integration}/ files by name+content (e.g. test_retype.py->unit/test_identity.py+service/test_retype.py; test_index.py->unit/test_index_allocation.py+unit/test_id_padding.py+unit/test_backrefs.py+service/test_index_concurrency.py+service/test_index_locking.py; test_graph.py->service/test_graph_traversal.py+unit/test_graph_export_rendering.py+cli/test_graph_command_cli.py; test_show_render.py(46 tests)->cli/test_show_command_renders_body_and_subentities.py(18, consolidated); test_role_resolver.py(20)->unit/test_role_override_field_merge.py+service/test_role_and_dev_override_pickup_at_instantiation.py+cli/test_role_activate_with_override_cli.py(19); full group-by-group mapping in my scratch notes, available on request).
  - KEEP (3): tests/test_scale.py (the 5 @slow scale-bound tests, row 111, no other O(n) test exists outside it). tests/conftest.py (root autouse leak-guards + project/svc/runner/invoke/frozen_time fixtures — confirmed all 4 new layer conftest.py files are empty stubs that inherit these via normal pytest resolution). tests/fixtures/corpus/* (frozen per-schema squads v0.1-v0.8, referenced ONLY by tests/integration/test_migration_corpus.py, confirmed by grep).
  - BLOCK: tests/test_cli.py. Tell: it was never cited as a 'Currently tested in' source by ANY of the 159 ledger rows (only appears in the Deliverable-2 duration table) — that omission was real, not an oversight I should wave through. On inspection it holds distinct, load-bearing behavior with zero new-suite home (verified by keyword grep across all 4 new dirs, zero hits each).
  - BLOCK gap 1 (biggest): 'sq renumber' — the ENTIRE command (shift an ID block --from/--onto/--by, rewrite refs/parents, rename files, bump counter, reject --onto+--by together, refuse unsafe --by with zero mutation, listed in root --help) is not in the ledger at all (row 17's 'renumber-collision' is repair's internal collision handling, a different mechanism) and has zero tests anywhere in the new suite. 4 old tests: test_renumber_cli_shifts_block_and_updates_refs, test_renumber_cli_rejects_both_onto_and_by, test_renumber_cli_unsafe_by_refuses_with_no_mutation, test_renumber_listed_in_root_help_and_shows_onto_recipe.
  - BLOCK gap 2: schema-mismatch hard-stop gate (CLAUDE.md invariant: root callback hard-stops, points at 'sq migrate up') — test_schema_gate_blocks_until_migrate + test_exit_code_1_schema_mismatch have no new home; every new migration test proves migrate-up succeeds, none proves an ordinary command refuses first.
  - BLOCK gap 3: the TASK-83 exit-code contract itself (0/1/2/3 meanings) — 9 tests, never a ledger row, no new home. Individual codes are incidentally hit elsewhere but the contract ('these are exactly the 4 codes, this triggers each') is untested as a unit.
  - BLOCK gap 4: 'sq migrate repad'/'rename-*' CLI entry-point wiring. integration/test_repad.py calls svc.repad() directly, never through invoke/CliRunner — the command's own message text and exit-1-on-refuse-to-lower path are untested. (rename-type/rename-status ARE CLI-driven in integration/test_rename.py — confirmed, that half is fine.)
  - BLOCK gap 5-9: 'sq migrate help'/'chlog' (no home); 'sq docs' CLI dispatch — list/print/--rich/unknown-doc-exit-1 (unit/test_bundled_docs_registry.py only proves the registry, never invokes the command); _hoist_global_options, the --at/--dir position-independent shim, unit AND end-to-end via real subprocess (zero hits); shell completion bash/zsh --show-completion (zero hits); the FEAT-250/TASK-253 per-invocation spec-context-binding-order tests (Pierre's threaded-context contract) — test_spec_bound_before_parse_type_runs and siblings, zero hits.
  - BLOCK gap 10 (minor): test_create_cli_exits_1_when_index_full, test_repair_cli_holds_padding_after_file_loss, test_ref_add_help_references_workflow, test_dir_override, test_workflow_survives_cp1252_console (Windows-only, always-skipped here but real). Everything else in test_cli.py IS genuinely superseded — this is not a wholesale miss, just these ~20 tests across gaps 1-10.
  - Recommendation: port gaps 1-10 into the new tree (new cli/test_renumber_cli.py, a schema-mismatch-gate test, cli/test_docs_cli.py, unit/test_hoist_global_options.py, fold chlog/completion/spec-binding-order into existing files) then re-run this manifest. Don't delete the other 78 as a partial step either — Phase 3's own scope is 'old flat suite deleted' as one unit.
  - Unused-golden list (once the 78 are gone): show_feat.json + show_task.json removable (superseded by the generic-show/typed-show CONVERGE-on-one-golden design in cli/test_json_output_shape.py — a deliberate consolidation, not a loss). The 7 skill_body_sq-*.txt goldens removable (integration/test_item_skill_body_generation.py swapped byte-goldens for structural assertions — flagging for visibility per ledger row 152's target already saying 'integration' not 'golden', not blocking). tree_task_json.json removable (identical key-shape to tree.json/tree_feat.json already kept; the ancestor-preservation behavior it also checked is proven at service/test_tree_view_hierarchy_filtering.py). All other 30 goldens under tests/goldens/ are actively referenced by a surviving new file — confirmed one-by-one by grep — keep all.
  - Helper disposition: tests/_helpers.py — KEEP, still imported by 9 new-suite files (unit/test_status_machine_transitions.py, unit/test_backrefs.py, unit/test_workflow_reserved_vocab.py, unit/test_status_badge_glyphs.py, unit/test_type_alias_table.py, unit/test_custom_type_path_resolution.py, unit/test_item_and_subentity_templates_render_structurally.py, cli/test_type_aliases_cli.py, cli/test_status_display_has_no_badge.py). Not removable. No other shared old helper module exists under tests/.
  - Standalone confirm (no --run-slow): 'uv run pytest tests/unit tests/service tests/cli tests/integration -q', repeated 3x incl. --color=no/python -m pytest variants for consistency — exit 0 every time, 0 failure markers, 0 error markers, 2 skips, dot-count stable at 1073 pass outcomes across all 3 runs. Note: this environment's pytest wrapper truncates the standard 'N passed in Ys' summary line even when redirected to a file (confirmed harness quirk, not a code issue) so I'm reporting the counted-outcome figure: ~1073 passed / 0 failed / 2 skipped / exit 0, new dirs only, no old flat suite in scope. Consistent with (does not contradict) the coordinator's parity proof (a) at 1072, which additionally included test_scale.py.
<!-- sq:discussion:end -->
