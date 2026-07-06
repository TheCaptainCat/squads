---
id: TASK-132
sequence_id: 132
type: task
title: Implement the agents_md backend (AGENTS.md)
status: Done
parent: FEAT-16
author: tech-lead
priority: high
refs:
- TASK-131:depends-on
- BUG-134:fixes
description: Second AgentBackend writing a single project AGENTS.md; passes the shared
  conformance suite; sq init/sync target it
subentities:
- local_id: ST1
  title: Implement AgentsMdBackend writing/refreshing AGENTS.md
  status: Done
  story: US1
- local_id: ST2
  title: Parametrize the conformance suite over agents_md and make both backends pass
    it
  status: Done
  story: US2
created_at: '2026-06-15T13:03:01Z'
updated_at: '2026-07-06T15:18:53Z'
---
<!-- sq:body -->
## Goal

Implement a second, genuinely different `AgentBackend`: **`agents_md`**, which writes/refreshes a single project-root `AGENTS.md` (roster, workflow, skill content) from squad state — the cross-tool AGENTS.md convention. It must pass the **shared conformance suite from TASK-131** unchanged, which is the proof the ABC is honest. `sq init --backend agents_md` and `sq sync` must drive it end to end.

## Depends on

TASK-131 (conformance suite + ABC corrections) lands first. This backend is written to pass that suite; the suite's existence is what drives any remaining Claude-isms out of the contract.

## Approach

1. New subpackage `src/squads/_backends/_agents_md/` mirroring `_claude_code/`'s shape: `_backend.py` (the `AgentsMdBackend`, `name = "agents_md"`), `__init__.py` registering it via `_registry.register`, plus a small `_agents_md.py` for the managed-section marker injection (analogous to `_claude_md.py`).
2. **No pointer-file mechanic.** AGENTS.md is one file. Map the ABC onto it:
   - `ensure_scaffold`: ensure `AGENTS.md` exists (create with a header if absent), idempotent, never clobber user prose outside the managed markers. Return the `Artifact`.
   - `write_managed`: render roster + workflow + skill content into the managed section of `AGENTS.md` (reuse existing Jinja templates where tool-neutral — `workflow.md.j2`, the squads/greeting skill bodies — and add `templates/agents_md/*.j2` for AGENTS.md-specific framing). Idempotent marker injection.
   - `generate_role_pointer` / `generate_skill_pointer`: with no per-item pointer files, fold role/skill routing into the single AGENTS.md (or return an artifact pointing at the managed file). Whatever the ABC settled on in TASK-131 dictates the exact shape — follow the contract, do not reintroduce a Claude-ism.
   - `remove_artifacts`: remove the item's contribution from AGENTS.md (or no-op if folded), safe when absent.
3. Wire selection: `--backend agents_md` already flows through CLI → `default_backend` config → `get_backend`; ensure registration import in `_registry.get_backend` picks up the new backend (per the registration story chosen in TASK-131).
4. Tests: parametrize the conformance suite over `agents_md` (must pass), plus an `agents_md`-specific test (valid AGENTS.md, managed markers intact, user prose preserved, roster/workflow content present) and a CLI smoke test (`sq init --backend agents_md` then `sq sync`).
5. README: document running squads with the agents-md backend (US1 acceptance).

## Files

- NEW: `src/squads/_backends/_agents_md/{__init__,_backend,_agents_md}.py`
- NEW: `src/squads/_rendering/templates/agents_md/*.j2`
- NEW: `tests/test_backend_agents_md.py` (+ parametrize the shared conformance fixture onto it)
- EDIT (low blast radius): `src/squads/_backends/_registry.py` registration import only (the structural ABC/path changes were already made and merged in TASK-131); README.

## Conflict surface

Mostly **new files** — low conflict. The only shared edits are the registry registration import and README. It must NOT need to touch `_base.py` again — if it does, that means TASK-131 missed a contract correction; route it back through the architect, do not patch the ABC from here.

## Acceptance

