---
id: FEAT-1096
sequence_id: 1096
type: feature
title: Rebuild the test suite from the ground up
status: Cancelled
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
updated_at: '2026-10-27T20:16:28Z'
---
<!-- sq:body -->
## Problem

The suite has grown from about 6,300 tests at 0.15 to about 13,800 at 0.16, and to 15,636 on `release/0.17` (2026-10-26). Most
of that growth is parametrised position x shape tables, which prove each 
mechanism against many inputs but largely re-assert the same seam. The cost is 
now felt where it hurts most:

- Full suite: about 3.5 min locally at 0.16.
- CI pytest step on the 0.16 suite: 53 min on Windows, 14 on macOS and 8 on Ubuntu on the 2026-10-17 push to `main`; 39 to 59 min on Windows, 11 to 13 on macOS and 15 to 16 on Ubuntu on the two 2026-10-24 pull-request runs. `release/0.17` has no CI run yet.
- A speed boost is not enough: the operator ruled on 2026-10-17 that the suite 
needs another complete rebuild, from the ground up.

The previous rebuild (FEAT-231) fixed naming, layering, goldens and the 
30-second default run for a suite of about 1,100 tests. It did not set a rule 
against volume, so the suite grew again by a factor of twelve. REV-706 shows the
other half of the problem: the suite was green and every static gate clean, yet 
defects F1, F10, F11 and F12 were each untested. A large suite is not a 
protective one. The count of tests is not the measure; what breaks when the code
breaks is, and the cost is measured in CI wall time.

## Lessons carried from FEAT-231 and REV-706

- A rebuild without a volume rule regrows. This one carries CI time targets that 
bind the total, and code review checks table size and cross products.
- Per-implemented-branch tests prove the mechanism and miss unconsidered input 
shapes. The answer is a small boundary table per behaviour, not a bigger one.
- Green suite plus clean gates did not see REV-706's defects: cardinality 
compared against one status name instead of set membership, an incomplete 
pointer after reactivation, an untested `--unlink` path. Review attacks shapes, 
and the rebuild must include them as rows.
- Goldens must pin their whole input (roster, flags, frozen clock) and never be 
derived from the code under test.
- Test names describe behaviour, with no ticket IDs or process vocabulary.
- Waste patterns to remove: fresh init per table row; the same invariant 
asserted at unit, service, CLI and integration layers; full cross products where
the boundary rows carry the information; instance tests for a rule that is 
global.

## Principles

1. **Falsification decides existence.** If breaking the code under test does not
turn a test red, the test goes. Each kept test is mutation-checked once when 
written (break the seam, see red).
2. **One composed, user-visible assertion per behaviour.** Assert what an 
operator or adopter sees, once. No duplicate coverage across the unit, service, 
CLI and integration layers for a single seam.
3. **One table per behaviour**, holding only the boundary and failure rows. 
Never a full cross product; reviewers check table size and cross products.
4. **Prefer a `tests/meta` guard** (a rule encoded once) over many instance 
tests.
5. **Scale layers to risk.** Integrity core (index store, counter, markers, 
migrations, repair) gets the deepest layering; presentation gets a thin spine.
6. **Coverage parity on hard-won defects.** The old suite's regression classes 
are listed below and each maps to a ledger entry in the new suite.
7. **New behind old, retired area by area.** The new suite is built beside the 
old one; each area's old tests are deleted as soon as that area's parity is 
proven, so CI never gets slower than today.
8. **Time is the bound.** The CI time targets below are the only limit on volume;
there is no test-count ceiling.

## Regression classes to preserve (parity ledger seed)

