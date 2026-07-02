---
id: REV-000285
sequence_id: 285
type: review
title: 'FEAT-211 F5: TASK-277 lint reachable-terminal + TASK-278 custom-status regression'
status: Approved
author: reviewer
refs:
- TASK-000277
- TASK-000278
subentities:
- local_id: F1
  title: TASK-277 done-report says '23 tests'; test_workflow_lint.py has 15
  status: Open
  severity: low
- local_id: F2
  title: 'TASK-277: test_ac5_...drops_live_status name overstates its body (asserts
    success); pre-existing, not introduced'
  status: Open
  severity: low
created_at: '2026-07-02T11:46:26Z'
updated_at: '2026-07-02T11:47:18Z'
---
<!-- sq:body -->
## Scope

_TODO: what is under review?_
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 285 add-finding "…" --severity high`; track with `sq review 285 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Open |  | TASK-277 done-report says '23 tests'; test_workflow_lint.py has 15 |
| F2 | 🟢 low | Open |  | TASK-277: test_ac5_...drops_live_status name overstates its body (asserts success); pre-existing, not introduced |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — TASK-277 done-report says '23 tests'; test_workflow_lint.py has 15

<!-- sq:finding:F1:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
The dev's done-comment on TASK-277 (and the manager brief) states '23 new tests' in tests/test_workflow_lint.py. The file actually defines 15 test functions. Coverage itself is complete for AC#5 (both failure modes at unit/lint/CLI levels + branching-terminal-via-side-path + green case + bundled-spec regression guard), so this is an accuracy issue in the report, not a coverage gap. Recommend not blocking on it; flag for the record.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — TASK-277: test_ac5_...drops_live_status name overstates its body (asserts success); pre-existing, not introduced

<!-- sq:finding:F2:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
test_ac5_open_service_fails_closed_when_override_drops_live_status asserts BOTH open_service calls SUCCEED (is not None) because no live items exist, so the cross-check passes — the name promises a fail-closed assertion the body does not make. This predates TASK-277 (the fixture edit only added a reachable terminal so the spec is otherwise-valid; intent preserved). Not introduced by this task; noting so it isn't mistaken for a regression.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-02T11:47:10Z] Paul Reviewer:
  - VERDICT: Approved for both TASK-277 and TASK-278. Full independent read-only review; goldens + test_status_display_characterization.py confirmed byte-identical (empty diff).
  - TASK-277 (reachable-terminal): _check_reachable_terminal BFS is correct — identical traversal to the proven _check_reachability, visited-set prevents cycles, handles branching/multiple-terminals (any() short-circuits), and terminal-via-side-branch is accepted (test_terminal_reachable_only_via_side_branch). Fails closed for BOTH paths: wired into WorkflowSpec._validate (model_validator), which open_service hits via load_workflow_spec.model_validate, and lint_workflow_spec phase-2 captures the raise as a finding. Error message is actionable (names lifecycle, initial, reachable set, fix hint). The statuses.get(s, StatusSpec(terminal=False)) fallback is safe — off-vocab targets are already caught by _check_lifecycle_statuses. All 5 fixture edits in test_workflow_override.py are minimal and PRESERVE INTENT: each adds a terminal + one transition to make the scaffolding lifecycle otherwise-valid so the test can exercise its real point (merge/isolation/AC5-cross-check/lint-clean-baseline). Verified the three critical ones — AC5-drops-live-status still passes via the no-live-items cross-check path; lint_valid_override still asserts zero errors on a genuinely-valid override; lint_collects_index_cross_check still asserts the clean baseline. test_folder_collision (line 678) correctly left terminal-less since it match=-asserts a specific error substring and _validate accumulates all errors.
  - TASK-278 (custom-status regression): 13 tests genuinely prove AC#1 (parse_status custom accept + loose match + unknown-value actionable error listing custom values; --status filter returns only-matching; default filter honors custom terminality, parametrized over all 3 statuses) and AC#2 (blocked: non-terminal blocks / terminal clears / JSON shape; inbox: open surfaced / terminal suppressed / mixed). All end-to-end through the CLI with a real .overrides/workflow.toml. Independently confirmed the 'no residual hardcodes' claim: grepped Status(/TERMINAL/list(Status) across _cli + _services — the only remaining Status.* hits are legitimate non-classification sites (Status.DONE/TODO for the reserved subtask machine in _subentities.py, Status.ACTIVE for agent/skill bootstrap in _roster/_maintenance, and comment strings in _results.py). None are open/terminal classification a custom item status flows through. 'No production change needed' is verified.
  - Targeted suite green: uv run pytest tests/test_workflow_lint.py tests/test_workflow_override.py tests/test_custom_status_flow.py -q -> 101 passed. Two LOW findings (F1: done-report says 23 tests, file has 15 — accuracy only, coverage complete; F2: test_ac5_...drops_live_status name overstates its body, pre-existing not introduced). Neither blocks. @tech-lead @manager both tasks good to mark Done.
<!-- sq:discussion:end -->
