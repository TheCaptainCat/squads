---
id: TASK-366
sequence_id: 366
type: task
title: Pass active spec to item templates and fix hardcoded vocab
status: Draft
parent: FEAT-336
author: tech-lead
created_at: '2026-07-10T02:00:09Z'
updated_at: '2026-07-10T02:02:36Z'
---
<!-- sq:body -->
## Scope

Surface 2 of the REV-360 audit: item + sub-entity Jinja templates. The root cause of
most of these is that the item-template render context does NOT pass the active spec —
see `_services/_base.py:384-385`
(`render(self._template_for(item_type), item=item, description=description, extra=item.extra)`).
This task does the SHARED PLUMBING FIX (thread the active spec into the item-template
render context) first, then fixes each template that needs it. Files:
`_services/_base.py` (plumbing), `_rendering/templates/items/review.md.j2`,
`items/feature.md.j2`, `items/task.md.j2`, `subentities/head.md.j2`.

## Covered REV-360 findings

- HIGH — `items/review.md.j2:13` — findings severity legend fully hardcoded
  (`🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info`). Post-FEAT-327 severity is a
  spec-defined Collection (values/labels/emoji overridable). Render the legend from the
  active spec's severity collection. Requires the plumbing.
- MEDIUM — `subentities/head.md.j2:5` — severity line hardcodes the axis LABEL
  (`**Severity:** …`); the value is already resolved generically via
  `_discussion.set_head`. Pass the collection's label through so a renamed axis
  (e.g. "Impact") relabels the head. (The set_head path already has spec access —
  this is a template + set_head label plumbing fix, distinct from the item-template
  render context above.)
- LOW — `items/review.md.j2:15` — add-finding hint hardcodes `--severity high`; pick a
  valid value from the spec's severity collection (needs the plumbing).
- LOW — `items/feature.md.j2:9` and `items/task.md.j2:9` — scaffold hints hardcode the
  sub-entity kind/command (`add-story`/`story <n>`, `add-subtask`/`subtask <n>`); the
  kind is spec-driven via `item_subentity_kind(type)`. Derive from the spec (needs the
  plumbing).

## Dependency note

The item-template-render-context plumbing (spec into `_base.py:384` render call) is the
shared prerequisite for the review-legend, review-hint, and feature/task scaffold-hint
fixes — do it first, in this task. No OTHER FEAT-336 task depends on it (it is
self-contained here). The `head.md.j2` label uses the separate set_head path.

## Acceptance

- Scaffolded review body renders a severity legend derived from the active spec
  (verified against a spec with customized severity values/emoji).
- head badge label reflects the collection's declared label under a renamed axis.
- feature/task scaffold hints name the spec's actual sub-entity kind.
- Byte-identical output on the bundled default spec (no golden churn beyond intended);
  full gate green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 366 add-subtask "<title>"`; track with `sq task 366 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
