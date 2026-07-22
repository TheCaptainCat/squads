---
id: REV-555
sequence_id: 555
type: review
title: 'Review of FEAT-533 Increment A: request-context seam'
status: Approved
author: reviewer
refs:
- FEAT-533
subentities:
- local_id: F1
  title: 'Stale main_callback comment: clock no longer force-reset at edge'
  status: Verified
  severity: low
- local_id: F2
  title: CLI edge not yet fresh-context-per-request (clock leak pre-US5)
  status: Verified
  severity: low
- local_id: F3
  title: TASK-548 code-cache allowlist not exhaustive for TASK-549 guard
  status: Verified
  severity: low
created_at: '2026-07-21T22:04:28Z'
updated_at: '2026-07-22T14:03:24Z'
---
<!-- sq:body -->
Independent review of FEAT-533 Increment A — the request-scoped context seam (TASK-548 static-state audit, TASK-550 RequestContext primitive + clock/actor migration, TASK-551 conftest fixture rework). Verdict: APPROVE WITH NITS. The seam is correct, isolation-safe, and behavior-preserving for one-shot CLI use. The one deliberate production change — apply_timestamp's no-op on absent --at — is correct and necessary (it is what lets frozen_time's clock_override rebind survive a CliRunner.invoke's root callback; a fresh process/context starts at None so single-shot is byte-identical to before, and per ADR-534/ADR-77 clearing between requests is the fresh-context's job, not this call's). All findings are Low: two documentation/forward-looking notes on the CLI edge, one audit-completeness gap feeding the not-yet-built TASK-549 guard. No code correctness defect.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 555 add-finding "…" --severity medium`; track with `sq review 555 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Verified |  | Stale main_callback comment: clock no longer force-reset at edge |
| F2 | 🟢 low | Verified |  | CLI edge not yet fresh-context-per-request (clock leak pre-US5) |
| F3 | 🟢 low | Verified |  | TASK-548 code-cache allowlist not exhaustive for TASK-549 guard |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Stale main_callback comment: clock no longer force-reset at edge

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
In main_callback (_cli/__init__.py, the block above actor.set_actor("system")), the comment states that the unconditional re-set 'is the same mechanism apply_timestamp uses for the clock (no try/finally needed).' That is no longer true: this increment made apply_timestamp a no-op when --at is absent, so the clock is NOT force-reset at the edge the way actor/session are. The comment now misdescribes the code.

Impact: Low, comment-only, no runtime effect. But it is exactly the kind of note a future daemon/server author would trust when deciding whether the CLI edge self-clears per request. Failure scenario: they reuse main_callback per request believing the clock resets like actor/session; it does not (only a fresh RequestContext bind clears clock_override), so request N's --at silently backdates request N+1.

Recommendation: update the comment to say the actor/session force-reset is a belt-and-suspenders edge reset, while the clock is intentionally left to the (future) fresh-per-request context bind — cross-reference the apply_timestamp docstring.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-07-21T22:27:08Z] Elias Python:
  - Reworded in TASK-552: the belt-and-suspenders actor/session force-reset vs. the clock's deliberate carry-forward are now called out explicitly in _cli/__init__.py's _resolve_clock_override docstring/comment.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — CLI edge not yet fresh-context-per-request (clock leak pre-US5)

<!-- sq:finding:F2:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
Observation, forward-looking (adjacent to this increment, not a defect in it). main_callback force-resets actor (set_actor("system")) and session (seed_session(from_env=True)) on every invocation, but after this change does not reset the clock. For one-shot CLI use this is invisible and correct (a fresh process starts with clock_override=None). It does mean the CLI edge is not yet 'one fresh RequestContext per request' — that consolidation is US5/TASK-552's bind_context(RequestContext(...)) per the architect's boundary rule.

Failure scenario: if the daemon fast-path (a motivation named in FEAT-533) reuses main_callback in a long-lived process BEFORE US5 lands, a prior --at leaks into a later no---at invocation, because nothing clears clock_override between them. actor/session would be safe (they force-reset); the clock would not.

Recommendation: none for this increment — single-shot is correct. Flagging so the US5 dependency is explicit: the clock no-op is only fully safe once the edge binds a fresh RequestContext per request. Do not ship the daemon reusing main_callback until US5 lands.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-07-21T22:27:09Z] Elias Python:
  - Resolved by TASK-552: main_callback now assembles one bind_context(RequestContext(...)) per invocation (clock/actor/session/spec/dir/client_cwd all freshly computed), closing the pre-US5 hybrid-reset gap this finding flagged.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — TASK-548 code-cache allowlist not exhaustive for TASK-549 guard

<!-- sq:finding:F3:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
TASK-548's acceptance says the sanctioned-code allowlist for the TASK-549 AST guard is 'enumerated exactly'. It is not exhaustive. A module-scope dict/list/set scan across the engine also hits immutable constant lookup tables not on the list: _models/_metadata._GENERIC_FIELDS, _workflow/_models._SIDE_PRIORITY, _services/_retype._BUNDLED_CONTAINER_HEADINGS, _roles/_resolver._PREDEFINED_BY_SLUG, _backends/_claude_code/_frontmatter._VALID_MODELS, and the migration tables (_v0_2_to_v0_3._KIND_BY_TYPE, _v0_1_to_v0_2._BODY_KIND, _meta_compat._LOCAL_ID_PREFIX). Also minor: the audit places _PREDEFINED_BY_SLUG in _catalog.py; it lives in _resolver.py.

All of these are correctly CODE (built once from literals, never mutated), so the substantive DATA-vs-CODE conclusion is sound and nothing DATA was missed or misclassified. The gap is purely allowlist exhaustiveness.

Failure scenario: TASK-549 ships the AST guard against the enumerated allowlist as-is → build goes red on day one from these pre-existing constants, or the guard has to distinguish 'assigned-once-from-literal constant' from 'mutable cache'. Recommendation: expand the allowlist (or the guard's mutable-detection heuristic) before TASK-549 lands; fix the _PREDEFINED_BY_SLUG location note.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T22:05:59Z] Paul Reviewer:
  - Verdict: APPROVE WITH NITS. Increment A (TASK-548/550/551) is correct, isolation-safe, and behavior-preserving for one-shot CLI use. The apply_timestamp no-op on absent --at is correct and necessary (it stops the root callback from clobbering frozen_time's clock_override on the first CliRunner.invoke; single-shot is byte-identical to before; per ADR-534/ADR-77 clearing between requests is the fresh-context's job).
  - All 3 findings are Low: F1 stale comment, F2 forward-looking CLI-edge asymmetry (US5 dependency), F3 audit allowlist not exhaustive for the not-yet-built TASK-549 guard. None block this increment — F2/F3 feed forward work. Approving; findings left Open as trackers.
- [2026-07-22T14:03:24Z] Catherine Manager:
  - F3 (allowlist not exhaustive) was resolved when the AST-guard allowlist was completed + extended to factory-built caches during the Phase-B guard work (REV-557 F1); the guard is green in-tree. Closing.
<!-- sq:discussion:end -->
