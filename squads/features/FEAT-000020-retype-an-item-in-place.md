---
id: FEAT-000020
sequence_id: 20
type: feature
title: Retype an item in place
status: Ready
parent: EPIC-000012
author: product-owner
priority: medium
refs:
- FEAT-000019:depends-on
description: 'sq <type> <n> retype <new-type>: fix a wrongly-filed item keeping its
  number, discussion and incoming refs'
subentities:
- local_id: US1
  title: As a user who filed work under the wrong type, I want to retype it in place,
    so that the number, body and discussion survive the fix
  status: Todo
- local_id: US2
  title: As a teammate whose items reference the retyped one, I want every incoming
    ref, parent link and prose mention rewritten to the new ID, so that nothing dangles
  status: Todo
created_at: '2026-06-10T13:24:54Z'
updated_at: '2026-06-11T07:54:54Z'
---
<!-- sq:body -->
## Problem

Items get filed as the wrong type — a bug created as a task, a guide that should be an ADR. Today
the only fix is delete-and-recreate, which loses the number, the discussion history, and breaks
every incoming ref.

## Value

`sq <type> <n> retype <new-type>` fixes the classification in place: the globally-unique number is
the durable identity, so only the ID prefix flips (`TASK-000020 → BUG-000020`), the file moves to
the right folder, and **all incoming references — other items' refs, children's parent, prose
mentions — are rewritten** so nothing dangles. The verb joins the CLI grammar before 1.0 freezes it.

## Scope (per the approved implementation plan)

- Work-item types only (epic, feature, task, bug, decision, review, guide).
- Status carries when the workflows match (task↔bug, feature↔epic); otherwise resets to the new
  type's initial status, announced loudly.
- Refusals with actionable errors: item has sub-entities; parent invalid for the new type; a child
  would end up with an invalid parent.
- Body stays verbatim (marker-safe); a missing sub-entity container is appended when retyping into
  feature/task/review.
- A system comment records `retyped OLD → NEW` in the discussion.
- Interplay: after retype, `sq task 20` still silently resolves the bug — that wrong-type
  addressing error is FEAT-000019's shared-resolver decision (op-pierre: error with a pointer);
  no hard ordering dependency, but 19 makes the retype announcement enforceable.

## Acceptance

- `sq <type> <n> retype <new-type>` works for every work-item pair, keeping number, body,
  discussion and refs; output states the new ID, carried/reset status, and rewritten refs.
- All refusal cases error cleanly with next-step hints; `sq check` is clean and `sq repair` stable
  after any retype.
- Covered by service tests + CLI smoke; pyright/ruff gates stay green; documented in the workflow
  docs.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 20 add-story "As a <role>, I want … so that …"`; track with `sq feature 20 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a user who filed work under the wrong type, I want to retype it in place, so that the number, body and discussion survive the fix |
| US2 | Todo |  | As a teammate whose items reference the retyped one, I want every incoming ref, parent link and prose mention rewritten to the new ID, so that nothing dangles |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a user who filed work under the wrong type, I want to retype it in place, so that the number, body and discussion survive the fix

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
**Acceptance:** `sq task <n> retype bug` yields BUG-<same number>, file moved to bugs/, body verbatim, discussion intact + a system comment recording the change; status carried on same-workflow pairs, reset-and-announced otherwise; sub-entity/parent/children conflicts refuse with actionable errors.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a teammate whose items reference the retyped one, I want every incoming ref, parent link and prose mention rewritten to the new ID, so that nothing dangles

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
**Acceptance:** other items' refs (kinds preserved), children's parent fields and prose mentions all show the new ID after retype; sq check clean and sq repair stable afterwards.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-10T13:29:39Z] Nina Product:
  - Design exploration for this feature exists (implementation plan drafted 2026-06-10, reviewed by op-pierre); attach it when the feature moves to Ready. Like the rest of EPIC-000012, no work starts yet.
<!-- sq:discussion:end -->
