---
id: REV-585
sequence_id: 585
type: review
title: 'Review of FEAT-568 Phase B: validator catalog'
status: Approved
author: reviewer
refs:
- FEAT-568
subentities:
- local_id: F1
  title: create/update/reparent gate now runs the full per-item error-level set
  status: WontFix
  severity: low
created_at: '2026-07-22T11:33:31Z'
updated_at: '2026-07-22T11:46:30Z'
---
<!-- sq:body -->
Independent read-only review of FEAT-568 Phase B (TASK-581 catalog lift, 582 route+sort, 583 assignment surface + Plane-1). Reviewed against ADR-541 and Robert's 3 pinned decisions. Diffed the retired `_check_*` methods (HEAD) against the lifted named validators check-by-check.

VERDICT: Approved. SET-preservation holds; the author/assignee vs agent_registered split is correct; the deterministic sort, bundle composition, Plane-1/layering, and error-only gate are all correct. TASK-584 (records/epic no_parent) is correctly absent (gated on FEAT-572). One Low informational finding (gate widening) — surface-to-operator, not a blocker.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 585 add-finding "…" --severity medium`; track with `sq review 585 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | WontFix |  | create/update/reparent gate now runs the full per-item error-level set |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — create/update/reparent gate now runs the full per-item error-level set

<!-- sq:finding:F1:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
gate() runs the item's full effective per-item set and aborts on the first error-level issue. Since the catalog is now populated, create/update/reparent hard-abort on item_status_valid / subtask_story_mapping / subentity_status_valid / parent_in — where today only parent-TYPE (via _check_parent) and author/assignee were hard gates; those three error-level checks were previously sq-check-report-only. reparent/link, which today only checked parent existence+type, now gates the full set on the child.

This is intended per ADR-541 ('one engine, two call sites; create/update runs in abort mode'), the full suite is green, and these are invariants that should always hold. NOT a regression and NOT a blocker — but it IS a behavior widening of the create/update gate beyond strict today-behavior, in the same class as the sort-order change Robert already flagged for operator surfacing. Failure scenario: a flow that previously updated an item into a transiently-invalid state (e.g. a status the type's lifecycle doesn't contain, reachable via --force elsewhere) now aborts instead of succeeding-with-a-later-check-warning. Recommend: note it in the FEAT-568 operator handoff next to the sort-order change. WontFix as code — recording for visibility.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T11:34:19Z] Paul Reviewer:
  - SET-preservation: VERIFIED check-by-check. All 8 retired _check_* methods (reconciliation, backends, items[status/parent/ref/agent], subtask_stories, subentity_status, decisions, unwritten_bodies, status_banners, title_lengths) have faithful named-validator equivalents with identical level/item/message. None dropped, none shifted. Body text now threaded once via _scan_for_check's bodies map into report(bodies=) — no-status-banner/subentity-body-written are NOT silently dropped. Marker/no-id scan + drift + override checks retained as residue; no double-run (old empty-catalog engine call + hardcoded calls both removed). sq check on this repo clean (exit 0).
  - Author-split (Elias's deliberate deviation): CORRECT. _is_participant (role/operator only, excludes skill + self-author bootstrap) stays the create/update ABORT gate (_check_author/_check_assignee, raise SquadsError). agent_registered is warn-level + roster-INCLUSIVE (item_is_roster incl. skill) for sq-check report only. Folding them WOULD regress: a skill slug would pass create/update silently (warn + roster-inclusive). Confirmed non-redundant, non-conflicting — different plane (abort vs report), membership (excl-skill vs incl-skill), level. Pinned test test_a_skill_slug_is_not_a_valid_author... passes.
  - Sort (decision #2): CORRECT. Key (has_item, seq or 0, level_rank err<warn, message), stable, applied to workflow_issues+svc.check() at the report boundary for BOTH console and --json; gate() unsorted. Same SET, stable total order. Minor: reconciliation issues carrying a real id sort into the item block (not the no-item leading block) — consistent with the pin's resolvability-based '(no item)' definition, not a defect.
  - Bundle composition (#4): CORRECT. no_parent WITHHELD from records bundle (records=core+supersedes_incoming) and NOT added to epic (work bundle carries no no_parent) — byte-identical until 584. COMMON_CORE + roster/work/records map to the right names. assert set(CATALOG)==VALIDATOR_NAMES + squad-global equivalent present. Plane-1/layering (#3/#5): VALIDATOR_NAMES/SQUAD_GLOBAL/PARAMETERIZED in _workflow/_models.py; membership check param-aware; no empty-parent_in check (correctly moot per architect corollary); ItemSpec.validators validated at load; NO back-edge (_workflow does not import _services); acyclic preserved. gate() error-only (#6): correct, matches today (create/update never aborted on warn). TASK-584 correctly absent.
  - One Low finding (F1, WontFix): gate now runs the full per-item error-level set at create/update/reparent — a deliberate ADR-541 unification, worth surfacing to the operator alongside the sort-order change. @tech-lead @manager: Approved.
- [2026-07-22T11:46:30Z] Catherine Manager:
  - F1 (create/update/reparent now gate the full per-item error set) is the intended ADR-541 one-engine/abort-mode unification, not a regression — QA confirmed valid mutations succeed and invalid ones abort cleanly. Marked WontFix and flagged to the operator as a behavior change alongside the deterministic sq check sort.
<!-- sq:discussion:end -->
