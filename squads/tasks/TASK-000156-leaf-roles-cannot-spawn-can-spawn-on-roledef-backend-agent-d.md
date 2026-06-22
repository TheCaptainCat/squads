---
id: TASK-000156
sequence_id: 156
type: task
title: 'Leaf roles cannot spawn: can_spawn on RoleDef + backend Agent denylist'
status: Done
parent: FEAT-000122
author: tech-lead
assignee: python-dev
refs:
- BUG-000152:fixes
subentities:
- local_id: ST1
  title: Block leaf roles from spawning (US2)
  status: Done
  story: US2
created_at: '2026-06-21T21:46:41Z'
updated_at: '2026-06-21T22:27:47Z'
---
<!-- sq:body -->
Implements **FEAT-000122 Slice A (leaf-no-spawn)** / US2; fixes **BUG-000152**. Grounded in
**ADR-000155** (Accepted): the spawn-capability boundary lives at the Claude Code backend, bound
to the agent **type** at launch — not an sq-runtime check. First cut is "all tools minus
Agent/Task" for every leaf role.

## Goal

A leaf-role session launched by squads (manager spawns `python-dev` by type, etc.) structurally
cannot invoke the spawn tool, because its rendered `.claude/agents/<slug>.md` denies it. Manager
and tech-lead — the orchestrating roles in the loop — keep spawn authority.

## Changes (three seams)

1. **`RoleDef.can_spawn` bit** — `src/squads/_roles/_catalog.py`.
   - Add a `can_spawn: bool` field to the `RoleDef` dataclass (class at line 17), default
     `False`.
   - In the 8 bundled `RoleDef(...)` entries, set `can_spawn=True` for **`manager`** and
     **`tech-lead`** only. Leave `False` (the default) for `architect`, `reviewer`, `qa`,
     `devops`, `product-owner`, `tech-writer`.
   - `dev_role()` (the dynamic `<tech>-dev` factory around line 261) must produce
     `can_spawn=False` — developers are leaves.

2. **Backend emits the denylist** — `src/squads/_backends/_claude_code/_backend.py` +
   `src/squads/_rendering/templates/claude/pointer_agent.md.j2`.
   - `generate_role_entry` (line 187) renders `pointer_agent.md.j2` with the role context. Pass
     `can_spawn` (i.e. `role.can_spawn`) into the template render dict alongside the existing
     `slug`/`description`/`model`/`color`/`skills`.
   - In `pointer_agent.md.j2`, inside the YAML frontmatter (before the closing `---`), add:
     `{% if not can_spawn %}disallowedTools: Agent{% endif %}`. Per ADR-000155, denying `Agent`
     also covers the legacy `Task` alias (renamed `Task` → `Agent` in 2.1.63). Do not emit a
     `tools:` allowlist — omitting it preserves full-tool inheritance minus the denied spawn tool.
   - Keep frontmatter well-formed YAML (mind the existing `{% if %}` whitespace style in the
     template).

3. **Surface via `sq role <slug> show`** — the role show path in the CLI/service.
   - Add `can_spawn` to the rendered role detail so each role displays whether it can spawn
     (e.g. a "can spawn: true/false" line). Find the existing `sq role show` rendering and
     extend it; do not invent a new command.

## Acceptance

- A leaf role's rendered `.claude/agents/<slug>.md` contains `disallowedTools: Agent` in its
  frontmatter; `manager` and `tech-lead` rendered files do **not** (they retain spawn authority).
- `RoleDef.can_spawn` is `True` only for `manager` + `tech-lead`; `False` for every other bundled
  role and for all `<tech>-dev` roles from `dev_role()`.
- `can_spawn` is visible via `sq role <slug> show`.
- A **backend test** asserts the rendered agent frontmatter: leaf → denies `Agent`,
  manager/tech-lead → no `disallowedTools` line. Add a service/CLI smoke test for the
  `sq role show` surfacing too.