- Enum identity versus value equality (`is` vs `==`) in retype and type/status 
comparisons.
- Dangling `.claude` skill pointers after init, sync and migrate.
- Migration edges: forward-only, `sq repair` idempotency, no data loss on schema
bump, `sq migrate up` reconcile and corpus-fit.
- `FORCE_COLOR` and ANSI contamination of `--json` output.
- `has_dev` roster gate in generated skills (dev-less versus dev-bearing 
roster).
- Invalid or unknown vocabulary at the load boundary: corrupt frontmatter 
type/status, malformed spec, reserved-vocab violations, override-merge 
conflicts.
- Cardinality and liveness checks use set membership, not one status name 
(REV-706).
- Reactivation regenerates a complete role pointer; retirement recompiles every 
compiled region (REV-706).
- Config-integrity gate: `--unlink` abort leaves the item file byte-identical; 
`--force` never overrides a clause.
- Markdown never behind the index; marker-safe edits; `reject_markers` on every 
prose input.
- Path traversal guard on `abspath`; global counter allocation only inside a 
transaction; ID collision and renumber.
- Cross-platform file handling: preserved line endings, escaped squad paths on 
Windows.
- Write-once guard behaviour.
- Golden renders with pinned inputs (CLAUDE.md section, AGENTS.md section, 
workflow cheatsheet, template manifest).
- CR leaking into reads from a verbatim read: readers (show, `--json` bodies, the template-body guard) see LF; only the write seam sees the on-disk bytes.
- Line endings conformed only at the write seam: every writer of an item, skill or managed-region file goes through it, and untouched lines keep their endings in mixed-ending files with duplicate lines, in linear time.
- Block outside its container: a lost container is restored around the surviving blocks on every write path, adds included, never inside another region and never with a second heading; prose between blocks or a half-present marker pair refuses with one error line, not a traceback.
- Role base resolution from stored facts: the base comes from what the item stores, an existing item is found before the catalog is consulted, and origin follows a change of base.
- One validated accessor per stored value: a value outside its whitelist reads as unset on every resolution path and is reported by `sq check`, never filtered on one path and shown on another.
- A migration step must be safe to re-apply: it drops only what it can tell is residue, keeps and reports a differing operator setting, reports every value it drops, and leaves no legacy mirrored value winning as a setting.
- A lint relaxation that hides adopter errors: an exemption covers only inherited keys the override neither writes nor enters; an adopter's own unreachable state still fails, and lint and load apply the same rule.
- Tests that tolerate a whole error class instead of naming the expected set: a helper or exit-code switch that ignores every finding of a rule hides a regression of that rule.
- A refused command writes nothing: resolution and validation run before the first write, on fresh and forced runs.
- Lookups read the squad's merged document, not the bundled one, on every path to them, interactive prompts included.
- A second creation path that bypasses the one creation seam (an import creating a roster entry with no base) is refused or routed through it.
- Required text rejects whitespace-only values and malformed stored names, at the write and in `sq check`; reserved slugs are refused wherever a slug enters, grammar-only checks included.
- Bundled documents agree with each other (every bundled guide subject is held by a bundled role or template), held by a guard rather than only by goldens.
- An accepted flag has an effect: `--as` implies an attributed reflog line, every verb that writes a reflog line takes `--as`, and a no-op given differing values refuses instead of reporting success.
- Messages and remedies state the set the rule actually checks and name a command that works in the state where they are shown.
- A client moving to another payload keeps the filter the old one applied (an archived role is not a mention target), and the skew canary pins the exact key set of each payload the client reads.
- Test preconditions do not depend on the host terminal or platform (forced colour on a Windows pipe, `TERM=dumb`).
- An unlocked reader built from two scans reports a concurrent rename as a duplicate id; a finding drawn from two reads is confirmed before it is reported.
- Each spec document is read once per invocation on every command, `init` included.

The ledger is a living inventory: the first story extends this seed from the 
actual suite.

## CI time targets

| Measure | 2026-10-17 push to `main` | 2026-10-24 pull-request runs | Target |
|---|---|---|---|
| CI pytest step, Ubuntu | 8 min | 15 to 16 min | under 10 min |
| CI pytest step, macOS | 14 min | 11 to 13 min | under 10 min |
| CI pytest step, Windows | 53 min | 39 to 59 min | up to 15 min |