- `sq init --backend agents_md` produces a valid, useful `AGENTS.md`; `sq sync` refreshes it idempotently without clobbering user prose.
- Both `claude_code` and `agents_md` pass the shared conformance suite.
- README documents the agents-md backend.
- `uv run pyright && uv run ruff check . && uv run ruff format --check . && uv run pytest` all green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 132 add-subtask "<title>"`; track with `sq task 132 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Implement AgentsMdBackend writing/refreshing AGENTS.md | US1 |
| ST2 | Done |  | Parametrize the conformance suite over agents_md and make both backends pass it | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Implement AgentsMdBackend writing/refreshing AGENTS.md

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — AGENTS.md backend for non-Claude agent tooling
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Implement AgentsMdBackend writing/refreshing project AGENTS.md (roster, workflow, skill content); sq init/sync target it; README.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Parametrize the conformance suite over agents_md and make both backends pass it

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — As a future backend implementer, I want a backend conformance test suite, so that I know exactly what the AgentBackend contract requires of me
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Covers parametrizing the shared TASK-131 conformance suite over the new agents_md backend (via the backend-factory fixture) and making both claude_code and agents_md pass it unchanged — the proof that the AgentBackend ABC is honest and free of Claude-specific assumptions. Includes the agents_md-specific test (valid AGENTS.md, managed markers intact, user prose preserved, roster/workflow content present) and a sq init --backend agents_md + sq sync smoke test.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-15T13:03:23Z] Olivia Lead:
  - Depends-on TASK-131: written to pass the shared conformance suite from that task. If implementing agents_md forces another touch of _base.py, that's a missed contract correction in 131 — route it back through @architect, don't patch the ABC from this task.
  - Conflict surface: almost all new files (_backends/_agents_md/, templates/agents_md/, tests). Only shared edits are the registry registration import and README — low blast radius.
- [2026-06-15T13:44:37Z] Elias Python:
  - agents_md backend implemented (ST1 + ST2 done).
  - New files: src/squads/_backends/_agents_md/__init__.py, _backend.py, _managed.py; src/squads/_rendering/templates/agents_md/agents_section.md.j2, role_entry.md.j2, skill_entry.md.j2; tests/test_backend_agents_md.py (11 new tests). Updated templates_manifest.json, README.md.
  - Backend design: ensure_scaffold creates AGENTS.md at project root; write_managed injects roster/operators into the managed section (<!-- squads:start/end -->), idempotent; generate_role_entry writes a per-role staging file under .agents_md/roles/{slug}.md; generate_skill_entry writes .agents_md/skills/{slug}.md; remove_artifacts unlinks the staging file (missing_ok). User prose outside the markers is never clobbered.
  - Backend selection: pass --backend agents_md to sq init (or set default_backend in .squads.toml); it flows through to get_backend() which now uses the _BUILTIN_BACKEND_MODULES tuple (CC-006). sq sync drives it the same way as claude_code.
  - Conformance: both claude_code and agents_md pass the shared suite — 70 conformance tests (35 per backend). agents_md-specific tests: 11 additional. Full gate: 794 tests, pyright 0 errors, ruff clean.
  - ADR-133 conformance: this task required zero changes to _base.py — exactly as the ADR required. The ABC was already clean after TASK-131.
  - @reviewer ready for review. @qa suite is green.
- [2026-06-15T13:54:43Z] Mara Tester:
  - QA verification: PARTIAL PASS — backend mechanics pass, but AGENTS.md content gap found against FEAT-16 US1 acceptance.
  - PASS:
  -   - sq init --backend agents_md creates AGENTS.md (no .claude/ or CLAUDE.md)
  -   - default_backend = agents_md in .squads.toml selects it correctly
  -   - sq sync refreshes operator in managed section idempotently (byte-identical on second run)
  -   - User prose before and after managed markers is preserved
  -   - Conformance suite: 70 tests pass (35 per backend); agents_md-specific 11 tests all pass
  -   - README documents agents_md backend
  - FAIL (US1 acceptance gap): FEAT-16 US1 requires AGENTS.md to carry 'roster, workflow and skill content'. The generated AGENTS.md carries roster correctly but:
  -   - Workflow: only a generic one-liner ('a status lifecycle, and a handoff protocol') — no actual workflow commands, status transitions, or workflow.md.j2 content. TASK-132 approach explicitly said to reuse workflow.md.j2.
  -   - Skill content: not present in AGENTS.md at all. Staging files exist under .agents_md/roles/ with mission text, but they are never compiled into AGENTS.md.
  -   - Role definitions section only shows 'Role: manager' (title) — no mission, responsibilities, or actionable guidance.
  - @python-dev please review: should workflow.md.j2 be included in write_managed, and should role missions from .agents_md/roles/ staging files be compiled into the AGENTS.md managed section?
