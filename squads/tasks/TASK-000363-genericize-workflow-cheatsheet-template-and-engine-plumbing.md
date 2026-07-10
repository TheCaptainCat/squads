---
id: TASK-363
sequence_id: 363
type: task
title: Genericize workflow cheatsheet template and engine plumbing
status: Done
parent: FEAT-334
author: tech-lead
created_at: '2026-07-10T02:00:02Z'
updated_at: '2026-07-10T04:42:43Z'
---
<!-- sq:body -->
## Scope

Redesign the "Team workflow" section of `src/squads/_rendering/templates/workflow.md.j2`
so it is driven generically from the loaded spec + playbook + roster instead of
hardcoded bundled type/kind/status literals, plus the data plumbing this needs in
`src/squads/_rendering/_engine.py`. Also fix the retype static example in
`workflow_static.md.j2`. This template is the shared source for both the `squads`
skill's cheatsheet and `sq workflow`.

## Covered REV-360 findings (FEAT-334 scope)

- MEDIUM — `workflow.md.j2:5` — authoring-lane blocks gated on literal
  `authoring_owner('feature')` + `item_subentity_kind('feature')=='story'` and the
  `task`/`subtask` equivalent; renamed/dropped types silently drop the guidance.
- MEDIUM — `workflow.md.j2:23` — "Sub-entities are tracked too" bullet hand-writes
  bundled kinds ("Subtasks & user stories", "review findings"), literal lifecycles
  ("Todo → InProgress → Done", "Open → Fixed → Verified"), `--severity high`, and
  type names task/feature/review.
- MEDIUM — `workflow_static.md.j2:19` — retype "Status behaviour" prose hardcodes
  workflow-sharing type pairs "task↔bug, feature↔epic"; wrong under custom vocab.
- LOW — `workflow.md.j2:33` — per-type skills bullet hardcodes example skill names
  `(sq-feature, sq-task, sq-bug, …)`.

## Design constraints (from FEAT-334)

- Iterate `spec.items` (non-meta) and the roster in declared order; render from
  `_interactions` data (`ItemPlaybookSpec`/`RoleGuideSpec`) + `authoring_owner(type)`
  + spec accessors — never an if-branch keyed to one specific type name.
- CONCISE cross-type overview: roughly one condensed line per type-role pairing
  (who acts + the single highest-signal handoff), NOT a duplicate of the full
  enter/do/handoff/watch that the per-type `sq-<type>` skills already render. State
  the chosen summarization/altitude rule in a code comment so a future editor knows
  why it stops short of full playbook detail (US2 acceptance).
- The retype static section should describe workflow-sharing generically (types that
  share a status machine) rather than naming bundled pairs.
- Note: `_interactions/__init__.py` `CREATE_LANES`/`authoring_owner()` is the data
  source for authoring lanes; the REV-360 LOW on CREATE_LANES documents it degrades
  gracefully (a custom type with no lane owner gets no authoring bullet) — consume it
  as-is, do not rework it here.

## Acceptance

- Rendered "Team workflow" section contains no hardcoded literal type/kind/status
  words as template text; every name in the output comes from iterating
  spec/playbook/roster (US1 acceptance).
- Every non-meta spec type with at least one playbook role guide renders at least one
  line; renaming a type changes only the rendered name, not whether guidance appears.
- Update the cheatsheet golden/snapshot(s) atomically with the template change; the
  bundled-default render carries every fact present today (authoring flow, subtask→
  story mapping, sub-entity machines, hierarchy line, alias table, lifecycle table,
  retype/remove-vs-cancel/ref-kind static sections) — nothing the default squad relies
  on silently disappears (US3).
- `uv run pytest`, `uv run pyright`, `uv run ruff check .`, `ruff format --check .`
  all clean.

## Notes

