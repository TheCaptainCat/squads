---
id: TASK-342
sequence_id: 342
type: task
title: CLI derives --<field> filter/sort/badges generically
status: Done
parent: FEAT-327
author: tech-lead
refs:
- ADR-323
- TASK-341:depends-on
description: One parse_badge_code/badge_render for all axes; --<field>/--min-<field>/sort/columns
  from fields_for(); custom-axis verified
subentities:
- local_id: ST1
  title: Generic parse_badge_code/badge_render; --<field>/--min-<field>/sort/columns
    from fields
  status: Done
  story: US2
- local_id: ST2
  title: Verify full CLI surface against a custom badge axis beyond priority/severity
  status: Done
  story: US2
created_at: '2026-07-09T08:20:10Z'
updated_at: '2026-07-09T13:12:13Z'
---
<!-- sq:body -->
## Scope

Make the CLI derive its badge surface **generically from the fields a type or
sub-entity-kind declares** — the `--<field-code>` value/filter options,
`--min-<field-code>` (ordered collections only), sort, and the badge columns
all come from `fields_for(type_or_kind)`, with no hand-written per-axis
`parse_priority`/`parse_severity`/`priority_badge`/`_severity_badge` pairs
left. Delivers US2, including verification against a **custom** badge axis
beyond the two bundled ones.

## Areas / files

- `_cli/_common.py` — collapse `parse_priority`/`parse_severity` into one
  `parse_badge_code(field, code, spec)` and `priority_badge`/`_severity_badge`
  into one `badge_render(field, code, spec)`; validate the given code against
  the field's bound collection, error clearly on an unknown code (listing the
  collection's codes). Column headers come from the field `label`.
- `_cli/_main.py` — `--<field>` create/list/tree filter and the badge column
  in list/tree/`--json` derive from the declared fields of the type being
  listed/created, not a hardcoded `--priority`/`Priority` pair. `--min-<field>`
  threshold filter and sort are offered **only** when the field's collection
  is `ordered` (both bundled defaults are). Options are generated per the
  active spec's fields.
- `_cli/_items.py` — finding `--severity` (create default + update) and the
  finding `Severity` column derive from the `finding` kind's declared fields;
  same generic path as item-level fields.
- `_discussion.py` — the finding summary/head `Severity` column and any
  badge rendering resolve emoji/label from the bound collection via the shared
  `badge_render`, with the graceful raw-code fallback (no `SEVERITY_EMOJI`).
- Any per-type CLI option generation must stay deterministic and handle a type
  that declares **zero** fields (no badge option/column) and a type that
  declares a **non-bundled** field.

## Done criteria

- No hand-written per-axis parse/render pairs remain: `grep -rn
  'parse_priority\|parse_severity\|priority_badge\|_severity_badge'
  src/squads/_cli src/squads/_discussion.py` is empty; the generic
  `parse_badge_code`/`badge_render` (or equivalently named) helpers drive all
  axes.
- `--<field>`, `--min-<field>` (ordered only), sort, and badge columns work
  for **any** field declared in the spec — proven by a test spec that declares
  a custom badge axis (e.g. an `impact` field off a custom `level` collection,
  and/or the ADR-323 `impact`/`urgency`-off-one-collection reuse case) and
  exercises create/update/filter/sort/column for it, not just priority and
  severity.
- A no-override squad's CLI surface (options, columns, filters, sort order) is
  identical to before the feature.
