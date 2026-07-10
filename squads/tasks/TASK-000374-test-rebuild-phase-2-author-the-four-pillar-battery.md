---
id: TASK-374
sequence_id: 374
type: task
title: 'Test rebuild Phase 2: author the four-pillar battery'
status: InProgress
parent: FEAT-231
author: tech-lead
subentities:
- local_id: ST1
  title: Behavior-named taxonomy across the four pillars, no dev-archaeology
  status: Todo
  story: US1
- local_id: ST2
  title: 'Fast by default: mark scale slow, flip addopts to -m not slow, under 30s'
  status: Todo
  story: US2
- local_id: ST3
  title: Each invariant asserted once at the lowest meaningful layer
  status: Todo
  story: US3
created_at: '2026-07-10T04:48:20Z'
updated_at: '2026-07-10T11:14:04Z'
---
<!-- sq:body -->
## Phase 2 — Author the four-pillar battery

Third phase of the FEAT-231 rebuild, and the bulk of the authoring. Write the new suite against the
**shipped, final** generic spec engine (EPIC-280 + EPIC-335 landed — no ItemType/Status enums,
byte-identical-default behaviour). **The old flat suite stays in place and green throughout; this
phase only adds.** Structure the battery around the four pillars from the manager's strategy comment,
not per-type re-testing:

### The four pillars (parallelizable work-streams — mostly separate subdirs)
1. **Generic-engine-once** (`tests/unit/`, some `tests/service/`) — test the mechanism a single
   time, keyed on a spec: transitions / terminal / parent-allowed / capability flags / badge
   collections derived from a spec, NOT re-tested per built-in type. This is where the suite shrinks.
2. **Spec-as-artifact + goldens** (`tests/unit/` + `tests/goldens/`) — the bundled spec is now a
   tested artifact: assert its shape and correct flag/badge values; disciplined goldens for
   generated artifacts (CLAUDE.md/AGENTS.md sections, skill pointer bodies, rendered templates) with
   all inputs pinned (roster, flags, frozen clock) and one golden per distinct rendering path.
3. **Behavioural spine** (`tests/cli/`, `tests/integration/`) — a SMALL end-to-end set proving the
   configured types behave: `sq check`, retype, skill generation, create/transition/comment happy
   paths. Absorb the thin acceptance tests EPIC-280/335 already added (e.g. custom-type, custom
   badge-axis, load-boundary-vocab, spine-characterization) as characterization seeds — migrate,
   rename to behavior-named form, dedup against pillar 1.
4. **Failure / edge surface (first-class — the part the old enum suite structurally lacked)** —
   budget for this explicitly: invalid/unknown vocab at the load boundary (the FEAT-208 F1 miss:
   corrupt frontmatter silently indexed then crashes `sq check`), malformed spec, reserved-vocab
   violations (only role/skill/operator reserved; the 7 work types fully overridable), override-merge
   conflicts, custom-type / custom-status scenarios.

### Cross-cutting requirements (realize the user stories)
- **US1 — behavior-named:** every file/class/function name completes "This system guarantees
  that…". No `layer_a/b`, `golden_lock`, `FEAT-`/`TASK-`/`ADR-` refs, no ticket-ID filenames.
