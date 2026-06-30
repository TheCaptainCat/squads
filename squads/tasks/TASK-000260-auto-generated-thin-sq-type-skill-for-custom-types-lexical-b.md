---
id: TASK-000260
sequence_id: 260
type: task
title: Auto-generated thin sq-<type> skill for custom types (lexical-by-slug)
status: Draft
parent: FEAT-000210
author: tech-lead
refs:
- TASK-000262:depends-on
- TASK-000258:depends-on
- TASK-000256:depends-on
created_at: '2026-06-30T12:01:06Z'
updated_at: '2026-06-30T12:03:21Z'
---
<!-- sq:body -->
**Slice 4 — auto-generated thin `sq-<type>` skill for custom types.**
Maps to: US3, AC#5, AC#6.

### Scope
Each managed custom type gets a thin, auto-generated `sq-<type>` skill via the
backend's `_write_item_skills`. Today that method iterates
`interactions.managed_item_types()` (= `list(PLAYBOOK)`, bundled types only) and
pulls rich per-role guidance from `PLAYBOOK[item_type]`. A custom type has NO
PLAYBOOK entry, so it needs a spec-derived thin path:
- lifecycle string (from the auto-linearization helper, task 262),
- the basic command list (the standard verb set, same as built-ins),
- any declared role interactions IF available (graceful degradation — the custom
  skill is thinner than a built-in skill but functional; no rich enter/do/handoff/
  watch sections).
Reuse `agents/item_skill.md.j2` or add a minimal variant; render `sections=[]`
for custom types so the template degrades cleanly.

### SKILL-id allocation — COORDINATE with FEAT-178 (Done)
FEAT-178 already shipped the lexical-by-slug allocation primitive:
`interactions.bundled_skill_slugs()` returns sorted slugs and is the single
ordering primitive consumed by `sq init` seeding and the migration
(`_services/_maintenance.py::seed_bundled_skills`, which allocates SKILL ids via
`db.allocate_id(ItemType.SKILL)` in lexical-by-slug order). Do NOT build a new
allocator — extend the existing slug set so a custom type's `sq-<type>` skill is
minted in the SAME lexical-by-slug order, satisfying AC#6 (no SKILL-id churn).
The custom skill is allocated when the custom type is first synced/seeded, not at
init of a bundled squad.

### Acceptance
- AC#5: a thin `sq-incident` skill is generated with the correct
  auto-linearized lifecycle string and the standard command list.
- AC#6: the new managed-type skill is allocated in lexical-by-slug order
  consistent with FEAT-178 (no churn of existing SKILL ids; assert ordering).
- HARD CONSTRAINT — AC#7/#8: for a bundled (non-custom) squad the generated
  `sq-<type>` skill bodies are byte-identical (task 256 golden green). Hold the
  roster constant when diffing ([[pin-roster-when-diffing-generated-skills]]).

### Files
- src/squads/_backends/_claude_code/_backend.py (`_write_item_skills`),
  src/squads/_interactions/__init__.py (extend the managed-type / slug set to
  cover custom types from the spec), src/squads/_services/_maintenance.py
  (seeding for custom skills), src/squads/_rendering/templates/agents/
  item_skill.md.j2 (thin-path degradation), tests.

### Dependencies
- Depends on task 262 (lifecycle string), task 258 (folder), FEAT-178 (Done,
  allocation primitive). Gated by task 256 golden for the byte-identical
  built-in case.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 260 add-subtask "<title>"`; track with `sq task 260 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
