---
id: FEAT-1173
sequence_id: 1173
type: feature
title: CLI surface test suite
status: Done
author: product-owner
refs:
- MILE-1051:targets
- ADR-1172
description: 'Rebuild the tests as in-process CLI surface tests: every command and
  parameter of the bundled tree, guarded coverage.'
subentities:
- local_id: US1
  title: Harness and the two guards
  status: Done
- local_id: US2
  title: Root options
  status: Done
- local_id: US3
  title: Item verbs on the reference type
  status: Done
- local_id: US4
  title: Sub-entity and comment verbs
  status: Done
- local_id: US5
  title: Create
  status: Done
- local_id: US6
  title: Roster groups
  status: Done
- local_id: US7
  title: Squad-wide commands
  status: Done
- local_id: US8
  title: Read commands
  status: Done
- local_id: US9
  title: Override group
  status: Done
created_at: '2026-10-27T21:29:30Z'
updated_at: '2026-10-28T01:03:11Z'
---
<!-- sq:body -->
## Problem

The repository holds only its `tests/meta` guards and shared helpers. The CLI, the product's whole user-facing surface, has no behavioural tests: a change to any command or parameter is caught by nothing but the guards. The previous suite was removed because it grew to about 16,000 tests and about 50 minutes on Windows CI through cross products and the same seam asserted at several layers.

## Scope

Rebuild the test suite as CLI surface tests, as ruled by ADR-1172: every command and every parameter of the bundled tree, run in-process against the engine and the bundled workflow spec, playbook and role catalog, with no project override. This feature defines the deliverable; the rules (one case per parameter, shared registrations tested once on a reference host, the `covers` marker, assertions on what the user sees, layout and names, time bound) are ADR-1172's and are not restated here.

Deliverables:
- the harness changes ADR-1172 names (the `covers` marker, the invoke fixture's cross-check) and the two new `tests/meta` guards, verb-set parity and (command, parameter) coverage;
- `tests/cli/` modules, one per command group, covering every (command, parameter) pair of the tree, hidden parameters included, each with its boundary refusals;
- `--as` covered on every write command, `--json` on every command that declares it.

The stories below split the work by command surface.

## Out of scope

- Unit tests of internals.
- Behaviour under a project override (custom vocabulary); a later run on a second squad build can declare against the same keys.
- One regression test per verified bug (`tests/regressions/`): a separate, later stage.
- Subprocess-only behaviour (console-script entry point, interpreter-start environment latching).
- Whether each bundled lifecycle is well formed: the spec loader's concern.

## Acceptance criteria

- The verb-set parity guard and the coverage guard of ADR-1172 exist in `tests/meta` and pass.
- Every (command, parameter) pair of the bundled tree is declared by a test, with only the named exclusions of the coverage guard, and no marker names a stale pair.
- Each test was mutation-checked when written: the parameter's effect broken, the test seen red, the effect restored.
- No cross-product tables; reviewed for duplicated cases.
- The CI time targets of ADR-1172 hold: every test job under 10 minutes, Windows full suite at most 15, on at least two runs per OS.
- pyright, ruff and `sq check` are clean.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1173 add-story "As a <role>, I want … so that …"`; track with `sq feature 1173 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Harness and the two guards

<!-- sq:story:US1:body -->
## Scope

The foundation the other stories build on.
- Register the `covers` pytest marker and extend the `invoke` fixture to record the (key, parameter) pairs each invocation reached and fail the test at teardown when a declared pair was not reached.
- Add the verb-set parity guard and the coverage guard to `tests/meta`, reading the tree through the existing help-tree helper, with the named exclusion constant.
- Create `tests/cli/` and its shared fixtures, using the module-scoped squad copied per test.

## Acceptance

- Both guards pass on the tree and fail on a seeded verb or parameter that is missing, stale or undeclared.
- A marker naming a pair its test does not run fails that test.
- The guards stay valid under `-k`, `--lf` and xdist.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Root options

<!-- sq:story:US2:body -->
## Scope

`-C`, `--at`, `--version` and the hidden removed `--dir`, covered once each on one ordinary command in `test_root_options.py`, each with its refusals (missing path, malformed time).

## Acceptance

- Every root-callback parameter is declared by a test under the empty key.
- `--install-completion` and `--show-completion` are the only excluded parameters.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Item verbs on the reference type

<!-- sq:story:US3:body -->
## Scope

The generic work-item verbs on the reference type `task` in `test_item_verbs.py`: show, update, status, body, retype, remove and the other verbs the builder mounts, with the options of each, the `status` allowed and refused transition, and the combination cases ADR-1172 names (parent with no-parent, assignee with clear-assignee, add-label with rm-label, set with unset).

## Acceptance

- Every (verb, parameter) pair of the item group is declared once under the `<type>` key.
- Each interacting pair has a test named for the interaction.
- `--as` and `--json` are covered on every verb that declares them.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Sub-entity and comment verbs

<!-- sq:story:US4:body -->
## Scope

Sub-entity verbs on `task subtask` in `test_subentity_verbs.py`, with `--severity` and `--deferred-to` on `review finding`, `--story` resolved against the parent feature; and the comment verbs on the `task` host in `test_comment_verbs.py`, plus one addressing case each for the sub-entity, role, skill and operator hosts.

## Acceptance

- Every sub-entity and comment pair is declared under the `<kind>` and `<host>` keys.
- Comment addressing is tested once per host kind, not the verb parameters again.
- Edit and remove are refused for a comment whose author is someone else.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Create

<!-- sq:story:US5:body -->
## Scope

`sq create <type>` on `task` in `test_create.py`, with `--tag` and `--tech` on `guide`: every option, the required author, the parent rule, ref parsing with and without a kind, and the body from `-m` or `--file`.

## Acceptance

- Every `create` pair is declared; type-specific options are covered on a type that carries them.
- The exclusion of `-m` with `--file` has its own named test.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — Roster groups

<!-- sq:story:US6:body -->
## Scope

The roster groups, one module each: `role`, `dev`, `operator`, `skill`, `memory` and `board`. Covers listing, adding, activating and merged/catalog views for roles, notebook read, write, search and forget for memory, and post, list and clear for the board, with the generated agent-facing files read where the command writes them.

## Acceptance

- Every (command, parameter) pair of the six groups is declared.
- Refusals cover an unknown slug, a duplicate add and a missing required value.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->

<!-- sq:story:US7 -->
### US7 — Squad-wide commands

<!-- sq:story:US7:body -->
## Scope

Commands that act on the whole squad: `init`, `adopt`, `sync`, `repair`, `renumber`, `check`, `import` and the `migrate` group. These read the generated `.claude/` pointers and the managed `CLAUDE.md` and `AGENTS.md` regions directly, as ADR-1172 allows.

## Acceptance

- Every pair of these commands is declared.
- `init` and `sync` assert the generated files; `repair` asserts a rebuilt index through the CLI; `import` asserts its single-transaction behaviour on a refusal.
- A destructive command is only ever run on a copied squad.
<!-- sq:story:US7:body:end -->

#### Discussion

<!-- sq:story:US7:discussion -->
<!-- sq:story:US7:discussion:end -->
<!-- sq:story:US7:end -->

<!-- sq:story:US8 -->
### US8 — Read commands

<!-- sq:story:US8:body -->
## Scope

The read commands: `list`, `tree`, `show`, `search`, `inbox`, `mine`, `blocked`, `graph`, `workload`, `reflog`, `docs`, `workflow` and `ui`'s non-interactive surface, one module per command or closely related pair. Each filter is tested alone; `--sort` is tested with `--json` because they interact.

## Acceptance

- Every pair is declared; filters are not crossed.
- Each case asserts the whole output line or JSON object, not a substring.
<!-- sq:story:US8:body:end -->

#### Discussion

<!-- sq:story:US8:discussion -->
<!-- sq:story:US8:discussion:end -->
<!-- sq:story:US8:end -->

<!-- sq:story:US9 -->
### US9 — Override group

<!-- sq:story:US9:body -->
## Scope

The `override` group in `test_override.py`: scaffold, list, diff, update and drift, run on the bundled spec in a copied squad. The squad-wide overrides of vocabulary stay out of scope; this story covers the command surface only.

## Acceptance

- Every `override` pair is declared, with refusals for an unknown target and a file that does not load.
<!-- sq:story:US9:body:end -->

#### Discussion

<!-- sq:story:US9:discussion -->
<!-- sq:story:US9:discussion:end -->
<!-- sq:story:US9:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-27T21:32:20Z] `op-pierre` Pierre Chat:
  - Break FEAT-1173 into one task per story.
