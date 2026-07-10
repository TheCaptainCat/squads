---
id: TASK-364
sequence_id: 364
type: task
title: Verify cheatsheet altitude and default/custom-vocab renders
status: Draft
parent: FEAT-334
author: tech-lead
created_at: '2026-07-10T02:00:03Z'
updated_at: '2026-07-10T02:02:35Z'
---
<!-- sq:body -->
## Scope

Verification/sign-off task for the genericized workflow cheatsheet (sibling
implementation task under this feature). Confirms the redesign hits its distinct
altitude and does not regress the bundled-default reader — this is the human /
tech-writer read-through that FEAT-334 US2/US3 explicitly require in addition to the
automated golden diff.

## Verification steps

- US1 (custom vocab): render the cheatsheet against a spec that renames, drops, and
  adds item types/roles (not the bundled default) and inspect output — no blank gaps,
  no hardcoded bundled words, every custom type with playbook data gets a line.
- US2 (altitude): review the rendered cheatsheet side by side with the generated
  `sq-<type>` skills; confirm it is a condensed cross-type overview (one line per
  type-role pairing capturing who acts + primary handoff), not a second lower-fidelity
  copy of the full enter/do/handoff/watch lists. Confirm the implementation records
  the chosen altitude/summarization rule.
- US3 (bundled quality): render `sq workflow` and the `squads` skill cheatsheet for
  the bundled unmodified squad; tech-writer read-through for voice/readability — it
  must stay coherent prose/tables, at least as good as today, not a raw data dump.

## Acceptance

- Tech-writer signs off (comment on this task) that the default cheatsheet reads at
  least as well as today and the altitude is distinct from the `sq-<type>` skills.
- Custom-vocab render inspected and confirmed accurate + non-blank.

## Notes

Depends on the implementation task landing first. This is a review/QA-shaped task
(tech-writer input); no source changes expected here beyond any tweaks the read-through
surfaces (which should fold back into the implementation task).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 364 add-subtask "<title>"`; track with `sq task 364 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
