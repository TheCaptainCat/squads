---
id: TASK-369
sequence_id: 369
type: task
title: Genericize squads skill and role prose for spec-driven vocab
status: Done
parent: FEAT-336
author: tech-lead
created_at: '2026-07-10T02:00:11Z'
updated_at: '2026-07-10T02:55:15Z'
---
<!-- sq:body -->
## Scope

Surface 4b of the REV-360 audit — the `squads` skill body and the bundled role prose.
Genericize the hardcoded vocab in the squads-skill template and fix the role definitions'
prose that names now-overridable work vocab. Files:
`_rendering/templates/agents/squads_skill.md.j2`, `_roles/roles.toml`; regenerate the
`squads` skill snapshot + role snapshots under `squads/agents/`.

## Covered REV-360 findings

- HIGH — `squads_skill.md.j2:88` (also `:76`) — "Set importance with
  `--priority urgent|high|medium|low`" hardcodes the priority field name AND its badge
  values; priority is a spec-defined overridable badge collection. Derive/soften.
- MEDIUM — `squads_skill.md.j2:72` — create example trailing comment
  `# also: epic|feature|bug|decision|review|guide` hardcodes the built-in work-type set.
- MEDIUM — `squads_skill.md.j2:19` and comment-scoping table `:47-52` — sub-entity kinds
  + severity axis hardcoded in prose and the example table (`sq review <n> finding`,
  `sq feature <n> story`, `sq task <n> subtask`, "a finding's --severity").
- MEDIUM — `_roles/roles.toml:76,90-92,113,125,127,153-154` — bundled role
  responsibilities name overridable work vocab (architect "Write and maintain ADRs";
  tech-lead task/feature/subtask/user-story/bug/review; reviewer "File review findings …
  with severity"; qa "Derive test cases from user stories"/"Report defects as bug items";
  product-owner "Author features"/"Write each feature's user stories"). Roles are reserved
  meta-vocab but their PROSE names spec-overridable types/kinds/axes, and there is no
  role-override mechanism. Soften the prose so it doesn't instruct authoring types that
  may not exist.
- BONUS current bug — `roles.toml:154` cites `sq story add`, which is not a real command
  (correct is `sq feature <n> add-story`). Fix.

## Ordering / flag

Contains a HIGH (priority hardcoding, custom-vocab) plus a real current-behaviour command
bug (`sq story add`). The `sq story add` fix + the priority softening are quick wins.

## Dependency note

Regenerates `squads/agents/skills/SKILL-*` and `squads/agents/roles/ROLE-*` snapshots —
shares the generated-snapshot surface with the sq-<type>-skill task; sequence the two to
avoid snapshot merge conflicts.

## Design note

Role prose is genuinely hand-authored guidance (there is no role-override spec today), so
the fix is careful rewording toward role-neutral phrasing / pointing at the active spec's
vocabulary rather than mechanical interpolation. Keep it readable for the bundled default.

## Acceptance

- squads-skill priority guidance no longer states a fixed field name + value list as the
  grammar; the create-example type list and comment-scoping table no longer read as the
  authoritative closed vocab.
- Role prose no longer instructs agents to author specifically-named types that a custom
  spec may not have; `sq story add` corrected.
