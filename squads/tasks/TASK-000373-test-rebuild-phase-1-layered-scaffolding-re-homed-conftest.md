---
id: TASK-373
sequence_id: 373
type: task
title: 'Test rebuild Phase 1: layered scaffolding + re-homed conftest'
status: Done
parent: FEAT-231
author: tech-lead
created_at: '2026-07-10T04:48:19Z'
updated_at: '2026-07-10T08:14:15Z'
---
<!-- sq:body -->
## Phase 1 — Layered scaffolding + re-homed conftest

Second phase of the FEAT-231 rebuild. **Nothing from the old suite is deleted or moved.** This
phase stands up the new tree so it runs green-empty alongside the existing flat suite, ready for
Phase 2 to author into.

### Scope
- Create the four-layer directory structure per the feature's Principle 2:
  - `tests/unit/` — pure functions, models, spec logic; no `project` fixture, in-process values.
  - `tests/service/` — `Service` façade + `IndexStore`; `svc` fixture; assert return values +
    frontmatter.
  - `tests/cli/` — `CliRunner` invocations; `project` fixture; assert exit code, stdout, generated
    files.
  - `tests/integration/` — multi-step workflows + migration round-trips; cross-layer by design.
- Author `tests/CONVENTIONS.md` (initial version; finalized in Phase 4): naming rules
  (behavior-named, no dev-archaeology — realizes US1), which fixtures belong in which layer, how to
  add a layer, and the golden-snapshot protocol (pin all inputs, source of truth is the input spec,
  one golden per distinct rendering path, goldens live under `tests/goldens/`, updated intentionally).
- Re-home the shared `conftest.py`, carrying its hard-won guards **verbatim in behaviour**:
  - the pre-import `FORCE_COLOR`/`CLICOLOR_FORCE`/`PY_COLORS` strip (module-level Console latches
    color at import) plus the autouse per-test re-strip and `COLUMNS=80` width pin;
  - the leak-guards: clock override reset, ambient actor reset, `_active_spec`/`_active_dir` +
    custom-command cache resets, rendering-engine ContextVar/`_env_cache` reset;
  - the `frozen_time`, `project`, `svc`, `runner`, `invoke`, `run_in_thread` fixtures.
  Decide layout: a single root `tests/conftest.py` for cross-layer fixtures + per-layer `conftest.py`
  for layer-scoped ones (document the split in CONVENTIONS.md).
- Carry `tests/fixtures/corpus/*` **verbatim** (frozen migration-input snapshots — v0_1..v0_8) and
  keep the corpus README's standing "add a fixture on every schema bump" rule. Do NOT regenerate.
- Keep `pyproject.toml` `testpaths`/`-n auto` working so both old and new trees collect and run
  together, green. (The `addopts = -m 'not slow'` flip is deferred to Phase 2, where scale tests
  get marked.)

### Dependencies
Depends on Phase 0 (inventory informs the taxonomy). Blocks Phase 2.

### Acceptance
- New `tests/{unit,service,cli,integration}/` collect and run green-empty alongside the old suite.
- `CONVENTIONS.md` present with naming + fixture + golden rules.
- conftest guards preserved (prove FORCE_COLOR strip + leak-guards still active).
- corpus fixtures carried byte-identical; `uv run sq check` clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 373 add-subtask "<title>"`; track with `sq task 373 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-10T07:52:50Z] Elias Python:
  - Starting Phase 1: layered scaffolding + CONVENTIONS.md + conftest verification. Non-destructive; old flat suite untouched.
