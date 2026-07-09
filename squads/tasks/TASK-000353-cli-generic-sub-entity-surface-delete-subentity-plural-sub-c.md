---
id: TASK-353
sequence_id: 353
type: task
title: 'CLI: generic sub-entity surface; delete _SUBENTITY_PLURAL/_SUB_COLS'
status: Done
parent: FEAT-212
author: tech-lead
refs:
- TASK-351:depends-on
- TASK-352:depends-on
subentities:
- local_id: ST1
  title: add-<kind> verb built dynamically from spec; e.g. incident add-action
  status: Todo
  story: US1
created_at: '2026-07-09T21:31:33Z'
updated_at: '2026-07-09T23:51:01Z'
---
<!-- sq:body -->
ADR-348 §5 CLI half + FEAT-212 AC1/AC2/AC3: build the whole sub-entity CLI surface generically from the resolved SubentityKindSpec, and delete the last static per-type vocabulary artifacts. This is where `sq incident <n> add-action ...` starts working with no code change.

## Scope

Delete `_SUBENTITY_PLURAL` (FEAT-212's named deliverable — the last static per-type vocab artifact; op-pierre confirmed the boundary) and `_SUB_COLS`. In `build_item_app(item_type)`, resolve the kind via `spec.item_subentity_kind(item_type)` -> `SubentityKindSpec` and build the surface from it.

`add-<kind>`: base flags (title, --assignee, -m/--message, --file, --json) + one `--<field-code>` option per declared field (ADR-323-derived, same as item-level field flags) + `--story` iff `maps_parent_story`. Replaces the three hand-written _register_add closures.

`<plural>` list verb + the nested `<kind> <n> ...` subgroup (show/update/body/comment) built the same generic way; `update` derives its `--<field-code>` flags identically. Replaces _register_update's per-kind branches.

All verbs call the **public kind-taking generic service methods** (TASK-351) instead of `getattr(svc, f"list_{plural}"|f"get_{kind}"|f"set_{kind}_body")`. The list table consumes the shared field-driven column derivation from TASK-352.

Use the new `subentity_plural` resolver accessor (add it to the resolver surface if not already present) for the plural vocab; no _SUBENTITY_PLURAL fallback remains.

## Files owned

- src/squads/_cli/_items.py (_SUBENTITY_PLURAL + _SUB_COLS deleted; _register_subentity/_register_add/_register_update/_register_sub_verbs/_sub_table generic field-driven; getattr-per-kind dispatch replaced with the public service surface)

## Acceptance

- AC1: a custom type declaring a custom kind gets `sq <type> <n> add-<kind> ...` + a summary table with derived columns, no code change.

- AC2: update/body/comment resolve the kind from the spec for built-in and custom kinds.

- AC3: _SUBENTITY_PLURAL deleted; plural vocab comes from the subentity_plural resolver accessor.

- AC4: built-in story/subtask/finding CLI verbs, flags, and output unchanged.

- Full suite green (add a CLI smoke test for a custom-kind add-<kind> per CLAUDE.md).

## Depends on

TASK-351 (public kind-taking service surface) and TASK-352 (shared column derivation); transitively TASK-349.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 353 add-subtask "<title>"`; track with `sq task 353 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | add-<kind> verb built dynamically from spec; e.g. incident add-action | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — add-<kind> verb built dynamically from spec; e.g. incident add-action

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — As a project admin, I want to define custom sub-entity kinds for my custom types in TOML
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-09T23:42:41Z] Elias Python:
  - Implemented: _cli/_items.py rebuilt generically off spec.item_subentity_kind()/subentity_kinds[kind] — add-<kind>/<plural>/<kind> <n> show|update|body|comment all built from the resolved SubentityKindSpec via a dynamic inspect.Signature (one --<field-code> Option per declared field + --story iff maps_parent_story), replacing the three hand-written closures + getattr(svc, f'...{kind}') dispatch with svc.add_block/list_blocks/get_block/update_block/set_block_body. _SUBENTITY_PLURAL and _SUB_COLS deleted; plural vocab via new WorkflowSpec.subentity_plural(kind); list table now shares discussion.summary_columns/summary_row with the body summary (fixes the old CLI-vs-body Story-column drift).
  - F2 gaps closed: threaded self.spec into add_block/set_block_body's next_local_id/build_block/body_placeholder calls and _maintenance.py's unwritten-body check; _cli/_common.py's _subentity_pane_title_raw and _print_full_panes are now spec-generic (get_block, no kind==literal). Extra fix beyond the enumerated F2 list, required for AC2: _services/_collab.py comment()/_discussion_tag() gained an additive generic sub=(kind, local_id) pair (backward-compatible with story=/subtask=/finding=) since the sub-entity comment verb had no way to target a custom kind otherwise. Also promoted SubentitiesMixin._field_default to public field_default (called generically from the CLI's per-field default resolution, same outcome as before for finding's severity).
  - Added tests/test_custom_subentity_kind_cli.py: a custom 'incident' type + 'action' kind (own lifecycle/completion/plural/local_prefix, own item template for the container section) exercised end-to-end — add-action, actions list (table + --json), action <n> update/body/comment, show --full — all with zero source change beyond the project's own workflow.toml + template override.
  - Fast gates green: pyright/ruff check/ruff format clean; targeted tests green (test_cli.py, test_custom_type_cli.py, test_custom_subentity_kind_cli.py, test_collab.py, test_workflow_badges.py, test_subentity_kind_spec_driven.py, test_custom_badge_axis.py, test_custom_status_badges.py, test_unwritten_subentity_body_check.py, test_show_render.py, test_status_display_characterization.py, test_title_advisory.py, test_retype.py, test_spine_characterization.py, test_workflow_spec.py, test_status_banner_check.py, test_discussion.py, test_golden_json.py, test_migrations.py, test_workflow_override.py, test_workflow_lint.py, test_workflow_authoring_prose.py, test_squad_ref_hygiene.py).
  - Left InProgress for review: flag for @reviewer — (1) the dynamic-signature (__signature__ monkeypatch) technique in _register_add/_register_update is new to this codebase, no prior precedent, worth a careful look; (2) a declared field whose code isn't 'severity' has no CLI storage yet (SubEntity has no generic field-code store) — add-<kind>/update raise a clear SquadsError rather than silently dropping or crashing, documented via _STORED_FIELD_CODES; (3) add-<kind>'s --help summary line is now generic ('Scaffold a <kind> on this item.') vs the old kind-specific wording — cosmetic, no test depends on it, flagging per AC4's 'output unchanged' scope. Full suite not run by me per instructions — over to the main loop.
