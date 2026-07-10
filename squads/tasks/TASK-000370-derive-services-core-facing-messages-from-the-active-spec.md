---
id: TASK-370
sequence_id: 370
type: task
title: Derive services-core facing messages from the active spec
status: Draft
parent: FEAT-336
author: tech-lead
created_at: '2026-07-10T02:00:12Z'
updated_at: '2026-07-10T02:02:38Z'
---
<!-- sq:body -->
## Scope

Surface 5 of the REV-360 audit — services-core facing messages/metadata that hardcode
bundled vocab even though the required value is already resolved from the spec one line
away. Derive the vocab from the active spec. Files: `_workflow/_models.py` (parent_hint),
`_services/_subentities.py`, `_models/_metadata.py`, `_services/_maintenance.py`,
`_services/_results.py`. Independent of the other FEAT-336 tasks (disjoint files).

## Covered REV-360 findings

- MEDIUM — `_workflow/_models.py:782-784` (`WorkflowSpec.parent_hint`) — hardcodes ref-kind
  names + the whole hint sentence ("link a bug or review with `sq ref add … --kind
  fixes|addresses`") even though `RefRule` carries a per-rule `hint` field populated for
  this purpose (default_workflow.toml 295-296). Use the spec-declared hint instead of
  re-detecting literal fixes/addresses + emitting bundled "bug or review" prose. Feeds
  `sq check` output and retype refusals.
- MEDIUM — `_services/_subentities.py:473` (`_validate_subtask_story`) — message
  `"{task.id}'s parent is a {kind}, not a feature"` hardcodes "feature" though
  `required = self.spec.item_parent_required(task.type)` is resolved one line above.
- MEDIUM — `_models/_metadata.py:42-47` (`EXTRA_FIELDS`) — settable `extra` metadata keyed
  by hardcoded type names 'guide' (X.TAGS) / 'review' (X.TARGET_REF); both are overridable
  work types. A renamed guide→doc / review→audit makes `sq update --set tags=…` /
  `--set target_ref=…` rejected and the fields unsettable. This drives real accept/reject
  behaviour + the valid-field error list — key it on spec-declared type identity, not the
  bundled literal.
- LOW — `_services/_subentities.py:467` — message "{task.id} has no feature parent; …"
  hardcodes "feature"; required parent type is available via `item_parent_required`.
- LOW — `_services/_maintenance.py:1042` & `:1048` (`_check_subtask_stories`) — `sq check`
  messages hardcode "task"/"feature"/"subtask"/"user story" though `required_parent` is
  resolved at 1036.
- LOW — `_services/_maintenance.py:1098` (`_check_decisions`) — warning hardcodes the
  status label "Superseded" though gated on `status_role(...)=='superseded'` with the real
  status in `item.status`.
- LOW — `_services/_results.py:57,70` (`GraphNode.priority` / `to_dict`) — carries a single
  hardcoded `priority` badge field + serialises the fixed key 'priority'; a project on a
  different/additional badge axis sees a permanently-null 'priority' in `sq graph --json`.
  (TreeNode carries the whole Item and stays generic — GraphNode-specific.)

## Ordering / flag

`EXTRA_FIELDS` (MEDIUM) is the one with real behavioural impact (fields become unsettable
under a renamed type), not just message wording — prioritize it within this task. The rest
are message-accuracy fixes.

## Out of scope (REV-360 INFO — sanctioned deferred, do NOT fix here)

- `_base.py:54-58` SUBENTITY_CONTAINER / `_retype.py:26-30` _CONTAINER_HEADINGS /
  `_workflow/__init__.py:50` _SUBENTITY_KINDS — custom sub-entity-kind support is a
  documented deferred non-goal; these stay bundled-keyed.
- `_workflow/_models.py:567-573` _SIDE_PRIORITY — cosmetic ordering with deterministic
  fallback; output stays coherent.

## Acceptance

- Each cited message names the spec-resolved required type/status/kind, not the bundled
  literal (verified on a spec that renames feature/task/guide/review and a superseded-role
  status).
- `EXTRA_FIELDS`/`settable()` resolve by spec type identity so tags/target_ref stay
  settable on a renamed host type.
- `GraphNode` surfaces the type's actual badge axis (or is made generic) in `sq graph
  --json`.
- Full gate green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 370 add-subtask "<title>"`; track with `sq task 370 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
