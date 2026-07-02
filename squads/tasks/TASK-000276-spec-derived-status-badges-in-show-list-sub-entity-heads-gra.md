---
id: TASK-000276
sequence_id: 276
type: task
title: Spec-derived status badges in show/list + sub-entity heads, graceful default
status: Done
parent: FEAT-000211
author: tech-lead
priority: high
subentities:
- local_id: ST1
  title: Spec-derived badge resolver with graceful default in show/list/heads
  status: Todo
  story: US2
created_at: '2026-07-02T09:20:17Z'
updated_at: '2026-07-02T10:22:07Z'
---
<!-- sq:body -->
## Goal — spec-derived status badges everywhere, with a graceful default (AC#3, US2)

Custom statuses must render their configured badge in `sq <type> show` and `sq list`, and fall
back to a neutral default (⚪) when no badge is declared — never crash. Runs under the
TASK-000275 golden guard (built-in output must stay byte-identical).

## The bug to fix

`_discussion._status_badge` does `STATUS_EMOJI.get(Status(status_value), "")`. `Status(...)`
**raises ValueError** for any status not in the `Status` StrEnum — so a custom status (e.g.
`Triage`, `Mitigating`) crashes the sub-entity head render and the `--full` pane title. The
enum-keyed `STATUS_EMOJI` (`_models/_enums.py`) only covers the 9 sub-entity statuses.

## Design

- Route badge lookup through the spec: `WorkflowSpec.status_badge(status)` already exists and
  returns the declared badge or `None`. Add a resolved helper that returns `spec.status_badge(s)`
  or the neutral default `⚪` when `None` — so every status (built-in or custom) has a badge.
- `default_workflow.toml` currently declares badges only for the 9 sub-entity statuses (to
  mirror `STATUS_EMOJI`). Decide + confirm with the golden: either (a) declare badges for ALL
  built-in item statuses in the TOML so `sq show`/`sq list` gain a badge, OR (b) keep top-level
  item display badge-free and only fix the sub-entity path's crash + custom-status support.
  **PRODUCT QUESTION for the manager (see return summary):** AC#3 literally says badges render
  in `sq show` and `sq list` — that implies top-level items should show a badge, which they do
  NOT today. If we add top-level badges, TASK-000275's golden for built-in `sq show`/`list`
  changes and 275 must pin the *target* (post-badge) built-in output. Resolve this before coding.
- Rewire `_discussion._status_badge` and `_common._subentity_pane_title_raw` (and wherever
  `STATUS_EMOJI`/`Status(...)` is used for status display) to the spec-derived resolver, threading
  the active spec (`get_active_spec()` in CLI, `self.spec` in services — see
  [[prefers-threaded-context-over-globals]], no module-global singleton).
- Keep the `InProgress → In Progress` label spacing behaviour; only the emoji source changes.

## Acceptance

1. A status declared with `badge = '🟠'` in `.overrides/workflow.toml` renders that emoji in
   `sq show` and `sq list` (and in sub-entity heads if the custom status is a sub-entity status).
2. A custom status with no `badge` renders the ⚪ default — no crash, no empty/missing output.
3. Built-in badges + built-in `sq show`/`sq list`/sub-entity-head output remain exactly as the
   TASK-000275 golden pins them (whichever target 275 pins per the product question above).
4. Service-level test + CLI smoke test (per CLAUDE.md testing rule); custom-status case pinned
   with roster/clock/flags.

## Files
`src/squads/_discussion.py` (`_status_badge`), `src/squads/_cli/_common.py`
(`_subentity_pane_title_raw`, `_build_item_panel_rows`, `_item_table` in `_main.py`),
`src/squads/_models/_enums.py` (`STATUS_EMOJI` — may be retired/kept as the TOML source),
`src/squads/_workflow/default_workflow.toml` (badge declarations),
`src/squads/_workflow/_models.py` (`status_badge` helper).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 276 add-subtask "<title>"`; track with `sq task 276 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Spec-derived badge resolver with graceful default in show/list/heads | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Spec-derived badge resolver with graceful default in show/list/heads

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US2 — As a team member, I want custom status badges to render in sq show and sq list output
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
- [2026-07-02T10:03:11Z] Elias Python:
  - Done. Fixed the _discussion._status_badge crash by resolving badges through the spec (WorkflowSpec.status_badge) instead of parsing back into the built-in Status StrEnum; a status with no declared badge (custom or built-in) falls back to a graceful ⚪ default — no crash.
  - Design: _status_badge(status_value, spec=None) and set_head(..., spec=None) now take an optional WorkflowSpec, threaded explicitly (no new global) — self.spec at the service boundary (_services/_subentities.py::_refresh_head) and get_active_spec() at the CLI boundary (_cli/_common.py::_subentity_pane_title_raw). Callers that don't thread one (the frozen 0.2→0.3 migration runner) default to bundled_spec(), preserving today's behavior.
  - Scope respected AC#3 ruling (b): no new badge surface on sq show/sq list — _build_item_panel_rows still renders it.status as a plain string; only the two surfaces that render badges today (sub-entity :head regions, sub-entity pane titles) were rewired.
  - Files: src/squads/_discussion.py (_status_badge, set_head), src/squads/_services/_subentities.py (_refresh_head threads self.spec), src/squads/_cli/_common.py (_subentity_pane_title_raw threads get_active_spec()), src/squads/_models/_enums.py (STATUS_EMOJI docstring — see F4 below).
  - REV-000284 findings addressed: (1) moved the new custom-status tests out of the HEAD-pinned golden into a standalone tests/test_custom_status_badges.py — tests/test_status_display_characterization.py is untouched (verified: git diff shows zero changes to that file). (2) F4 STATUS_EMOJI: it now has zero production consumers (grep confirms) — production badge resolution is 100% spec-driven. Kept the dict rather than deleting it, because it is still read by two tests as the historical golden the spec's built-in badges are checked against (tests/test_workflow_spec.py::test_golden_status_badges, tests/test_status_display_characterization.py); relabeled its docstring to say explicitly it is a test-only golden fixture with no production reader, and to delete it if it ever loses its last test consumer — one source of truth (the spec) for actual behavior, one pinned reference (the dict) for the golden checks.
  - Verified: tests/test_status_display_characterization.py (the gating golden) is byte-for-byte unchanged and green — built-in output stays byte-identical. New tests/test_custom_status_badges.py covers: declared badge renders, no-badge renders ⚪, never raises, no-spec-arg falls back to bundled, built-in badges unaffected by a spec extension. Also green: test_discussion.py, test_rendering.py, test_show_render.py, test_workflow_spec.py, test_load_boundary_vocab.py, test_migrations.py, test_migration_corpus.py, and the full suite (uv run pytest -q, exit 0, all pass). pyright + ruff check + ruff format --check clean on all touched files.
  - @reviewer ready for review.
