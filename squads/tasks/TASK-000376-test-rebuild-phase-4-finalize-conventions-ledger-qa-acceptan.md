---
id: TASK-376
sequence_id: 376
type: task
title: 'Test rebuild Phase 4: finalize conventions, ledger, QA acceptance'
status: Done
parent: FEAT-231
author: tech-lead
created_at: '2026-07-10T04:48:21Z'
updated_at: '2026-07-10T15:49:51Z'
---
<!-- sq:body -->
## Phase 4 — Finalize conventions, ledger, QA acceptance

Final phase of the FEAT-231 rebuild. The battery is authored and the old suite is gone; this phase
turns the working artifacts into durable documentation and drives feature acceptance.

### Scope
- Finalize `tests/CONVENTIONS.md`: lock the layer structure, naming rules, per-layer fixture
  conventions, how to add a layer, and the golden-snapshot protocol as the standing contract for
  future test authors.
- Finalize the coverage ledger (proposed `tests/COVERAGE_LEDGER.md`) as the **durable
  characterization artifact** — the map a future developer reads before a schema/vocab change to
  see what each cluster protects and why. Reconcile it with the actual shipped test ids from
  Phase 3's parity report so it stays accurate.
- Update any project docs that reference the test layout (e.g. CLAUDE.md's Testing section if the
  layered structure / `-m 'not slow'` default changes the documented workflow).
- Hand to QA for **feature acceptance** against all of FEAT-231's acceptance criteria:
  1. default `uv run pytest` < 30s (scale excluded via `slow` + addopts);
  2. zero dev-archaeology vocab in any test name/file/dir;
  3. `CONVENTIONS.md` documents structure/naming/fixtures/golden protocol;
  4. coverage ledger maps every Principle-5 bug-class with no gaps;
  5. `uv run pytest -m slow` exercises scale paths and passes;
  6. `uv run sq check` clean.
  And the four user stories US1–US4.

### Dependencies
Depends on Phase 3 (swap complete). Last phase; on QA acceptance, FEAT-231 closes.

### Acceptance
- CONVENTIONS.md + COVERAGE_LEDGER.md finalized and committed alongside the new suite.
- QA verifies all six ACs + US1–US4 end-to-end and records the acceptance verdict on FEAT-231.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 376 add-subtask "<title>"`; track with `sq task 376 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-10T15:49:27Z] Mara Tester:
  - FEAT-231 ACCEPTED — all 6 ACs + US1-4 verified on final state (old flat suite gone, tests/{unit,service,cli,integration}/ + kept test_scale.py is the sole suite).
  - AC1 (default <30s) PASS: bare 'uv run pytest' = 24.09s real, 1219 passed/6 skipped (1225 collected), exit 0.
  - AC5 (slow paths pass) PASS: 'uv run pytest --run-slow' = 2m34.7s real, 1224 passed/1 skipped (1225 collected, exit 0) — the 5 scale tests all ran. Note: shipped mechanism is a custom --run-slow collection hook, not a literal 'pytest -m slow' (that alone just skips all 5, exit 0, exercising nothing) — licensed by Principle 3's 'or equivalent' wording; CONVENTIONS.md $8 now documents this explicitly (was stale, said 'addopts -m not slow', which never shipped).
  - AC2 (no dev-archaeology vocab) PASS: grepped tests/ for layer_a/layer_b/golden_lock/ticket-ID filenames — zero hits outside the two governance docs (which legitimately cite FEAT-231's own numbers) and tests/unit/test_source_and_new_test_tree_have_no_stray_ticket_references.py's own hygiene-scan test data (allowlisted by design, verified by reading that test's logic). No ticket-ID filenames found.
  - AC3 (CONVENTIONS.md) PASS: layers/naming/fixtures/golden protocol all documented; confirmed TASK-373's F1 clarification (unit-layer 'no filesystem' for repo-artifact self-tests) landed verbatim (line ~26). Found + fixed 3 stale spots (Phase-in-progress framing, a nonexistent 'addopts -m not slow' claim, a reference to the deleted tests/test_squad_ref_hygiene.py) — see artifact edits below.
  - AC4 (coverage ledger) PASS: 211 numbered rows / 26 groups, every Principle-5 bug-class mapped (is-vs-==, dangling pointers, FORCE_COLOR/ANSI, has_dev gate, migration edges, F1 load-boundary), row-count summary matches actual max row (211). Intro was stale (still said 'Phase 0, nothing deleted yet' and framed Phase 3 as not-yet-happened) — fixed to reflect the completed swap.
  - AC6 (sq check clean) PASS: exit 0, only pre-existing warn-level advisories (unwritten-stub placeholders, title-length) unrelated to FEAT-231.
  - Four-layer/four-pillar structure PASS: unit(62)/service(43)/cli(49)/integration(36) files all populated; spot-checked P1 (mechanism-once), P2 (goldens: 39 files under tests/goldens/), P3 (thin spine files), P4 (test_load_boundary_vocab.py, test_schema_mismatch_gate.py, test_workflow_reserved_vocab.py, test_workflow_lint_merge_errors.py, test_status_machine_transitions.py) all present and behavior-named.
  - US1-US4 PASS: US1 (behavior names) — AC2 grep confirms. US2 (<30s default) — AC1 timing confirms. US3 (invariant once, right layer) — ledger's dedup-cluster section + CONVENTIONS $5 codify this, spot-checked no obvious per-type duplication left in unit/. US4 (ledger preserves bug classes) — AC4 confirms every Principle-5 class + FEAT-208 F1 has a named row.
  - Artifact edits (light polish, both files, no src/test changes): COVERAGE_LEDGER.md — rewrote the stale Phase-0-only intro/status line to reflect the completed rebuild (kept the Deliverable-2 historical profiling section untouched, it's legitimately dated evidence). CONVENTIONS.md — updated the status line to 'finalized', rewrote $8 (scale/slow tests) to describe the actual shipped --run-slow collection hook instead of a never-shipped addopts flip, and fixed the ticket-ID-ban bullet's reference from the deleted tests/test_squad_ref_hygiene.py to the real new-suite hygiene test. Re-ran the hygiene test after editing (7/7 pass) — edits don't self-flag.
  - Process note (not a blocker): TASK-374 (Phase 2) is still status=InProgress in sq despite its work having fully landed and fed TASK-375's completed swap — worth a bookkeeping fix by whoever owns it.
<!-- sq:discussion:end -->