- `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean;
  full suite green.

## Sequencing note

Depends-on the enum-deletion/generic-storage task — the CLI consumes
`fields_for()` and the generic badge-code storage/render that task establishes,
and the old `parse_*`/`*_badge` helpers it replaces are removed there or here
in one sweep. Independent of the migration task (can land before or after it);
the CLI reads the badge code regardless of which on-disk location severity
currently sits in.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 342 add-subtask "<title>"`; track with `sq task 342 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Generic parse_badge_code/badge_render; --<field>/--min-<field>/sort/columns from fields | US2 |
| ST2 | Done |  | Verify full CLI surface against a custom badge axis beyond priority/severity | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Generic parse_badge_code/badge_render; --<field>/--min-<field>/sort/columns from fields

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US2 — CLI derives filter/sort/badges from fields
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Collapse parse_priority/parse_severity into parse_badge_code and priority_badge/_severity_badge into badge_render; generate --<field>/--min-<field> (ordered only)/sort/columns per the type-or-kind's declared fields across _common/_main/_items/_discussion.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Verify full CLI surface against a custom badge axis beyond priority/severity

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — CLI derives filter/sort/badges from fields
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Add a test spec declaring a custom badge axis (e.g. impact off a custom 'level' collection, incl. the impact/urgency-off-one-collection reuse case) and exercise create/update/filter/min/sort/column for it — proving the surface isn't hardwired to priority/severity.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-09T10:40:41Z] Catherine Manager:
  - Carry-over from TASK-341 review (REV-344, LOW/F1): collapse the duplicate emoji-resolution logic between _cli/_common.py::_badge_emoji and _discussion.py::_severity_emoji/_severity_badge as part of this task's generic CLI derivation — the per-axis parse/badge pairs (parse_priority/parse_severity, the two emoji resolvers) should become one spec-field-driven path.
- [2026-07-09T12:15:53Z] Elias Python:
  - Landed: collapsed F1's duplicated per-axis pairs into ONE generic path — _cli/_common.py::parse_priority/parse_severity -> parse_badge_code(collection_code, value); _cli/_common.py::_badge_emoji + priority_badge/severity_badge and _discussion.py::_severity_emoji/_severity_badge -> one discussion.badge_render(collection_code, code, spec, as_label=...) (as_label=True for head/pane-title sites, False for list/panel/summary — preserving the exact casing parity TASK-341 established) plus a resolve_collection(type_or_kind, field_code, spec) that looks up the bound collection from fields_for() instead of assuming field code == collection code.
  - Generic derivation, proven beyond priority/severity: Item.badge_value()/set_badge_value() (new, generic getter/setter — real attribute for priority/severity, extra[code] for any other declared field) let _services/_items.py::_apply_extra drop the old _ITEM_BADGE_ATTR_FIELDS allowlist shim entirely — --set <field>=<code> now works for ANY declared field, not just severity. sq list/sq tree gained --min-priority (new, ordered-only sugar) plus a generic --badge/--min-badge CODE=VALUE (repeatable) escape hatch and --sort CODE, all resolved via ItemFilter's new badges/badge_min tuples + WorkflowSpec.fields_for()/collections rank lookup (ItemFilter.priority field removed, folded into badges). sq show's item panel now loops fields_for(it.type) generically (was a hardcoded priority-then-severity pair) — same order, same raw-code rendering. add_finding's severity default resolves via field.default/collection.default (SubentitiesMixin._field_default, new) instead of a frozen literal — closes the TASK-341-left forward note.
  - Byte-identical proof: full targeted run (priority views, workflow badges, discussion, rendering, tree, custom-type cli/create, cli, collab, show_render, golden_json, golden_rendered_output, graph, title_advisory, bug_workflow, models, custom_status_badges, spine_characterization, service, playbook, status_display_characterization, workflow_spec, load_boundary_vocab) all green with zero golden regen needed — no --priority/--severity output changed. New CLI options (--min-priority/--badge/--min-badge/--sort) are all-optional and additive.
  - Custom-axis test (tests/test_custom_badge_axis.py, ADR-323's own impact/urgency-off-one-collection example): a project override declares a 'level' collection + a brand-new 'incident' type with impact/urgency fields both bound to it. Exercises --set impact=high/urgency=low (generic value setting + unknown-code rejection), sq show's generic panel row, --badge impact=VALUE exact filter, --min-badge urgency=VALUE threshold filter (ordered-collection rank), --sort urgency, on both list and tree — plus a second test pinning that --priority/--min-priority keep working unchanged for the bundled axis alongside the generic escape hatch.
  - Files: src/squads/_discussion.py, _cli/_common.py, _cli/_main.py, _cli/_items.py, _cli/_create.py (mechanical parse_priority rename only), _models/_item.py, _services/_base.py, _services/_items.py, _services/_subentities.py; tests/test_custom_badge_axis.py (new) + test_priority_views.py/test_discussion.py/test_rendering.py/test_tree.py updated for the renamed/collapsed API. Gates: pyright + ruff check + ruff format --check all clean. Unverified: full suite (left to the main loop per instructions).
- [2026-07-09T12:40:58Z] Paul Reviewer:
  - Reviewed in REV-346 → APPROVED. Byte-identical default (golden + smoke), F1 collapse confirmed (grep clean), generic derivation proven end-to-end by the custom incident/impact/urgency axis test, gates + targeted suites green.
  - 5 non-blocking findings recorded on REV-346: F1(med) Collection.ordered is never enforced (--min-badge/--sort rank by declaration order regardless — no impact on the all-ordered defaults); F2-F5(low) unvalidated generic --badge, per-field-option interpretation, badge helpers misplaced in _discussion (deferred to a _badges.py relocation — TASK-345 currently Cancelled), and a ticket ID in the new test docstring. None block the merge.
- [2026-07-09T12:51:26Z] Elias Python:
  - REV-346 F1/F5 fixed (per Catherine's routing): F1 - spec load now fails closed on ordered=false (_workflow/_models.py::_check_field_collections), with 2 new tests in test_workflow_badges.py; F5 - dropped the ticket-ID prefix from test_custom_badge_axis.py's docstring + fixed test_graph.py's stale priority_badge() reference. F2/F3/F4 left untouched (deferred/accepted separately). Gates (pyright/ruff/format) clean; targeted (workflow_badges, workflow_spec, load_boundary_vocab, custom_badge_axis, graph) green. Still InReview, uncommitted.
- [2026-07-09T12:56:14Z] Elias Python:
  - Hygiene follow-up: reworded the F1 fix's comment at _workflow/_models.py (ordered-collection check) to drop the ADR id/section reference the full suite flagged (squad/ticket IDs banned outside squads/**) — kept the same explanation, no ADR-3xx/§3 text. test_squad_ref_hygiene.py green; pyright/ruff/format re-confirmed clean. Still InReview, uncommitted.
<!-- sq:discussion:end -->
