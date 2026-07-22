---
id: REV-603
sequence_id: 603
type: review
title: 'Review of FEAT-570 US1: category-aware visibility + filter'
status: Approved
author: reviewer
refs:
- FEAT-570
subentities:
- local_id: F1
  title: 'StatusSpec.role docstring stale: now engine-consumed'
  status: WontFix
  severity: low
- local_id: F2
  title: Rejected records now visible by default — confirm intent
  status: WontFix
  severity: low
created_at: '2026-07-22T13:37:59Z'
updated_at: '2026-07-22T20:38:23Z'
---
<!-- sq:body -->
Independent review of FEAT-570 US1 (TASK-595/596/597): category on the `sq workflow types --json` catalog, category-aware default visibility (folds REV-565 F9), the empty-view hint, and a `--category` filter on sq list/tree. Read-only — did not author. Gates verified green: pyright/ruff/format clean, full suite --all-extras exit 0, sq check clean.

Verdict: Approve with nits. The highest-risk item — the status-role ripple from adding role=retired to Deprecated and Cancelled — is contained, and the work/roster path is byte-identical. Two Low findings (both non-blocking): a stale StatusSpec.role docstring, and a design-intent question about Rejected records now showing by default.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 603 add-finding "…" --severity medium`; track with `sq review 603 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | WontFix |  | StatusSpec.role docstring stale: now engine-consumed |
| F2 | 🟢 low | WontFix |  | Rejected records now visible by default — confirm intent |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — StatusSpec.role docstring stale: now engine-consumed

<!-- sq:finding:F1:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
`StatusSpec.role` docstring (_workflow/_models.py ~L344) still reads "Currently used to identify Superseded" and "Not yet consumed by the engine." Both are now false: this task makes `role` engine-consumed via `WorkflowSpec.hidden_by_default` (records hide iff role in RETIRED_STATUS_ROLES), and the roled set is now {superseded, active, retired}. Refresh so the next reader doesn't trust a stale 'not consumed' marker. Doc-only; zero behavioral impact.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Rejected records now visible by default — confirm intent

<!-- sq:finding:F2:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
New behavior: a records item at a terminal-but-unroled status stays visible by default. In the bundled spec that means a Rejected ADR now shows in the default sq list/tree (previously hidden under is_open). Deliberate + tested (test_records_category_terminal_but_unroled_status_stays_visible) and correct per the implemented rule (records hide only on a retired role), but it exceeds F9's stated intent: the driver named Accepted/Published as the final-but-live cases and Superseded/Deprecated/Cancelled as retired — Rejected was never classified. A Rejected decision is a dead-end, not a standing live record, so arguably it should hide like finished work. Not a code defect, not a blocker — a PO/architect intent call: accept Rejected-stays-visible, or give Rejected a retired role. Flagged so the choice is on the record.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T13:38:52Z] Paul Reviewer:
  - Ripple verdict (priority focus 1): status-role addition is CONTAINED. Traced every StatusSpec.role/status_role consumer: (a) _supersedes_incoming keys on == 'superseded' AND is gated on the type declaring a supersedes ref rule — retired never triggers it; (b) hidden_by_default reads role only on the records branch; (c) workflow types --json emits role (golden updated, additive); (d) status_role is a passthrough. is_open/terminal/workflow-lint/badge read the terminal flag, never role, and role is a free-form str|None (no closed-set lint), so 'retired' needs no registration. Cancelled gaining a role does NOT touch work-item behavior: work/roster hidden_by_default returns .terminal, ignoring role.
  - Byte-identical verdict (priority focus 2): CONFIRMED. hidden_by_default(t,s) == not is_open(s) for work/roster, proven exhaustively over every declared type x status (test_hidden_by_default_matches_is_open_inverse...). Records path correct: Accepted/Published/Proposed now visible (the F9 fix), Superseded/Deprecated hidden.
  - The two 'fixed' terminal-status tests (focus 3): legitimately encoded the OLD hide-everything-terminal behavior (the F9 symptom); new assertions are correct, and the blocked-unaffected test (is_open) is unchanged — not masking a regression.
  - @tech-lead @product-owner: Approve with 2 Low nits (F1 stale docstring, F2 Rejected-records-visible intent call). Neither blocks the merge. Gates: pyright/ruff/format clean, full suite --all-extras green, sq check clean.
- [2026-07-22T15:38:13Z] Olivia Lead:
  - F1/F2 are subsumed by the FEAT-605 rework. F1 (stale StatusSpec.role docstring 'not consumed by the engine'): moot — role becomes the first-class engine-consumed axis and the docstring is rewritten in FEAT-605 TASK-606/607. F2 (Rejected records visible by default): resolved by ADR-604 §2 — Rejected moves into the retired role (settled/hidden/muted), so it now hides. Leaving this review for the manager to close.
- [2026-07-22T20:38:22Z] Catherine Manager:
  - Closing: the FEAT-570 US1 increment this reviewed (RETIRED_STATUS_ROLES visibility) was superseded by ADR-604/FEAT-605's role-object model. Both findings are resolved by that model — F1's StatusSpec.role docstring was rewritten under FEAT-605 (role is now a first-class object), and F2 (Rejected visible) is answered: ADR-604 deliberately moved Rejected to the retired role, so it now hides by default. Marked WontFix (reviewed code replaced, concerns resolved).
<!-- sq:discussion:end -->