All three runs test the 0.16 suite (13,816 tests collected; run 39020459902, and runs 40116628420 and 40116638095 from two dependency-bump pull requests, whose second Windows leg failed one TUI test). The spread between the two same-day runs is the runner noise any later comparison has to allow for. Worker counts are not in the `-q` logs.

Every CI test job stays under 10 minutes; Windows may take up to 15. Windows CI 
runs the full suite, not a platform subset. Targets are measured at the same 
test-job scope as today, on the same runners, with the worker counts recorded. 
The test count is reported but not capped: these times are the only bound.

Each target is judged on at least two CI runs per OS: it is met on an OS when every one of those runs is under it. One run alone neither meets nor misses a target, given the 39 to 59 min spread between two same-day Windows runs of one suite.

## Scope

- Inventory the current behaviours and regression classes; build the parity 
ledger.
- Define a layer policy scaled to risk and the `tests/meta` guards that enforce 
it (no duplicate seam, naming). Reviewers check table size and cross products.
- Rebuild fixtures and goldens with shared, copy-per-row squad setup.
- Author the new suite beside the old one under a separate root.
- Prove parity area by area: per ledger entry, break the code and show the old 
and new suites both go red, then delete that area's old tests.
- Re-measure on CI per OS once the last area is retired.

## Out of scope

- Product behaviour changes. Production code changes only to remove a test seam 
need, and then as separate items.
- Speed work as a goal in itself; profiling findings feed the baseline and 
setup-sharing design here.
- New features' own tests while the rebuild runs: they follow the new 
conventions as each lands.
- CI runner or provider changes beyond what profiling shows.
- The VS Code client's TypeScript tests (`clients/vscode`): they keep their own suite and are not rebuilt here.

## Acceptance

1. The old suite is fully deleted, area by area, and the new one passes with 
`uv run --all-extras pytest`; pyright, ruff and `sq check` are clean.
2. Every ledger entry has a named test or `tests/meta` guard, and a recorded 
proof that breaking the code turns it red.
3. Every CI test job runs in under 10 minutes, and Windows, running the full 
suite, in at most 15 minutes; the measurements are recorded in a comment with 
the run links.
4. No behaviour is asserted at more than one layer; the seam map shows one owner
per behaviour.
5. A contributor document states conventions, layer policy, table rules and the 
golden protocol.
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
As a contributor, I want written rules for the rebuilt suite, so that it does 
not regrow. Acceptance: the document states one composed assertion per 
behaviour, one owner layer per seam, boundary-and-failure-only tables, the risk 
tiers (integrity core deepest, presentation thin), that reviewers check table 
size and cross products, and the golden protocol with pinned inputs; a reviewer 
applying it to a new test gets one answer.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Meta guards for volume, duplicate seams and naming

<!-- sq:story:US4:body -->
As a maintainer, I want rules encoded once as tests/meta guards, so that 
duplication cannot creep back. Acceptance: guards enforce no ticket IDs or 
process words in test names and one owner layer per seam; there is no row-budget
or test-count guard, since table size and cross products are checked in code 
review and the CI time targets bound the total; each guard has a liveness test 
that fails when its target is removed.
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
As the operator, I want each area's old tests removed as soon as that area is 
proven, so that nothing hard-won is lost and CI never gets slower than today. 
Acceptance: for every ledger entry in an area the code is broken and both suites
are shown red, or the old suite's gap is recorded; only then that area's old 
tests are deleted, in a reviewed commit per area; when the last area is retired 
the old root is gone, and the new suite passes uv run --all-extras pytest with 
pyright, ruff and sq check clean.
<!-- sq:story:US9:body:end -->

#### Discussion

<!-- sq:story:US9:discussion -->
<!-- sq:story:US9:discussion:end -->
<!-- sq:story:US9:end -->

<!-- sq:story:US10 -->
### US10 — Measure per-OS CI times and test count

