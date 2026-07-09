---
id: FEAT-231
sequence_id: 231
type: feature
title: 'Ground-up test battery: behavior-named, fast, redundancy-pruned'
status: Draft
author: qa
refs:
- FEAT-208
- EPIC-325:depends-on
subentities:
- local_id: US1
  title: Behavior-named tests, not development archaeology
  status: Todo
- local_id: US2
  title: Default test run under 30 seconds
  status: Todo
- local_id: US3
  title: Each invariant asserted once, at the right layer
  status: Todo
- local_id: US4
  title: Coverage ledger preserves previously-caught bugs
  status: Todo
created_at: '2026-06-26T09:33:10Z'
updated_at: '2026-07-09T21:47:55Z'
---
<!-- sq:body -->
## Overview

The current test suite (~1 100 tests, ~4 min wall-clock) has accreted alongside the product. It
works — it catches regressions — but it was never architected; it grew. Three concrete problems
make a clean rebuild worthwhile as a "someday" initiative:

1. **Development-archaeology names.** Tests carry the vocabulary of how features were built:
   `test_layer_b_*` (from an ADR's "Layer A / Layer B" framing), `golden_lock`, `FEAT-000NNN`
   references. A test suite should read as a specification of what the system does, not a diary
   of how it got there. A newcomer — human or agent — should be able to open the test tree and
   learn the contracts, not reverse-engineer an internal roadmap.

2. **Redundancy.** Multiple CLI smoke tests exercise the same narrow path. Golden snapshots
   re-assert the same invariant at different layers. When a contract changes, several tests
   need updating for one logical reason, which erodes confidence in what each test is actually
   protecting.

3. **Slowness drives thrash.** The scale tests own most of the 4-minute budget. When an AI agent
   needs to iterate on a fix, the only safe option is "run the full suite" — and that 4-minute wait
   creates a strong pressure to skip the check entirely, or re-run repeatedly just to see if the
   latest slice passes. Making the default run take seconds removes that pressure at the source.

---

## Motivation: relationship to FEAT-208

The natural trigger for this rebuild is the FEAT-208 de-typing work (collapsing `ItemType` and
`Status` enums to plain strings). That change will invalidate a significant fraction of the
enum-coupled assertions in the current suite. Rather than patching those tests piecemeal — once
during de-typing, and again during any future vocabulary change — the principled moment to rebuild
is immediately after FEAT-208 lands. The new battery is authored against the post-de-typing
contracts from the start, avoiding a double rewrite.

This feature is a deferred "someday" initiative. It is not scheduled and does not block EPIC-206
or any current work. The existing suite remains the safety net until a full replacement is complete
and verified to have coverage parity.

---

## Principles

### 1. Pure, behavior-named tests

Every test file, class, and function name must describe the behavior or contract it verifies — not
the development process that produced it. Concretely:

- No `layer_a` / `layer_b` — those are ADR vocabulary, not system vocabulary.
- No `golden_lock` — that is a technique name, not a behavior name.
- No `FEAT-000NNN` or `ADR-000NNN` in test identifiers. Process belongs in commit history.
- Correct form: `test_item_id_is_globally_unique`, `test_cli_json_output_has_no_ansi_escapes`,
  `test_migration_preserves_ref_kinds_across_schema_versions`.

The rule of thumb: a test name should complete the sentence "This system guarantees that…" without
requiring the reader to know anything about the development timeline.

### 2. Clear layered structure with documented conventions

Four layers, each with a defined scope and a convention document:

| Layer | Scope | Fixture conventions |
|---|---|---|
| `tests/unit/` | Pure functions, models, enum logic — no I/O | No `project` fixture; inputs are in-process values |
| `tests/service/` | `Service` façade + `IndexStore` — filesystem, no CLI | `svc` fixture (tmp_path squad); assert on return values and frontmatter |
| `tests/cli/` | `CliRunner` invocations — public command surface | `project` fixture; assert on exit code, stdout, and generated files |
| `tests/integration/` | Multi-step workflows and migration round-trips | Composites of the above; explicitly cross-layer by design |

A `CONVENTIONS.md` (or docstring in `conftest.py`) must document: naming rules, which fixtures
belong in which layer, how to introduce a new layer, and the golden snapshot protocol (see below).

### 3. Fast by default

- All tests that require generating hundreds of items or exercising O(n) paths must carry a `@pytest.mark.slow` marker.
- `pytest.ini` (or `pyproject.toml`) configures `addopts = "-m 'not slow'"` so the default run
  is the full suite minus scale tests.
- Scale / stress tests are run explicitly: `uv run pytest -m slow` or `uv run pytest --all` (or
  equivalent).
- Target: default run completes in under 30 seconds on a modern laptop. This is the metric.
- The `conftest.py` must strip `FORCE_COLOR` (the harness injects it) so ANSI never leaks into
  assertions.

### 4. Eliminate redundancy

Before any tests are removed, profile the current suite:

1. Measure per-test wall-clock time (`pytest --durations=50`).
2. Map coverage by module (`pytest --cov`).
3. Identify clusters of tests that assert the same invariant at more than one layer (the
   "duplicate invariant" smell).

The principle: each invariant is asserted once, at the lowest layer where it can be meaningfully
tested. A contract about `Item.id` format belongs in a unit test, not in five CLI smoke tests.
CLI tests prove that commands exit cleanly and produce parseable output — not that the underlying
model fields are well-formed (that is already proven at the unit layer).

### 5. Preserve hard-won coverage (critical)

A rewrite must not silently drop coverage for real bugs that have been caught. Before any test is
deleted, characterize what it was protecting. Concrete examples from this project's history that
must have equivalents in the new battery:

- **`is` vs `==` identity bug in `_retype.py`.** The enum identity comparison bug that slipped
  through type-checking and was caught only by a test exercising the retype path. The new suite
  must have a test that would catch this class of bug (value equality for type/status comparisons,
  especially after de-typing).
- **Dangling `.claude` skill pointers.** The `sq sync` / `sq init` path can leave pointer files
  pointing to non-existent skill bodies. There must be a test that verifies no dangling pointers
  after a full init and migrate cycle.
- **Schema/migration edge cases.** Forward-only migration, idempotency of `sq repair`, no data
  loss on `schema_version` bump. The migration round-trip tests are load-bearing.
- **`FORCE_COLOR` / ANSI contamination in `--json` output.** The harness injects `FORCE_COLOR=3`;
  `sq --json` output must be clean JSON regardless. This is easy to regress silently.
- **`has_dev` gate for generated skill rosters.** The roster-dependency in skill generation — if
  no developer role is present, the generated roster must omit dev-specific skills without
  crashing. This is a conditional path that integration tests must cover.

The characterization step (mapping existing tests to bug classes) should produce a "coverage ledger"
stored alongside the new suite so future maintainers understand what each cluster of tests is
protecting and why.

### 6. Disciplined goldens / snapshots

Generated artifacts (CLAUDE.md sections, skill pointer files, rendered templates) need snapshot
tests. The discipline:

- **Pin all inputs.** A golden test must fix the full roster (which roles, which dev), all flags,
  and the frozen clock. No "use whatever the current default is" — that is what made a previous
  near-miss possible where a snapshot was almost anchored to the artifact under test.
- **Source of truth is the input spec, not a prior run's output.** The golden file is derived from
  a known, manually-reviewed reference render. It is updated intentionally (`pytest --snapshot-update`
  or equivalent), never silently.
- **One golden per distinct rendering path.** Two goldens that differ only in one flag value are
  redundant; parameterize them.
- **Goldens live in `tests/goldens/` (or `tests/fixtures/`)**, never inline in the test body
  (readability) and never auto-generated from the code under test without human review.

### 7. Determinism

Every test must be fully deterministic:

- Clock: use the `frozen_time` fixture (inject `clock.now()`) — no `datetime.now()` anywhere in
  test-supporting code.
- Filesystem: tmp_path isolation; no writes outside the fixture directory.
- Environment: strip `FORCE_COLOR`, `NO_COLOR`, and any `SQ_*` env vars in conftest to prevent
  harness bleed.
- Ordering: tests must pass in any order; no shared mutable state between test functions.

---

## Non-goals

- **Not a now-task.** This is a backlog item. No work is scheduled; nothing blocks on it.
- **Not a partial patch.** The existing suite should not be selectively renamed or annotated to
  satisfy these principles — that produces the worst of both worlds (confusion without gain). The
  goal is a clean rebuild, not incremental improvement of the current structure.
- **Does not block EPIC-206.** Current work (workflow spec externalization, FEAT-207 / 208)
  proceeds on the current test suite. This feature is a follow-on, not a blocker.
- **Does not require migrating every current test by hand.** The rebuild starts from a behavior
  inventory, not from porting existing test files one-to-one.

---

## Sequencing

This feature should be scheduled to begin immediately after FEAT-208 lands. The de-typing change
will invalidate a significant portion of enum-coupled test assertions anyway, so that moment is the
principled starting point: rebuild against the de-typed contracts rather than patching twice.

---

## Acceptance criteria

1. The default `uv run pytest` run (no flags) completes in under 30 seconds on a modern laptop
   (scale tests excluded via the `slow` marker and `addopts`).
2. Zero test names, file names, or directory names contain development-process vocabulary:
   `layer_a`, `layer_b`, `golden_lock`, or any `FEAT-`, `TASK-`, `ADR-` reference.
3. A `CONVENTIONS.md` (or equivalent) documents the layer structure, naming rules, fixture
   conventions, and golden snapshot protocol.
4. The coverage ledger (or equivalent characterization artifact) maps the new suite to every
   previously-caught bug class listed in Principle 5, with no gaps.
5. `uv run pytest -m slow` exercises the scale paths and passes.
6. `uv run sq check` is clean; the existing suite remains green until the replacement is complete
   and verified.

---

## User stories

See attached stories on this feature.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 231 add-story "As a <role>, I want … so that …"`; track with `sq feature 231 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Behavior-named tests, not development archaeology |
| US2 | Todo |  | Default test run under 30 seconds |
| US3 | Todo |  | Each invariant asserted once, at the right layer |
| US4 | Todo |  | Coverage ledger preserves previously-caught bugs |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Behavior-named tests, not development archaeology

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a maintainer reading tests, I want behavior-named tests organized by contract so that I can understand system guarantees without reverse-engineering development history (no `layer_b`/`golden-lock`/FEAT-number names).
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Default test run under 30 seconds

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As an AI agent iterating on a fix, I want the default test run to complete in under 30 seconds (slow/scale tests opt-in) so that I can verify correctness without thrashing on a ~4-minute cycle.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Each invariant asserted once, at the right layer

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As a code reviewer, I want each invariant asserted exactly once at the right layer (unit/service/CLI/integration) so that a failing test pinpoints which contract is broken instead of lighting up redundant overlapping tests.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Coverage ledger preserves previously-caught bugs

<!-- sq:story:US4:head -->
**Status:** ⚪ Todo
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
As a future developer introducing a schema change, I want a coverage ledger mapping tests to previously-caught bug classes (retype is/== identity, dangling .claude pointers, FORCE_COLOR ANSI, has_dev gate, migration edges) so that I can verify no hard-won coverage was silently dropped in the rebuild.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-26T14:38:35Z] Catherine Manager:
  - Design principle (Pierre) — the test overhaul follows directly from squads being generic now. The suite was built for the OLD hardcoded-per-type design: exhaustive per-type happy-path coverage, but structurally blind to genericity failure modes (bad vocab was impossible when types were enums). Restructure the battery around FOUR pillars, not per-type re-testing:
    1. Generic-engine tests — the mechanism once (transitions/terminal/parent/flags keyed on a spec), not per type.
    2. Spec-validation + golden — the bundled spec is now a tested artifact (shape + correct flag values).
    3. Thin behavioral spine — a SMALL set proving the configured types behave end-to-end (sq check / retype / skill-gen).
    4. Failure/edge surface (FIRST-CLASS, the part the old suite lacked) — invalid/unknown vocab at the load boundary, malformed spec, reserved-vocab violations, override-merge conflicts, custom-type/status scenarios.
    
    Motivating case = the FEAT-208 F1 miss: a 1247-test suite missed that corrupt frontmatter (an invalid type/status) is silently indexed then crashes sq check — because the bad-vocab path never existed under enums and was never characterized. Genericity opened the failure mode; the battery must cover it. Net: fewer per-type tests, but the genericity earns its own validation/edge pile — budget for it explicitly. Pairs with the FORCE_COLOR / has_dev / is-vs-== entries in the coverage ledger.