- Frontmatter stays valid YAML (parse it in the test rather than substring-matching only).
- `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean; full
  `uv run pytest` green.

## Out of scope

Slice B (full structured capability profile, lane enforcement, separation-of-duties) — gated on
FEAT-000125. Do not touch global `settings.json` deny rules; per-role capability belongs in the
agent definition per ADR-000155. The main-thread `--as <role>` path is explicitly **not** governed
by this change (ADR-000155 boundary caveat).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 156 add-subtask "<title>"`; track with `sq task 156 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Block leaf roles from spawning (US2) | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Block leaf roles from spawning (US2)

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US2 — Leaf roles structurally blocked from spawning agents (Slice A — fixes BUG-000152)
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
- [2026-06-21T21:47:28Z] Olivia Lead:
  - @python-dev — Slice A of FEAT-000122 (US2), fixes BUG-000152. Per ADR-000155 the spawn boundary lives at the Claude Code backend, bound to the agent type at launch — NOT an sq-runtime check.
  - Three seams: (1) add can_spawn: bool (default False) to RoleDef in _roles/_catalog.py — True only for manager + tech-lead, False for all others including dev_role(); (2) pass can_spawn into generate_role_entry's render in _backends/_claude_code/_backend.py and add {% if not can_spawn %}disallowedTools: Agent{% endif %} to pointer_agent.md.j2 (denying Agent also covers the legacy Task alias; no tools: allowlist); (3) surface the bit via sq role <slug> show.
  - Acceptance: leaf role's rendered .claude/agents/<slug>.md denies Agent; manager/tech-lead retain it; backend test parses the frontmatter as YAML for both cases; can_spawn shown in sq role show; pyright + ruff clean; full pytest green. Out of scope: Slice B / lane enforcement (gated on FEAT-000125) and settings.json deny rules.
- [2026-06-21T22:03:15Z] Elias Python:
  - Implemented TASK-000156 (Slice A / US2 / BUG-000152 fix). All gates green.
  - **Files changed:**
  - - `src/squads/_roles/_catalog.py` — added `can_spawn: bool` field to `RoleDef` (default `False`); set `can_spawn=True` on `manager` and `tech-lead` only; updated `to_extra`/`from_extra` to round-trip the field.
  - - `src/squads/_models/_extras.py` — added `ExtraKey.CAN_SPAWN = 'can_spawn'`.
  - - `src/squads/_backends/_claude_code/_backend.py` — pass `can_spawn=role.can_spawn` into the `pointer_agent.md.j2` render dict in `generate_role_entry`.
  - - `src/squads/_rendering/templates/claude/pointer_agent.md.j2` — added `{% if not can_spawn %}disallowedTools: Agent{% endif %}` in the YAML frontmatter block.
  - - `src/squads/_cli/_role.py` — added `can spawn: yes/no` line to the role card panel (and `can_spawn` to the `--json` output for both catalog and fallback paths).
  - - `src/squads/_rendering/templates_manifest.json` — regenerated hash for updated `pointer_agent.md.j2`.
  - - `tests/goldens/` — updated golden JSON files (`list`, `role_manager_show`, `role_qa_show`) to include `can_spawn`.
  - - `tests/test_can_spawn.py` — new test file with 19 tests across three seams: catalog field values, rendered pointer frontmatter (YAML-valid, Agent denied for leaves, not for spawners), and CLI show output.
  - **Gate results:**
  - - `uv run pyright`: 0 errors, 0 warnings, 0 informations
  - - `uv run ruff check . && uv run ruff format --check .`: All checks passed
  - - `uv run pytest`: 862 passed, 1 skipped
  - @reviewer — ready for review. Three seams: RoleDef.can_spawn bit, backend+template denylist, and sq role show surfacing. All acceptance criteria met.
- [2026-06-21T22:21:02Z] Paul Reviewer:
  - Reviewed and **approved** (REV-000157). Slice A of FEAT-000122 (US2), fixes BUG-000152, conforms to ADR-000155.
  - Verified independently: catalog logic (can_spawn True only for manager + tech-lead; False for all 6 other bundled roles and all dev_role() techs), rendered .claude/agents/*.md frontmatter parsed as YAML (leaves deny Agent, spawners don't, no whitespace breakage), to_extra/from_extra round-trip, and can_spawn surfaced in both sq role show text and --json. Gates re-run clean: pyright 0 errors, ruff check + format clean, pytest 862 passed / 1 skipped.
  - One non-blocking note in REV-000157: the --json activated-item/index path is verified manually but not unit-tested (optional follow-up).
  - Ready for QA. @qa
- [2026-06-21T22:27:47Z] Mara Tester:
  - Verified. TASK-000156 meets all Slice A acceptance criteria.
  - **Suite:** 862 passed, 1 skipped. test_can_spawn.py 19/19 green.
  - **Render check (sq init --roles all):** All 8 .claude/agents/*.md parse as valid YAML. Leaves (architect, devops, qa, reviewer, product-owner, tech-writer) carry disallowedTools: Agent. Orchestrators (manager, tech-lead) do not.
  - **dev_role():** All tech variants produce can_spawn=False.
  - **sq role show:** Correct can spawn: yes/no for all 8 roles.
  - **BUG-000152** transitioned to Verified. The recursive self-spawn mechanism is structurally closed at the agent-type level per ADR-000155.
<!-- sq:discussion:end -->
