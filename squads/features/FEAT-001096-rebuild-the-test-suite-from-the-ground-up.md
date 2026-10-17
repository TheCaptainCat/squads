---
id: FEAT-1096
sequence_id: 1096
type: feature
title: Rebuild the test suite from the ground up
status: Draft
author: product-owner
priority: high
refs:
- MILE-1051:targets
description: Replace the 13,800-test suite with a smaller, falsification-checked one;
  parity ledger, per-OS CI targets.
subentities:
- local_id: US1
  title: Behaviour inventory and parity ledger
  status: Todo
- local_id: US2
  title: Falsification audit of the old suite
  status: Todo
- local_id: US3
  title: Conventions, layer policy and risk scaling
  status: Todo
- local_id: US4
  title: Meta guards for volume, duplicate seams and naming
  status: Todo
- local_id: US5
  title: Shared fixtures and goldens for the new suite
  status: Todo
- local_id: US6
  title: Rebuild the integrity core tests
  status: Todo
- local_id: US7
  title: Rebuild the engine, services and CLI tests
  status: Todo
- local_id: US8
  title: Rebuild the backend, skills and rendering tests
  status: Todo
- local_id: US9
  title: Prove parity, then delete the old suite
  status: Todo
- local_id: US10
  title: Measure per-OS CI times and test count
  status: Todo
created_at: '2026-10-17T07:56:25Z'
updated_at: '2026-10-17T07:57:06Z'
---
<!-- sq:body -->
## Problem

The suite has grown from about 6,300 tests at 0.15 to about 13,800 at 0.16. Most of that growth is parametrised position x shape tables, which prove each mechanism against many inputs but largely re-assert the same seam. The cost is now felt where it hurts most:

- Full suite: about 3.5 min locally.
- CI wall time: about 42 min on Windows, 14.5 min on macOS, 11 min on Ubuntu.
- A speed boost is not enough: the operator ruled on 2026-10-17 (TASK-1095) that the suite needs another complete rebuild, from the ground up.

The previous rebuild (FEAT-231) fixed naming, layering, goldens and the 30-second default run for a suite of about 1,100 tests. It did not set a rule against volume, so the suite grew again by a factor of twelve. REV-706 shows the other half of the problem: the suite was green and every static gate clean, yet defects F1, F10, F11 and F12 were each untested. A large suite is not a protective one. The count of tests is not the measure; what breaks when the code breaks is.

## Lessons carried from FEAT-231 and REV-706

- A rebuild without a volume rule regrows. This one carries per-behaviour budgets and a count ceiling that a `tests/meta` guard enforces.
- Per-implemented-branch tests prove the mechanism and miss unconsidered input shapes. The answer is a small boundary table per behaviour, not a bigger one.
- Green suite plus clean gates did not see REV-706's defects: cardinality compared against one status name instead of set membership, an incomplete pointer after reactivation, an untested `--unlink` path. Review attacks shapes, and the rebuild must include them as rows.
- Goldens must pin their whole input (roster, flags, frozen clock) and never be derived from the code under test.
- Test names describe behaviour, with no ticket IDs or process vocabulary.
- Waste patterns to remove: fresh init per table row; the same invariant asserted at unit, service, CLI and integration layers; full cross products where the boundary rows carry the information; instance tests for a rule that is global.

## Principles

1. **Falsification decides existence.** If breaking the code under test does not turn a test red, the test goes. Each kept test is mutation-checked once when written (break the seam, see red).
2. **One composed, user-visible assertion per behaviour.** Assert what an operator or adopter sees, once. No duplicate coverage across the unit, service, CLI and integration layers for a single seam.
3. **One table per behaviour**, holding only the boundary and failure rows. Never a full cross product.
4. **Prefer a `tests/meta` guard** (a rule encoded once) over many instance tests.
5. **Scale layers to risk.** Integrity core (index store, counter, markers, migrations, repair) gets the deepest layering; presentation gets a thin spine.
6. **Coverage parity on hard-won defects.** The old suite's regression classes are listed below and each maps to a ledger entry in the new suite.
7. **New behind old.** The new suite is built beside the old one; the old one is deleted only after parity is proven.
8. **Measured targets**, per OS on CI, plus a test-count target.

## Regression classes to preserve (parity ledger seed)

