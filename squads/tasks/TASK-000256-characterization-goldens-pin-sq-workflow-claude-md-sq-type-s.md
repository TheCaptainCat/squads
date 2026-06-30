---
id: TASK-000256
sequence_id: 256
type: task
title: 'Characterization goldens: pin sq workflow / CLAUDE.md / sq-<type> skill output'
status: Done
parent: FEAT-000210
author: tech-lead
created_at: '2026-06-30T12:00:58Z'
updated_at: '2026-06-30T12:14:20Z'
---
<!-- sq:body -->
**Slice 0 — characterization goldens (GATING, authored FIRST against HEAD).**
Maps to: AC#7, AC#8 (the proof that non-custom squads see byte-identical
behaviour/output). This is the guard the rewire tasks (257, 260, 261) run under.

Per the FEAT-220/REV-000230 process rule and [[pin-roster-when-diffing-generated-skills]]:
the characterization golden MUST be authored and merged FIRST, against HEAD,
as a passing gating test — BEFORE any rewire. Do not leave the proof as a
trailing task.

### Scope
Pin TODAY's rendered output for the three artifacts the rewire will touch, with
ALL inputs frozen so the comparison is deterministic:
- `sq workflow` / `sq workflow show` stdout (the cheatsheet).
- The managed CLAUDE.md workflow section AND the AGENTS.md workflow section
  emitted by `write_managed` (both backends — see
  [[verify-claude-artifacts-on-item-type-changes]]).
- Every generated `sq-<type>` skill body for the bundled types (the
  `_write_item_skills` output).

### Pin ALL inputs (mandatory)
- **Roster**: hold it constant — pin a fixed roster (the dev-bearing default) so
  the `has_dev` gate in `_write_item_skills` does not flip and produce a
  false-positive diff. See [[pin-roster-when-diffing-generated-skills]].
- **Clock**: freeze via the `frozen_time` fixture.
- **Flags / FORCE_COLOR**: conftest already strips FORCE_COLOR; assert no ANSI in
  captured output (see [[force-color-harness-gotcha]]).
- Use the existing `goldens/` fixture convention (see tests/goldens, and the
  pattern in tests/test_spine_characterization.py and test_golden_json.py).

### Acceptance
- New gating test(s) capture the three artifacts' current output as golden
  fixtures and assert byte-equality on a fresh bundled-spec squad.
- Green against HEAD with no production code change.
- The test is structured so tasks 257/260/261 can re-run it unchanged after their
  rewire and it stays green (that is the AC#7/#8 enforcement).

### Files
- tests/ (new characterization test module), tests/goldens/ (new fixtures).

### Dependencies
- None — this is first. Blocks 257, 260, 261 (the byte-identical rewires).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 256 add-subtask "<title>"`; track with `sq task 256 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-30T12:14:20Z] Mara Tester:
  - Characterization goldens authored and green. New test file: tests/test_golden_rendered_output.py. New golden fixtures (10 .txt files under tests/goldens/).
  - What is pinned: (1) workflow_cheatsheet.txt — raw markdown from render('workflow.md.j2', type_aliases=TYPE_ALIASES), the exact text TASK-261 will replace with a spec-derived renderer; (2) claude_md_section.txt — render('claude/claude_section.md.j2') with pinned roster, the CLAUDE.md managed body TASK-261 will regenerate; (3) agents_md_section.txt — render('agents_md/agents_section.md.j2') with pinned roster, the AGENTS.md managed body TASK-261 will regenerate (both backends covered); (4) skill_body_sq-{epic,feature,task,bug,decision,review,guide}.txt — render('agents/item_skill.md.j2') for each type, the bodies TASK-260 will regenerate.
  - How inputs are frozen: Roster — PINNED_ROSTER constant (all 8 bundled roles + python-dev, has_dev=True, developer sections included). Version — PINNED_VERSION='0.5.0' literal constant (not read from __version__). squad_dir — literal string 'squads', no tmp-path in rendered output. FORCE_COLOR/ANSI — conftest autouse _neutralize_forced_color strips it; tests call render() directly so no ANSI enters.
  - Tests call render() directly (no CLI invocation), so they are deterministic, fast (<0.1s for all 12), and ANSI-free by construction. test_all_managed_item_types_covered() is a coverage guard that fails if a new item type is added to managed_item_types() without a corresponding golden test.
  - No normalization needed: squad_dir is pinned as a string (not a path), templates contain no timestamps, and version is a fixed constant. Pyright, ruff check, and ruff format all clean. @manager goldens are green; TASK-257/260/261 may proceed.
<!-- sq:discussion:end -->
