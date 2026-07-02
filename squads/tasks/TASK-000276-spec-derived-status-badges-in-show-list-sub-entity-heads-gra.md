---
id: TASK-000276
sequence_id: 276
type: task
title: Spec-derived status badges in show/list + sub-entity heads, graceful default
status: Draft
parent: FEAT-000211
author: tech-lead
priority: high
subentities:
- local_id: ST1
  title: Spec-derived badge resolver with graceful default in show/list/heads
  status: Todo
  story: US2
created_at: '2026-07-02T09:20:17Z'
updated_at: '2026-07-02T09:22:06Z'
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
<!-- sq:discussion:end -->