- Regenerated snapshots committed; full gate green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 369 add-subtask "<title>"`; track with `sq task 369 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-10T02:49:08Z] Elias Python:
  - Fixed roles.toml:154 sq story add -> sq feature <n> add-story (real bug).
  - Genericized squads_skill.md.j2: priority guidance (--priority + values) now derives from spec.fields_for('task')'s ordered field + its collection's badges (falls back to nothing if task carries no ordered field); create-example type list derives from spec.work_types(); comment-scoping table/prose derive kind->host-type + kind fields from spec.subentity_kinds/items.
  - roles.toml: softened architect/tech-lead/reviewer/qa/product-owner responsibility lines that named work types/kinds/axes as though closed vocab (parenthetical 'bundled default'/'in the bundled workflow' framing), keeping the actual bundled commands as illustrative examples -- there's no role-override mechanism so left mission/description prose (e.g. 'ADRs' in mission text) untouched, only touching the cited lines.
  - Regenerated manifest (gen_template_manifest.py) + sq sync snapshots: SKILL-000200-squads.md and ROLE-000002/3/4/5/7.md changed, all diffs spot-checked correct. Updated the role-catalog golden-lock test + role_qa_show.json golden to match. Added 3 behaviour-named tests (custom priority collection shows in guidance not the bundled literal; dropped work type disappears from the create-example list; product-owner cites the real add-story command).
  - Gates green: pyright/ruff/ruff format clean; targeted tests (test_skills, test_role_catalog, test_skill_seeding, test_override_commands incl. manifest freshness, test_squad_ref_hygiene) all pass. Did not run the full suite per instructions.
- [2026-07-10T02:54:32Z] Paul Reviewer:
  - Reviewed uncommitted TASK-369 diff (independent). VERDICT: APPROVE. gates clean (ruff/pyright unaffected — no src .py changed), manifest regenerated, full suite green (exit 0, 0 failures). All four focus questions yes. One LOW nice-to-have test.
  - HIGH bug fixed (Q1): YES. roles.toml:154 product-owner 'sq story add' -> 'sq feature <n> add-story' (the real command); ROLE-000007 snapshot shows 'sq story add' gone from both the extra: block and the rendered Responsibilities. Regression test test_product_owner_role_cites_a_real_add_story_command asserts the old string absent + the real one present.
  - Priority derivation correct + graceful (Q2): YES. Template resolves the task type's FIRST ordered field/collection at render time (spec.fields_for('task') + spec.collection(...)), taking the field code + live badge codes; both usages (create example, 'Set importance') are guarded by {% if _priority.field %} so a task with no ordered field OMITS the sentence rather than crashing. Bundled render reads well and the 'Set importance with --priority urgent|high|medium|low' line is byte-identical (no snapshot diff there). test_squads_skill_priority_guidance_derives_from_active_collection proves a custom 'p0' collection surfaces verbatim with no bundled-literal fallback.
  - Snapshots clean, no drift (Q3): YES. SKILL-000200 + ROLE-2/3/4/5/7 diffs are ONLY the intended vocab-derivation/prose-softening; mission/title/model/color untouched, roster held at 9. The scoping-table row reorder (now spec-declaration order: story/subtask/finding) is cosmetic — same 3 rows/commands, not a regression. create-example '# also:' now spec.work_types()|reject task|sort (same 6 types, alphabetized). spec is correctly threaded into the render (_backend.py:79 spec=spec).
  - Role prose not overclaiming (Q4): softened lines are accurate and read well — architect 'Record significant design decisions (ADRs in the bundled workflow)', tech-lead 'scoped units of work ... (bundled default: sq create task ...)', reviewer 'badge field(s) set (severity in the bundled workflow)', qa 'acceptance criteria (user stories ...)' / 'tracked items (bug items ...)', PO 'sq feature <n> add-story'. Leaving mission/description as bundled-default is a reasonable call (no role-override mechanism). Manifest FRESH (Q5): squads_skill.md.j2 hash regenerated, freshness test passes; version NOT bumped. No ticket IDs in source.
  - LOW (non-blocking): the priority graceful-OMIT path (task declares no ordered field -> sentence dropped) is guarded-by-construction but not covered by a test (the custom-collection test uses ordered=True). A thin test asserting the sentence is absent when task has no ordered field would close it. Optional.
- [2026-07-10T02:55:14Z] Catherine Manager:
  - Reviewer-approved; all focus answers YES (sq story add fixed, priority derivation correct+graceful, snapshots clean/no drift, manifest fresh, version not bumped). Full suite green. F1 (LOW: the priority graceful-OMIT path untested — guarded by construction, display-only, zero correctness risk) accepted as noted, not round-tripped. Landing.
<!-- sq:discussion:end -->
