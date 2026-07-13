---
id: TASK-352
sequence_id: 352
type: task
title: 'Discussion rendering: resolver/field-driven prefixes, placeholders, columns'
status: Done
parent: FEAT-212
author: tech-lead
refs:
- TASK-349:depends-on
subentities:
- local_id: ST1
  title: Summary table renders from declared columns (base + fields + Story)
  status: Todo
  story: US1
created_at: '2026-07-09T21:31:32Z'
updated_at: '2026-07-13T09:27:34Z'
---
<!-- sq:body -->
ADR-348 §5 rendering half: retire the static per-kind tables in _discussion.py so local-id prefixes, scaffold prose, and summary columns all derive from the resolved SubentityKindSpec + its ADR-323 fields.

## Scope

Replace `_LOCAL_ID_PREFIX` (kind->US/ST/F) with `kind_spec.local_prefix`; `local_id_for`/`next_local_id` resolve via the active spec.

Replace `_PLACEHOLDER` (and the three _*_PLACEHOLDER strings) with `kind_spec.placeholder`, falling back to a generic kind-name-derived scaffold line when the kind declares none; `body_placeholder`/`build_block` resolve via spec.

Replace `_SUMMARY_COLS`/`_summary_cells` with a field-driven derivation: fixed base (local_id, Status, Assignee, Title) + one column per declared `field` (headed by the field label, e.g. Severity, resolved through _badges.py — no severity special-casing) + a Story column iff `maps_parent_story`. `render_summary` builds rows from this derivation.

Establish this as the single column-derivation shared with the CLI list table (TASK-353 consumes it) — this unifies the current CLI-vs-body column drift the ADR notes (the CLI story table shows a Story column the body summary omits). Put the shared derivation where both callers can reach it (e.g. a helper in _discussion.py or _badges.py).

## Files owned

- src/squads/_discussion.py (_LOCAL_ID_PREFIX/_PLACEHOLDER/_SUMMARY_COLS/_summary_cells retired; local_id_for/next_local_id/body_placeholder/build_block/render_summary spec-driven; shared column-derivation helper)

## Acceptance

- Built-in story/subtask/finding blocks render byte-identical local ids, placeholders, and summary tables (AC4) — modulo the intended drift fix (Story column now consistent between CLI and body).

- A custom kind with a declared field renders its column headed by the field label; severity is just the generic field column.

- Full suite green.

## Depends on