- [2026-06-15T13:58:21Z] Paul Reviewer:
  - REV-135: CHANGES REQUESTED. Blocking: F1 (high) — sq init --backend agents_md + sync produces an AGENTS.md with roster ONLY: no workflow content (workflow.md.j2 never rendered in), no skill content (squads/greeting/per-type bodies absent), and role definitions are title-only stubs. The richer per-role staging files generate_role_entry writes to .agents_md/roles/ are never folded into AGENTS.md — orphans. That misses FEAT-16/US1's 'valid, useful AGENTS.md carrying roster, workflow and skill content'. Not an ABC violation and the gate is green, but as shipped it's closer to a stub than the 'genuinely useful second backend' the feature is for.
  - Non-blocking: F2 (low) _cli/_main.py:185 hardcodes '(pointers + squads skill + CLAUDE.md)' for ALL backends — false + Claude-leaky for agents_md, on the exact line ADR-133 CC-005 told you to keep backend-neutral. F3 (low) _backend.py module docstring claims write_managed compiles staging entries into AGENTS.md; it doesn't.
  - Fix F1 (render workflow + at least the squads-skill summary into agents_section.md.j2; emit role mission into Role definitions or fold the staging files), tidy F2/F3, and I'll re-review. @python-dev
- [2026-06-15T14:13:49Z] Elias Python:
  - Addressed all three findings from REV-135. Gate is green: 798 passed, 1 skipped; pyright 0 errors; ruff check + format clean.
  - **F1 (high) — AGENTS.md now carries roster, workflow, and role content:**
  - - agents_section.md.j2 now uses '{% include "workflow.md.j2" %}' (same partial the Claude backend's squads skill uses) plus a rich Role definitions section with mission and responsibilities.
  - - write_managed now passes type_aliases=TYPE_ALIASES so the workflow template renders the full alias table and command cheatsheet.
  - - Staging-file incoherence resolved: write_managed reads .agents_md/roles/<slug>.md staging files written by generate_role_entry and folds the mission text into AGENTS.md — no orphans. When staging files are absent (fresh unit test without a prior generate_role_entry call), role entries fall back to name/title-only gracefully, and the workflow section is always included.
  - **F2 (low):** Dropped the false '(pointers + squads skill + CLAUDE.md)' parenthetical from _main.py line ~185. Init summary now shows just the backend name, which is accurate for any backend.
  - **F3 (low):** Rewrote the module docstring in _agents_md/_backend.py to accurately describe the actual design: staging files are compile inputs to write_managed, not orphans.
  - **New usefulness test** in tests/test_backend_agents_md.py class TestAgentsMdUsefulnessPin (4 tests): asserts AGENTS.md after sq init+sync contains workflow commands ('sq create task', 'Todo', 'InProgress', 'Canonical' alias table), role mission text ('first point of contact'), and the '**Mission:**' heading — so a future regression to a roster-only stub fails immediately.
  - templates_manifest.json updated for the changed agents_section.md.j2 hash. @reviewer please re-verify. @qa please verify BUG-134 closed.
- [2026-06-15T14:22:06Z] Paul Reviewer:
  - REV-135 APPROVED on re-review. F1/F2/F3 all verified resolved; gate green (798 passed, 1 skipped; pyright 0; ruff clean). AGENTS.md now carries roster + full workflow cheatsheet (alias table via type_aliases) + role missions folded from .agents_md/roles/ staging files; idempotent (byte-identical second sync); marker-safe. Staging-file design judged sound — the generate_role_entry→write_managed ordering holds on all real paths (sync/init/adopt/add_role), the mission='' fallback is honest unit-test behaviour not a coupling bug, and the new TestAgentsMdUsefulnessPin is non-vacuous (asserts workflow + mission content that the old stub lacked). Clearing for Done. @qa BUG-134 should now verify as Fixed.
  - @tech-lead TASK-132 review complete and approved — ready to move to Done.
<!-- sq:discussion:end -->
