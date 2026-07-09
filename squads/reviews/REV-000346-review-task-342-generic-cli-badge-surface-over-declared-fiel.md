---
id: REV-346
sequence_id: 346
type: review
title: 'Review TASK-342: generic CLI badge surface over declared fields'
status: Approved
author: reviewer
refs:
- TASK-342:addresses
subentities:
- local_id: F1
  title: 'ordered flag never enforced: --min-badge/--sort rank by declaration order
    on any collection'
  status: Fixed
  assignee: tech-lead
  severity: medium
- local_id: F2
  title: Generic --badge/--min-badge CODE=VALUE do not validate code or value; typos
    silently return empty
  status: WontFix
  severity: low
- local_id: F3
  title: Per-field --<field> option generation delivered as a generic --badge escape
    hatch instead
  status: WontFix
  assignee: tech-lead
  severity: low
- local_id: F4
  title: Badge-rendering helpers misplaced in _discussion.py; relocate to a _badges
    module (deferred)
  status: Fixed
  severity: low
- local_id: F5
  title: tests/test_custom_badge_axis.py docstring leads with a real ticket ID (no-ticket-IDs-in-code)
  status: Fixed
  severity: low
created_at: '2026-07-09T12:38:59Z'
updated_at: '2026-07-09T19:23:21Z'
---
<!-- sq:body -->
Independent review of the uncommitted TASK-342 diff on release/0.8: the CLI badge surface is made generic over spec-declared fields and the per-axis parse/render pairs (F1) are collapsed into one path.

Verdict: APPROVE. Default surface is byte-identical, F1 is genuinely collapsed, the generic derivation is proven end-to-end by a custom incident/impact/urgency axis, and all gates + targeted suites are green. Findings below are all non-blocking follow-ups.

Scope checked: byte-identical default (golden + manual smoke), generic parse_badge_code/badge_render/resolve_collection derivation, Item.badge_value/set_badge_value storage, ItemFilter.badges/badge_min/_meets_min, finding-severity default via field/collection default, and hygiene.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 346 add-finding "…" --severity high`; track with `sq review 346 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Fixed | tech-lead | ordered flag never enforced: --min-badge/--sort rank by declaration order on any collection |
| F2 | 🟢 low | WontFix |  | Generic --badge/--min-badge CODE=VALUE do not validate code or value; typos silently return empty |
| F3 | 🟢 low | WontFix | tech-lead | Per-field --<field> option generation delivered as a generic --badge escape hatch instead |
| F4 | 🟢 low | Fixed |  | Badge-rendering helpers misplaced in _discussion.py; relocate to a _badges module (deferred) |
| F5 | 🟢 low | Fixed |  | tests/test_custom_badge_axis.py docstring leads with a real ticket ID (no-ticket-IDs-in-code) |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — ordered flag never enforced: --min-badge/--sort rank by declaration order on any collection

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Assignee:** Olivia Lead
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
Collection.ordered (_workflow/_models.py:148) is documented as 'drives sort + threshold filtering' and ADR-323 says ordered=true 'enables --min-<field>'. But nothing reads the flag: grep '\.ordered' across src returns nothing (only two test asserts). _badge_rank (_cli/_main.py) and ItemFilter._meets_min (_services/_base.py) both rank purely by badge position in coll.badges regardless of ordered. On a custom UNORDERED collection, --min-badge/--sort silently produce a meaningless declaration-order ranking instead of being disabled/rejected as the task ('ordered only') and ADR specify.

Blast radius: zero for the bundled defaults (priority+severity are both ordered=true) and zero for the custom-axis test (level is ordered=true), so default behavior and the shipped test are correct. Manifests only with a future unordered collection.

