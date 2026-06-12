---
id: TASK-000084
sequence_id: 84
type: task
title: Golden-file tests freezing every --json shape
status: Ready
parent: FEAT-000015
author: tech-lead
priority: high
subentities:
- local_id: ST1
  title: Golden files freezing every --json shape
  status: Todo
  story: US3
created_at: '2026-06-12T15:27:48Z'
updated_at: '2026-06-12T20:45:19Z'
---
<!-- sq:body -->
## Goal
Freeze the JSON shape of every `--json` command with golden-file tests that run in CI, so any shape change is a deliberate, reviewed diff (US3).

## Surface to pin (all current `--json` emitters)
- `list` (_main.py:144), `tree` (206), `inbox` (247), `search` (271), `blocked` (291), `workload` (326), `mine` (360), root `show` (438)
- item `show` (_items.py:104), item `refs` (227)
- `create` (_create.py:79)
- **plus the new emitters from TASK-000082**: `check` and sub-entity `list` — depends on TASK-000082 landing first.

## Approach
- Today there is **no golden/snapshot harness** (tests inline-assert specific fields in tests/test_cli.py). Introduce one: a fixtures dir of expected JSON per command, a helper that runs the command via `CliRunner` against a deterministic seeded squad and compares parsed JSON to the golden file.
- **Determinism is the hard part**: freeze time (`frozen_time` fixture already exists), freeze the global id counter via a fixed seed sequence, and pin the dev-name pool / any random selection. Golden files must be byte-stable across runs or they're worthless.
- Provide an update path (e.g. `UPDATE_GOLDENS=1`) so a deliberate shape change regenerates fixtures — the PR diff then shows the contract change.

## Dependency
Sequence after TASK-000082 (needs the new `check`/sub-entity shapes) and ideally after TASK-000083 (so check's exit code is settled before its shape is pinned).

## Done when
- A golden file exists for every `--json` command and is asserted in CI.
- Changing any shape requires updating its golden in the same PR (documented in the test/README).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 84 add-subtask "<title>"`; track with `sq task 84 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Golden files freezing every --json shape | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Golden files freezing every --json shape

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US3 — As a tool builder, I want the JSON shapes frozen by tests, so that an sq upgrade can't break my parser unannounced
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T20:45:19Z] Catherine Manager:
  - Carry-over from REV-000086 re-review (@reviewer): print_block's JSON shape in _cli/_common.py:76 (used by add-story/add-subtask/add-finding) still emits the path as "file" — the same divergence F1 fixed on the read side. Before cutting goldens, either rename it file→path or document the exception explicitly. Settle this first so the goldens freeze a clean surface.
<!-- sq:discussion:end -->
