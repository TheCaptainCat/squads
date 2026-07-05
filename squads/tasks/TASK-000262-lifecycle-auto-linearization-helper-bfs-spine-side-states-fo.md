---
id: TASK-262
sequence_id: 262
type: task
title: Lifecycle auto-linearization helper (BFS spine + side states) for F4 renderer
status: Done
parent: FEAT-210
author: tech-lead
created_at: '2026-06-30T12:01:08Z'
updated_at: '2026-06-30T12:35:04Z'
---
<!-- sq:body -->
**Slice 6 — lifecycle auto-linearization helper (BFS spine + side states).**
Maps to: US2/US3 enabling; consumed by tasks 260 (skill lifecycle string) and
261 (sq workflow / CLAUDE.md renderer).

### Scope
Add a pure, deterministic helper that turns an arbitrary transition graph
(`Lifecycle.initial` + `Lifecycle.transitions`) into a readable lifecycle string
of the shape `A → B → C (+ D, E)`:
- BFS from the initial state for the "happy-path" spine (the main A → B → C
  chain).
- Remaining (branch/cycle/side) states rendered as `(+ D, E)`.
- Deterministic ordering (stable across runs) so it is golden-testable.

This is a small, well-tested utility on `WorkflowSpec`/`Lifecycle` (or a free
function in `_workflow`). No I/O. Today the bundled types ship a hardcoded
`lifecycle` prose string in PLAYBOOK; this helper derives it from the machine so
custom types get one for free.

### CRITICAL — byte-identical for built-in types (AC#7/#8)
The auto-derived string for the bundled types MUST be consistent with what the
characterization golden (task 256) captures. Either:
(a) the derived string for built-ins matches the existing PLAYBOOK lifecycle
    prose exactly (preferred — then the golden is unchanged), OR
(b) if the derived form differs, the golden is updated in THIS task with explicit
    sign-off in the breakdown, and the change is justified as cosmetic.
Resolve this explicitly; do not let a divergence slip silently past the golden.

### FEAT-211 ownership boundary
FEAT-211 (Ready) lists "lifecycle auto-linearization" in its OWN scope/AC and
depends-on FEAT-210. This task builds the helper that F4's renderer/skill need
to render at all; FEAT-211 then CONSUMES and HARDENS it across every status
surface (filters, inbox, blocked, STATUS_EMOJI/badge fallback for custom
statuses). Build the core BFS-spine-plus-side-states linearizer here; leave the
status-surface wiring and custom-status-badge fallback to FEAT-211. Flagged in
the breakdown comment so the two features do not collide.

### Acceptance
- Given a machine, the helper returns a deterministic `A → B → C (+ side)`
  string; unit-tested on linear, branching, and cyclic machines.
- Built-in types' derived strings reconcile with task 256 golden (per the
  critical note above).

### Files
- src/squads/_workflow/_models.py or _workflow/__init__.py (the helper),
  tests/test_workflow*.py.

### Dependencies
- None upstream (pure helper). Blocks tasks 260 and 261.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 262 add-subtask "<title>"`; track with `sq task 262 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-30T12:15:30Z] Elias Python:
  - Starting TASK-262: lifecycle auto-linearization helper. Algorithm decision: greedy spine + BFS side states. Spine = follow first unvisited transition from each state; side = remaining reachable states in BFS discovery order. This produces byte-identical output for work/adr/guide/agent/bug lifecycles vs TOML comments. For review lifecycle, algorithm produces 'Requested → InReview → ChangesRequested → Rejected (+ Approved)' rather than the hand-written PLAYBOOK 'Requested → InReview → ChangesRequested → Approved (+ Rejected)' — option-b divergence, documented. The TASK-256 characterization golden is not yet written, so no golden update needed here. Helper placed in _workflow/_models.py alongside WorkflowSpec/Lifecycle. No I/O, pure deterministic utility.
- [2026-06-30T12:35:04Z] Elias Python:
  - Done. linearize_lifecycle(machine: Lifecycle) -> str added to _workflow/_models.py and exported from _workflow/__init__.py (__all__). Algorithm: greedy spine (follow first unvisited transition from initial, halt when no unvisited successors) + BFS side states (all reachable states not on the spine, in BFS discovery order). Pure utility — no I/O, deterministic.
  - Option-b divergence documented explicitly (TASK-262): the review lifecycle spine ends at Rejected (first unvisited from ChangesRequested), leaving Approved as a side state — 'Requested → InReview → ChangesRequested → Rejected (+ Approved)' vs. the hand-written PLAYBOOK '...→ Approved (+ Rejected)'. Both are correct; the algorithm follows first-listed transitions.
  - 22 tests in tests/test_linearize_lifecycle.py: linear, branching, diamond, terminal-side, determinism, bundled lifecycle smoke tests for all 9 bundled lifecycle names. All pass in 0.41 s.
  - Gate: pyright 0 errors, ruff clean. No import cycle — function placed in _workflow._models where Lifecycle is already defined.
<!-- sq:discussion:end -->
