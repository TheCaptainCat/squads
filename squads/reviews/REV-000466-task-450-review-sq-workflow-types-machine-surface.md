---
id: REV-466
sequence_id: 466
type: review
title: 'TASK-450 review: sq workflow types machine surface'
status: Approved
author: reviewer
refs:
- TASK-450
subentities:
- local_id: F1
  title: Human table renders whole orders as floats (10.0)
  status: Open
  severity: low
created_at: '2026-07-17T15:46:31Z'
updated_at: '2026-07-17T15:49:02Z'
---
<!-- sq:body -->
Independent review of TASK-450 — the new frozen `sq workflow types` type-catalog surface, against Accepted ADR-459. Scope: src/squads/_cli/_workflow_cmd.py, tests/goldens/workflow_types.json, tests/cli/test_workflow_types_cli.py, tests/cli/test_json_output_shape.py, CHANGELOG.md. (_workflow/_models.py not touched — order/is_meta already existed.)

Contract (ADR-459) verified end-to-end against live output from a fresh scratch squad:
- Bare JSON array, one object per declared type; fields exactly {type, order, prefix, reserved}.
- Ascending resolved order (type-name tiebreak): epic..guide 10-70, role/skill/operator 80-100.
- ALL declared types incl. reserved meta-types; reserved = ItemSpec.is_meta.
- order is a JSON number or null (present, not omitted) — null for +inf, dev-tested via a constructed spec (incident) that sorts last.
- Spec-driven: reads get_active_spec().items, no hardcoded type list.
- Default (no --json) prints a human Rich table; additive-superset — no existing golden changed (only tests/goldens/workflow_types.json added; the only source removal is help-text, replaced by an expanded version).
- Golden byte-frozen + wired into the shared shape harness; field-set pinned to a module tuple and traced to real ItemSpec fields.

Gates (scoped): pytest test_workflow_types_cli.py + test_json_output_shape.py + tests/meta all green; pyright strict + ruff check/format clean on touched files; sq check clean.

Recommended verdict: APPROVE. One Low cosmetic nit (F1), non-blocking.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 466 add-finding "…" --severity medium`; track with `sq review 466 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Open |  | Human table renders whole orders as floats (10.0) |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Human table renders whole orders as floats (10.0)

<!-- sq:finding:F1:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
The human Rich table prints ItemSpec.order (a float) via str(), so whole values show as '10.0', '20.0', etc. Cosmetic only — the --json contract deliberately uses float (order can be 25.5 for insertion between types), the human table is NOT part of the frozen golden, and no ADR-459 requirement is violated. Optional polish: render whole floats as ints in the table (e.g. int(order) when order.is_integer()). Non-blocking; approver's call whether to bother.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
