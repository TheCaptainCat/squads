---
id: TASK-372
sequence_id: 372
type: task
title: 'Test rebuild Phase 0: behavior inventory + coverage ledger'
status: Done
parent: FEAT-231
author: tech-lead
subentities:
- local_id: ST1
  title: Coverage ledger maps every previously-caught bug-class to a new home
  status: Done
  story: US4
- local_id: ST2
  title: Profile durations + coverage to find duplicate-invariant clusters
  status: Done
  story: US3
created_at: '2026-07-10T04:48:18Z'
updated_at: '2026-07-10T05:30:56Z'
---
<!-- sq:body -->
## Phase 0 — Behavior inventory & coverage ledger (the accept gate)

First phase of the ground-up test-suite rebuild (FEAT-231). **Nothing is deleted or moved in this
phase.** Its output is the artifact that gates every later deletion: an inventory of what the
current ~1800-test / 80-file flat suite actually protects, and a ledger mapping each protected
bug-class to its planned home in the new four-pillar battery.

### Scope
- Enumerate the behaviours the current suite verifies, grouped by contract (not by current file).
  Read `tests/test_*.py` and the goldens under `tests/goldens/`.
- Build the **coverage ledger**: a table with one row per distinct bug-class / invariant, columns
  = {what it protects, where it lives today, planned new home (pillar + layer), notes}. Every
  bug-class named in the feature's Principle 5 and the manager's four-pillar comment MUST appear as
  a row, at minimum:
  - `is` vs `==` identity in the retype path (value-equality after de-typing)
  - dangling `.claude` skill pointers after a full init + migrate cycle
  - `FORCE_COLOR` / ANSI contamination in `--json` output
  - `has_dev` gate for generated skill rosters (dev-less roster omits dev skills, no crash)
  - migration edges: forward-only, `sq repair` idempotency, no data loss on `schema_version` bump
  - the FEAT-208 F1 miss: invalid/unknown vocab at the load boundary is silently indexed then
    crashes `sq check` (the genericity failure mode the enum suite structurally could not have)
  - reserved-vocab violations, malformed spec, override-merge conflicts, custom-type/status flows
- Profile the current suite: `pytest --durations=50` to identify the scale tests that own the
  wall-clock budget (candidates for the `slow` marker), and `pytest --cov` per module to find
  coverage hotspots and the "same invariant asserted at multiple layers" duplicate-invariant
  clusters (feeds the Phase 2 dedup — assert each invariant once, at the lowest meaningful layer).
- Record dev-archaeology naming to purge (`layer_a/b`, `golden_lock`, `FEAT-`/`TASK-`/`ADR-` refs,
  ticket-ID filenames like `test_workflow_renderer_261.py`) so Phase 2 authors against clean names.

### Deliverable
A reviewed inventory + coverage ledger, stored where it will become the durable characterization
artifact (proposed `tests/COVERAGE_LEDGER.md`, finalized in Phase 4). Reviewer sign-off required.

### Dependencies
None (first phase). Blocks Phase 1, 2, 3. The ledger is the accept gate: Phase 3 deletion cannot
proceed until every ledger row has a verified green home.

### Acceptance
- Ledger covers every Principle-5 bug-class and every four-pillar edge-surface case with no gaps.
- Duration + coverage profile captured; scale-test `slow` candidates listed.
- Reviewed and approved before any Phase 2 authoring begins in earnest.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 372 add-subtask "<title>"`; track with `sq task 372 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Coverage ledger maps every previously-caught bug-class to a new home | US4 |
| ST2 | Done |  | Profile durations + coverage to find duplicate-invariant clusters | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Coverage ledger maps every previously-caught bug-class to a new home

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US4 — Coverage ledger preserves previously-caught bugs
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Delivered: tests/COVERAGE_LEDGER.md — 111 rows across 18 contract groups, every Principle-5 bug-class + four-pillar edge case mapped to a layer/pillar home. 4 gaps flagged (none blocking). 8 duplicate-invariant clusters flagged.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Profile durations + coverage to find duplicate-invariant clusters

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US3 — Each invariant asserted once, at the right layer
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Profiled once via uv run pytest (durations2.log/notslow.log, not re-run repeatedly). Full suite incl. slow: 129.13s. -m 'not slow': 25.78s (already under the 30s AC / sub-minute goal, no code change needed). The 5 tests in test_scale.py are the entire slow-marker set; no other O(n) test found hiding outside it.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-10T04:52:11Z] Mara Tester:
  - Starting Phase 0: behavior inventory + coverage ledger. No deletion/rewrite in this pass.