- Enum identity versus value equality (`is` vs `==`) in retype and type/status comparisons.
- Dangling `.claude` skill pointers after init, sync and migrate.
- Migration edges: forward-only, `sq repair` idempotency, no data loss on schema bump, `sq migrate up` reconcile and corpus-fit.
- `FORCE_COLOR` and ANSI contamination of `--json` output.
- `has_dev` roster gate in generated skills (dev-less versus dev-bearing roster).
- Invalid or unknown vocabulary at the load boundary: corrupt frontmatter type/status, malformed spec, reserved-vocab violations, override-merge conflicts.
- Cardinality and liveness checks use set membership, not one status name (REV-706).
- Reactivation regenerates a complete role pointer; retirement recompiles every compiled region (REV-706).
- Config-integrity gate: `--unlink` abort leaves the item file byte-identical; `--force` never overrides a clause.
- Markdown never behind the index; marker-safe edits; `reject_markers` on every prose input.
- Path traversal guard on `abspath`; global counter allocation only inside a transaction; ID collision and renumber.
- Cross-platform file handling: preserved line endings, escaped squad paths on Windows.
- Write-once guard behaviour.
- Golden renders with pinned inputs (CLAUDE.md section, AGENTS.md section, workflow cheatsheet, template manifest).

The ledger is a living inventory: the first story extends this seed from the actual suite.

## Proposed targets (proposals for the operator, not decided)

| Measure | Now | Proposed |
|---|---|---|
| Test count | about 13,800 | at most 4,000 |
| Local full suite | 3.5 min | at most 60 s |
| CI Windows | 42 min | at most 12 min |
| CI macOS | 14.5 min | at most 6 min |
| CI Ubuntu | 11 min | at most 5 min |
| Default local run (no slow marker) | not set | at most 30 s |

Targets are measured at the same test-job scope as today, on the same runners, with the worker counts recorded. The operator sets the final numbers.

## Scope

- Inventory the current behaviours and regression classes; build the parity ledger.
- Define per-behaviour budgets, a layer policy scaled to risk, and the `tests/meta` guards that enforce them (count ceiling, no full cross products, no duplicate seam, naming).
- Rebuild fixtures and goldens with shared, copy-per-row squad setup.
- Author the new suite beside the old one under a separate root.
- Prove parity: per ledger entry, break the code and show the old and new suites both go red.
- Delete the old suite and re-measure on CI per OS.

## Out of scope

- Product behaviour changes. Production code changes only to remove a test seam need, and then as separate items.
- TASK-1095's speed work as a goal in itself: its profiling and setup-sharing findings are input here, and it is not a substitute.
- New features' own tests while the rebuild runs: they follow the new conventions as each lands.
- CI runner or provider changes beyond what profiling shows.

## Acceptance