- [2026-07-10T08:06:18Z] Elias Python:
  - Phase 1 done: tests/{unit,service,cli,integration}/ created with __init__.py (needed — the flat suite has no tests/__init__.py, so layers must be packages to avoid future basename collisions under pytest's default import-mode) + a per-layer conftest.py stub (docstring only, no fixtures yet) + one behavior-named scaffold test each proving the layer reaches its intended fixture (svc / invoke+project / svc+invoke).
  - Root tests/conftest.py left 100% untouched (git diff is empty) — it already cascades to the new dirs via pytest's normal conftest resolution, so 'both trees share fixtures' required zero edits. Every leak-guard, the FORCE_COLOR/COLUMNS strip, and the --run-slow hook are verbatim, unchanged.
  - tests/CONVENTIONS.md added: layer scope table, the 4 pillars (P1-P4), naming bans (layer_a/b, golden_lock, ticket IDs, ticket-ID filenames; *_characterization discouraged), fixture split (root vs per-layer), golden protocol, and the dedup discipline citing the ledger's duplicate-invariant clusters as worked examples.
  - Gates: pyright 0 errors, ruff check + format clean. Full suite: 1794 passed, 6 skipped (5 slow + 1 pre-existing), 0 failures, 32.57s — 1796 old (matches ledger's Phase 0 count exactly, byte-identical) + 4 new scaffold tests. test_squad_ref_hygiene.py: 5 passed. sq check clean (only pre-existing unrelated advisories). tests/fixtures/corpus/* and every tests/test_*.py file: zero diff.
  - Left InProgress for tech-lead/reviewer sign-off; tree is dirty for review, nothing committed.
- [2026-07-10T08:12:04Z] Paul Reviewer:
  - Reviewed FEAT-231 Phase 1 scaffolding (independent). VERDICT: APPROVE. CONVENTIONS.md is solid enough to author Phase 2 against, the packaging is safe, and the old flat suite is provably intact. Two LOW non-blocking notes below.
  - CONVENTIONS.md is solid: the four-layer split is unambiguous (the table s "Needs project/svc?" column + "Asserts on" + the placement rule-of-thumb + the explicit "if a unit test would prove it, it goes in unit even if cli could" tie-break + the integration criterion of "genuinely chains 2+ ops no single layer expresses"); the four pillars are actionable with concrete examples and an infer-from-claim-shape fallback, P4 budgeted as first-class; the naming bans (layer_a/layer_b, golden_lock, all ticket prefixes in file/name/docstring, ticket-in-filename) are unambiguous with the "This system guarantees that…" sentence test + correct-form examples, and *_characterization is correctly the softer "discouraged, judgment" call; the golden protocol (pin all inputs, human-reviewed source-of-truth, one-golden-per-path, own file) and the dedup discipline (assert once at lowest layer; the genuine-duplicate vs deliberate-wiring-point distinction modeled on the slug-validator cluster) are concrete enough to prevent the drift the ledger flagged. Fixtures/determinism/scale sections carry the leak-guards forward correctly.
  - Packaging is SAFE. import-mode defaults to prepend; each layer dir has its own __init__.py while root tests/ has none, so same-basename files namespace cleanly (unit.test_scaffold vs service.test_scaffold) and coexist with the flat top-level modules (test_index etc.) with no collision — and this holds through the Phase-2 transition (a future unit.test_index vs the still-present flat test_index are distinct dotted names). Full suite with --run-slow is green (exit 0, 0 failures): flat suite + the 4 new scaffold layers collect and pass together. anyio_mode=auto means async tests need no explicit marker, so that is not a CONVENTIONS gap.
  - Old suite intact: root tests/conftest.py is byte-identical (empty git diff), corpus untouched, flat test_*.py unchanged, and no leak-guard was relocated out of root (the 4 layer conftests are docstring-only stubs that point back to root). Scaffold tests are behavior-named assert-True placeholders explicitly flagged for Phase-2 deletion. No ticket IDs in any new test file or name — the only FEAT-231 references are governance prose in CONVENTIONS.md (Status line + example attributions), which is a governing doc, not a test identifier, so not a section-3 violation.
  - LOW (non-blocking, for Phase 2): (1) section-1 says unit = "No filesystem", but the ledger homes the repo-hygiene/packaging self-tests (squad-ref-hygiene, docfiles, ships-in-wheel) at the unit layer even though they READ static repo/wheel assets. A one-line clarification — "repo-artifact/packaging self-tests read static repo assets and still count as unit; the no-filesystem rule means no squad tmp dir, not never opening a file" — would remove placement ambiguity for those re-homings. (2) When Phase 2 extends the squad-ref-hygiene scan to cover tests/, it must target test identifiers or allowlist the two governance docs (CONVENTIONS.md, COVERAGE_LEDGER.md), which legitimately cite FEAT-231/row numbers — otherwise the extended scan self-flags. Neither blocks Phase 1.
- [2026-07-10T08:14:14Z] Catherine Manager:
  - Reviewer-approved; full suite green (1794+6, --run-slow green too). CONVENTIONS.md confirmed solid enough to author Phase 2 against; package layout safe (import-mode prepend, per-layer __init__ namespaces same-basename files); old suite byte-identical/intact. Two LOW notes carried into Phase 2 (F1: clarify unit-layer 'no filesystem' for repo-artifact self-tests; F2: allowlist CONVENTIONS.md/COVERAGE_LEDGER.md when the ref-hygiene scan extends to tests/). Landing.
<!-- sq:discussion:end -->
