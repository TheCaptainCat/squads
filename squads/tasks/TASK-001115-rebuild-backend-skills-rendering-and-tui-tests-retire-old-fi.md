---
id: TASK-1115
sequence_id: 1115
type: task
title: Rebuild backend, skills, rendering and TUI tests, retire old files
status: Cancelled
parent: FEAT-1096
author: tech-lead
assignee: python-dev
refs:
- TASK-1112:depends-on
- TASK-1114:depends-on
description: Pointers, skills, has_dev gate, goldens, Windows paths and line endings,
  TUI; parity then deletion.
subentities:
- local_id: ST1
  title: Rebuild pointer and skill generation through init, sync and migrate
  status: Todo
  maps_to: US8
- local_id: ST2
  title: Rebuild goldens, rendering, Windows path rows and the TUI tests
  status: Todo
  maps_to: US8
- local_id: ST3
  title: Prove backend and rendering parity and delete the old files they cover
  status: Todo
  maps_to: US9
created_at: '2026-10-24T13:42:18Z'
updated_at: '2026-10-27T20:16:26Z'
priority: high
---
<!-- sq:body -->
Rebuild the backend, skills, rendering and TUI tests in the new root (US8), then prove parity and delete the old files this area covers (US9). Generated artifacts are checked by pinned goldens and `tests_next/meta` guards rather than per-instance tests. This is the last area increment, after the engine one.

**Measured** (2026-10-24, by filename): about 2,450 old tests in 180 files fall here (claude, agents_md, pointer, skill, backend, sync, golden, render, template, manifest, role, roster, operator, pronoun), plus 77 tests in 11 files under `tests/tui`. `tests/goldens` holds 54 entries, of which this area owns the rendered-artifact ones: the CLAUDE.md and AGENTS.md sections, the `skill_body_sq-*` bodies, the workflow cheatsheet (both forms), and the role, skill and operator shows. The CLI `--json` goldens belong to the engine area. The largest files are `tests/cli/test_content_writes_on_a_generated_role_or_skill_are_refused_cli.py` (143) and `tests/cli/test_pronouns_are_set_and_cleared_through_the_verbs_cli.py` (97). Re-run on 2026-10-26 with the same keyword lists over per-file collected counts: about 2,711 tests in 192 files, 77 TUI tests in 11 files, and still 54 golden entries. That count includes role-named files whose service behaviour (role bases, creation, update) is the engine area's; this area keeps what they write to generated files.

Code added or reshaped since the plan was written that lands here: the pointer and managed files for a role of each base (catalog, template, item-defined), including a resolved description and no `model:` line for an invalid stored model; `sq role add` refreshing the CLAUDE.md and AGENTS.md roster; the role show ending with how to change the role. The VS Code mention hover reading `sq role list --json` is client code tested by the client's own suite and skew canary in `clients/vscode`; the CLI side of that payload is an engine-area golden.

Ledger classes owned here: dangling `.claude` pointers after init, sync and migrate; the `has_dev` gate with dev-less and dev-bearing rosters held constant; reactivation regenerating a complete pointer and retirement recompiling every compiled region (REV-706 F1); escaped squad paths on Windows; golden renders with pinned inputs (CLAUDE.md section, AGENTS.md section, workflow cheatsheet, template manifest); a role created by any path appearing in the managed roster with a complete pointer. Preserved line endings on file writes belong to the integrity-core area, not here.

**Parity proof before deletion.** For every ledger entry of this area, apply its recorded break in a scratch worktree, run only the old test ids the ledger lists and the new test that owns the entry, and record that both go red (or that the old suite had a gap). Only then are the old files covering the area deleted, in this increment, in one reviewed commit. An old file that still covers an entry outside this area stays until the close-out task.

**Acceptance**

- No dangling pointer after init, sync and migrate is one guard over the generated tree, not one test per role.
- The `has_dev` gate has a dev-less and a dev-bearing row with everything else pinned; reactivation yields the same pointer as first creation; retirement recompiles every compiled region.
- Windows path-escape cases have rows; the goldens this area owns pin roster, flags and frozen clock.
- TUI tests run in the new root and are stable under xdist.
- Every entry owned here is red when its seam breaks (recorded in the ledger); the old files covering only this area are deleted; CI time per OS after the increment is recorded and not above the time before it.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1115 add-subtask "<title>"`; track with `sq task 1115 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Rebuild pointer and skill generation through init, sync and migrate

<!-- sq:subtask:ST1:body -->
Rebuild pointer and skill generation through init, sync and migrate: a guard that every generated pointer resolves, the `has_dev` gate on two pinned rosters, reactivation equal to first creation, and retirement recompiling every compiled region. One row per role base (catalog, template, item-defined) for the generated pointer, including the resolved description and the model line (absent for an invalid stored model), and a row that a role created by `sq role add` reaches the CLAUDE.md and AGENTS.md roster.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Rebuild goldens, rendering, Windows path rows and the TUI tests

<!-- sq:subtask:ST2:body -->
Rebuild the rendered-artifact goldens and rendering tests with pinned inputs (CLAUDE.md and AGENTS.md sections, skill bodies, workflow cheatsheet, role, skill and operator shows), the Windows path-escape rows, and the 77 TUI tests, each owning one behaviour.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Prove backend and rendering parity and delete the old files they cover

<!-- sq:subtask:ST3:body -->
Apply each entry's recorded break for this area in a scratch worktree, show the listed old tests and the new owner both red, record it in the ledger, then delete the old files this area alone covers in one reviewed commit. Record CI time per OS after the increment.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T19:48:46Z] `tech-lead` Olivia Lead:
  - Re-read for Ready on 2026-10-24: owns the rendered-artifact goldens only; line endings moved to TASK-1113 (they were in both); retirement recompile added to acceptance; now depends on TASK-1114. Moved to Ready.
<!-- sq:discussion:end -->
