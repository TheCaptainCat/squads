---
id: TASK-312
sequence_id: 312
type: task
title: Strip squad-item refs from bundled prose + CLAUDE.md
status: Done
parent: FEAT-237
author: tech-lead
assignee: python-dev
priority: medium
subentities:
- local_id: ST1
  title: Strip refs from bundled prose templates
  status: Done
  assignee: python-dev
  story: US5
- local_id: ST2
  title: Verify/clean CLAUDE.md (removal only)
  status: Done
  assignee: python-dev
  story: US5
created_at: '2026-07-06T12:55:27Z'
updated_at: '2026-07-06T14:06:18Z'
---
<!-- sq:body -->
USER-FACING WAVE. Scope: the bundled agent-facing prose templates (src/squads/_rendering/templates/agents/greeting_skill.md.j2, agents/squads_skill.md.j2, agents_md/agents_section.md.j2, workflow.md.j2) plus CLAUDE.md. Blast radius: 4 templates + CLAUDE.md; CLAUDE.md currently has ZERO digit-refs (only template forms like --parent FEAT-… / USn) so it is a verify-clean, not a rewrite. REMOVAL ONLY — no restyling/rewording of the guidance wording. Disjoint files from all other tasks — parallel-safe. Done when: zero real-citation refs remain in the .j2 templates and CLAUDE.md; the generated skill/agent output (via sq sync) carries no refs; wording is otherwise unchanged; managed-region regeneration unaffected.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 312 add-subtask "<title>"`; track with `sq task 312 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done | python-dev | Strip refs from bundled prose templates | US5 |
| ST2 | Done | python-dev | Verify/clean CLAUDE.md (removal only) | US5 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Strip refs from bundled prose templates

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
**Implements:** US5 — Bundled prose stripped of refs without churning wording
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Remove squad-item refs from the bundled agent-facing prose: src/squads/_rendering/templates/agents/greeting_skill.md.j2, agents/squads_skill.md.j2, agents_md/agents_section.md.j2, workflow.md.j2. REMOVAL ONLY — preserve the guidance wording; do not restyle/shorten/rewrite. Done when: grep over these templates returns zero refs, the rendered output (via sq sync) carries no refs, and wording is otherwise byte-for-byte unchanged apart from the removals.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Verify/clean CLAUDE.md (removal only)

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Assignee:** Elias Python
**Implements:** US5 — Bundled prose stripped of refs without churning wording
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
CLAUDE.md currently has zero digit-refs (only template forms like --parent FEAT-… and USn), so this is primarily a verify-clean: confirm no real-citation ref exists and remove any that is real, without rewording. Do not restyle the file. Done when: grep of the ref pattern over CLAUDE.md returns zero real citations and the managed-region regeneration is unaffected.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-06T14:06:18Z] Elias Python:
  - Stripped digit-bearing squad-item refs from the 4 bundled prose templates (greeting_skill.md.j2, squads_skill.md.j2, agents_md/agents_section.md.j2, workflow.md.j2): TASK-3→TASK-<n>, FEAT-2→FEAT-<n>, FEAT-10→FEAT-<n>, US1→USn, matching the placeholder convention already used elsewhere in the same files (FEAT-…, USn).
  - CLAUDE.md verified clean: grep of the full pattern (incl. US/ST/§) over CLAUDE.md returns zero matches — it already only carried non-digit template forms (FEAT-…, USn, <n>); no edit needed.
  - Regenerated via 'uv run sq sync': squads/agents/skills/SKILL-000192-greeting.md and SKILL-000200-squads.md re-rendered from the cleaned templates (only the touched lines changed). No AGENTS.md backend is active in this repo so agents_section.md.j2's change has no on-disk generated counterpart here; it is covered by the golden test instead.
  - Regenerated goldens: tests/goldens/workflow_cheatsheet.txt and tests/goldens/agents_md_section.txt via UPDATE_GOLDENS=1 uv run pytest tests/test_golden_rendered_output.py — diff confirmed to be exactly the placeholder swap, nothing else moved.
  - Gates green (pyright, ruff check, ruff format --check); targeted tests (golden/skill/playbook/rendered + backend_agents_md/custom_type_cli/skill_seeding/workflow_renderer_261/workflow_authoring_prose/status_display_characterization) all pass.
  - ST1 and ST2 done; task Done.
<!-- sq:discussion:end -->
