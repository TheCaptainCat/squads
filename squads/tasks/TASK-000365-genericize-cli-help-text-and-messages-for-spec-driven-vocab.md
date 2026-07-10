---
id: TASK-365
sequence_id: 365
type: task
title: Genericize CLI help text and messages for spec-driven vocab
status: Done
parent: FEAT-336
author: tech-lead
created_at: '2026-07-10T02:00:09Z'
updated_at: '2026-07-10T03:49:06Z'
---
<!-- sq:body -->
## Scope

Surface 1 of the REV-360 audit: CLI `--help` text, command docstrings, next-step hints,
and the `sq <kind> show` display pane. Make every enumerated value/vocab reference derive
from the active spec (or drop the misleading enumeration) so help and enforcement agree.
Files: `_cli/_items.py`, `_cli/_create.py`, `_cli/_main.py`, `_cli/_override.py`,
`_cli/_common.py`. Independent of the other FEAT-336 tasks (disjoint files).

## Covered REV-360 findings

- MEDIUM — `_cli/_items.py:262-266` — retype NEW-TYPE help hardcodes
  "epic|feature|task|bug|decision|review|guide"; validation two lines away derives
  targets from `get_active_spec().work_types()`. Make help agree.
- MEDIUM — `_cli/_items.py:168` (+ siblings `_create.py:63`, `_create.py:243`,
  `_main.py:358` & `415` list/tree `--priority`, `_main.py:360` & `417`
  `--min-priority`) — `--priority` help hardcodes "urgent|high|medium|low"; value is
  validated via `parse_badge_code("priority", …)` against the active spec.
- MEDIUM — `_cli/_items.py:545` (+ `_items.py:618-619` finding update) —
  `add-finding --severity` help hardcodes "critical|high|medium|low|info".
- LOW — `_cli/_items.py:496` (add_story) `:522` (add_subtask) `:552` (add_finding)
  docstrings hardcode the parent type name ("on this feature/task/review").
- LOW — `_cli/_main.py:307` — `sq init` success hint hardcodes `sq create task "…"`.
- LOW — `_cli/_main.py:865` (reflog `--item` "e.g. TASK-<n>") and `_override.py:50`
  ("e.g. 'items/task.md.j2'") — illustrative example prefixes bake in `task`.
- ADDED (see REV-360 comment) — `_cli/_common.py:384` `print_subentity` hardcodes a
  severity-only meta line in the `sq <kind> show` pane; it won't display any other
  declared field on a custom sub-entity kind. Derive the displayed field(s) from the
  kind's declared fields.

## Guidance

- Prefer deriving the enumerated values from the active spec collection/`work_types()`;
  where a help string can't easily interpolate spec data, drop the hardcoded enumeration
  in favour of a spec-pointing phrasing rather than lying about accepted values.
- Illustrative-example prefixes (reflog/override) are LOW: acceptable to keep a generic
  phrasing rather than a specific bundled prefix.

## Acceptance

- No CLI help/docstring enumerates bundled type/priority/severity values as the fixed
  grammar where the underlying validation is spec-driven.
- `print_subentity` shows all declared fields for the sub-entity kind, not just severity.
- Full gate green (pytest/pyright/ruff check/ruff format).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 365 add-subtask "<title>"`; track with `sq task 365 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-10T03:21:21Z] Elias Python:
  - Starting: CLI help-surface genericization (_items.py, _create.py, _main.py, _override.py, _common.py print_subentity).