Fix: enforce ordered in _meets_min/_badge_rank (skip or raise for unordered fields), or drop the flag if unordered isn't a real case. Non-blocking for 342.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-07-09T12:51:07Z] Elias Python:
  - Fixed: spec load now fails closed on an unordered collection (WorkflowSpec._validate -> _check_field_collections, src/squads/_workflow/_models.py) — 'collection <code>: unordered collections are not supported yet'; ordered stays reserved in the schema per ADR-323 §3 but is no longer silently ignored. Tests: test_unordered_collection_fails_closed + test_unordered_collection_override_fails_closed (tests/test_workflow_badges.py).
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Generic --badge/--min-badge CODE=VALUE do not validate code or value; typos silently return empty

<!-- sq:finding:F2:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
parse_badge_code validates --priority against the collection and errors clearly ('unknown priority \'bogus\' (one of: urgent, high, medium, low)'). The generic --badge/--min-badge CODE=VALUE path (_parse_badge_pairs in _cli/_main.py) only splits+lowercases: it validates neither the field CODE nor the VALUE. Verified: 'sq list --badge priority=bogus' exits 0 with an empty result rather than the clear error --priority gives.

UX inconsistency between the dedicated sugar and the generic escape hatch. Non-blocking; consider validating via resolve_collection+parse_badge_code when a field/collection resolves.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-07-09T12:52:22Z] Catherine Manager:
  - Deferred/accepted: the generic --badge/--min-badge escape hatch not validating code/value is a minor power-user UX gap; the dedicated --priority path gives the clear error. Revisit only if the generic path sees real use.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Per-field --<field> option generation delivered as a generic --badge escape hatch instead

<!-- sq:finding:F3:head -->
**Status:** ⚫ Wont Fix
**Assignee:** Olivia Lead
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
TASK-342 'Areas/files' for _main.py reads 'Options are generated per the active spec's fields' and '--<field> filter'. The dev instead kept --priority/--min-priority as byte-identical bundled sugar and added a generic --badge/--min-badge/--sort CODE=VALUE surface for every other field. The literal per-field flag (--impact/--urgency) is not generated.

Assessment: defensible and arguably better. Typer options are fixed at import time while the active spec is per-invocation (--dir/cwd), so dynamically generating per-field flags is fragile. The functional Done criterion (works for any declared field, proven by the custom-axis test) is met. Recording for tech-lead confirmation that this interpretation is accepted; not a blocker.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-07-09T12:52:21Z] Catherine Manager:
  - Accepted as designed: per-field --<field> Typer options are import-time while the spec is per-invocation, so the generic --badge/--min-badge CODE=VALUE escape hatch (plus byte-identical --priority/--min-priority sugar) is the correct shape. Not a defect.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Badge-rendering helpers misplaced in _discussion.py; relocate to a _badges module (deferred)

<!-- sq:finding:F4:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
op-pierre-flagged cohesion finding. _status_badge, resolve_collection, and badge_render live in _discussion.py, whose remit is comment/story/subtask prose + @mention extraction. These are presentation helpers, not discussion; they landed here for historical reasons (old sub-entity-head severity badges). _cli/_common and _cli/_main now import them from _discussion, which is a layering smell.

Disposition: LOW / deferred. A clean byte-identical relocation to a top-level _badges.py after 342/343 land. NOT a blocker for 342. Note: TASK-345 was scaffolded for exactly this move but is currently Cancelled; this finding is the tracked home for it and a fix-task should be (re)dispatched on the settled code.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-07-09T15:06:51Z] Elias Python:
  - Fixed by TASK-347: _status_badge/resolve_collection/badge_render (+ _DEFAULT_BADGE) relocated verbatim from _discussion.py to a new src/squads/_badges.py; callers repointed (_discussion, _cli/_common, _cli/_main, _cli/_items). Byte-identical, no golden change.
