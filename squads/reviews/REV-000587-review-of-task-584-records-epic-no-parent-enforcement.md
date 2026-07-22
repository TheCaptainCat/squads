---
id: REV-587
sequence_id: 587
type: review
title: 'Review of TASK-584: records + epic no_parent enforcement'
status: Approved
author: reviewer
refs:
- FEAT-568
subentities:
- local_id: F1
  title: Correct wiring, no over-reach
  status: Verified
  severity: info
- local_id: F2
  title: sq check clean on this repo
  status: Verified
  severity: info
- local_id: F3
  title: Enforcement genuine (tests not tautological)
  status: Verified
  severity: info
- local_id: F4
  title: Stale _no_parent function docstring
  status: Verified
  severity: low
created_at: '2026-07-22T12:10:14Z'
updated_at: '2026-07-22T12:13:53Z'
---
<!-- sq:body -->
Focused review of the TASK-584 wiring change (turning on records + epic `no_parent`, unblocked by the FEAT-572 ADR migration). The `no_parent` validator itself was reviewed/approved in REV-585; this reviews only the wiring.

Scope reviewed: the diff to `_services/_validators.py` (CATEGORY_BUNDLES + docstrings) and `_workflow/default_workflow.toml` (epic validators), plus `tests/service/test_records_epic_no_parent_enforcement.py`.

**Verdict: Approve.** Wiring is correct, minimal, and non-over-reaching; enforcement genuine; sq check clean (exit 0); all 10 targeted tests pass. One Low finding (stale function docstring), non-blocking.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 587 add-finding "…" --severity medium`; track with `sq review 587 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🔵 info | Verified |  | Correct wiring, no over-reach |
| F2 | 🔵 info | Verified |  | sq check clean on this repo |
| F3 | 🔵 info | Verified |  | Enforcement genuine (tests not tautological) |
| F4 | 🟢 low | Verified |  | Stale _no_parent function docstring |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Correct wiring, no over-reach

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🔵 Info
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
`no_parent` appears in exactly two places: `CATEGORY_BUNDLES["records"] = ("no_parent", "supersedes_incoming")` and epic's per-type `validators = ["no_parent"]` in default_workflow.toml. Verified nowhere else: work types feature/task/bug/review and all roster types (role/skill/operator) carry no `validators` field and no `no_parent`. `_run_per_item` threads `tuple(item_spec.validators)` as `extra`, so epic's addition composes as common_core + work bundle + no_parent. Epic is category=work, parents=[], so its `parent_in` is vacuous and `no_parent` narrows it with no conflict — a pure AND-compose tightening.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — sq check clean on this repo

<!-- sq:finding:F2:head -->
**Status:** 🟢 Verified
**Severity:** 🔵 Info
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
`uv run sq check` exits 0 (no issues) on this repo. The FEAT-572 migration re-homed the 5 formerly-parented ADRs to `related` refs and there are no parented epics, so turning on the two enforcements surfaces zero new violations here — Plane-2 report stays clean, load is not bricked.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Enforcement genuine (tests not tautological)

<!-- sq:finding:F3:head -->
**Status:** 🟢 Verified
**Severity:** 🔵 Info
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
Enforcement is real, not tautological. Create path gates via ValidatorEngine.gate() at _base.py:401; link/reparent path sets child.parent then gates at _items.py:191. `_no_parent` emits an **error**-level CheckIssue (`{type} takes no parent (got {parent})`) so gate() aborts. The link/create tests assert `match="takes no parent"` — the exact _no_parent string; a different validator firing would fail the match, so the assertion is load-bearing. The check() tests corrupt parent inside a real store transaction and assert the report surfaces the item+message. Parentless-still-succeeds is covered for decision/guide/epic. All 10 tests pass.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Stale _no_parent function docstring

<!-- sq:finding:F4:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
The module docstring, CATALOG comment, CATEGORY_BUNDLES comment, and effective_validator_names docstring were all correctly refreshed to describe the live wiring. But the `_no_parent` function docstring (`_services/_validators.py:147-148`) still ends "Not yet selected by any bundle." — now false: it is selected by the `records` bundle and epic's `validators`. Non-blocking (comment-only, zero functional impact), but it contradicts the now-live enforcement and should be corrected to match the other refreshed docstrings. Recommend dropping that trailing sentence.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T12:12:02Z] Paul Reviewer:
  - Approved. Wiring is correct and minimal — no_parent lands only on the records bundle + epic's validators; work/roster untouched. sq check clean (exit 0), all 10 enforcement tests genuine and green. One non-blocking Low finding (F4): the _no_parent function docstring still says "Not yet selected by any bundle" (stale post-wiring) — safe to land as-is and fix in the next comment sweep. @python-dev
<!-- sq:discussion:end -->