- [2026-07-02T10:08:13Z] Paul Reviewer:
  - Reviewed and approved (REV-000284 → Approved). The _status_badge crash fix is correct: spec-derived resolution (active_spec.status_badge(status_value) or '⚪'), no Status(value) parse, graceful default for custom statuses, bundled-spec fallback when no spec is threaded. Spec threaded via self.spec (service) and get_active_spec() (CLI) — no new global, no new pyright suppression. AC#3 ruling (b) respected: top-level sq show/sq list stay badge-free (plain it.status). All REV-284 findings closed (F1/F2/F4 Fixed, F3 waived as a non-blocker). Targeted tests: 51 passed; the HEAD-pinned characterization golden is byte-identical to 495fc95. Good to mark Done. @tech-lead
- [2026-07-02T10:09:35Z] Paul Reviewer:
  - Correction to my earlier approval: REV-000284 is back to ChangesRequested. op-pierre reviewed the STATUS_EMOJI resolution (F4) and it is not adequately fixed. Two required changes before TASK-276 is Done: (1) remove the 'FEAT-000211 / TASK-000276' sq item IDs from the STATUS_EMOJI docstring in src/squads/_models/_enums.py (sq IDs must not appear in source); (2) delete the now-dead STATUS_EMOJI dict from _enums.py and move its 9-glyph golden into the test layer as a shared test constant, repointing tests/test_workflow_spec.py and tests/test_status_display_characterization.py to import it (keeping the characterization golden's asserted glyphs byte-identical). The crash fix itself, the byte-identical baseline, no-top-level-badge (AC#3 b), and no-new-suppression all still verify clean — only F4 blocks. Not Done yet. @tech-lead @python-dev
- [2026-07-02T10:19:34Z] Elias Python:
  - Follow-up applied (op-pierre's call, hardening REV-284 F4).
  - 1. Stripped sq item IDs from source: removed the FEAT-000211/TASK-000276 citation from the STATUS_EMOJI docstring before deleting it entirely (see #2); scanned the full diff's added lines for FEAT-/TASK-/BUG-/REV-/ADR-/EPIC-/DEC- and confirmed zero matches across every touched src/ and tests/ file.
  - 2. Deleted STATUS_EMOJI from src/squads/_models/_enums.py entirely — grep -rn STATUS_EMOJI src/ now returns nothing (only src/squads/_workflow/default_workflow.toml had a stale comment mentioning the name in prose; reworded it too since it now dangled).
  - 3. Moved the 9-glyph golden reference into the test layer: new tests/_helpers.py holds EXPECTED_BUILTIN_STATUS_BADGES (bare emoji per built-in status, no production analogue, no ticket IDs). Repointed both consumers: tests/test_workflow_spec.py::test_golden_status_badges and tests/test_status_display_characterization.py (import + all STATUS_EMOJI usages) now read from tests/_helpers.py. tests/test_custom_status_badges.py also derives its full-text badge map from the same shared constant instead of hand-duplicating it.
  - Byte-identical check: diffed tests/test_status_display_characterization.py against HEAD 495fc95 — every change is a mechanical import/name rename (STATUS_EMOJI -> EXPECTED_BUILTIN_STATUS_BADGES); every pinned literal (the _EXPECTED_BADGES text map, all emoji values, all assertions against rendered sq show/list/head output) is untouched. No production rendering behavior changed.
  - Verified: grep -rn STATUS_EMOJI src/ returns nothing. uv run pytest tests/test_workflow_spec.py tests/test_status_display_characterization.py tests/test_custom_status_badges.py tests/test_discussion.py -q — all green. Also re-ran test_rendering.py, test_show_render.py, test_load_boundary_vocab.py, test_migrations.py, test_migration_corpus.py — green. pyright + ruff check + ruff format --check clean on all touched files. Full suite (uv run pytest -q) re-run in background to confirm no wider fallout; will flag if anything surfaces.
  - Left TASK-276 InReview. Did not touch 277/278/279; no subagents spawned. @reviewer
<!-- sq:discussion:end -->
