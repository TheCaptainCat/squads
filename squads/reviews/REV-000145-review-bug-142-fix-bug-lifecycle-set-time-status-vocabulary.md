---
id: REV-145
sequence_id: 145
type: review
title: 'Review BUG-142 fix: bug lifecycle + set-time status vocabulary validation'
status: Approved
author: reviewer
refs:
- BUG-142
- ADR-143:addresses
subentities:
- local_id: F1
  title: All ADR-143 acceptance points verified; no defects
  status: Verified
  severity: info
created_at: '2026-06-16T13:48:41Z'
updated_at: '2026-06-16T13:49:26Z'
---
<!-- sq:body -->
Independent review of the BUG-142 fix (bug lifecycle + set-time status
vocabulary validation), implemented per ADR-143 with the op-pierre override
(schema stays 0.3, no migration runner; existing bugs remapped in place).

## Scope verified

- src/squads/_workflow.py — new `_BUG` machine + `WORKFLOWS[ItemType.BUG]`
- src/squads/_errors.py — `StatusNotInWorkflowError(SquadsError)`
- src/squads/_services/_items.py — `_apply_status` vocabulary check
- tests/test_bug_workflow.py (new), tests/test_retype.py (updated)
- tests/goldens/{list,blocked,tree}.json (regenerated)
- 9 remapped bug .md files

## Verdict: APPROVED

The fix is correct, complete, and conforms to ADR-143. The key vocabulary
hole that let BUG-134 become `Fixed` is closed and proven closed empirically.
Gate is fully green. No findings above informational.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 145 add-finding "…" --severity high`; track with `sq review 145 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🔵 info | Verified |  | All ADR-143 acceptance points verified; no defects |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — All ADR-143 acceptance points verified; no defects

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🔵 Info
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
ADR-143 conformance: _BUG workflow matches exactly — initial Open; edges Open→{InProgress,WontFix,Cancelled}, InProgress→{Fixed,Blocked,WontFix,Cancelled}, Fixed→{Verified,InProgress}, Verified→{InProgress}, Blocked→{InProgress,WontFix,Cancelled}, WontFix→{Open}, Cancelled→{Open}; terminals Verified/WontFix/Cancelled already in TERMINAL. Draft/Ready/InReview/Done/Todo correctly excluded (test_bug_workflow_excludes_work_states).

Key fix (force does NOT bypass vocabulary): _apply_status checks 'status not in workflow_for(item.type).states' BEFORE the can_transition edge check and INDEPENDENT of force (force only gates the edge check on line 121). Proven empirically in a scratch squad: 'sq bug N status Done' rejected (StatusNotInWorkflowError, exit 1); 'sq bug N status Done --force' rejected IDENTICALLY; 'sq bug N status Verified --force' (valid vocab, invalid Open→Verified edge) succeeds — force still relaxes the edge. This is exactly the hole that let BUG-134 become Fixed. Closed.

No collateral on other types: task force edge override (Draft→Done --force) still works; 'Verified' correctly rejected for a task with the right allowed list; normal non-force Draft→Ready works. Both set_status and update route through _apply_status, so the check is uniform.

Remap integrity (Invariant 1): all 9 closed bugs show status: Verified in frontmatter (was Done); git diff confirms ONLY the status line changed (BUG-134 also dropped its stale Fixed + updated_at). Markers and bodies untouched. 'sq repair' rebuilds the index byte-identically from frontmatter; 'sq check' clean.

Goldens: tests/goldens/{list,blocked,tree}.json regenerated — the only diff is the seeded bug's status Draft→Open (new initial), shape otherwise unchanged. No stray tests/tests/ nested directory; golden file at tests/test_golden_json.py and tests/goldens/.

Gate: uv run pytest exit 0 (incl. 16 new bug-workflow tests + updated retype tests); pyright 0 errors; ruff check + format --check clean; SCHEMA_VERSION still '0.3' (no bump, per op-pierre override).
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