<!-- sq:story:US10:body -->
As the operator, I want measured results against the CI time targets, so that I 
can judge the rebuild. Acceptance: one CI run per OS after the last area is 
retired is recorded with wall time, worker count and test count; every test job 
is under 10 minutes and Windows, running the full suite, is at most 15; misses 
are reported with the --durations profile; the CI baseline measured before the 
rebuild is cited.
<!-- sq:story:US10:body:end -->

#### Discussion

<!-- sq:story:US10:discussion -->
<!-- sq:story:US10:discussion:end -->
<!-- sq:story:US10:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-17T07:57:06Z] `product-owner` Nina Product:
  - @manager: targeted at MILE-1051 (0.17) for now; the milestone is the operator's call. Targets in the body are proposals for the operator.
- [2026-10-24T13:31:04Z] `op-pierre` Pierre Chat:
  - Scheduled in 0.17: the rebuild starts right after the current queue (TASK-1110, TASK-1098, TASK-1103 to TASK-1107) and before the daemon work, so the daemon's tests are written under the new rules.
- [2026-10-24T13:33:48Z] `op-pierre` Pierre Chat:
  - Targets: a test pipeline over 10 minutes is not acceptable (50 minutes today is intolerable). Every CI test job stays under 10 minutes; Windows may take up to 15.
- [2026-10-24T13:44:14Z] `tech-lead` Olivia Lead:
  - - Planned as six Draft tasks: TASK-1111 inventory, ledger, audit and CI baseline (qa, with devops on the baseline); TASK-1112 new root, conventions, guards and fixtures; TASK-1113, TASK-1114 and TASK-1115 one area increment each (python-dev); TASK-1116 close-out and per-OS measurement (devops).
    - Measured on 2026-10-24: 13,816 tests, 4,975 functions, 9,605 parametrised rows. CI pytest step on the 2026-10-17 main push: Windows 53 min, macOS 14, Ubuntu 8, which is about 231, 62 and 35 ms per test. Windows is the binding constraint: under 15 min means about 3,900 tests at today's per-test cost.
    - TASK-1111 depends on the whole queue named on 2026-10-24 (TASK-1110, TASK-1098, TASK-1103 to TASK-1107), because those tasks are not chained to each other.
    - @manager, the operator still has to decide: the count ceiling (3,500 proposed), whether old files are deleted per area (planned that way, so CI never gets slower than today; US9 says one deletion commit at the end and would need rewording), whether Windows runs the full suite or a platform subset, what happens to TASK-1095, and what the new root is called and whether it becomes tests/ at the end.
- [2026-10-24T14:09:04Z] `op-pierre` Pierre Chat:
  - No numeric test-count ceiling: the CI time targets are the only bound.
  - Old tests are deleted area by area, as soon as that area's parity is proven.
  - Windows CI runs the full suite.
  - TASK-1095 is cancelled; its profiling is covered by TASK-1111 ST3.
- [2026-10-24T14:10:36Z] `tech-lead` Olivia Lead:
  - - Applied op-pierre's 2026-10-24 rulings: no count ceiling (removed from TASK-1112 and TASK-1116), area-by-area deletion kept, Windows runs the full suite (TASK-1111 ST3, TASK-1116), TASK-1095's profiling carried by TASK-1111 ST3, and the new root is `tests_next/`, renamed to `tests/` in TASK-1116 ST1. The per-table row budget guard stays in TASK-1112 ST2, because cross-product tables are where the growth came from.
- [2026-10-24T14:33:40Z] `op-pierre` Pierre Chat:
  - No row-budget guard either: an oversized or cross-product table is for the review to catch, not a tests/meta guard.
- [2026-10-24T14:34:30Z] `tech-lead` Olivia Lead:
  - - Applied op-pierre's ruling: no row-budget guard. I removed it from TASK-1112 (body, ST1, ST2) and TASK-1113; reviewers now check table size and cross products. TASK-1112 ST2 keeps only the naming and one-owner-layer guards.
