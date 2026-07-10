---
id: TASK-369
sequence_id: 369
type: task
title: Genericize squads skill and role prose for spec-driven vocab
status: Draft
parent: FEAT-336
author: tech-lead
created_at: '2026-07-10T02:00:11Z'
updated_at: '2026-07-10T02:02:38Z'
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
<!-- sq:discussion:end -->