- [2026-07-09T23:49:16Z] Paul Reviewer:
  - Reviewed uncommitted TASK-353 diff (independent, on committed TASK-352). VERDICT: APPROVE for the code as scoped. Gates clean (pyright/ruff/format), full suite green (exit 0, 0 failures), AC1/AC2/AC3/AC4 met. One MEDIUM feature-completeness finding for the coordinator (§4) + two low nits below.
  - Dynamic __signature__ builder (flag 1): SAFE and correct. Each _register_add/_register_update builds a FRESH params list with a FRESH typer.Option per field (_field_param) and per base flag — no shared-mutable-default or cross-kind closure bleed; the _add/_update closures capture their own kind/spec/fields. Typer reads func.__signature__ (confirmed by the passing suite). Built-in add-story/add-subtask/add-finding + update come out byte-identical in flags, order, and behaviour (story before assignee on subtask; --severity on finding; --story/--no-story only when maps_parent_story) — full suite's existing CLI tests pass unchanged.
  - AC1 end-to-end GENUINELY proven: tests/test_custom_subentity_kind_cli.py declares incident+action purely via .overrides/workflow.toml + a custom item template (zero source change) and exercises add-action, actions list (table + --json), action update --status (against the custom 'action' machine), body, comment (generic (kind,local_id) tag), show, and show --full. Real test, not a stub. AC3: _SUBENTITY_PLURAL/_SUB_COLS/_severity_collection/_SEVERITY_FIELD_CODE all deleted (grep-clean); plural vocab now only from spec.subentity_plural (_models.py:829).
  - _collab.py sub param (flag 4): CLEAN + backward-compatible. Additive sub:(kind,local_id) folded into the same >1 mutual-exclusion guard; story=/subtask=/finding= call sites untouched. Genuinely needed for AC2 custom-kind comments, and byte-identical for built-ins — markers.story_tag/subtask_tag/finding_tag all return f'{kind}:{local_id}', exactly what the sub path builds. Not a smell.
