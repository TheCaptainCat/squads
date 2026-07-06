---
id: TASK-243
sequence_id: 243
type: task
title: sq check surfaces a one-line invalid-workflow-spec warning
status: Done
parent: FEAT-209
author: tech-lead
subentities:
- local_id: ST1
  title: sq check one-line invalid-workflow-spec warning
  status: Todo
  story: US2
created_at: '2026-06-30T07:49:54Z'
updated_at: '2026-07-06T15:21:08Z'
---
<!-- sq:body -->
## Goal
Make `sq check` surface a one-line warning when the project workflow spec is invalid, instead of
either silently passing or hard-crashing. (AC #4.)

## Current state
`Service.check()` in `src/squads/_services/_maintenance.py` (~line 577) aggregates `CheckIssue`
records from several `_check_*` helpers plus `check_override_issues(...)` from the overrides service.
It returns a `list[CheckIssue]` (level "warn"/"error", item, message). The CLI `sq check` renders
them. Today there is no workflow-spec validity check in this aggregation.

Note a subtlety: if the workflow override is invalid, `open_service` itself will hard-stop
(TASK-240) — so `sq check` may never get to run. Decide the behaviour: either (a) `sq check`
catches the load error and reports it as a single `CheckIssue` so the rest of check still runs
(preferred — `sq check` is the diagnostic command and should degrade gracefully), or (b) it relies
on open_service's hard-stop and this AC is satisfied by the pointer message. **Recommend (a)**: have
`check()` run the workflow validation in collect-mode (the same core as TASK-242) guarded so a
broken spec yields ONE `CheckIssue("error"/"warn", "workflow", "workflow config invalid — run `sq
workflow lint`")` rather than aborting check entirely. Confirm the open_service ordering allows this
(check may need to tolerate being reached even with a borderline spec).

## What to build
- In `Service.check()`, add a workflow-spec validity probe that appends a single concise
  `CheckIssue` with the message "workflow config invalid — run `sq workflow lint`" when the merged
  spec fails validation (pure-spec OR index cross-check). One line only — the detail lives in
  `sq workflow lint` (TASK-242), per AC #4 wording.
- Keep it cheap: reuse the collect-mode validation core; don't re-implement rules.

## Acceptance
- On a squad with an invalid workflow override, `sq check` prints exactly one line
  "workflow config invalid — run `sq workflow lint`" (AC #4) and the rest of check still runs.
- On a squad with no override / a valid override, `sq check` shows no workflow line (no false
  positive; AC #7 spirit).

## Ordering
After TASK-241/242 (shares the validation core). Independent of TASK-244 (override artifact).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 243 add-subtask "<title>"`; track with `sq task 243 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | sq check one-line invalid-workflow-spec warning | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — sq check one-line invalid-workflow-spec warning

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US2 — As a project admin, I want sq workflow lint to validate my spec config and report every error clearly before I commit it
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Covers making `sq check` degrade gracefully on a bad workflow override: `Service.check()` runs the workflow validation in collect-mode (the same core as TASK-242) guarded so a broken spec yields exactly ONE concise `CheckIssue` — "workflow config invalid — run `sq workflow lint`" — rather than aborting check entirely, letting the rest of the checks still run. No workflow line appears for a squad with no override or a valid override (no false positive). Detail lives in `sq workflow lint`, per AC#4's one-line wording. (US2)
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-30T08:29:12Z] Catherine Manager:
  - AC#5 wiring gate (from REV-246 + QA on Wave 1): validate_against_index() is implemented in _workflow/_loader.py but has NO production call site — AC#5 ('removing a status still in use by live items fails closed, listing offending IDs') is not end-to-end. This task MUST wire it in. Design constraint: 'fails closed' means a normal command on such a squad hard-stops (open_service is the natural point) with the 'run sq workflow lint' pointer — BUT sq workflow lint (TASK-242) must still run and report the offenders without being self-blocked by the same check. FEAT-209 cannot be signed off AC#5-complete until this is wired and proven by an end-to-end test.
- [2026-06-30T08:45:56Z] Elias Python:
  - Implemented AC#5 wiring and sq check integration (TASK-243).
  - AC#5 wiring: validate_against_index_fail_closed(spec, squad_dir) in _loader.py reads the index synchronously (bypassing the async layer) after load_workflow_spec succeeds, raises SquadsError listing every offending item ID if the merged spec drops a type or status still used by live items. Called from open_service() (F3/REV-246 fast-path also wired: no-override squads use cached _BUNDLED_SPEC without re-parsing). sq workflow lint bypasses this by calling lint_workflow_spec() directly.
  - sq check integration (AC#4): check command now probes lint_workflow_spec() before calling get_service(). If any error findings, appends CheckIssue('error', 'workflow', 'workflow config invalid — run sq workflow lint'). If get_service() raises (AC#5 hard-stop), falls back to bundled spec and constructs Service(sp) directly so remaining checks (markers, dangling links, etc.) still run.
  - Private API cleanup (policy change from coordinator): added public active_spec() and bundled_spec() accessors to _workflow/__init__.py; made Workflow._from_machine public as Workflow.from_machine. Updated call sites in _index/_store.py, _services/_maintenance.py, _cli/_common.py, _services/_service.py, _cli/_main.py — all reportPrivateUsage suppressions for workflow names removed.
  - Tests added in tests/test_workflow_override.py: test_lint_no_override_reports_ok, test_lint_valid_override_reports_ok, test_lint_invalid_override_collects_all_errors, test_lint_collects_index_cross_check_errors, test_lint_does_not_self_block_on_ac5_spec, test_lint_cli_exits_0_on_no_override, test_lint_cli_exits_0_on_valid_override, test_lint_cli_exits_1_on_invalid_override, test_workflow_show_still_works, test_workflow_show_subcommand_works, test_check_no_workflow_issue_when_spec_valid, test_check_reports_workflow_issue_for_invalid_spec, test_ac5_open_service_fails_closed_with_live_items, test_ac5_lint_reports_not_hard_stops_on_dropped_status, test_open_service_no_override_uses_bundled_fast_path. Previous gap-doc test updated to reflect the now-wired AC#5.
  - Gate results: pyright 0 errors/0 warnings, ruff check clean, ruff format clean. Targeted pytest (test_workflow_override.py + test_workflow_spec.py + test_service.py + test_load_boundary_vocab.py) 132/132 passed.
  - @manager: TASK-242 and TASK-243 Done. AC#5 is wired end-to-end. Wave 2 complete. Ready for review.
- [2026-06-30T09:29:52Z] Elias Python:
  - Fix 2 (F2 / REV-248) applied — TASK-243 follow-up.
  - In `_services/_service.py` open_service: deleted the vestigial F5 comment block (the OSError guard that was described but did not exist) and removed the no-op `try/except SquadsError: raise SquadsError(f'{exc}')` re-wrap around `validate_against_index_fail_closed`. Now calls it directly — the function's own SquadsError message already carries the lint pointer.
<!-- sq:discussion:end -->