TASK-349 (local_prefix/placeholder/plural/fields/maps_parent_story on kind_spec). Runs in parallel with TASK-351 (disjoint files); TASK-353 depends on the shared column-derivation landed here.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 352 add-subtask "<title>"`; track with `sq task 352 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Summary table renders from declared columns (base + fields + Story) | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Summary table renders from declared columns (base + fields + Story)

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — As a project admin, I want to define custom sub-entity kinds for my custom types in TOML
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Retired the static per-kind tables in `_discussion.py` (`_LOCAL_ID_PREFIX`/`_PLACEHOLDER`/`_SUMMARY_COLS`) so local-id prefixes, placeholders, and the summary columns all derive from the resolved kind spec: a fixed base (local-id, Status, Assignee, Title) plus one column per declared field and a Story column only when the kind maps to a parent story. Built-in blocks render byte-identical, a custom field renders as a generic labelled column, and the column derivation is shared with the CLI list table.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-09T23:06:12Z] Elias Python:
  - Landed the discussion-rendering half. Files: src/squads/_discussion.py (owned), src/squads/_services/_retype.py (F1 finding), src/squads/_cli/_common.py (fixed the two call sites that would've broken/drifted otherwise), tests/test_discussion.py + a docstring fix in tests/test_unwritten_subentity_body_check.py.
  - _LOCAL_ID_PREFIX/_PLACEHOLDER retired: local_id_for/next_local_id/body_placeholder/build_block now take an optional spec (default bundled) and resolve kind_spec.local_prefix/.placeholder; undeclared placeholder falls back to a generic '_Describe this {kind} here...' line.
  - _SUMMARY_COLS/_summary_cells retired: new public summary_columns(kind, spec)/summary_row(kind, sub, spec) — base [kind.title(), Status, Assignee, Title] + one column per declared field (label from _badges.py, inserted after the local-id col) + trailing Story iff maps_parent_story. render_summary composes them. Field values are read via getattr(sub, field.code) — structurally generic, not an 'if code==severity' branch; only severity has a real storage slot today so a custom field's cell is empty until a generic sub-entity field store lands (ADR-348 §4, not in this task's scope).
  - Reusable for TASK-353: summary_columns/summary_row are public, kind+spec parameterized, no SubEntity-shape assumptions beyond local_id/status/assignee/title/story — the CLI list table can call them directly instead of re-deriving columns.
  - F1 fixed: _CONTAINER_HEADINGS retired in favor of _container_heading(spec, kind) — bundled literals (User Stories/Subtasks/Findings) kept in a small dict (since 'stories'.title() != 'User Stories'), custom kinds fall back to plural.title(). No new SubentityKindSpec field added, per the routing note.
  - Also fixed in _cli/_common.py (not excluded, needed for correctness): resolve_local_id now threads get_active_spec() into local_id_for; _print_subentity_summary was reaching into discussion._SUMMARY_COLS privately (pyright-ignored) with its own hardcoded finding/subtask branches — replaced with summary_columns/summary_row so the CLI show-pane table and the body :summary region share one derivation (closes the drift the ADR calls out for this call site).
  - Gap I did NOT fix, per the 'don't touch the service layer' boundary: src/squads/_services/_subentities.py's add_block/set_block_body still call next_local_id/build_block/body_placeholder with no spec arg, so they resolve against bundled_spec() only. Harmless for built-in kinds (overrides can't redefine them, so bundled == active there), but a genuinely custom kind would KeyError in these paths until self.spec is threaded through. Same gap in _services/_maintenance.py's unwritten-body check (body_placeholder(kind) with no spec) and _subentity_pane_title_raw in _cli/_common.py (still literal kind=="finding"/kind=="subtask" branches for the --full pane title, untouched — different concern from the summary table, not in this task's scope). Flagging for TASK-353 or a follow-up.
  - Gates: pyright 0 errors, ruff check + format clean, vulture clean on discussion/retype. Targeted tests green (discussion/rendering/service/retype/meta_compat/unwritten_subentity_body/status_banner/show_render/collab/sections/load_boundary_vocab/workflow_spec + golden_json + golden_rendered_output, 380+ tests, exit 0) plus test_squad_ref_hygiene. No golden diff at all — default_workflow.toml untouched, bundled kinds byte-identical, confirmed by the golden tests passing with zero delta. Added one new test (test_custom_kind_summary_table_derives_columns_from_declared_fields) proving a custom kind's field renders as a generic labeled column via render_summary end-to-end. Did not run the full suite (per brief) — left for the main loop. Tree is dirty, no commit made.
- [2026-07-09T23:14:17Z] Paul Reviewer:
  - Reviewed uncommitted TASK-352 diff (independent, on committed TASK-351). VERDICT: APPROVE. Byte-identical for built-ins confirmed, F1 heading fix correct, reusability contract clean, gates clean (pyright/ruff/format), full suite green (exit 0, 0 failures). One MEDIUM tracking finding (downstream scope) below.
  - Byte-identical CONFIRMED for built-ins: summary_columns/summary_row reproduce the old _SUMMARY_COLS/_summary_cells exactly — subtask=[Subtask,Status,Assignee,Title,Story], story=[Story,Status,Assignee,Title], finding=[Finding,Severity,Status,Assignee,Title] (field label inserted right after the local-id col, matching finding's old Severity position); rows identical incl. the severity badge cell (_field_value(sub,'severity')==sub.severity for the only field with a storage slot). local_prefix US/ST/F and placeholders resolve to the same bundled strings. Golden JSON tests (feature_stories/review_findings/task_subtasks/show_feat/show_task) all pass unchanged — no golden diff is real.
  - F1 heading fix (_retype.py:26-40) CORRECT: _BUNDLED_CONTAINER_HEADINGS keeps the 3 literals (esp. story->'User Stories', not derivable from plural.title()); _container_heading falls back to plural.title() for a custom kind. Correctly did NOT add a schema field — heading stays a derived/literal concern, not SubentityKindSpec vocabulary. Resolves the TASK-351 F1 cleanly.
- [2026-07-09T23:14:35Z] Paul Reviewer:
  - Reusability contract for TASK-353 CLEAN: summary_columns(kind,spec)/summary_row(kind,sub,spec) are pure spec-driven derivations with no console/markdown coupling — usable by both the body :summary (render_summary) and any Rich table. _cli/_common.py::_print_subentity_summary already switches to them (cells wrapped in e()), proving the contract. Note: the new blanket e() over every cell is byte-identical for built-ins (badge_render emits 'emoji code', bracket-free) and is more correct per the escape-dynamic-output invariant — benign improvement.
  - Deferred gap (a) — YES, correctly deferred / harmless for built-ins now, BUT the tracking home is wrong. Call sites resolving against bundled_spec() (would KeyError for a project-only custom kind): _subentities.py:115 next_local_id, :126 build_block, :407 body_placeholder, _maintenance.py:1129 body_placeholder. All safe today (bundled has every built-in; custom kinds aren't CLI-reachable until 353). Deferred gap (b) — YES: _common.py:205/212 _subentity_pane_title_raw still special-cases finding-severity/subtask-story; harmless for built-ins (pane title only).
  - F2 (MEDIUM, tracking — not a fix for this diff): TASK-353's Files-owned is _cli/_items.py ONLY, so neither gap (a) [_services/_subentities.py, _services/_maintenance.py] nor gap (b) [_cli/_common.py] is in its scope. But TASK-353 AC1 (custom-kind add works no-code-change) drives add_block -> next_local_id/build_block, which will KeyError on the bundled spec unless self.spec is threaded there. Ask tech-lead to EXPAND TASK-353's file ownership to _services/_subentities.py + _services/_maintenance.py + _cli/_common.py (the fix is trivial — self.spec/get_active_spec() are in scope at each site), else 353's own acceptance fails.
  - getattr(sub, field.code, None) field retrieval (_discussion.py::_field_value) — ACCEPTABLE: structurally generic, no severity special-casing; a custom field with no typed storage slot renders empty until the ADR-348 §4 generic store lands (out of scope). isinstance(str) guard keeps it type-safe. Scope-disciplined; no ticket IDs leaked (the one ADR-348 ref is a test docstring, matching the repo's ADR-provenance convention). Test additions real + behavior-named (custom 'action'/'impact' column derivation).
- [2026-07-09T23:15:22Z] Catherine Manager:
  - Reviewer-approved; byte-identical for built-ins (no golden diff); full suite green. F1 (container-heading retirement) landed spec-driven with bundled literals preserved. F2 (MEDIUM tracking): the two custom-kind-path gaps — service-layer spec threading in _services/_subentities.py + _maintenance.py, and the --full pane-title special-case in _cli/_common.py — are outside 353's original _cli/_items.py-only ownership but are required for 353's AC1, so 353's scope is expanded to include those sites. Landing.
<!-- sq:discussion:end -->