Already-generic parts (alias table, lifecycle table iterating `spec.machine_for(...)`)
stay untouched except as needed to keep them consistent. Do not touch the per-type
`sq-<type>` skill templates (FEAT-334 non-goal). The tech-writer/altitude read-through
(US2/US3 human verification) is the sibling verification task.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 363 add-subtask "<title>"`; track with `sq task 363 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-10T04:33:54Z] Elias Python:
  - Genericized workflow.md.j2's Team-workflow section: loops spec.items (non-meta, declared order), deriving each type's authoring_owner + item_parent_required + item_subentity_kind + item_ref_rules generically -- no more hardcoded 'feature'/'task' literals. Fixed the two crash points: item_parent_required('task') and parent_chain(spec,'task') were called unconditionally outside their guard; now only ever called with a loop var guaranteed present in spec.items. Also hardened the --parent lookup against a stale parent_required pointing at a since-dropped type (spec.items[parent].prefix guarded by 'parent in spec.items').
  - Altitude rule recorded as a template comment in workflow.md.j2: one condensed line per type-role authoring pairing (who + create cmd + single highest-signal handoff), not the full enter/do/handoff/watch (that's the sq-<type> skill's job). Bonus: now covers all 6 owned types (epic/feature/task/bug/decision/review), not just feature+task as before.
  - workflow_static.md.j2 retype example: groups non-meta types by declared lifecycle name instead of naming 'task/bug/feature/epic' -- which was already wrong on the bundled spec (task and bug do NOT share a workflow; epic/feature/task do, all three). Now correctly renders 'epic↔feature↔task'.
  - claude_section.md.j2 had the identical crash pattern (its own hand-duplicated Team-workflow section) -- applied the same generic loop, same guard, in that file's narrative voice.
  - Regression tests added to test_workflow_authoring_prose.py: dropping 'task' from spec.items no longer crashes either template; a custom type with a declared subentity_kind generically appears in the Sub-entities summary line. Updated 3 pre-existing tests whose assertions pinned the old hardcoded wording.
  - Regenerated goldens (workflow_cheatsheet.txt, claude_md_section.txt, agents_md_section.txt via UPDATE_GOLDENS=1) and the manifest (gen_template_manifest.py). Did NOT run sq sync on this repo's own CLAUDE.md/squads skill/.squads.json -- reverted that side effect to keep the diff scoped to the task's file list; a sync pass is a separate step.
  - Gates: pyright clean, ruff check clean, ruff format clean. Targeted tests green: test_workflow_authoring_prose, test_workflow_renderer_261, test_golden_rendered_output, test_skills, test_custom_type_cli, test_custom_type_skill, test_status_display_characterization, test_backend_agents_md, test_linearize_lifecycle, test_override_commands (manifest freshness), test_squad_ref_hygiene. Did not run the full suite per instructions.
  - Reviewer should scrutinize: (1) the Jinja namespace() scoping fix -- 'set x = true' inside a nested {% for %} does NOT leak out of that loop in Jinja2, I hit this for both the maximal-hierarchy-chain filter and the lifecycle-sharing-group builder, fixed via namespace(); (2) whether dropping a lane-ambiguous type like 'guide' (2 owners) correctly stays silently omitted (unchanged pre-existing CREATE_LANES behavior, not reworked); (3) the new claude_section.md.j2 wording vs. its old narrative style -- I kept 'its parent is the X it implements' phrasing to preserve continuity but collapsed it to one line for readability.