- **US3 — each invariant once, at the lowest meaningful layer:** use the Phase-0 duplicate-invariant
  clusters to collapse redundant multi-layer assertions. CLI tests prove clean exit + parseable
  output, not model-field well-formedness (that's a unit test).
- **US2 — fast by default:** mark scale/stress tests `@pytest.mark.slow` and flip
  `pyproject.toml` `addopts` to include `-m 'not slow'` (keep `-n auto`). The deferred wall-clock
  win folds in HERE. Target: default run < 30s; `uv run pytest -m slow` runs the scale paths.
- Determinism per Principle 7: `frozen_time`, tmp_path isolation, env stripped, order-independent.

### Dependencies
Depends on Phase 1 (scaffolding + conftest). Blocks Phase 3. The four pillars are internally
parallelizable (mostly distinct subdirs), but if authored by concurrent agents they share
`conftest.py`/`CONVENTIONS.md`/`tests/goldens/` — sequence or worktree-isolate those touch points to
avoid collisions. Do NOT delete any old test here.

### Acceptance
- All four pillars authored; every Phase-0 ledger row has a corresponding new-suite test.
- Default `uv run pytest` (with `-m 'not slow'`) green and under 30s; `-m slow` green.
- Zero dev-archaeology names in the new tree; `uv run sq check` clean; old suite still green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 374 add-subtask "<title>"`; track with `sq task 374 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Behavior-named taxonomy across the four pillars, no dev-archaeology | US1 |
| ST2 | Todo |  | Fast by default: mark scale slow, flip addopts to -m not slow, under 30s | US2 |
| ST3 | Todo |  | Each invariant asserted once at the lowest meaningful layer | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Behavior-named taxonomy across the four pillars, no dev-archaeology

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — Behavior-named tests, not development archaeology
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Fast by default: mark scale slow, flip addopts to -m not slow, under 30s

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US2 — Default test run under 30 seconds
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Each invariant asserted once at the lowest meaningful layer

<!-- sq:subtask:ST3:head -->
**Status:** ⚪ Todo
**Implements:** US3 — Each invariant asserted once, at the right layer
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-10T07:50:08Z] Catherine Manager:
  - Note: the fast-default slow-test split (ST2 in this task's scope) was implemented standalone at op-pierre's request — --run-slow opt-in in tests/conftest.py, slow tests skipped by default. Phase 2 does NOT need to redo the addopts/marker flip; just don't regress the ~30s default while re-authoring.
- [2026-07-10T08:14:45Z] Catherine Manager:
  - Phase 2 execution: decomposing the authoring into 5 contract-group chunks (core-integrity grps1-4; spec-engine grps5-7; backend/agent grps8-10; mechanics grps11-17; review-added grps19-24), each authored into the right layers per CONVENTIONS.md alongside the old suite, gated+reviewed+committed sequentially. Group 18 (scale) stays as-is (test_scale.py, already slow-marked). Tracking chunk progress here rather than spawning per-chunk sq tasks.
- [2026-07-10T08:37:15Z] Elias Python:
  - Chunk 1/5 (core integrity, ledger rows 1-33) done: authored unit/service/integration tests for groups 1-4 (identity/retype/rename, index/storage integrity, load-boundary vocab, migrations+corpus). Full suite green (old+new); fast gates clean. See close-out comment for file map + dedup/gap notes.
- [2026-07-10T08:38:28Z] Elias Python:
  - Chunk 1/5 close-out (ledger rows 1-33, groups 1-4). New files (all under tests/unit|service|integration/, old flat suite untouched):
  - unit/: test_identity.py (rows 1-id-math,2,3 + gap#1 adversarial ==-not-is test), test_migration_registry.py (row 8 registry half), test_index_allocation.py (9,11,12,16), test_id_padding.py (15 unit half), test_backrefs.py (14), test_bug_severity_migration.py (28), test_legacy_meta_compat.py (30), test_legacy_severity_backfill.py (25 unit half)
  - service/: test_retype.py (1 file/index half, 4, 5), test_index_concurrency.py (10), test_index_locking.py (13), test_remove.py (19 minus crash-ordering)
  - integration/: test_rename.py (6,7,8-live-squad half), test_repair_integrity.py (17,18-consolidated), test_repad.py (15 integration half), test_remove_crash_safety.py (19 unlink-before-commit), test_load_boundary_vocab.py (20-24,25 integration half), test_migrations.py (26,33), test_migration_corpus.py (31, corpus untouched), test_skill_migration.py (27, 32-folded), test_unpadded_id_migration.py (29), test_init_then_migrate.py (gap#2)
  - Gap#1: unit/test_identity.py::test_status_carry_relies_on_workflow_value_equality_not_object_identity -- two independently load_workflow_spec()'d specs, proves workflow_for() builds distinct-but-== objects, then drives _carry_or_reset_status to show carry fires on value equality.
  - Gap#2: integration/test_init_then_migrate.py -- init then run_pending_migrations()/CLI migrate up, then scans every .claude pointer's @-reference for a dangling target, both service-call and real-CLI variants.
  - Dedup: backrefs width-tolerance proven once at unit (not re-asserted post-repad as a second test); repair-idempotency consolidated to one parametrized integration test (fresh/skill-seeded/repadded); schema-not-bumped split cleanly into a pure registry fact (unit) vs a live-squad disk fact (integration), not duplicated.
  - Deviation: row 32's CLI target folded into integration/test_skill_migration.py (this chunk's file scope was unit|service|integration only, no tests/cli/ yet).
  - Deferred, flagged not blocking: test_skill_migration.py's ref/show CRUD tests (not migration-shaped, belong to a later agent-artifact chunk) and its lexical-ordering-parity test were not ported; scaffold placeholder files left in place (shared across all 5 chunks).
  - Verification: new tests 125 passed (0 failed) via tests/unit tests/service tests/integration; full default suite (old+new) green, exit 0; test_squad_ref_hygiene.py green. Fast gates repo-wide: pyright 0 errors, ruff check clean, ruff format clean.
- [2026-07-10T08:45:44Z] Paul Reviewer:
  - Reviewed FEAT-231 Phase 2 chunk 1 (ledger rows 1-33, groups 1-4) — the quality gate for the rebuild. VERDICT: APPROVE. The new tests are genuinely non-vacuous, dedup preserved every distinct case, and all rows 1-33 are homed at the right layer. Both trees pass together (full run incl --run-slow: exit 0, 0 failures). One LOW naming fix below.
  - NON-VACUOUS & catches regressions: YES, verified by deep sampling across all 4 groups. The is-vs-== adversarial (unit/test_identity.py::test_status_carry_relies_on_workflow_value_equality_not_object_identity) genuinely drives _carry_or_reset_status(feature->epic), whose two internal workflow_for() calls yield distinct-but-equal Workflow objects — it asserts reset is False, so it WOULD fail if == regressed to is (feature and epic are different keys -> never the same object under is -> carry never fires). It also independently proves the ==-but-not-is property (two specs, wf==wf and wf is not wf). The load-boundary F1 (integration/test_load_boundary_vocab.py) corrupts the REAL on-disk index JSON / .md frontmatter then drives the real load()/repair() path — rows 20-25 all present incl. the message-ordering assertion (cause before sq-repair). Corpus (integration/test_migration_corpus.py) copytrees each frozen fixture and drives it via BOTH service and CLI to SCHEMA_VERSION + sq check clean; the 7 parametrized cases match the 7 fixtures on disk exactly (and it even ADDS v0_4 beyond the ledger list). Index allocation/atomic-RMW/corruption/index-full and the remove unlink-before-commit crash-ordering (integration/test_remove_crash_safety.py) all exercise real behaviour, not mocks.
  - DEDUP preserved all distinct cases: YES. Backrefs (row 14) keeps all 3 cases in unit/test_backrefs.py (inversion-not-persisted, width-tolerant, no-cross-type-false-positive) PLUS the post-repad re-verification in integration/test_repad.py. Repair-idempotency (row 18) is parametrized over fresh/seeded-skills/repad in integration/test_repair_integrity.py, with the 4th case (repair-after-skill-migration) kept in integration/test_skill_migration.py::test_repair_after_migration_rebuilds_the_index_cleanly, and the custom-type-repair case correctly deferred to the group-7 chunk (not lost). Rename-no-schema-bump (row 8) is split: unit/test_migration_registry.py (no rename entry / nothing past current schema) + integration/test_rename.py (rename ops never bump the on-disk version). Nothing silently dropped.
  - ROWS 1-33 homed at the right layer, behavior-named. Two deviations, both acceptable: (a) row 32 (ledger target cli) is folded into integration/test_skill_migration.py (test_sq_migrate_up_cli_stamps_skills... + ..._idempotent_from_the_cli) because tests/cli/ is not authored yet — the behaviour IS covered and green; this is a placement deferral, not a coverage gap, reconcile into tests/cli/ (or amend the ledger target) when the CLI chunk lands. (b) skill-CRUD/show/ordering are correctly out of this chunk (groups 8-9). No ticket IDs in filenames or test names; the FEAT-/BUG-/TASK- grep hits are all synthetic 6-digit item-IDs used as test DATA (refs/frontmatter), which is legitimate and matches the old suite.
  - F1 (LOW, the only fix): tests/unit/test_legacy_severity_backfill.py:1 docstring says "A pre-ADR-323 bug..." — a ticket-ID reference in a docstring, which CONVENTIONS.md section 3 bans ("Any ADR- reference ... docstring"). Reword to the behaviour, e.g. "a pre-badge-collections / legacy-shaped bug whose severity lived under extra". Sole naming-ban breach in the 22 new files; everything else is clean behavior-naming. Not a coverage issue — safe to fix in place. Recommendation: fix F1 and this chunk is a clean parity-gate input for Phase 3.
- [2026-07-10T08:47:26Z] Elias Python:
  - Naming-ban fix applied per review: test_legacy_severity_backfill.py docstring reworded from 'A pre-ADR-323 bug...' to 'A pre-badge-collections / legacy-shaped bug...' (no ticket ID). Verified: test_squad_ref_hygiene.py green, ruff check/format-check clean, the file's own 2 tests pass. Doc-only, no full suite run, no commit.
- [2026-07-10T08:48:25Z] Catherine Manager:
  - Chunk 1/5 (core-integrity, ledger rows 1-33) reviewer-APPROVED: non-vacuous coverage confirmed by deep sampling (is-vs-== would fail if == regressed to is; F1 load-boundary drives the real corrupt-index path; corpus round-trips real), dedup preserved every distinct case, all rows homed. F1 (ADR-323 in a docstring) fixed. Full suite green (1916 passed, --run-slow green). Landing chunk 1.
- [2026-07-10T09:17:20Z] Elias Python:
  - Chunk 2/5 (spec engine, ledger rows 34-59, groups 5-7) done: authored unit/service/cli/integration tests. Full suite green (old+new, 2087 collected, 0 failures); fast gates (pyright/ruff check/ruff format) clean.
- [2026-07-10T09:17:39Z] Elias Python:
  - Chunk 2/5 close-out (ledger rows 34-59, groups 5-7). New files, all under tests/unit|service|cli|integration/:
  - unit/: test_workflow_reserved_vocab.py (34-36), test_workflow_override_merge.py (37 + gap#4), test_workflow_lint_merge_errors.py (41 unit half), test_workflow_spec_artifact.py (39,40,F6-alias-defense), test_badge_collections.py (44-50), test_custom_status_badge_resolution.py (51), test_status_badge_glyphs.py (52), test_custom_type_path_resolution.py (54), test_custom_skill_generation.py (55 pure-fn half)
  - cli/: test_workflow_lint_cli.py (41 cli half), test_generic_badge_axis_cli.py (49 cli half + priority-is-bundled-instance dedup), test_custom_type_end_to_end.py (53,58 + F5/F6 edge cases), test_custom_status_vocab_flow.py (56), test_custom_subentity_kind_cli.py (57 cli half)
  - service/: test_custom_type_lifecycle.py (53/54 retype+refs+sync+repair for a custom type), test_custom_subentity_kind.py (57 service half)
  - integration/: test_workflow_override_service_integration.py (38,42 + real end-to-end AC5 fail-closed through open_service, not just the lower-level cross-check), test_custom_type_skill_generation.py (55 service/integration half)
  - Every row 34-59 is homed at its target layer; none deferred. Row 43 (.squads.toml legacy backend key) was already covered by chunk-1's test_migration_corpus.py, confirmed not re-added.
  - Gap #4 (override-merge conflict): the duplicate-field-code guard lives in WorkflowSpec's own model validator, which runs on the merged payload regardless of source -- so it already fails closed for a genuinely conflicting override-merge. Added test_two_fields_declared_with_the_same_code_in_one_override_stanza_fails_closed to prove that path explicitly via real on-disk TOML (not just direct model construction, which was the only proof that existed before).
  - Dedups: reserved prefix/folder shadow (row36) now asserted once via direct construction (unit/test_workflow_reserved_vocab.py) plus once via the on-disk loader path with a different collision instance (unit/test_workflow_override_merge.py) -- not the same case twice. Priority-views vs generic axis: ported only test_bundled_axis_still_uses_the_dedicated_flags from the old custom-badge-axis file (kept as test_priority_is_the_bundled_instance_of_the_same_generic_axis); did not port test_priority_views.py's full pre-genericity cluster (that file's remaining rows are group 13, out of this chunk's range).
  - Repair-idempotency-after-custom-type-setup could not be folded into chunk-1's existing parametrized repair test (that parametrize shares one svc fixture; a custom type needs its own overridden-spec Service) -- kept as its own service-level test with a note pointing back at the consolidated one.
  - Removed the four Phase-1 scaffold placeholder tests (tests/{unit,service,cli,integration}/test_scaffold.py) per their own docstrings, now that real tests exist in all four layers.
  - Real finding: none -- every ledger row's behaviour held (including AC5 fail-closed through open_service end-to-end, which the old suite had only exercised as a documented gap via a mock spec, never a real live-index+open_service round trip).
  - Counts: 169 new tests, all green. Full suite (old+new): 2087 collected, 0 failures. Fast gates green: pyright 0 errors, ruff check clean, ruff format clean. tests/test_squad_ref_hygiene.py green.
- [2026-07-10T09:24:30Z] Paul Reviewer:
  - Reviewed FEAT-231 Phase 2 chunk 2 (ledger rows 34-59, groups 5-7). VERDICT: APPROVE. Non-vacuous and regression-catching, gap #4 genuinely proven, dedup preserved every distinct case, all rows 34-59 homed at the right layer, both trees green (full run incl --run-slow: exit 0, 0 failures). No findings — clean chunk (chunk 1 F1 was the one nit; none here).
  - NON-VACUOUS & regression-catching: YES, sampled across all 3 groups. Badge/collection engine (unit/test_badge_collections.py) drives a real custom "level" collection reused by two relabeled fields (impact/urgency) and the full fail-closed cluster (dup code, reserved-key shadowing incl. sub-entity, undeclared collection, non-badge default at field+collection level, unordered rejected BOTH directly and through the override loader) — would fail if the generic resolution/validation broke. The CLI half (cli/test_generic_badge_axis_cli.py) exercises --set impact=/urgency= on a custom axis, invalid-code rejection, --badge/--min-badge ordered threshold, --sort, and tree filter/sort — the flagship proof the axis is genuinely spec-derived, not bundled priority/severity. Custom type/status/sub-entity-kind e2e (cli/test_custom_type_end_to_end, cli/test_custom_status_vocab_flow, service/test_custom_subentity_kind) all declare vocab via real .overrides/workflow.toml and drive it through create/list/show/retype/status-views/blocked — non-vacuous.
  - AC5 fail-closed (row 38) is a GENUINE end-to-end proof: integration/test_workflow_override_service_integration.py::test_open_service_fails_closed_end_to_end_when_a_new_override_orphans_a_live_status writes a real override that drops a live status and drives open_service(), asserting it hard-stops with a message naming the offending item + dropped status + pointing at sq workflow lint. The _MockSpec objects are used ONLY for the isolated lower-level validate_against_index unit checks (legitimate function isolation); the real spec + open_service path is separately and genuinely proven. Also confirms lint still runs after open_service would hard-stop (not self-blocked).
  - Gap #4 GENUINELY proven: unit/test_workflow_override_merge.py::test_two_fields_declared_with_the_same_code_in_one_override_stanza_fails_closed writes a real .overrides TOML with an incident type carrying two same-coded (impact) fields with conflicting collections/defaults, loads via load_workflow_spec(squad_dir=...) — the actual override-MERGE path — and asserts SquadsError "duplicate field code". "Already fails closed" is correct: WorkflowSpec s own validator runs on the merged payload. The dev correctly identified that the only genuinely-CONFLICTING field override is the duplicate-code case (relabeling one collection under distinct codes is cooperative, proven separately at row 49), and it is guarded.
  - DEDUP preserved all cases: reserved prefix/folder collision is a legit wiring-point split — direct-construction in unit/test_workflow_reserved_vocab.py (test_custom_type_cannot_shadow_a_reserved_prefix/_folder) AND the loader path in test_workflow_override_merge.py (with a docstring cross-ref), two distinct instances, nothing dropped. Priority-views pre-genericity cluster correctly LEFT for group 13/chunk 4 — only the generic-axis mechanism is ported here. Row 43 (backend-key rewrite) correctly not duplicated (lives in chunk 1 corpus). All rows homed at target layer, behavior-named; NO ticket IDs / layer_a/golden_lock in any of the 18 files (grep clean). The 4 Phase-1 test_scaffold.py placeholders are correctly deleted now that each layer has real tests. Parent-cycle (39) -> test_workflow_spec_artifact.py; glyph pin (52) -> test_status_badge_glyphs.py; custom status badges (51) -> test_custom_status_badge_resolution.py. Clean parity-gate input for Phase 3.
- [2026-07-10T09:25:15Z] Catherine Manager:
  - Chunk 2/5 (spec-engine, ledger rows 34-59) reviewer-APPROVED, no findings: generic badge axis proven end-to-end on a real custom collection, custom type/status/sub-entity-kind flows via real .overrides, genuine AC5 fail-closed through open_service (old suite only mocked it), gap #4 (conflicting override-merge) closed via real TOML. Dedup preserved all cases; 4 scaffold placeholders removed. Full suite green (2081, --run-slow green). Landing chunk 2.
- [2026-07-10T09:55:39Z] Elias Python:
  - Chunk 3/5 (backend & agent surface, ledger rows 60-81, groups 8-10) done: authored unit/service/cli/integration tests for backend lifecycle (ABC conformance parametrized over both backends, claude-code/agents_md specifics, multi-active-backend runtime), agent-facing artifacts (has_dev gate, can_spawn, role/playbook catalogs as goldens, lane derivation, lifecycle linearization, agent naming precedence), and CLI output hygiene (FORCE_COLOR/ANSI, JSON golden shapes, status-plain-string, COLUMNS pin, aliases, slug validation). Also homed chunk 1's deferred skill-CRUD/skill-show/lexical-ordering tests here. Full suite green (old+new); fast gates clean. See close-out comment for file map, dedup notes, and the golden-dedup fix applied mid-chunk.
- [2026-07-10T09:55:57Z] Elias Python:
  - Chunk 3/5 close-out (ledger rows 60-81, groups 8-10). New files, all under tests/{unit,service,cli,integration}/, old flat suite untouched:
  - unit/: test_active_backends_config.py (row 67 model half), test_item_skill_dev_gate.py (63,64), test_can_spawn.py (70 unit half), test_role_catalog_artifact.py (71), test_playbook_spec_artifact.py (74), test_bundled_toml_packaging.py (71/74 ships-in-wheel, dedup cluster 5, playbook+roles TOML only), test_create_lane_derivation.py (72), test_linearize_lifecycle.py (73), test_init_names_config.py (69 model half), test_type_alias_table.py (79 unit half)
  - service/: test_agent_naming_precedence.py (69 service half), test_create_lane_advisory.py (72's advisory behaviour), test_slug_resolution.py (81 validator, one test)
  - cli/: test_init_naming_flags.py (69 cli half), test_create_lane_advisory_cli.py (72's cli surfaces), test_json_output_is_ansi_free.py (75), test_json_output_shape.py (76, 24 goldens), test_status_display_has_no_badge.py (77), test_help_text_width_is_pinned.py (78), test_type_aliases_cli.py (79 cli half + 80), test_help_text_follows_spec_vocabulary.py (cited under 78/80 by the ledger; content is really spec-vocab-derivation, flagged for a possible future re-file), test_slug_validation_surfaces.py (81, one thin test per surface), test_skill_item_surface.py (chunk-1 skill-CRUD deferral)
  - integration/: test_backend_lifecycle_contract.py (60,61,62,68), test_claude_code_backend.py (65), test_agents_md_backend.py (66), test_multi_active_backends.py (67 runtime half), test_can_spawn_surfaces.py (70 integration half), test_bundled_skill_ordering_parity.py (chunk-1 lexical-ordering deferral)
  - Every row 60-81 homed; row 32 (sq migrate up stamps skills) reconciled -- it's already correctly at chunk 1's integration home (migration-shaped), not duplicated here. has_dev roster hazard: every has_dev test builds its own explicit roster dict (with/without a *-dev slug), never trusts init defaults. FEAT-336 regressions pinned: the byte-identical-to-golden test reuses the existing 7 skill_body_sq-<type>.txt goldens (which already encode the fixed trailer/lifecycle logic), so a regression back to the old bug reappears immediately.
  - Goldens: added 2 new JSON goldens (role_catalog_spec.json, playbook_spec.json -- P2 spec-as-artifact snapshots, distinct render path from the existing rendered-output txt goldens). Reused all pre-existing JSON/txt goldens read-only, no duplicates created. Mid-chunk, caught and fixed a golden-dedup issue: feature_show.json/show_feat.json and task_show.json/task_show.json were byte-identical pairs (generic sq show vs typed sq <type> show); collapsed test_json_output_shape.py to one golden per render with a dedicated convergence test asserting both entry points equal it, per CONVENTIONS.md 'one golden per distinct render path'. Audited the rest of the 23 JSON goldens for other such pairs -- none found. For the 7 skill_body_sq-<type>.txt goldens, kept per-type full snapshots as-is (no new files) rather than collapsing, since they demonstrably caught the FEAT-336 trailer bug and I'm not adding new ones, just reusing them read-only.
  - Verification: 304 new tests, all passed via the file list above. Full default suite (old+new) green, exit 0 (both before and after the golden-dedup fix). tests/test_squad_ref_hygiene.py green (5 tests). Fast gates repo-wide: pyright 0 errors, ruff check clean, ruff format clean.
- [2026-07-10T10:03:50Z] Paul Reviewer:
  - Reviewed FEAT-231 Phase 2 chunk 3 (ledger rows 60-81, groups 8-10 + the chunk-1-deferred skill-CRUD). VERDICT: APPROVE. Non-vacuous & regression-catching, golden dedup correct with no coverage lost, has_dev both states pinned, the in-scope FEAT-336 regressions genuinely pinned, every row 60-81 homed at target layer. Both trees green (full run incl --run-slow: exit 0, 0 failures). No blocking findings; two LOW notes.
  - NON-VACUOUS: FORCE_COLOR/ANSI-free JSON (cli/test_json_output_is_ansi_free.py) re-injects FORCE_COLOR=3 after setup and asserts no \x1b + clean json.loads — deliberately defeats the conftest strip to exercise the real code path (row 75, per Principle 5). Backend conformance (integration/test_backend_lifecycle_contract.py) drives the REAL backend: write_managed byte-identical on 2nd run, marker-at-most-once, roster/operator names reach the output, role pointer references the real definition. claude-code specifics pin the "regenerated by sq sync" warning in both the skill pointer and CLAUDE.md (invariant #7) + valid-YAML frontmatter. Multi-backend (row 67) and can_spawn (row 70, unit round-trip + integration pointer-denies-the-agent-tool + JSON) both genuine.
  - has_dev BOTH states pinned (row 63): unit/test_item_skill_dev_gate.py pins an EXPLICIT _ROSTER_WITH_DEV (8 bundled + python-dev) and _ROSTER_NO_DEV, asserts the dev section present iff item_type in {task,bug,review} and absent-without-crash otherwise, plus a byte-identical golden on the dev roster — directly honoring the pin-roster hazard. This uses the same template-render mirror the OLD suite used (test_playbook layer_b), so no coverage lost. FEAT-336 pins genuinely present for the in-scope rows: TASK-365 CLI help (cli/test_help_text_follows_spec_vocabulary.py — retype/create/update --priority follow the bound collection [high|low not urgent/medium], list/tree de-enumerate to "priority collection", init hint points at create --help), and TASK-368 item-skill trailer-names-real-kind + spec-derived lifecycle are pinned by the byte-identical skill_body_sq-<type>.txt golden. TASK-369 squads-skill/role-body pins are ledger group 24 (a later chunk), correctly out of rows 60-81.
  - GOLDEN DEDUP correct, no coverage lost (row 76): cli/test_json_output_shape.py parametrizes one golden per command reusing the existing reviewed reference renders (read-only), and adds test_the_generic_show_and_the_typed_show_converge_on_one_identical_golden_shape — the convergence test proving the typed and generic entry points agree on ONE golden instead of two identical files. Both entry points still checked. UPDATE_GOLDENS=1 reviewed-regen protocol per CONVENTIONS section 6. SLUG dedup correct (row 81): the validator gets one service unit home (test_slug_resolution.py: agent/operator/sentinel/@-normalise/unknown-raises/error-names-valid) and each CLI surface keeps a thin per-surface test (test_slug_validation_surfaces.py: mine/inbox/comment-as/update-assignee+author/list-assignee/subtask add+update) — the deliberate wiring-point repetition, nothing distinct dropped.
  - Rows homed at target layer, behavior-named; NO ticket IDs / layer_a / golden_lock / characterization in any of the 31 files (grep clean). The 2 new goldens (playbook_spec.json, role_catalog_spec.json) are legit P2 spec-as-artifact snapshots (test_playbook_spec_artifact / test_role_catalog_artifact). Row 32 correctly not duplicated (chunk 1). LOW (non-blocking, carry-forward): (1) the has_dev two-state GATE is proven only via the render mirror (both old and new) — neither drives the dev-section-present-iff-dev branch against the real ClaudeCodeBackend._write_item_skills; a dev-section assertion on the real backend (in test_backend_lifecycle_contract or test_custom_type_skill_generation) would close the mirror-drift gap, but it is not a regression vs the old suite. (2) ledger row 63 targets has_dev at integration; homed at unit — defensible (old test was also a render mirror; the real-backend managed-output is separately covered at integration). Clean parity-gate input for Phase 3.
- [2026-07-10T10:04:59Z] Catherine Manager:
  - Chunk 3/5 (backend/agent, ledger rows 60-81) reviewer-APPROVED: non-vacuous (real ANSI-strip path, real backend conformance), has_dev pinned both roster states, FEAT-336 CLI-help + item-skill regressions pinned, golden dedup correct (one golden + convergence test, no coverage lost; other 23 audited clean). Two LOW carry-forward notes accepted (real-backend has_dev assertion vs render mirror; row-63 unit-vs-integration placement). Full suite green (2383, --run-slow green). Landing chunk 3.
- [2026-07-10T10:13:31Z] Elias Python:
  - Starting chunk 4a (groups 11-13: sub-entity/discussion mechanics, reflog emission + lineage-tree core, views/filters). Adding new files under tests/{unit,service,cli,integration} only; old suite untouched.
- [2026-07-10T10:26:07Z] Elias Python:
  - Chunk 4a done: 19 new files (unit 8, service 8, cli 4, integration 1) covering ledger rows 82-97 (groups 11-13).
  - Group 11 (82-89): row82 frontmatter-not-markers + row84 head/summary mechanism split unit(_discussion.py pure fns)+service(re-render on real mutations); row83/85 marker/comment cluster thin service; row86 check-detects integration; row87 inbox service; row88 title-advisory parametrized-over-kind service+cli; row89 terminal Accepted/Published unit+service+cli.
  - Group 12 (90-92): row90/91 split from ledger's single 'service' label per actual layering -- unit test for the append_line/read_lines primitive (OSError+serialization-error swallow, malformed-line handling) plus service test for the verb-emits-one-line parametrization + repair/check-never-reads-reflog + no-reflog-backward-compat + failed-append-no-rollback; row92 pure tree-building fns (_build_session_maps/_render_reflog_tree) unit, no CLI/svc -- correctly excludes sq-reflog-tree CLI and session-seeding (chunk 5's groups 21/22).
  - Group 13 (93-97): row93 ItemFilter unit + tree_view ancestor/depth mechanism service + thin list/tree CLI smoke; row94 depends-on/blocks equivalence service + gap#3 (Ready-while-blocked orthogonality, now directly asserted); row95 search/workload service+cli; row96 (priority views) confirmed fully collapsed into chunk 2's generic-badge-axis test, no new file (per dedup #8); row97 (mine) confirmed already homed in chunk1's test_slug_validation_surfaces.py.
  - Gates: pyright/ruff check/ruff format clean repo-wide. New files alone: 130 tests green. Full suite (old+new): 2519 tests, 0 failures, 6 skipped (slow), exit 0. ref-hygiene test green. No old files touched, no pyproject change, nothing committed.
- [2026-07-10T10:33:30Z] Paul Reviewer:
  - Reviewed FEAT-231 Phase 2 chunk 4a (ledger rows 82-97, groups 11-13). VERDICT: CHANGES-REQUESTED — one genuine coverage gap (row 97, the mine VIEW behaviour). Everything else is APPROVE-quality: non-vacuous, gap #3 genuine, reflog dedup lost nothing, all other rows homed; both trees green (full run incl --run-slow: exit 0, 0 failures). The fix is one small test.
  - F1 (BLOCKER, narrow — row 97 mine view behaviour is a real coverage loss): the old tests/test_priority_views.py::test_mine_cli positively asserted that mine manager RETURNS the manager-assigned TASK-2 (the filter behaviour). That assertion has NO new home. What exists: cli/test_slug_validation_surfaces.py::TestMine only validates the slug ARGUMENT (requires-slug / unknown-exits-1 / valid-works=exit0), and cli/test_json_output_shape.py pins the mine_manager golden which is [] (the golden_squad assigns NOTHING to manager, so it never exercises a match). mine is thin wiring over svc.list_items(assignee=slug); the ItemFilter assignee mechanism IS unit-tested (unit/test_item_filter_matching.py::test_matches_assignee), but neither list_items(assignee=) NOR the mine command is ever asserted to return an assigned item and exclude an unassigned one. The dev claim (mine already homed in the slug-validation surfaces) is incorrect for the VIEW behaviour. Fix: add one row-97 test (service or cli) creating an item assigned to a slug + one assigned elsewhere, asserting mine <slug> (or list_items(assignee=slug)) returns exactly the first — matching the deleted test_mine_cli. Cheap; needed before Phase 3 deletes the old suite.
  - Everything else verified GENUINE and non-vacuous. Gap #3 (Ready-and-blocked): service/test_dependency_blocking.py::test_an_item_can_be_ready_and_blocked_at_the_same_time sets the dependent status to Ready (asserts get().status==Ready) AND asserts it appears in svc.blocked() via a still-open depends-on — both facts on ONE item, exactly the ledger gap. Sub-entity state in frontmatter not body (row 82), marker-injection guard (85, 7 tests, invariant #3), check detects dangling-parent + broken-marker (86), inbox @mention surfacing incl. terminal exclusion (87), Accepted/Published terminal semantics unit+service (89), reflog emission (90) parametrized over all 8 verbs create/status/update/ref/comment/subentity/retype/remove — no verb dropped, no 9 near-identical bodies. blocked equivalence/union/closed-excluded (94) genuine.
  - DEDUP + layer split sound: reflog 90/91 split is correct — unit/test_reflog_line_persistence.py covers the append_line/read_lines primitive + resilience (OSError/serialization swallowed, truncated/interior-malformed lines) against bare tmp_path; service/test_reflog_emission_and_resilience.py covers the real per-verb emission through the service. The unit half does NOT claim the emission path (that is the service half) — no gap. Row 96 (priority views) correctly fully collapsed into chunk 2 generic-axis (no new file). Scope boundary respected: no reflog-READ CLI (group 21) or session-SEEDING (group 22) here — those are chunk 5; no premature overlap. All rows behavior-named; NO ticket IDs / layer_a / golden_lock / characterization in the 19 files (grep clean, excluding synthetic data IDs). Re-review = just confirm the one row-97 test lands green.
- [2026-07-10T10:36:47Z] Elias Python:
  - Row-97 gap closed per reviewer/coordinator feedback: added test_mine_view_returns_exactly_the_items_assigned_to_that_slug to tests/service/test_search_and_workload_views.py -- creates an item assigned to 'manager' and another assigned to 'python-dev', asserts list_items(assignee='manager') (the mechanism sq mine calls) returns exactly the manager item and excludes the other. This is the positive assertion the old test_mine_cli made that had no new home.
  - Verified: file's 3 tests green; ref-hygiene green; pyright/ruff check/ruff format clean repo-wide; full default suite 2520 tests, 0 failures, 6 skipped (slow), exit 0. Additive only, nothing committed. Leaving TASK-374 InProgress for the next chunk.
- [2026-07-10T10:37:26Z] Catherine Manager:
  - Chunk 4a/6 (mechanics, ledger rows 82-97) reviewer-APPROVED after fixing F1: the row-97 'mine' VIEW behaviour was a genuine coverage loss (old test_mine_cli's positive assertion had no new home; the slug-validation test only checked the argument, golden was empty) — now restored with a service test asserting mine returns exactly the assigned item and excludes others. Gap #3 (Ready-and-blocked) genuine; priority-views collapsed into chunk 2's generic axis; reflog-emission parametrized over all 8 verbs. Full suite green (2520, --run-slow green). Landing chunk 4a.
- [2026-07-10T10:49:26Z] Elias Python:
  - Starting chunk 4b/6: FEAT-231 Phase 2 checks/rendering/hygiene/adoption (ledger groups 14-17, rows 98-110). New files only under tests/{unit,service,cli,integration}/; old flat suite untouched.
- [2026-07-10T10:59:30Z] Elias Python:
  - Chunk 4b/6 done: 17 new test files (unit/service/cli/integration) covering ledger groups 14-17 (rows 98-110), plus a 1-liner CONVENTIONS.md F1 clarification and a 1-asset extension to unit/test_bundled_toml_packaging.py (default_workflow.toml, per that file's own forward note).
  - Dedup cluster #7 audit: rendered-text goldens across test_show_render/test_golden_rendered_output/test_rendering had no literal overlap once sorted by render path — the CLAUDE.md/AGENTS.md/workflow-cheatsheet/skill-body goldens in test_golden_rendered_output.py are groups 8/9 territory (item-skill goldens already homed in chunk 4a's test_item_skill_dev_gate.py; the other 3 remain unhomed, out of my rows). Kept exactly 2 new homes for row 104: cli/test_show_command_renders_body_and_subentities.py (the sq-show panel/TTY/--full/bracket-escaping path, consolidated ~60 old tests to 17) and unit/test_item_and_subentity_templates_render_structurally.py (the raw items/*.md.j2+block.md.j2 template path). Everything else in test_rendering.py was already homed by chunk 4a (badge collections, head/summary mechanism) so not re-created.
  - F1: added the one-line unit-layer clarification to tests/CONVENTIONS.md #1 (repo-artifact/packaging self-tests still count as unit).
  - F2: new unit/test_source_and_new_test_tree_have_no_stray_ticket_references.py splits the scan in two: full-text over src/+docs/ (same as the old scan, plus its tutorial/recipes/adoption doc allowlist), and a narrower identifier+docstring-only AST scan over tests/unit|service|cli|integration/ (assertion data like rendered TASK-000001/ST1 ids is legitimate and excluded on purpose; only file/class/function names+docstrings are checked) — confirmed clean against the whole new tree bar one pre-existing, explicitly allowlisted synthetic-id docstring mention in chunk 4a's test_json_output_shape.py fixture.
  - Gates: pyright 0 errors, ruff check+format clean. New files: all pass in isolation. Full suite (old+new, default -n auto): exit 0, green, only pre-existing slow-marked skips. Old tests/test_squad_ref_hygiene.py still green standalone.
- [2026-07-10T11:08:00Z] Paul Reviewer:
  - Reviewed FEAT-231 Phase 2 chunk 4b (ledger rows 98-110, groups 14-17 + dedup cluster #7). VERDICT: APPROVE. Non-vacuous, the 3 flagged section-goldens are all scheduled (no gap), F1/F2 sound, every row 98-110 homed; both trees green (full run incl --run-slow: exit 0, 0 failures). Two LOW non-blocking notes.
  - NON-VACUOUS: advisory checks are genuinely fail-OPEN (service/test_status_banner_advisory_check.py + test_unwritten_subentity_body_advisory_check.py assert level=="warn", name the item + the fix, AND pin the never-flagged negatives: topical mention / cross-ref to another item status / fenced-code / discussion banner / one-char divergence from the placeholder). Override precedence (100), env-cache isolation (101), manifest/stamp freshness (102), the full override scaffold/scan/diff/update/check lifecycle (103, 19 tests), adopt-imports-legacy-tree + idempotent (108), --at time-forging of item+comment timestamps + unparseable-rejected (109) and set_now-until-cleared + parse_iso (110) all genuinely exercised.
  - The 3 flagged section-goldens are covered-or-scheduled — NO gap. workflow_cheatsheet, claude_md_section, agents_md_section are all group 23 (chunk 5): row 144 pins the cheatsheet + the CLAUDE.md section golden, rows 140-145 own the whole cheatsheet/CLAUDE.md/AGENTS.md rendering surface. Chunk 3 additionally covers the managed SECTIONS for content-presence (roster names appear), idempotency (write_managed byte-identical on 2nd run), marker-once, and the "regenerated by sq sync" warning — so they are not un-covered today, only their byte-identical golden pin lives in chunk 5. Chunk 4b correctly does NOT claim them and correctly defers. Forward-flag (LOW) for the chunk-5 review: row 144 names only ONE section golden ("the CLAUDE.md agents-section") + the cheatsheet — ensure BOTH claude_md_section AND agents_md_section get byte-identical goldens (old row 64 / the retired test_layer_b_rendered_output_byte_identical_to_snapshot pinned the managed-section render), so the AGENTS.md section render does not lose its exact pin.
  - F2 allowlisted docstring is LEGIT (not a chunk-1-style leak to clean): the allowlisted ("tests/cli/test_json_output_shape.py","FEAT-2") is a SYNTHETIC fixture-layout docstring ("ROLE-2 manager, FEAT-2 User authentication, TASK-3 ...") documenting the golden_squad s manufactured item ids for the reader — describing test DATA, not citing a real backlog ticket. Materially different from chunk 1 s "pre-ADR-323" (a real-decision citation that HAD to be reworded). Allowlisting is the right handling (a synthetic fixture id does not go stale and is not dev-archaeology); a trivial reword ("the feature item" instead of "FEAT-2") would avoid the allowlist entry but is optional, not required. F1 CONVENTIONS one-liner is accurate + minimal (the exact unit-layer no-filesystem clarification I recommended). F2 scan design is sound: full-text scan of src/+docs/ (doc-allowlisted) + AST identifier/docstring-only scan of the new tests dirs (assertion-data left alone), with positive plant-tests proving it catches a real ref and ignores placeholders/data.
  - F1-chunk4b (LOW, non-blocking — F2 scan robustness): _name_and_docstring_violations uses REFERENCE_PATTERN.search (FIRST match per surface only) + a (path,token) allowlist, so a SECOND non-allowlisted ticket reference in the SAME docstring/surface, appearing AFTER an allowlisted first match, is masked (never examined). Concretely: the test_json_output_shape module docstring contains FEAT-2, TASK-3, BUG-4, ADR-5, REV-6 — only FEAT-2 (first) is seen and allowlisted; the rest are silently permitted (benign today, all synthetic, but a future REAL citation appended to such a surface would slip). Harden with re.findall over each surface, allowlisting specific (path,token) pairs and reporting every non-allowlisted match. Row 107 (ships-in-wheel) correctly folded into the parametrized packaging test (playbook+roles+default_workflow). No ticket IDs in the 16 new files (its own scan is green). Dedup cluster #7 preserved. Clean parity-gate input for Phase 3 (modulo the two LOW notes).
- [2026-07-10T11:12:35Z] Elias Python:
  - Hardening applied to the F2 hygiene scan (tests/unit/test_source_and_new_test_tree_have_no_stray_ticket_references.py): _name_and_docstring_violations now uses REFERENCE_PATTERN.findall over each surface (not .search), checking every matched token against the allowlist instead of only the first — a later non-allowlisted ref on the same surface can no longer be masked by an earlier allowlisted one.
  - Confirmed the fix actually bites: re-running with findall immediately surfaced TASK-3/BUG-4/ADR-5/REV-6 in tests/cli/test_json_output_shape.py's fixture docstring (previously masked behind the already-allowlisted FEAT-2) — extended the allowlist with all four (same synthetic-seeded-id rationale as FEAT-2, same file).
  - Added a regression test (test_an_allowlisted_token_never_masks_a_later_non_allowlisted_token_on_the_same_surface) reproducing the exact masking scenario via monkeypatched allowlist, proving the second token is still caught.
  - Gates: pyright 0 errors; ruff check + format clean (one PERF401 finding fixed, autoformatted). tests/unit/test_source_and_new_test_tree_have_no_stray_ticket_references.py: 8/8 green (incl. the planted positive-control ref test and the new regression test). tests/test_squad_ref_hygiene.py (old): 5/5 green. Full default suite (old+new, -n auto): exit 0, green.
  - No commits made; TASK-374 left InProgress per instruction.
- [2026-07-10T11:14:04Z] Catherine Manager:
  - Chunk 4b/6 (checks/rendering/hygiene/adoption, ledger rows 98-110) reviewer-APPROVED: advisory checks fail-open, rendered-output dedup (sq-show ~60->17), adoption/time-forging genuine. The 3 section goldens (CLAUDE/AGENTS/cheatsheet) confirmed scheduled for chunk 5 group 23 + content-covered by chunk 3 (no gap). F1 (CONVENTIONS clarification) + F2 (hygiene scan extended to new dirs, hardened to findall per review F-a — immediately caught 4 masked synthetic fixture-ids). F-b (both CLAUDE+AGENTS section goldens) carried to chunk 5. Full suite green (2634, --run-slow green). Landing chunk 4b.
<!-- sq:discussion:end -->