- [2026-07-10T03:40:31Z] Elias Python:
  - Done: retype NEW-TYPE help + update/create --priority help now derive from the resolved spec in build_item_app/_create.py (byte-identical for bundled types; correct for a custom-declared type or a field re-bound to a different collection).
  - list/tree --priority/--min-priority (cross-type, static) de-enumerated per guidance: 'Priority code (as defined by your workflow's priority collection).'
  - add-story/add-subtask/add-finding docstrings + add-finding/finding-update --severity help were already generic (landed in TASK-342, pre-dating this REV) — no change needed there.
  - sq init hint now says 'sq create --help to see your item types' instead of naming task; reflog --item help/docstring use a generic <PREFIX>-<n>; _override.py examples use 'items/<type>.md.j2'.
  - print_subentity (_common.py) now loops spec.fields_for(kind) and renders every declared field via badge_value(), not just severity — byte-identical for story/subtask/finding, shows a custom kind's own field (e.g. urgency) too.
  - Added tests/test_cli_help_vocab.py (retype/priority help derivation + list/tree de-enumeration + init hint) and one test in test_custom_subentity_kind_cli.py for the print_subentity generalization.
  - Gates green: pyright, ruff check, ruff format --check, targeted CLI/override/custom-type/retype/ref-hygiene suites. Did not run the full suite (main loop's job) or commit.
- [2026-07-10T03:47:47Z] Paul Reviewer:
  - Reviewed uncommitted TASK-365 diff (independent). VERDICT: APPROVE. gates clean (pyright/ruff/format), full suite green (exit 0, 0 failures — the full-suite bar the last two FEAT-336 tasks missed). Byte-identical where it matters; de-enumerations honest; one pre-existing timing gap worth a tracked follow-up (below).
  - Byte-identical (Q1) CONFIRMED by direct resolution: retype help sorted by (order,name) = 'epic|feature|task|bug|decision|review|guide' exactly; item-level --priority help = 'Priority: urgent|high|medium|low.' (create + update, from the priority collection's badge codes); print_subentity for finding renders 'severity: <value>' (field.label.lower()='severity' via badge_value('severity')=info.severity) — stories/subtasks unchanged (no fields). test_retype_help_lists_bundled_work_types_in_order + the priority-help tests lock this.
  - print_subentity generalization (Q3): correct — loops get_active_spec().fields_for(kind) rendering each declared field via badge_value, byte-identical for built-ins AND now shows a custom kind's field (test_kind_show_meta_line_displays_a_declared_non_severity_field asserts 'urgency: high'). This also closes the print_subentity gap I flagged deferred on TASK-361 (REV-360).
  - De-enumeration honest (Q2): the de-enumerated static surfaces (list/tree --priority/--min-priority, init hint, reflog --item, override scaffold) all point at the spec ('as defined by your workflow's priority collection', 'sq create --help to see your item types', '<PREFIX>-<n>', 'items/<type>.md.j2') rather than substituting a different hardcoded list. Right call — list/tree priority is cross-type (no single collection binding), so a spec-pointing phrase beats a fake enumeration. No --help golden asserts these (confirmed: suite green with the changed text). No ticket IDs in source.
  - Timing gap (Q4): REAL, worth a tracked follow-up — LOW-MEDIUM. build_item_app resolves spec = common.get_active_spec() (module global), which returns bundled when _bind_active_spec hasn't run — so on a cold first-in-process introspection of a CUSTOM type (e.g.  where the root callback is short-circuited), the custom type's command tree/help is built from the bundled spec: missing its add-<kind> surface, wrong retype targets/priority help. Does NOT affect enforcement (handlers re-read the live spec) or data, and real command dispatch binds the spec first. PRE-EXISTING (build_item_app already used get_active_spec for subentity registration); this task only widens the derived surface. Correctly OUT OF SCOPE here (the fix touches _cli/__init__.py — thread _resolve_spec_for_ctx(ctx) into build_item_app, or bind before subcommand build). Recommend filing it; not a blocker for TASK-365. The dev's test-side workaround (bind via a prior invoke) is appropriate given the scope boundary.
- [2026-07-10T03:47:59Z] Paul Reviewer:
  - Correction (shell redirect mangled the timing-gap bullet): Q4 timing gap is REAL, worth a tracked follow-up, LOW-MEDIUM. build_item_app resolves its spec from common.get_active_spec() (the module global), which returns the bundled spec when _bind_active_spec has not yet run. So on a cold first-in-process introspection of a CUSTOM type (a fresh-process sq CUSTOMTYPE --help where the root callback is short-circuited), that type command tree/help is built from the bundled spec: its add-KIND surface is missing and retype-targets/priority-help are wrong. It does NOT affect enforcement (handlers re-read the live spec) or data, and real command dispatch binds the spec first. It is PRE-EXISTING (build_item_app already read get_active_spec for sub-entity registration); this task only widens the derived surface. Correctly OUT OF SCOPE for TASK-365 (the fix touches _cli/__init__.py: thread _resolve_spec_for_ctx(ctx) into build_item_app, or bind the spec before subcommand build). Recommend filing a follow-up; not a blocker. The dev test-side workaround (bind via a prior invoke) is appropriate given the scope boundary.
- [2026-07-10T03:49:05Z] Catherine Manager:
  - Reviewer-approved; full suite green; byte-identical where it matters (retype/priority help, print_subentity built-ins), de-enumerations honest. print_subentity generalization also closed the earlier REV-360 finding. F1 (pre-existing cold-first-dispatch timing gap: custom-type help built from bundled spec — help-only, no enforcement/data impact) filed as BUG-371 for scheduling, correctly out of this task's scope. Landing.
<!-- sq:discussion:end -->
