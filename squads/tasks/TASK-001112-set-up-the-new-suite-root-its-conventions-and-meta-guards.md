---
id: TASK-1112
sequence_id: 1112
type: task
title: Set up the new suite root, its conventions and meta guards
status: Draft
parent: FEAT-1096
author: tech-lead
assignee: python-dev
priority: high
refs:
- TASK-1111:depends-on
description: New root beside the old one, conventions, volume and naming guards, shared
  fixtures, pinned goldens.
subentities:
- local_id: ST1
  title: Write the conventions, layer policy and review checks for the new root
  status: Todo
  story: US3
- local_id: ST2
  title: Add meta guards for test naming and one owner layer per seam
  status: Todo
  story: US4
- local_id: ST3
  title: Create the new root with shared copy-per-row fixtures and pinned goldens
  status: Todo
  story: US5
created_at: '2026-10-24T13:42:14Z'
updated_at: '2026-10-24T14:34:29Z'
---
<!-- sq:body -->
Set up the new suite's root, its rules and the guards that enforce them, so the area rebuilds that follow write to one standard. Covers US3 (conventions), US4 (meta guards) and US5 (fixtures and goldens). No old test is deleted here.

**Why a separate root and area-by-area increments.** The new suite is built under its own root, `tests_next/`, with its own `conftest.py`, and both roots run in CI until an area is proven. Each area task then deletes the old files its ledger entries cover in the same increment. Deleting per area, not once at the end, is what keeps CI from getting worse during the rebuild: while both roots run, every new test adds time on top of today's 53 minutes on Windows. Per-area increments also keep each parity proof and each review to one surface.

**Time arithmetic for the binding targets.** The operator's targets (2026-10-24) are binding: every CI test job under 10 minutes, Windows up to 15. At today's per-test cost (231 ms on Windows, 62 on macOS, 35 on Ubuntu), 15 minutes on Windows allows about 3,900 tests and 12 minutes about 3,100; macOS under 10 minutes allows about 9,700. Windows runs the full suite and is the constraint. There is no test-count ceiling (op-pierre, 2026-10-24): CI time is the only bound. The arithmetic shows where the reduction has to land, and shared-squad fixtures that cut the per-test cost raise that figure.

**Acceptance**

- `tests_next/` exists, is in `testpaths`, runs on all three CI jobs beside the old root, and passes `uv run --all-extras pytest`.
- `tests/CONVENTIONS.md` (or its successor in the new root) states: one composed user-visible assertion per behaviour; one owner layer per seam; tables of boundary and failure rows only, never a cross product, which reviewers check along with table size; risk tiers (integrity core deepest, presentation thin); the golden protocol with pinned roster, flags and frozen clock; mutation-check each test once when written. A reviewer applying it to a sample new test gets one answer.
- `tests/meta` guards, each with a liveness test that fails when its target is removed: no ticket IDs or process words in test names, and one owner layer per seam (a seam map the guard reads). The 55 existing guard files (450 tests) are moved to the new root after the audit shows them protective.
- Shared fixtures: a squad built once per module and copied per row, reusing `tests/_roster_squad.py`; isolation holds under xdist in any order; the setup share of wall time is measured before and after on one module.
- Goldens regenerated from pinned inputs and reviewed as reference renders; none derived from the code under test at assertion time.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1112 add-subtask "<title>"`; track with `sq task 1112 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Write the conventions, layer policy and review checks for the new root

<!-- sq:subtask:ST1:body -->
Rewrite the contributor conventions for the new root from the existing `tests/CONVENTIONS.md` (178 lines, its dedup and golden sections included) and the audit's findings: the rules listed in the task body, the risk tiers with which seams sit in each, and what a reviewer checks in a table: its size and that it holds no cross product. Include worked examples from the audit: the `-C` differential reduced to its boundary layouts, and one check table reduced from check by type by level to the boundary rows.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Add meta guards for test naming and one owner layer per seam

<!-- sq:subtask:ST2:body -->
Add the `tests/meta` guards for naming (no ticket IDs, no process words) and one owner layer per seam, each with a liveness test. There is no count ceiling and no row-budget guard: table size and cross products are checked in code review. Move the existing meta guards to the new root once the audit shows each is protective; a guard that stays green under a break of its target is fixed or dropped.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Create the new root with shared copy-per-row fixtures and pinned goldens

<!-- sq:subtask:ST3:body -->
Create `tests_next/` with its own `conftest.py`, the shared build-once-copy-per-row squad fixture (reusing `tests/_roster_squad.py`) and the pinned goldens. Wire the root into `testpaths` and CI beside the old one. Measure the setup share of wall time on one module before and after, and prove isolation under xdist with a random order run of the new root.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