- [2026-07-10T05:14:11Z] Mara Tester:
  - Phase 0 done, no deletion/rewrite performed. Deliverable: tests/COVERAGE_LEDGER.md (111 rows / 18 contract groups). Every Principle-5 bug-class + four-pillar edge case has a row (retype is-vs-== -> row 2, dangling .claude pointers -> rows 61-62, FORCE_COLOR/ANSI -> row 75, has_dev gate -> row 63, migration edges -> rows 18/26/31, F1 load-boundary miss -> rows 20-24 given its own integration home, reserved-vocab/override-merge/custom-type flows -> rows 34-58).
  - 4 gaps flagged (additive, none blocking): the literal is-vs-== adversarial WorkflowSpec case (row 2), the compound init-then-migrate dangling-pointer scenario (no single test chains it today), Ready-status-while-blocked orthogonality, and conflicting-field override-merge (as opposed to cooperative reuse).
  - 8 duplicate-invariant clusters flagged for Phase 2 dedup (backrefs asserted at 2 layers, repair-idempotency re-derived per feature, reserved-prefix-collision in 2 files, reflog-emission-per-verb x9, ships-in-wheel x3, slug-validation x26 by design, 3 files of rendering goldens to audit for overlap, priority-views vs the new generic badge axis).
  - Dev-archaeology naming to purge: layer_a/layer_b (test_playbook.py x3), FEAT/TASK/ADR refs in docstrings/names (test_load_boundary_vocab.py, test_spine_characterization.py, reflog/service comments), the one ticket-ID filename (test_workflow_renderer_261.py), and a softer call on the *_characterization.py file-name suffix.
  - Duration profile (run once, not re-run repeatedly): full suite incl. the 5 already-slow-marked scale tests = 129.13s; -m 'not slow' = 25.78s (1791 tests) -- already comfortably under the 30s AC / sub-minute goal on this suite's own xdist -n auto (14 cores, already the default addopts). No new slow candidates found outside test_scale.py's existing 5. The 129s-vs-26s gap is core contention, not per-test cost -- confirms flipping addopts (TASK-374 ST2) is the whole win, no further speedup design needed.
  - Open question for op-pierre: is the coverage-ledger structure/row-granularity what you want as the durable artifact, or do you want it flatter/shorter before Phase 1 scaffolding starts? Leaving TASK-372 InProgress for reviewer sign-off per its own acceptance criteria.
