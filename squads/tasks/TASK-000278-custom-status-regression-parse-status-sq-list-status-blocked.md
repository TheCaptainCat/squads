---
id: TASK-278
sequence_id: 278
type: task
title: 'Custom-status regression: parse_status, sq list --status, blocked, default
  filter'
status: Done
parent: FEAT-211
author: tech-lead
assignee: python-dev
priority: medium
subentities:
- local_id: ST1
  title: sq list --status + default filter + blocked + inbox honor custom statuses
  status: Todo
  story: US1
created_at: '2026-07-02T09:20:18Z'
updated_at: '2026-07-02T12:12:10Z'
---
<!-- sq:body -->
## Goal — custom statuses through query/filter surfaces (AC#1, AC#2, US1)

Prove (and fix if needed) that `parse_status`, `sq list --status`, `sq list` default filter,
`sq blocked`, and `sq inbox` all classify items by the loaded spec's custom statuses.

## Current state (read before coding — much of this may already work)

- `parse_status` (`_cli/_common.py`) already validates against `get_active_spec().statuses`
  (exact + loose match) and errors "unknown status … (one of: …)". Custom statuses SHOULD already
  parse. Confirm the error lists custom values too.
- Open/terminal classification is already spec-derived: `self.spec.is_open(status)` is used in
  `_services/_base.py` (list filter), `_roster.py`, `_refs.py` (blocked graph), `_collab.py`
  (inbox suppression), and `_cli/_main.py` (list default filter, tree). So AC#1/AC#2 are largely
  a **characterization + regression** job, not new wiring — but VERIFY each path end-to-end with
  a real custom-status override rather than assuming.

## Scope

- Add an end-to-end test override (`.overrides/workflow.toml`) with a custom lifecycle whose
  statuses include a custom **non-terminal** status (e.g. `Triage`, `Mitigating`) and a custom
  **terminal** status (e.g. `Resolved`, terminal=true).
- Assert: `sq list --status Triage` returns the item; `sq list` (no `--all`) hides an item in the
  terminal custom status and shows one in a non-terminal custom status; `sq blocked` treats a
  blocker in a non-terminal custom status as still-blocking and one in a terminal custom status as
  cleared; `sq inbox` suppresses mentions in items with a terminal custom status.
- Unknown `--status Bogus` → actionable "known values" error (exit 1).
- Fix any surface still hardcoding `TERMINAL`/`Status(...)`/enum membership that a custom status
  would break (grep for `Status(` and `TERMINAL` in services/CLI first).

## Acceptance

Matches FEAT-211 AC#1 and AC#2 exactly. All new tests pin roster/clock/flags and run green
under the TASK-275 guard.

