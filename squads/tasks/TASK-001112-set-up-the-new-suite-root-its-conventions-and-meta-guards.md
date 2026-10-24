---
id: TASK-1112
sequence_id: 1112
type: task
title: Set up the new suite root, its conventions and meta guards
status: Ready
parent: FEAT-1096
author: tech-lead
assignee: python-dev
priority: high
refs:
- TASK-1111:depends-on
description: New root beside the old one, conventions, naming and owner-layer guards,
  copy-per-row fixtures, golden mechanism.
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
  title: Create the new root with copy-per-row fixtures and the golden mechanism
  status: Todo
  story: US5
- local_id: ST4
  title: Hold the new root to the one-line test docstring rule
  status: Todo
  story: US4
created_at: '2026-10-24T13:42:14Z'
updated_at: '2026-10-24T21:56:20Z'
---
<!-- sq:body -->
Set up the new suite's root, its rules and the guards that enforce them, so the area rebuilds that follow write to one standard. Covers US3 (conventions), US4 (meta guards) and US5 (fixtures and goldens). No old test is deleted here except the `tests/meta` guards that move to the new root.

**Why a separate root and area-by-area increments.** The new suite is built under its own root, `tests_next/` (started by the ledger from the inventory task), with its own `conftest.py`, and both roots run in CI until an area is proven. Each area task then deletes the old files its ledger entries cover in the same increment. Deleting per area, not once at the end, is what keeps CI from getting worse during the rebuild: while both roots run, every new test adds time on top of today's 53 minutes on Windows. Per-area increments also keep each parity proof and each review to one surface. From this task on, new features' own tests are written in `tests_next/` under the new conventions.

**Time arithmetic for the binding targets.** The operator's targets (2026-10-24) are binding: every CI test job under 10 minutes, Windows up to 15. At today's per-test cost (231 ms on Windows, 62 on macOS, 35 on Ubuntu), 15 minutes on Windows allows about 3,900 tests and 12 minutes about 3,100; macOS under 10 minutes allows about 9,700. Windows runs the full suite and is the constraint. There is no test-count ceiling (op-pierre, 2026-10-24): CI time is the only bound. The arithmetic shows where the reduction has to land, and shared-squad fixtures that cut the per-test cost raise that figure.

**Two roots in one run.** Today `tests/` has no `__init__.py`, so its subpackages import as top-level `cli`, `unit`, `meta` and so on, and helpers as `_helpers`; `tests/conftest.py` registers `--run-slow` and the `slow` skip hook. A second root with the same layout would clash on those module names and on the option. The new root must collect beside the old one in a single `uv run --all-extras pytest` with no name clash, one registration of `--run-slow`, and no import from `tests/` (helpers such as `_roster_squad.py` are ported, not imported, because the old root is deleted later).

**Acceptance**

- `tests_next/` is in `testpaths`, runs on all three CI jobs beside the old root, and passes `uv run --all-extras pytest`; pyright (`include` and the tests execution environment), ruff's per-file ignores and the pytest markers cover it as they cover `tests/`; nothing under `tests_next/` imports from `tests/`.
- `tests_next/CONVENTIONS.md` states: one composed user-visible assertion per behaviour; one owner layer per seam; tables of boundary and failure rows only, never a cross product, which reviewers check along with table size; risk tiers (integrity core deepest, presentation thin); the golden protocol with pinned roster, flags and frozen clock; mutation-check each test once when written. A reviewer applying it to a sample new test gets one answer. `CONTRIBUTING.md` points new tests at `tests_next/` and its conventions.
- Guards in `tests_next/meta`, each with a liveness test that fails when its target is removed: no ticket IDs or process words in test names, and one owner layer per seam (a seam map the guard reads). Guards that scan the test tree cover both roots while both exist. The 55 existing guard files (450 tests) move to `tests_next/meta` once the audit shows each protective; one that stays green under a break of its target is fixed or dropped.
- Shared fixtures: a squad built once per module and copied per row, ported from the `tests/_roster_squad.py` pattern; isolation holds under xdist in any order; the setup share of wall time is measured before and after on one module.
- The golden mechanism: pinned inputs (roster, flags, frozen clock), one documented regeneration path, and review as reference renders; nothing derived from the code under test at assertion time. The goldens themselves are ported by the area task that owns them.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1112 add-subtask "<title>"`; track with `sq task 1112 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Write the conventions, layer policy and review checks for the new root

<!-- sq:subtask:ST1:body -->
Write `tests_next/CONVENTIONS.md` from the existing `tests/CONVENTIONS.md` (178 lines, its dedup and golden sections included) and the audit findings: the rules listed in the task body, the risk tiers with which seams sit in each, and what a reviewer checks in a table: its size and that it holds no cross product. Include worked examples from the audit: the `-C` differential reduced to its boundary layouts, and one check table reduced from check by type by level to the boundary rows. Point the tests section of `CONTRIBUTING.md` at the new root and this document.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Add meta guards for test naming and one owner layer per seam

<!-- sq:subtask:ST2:body -->
Add the guards in `tests_next/meta` for naming (no ticket IDs, no process words) and one owner layer per seam, each with a liveness test; guards that scan the test tree cover both roots while both exist. There is no count ceiling and no row-budget guard: table size and cross products are checked in code review. Move the existing `tests/meta` guards (55 files, 450 tests) to the new root once the audit shows each is protective; a guard that stays green under a break of its target is fixed or dropped.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Create the new root with copy-per-row fixtures and the golden mechanism

<!-- sq:subtask:ST3:body -->
Create the rest of `tests_next/`: its `conftest.py`, the build-once-copy-per-row squad fixture (ported from the `tests/_roster_squad.py` pattern, not imported), and the golden mechanism (pinned inputs, one regeneration path). Make both roots collect in one run: no clash on the top-level module names `tests/` uses today (`cli`, `unit`, `meta`, `_helpers` and so on), and `--run-slow` with its skip hook registered once. Wire the root into `testpaths`, CI, pyright (`include` and the tests execution environment), ruff per-file ignores and the pytest markers. Measure the setup share of wall time on one module before and after, and prove isolation under xdist with a shuffled-order run of the new root (no random-order plugin is installed; a collection hook is enough, no new dependency).
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Hold the new root to the one-line test docstring rule

<!-- sq:subtask:ST4:body -->
Hold the new root to the project comment rule from its first file: a test docstring is one line, any other docstring (module, helper, fixture) is one or two sentences, comments do not restate the code, and there are no release versions, ticket ids or history phrases. State the rule in the conventions document. Add a `tests/meta` guard scoped to the new root that enforces the objective parts: test-docstring length, other-docstring length over five non-blank lines, version strings outside migration subjects, and ticket-id shapes. Scan with `ast` plus `tokenize`, whitespace collapsed, and add a liveness row. Old-root files are not swept; they are deleted area by area. This carries REV-956 F19 (1431 test docstrings fail the check on 2026-10-17).
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T19:48:43Z] `tech-lead` Olivia Lead:
  - Re-read for Ready on 2026-10-24: added the two-roots constraint (top-level module names and --run-slow clash today), the pyproject wiring, tests_next/ paths for conventions and guards, the CONTRIBUTING pointer, and goldens ported by their area. Moved to Ready.
- [2026-10-24T21:56:20Z] `tech-lead` Olivia Lead:
  - Added ST4: the new root is held to the one-line test docstring rule, carrying REV-956 F19 from FEAT-1092.
<!-- sq:discussion:end -->
