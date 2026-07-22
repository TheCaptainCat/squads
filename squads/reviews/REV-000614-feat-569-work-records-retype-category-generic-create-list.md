---
id: REV-614
sequence_id: 614
type: review
title: FEAT-569 work/records retype + category-generic create/list
status: Approved
author: reviewer
subentities:
- local_id: F1
  title: Parent self-check in _validate_refusals now overlaps the gate
  status: WontFix
  severity: low
- local_id: F2
  title: Retype now fails closed on a dangling parent (contract change)
  status: WontFix
  severity: low
created_at: '2026-07-22T17:13:04Z'
updated_at: '2026-07-22T20:38:24Z'
---
<!-- sq:body -->
Independent review of FEAT-569 (TASK-592/593/594): making create/retype/list honour a type's category generically so a custom records-category type is fully spec-driven. Scope = uncommitted diff on src/tests + the new integration test.

Gate ordering + prospective fidelity (retype) verified correct; create is genuinely category-generic with no code change; wording/tests clean. See findings for one low consolidation note and one informational behavior-change observation.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 614 add-finding "…" --severity medium`; track with `sq review 614 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | WontFix |  | Parent self-check in _validate_refusals now overlaps the gate |
| F2 | 🟢 low | WontFix |  | Retype now fails closed on a dangling parent (contract change) |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Parent self-check in _validate_refusals now overlaps the gate

<!-- sq:finding:F1:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
_retype.py::_validate_refusals (lines 74-82) still checks spec.parent_allowed(new_type, parent.type) for the item's own parent. The new ValidatorEngine.gate(prospective, db) at line 161 already enforces the same rule generically (parent_in for work, no_parent for records), so this branch is now redundant for the single-item parent case. Not a conflict (both give the same verdict; _validate_refusals runs first and raises a more actionable message), and _validate_refusals is still load-bearing for the has_subentities and invalid-children cases the gate does not cover. Left as-is is acceptable; noting the consolidation opportunity. No action required to approve.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-07-22T20:05:56Z] Operator:
  - Left the own-parent branch in _validate_refusals: removing it would shift that refusal's message to ValidatorEngine.gate's generic per-item message (loses old_id/current-parent context + the retype-specific hint), which fails the 'same or better message' bar. Consolidated via comment only (_retype.py:74-80) documenting the intentional overlap with gate's parent_in check and why it stays; sub-entity and invalid-children checks untouched. Behaviour/messages unchanged; targeted retype + tests/meta gates green.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Retype now fails closed on a dangling parent (contract change)

<!-- sq:finding:F2:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
The gate at line 161 runs parent_in/no_parent on the prospective item. parent_in refuses a dangling parent (parent lookup is None -> 'dangling parent' error) and no_parent refuses any truthy parent. So retyping an item that carries a dangling/orphaned parent ref now fails closed, whereas the pre-change path (_validate_refusals only) silently allowed it (it skips when db.get(parent) is None). This is a defensible improvement (a dangling parent is already an sq-check error, and fail-closed is correct), but it is a slight contract change to retype worth recording. No fix needed; flagging for awareness only.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T17:13:41Z] Paul Reviewer:
  - Clean leads: (1) Gate ordering CORRECT — ValidatorEngine.gate(prospective, db) at _retype.py:161 runs before _apply_type_change at :163; require_item/_validate_*/model_copy are all read-only, so a refusal leaves the file, index, edges, and reflog untouched. (2) prospective fidelity CORRECT — type/status/prefix match exactly what _apply_type_change writes: new_status comes from the same _carry_or_reset_status call the real path uses, prefix = prefix_for(new_type, spec) (identical to :241), parent/refs preserved by model_copy. No drift between gated item and written item.
  - (3) No re-encoded rule — no_parent comes from the records CATEGORY_BUNDLES via the shared engine; no bespoke retype-only records check. (4) Create (TASK-592) genuinely category-generic: _CREATABLE iterates spec.non_roster_types(); custom records type resolves via _CustomCreateGroup; no_parent gates through the single ValidatorEngine.gate at _base.py:417; the guide --tech/--tag command is field-based, not a category gate; bundled create unchanged. (5) Wording clean (no 'work type only' remains; help/docstring updated to work/records); no ticket-ID or new 'meta' leaks (the two roster_type test renames are fine; ID strings are display-ID assertions). (6) Integration test proves spec-driven-ness end to end.
  - Gate: pyright 0 errors, ruff check + format clean, no SCHEMA_VERSION bump. Targeted pytest green: test_retype.py + test_retype_command_cli.py + the new integration test (29 passed) and create/no_parent/records selection (35 passed).
- [2026-07-22T17:16:01Z] Catherine Manager:
  - Manager independent verification: read _retype.py directly — ValidatorEngine.gate(prospective, db) at :161 runs before the first mutation (_apply_type_change :163); prospective faithfully mirrors the written item (status via _carry_or_reset_status, prefix via prefix_for, parent/refs preserved). Gate-ordering + fidelity confirmed; refusal leaves file/index/edges/reflog untouched. F1 (own-parent check redundancy) left Open as a future consolidation cleanup; F2 (dangling-parent now fails closed) is an intended improvement, sq check already errors on dangling parents. Self-approval heuristic warning noted and dismissed: the reviewer was an independently-spawned party, distinct from the build lineage.
- [2026-07-22T20:07:08Z] Catherine Manager:
  - Attribution correction: the WontFix on F1 and its rationale (prior comment auto-attributed to Operator for lack of an --as flag) is an engineering decision by the dev, endorsed by me as manager — NOT a call by op-pierre. Rationale stands: removing the own-parent branch would downgrade the retype error to the gate's generic per-item message, losing the old_id/current-parent/'remove the parent first' context; the overlap is intentional message-quality duplication, now documented in _retype.py. F1 verified WontFix.
- [2026-07-22T20:38:24Z] Catherine Manager:
  - F2 WontFix: retype now failing closed on a dangling parent is the intended, correct behaviour — a dangling parent is already an sq check error, and refusing to retype onto an invalid parent state is an improvement, not a regression. No change wanted.
<!-- sq:discussion:end -->