- [2026-07-10T04:41:11Z] Paul Reviewer:
  - Reviewed uncommitted TASK-363 diff (independent). VERDICT: APPROVE. gates clean (ruff/format; no .py src changed), manifest regenerated, full suite green (exit 0, 0 failures). No findings.
  - Crash-on-drop FIXED (Q1): the literal spec.item_parent_required('task')/parent_chain(spec,'task')/spec.items[task_parent] calls are gone — both workflow.md.j2 and the duplicated block in claude/claude_section.md.j2 now loop  (loop var always present) and guard the parent-prefix lookup with  (sound — a parent_required naming a since-dropped type drops the --parent clause instead of KeyError-ing). subkind->subentity_kinds and subentity_kinds[subkind].lifecycle are safe by TASK-349's load-time validation. Regression tests test_dropped_task_does_not_crash_workflow_cheatsheet + _claude_section are genuine (drop task, render, assert no crash + no stale trace).
  - Cheatsheet quality/altitude (Q2): GOOD. Read the regenerated workflow_cheatsheet.txt — the Team-workflow section is now one condensed line per authoring type-role pairing (owner → create + its single highest-signal handoff: parent/sub-entity/ref), e.g. 'Tech lead → sq create task --parent FEAT-…, then add-subtask --story USn; link with ref add <id> --kind fixes|addresses'. It's a cross-type SYSTEM MAP, not a duplicate of the per-type sq-<type> playbook, and still conveys the spine (tech-lead line + 'Hierarchy: epic → feature → task' + the sub-entities summary). Coherent and accurate. Hierarchy dedup (namespace prefix check) correctly prints only the longest chain (no redundant epic→feature line).
  - Lifecycle-sharing factual fix (Q3): CORRECT. Verified against default_workflow.toml — epic/feature/task all lifecycle='work' (shared); bug='bug', decision='adr', review='review', guide='guide' (each distinct). The OLD 'task↔bug, feature↔epic' was factually WRONG (task and bug do NOT share a workflow). The new workflow_static.md.j2 groups non-meta types by declared lifecycle name and renders 'e.g. epic↔feature↔task' — the only shared group. Correct.
  - Custom-type participation (Q4): genuine — test_custom_type_with_a_subentity_kind_appears_in_the_subentities_summary declares an 'incident' type hosting 'finding' and asserts ' → ' in the derived sub-entities summary line. namespace() scoping fixes are correct (ns.is_prefix_of_another for hierarchy dedup, ns.matched for lifecycle grouping; list.append via {% set _ = %} mutates in place). _engine.py needed no change (linearize_lifecycle/parent_chain/authoring_owner already globals). Manifest fresh (workflow/workflow_static/claude_section rehashed); version not bumped; no ticket IDs in source. Completes FEAT-334's REV-360 cheatsheet surfaces.
- [2026-07-10T04:41:47Z] Paul Reviewer:
  - Reposting Q1/Q2/Q4 cleanly (backticks truncated the earlier bullets). Q1 crash-on-drop FIXED: the literal item_parent_required(quote task)/parent_chain(spec, task)/spec.items[task_parent] calls are gone; both workflow.md.j2 and the duplicated block in claude_section.md.j2 now loop over spec.items (loop var always present) and guard the parent-prefix lookup with an "if parent and parent in spec.items" test — sound, so a parent_required naming a since-dropped type drops the parent clause instead of KeyError. subkind and its lifecycle are safe by TASK-349 load-time validation. Regression tests (drop task, render both templates, assert no crash + no stale trace) are genuine.
  - Q2 cheatsheet quality/altitude GOOD: read the regenerated workflow_cheatsheet.txt — the Team-workflow section is now one condensed line per authoring type-role pairing (owner then create + its single highest-signal handoff: parent/sub-entity/ref), e.g. the Tech lead line = create task with parent FEAT plus add-subtask with story USn plus link ref add fixes/addresses. It is a cross-type SYSTEM MAP, not a duplicate of the per-type sq-type playbook, and still conveys the spine (tech-lead line + Hierarchy epic to feature to task + the sub-entities summary). Coherent and accurate; the hierarchy dedup prints only the longest chain (no redundant epic-to-feature line).
  - Q4 custom-type participation genuine: test_custom_type_with_a_subentity_kind_appears_in_the_subentities_summary declares an incident type hosting finding and asserts incident maps to finding in the derived sub-entities summary line. namespace() scoping is correct (ns.is_prefix_of_another for hierarchy dedup, ns.matched for lifecycle grouping; list append via set-underscore mutates in place). _engine.py needed no change (linearize_lifecycle/parent_chain/authoring_owner already globals). Manifest fresh (workflow/workflow_static/claude_section rehashed); version not bumped; no ticket IDs in source. Completes FEAT-334 REV-360 cheatsheet surfaces.
- [2026-07-10T04:42:43Z] Catherine Manager:
  - Reviewer-approved, no findings. Crash-on-drop fixed (unguarded item_parent_required('task')/parent_chain literals gone, parent-prefix guarded; regression-tested by dropping a built-in type), cheatsheet restructured to a concise generic per-type map at the right altitude (reviewer-confirmed quality), and the workflow_static lifecycle-sharing factual error corrected. Manifest + goldens regenerated. Full suite green. Landing.
<!-- sq:discussion:end -->
