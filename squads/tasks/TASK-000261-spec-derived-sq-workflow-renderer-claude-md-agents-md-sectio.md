---
id: TASK-000261
sequence_id: 261
type: task
title: Spec-derived sq workflow renderer + CLAUDE.md/AGENTS.md section (static/dynamic
  split)
status: Draft
parent: FEAT-000210
author: tech-lead
refs:
- TASK-000262:depends-on
- TASK-000257:depends-on
- TASK-000256:depends-on
created_at: '2026-06-30T12:01:07Z'
updated_at: '2026-06-30T12:36:24Z'
---
<!-- sq:body -->
**Slice 5 — spec-derived `sq workflow` renderer + managed CLAUDE.md/AGENTS.md
section, with the static/dynamic split.**
Maps to: US2, US3, AC#3, AC#4.

### Scope
`sq workflow` today renders the fully-static `workflow.md.j2` template (via
`_cli/_workflow_cmd.py::_print_cheatsheet`, passing the hardcoded `TYPE_ALIASES`).
Rewire it to render from the LIVE loaded spec so custom types and their
lifecycles appear, AND make `sq sync` regenerate the managed CLAUDE.md AND
AGENTS.md workflow sections from the same live spec (both backends —
[[verify-claude-artifacts-on-item-type-changes]]).

### The SPLIT (hard requirement — AC#3)
The renderer MUST separate two tiers:
- **Spec-rendered (dynamic)**: the type list, per-type lifecycle string
  (auto-linearized, task 262), and the alias table — these now come from the
  spec, not hardcoded.
- **Static stability-contract prose (NEVER config-editable)**: the FEAT-000013
  sections in workflow.md.j2 — **Ref kinds** table (closed 8-kind vocabulary),
  **Retype**, **Remove vs. Cancel**. These stay literal template prose and must
  NOT become spec-driven. Keep them in a static partial; the dynamic sections
  render around them.

Migrate the alias source here too: `_print_cheatsheet`, `workflow.md.j2`, and
`agents/squads_skill.md.j2` currently consume `TYPE_ALIASES` — switch them to the
spec's per-type aliases (coordinate the retirement with task 257).

### Acceptance
- AC#3: `sq workflow` output includes the custom type's prefix, auto-linearized
  lifecycle, and aliases; the ref-kinds / retype / remove-vs-cancel sections are
  byte-identical static prose.
- AC#4: `sq sync` regenerates CLAUDE.md AND AGENTS.md workflow sections and the
  `squads` skill to include the custom type.
- HARD CONSTRAINT — AC#7/#8: on a non-custom squad, `sq workflow` stdout, the
  CLAUDE.md section, the AGENTS.md section, and the `squads` skill are
  byte-identical to HEAD (task 256 golden green). The static-prose split is what
  makes this provable.

### Files
- src/squads/_cli/_workflow_cmd.py, src/squads/_rendering/templates/workflow.md.j2
  (split into dynamic + static partials), src/squads/_backends/_claude_code/
  _backend.py + _claude_md.py (CLAUDE.md section), src/squads/_backends/
  _agents_md/_backend.py (+ _managed.py), agents/squads_skill.md.j2, tests.

### Dependencies
- Depends on task 262 (lifecycle linearization), task 257 (spec alias source).
- Gated by task 256 golden (the byte-identical proof for built-in squads).
- NOTE the FEAT-211 seam: FEAT-211 (Ready, depends-on FEAT-210) EXTENDS this
  renderer across all status surfaces + custom-status badges + side-states. Keep
  this task's renderer minimal and clean for FEAT-211 to build on; do not absorb
  FEAT-211's status-surface scope.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 261 add-subtask "<title>"`; track with `sq task 261 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-30T12:36:24Z] Catherine Manager:
  - CARRY-FORWARD / known tripwire (from TASK-262, confirmed by Olivia's risk #2): linearize_lifecycle(review machine) yields 'Requested → InReview → ChangesRequested → Rejected (+ Approved)' — Approved is a SIDE state under the greedy-spine heuristic because Rejected is the first unvisited successor of ChangesRequested. But the hand-written PLAYBOOK string + the TASK-256 golden (goldens/skill_body_sq-review.txt) put Approved ON the spine. So the moment this task (and TASK-260) render the review skill/cheatsheet FROM the spec via the linearizer, the review golden BREAKS. Resolve EXPLICITLY, do not silently re-baseline: options — (a) tie-break the spine heuristic toward terminal-Approved-style happy paths; (b) reorder the review machine's transitions so the greedy spine picks Approved; (c) consciously accept the new canonical string and re-bless the golden WITH sign-off (it's a bundled-output change the golden exists to catch — needs explicit approval, not a silent update). Pick one in this wave.
<!-- sq:discussion:end -->
