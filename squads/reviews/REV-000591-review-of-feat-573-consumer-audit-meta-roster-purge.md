---
id: REV-591
sequence_id: 591
type: review
title: 'Review of FEAT-573: consumer audit + meta->roster purge'
status: Approved
author: reviewer
refs:
- FEAT-573
subentities:
- local_id: F1
  title: Test file name still says 'meta_type' after the terminology purge
  status: Verified
  severity: low
- local_id: F2
  title: retype validator name/message still uses 'work' for the non-roster (work+records)
    set
  status: WontFix
  severity: low
created_at: '2026-07-22T12:52:05Z'
updated_at: '2026-07-22T12:54:08Z'
---
<!-- sq:body -->
Independent review of FEAT-573 (TASK-588 constant rename, TASK-589 consumer audit + work_types rework, TASK-590 terminology purge). Behavior-preserving refactor: no functional diff for the bundled spec.

Verdict: APPROVE. The two-meta-concepts trap is cleanly avoided and the reclassification is faithful. Two Low naming nits, neither blocking.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 591 add-finding "…" --severity medium`; track with `sq review 591 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Verified |  | Test file name still says 'meta_type' after the terminology purge |
| F2 | 🟢 low | WontFix |  | retype validator name/message still uses 'work' for the non-roster (work+records) set |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Test file name still says 'meta_type' after the terminology purge

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
TASK-590 purged the docstring inside tests/cli/test_meta_type_address_verbs_and_list_removal.py (meta-type -> roster-type) but left the FILENAME as test_meta_type_address_verbs_and_list_removal.py. This now contradicts both its own updated docstring and the new CONTRIBUTING convention (no 'meta' for the roster-type concept). Behavior-neutral; a rename to test_roster_type_address_verbs_and_list_removal.py would complete the purge. Renaming test files was not in TASK-590's enumerated scope, hence Low, but the feature's stated intent was 'drop meta repo-wide'.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — retype validator name/message still uses 'work' for the non-roster (work+records) set

<!-- sq:finding:F2:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
src/squads/_services/_retype.py: _validate_work_types() now checks spec.non_roster_types() (work+records) but keeps the name _validate_work_types and the message 'only work items can be retyped'. This imprecision (records like decision/guide are valid retype targets) predates this work and is behavior-preserving, so not a regression. Noting it because the audit touched this exact site; whether records SHOULD be retype targets is a design question, not a bug. Optional tightening.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T12:52:40Z] Paul Reviewer:
  - Trap-avoidance VERIFIED (highest risk): _migrations/ zero diff (incl. _meta_compat.py); loader's is_meta back-compat shim intact — literal "is_meta" and _pop_legacy_is_meta preserved, only the META_TYPES ref inside became ROSTER_TYPES; legacy :meta sub-entity markers and _cli/_common.py local 'meta' var untouched (zero diff). Only the roster vocabulary changed.
  - Faithful-reclassification VERIFIED: META_*->ROSTER_* is a pure symbol rename across constants + ~15 by-name dispatch sites, zero logic change. item_is_roster sites left as roster-vs-not (correct). work_types()->non_roster_types() is a faithful rename — every call site (create/__init__ command registration, retype targets, playbook coverage, tui filter/search) genuinely means non-roster=work+records; none needed a narrower is-work/is-records split, so no new predicate was warranted. _tui/_tree.py untouched (FEAT-570 territory).
  - Gates: sq check clean; pyright 0/0/0, ruff check + format clean (--all-extras); relevant test files (reserved-vocab/rename/retype/capability-flags/types-cli) green. No ticket IDs added. The 2 user-facing error-string wording changes (_rename.py, _workflow/_models.py) have matching updated test assertions. Manifest hashes updated only under the 0.12.0 (unreleased) key — no released entry corrupted.
  - Verdict: APPROVE. Two Low naming nits (F1 lingering test filename, F2 pre-existing retype 'work' imprecision) — neither blocks. Leaving the Approved transition to the main loop. @manager
<!-- sq:discussion:end -->
