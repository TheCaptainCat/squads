---
id: FEAT-000015
sequence_id: 15
type: feature
title: Machine-readable surface audit
status: InProgress
parent: EPIC-000012
author: product-owner
priority: high
description: --json on every read command, documented exit codes, golden-file tests
  freezing the JSON shapes
subentities:
- local_id: US1
  title: As a script author, I want --json on every read command (blocked, mine, workload,
    inbox, check, refs included), so that I can parse squad state without scraping
    tables
  status: Todo
- local_id: US2
  title: As a CI pipeline author, I want documented exit codes, so that I can gate
    builds on commands like sq check
  status: Todo
- local_id: US3
  title: As a tool builder, I want the JSON shapes frozen by tests, so that an sq
    upgrade can't break my parser unannounced
  status: Todo
created_at: '2026-06-10T12:41:11Z'
updated_at: '2026-06-12T15:44:25Z'
---
<!-- sq:body -->
## Problem

We promise stable `--json` shapes at 1.0, but the surface is incomplete and unfrozen: `blocked`,
`mine`, `workload`, `inbox`, `check` and `refs` have no `--json` at all today, exit codes are
undocumented folklore, and nothing in CI would notice if a shape drifted. We cannot freeze what we
have not finished, and we cannot keep a promise no test enforces.

## Value

Scripts, CI gates and orchestration layers (including our own agents) get a complete, reliable
machine interface: every read command parseable, every failure mode a documented exit code, every
shape pinned by a test that fails the build if it moves. This is the "prove it holds" half of the
epic for the CLI surface.

## Scope

- `--json` on every read command — close the gaps: `blocked`, `mine`, `workload`, `inbox`,
  `check`, `refs`.
- A documented exit-code table (success, user error, check failures, schema mismatch, …).
- Golden-file tests freezing the JSON shape of each command, so any change is a deliberate,
  reviewed diff.

## Acceptance

- Every read command accepts `--json` and emits a documented shape.
- Exit codes are documented and asserted in tests.
- Golden files exist for all `--json` outputs and run in CI; changing a shape requires updating a
  golden file in the same PR.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 15 add-story "As a <role>, I want … so that …"`; track with `sq feature 15 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a script author, I want --json on every read command (blocked, mine, workload, inbox, check, refs included), so that I can parse squad state without scraping tables |
| US2 | Todo |  | As a CI pipeline author, I want documented exit codes, so that I can gate builds on commands like sq check |
| US3 | Todo |  | As a tool builder, I want the JSON shapes frozen by tests, so that an sq upgrade can't break my parser unannounced |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a script author, I want --json on every read command (blocked, mine, workload, inbox, check, refs included), so that I can parse squad state without scraping tables

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
**Acceptance:** blocked, mine, workload, inbox, check and refs all accept --json; every read command emits a documented shape.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a CI pipeline author, I want documented exit codes, so that I can gate builds on commands like sq check

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
**Acceptance:** an exit-code table (success, user error, check failure, schema mismatch, …) is documented and each code is asserted in a test.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As a tool builder, I want the JSON shapes frozen by tests, so that an sq upgrade can't break my parser unannounced

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
**Acceptance:** golden files pin the JSON output of every --json command and run in CI; changing a shape requires a deliberate golden-file diff in the same PR.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T15:25:17Z] Catherine Manager:
  - Kicking off per op-pierre's go (2026-06-12). @tech-lead please break this down: tasks parented here, subtasks mapped to US1–US3. Audit current --json coverage first so the gap list in the body is verified against the code.
  - Reminder: shapes you settle here are contract material — leave a deferral comment on FEAT-000013 for anything you freeze.
- [2026-06-12T15:29:04Z] Olivia Lead:
  - @manager broken down. Three tasks parented here, one per user story; FEAT-000015 → InProgress, all tasks → Ready.
  - **TASK-000082 (US1) — close --json gaps.** Important correction: I audited `src/squads/_cli/` and the body's gap list is mostly stale. `blocked`, `mine`, `workload`, `inbox`, and `refs` **already have --json** today. Only **`check`** genuinely lacks it. The real remaining gaps are `check` and the sub-entity `list` commands (stories/subtasks/findings). Much smaller surface than the body implied.
  - **TASK-000083 (US2) — exit-code table.** Documented current reality (0 success / 1 runtime error incl. schema mismatch + check failures / 2 usage error) and tests asserting each. One decision needed before implementation: do check failures deserve a distinct exit code (e.g. 3) vs generic 1? Flagged for @product-owner.
  - **TASK-000084 (US3) — golden-file tests.** No snapshot harness exists yet; introduce one with determinism (frozen time + pinned id counter + pinned dev-name pool) and an UPDATE_GOLDENS path. Sequenced after 082 (needs new shapes) and 083 (settle check's exit code first).
  - **Needs a decision before impl starts:** (a) the check-distinct-exit-code question above; (b) confirm whether repair/docs/workflow/catalog viewers stay table-only or also get --json (I recommend table-only — they aren't script-author state reads). Left the contract obligation as a deferral comment on FEAT-000013.
- [2026-06-12T15:42:53Z] Pierre Chat:
  - Rulings on the two open questions (2026-06-12): check failures get a distinct exit code 3 (1 stays generic error). Scope boundary: repair, docs and workflow stay table-only; the role/skill/operator catalog viewers DO get --json.
  - @tech-lead fold these into TASK-000082/000083; @manager proceeds with implementation.
- [2026-06-12T15:44:25Z] Olivia Lead:
  - @manager breakdown updated to reflect op-pierre's rulings (2026-06-12).
  - TASK-000083 — exit code **3** for check failures is decided (1 stays generic); no open question remains, the task now implements/documents/tests it.
  - TASK-000082 — scope now explicitly lists check --json, the sub-entity list commands (stories/subtasks/findings), AND the role/skill/operator catalog viewers (added by ruling); repair/docs/workflow ruled out-of-scope (table-only).
  - TASK-000084 unchanged — its goldens will pin whatever 082/083 produce. FEAT-000013 deferral updated to reflect both settled points. Ready for implementation.
<!-- sq:discussion:end -->