- [2026-07-10T05:19:39Z] Paul Reviewer:
  - Completeness review of the coverage ledger (the Phase-3 accept gate). VERDICT: NEEDS-ROWS. The ledger is thorough and well-reasoned on the contracts it DOES cover (taxonomy, dedup, and the 4 flagged gaps are all sound — see below), but it MISSES several current-suite contracts entirely. As the gate that authorizes deleting the old suite, it must enumerate these first, or their protection is silently lost. I mapped all 80 test files to rows; 5 contracts have NO home.
  - UN-HOMED #1 (critical) — the entire  command: tests/test_graph.py (33 tests) + goldens graph_feat_json/graph_feat_dot. The only 'graph' in the ledger is row 39's 'custom lifecycle graph' (parent-cycle) — unrelated. The graph SERVICE traversal (BFS depth bound, --kind filter, --direction out/in/both, cycle handling, seen-dedup) and its CLI/JSON/DOT surface are absent. Row 76's JSON-golden '…' cannot stand in for 33 tests of traversal logic. Needs its own contract group.
  - UN-HOMED #2 (critical) — the core status-machine ENFORCEMENT contract: test_workflow.py (5) + test_workflow_rules.py (10) + test_bug_workflow.py (16) = 31 tests, cited by ZERO rows. Missing: per-type valid/illegal transitions (can_transition, illegal-skip rejected), initial states, exact TERMINAL-set membership, set_status vocabulary rejection, and the load-bearing --force semantics (force bypasses a transition EDGE but NOT the status vocabulary), plus the parent_allowed rule table + parent_hint. The ledger has retype-CROSSING (grp 1), spec-LOADING (grp 5), linearization-DISPLAY (73), custom-status views (56), and Accepted/Published-terminal (89) — but not the foundational 'the machine validates every transition and set_status enforces vocab+edge+force'. grep for parent_allowed in the ledger returns nothing. This is the workflow engine's core enforcement — highest coverage-loss risk.
  - UN-HOMED #3 — 2026-07-10T04:14:42Z  update  FEAT-336  actor=system  
    {"status":["Draft","InProgress"]}
    2026-07-10T04:14:42Z  update  FEAT-336  actor=system  
    {"status":["InProgress","Done"]}
    2026-07-10T04:14:57Z  update  TASK-363  actor=system  
    {"status":["Draft","Ready"]}
    2026-07-10T04:15:35Z  update  TASK-363  actor=system  
    {"status":["Ready","InProgress"]}
    2026-07-10T04:33:54Z  comment  TASK-363  actor=python-dev  
    {"author":"python-dev"}
    2026-07-10T04:35:14Z  update  TASK-363  actor=system  
    {"status":["Draft","InProgress"]}
    2026-07-10T04:41:11Z  comment  TASK-363  actor=reviewer  {"author":"reviewer"}
    2026-07-10T04:41:47Z  comment  TASK-363  actor=reviewer  {"author":"reviewer"}
    2026-07-10T04:42:43Z  comment  TASK-363  actor=manager  {"author":"manager"}
    2026-07-10T04:42:43Z  update  TASK-363  actor=system  
    {"status":["InProgress","Done"]}
    2026-07-10T04:43:43Z  comment  TASK-364  actor=manager  {"author":"manager"}
    2026-07-10T04:43:44Z  update  TASK-364  actor=system  
    {"status":["Draft","InProgress"]}
    2026-07-10T04:43:45Z  update  TASK-364  actor=system  
    {"status":["InProgress","Done"]}
    2026-07-10T04:43:45Z  comment  FEAT-334  actor=manager  {"author":"manager"}
    2026-07-10T04:43:46Z  update  FEAT-334  actor=system  
    {"status":["Draft","InProgress"]}
    2026-07-10T04:43:47Z  update  FEAT-334  actor=system  
    {"status":["InProgress","Done"]}
    2026-07-10T04:44:06Z  comment  REV-360  actor=manager  {"author":"manager"}
    2026-07-10T04:44:06Z  update  REV-360  actor=system  
    {"status":["Requested","InReview"]}
    2026-07-10T04:44:07Z  update  REV-360  actor=system  
    {"status":["InReview","Approved"]}
    2026-07-10T04:44:08Z  comment  EPIC-335  actor=manager  {"author":"manager"}
    2026-07-10T04:44:09Z  update  EPIC-335  actor=system  
    {"status":["Draft","InProgress"]}
    2026-07-10T04:44:09Z  update  EPIC-335  actor=system  
    {"status":["InProgress","Done"]}
    2026-07-10T04:46:24Z  update  FEAT-231  actor=system  
    {"status":["Draft","InProgress"]}
    2026-07-10T04:48:18Z  create  TASK-372  actor=tech-lead  {"title":"Test rebuild 
    Phase 0: behavior inventory + coverage ledger","type":"task","status":"Draft"}
    2026-07-10T04:48:19Z  create  TASK-373  actor=tech-lead  {"title":"Test rebuild 
    Phase 1: layered scaffolding + re-homed 
    conftest","type":"task","status":"Draft"}
    2026-07-10T04:48:20Z  create  TASK-374  actor=tech-lead  {"title":"Test rebuild 
    Phase 2: author the four-pillar battery","type":"task","status":"Draft"}
    2026-07-10T04:48:20Z  create  TASK-375  actor=tech-lead  {"title":"Test rebuild 
    Phase 3: parity verification + destructive swap","type":"task","status":"Draft"}
    2026-07-10T04:48:21Z  create  TASK-376  actor=tech-lead  {"title":"Test rebuild 
    Phase 4: finalize conventions, ledger, QA 
    acceptance","type":"task","status":"Draft"}
    2026-07-10T04:49:52Z  body  TASK-372  actor=system  {}
    2026-07-10T04:49:52Z  body  TASK-373  actor=system  {}
    2026-07-10T04:49:53Z  body  TASK-374  actor=system  {}
    2026-07-10T04:49:54Z  body  TASK-375  actor=system  {}
    2026-07-10T04:49:54Z  body  TASK-376  actor=system  {}
    2026-07-10T04:50:01Z  subentity  TASK-372  actor=system  
    {"op":"add","kind":"subtask","local_id":"ST1","title":"Coverage ledger maps 
    every previously-caught bug-class to a new home"}
    2026-07-10T04:50:01Z  subentity  TASK-372  actor=system  
    {"op":"add","kind":"subtask","local_id":"ST2","title":"Profile durations + 
    coverage to find duplicate-invariant clusters"}
    2026-07-10T04:50:02Z  subentity  TASK-374  actor=system  
    {"op":"add","kind":"subtask","local_id":"ST1","title":"Behavior-named taxonomy 
    across the four pillars, no dev-archaeology"}
    2026-07-10T04:50:02Z  subentity  TASK-374  actor=system  
    {"op":"add","kind":"subtask","local_id":"ST2","title":"Fast by default: mark 
    scale slow, flip addopts to -m not slow, under 30s"}
    2026-07-10T04:50:03Z  subentity  TASK-374  actor=system  
    {"op":"add","kind":"subtask","local_id":"ST3","title":"Each invariant asserted 
    once at the lowest meaningful layer"}
    2026-07-10T04:50:03Z  subentity  TASK-375  actor=system  
    {"op":"add","kind":"subtask","local_id":"ST1","title":"Verify ledger parity 
    before deleting the old suite"}
    2026-07-10T04:50:51Z  comment  FEAT-231  actor=tech-lead  {"author":"tech-lead"}
    2026-07-10T04:51:33Z  update  TASK-372  actor=system  
    {"status":["Draft","Ready"]}
    2026-07-10T04:52:10Z  update  TASK-372  actor=system  
    {"status":["Ready","InProgress"]}
    2026-07-10T04:52:11Z  comment  TASK-372  actor=qa  {"author":"qa"}
    2026-07-10T05:13:46Z  subentity  TASK-372  actor=system  
    {"op":"update","kind":"subtask","local_id":"ST1"}
    2026-07-10T05:13:47Z  subentity  TASK-372  actor=system  
    {"op":"update","kind":"subtask","local_id":"ST1"}
    2026-07-10T05:13:48Z  subentity  TASK-372  actor=system  
    {"op":"update","kind":"subtask","local_id":"ST2"}
    2026-07-10T05:13:48Z  subentity  TASK-372  actor=system  
    {"op":"update","kind":"subtask","local_id":"ST2"}
    2026-07-10T05:13:56Z  subentity  TASK-372  actor=system  
    {"op":"body","kind":"subtask","local_id":"ST1"}
    2026-07-10T05:13:56Z  subentity  TASK-372  actor=system  
    {"op":"body","kind":"subtask","local_id":"ST2"}
    2026-07-10T05:14:11Z  comment  TASK-372  actor=qa  {"author":"qa"} READ command: test_reflog_read.py (20 tests). Group 12 homes reflog EMISSION (90) and the session TREE (92) but not the read/query CLI: --tail default/0, --op/--item/--actor filters AND-ed, JSON output. UN-HOMED #4 — session-lineage SEEDING/STAMPING: test_session_lineage.py (26 tests). Row 92 homes only test_reflog_tree (tree-building); the _actor.seed_session/current_session env+arg reading and the reflog session_id/parent_session_id line-stamping that FEEDS the tree are a distinct mechanism with no row. UN-HOMED #5 — workflow-cheatsheet/authoring-prose rendering: test_workflow_authoring_prose.py (17) + test_workflow_renderer_261.py. renderer_261 appears only in the naming-purge (rename note), with no coverage row; authoring_owner()/parent_chain() + the generic spec-driven cheatsheet derivation (incl. the dropped-type no-crash class from TASK-363) have no home. Row 72 (lane-derivation) is a different contract.
  - PARTIAL/minor (contract mostly present but file uncited — confirm the specific cases survive): test_role_resolver.py (20, project role field-wise override merge — only touched by row 69 naming + 103 scaffold); test_operators.py (11, operator add/list/as-author-assignee — only row 81/97 slug-acceptance); test_sections.py (4, the marker-safe section-edit PRIMITIVE itself, CLAUDE.md inv #3 — row 85 is injection-rejection, not the primitive); test_discussion.py (12, _discussion funcs: mention extraction, local-id normalization — partial via 83-85); test_skills.py (29, built-in per-type skill BODY content incl. the lifecycle-line/trailer TASK-368/369 fixed — partial via 55/63/64); test_workflow_lint.py (17 — contract homed at row 41 but file uncited); test_workflow_capability_flags.py (23 — homed under grp 5 rows 34-43/47 but uncited).
  - SOUND (agree): the 4 flagged gaps (is-vs-==, init→migrate→pointer, Ready-while-blocked, conflicting-field override) are correctly identified as genuinely-absent AND additive (new tests to write, not existing coverage being dropped) — the is-vs-== reasoning (incidental-today, no adversarial construction) is exactly right. Taxonomy is sensible: F1 load-boundary kept at integration (20-24), atomic-RMW/global-counter at unit/service (9-11), no row mis-homed in a weakening way. All 8 dedup clusters are safe — none collapses genuinely-distinct cases, and #6 (slug-validation) correctly keeps one thin per-surface CLI test while consolidating the validator. Recommendation: add the 5 un-homed contracts above as rows (graph as its own group; the status-machine enforcement as a new group; reflog-read + session-seeding split out under grp 12; cheatsheet-rendering under grp 15) before this ledger is treated as the delete-authorizing gate.
- [2026-07-10T05:20:10Z] Paul Reviewer:
  - Reposting two bullets that shell-quoting corrupted (backticks ran commands). UN-HOMED #1 clarification: the un-homed command is the sq-graph command (tests/test_graph.py, 33 tests, plus the graph_feat_json and graph_feat_dot goldens) — its service traversal (BFS depth bound, kind filter, direction out/in/both, cycle handling, seen-dedup) and CLI/JSON/DOT surface have no row.
  - UN-HOMED #3 (reposted clean): the sq-reflog READ command — tests/test_reflog_read.py, 20 tests. Group 12 homes reflog emission (row 90) and the session tree (row 92) but not the read/query CLI: tail default and tail 0, the op/item/actor filters AND-ed, and JSON output. No row.
  - UN-HOMED #4 (reposted clean): session-lineage seeding/stamping — tests/test_session_lineage.py, 26 tests. Row 92 homes only test_reflog_tree (the tree-building functions). The _actor seed_session/current_session env-and-arg reading, and the reflog line session_id/parent_session_id stamping that FEEDS that tree, are a distinct mechanism with no row. UN-HOMED #5: workflow-cheatsheet + authoring-prose rendering — tests/test_workflow_authoring_prose.py (17) + tests/test_workflow_renderer_261.py. renderer_261 appears only in the naming-purge (a rename note), with no coverage row; the authoring_owner/parent_chain helpers and the generic spec-driven cheatsheet derivation (including the dropped-type no-crash class) have no home. Row 72 lane-derivation is a different contract.
- [2026-07-10T05:28:02Z] Mara Tester:
  - Addressed the independent-review follow-up (5 uncited contracts + 7 flagged partials). tests/COVERAGE_LEDGER.md only; no test/source change, no commit.
  - New groups 19-24, rows 112-159 (48 new rows, total 111->159): 19 sq graph traversal+rendering (rows 112-118); 20 status-machine enforcement -- can_transition/illegal-skip, initial_status, exact TERMINAL-set, set_status vocab rejection, --force edge-not-vocabulary, parent_allowed+parent_hint, plus test_workflow_lint.py's lifecycle-reachability lint folded in as row 127 (rows 119-127, was the highest-risk zero-citation gap); 21 sq reflog read/query CLI (rows 128-129); 22 session-lineage seeding/stamping (rows 130-135); 23 workflow-cheatsheet + authoring-prose rendering, incl. a second dropped-type no-crash instance at row 140 (rows 136-145).
  - 7 partials: role_resolver field-wise override -> rows 146-148; operators CRUD -> row 149; test_sections.py marker-safe primitive -> row 150 (new foundational unit anchor, rows 83/85/100 now reference it); test_discussion.py -> split across amended row 84 (head/summary mechanism, now cited directly) + new row 151 (comment/mention/local-id remainder); test_skills.py built-in per-type + role-body content -> rows 152-156 incl. a third dropped-type no-crash instance at row 153; test_workflow_lint.py -> row 127 (row 41 amended to cross-ref it as the sibling lint family); test_workflow_capability_flags.py -> rows 157-159. Also folded a duplicate 'repair never reads reflog' citation into row 91.
  - Row-count summary + intro bullets updated to the new total and cross-refs. Row-number sequence verified contiguous 1-159, no gaps/dupes. TASK-372 left InProgress.
- [2026-07-10T05:29:56Z] Paul Reviewer:
  - Confirmation pass complete. VERDICT: SIGN-OFF. The 48 added rows (111 to 159) adequately home all five flagged contracts and all seven partials; a full re-scan of the 80 test files now finds ZERO with no ledger home.
  - 1. Group 20 (my highest-risk gap) is GENUINELY covered, not name-dropped: row 119 can_transition legal + illegal-skip per type; row 120 initial_status per type + state-membership; row 121 EXACT TERMINAL-set membership + cross-workflow disjointness (no vocab leakage); row 122 set_status vocab rejection + CLI; row 123 the load-bearing --force bypasses EDGE not VOCABULARY distinction (verbatim, flagged P4); row 124 concrete full-lifecycle spine; row 125 parent_allowed rule table + parent_hint; row 126 subtask story-mapping + ref-kind validation; row 127 lifecycle-reachability lint (also absorbs the previously-uncited test_workflow_lint, cross-reffed from amended row 41). Every sub-point I listed is present with real test citations.
  - 2. All five flagged contracts homed: sq-graph -> Group 19 (112-118, traversal/direction/kind/cycle/DOT+Mermaid/CLI/JSON golden); status-machine -> Group 20; reflog-read -> Group 21 (128-129); session seeding/stamping -> Group 22 (130-135); cheatsheet/authoring-prose -> Group 23 (136-145, homing BOTH test_workflow_authoring_prose and the ticket-ID-named test_workflow_renderer_261). The 7 partials -> Group 24 (146-159): role_resolver 146-148, operators 149, sections 150, discussion 151, skills 152-156, capability_flags 157-159, lint 127. All cited.
  - 3. Bonus: the new rows add genuine analytical value, not just filler — row 140 + 153 correctly split the dropped-type no-crash class into its two instances (cheatsheet + skill body) as P4 first-class; row 128 honestly flags that combined-filter AND-semantics is not actually proven today (cheap Phase-2 add); row 135 flags migration-registry tests misfiled in session_lineage and recommends relocation; row 146 surfaces the role-override (permissive) vs workflow-override (fail-closed) asymmetry as a real design call; row 150 makes the sections primitive the foundational anchor and points 83/85/100 at it. The ledger is now complete and internally consistent enough to serve as the Phase-3 delete-authorizing accept gate. No remaining rows needed.
- [2026-07-10T05:30:55Z] Catherine Manager:
  - Reviewer SIGN-OFF: the 159-row coverage ledger homes all 80 current test files with zero blind spots (the first review caught 5 un-homed contracts incl. the foundational status-machine enforcement — Group 20 — all since added and confirmed genuinely covered). Profiling settles the perf question: full 129s vs -m 'not slow' 25.78s, the 5 scale tests own the entire gap. This is the delete-authorizing accept gate. Phase 0 complete.
<!-- sq:discussion:end -->