1. The old suite is deleted and the new one passes with `uv run --all-extras pytest`; pyright, ruff and `sq check` are clean.
2. Every ledger entry has a named test or `tests/meta` guard, and a recorded proof that breaking the code turns it red.
3. The measured targets above (or the operator's revised numbers) are met on CI per OS, recorded in a comment with the run links.
4. Test count is at or under the agreed ceiling, enforced by a guard.
5. No behaviour is asserted at more than one layer; the seam map shows one owner per behaviour.
6. A contributor document states conventions, layer policy, table rules and the golden protocol.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1096 add-story "As a <role>, I want … so that …"`; track with `sq feature 1096 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Behaviour inventory and parity ledger

<!-- sq:story:US1:body -->
As a maintainer, I want an inventory of every behaviour and regression class the old suite protects, so that the rebuild can prove parity. Acceptance: the ledger lists each class in the feature body plus those found by mapping the old tests; each entry names the seam, the owning layer and the new test or meta guard; the break-the-code proof per entry is recorded; the ledger lives in the repo as a contributor document.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Falsification audit of the old suite

<!-- sq:story:US2:body -->
As a maintainer, I want to know which old tests turn red when the code breaks, so that only protective tests inform the rebuild. Acceptance: for a sampled set per module the seam is broken and the result recorded; the share of tests that stayed green is reported per module; the report names the worst tables and fixtures. No old test is deleted in this story.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Conventions, layer policy and risk scaling

<!-- sq:story:US3:body -->
As a contributor, I want written rules for the rebuilt suite, so that it does not regrow. Acceptance: the document states one composed assertion per behaviour, one owner layer per seam, boundary-and-failure-only tables, the risk tiers (integrity core deepest, presentation thin), the per-behaviour row budget and the golden protocol with pinned inputs; a reviewer applying it to a new test gets one answer.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Meta guards for volume, duplicate seams and naming

<!-- sq:story:US4:body -->
As a maintainer, I want rules encoded once as tests/meta guards, so that volume cannot creep back. Acceptance: guards enforce the test-count ceiling, table row budgets, no ticket IDs or process words in test names, and one owner layer per seam; each guard has a liveness test that fails when its target is removed.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Shared fixtures and goldens for the new suite

<!-- sq:story:US5:body -->
As a test author, I want cheap isolated fixtures, so that setup is not the cost. Acceptance: a squad is built once per module and copied per row, reusing the pattern in tests/_roster_squad.py; goldens pin roster, flags and frozen clock and are reviewed reference renders; setup share of wall time is measured; isolation holds under xdist in any order.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — Rebuild the integrity core tests

<!-- sq:story:US6:body -->
As a maintainer, I want the index store, counter, markers, migrations, repair and path guard tested deepest, so that data loss is caught first. Acceptance: every integrity-core ledger entry has a test or guard that is red when its seam is broken (recorded); migration, repair idempotency, corpus-fit and write-once behaviour are covered once each; no cross-product tables.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->

<!-- sq:story:US7 -->
### US7 — Rebuild the engine, services and CLI tests

<!-- sq:story:US7:body -->
As a maintainer, I want the spec engine, services and CLI covered once per behaviour, so that a failure names one contract. Acceptance: generic-engine behaviour is tested once on a spec, not per type; bad-vocabulary and override-conflict failure rows exist at the load boundary; a thin CLI spine proves exit codes, clean --json without ANSI and generated files; each ledger entry is red when its seam breaks.
<!-- sq:story:US7:body:end -->

#### Discussion

<!-- sq:story:US7:discussion -->
<!-- sq:story:US7:discussion:end -->
<!-- sq:story:US7:end -->

<!-- sq:story:US8 -->
### US8 — Rebuild the backend, skills and rendering tests

<!-- sq:story:US8:body -->
As a maintainer, I want generated artifacts checked by pinned goldens and meta guards, so that pointers and skills cannot drift. Acceptance: no dangling .claude pointers after init, sync and migrate; the has_dev gate is covered with dev-less and dev-bearing rosters held constant; reactivation yields a complete pointer; Windows line-ending and path-escape cases have rows; each entry is red when broken.
<!-- sq:story:US8:body:end -->

#### Discussion

<!-- sq:story:US8:discussion -->
<!-- sq:story:US8:discussion:end -->
<!-- sq:story:US8:end -->

<!-- sq:story:US9 -->
### US9 — Prove parity, then delete the old suite

<!-- sq:story:US9:body -->
As the operator, I want the old suite removed only once the new one is proven, so that nothing hard-won is lost. Acceptance: for every ledger entry the code is broken and both suites are shown red, or the old suite's gap is recorded; the new suite passes uv run --all-extras pytest with pyright, ruff and sq check clean; the old suite is then deleted in one reviewed commit.
<!-- sq:story:US9:body:end -->

#### Discussion

<!-- sq:story:US9:discussion -->
<!-- sq:story:US9:discussion:end -->
<!-- sq:story:US9:end -->

<!-- sq:story:US10 -->
### US10 — Measure per-OS CI times and test count

<!-- sq:story:US10:body -->
As the operator, I want measured results against the proposed targets, so that I can judge the rebuild. Acceptance: one CI run per OS after the old suite is deleted is recorded with wall time, worker count and test count; the numbers are compared to the proposals in the feature body; misses are reported with the --durations profile; TASK-1095's profiling input is cited.
<!-- sq:story:US10:body:end -->

#### Discussion

<!-- sq:story:US10:discussion -->
<!-- sq:story:US10:discussion:end -->
<!-- sq:story:US10:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-17T07:57:06Z] Nina Product:
  - @manager: targeted at MILE-1051 (0.17) for now; the milestone is the operator's call. Targets in the body are proposals for the operator.
<!-- sq:discussion:end -->
