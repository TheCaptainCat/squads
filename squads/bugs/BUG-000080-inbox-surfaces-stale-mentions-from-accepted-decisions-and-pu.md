---
id: BUG-000080
sequence_id: 80
type: bug
title: Inbox surfaces stale mentions from Accepted decisions and Published guides
status: Done
author: manager
priority: medium
refs:
- ADR-000049
created_at: '2026-06-12T14:59:31Z'
updated_at: '2026-06-12T15:08:27Z'
---
<!-- sq:body -->
**Symptom (live, 2026-06-12).** op-pierre's inbox shows the acceptance-request mention from ADR-000049 — Accepted two days ago. The mention line ('this is Proposed for your acceptance') was written when the ADR was Proposed and is long resolved.

**Root cause.** The inbox scopes to open items via is_open() (_services/_collab.py), and is_open = not-in-TERMINAL — but Status.ACCEPTED is missing from the TERMINAL frozenset (_workflow.py), whose docstring says 'no further work expected — used to scope the inbox'. Same gap for PUBLISHED guides (symmetric workflow shape: Published → Deprecated|Draft mirrors Accepted → Superseded|Deprecated).

**Fix (operator-approved plan).** Add ACCEPTED and PUBLISHED to TERMINAL. Consumers audited, all favor it: inbox (the fix), blocked (accepting an ADR now unblocks dependents — more correct), list/tree/mine default filters (settled items move under --all, like Done), workload buckets (counted closed). Precedent that terminal-with-outgoing-transitions is safe: REJECTED is TERMINAL with Rejected → Proposed in the map.

**Out of scope.** Mention read/ack tracking (mentions never expire on open items) — its own feature if ever wanted.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T15:04:38Z] Elias Python:
  - Fix implemented and all gates green. Added ACCEPTED and PUBLISHED to the TERMINAL frozenset in src/squads/_workflow.py (two lines in the set + updated docstring explaining that terminal does not imply no outgoing transitions, with REJECTED as the pre-existing precedent).
  - New test file: tests/test_terminal_accepted_published.py — 19 tests covering: TERMINAL membership, inbox regression (BUG-000080 exact scenario for both decisions and guides), outgoing transitions still valid (Accepted to Superseded/Deprecated, Published to Draft/Deprecated), the full Draft/Published/Draft/Published cycle, blocked semantics (accepting an ADR unblocks depends-on tasks, same for Published guides), and CLI smoke (sq list default vs --all, sq search, sq blocked).
  - Sweep result: zero existing tests needed updating. No existing test assumed Accepted/Published items were open — the full suite passed before and after the change.
  - Gates: uv run pytest (all pass), uv run pyright (0 errors), uv run ruff check + format --check (clean). @reviewer please verify.
- [2026-06-12T15:07:57Z] Paul Reviewer:
  - APPROVED. Reviewed the TERMINAL change (S.ACCEPTED + S.PUBLISHED added) and the docstring; verified every consumer empirically in a throwaway squad (and the inbox fix read-only on the real squad).
  - Empirical results — inbox: @reviewer mention on Proposed ADR visible, gone after Accept (bug fixed); real squad 'sq inbox op-pierre' no longer surfaces ADR-000049. blocked: depends-on Proposed ADR blocks the task, accepting unblocks it (same for Published guide). list/mine/tree: Accepted/Superseded/Published hidden by default, shown with --all; tree rejects a closed root without --all, roots it with. search: finds Accepted ADR and Published guide. workload: closed work items land in the closed bucket (decisions/guides are non-work, correctly excluded).
  - Transitions confirmed live: Accepted→Superseded, Published→Draft→Published, and Published→Deprecated→Published all legal — terminal membership does not block the documented exits.
  - Gates: pytest green (incl. all 19 new tests), pyright 0 errors, ruff check + format clean, sq check no issues.
  - Docstring: honest and accurate — explicitly states terminal does not imply no outgoing transitions and enumerates the exits (Rejected→Proposed, Accepted→Superseded|Deprecated, Published→Deprecated|Draft), distinguishing the transition map (legal moves) from the set (settled-for-scoping).
  - Non-blocking opinion on test sizing: 19 tests for a 2-line change is right-sized rather than padded — they layer model/service/CLI per the project's testing convention. Minor redundancy: the pure can_transition asserts overlap the service-level cycle tests, and the parametrized test_cli_decision_by_status_filter exercises the --status filter more than this change. Fine to keep; no action required.
<!-- sq:discussion:end -->