- [2026-10-26T08:51:56Z] `op-pierre` Pierre Chat:
  - The test rebuild stays in 0.17 and runs last in the release, after the other 0.17 work.
- [2026-10-26T09:17:32Z] `op-pierre` Pierre Chat:
  - Show me the rebuild plan before any dev starts on it.
- [2026-10-26T09:19:32Z] `op-pierre` Pierre Chat:
  - Plan validated. Refresh it against current HEAD (counts, fresh CI figures, this week's regression classes in the ledger seed, new code mapped to the area tasks) before any dev starts; I want to see the refreshed plan.
- [2026-10-26T09:30:49Z] `tech-lead` Olivia Lead:
  - @manager Plan refreshed against `release/0.17` 9b79babd (2026-10-26). Principles, targets and the task breakdown are unchanged.
    
    - **Counts** (`pytest --collect-only -n0`, one directory at a time): 15,636 tests in 821 files, up from 13,931 on 2026-10-24. By directory: service 5,388, cli 4,451, unit 3,979, integration 1,243, meta 492, tui 77, scale 6. Most of the growth is in `tests/cli` (+1,068). The new large tables are the damaged-override table (402), load-once (145) and `--as` (100).
    - **CI** (`gh run view`): `release/0.17` has never run the `test` workflow, because it triggers only on `main`. The latest runs are two 2026-10-24 dependency-bump PRs on the 0.16 suite: Windows 39 and 59 min, macOS 11 and 13, Ubuntu 15 and 16. Run 40116638095 failed one TUI test on Windows. At those per-test costs, the 0.17 suite projects to about 44 to 66 min on Windows and 17 to 18 on Ubuntu. That is inferred, not run. FEAT-1096, TASK-1111, TASK-1112 and TASK-1116 now cite both runs.
    - **Ledger seed:** 19 classes added to the FEAT-1096 body, drawn from REV-1155 to REV-1161 and the bugs BUG-1030, 1045, 1065, 1075, 1141, 1144 and 1154.
    - **Mapping:**
      - Line endings and container restore go to a new TASK-1113 ST4. The 0.16 to 0.17 role step goes to TASK-1113 ST2.
      - Role bases, templates, creation (`role add`, `dev add`, `init`/`adopt --roles`, the import refusal) and update go to a new TASK-1114 ST7.
      - TASK-1114 ST1 gets the lifecycle drop and `Noted` to `Deferred`, ST2 the new check rules, ST3 the role-list golden and the load-once guard, ST5 `--as` and the `view` op.
      - TASK-1115 ST1 gets pointers per role base and the managed roster after `role add`. The VS Code hover stays with the client suite.
    
    Flags, for a decision, not edited:
    1. TASK-1111 has no depends-on for the 0.17 work still open (TASK-1127, TASK-1148, TASK-1153), although the rebuild is meant to run last. I recommend adding them.
    2. BUG-1154 is open, and TASK-1114 ST2 assumes its fix. I recommend fixing it before TASK-1111 starts; otherwise the ledger records it as a gap.
    3. No CI baseline exists for 0.17. I recommend pulling TASK-1111 ST3's on-demand trigger forward as a small devops change, so we get one run per OS now.
    4. The same suite on the same day took 39 and 59 min on Windows. I recommend judging the targets on at least two runs per OS; TASK-1116 ST2 records one.
    5. FEAT-1096 does not say whether the client's TypeScript tests are in scope. I recommend adding them to Out of scope explicitly.
- [2026-10-26T14:03:08Z] `op-pierre` Pierre Chat:
  - Validated Olivia's recommendations 1, 3, 4 and 5: the rebuild depends on the open 0.17 work; add a manual CI trigger for a 0.17 baseline; judge the targets on two runs per OS; client TypeScript tests are out of scope.
- [2026-10-27T20:16:21Z] `op-pierre` Pierre Chat:
  - 2026-10-27: test-suite rebuild cancelled. tests/ and tests_next/ deleted; only the repository meta guards are kept, moved to tests/meta.
<!-- sq:discussion:end -->