- [2026-07-09T23:49:33Z] Paul Reviewer:
  - F1 (MEDIUM — feature-completeness/tracking, NOT a defect in this diff): ADR-348 §4 (generic SubEntity field-code store, analogous to the shipped Item.badge_value) is unassigned across TASK-349..354 (TASK-354 is vulture/gates only). Consequence: a custom kind can DECLARE a non-severity field — it renders as an always-empty column — but CANNOT be set (add-<kind>/update raise 'no CLI storage yet', _items.py:504/676). Fail-loud is the RIGHT interim behaviour (never silently drop a value). But FEAT-212 is NOT materially complete without §4 — a declarable-but-unsettable field is a half-capability, asymmetric with the already-generic item axis. Coordinator: either file a §4 task before FEAT-212 closes, or record an explicit scope amendment (severity-backed sub-entity fields only) with §4 tracked as a named follow-up. My read: don't close FEAT-212 silently on the half.
  - F2 (LOW, test gap): the new fail-loud path SquadsError('<kind>'s '<code>' field has no CLI storage yet') at _items.py:504 (add) and :676 (update) has NO test — the e2e test uses a fieldless custom kind. Add a thin test: a custom kind declaring a non-severity field, then add-<kind> --<code> X exits non-zero with that message. Cheap insurance on a deliberate user-facing error branch.
  - F3 (LOW/nit, cosmetic help drift, AC4 borderline): the generic _field_param sets --severity help to 'Severity badge code.' (was 'critical|high|medium|low|info (defaults to the spec's severity default).'), and add-story/add-subtask title-arg help collapsed to 'Optional short label; detail in body.' (were kind-specific). Behaviour identical; only --help text changes. Acceptable, but if AC4 'output unchanged' is read strictly, worth a one-line help tweak (e.g. keep the enum hint for the severity column).
  - List-table change (flag 6): DRIFT-FIX, not a regression — _sub_table now shares discussion.summary_columns/summary_row. Data columns are byte-identical per kind; only the header labels change (local-id col 'ID'->kind.title(); title col 'Subtask'/'Story'/'Finding'->'Title'), unifying the CLI list table with the body :summary. No test asserted the old headers (grep-clean). Scope-disciplined; no ticket IDs in source (grep-clean); F2 spec-threading (_subentities/_maintenance/_common) and field_default publicization all correct.
- [2026-07-09T23:51:01Z] Catherine Manager:
  - Reviewer-approved (code as scoped); full suite green; AC1-4 met; dynamic-signature builder confirmed safe, _collab sub-param clean/backward-compatible. Dispositions: F1 (MEDIUM, §4 generic SubEntity field store unassigned — feature not materially complete without it) → filing a new §4 task under FEAT-212, sequenced before the 354 closeout. F2 (LOW, no test for the fail-loud 'no CLI storage yet' path) → folded into the §4 task, which replaces that path with real storage + its test. F3 (LOW, --severity/title help text drift toward generic wording) → aligns with the FEAT-336 de-hardcoding direction (the audit flagged the hardcoded enum hint as a defect), folded into FEAT-336. Landing.
<!-- sq:discussion:end -->