- [2026-07-08T08:36:29Z] Catherine Manager:
  - Scheduled into the 0.8 release by op-pierre, sequenced AFTER EPIC-325 (the spec/generic-engine rewrite) — depends-on EPIC-325 added. Rationale: (1) perf — the current ~4-min suite is not acceptable; the rewrite must land a dramatically faster suite (QA to set a concrete wall-clock target, sub-minute goal). (2) quality — the tests are a mess: dev-archaeology names, FEAT-000NNN refs, and redundant CLI smokes, per this feature's own overview.
  - Deferred until EPIC-325 lands so the battery is written against the FINAL generic spec engine (byte-identical-default behaviour, no ItemType/Status enums), not a moving target. Kept OFF the EPIC-325 critical path — the enum/badge golden fallout from FEAT-326/327 is still owned inside those features, not here.
  - Before dispatch (post-EPIC-325): @qa to add a concrete perf-target acceptance criterion and @tech-lead to break this into tasks + re-baseline scope against the shipped engine. Staying Draft until that prose refresh; then Ready.
- [2026-07-08T08:39:38Z] Catherine Manager:
  - Design inputs from op-pierre (scope for the rewrite): (1) Parallelize with pytest-xdist — run '-n auto' across available cores. Largely orthogonal to the rewrite (a config + dep add) and likely the single biggest cheap wall-clock win; the scale/slow tests that dominate today parallelize well. (2) The behavioural WHY: agents re-run the full suite 3-4x back-to-back even when explicitly told not to, repeatedly — prompt discipline alone doesn't hold (cf. the main-loop-owns-the-suite + run-once-to-a-file guidance). So the design goal is to make a re-run CHEAP enough that the thrash is harmless, not to rely on instructions suppressing it. Target framing: sub-minute full run via xdist + marking/excluding slow scale tests by default, full sweep explicit/CI.
- [2026-07-09T09:46:01Z] Pierre Chat:
  - The test-suite rebuild here is a full DESTROY-and-rebuild — all tests get torn down and rebuilt fresh, not incrementally renamed or restructured. So don't fix test naming/structure piecemeal beforehand (e.g. ticket-ID filenames like test_workflow_renderer_261.py); this feature replaces the lot.
- [2026-07-09T21:47:55Z] Pierre Chat:
  - Sequencing decision: the ground-up test-suite rebuild runs LAST — after FEAT-212 and FEAT-281 land. 212/281 reshape the sub-entity/migration/vocab surfaces the suite targets; rebuilding first discards that coverage and collides on the test tree mid-dev. Guardrail on 212/281 dispatch: thin, behavior-named acceptance tests only — FEAT-231 owns exhaustive coverage. The addopts '-m not slow' wall-clock win is folded INTO the rebuild (no piecemeal patching of the old suite).
<!-- sq:discussion:end -->