- [2026-07-09T19:23:21Z] Paul Reviewer:
  - Reviewer verification (independent): the relocation is sound. status_badge / resolve_collection / badge_render / _DEFAULT_BADGE now live in src/squads/_badges.py with byte-identical bodies (diffed vs 53e651c:_discussion.py — only the _status_badge→status_badge rename + the two docstring cross-refs differ). _discussion.py is left cohesive (comments/story/subtask prose + @mention) and delegates via 'from squads import _badges as badges'. All callers repointed (_discussion, _cli/_common, _cli/_main, _cli/_items); grep shows zero lingering _discussion._status_badge / discussion.badge_render refs in src. No import cycle: _badges only pulls WorkflowSpec/bundled_spec from _workflow (which imports neither _badges nor _discussion); _models stays spec-decoupled; runtime import of both modules confirmed clean. Sub-entity head/summary still reach the badges through the delegation; targeted render suites green. Gates green (pyright/ruff/format), 215 targeted tests pass. Nit (dev comment): the move was NOT strictly 'verbatim' — _status_badge was promoted to public status_badge; correct, and every reference is updated. Confirmed Fixed.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — tests/test_custom_badge_axis.py docstring leads with a real ticket ID (no-ticket-IDs-in-code)

<!-- sq:finding:F5:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
The new test file is well-named by behavior (test_custom_badge_axis.py) but its module docstring opens with 'TASK-000342: ...', a real ticket ID in source — against the project convention (keep the ticket pointer in the sq comment/PR, name code by behavior). Trivial: drop the ID prefix from the docstring, keep the behavioral description. Nit, non-blocking. (Also minor: tests/test_graph.py:675 docstring still references the now-removed priority_badge().)
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-07-09T12:51:08Z] Elias Python:
  - Fixed: dropped the 'TASK-000342:' ticket-ID prefix from tests/test_custom_badge_axis.py's module docstring (now leads with the behavior description); also fixed the stale priority_badge() reference in tests/test_graph.py:675's docstring to say badge_render().
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-09T12:40:45Z] Paul Reviewer:
  - APPROVE. Independent review of the uncommitted TASK-342 diff (read-only, no full suite — main loop ran it green, 0 failures/151s).
  - Byte-identical default: CONFIRMED. Golden JSON/rendered/show_render (104 tests) pass with zero regen; manual smoke on a fresh no-override squad shows the Priority column, 🟠 high raw-code badge, and listing order unchanged. All new options (--min-priority/--badge/--min-badge/--sort) are additive/optional.
  - F1 collapsed: CONFIRMED. grep of parse_priority|parse_severity|priority_badge|_severity_badge|_severity_emoji|_badge_emoji across _cli+_discussion is empty; one parse_badge_code + one badge_render(as_label=…) + resolve_collection drive every axis.
  - Generic derivation: CONFIRMED and genuinely exercise-level. test_custom_badge_axis.py drives create/--set/--badge/--min-badge/--sort/show-panel on a custom incident type with impact+urgency off one 'level' collection (ADR-323's own reuse example), plus unknown-code rejection and a bundled-axis parity test — not just parse. Storage (Item.badge_value/set_badge_value, --set <field>=<code> for any field via _badge_field, _ITEM_BADGE_ATTR_FIELDS shim deleted), ItemFilter.badges/badge_min/_meets_min rank resolution, and add_finding's field/collection-default severity (_field_default, closes the 341 forward-note) all verified.
  - Gates (re-run independently): pyright 0 errors, ruff check clean, ruff format clean. Targeted suites green: priority_views/custom_badge_axis/discussion/tree/workflow_badges/custom_status_badges (108), golden+render (104), graph (33).
  - 5 findings, all NON-BLOCKING follow-ups: F1(medium) the Collection.ordered flag is documented as load-bearing for sort/threshold but never read — --min-badge/--sort rank by declaration order on any collection (zero impact on the all-ordered bundled defaults); F2/F3/F4/F5(low) generic --badge value/code not validated, per-field-option interpretation, badge helpers misplaced in _discussion (op-pierre's cohesion flag — deferred relocation to _badges.py; TASK-345 is Cancelled and this finding is its tracked home), and a ticket ID in the new test's docstring.
  - @tech-lead: F1 (ordered enforcement) and F3 (confirm the generic --badge interpretation vs literal per-field flags) are yours to disposition; F4's relocation should be (re)dispatched on settled code post-342/343.
<!-- sq:discussion:end -->
