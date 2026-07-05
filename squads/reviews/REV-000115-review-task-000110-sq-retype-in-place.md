---
id: REV-115
sequence_id: 115
type: review
title: 'Review TASK-000110: sq retype in place'
status: Approved
author: reviewer
refs:
- TASK-110:addresses
- FEAT-20
subentities:
- local_id: F1
  title: Avoidable type suppression in _carry_or_reset_status
  status: Open
  severity: low
- local_id: F2
  title: Duplicated subentity-kind reverse map
  status: Open
  severity: low
created_at: '2026-06-15T08:44:31Z'
updated_at: '2026-06-15T08:45:19Z'
---
<!-- sq:body -->
Review of TASK-110 (FEAT-20): sq <type> <n> retype <new-type>.

Verdict: APPROVED. Correctness, invariants, and the full gate all hold; two low-severity quality findings only.

Verified: sequence number preserved; ID reprefixes via the computed field; file moves to the new folder with body bytes verbatim and markers intact; incoming-edge rewrite (refs with kinds, children's parent, prose mentions) atomic in one transaction with no dangling refs; status carry-vs-reset correct per workflow (task<->bug, feature<->epic carry; ADR/review/guide reset); all three refusals; Invariant 1 confirmed hands-on (sq repair rebuilds the index byte-identically from frontmatter); forward-edges-only respected; marker-safe edits; injectable clock; e() escaping in the CLI.

Forward-reference concern (architect-flagged _cmd_retype call-before-def in _cli/_items.py): genuinely resolved, not masked. build_item_app (line 61) references _cmd_retype (defined line 211) but is only invoked from _cli/__init__.py:101 after the module is fully imported, so the name binds at call time. Confirmed by the green test suite and a live CLI run.

Gate: 635 passed / 1 skipped; pyright 0 errors; ruff check + format clean.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 115 add-finding "…" --severity high`; track with `sq review 115 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Open |  | Avoidable type suppression in _carry_or_reset_status |
| F2 | 🟢 low | Open |  | Duplicated subentity-kind reverse map |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Avoidable type suppression in _carry_or_reset_status

<!-- sq:finding:F1:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
src/squads/_services/_retype.py: _carry_or_reset_status types current_status as 'object' and returns tuple[bool, object], which forces the '# type: ignore[assignment]' at line 129 (item.status = new_status). The inputs are fully typed: item.status is Status, workflow_for(...).states is set[Status], and initial_status(...) returns Status. Typing the param as Status and the return as tuple[bool, Status] removes the suppression entirely. CLAUDE.md asks for strict typing with no avoidable ignores. Non-blocking.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Duplicated subentity-kind reverse map

<!-- sq:finding:F2:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
src/squads/_services/_retype.py line 32 defines _SUBENTITY_KIND_FOR = {parent: k for k, parent in SUBENTITY_PARENT.items()}, which is byte-for-byte the same map already exported from _services/_base.py as SUBENTITY_KIND (line 45: {p: k for k, p in SUBENTITY_PARENT.items()}). The module already imports from _base. Reuse the existing SUBENTITY_KIND instead of recomputing it, so the reverse map has a single home. Non-blocking.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
