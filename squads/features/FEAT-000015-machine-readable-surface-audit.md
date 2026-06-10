---
id: FEAT-000015
sequence_id: 15
type: feature
title: Machine-readable surface audit
status: Ready
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
updated_at: '2026-06-11T07:54:53Z'
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
<!-- sq:discussion:end -->
