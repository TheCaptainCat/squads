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
updated_at: '2026-07-10T08:48:25Z'
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
<!-- sq:discussion:end -->
