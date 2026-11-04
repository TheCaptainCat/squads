---
id: FEAT-1288
sequence_id: 1288
type: feature
title: Re-exporting private packages
status: Done
author: product-owner
refs:
- ADR-1287:implements
description: Every private package's init re-exports the names other packages import,
  per ADR-1287; codebase swept, docs corrected.
subentities:
- local_id: US1
  title: Guard and package sweep
  status: Todo
- local_id: US2
  title: Documentation corrected
  status: Todo
created_at: '2026-11-04T11:05:52Z'
updated_at: '2026-11-04T15:17:34Z'
priority: medium
---
<!-- sq:body -->
Private packages re-export the names other packages import, as ADR-1287 rules, so a contributor writes one import statement per package and no importer tracks a package's internal file layout. The whole codebase is swept to the rule and the documents that stated the old one are corrected.

**Outcome for contributors.**

- An importer names the package, not the defining module: one import line per package, and moving code between modules of a package changes only that package's `__init__`.
- Each package's re-exports are its stated internal surface, held exact by the guard in `tests/meta`.
- The guards that hold the rule fail on an init that carries code, a reach into another package's module, a reach out to an enclosing init, or a re-export no outside module uses.
- Startup does not regress beyond run-to-run noise: each sweep step is benchmarked against the previous build with `scripts/bench_local_mode.py`, and a step that moves it stops for a decision.

**Acceptance criteria.** The rule, the guard's four checks, the cycle analysis, the startup limits and the sweep order are in ADR-1287 and are not restated here.

- The ADR-1287 rule is in force through the guard in `tests/meta/test_package_import_edges_match_the_recorded_table.py`, with no package left in the transitional pending set.
- `_models/_config.py` is `squads/_config.py`, `_cli/__init__` code is `_cli/_app.py`, and `_workflow/__init__` code is `_workflow/_bundled.py`; the edge table is updated for the new `_config` node.
- The five guards that match a module inside a package resolve re-exports through one shared resolver in `tests/_import_scan.py`, and none passes vacuously.
- CLAUDE.md, CONTRIBUTING.md, GUIDE-79, docs/internals.md, docs/stability.md and the README conventions paragraph state the new rule (ADR-1287, section 5).
- The bench shows no startup regression beyond noise.
- pyright, ruff, `tests/meta`, the full suite and `sq check` are green.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1288 add-story "As a <role>, I want … so that …"`; track with `sq feature 1288 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Guard and package sweep

<!-- sq:story:US1:body -->
Land the guard and sweep every private package to the rule, in the order of ADR-1287 section 6.

- The guard enforces init shape, no reach-in, no reach-out and exact surface (ADR-1287 section 4), plus per-level acyclicity, with a transitional pending set that shrinks as packages are swept and is deleted at the end.
- The shared re-export resolver in `tests/_import_scan.py` is used by the five module-matching guards.
- `_config`, `_cli/_app` and `_workflow/_bundled` are moved; `ops` and `markers` are re-exported as namespaces; every other cross-package module import is a name import.
- Each package step rewrites the init, every outside import in `src` and the test name-imports, and passes pyright, ruff, `tests/meta`, the full suite and `sq check`.
- Each step is benchmarked with `scripts/bench_local_mode.py` against the previous build; a result beyond noise stops for a decision.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Documentation corrected

<!-- sq:story:US2:body -->
Correct every document that states the old no-re-export rule, as listed in ADR-1287 section 5.

- CLAUDE.md: module privacy paragraph, the `_models/`, `_workflow/` and `_cli/` lines, the `LAZY_GROUPS` sentence and the renderer guard sentence.
- CONTRIBUTING.md: the private layout bullet and the lazy command table sentence.
- GUIDE-79: cross-cutting conventions point to ADR-1287.
- docs/internals.md, docs/stability.md (Tier 4) and the README conventions paragraph, written by the technical writer for adopters, with no internal references; no import path becomes public API.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-04T15:17:34Z] `manager` Catherine Manager:
  - Done: TASK-1289 delivered, REV-1291 approved.
<!-- sq:discussion:end -->