- [2026-10-27T21:37:22Z] `tech-lead` Olivia Lead:
  - Broken into nine tasks, one per story: TASK-1174 (US1, harness and guards) blocks TASK-1175..1182 via depends-on. All Draft, assigned python-dev.
  - Coverage guard during the build: it lands enforced with a named pending list of top-level keys owned by the other eight tasks; each task removes its keys, the last deletes the constant. Stale markers and every non-pending pair are enforced from day one.
  - @manager two points for op-pierre: confirm the pending-list approach; and a parameterless leaf (sync, ui, migrate up, workflow lint) has no pair under ADR-1172 wording, proposed handling is that the guard also requires every leaf key, declared as covers("sync"). Also proposed: keys drop the hidden _addr dispatcher segment, matching the ADR example key "<host> comment edit".
- [2026-10-27T21:38:04Z] `manager` Catherine Manager:
  - Decisions on Olivia's three questions, taken under the operator's delegation to drive FEAT-1173 (op-pierre, 2026-10-27), flagged for his review:
  - 1. Pending list confirmed: the coverage guard lands enforced with a shrinking pending list of top-level keys; an entry with no undeclared pair left fails; the last task deletes the constant.
  - 2. Every leaf command must be declared, a parameterless one as covers("sync") with no parameter: the operator asked for every surface, not only every parameter. ADR-1172 is amended to say so.
  - 3. Keys drop the hidden _addr dispatcher segment; its argument belongs to the parent key, matching ADR-1172's own example key.
- [2026-10-28T01:02:37Z] `manager` Catherine Manager:
  - CI measured on two green runs per OS of the full suite (1384 tests), release/0.17 at 2bdbe578: runs https://github.com/TheCaptainCat/squads/actions/runs/40611745465 and https://github.com/TheCaptainCat/squads/actions/runs/40611757667.
  - Test job / pytest step: Ubuntu 1m17s / 1m05s and 1m09s / 56s; macOS 1m57s / 1m39s and 1m57s / 1m38s; Windows 7m32s / 4m08s and 5m04s / 2m48s. Targets (each job under 10 min, Windows at most 15) met on both runs. Worker count: pytest-xdist -n auto (addopts).
- [2026-10-28T01:03:11Z] `manager` Catherine Manager:
  - Done under the operator delegation to drive FEAT-1173 to the end (op-pierre, 2026-10-27): every story delivered, REV-1198 approved (19 findings Verified or Noted), coverage and verb-parity guards green, CI targets met on two runs per OS. Product defects found while testing are BUG-1183 to BUG-1197 and BUG-1200, left for the regression-test stage.
<!-- sq:discussion:end -->