## Files
`src/squads/_cli/_common.py` (parse_status — likely no change), `src/squads/_cli/_main.py`
(list/blocked/inbox), `src/squads/_services/_base.py`, `_refs.py`, `_collab.py`, `_roster.py`
(verify only), tests under `tests/`.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 278 add-subtask "<title>"`; track with `sq task 278 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | sq list --status + default filter + blocked + inbox honor custom statuses | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — sq list --status + default filter + blocked + inbox honor custom statuses

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — As a team member, I want sq list --status and sq blocked to work correctly with my custom statuses
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
- [2026-07-02T11:34:55Z] Elias Python:
  - Verified AC#1/AC#2 end-to-end with a real .overrides/workflow.toml custom lifecycle (incident: Triage->Mitigating->Resolved, Resolved terminal). Confirmed via new tests/test_custom_status_flow.py (13 tests, all green) plus manual CLI runs: parse_status accepts custom statuses (exact + loose match) and rejects unknown values with an actionable 'unknown status ... (one of: ...)' error listing the custom values; sq list --status Triage returns the item; sq list (default, no --all) hides a Resolved (terminal) incident and shows Triage/Mitigating (non-terminal) ones, --all always shows both; sq blocked treats a Triage/Mitigating blocker as still-blocking and clears once the blocker reaches Resolved, --json reports the custom status string; sq inbox surfaces @mentions on Triage/Mitigating items and suppresses them on Resolved items.
  - Residual-hardcode sweep (grep for Status(, TERMINAL, list(Status)/iteration over the enum across src/squads/_services and src/squads/_cli): found NONE in my lane. parse_status, sq list --status/default filter, sq blocked (_refs.py), sq inbox (_collab.py), and _roster.py all already read spec.is_open(status)/spec.statuses rather than the built-in Status enum or a TERMINAL frozenset -- confirmed by direct grep and by the new end-to-end tests. The only remaining TERMINAL/Status( hits are the immutable bundled-spec backward-compat shim in _workflow/__init__.py (TERMINAL = _BUNDLED_SPEC.terminal_set(), unused by any status-classification call site) and _migrations/_meta_compat.py's frozen legacy-migration Status(b.status) parse -- both out of scope and correctly untouched. No production code changes were needed for AC#1/AC#2; this is a green verification, not a rewire.
  - Files touched: tests/test_custom_status_flow.py (new). Stayed in lane -- did not touch src/squads/_workflow/_loader.py or lint code (TASK-277's lane); confirmed via git status that only TASK-277's own files (_workflow/_models.py, test_workflow_lint.py) show sibling changes, untouched by me.
  - Green: uv run pytest tests/test_custom_status_flow.py tests/test_status_display_characterization.py -q -> 50 passed; broader collab/inbox/blocked/list + workflow_override + custom_status_badges modules also green. uv run pyright tests/test_custom_status_flow.py -> 0 errors. uv run ruff check + ruff format --check tests/test_custom_status_flow.py -> clean.
  - @reviewer ready for review on TASK-278.
- [2026-07-02T11:47:19Z] Paul Reviewer:
  - Reviewed (REV-285) — APPROVED, good to mark Done. 13 tests genuinely prove AC#1 + AC#2 end-to-end via the CLI with a real custom override. Independently confirmed 'no residual hardcodes': the remaining Status.* hits in _cli/_services are all legitimate non-classification sites (reserved subtask machine, agent bootstrap, comment strings), none in the open/terminal path. 'No production change needed' verified. No findings. @tech-lead
- [2026-07-02T12:04:13Z] Elias Python:
  - Fixed a real, pre-existing test-isolation gap surfaced by test_custom_status_flow.py: added an autouse fixture in tests/conftest.py (_reset_active_spec) that resets _cli/_common's per-invocation _active_spec/_active_dir globals after every test (same leak-guard class as the existing clock/actor resets).
  - Went one layer deeper than the initial diagnosis: resetting _active_spec/_active_dir alone did NOT fix the repro. Root-caused it further -- there are two additional process-global caches, _CustomTypeGroup._custom_cmd_cache (_cli/__init__.py) and _CustomCreateGroup._custom_cmd_cache (_cli/_create.py), ClassVar dicts keyed by canonical type name that a real 'sq <custom-type>' / 'sq create <custom-type>' call populates permanently. My test's many 'sq create incident ...' calls left _CustomCreateGroup._custom_cmd_cache = {'incident': <TyperCommand>} behind (confirmed by direct inspection), which is what actually short-circuited test_custom_type_cli.py::TestF5ExceptNarrowing::test_create_group_build_error_propagates's patch of _build_create_cmd -- the cached command was returned without ever calling the patched builder. test_custom_type_cli.py/test_custom_type_create.py already carried a local, partial version of this reset (clearing _CustomTypeGroup's cache only, not _CustomCreateGroup's, and only self-protecting within their own module), which is why the leak had stayed contained until a new module (mine) started exercising the create-side cache before those modules ran. Extended the new conftest.py fixture to clear both caches globally, so this is now a real backstop rather than a per-module patch.
  - No production code changed -- test-isolation only, confined to tests/conftest.py.
  - Verified: uv run pytest tests/test_custom_status_flow.py tests/test_custom_type_cli.py -q -> green (exit 0). Full suite: uv run pytest -q (run once, redirected) -> exit=0, 0 FAILED/ERROR occurrences, test_create_group_build_error_propagates no longer fails. uv run ruff check tests/conftest.py && uv run ruff format --check tests/conftest.py -> clean.
<!-- sq:discussion:end -->
