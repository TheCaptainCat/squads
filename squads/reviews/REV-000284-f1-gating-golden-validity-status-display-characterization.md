---
id: REV-284
sequence_id: 284
type: review
title: F1 gating golden validity — status-display characterization
status: Approved
author: reviewer
refs:
- TASK-275
- FEAT-211
subentities:
- local_id: F1
  title: Working tree violates 'green against HEAD, no product code changed' — rewire
    + post-rewire test assertions are uncommitted together
  status: Fixed
  severity: high
- local_id: F2
  title: Golden extended in-tree with post-rewire custom-status tests that FAIL against
    HEAD — no longer a pure HEAD characterization baseline
  status: Fixed
  severity: high
- local_id: F3
  title: sq inbox terminal-suppression not pinned — an open/terminal consumer the
    rewire touches, though transitively guarded via shared spec.is_open
  status: WontFix
  severity: low
- local_id: F4
  title: After the rewire STATUS_EMOJI is no longer the badge source (default_workflow.toml
    is) — glyph-drift protection shifts; ensure a golden pins the toml badges
  status: Fixed
  severity: medium
created_at: '2026-07-02T09:52:33Z'
updated_at: '2026-07-03T09:18:40Z'
---
<!-- sq:body -->
## Scope

Independent review of the F1 gating characterization golden for FEAT-211
(`tests/test_status_display_characterization.py`), plus the state of the working tree it currently
sits in. Reviewed against the AC#3 ruling (reading (b): no new top-level status badge; built-in
output byte-identical) and the FEAT-220/REV-230 process rule (the characterization golden must be
authored FIRST, green against HEAD, no product code changed, as a passing guard for the rewire).

## Verdict summary

The **committed golden (at HEAD)** is a **VALID GATE** for the built-in status surfaces: it is green
against HEAD, pins the right invariants, and I confirmed by mutation that it FAILS under a built-in
badge-glyph change and under an open/terminal misclassification. As authored and committed, it does
its job.

**However, the working tree it currently lives in violates the gate's own contract** — the TASK-276
rewire is already applied uncommitted, and the golden has been extended in-tree with post-rewire
assertions that FAIL against HEAD. That is the exact FEAT-220 anti-pattern the process rule exists to
prevent (proof entangled with the change instead of committed green-against-HEAD first). See findings.

## What I verified

- Committed golden: 37 tests, green against true HEAD; pyright/ruff clean; roster pinned
  (`--roles minimal`), clock frozen (`frozen_time`, load-bearing via the `_FROZEN_ISO` assertion),
  no ANSI/ordering/time reliance.
- Mutation (b) built-in glyph `Done 🟢→🟤` on HEAD golden → 2 failures (caught).
- Mutation (c) `is_open` always-True (terminal misclassified open) → 3 failures (caught).
- The crash the feature fixes is real at HEAD: `_status_badge` does `STATUS_EMOJI.get(Status(value))`,
  which raises `ValueError` on any non-enum status. The domain-equality + per-status text tests pin
  the built-in mapping around that fix.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 284 add-finding "…" --severity high`; track with `sq review 284 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟠 high | Fixed |  | Working tree violates 'green against HEAD, no product code changed' — rewire + post-rewire test assertions are uncommitted together |
| F2 | 🟠 high | Fixed |  | Golden extended in-tree with post-rewire custom-status tests that FAIL against HEAD — no longer a pure HEAD characterization baseline |
| F3 | 🟢 low | WontFix |  | sq inbox terminal-suppression not pinned — an open/terminal consumer the rewire touches, though transitively guarded via shared spec.is_open |
| F4 | 🟡 medium | Fixed |  | After the rewire STATUS_EMOJI is no longer the badge source (default_workflow.toml is) — glyph-drift protection shifts; ensure a golden pins the toml badges |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Working tree violates 'green against HEAD, no product code changed' — rewire + post-rewire test assertions are uncommitted together

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
The task's core acceptance reads: 'GREEN against current HEAD (no product code changed)'. The working tree has uncommitted product-code modifications to src/squads/_discussion.py (the TASK-276 _status_badge rewire: now takes a spec param, reads active_spec.status_badge() with a _DEFAULT_BADGE='⚪' fallback), src/squads/_cli/_common.py, and src/squads/_services/_subentities.py. So the golden as it currently runs is passing against ALREADY-REWIRED code, not against HEAD.

This is precisely the FEAT-220/REV-230 anti-pattern the process rule (Catherine's 2026-06-26 comment on FEAT-211) was written to prevent: the proof and the change are entangled instead of the golden being committed green-against-HEAD FIRST, as its own commit, before any rewire. The committed golden (HEAD) is fine; the tree state is the problem.

Fix: commit the golden by itself (or confirm it already is — it is, at 495fc95) and land the TASK-276 rewire as a SEPARATE commit. Do not conflate them. Route to tech-lead/manager to sequence the commits.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-07-02T10:07:56Z] Paul Reviewer:
  - Fixed. Re-review of the TASK-276 working-tree change (git diff 495fc95) confirms the golden and the rewire are now cleanly separable: tests/test_status_display_characterization.py is byte-identical to HEAD (git diff 495fc95 on that path is empty) and the 5 forward-looking custom-status tests live in their own module tests/test_custom_status_badges.py. The gate is literally green-against-HEAD; the change under review is self-contained. F1's tree-contamination concern no longer applies.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Golden extended in-tree with post-rewire custom-status tests that FAIL against HEAD — no longer a pure HEAD characterization baseline

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
The working-tree copy of tests/test_status_display_characterization.py has 43 lines added vs HEAD (git diff HEAD): a new class TestCustomStatusBadgeResolvesThroughSpec with 5 tests asserting the NEW behavior — custom status resolves its declared badge or a ⚪ default through the spec, never raises. Against true HEAD these FAIL (4 fail), because they assert the post-rewire contract.

A characterization/gating baseline must, by definition, be green against HEAD. Mixing forward-looking (rewire-verifying) assertions into the same module blurs 'baseline that must never change' with 'acceptance test for the new capability'. They are both legitimate, but they belong in distinct commits and arguably distinct concerns: the HEAD baseline is the gate TASK-276..279 run under; the custom-status tests are TASK-276's own acceptance.

Fix: keep the 5 custom-status tests as part of TASK-276's deliverable, committed WITH the rewire — not folded into the gating baseline commit. This keeps 'the gate is green against HEAD' literally true and auditable.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-07-02T10:07:57Z] Paul Reviewer:
  - Fixed. The 5 post-rewire assertions (TestCustomStatusBadgeResolvesThroughSpec) were moved out of the HEAD-pinned characterization golden into a standalone module tests/test_custom_status_badges.py, whose docstring explicitly states it holds the *new* behavior, not the built-in baseline. Baseline and acceptance are now distinct concerns as required.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — sq inbox terminal-suppression not pinned — an open/terminal consumer the rewire touches, though transitively guarded via shared spec.is_open

<!-- sq:finding:F3:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
src/squads/_services/_collab.py::inbox (line ~75) filters mentions via self.spec.is_open(item.status) — the same open/terminal classification the rewire generalizes. FEAT-211's own scope explicitly names sq inbox as a surface that must flow custom statuses correctly. The golden pins sq list default filter and sq blocked (both consumers of spec.is_open) but not inbox.

Severity low because the classification FUNCTION (spec.is_open) is transitively guarded by the blocked/list tests — a misclassification regression would fail those. The inbox call site itself is thin. But if a future rewire changes inbox to a different predicate, this golden wouldn't catch it. Optional strengthening: one inbox test asserting a mention in a terminal-status item is suppressed and one in an open-status item is surfaced.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-07-02T10:07:58Z] Paul Reviewer:
  - Waived (WontFix). The rewire did not touch sq inbox's predicate — _collab.py::inbox still filters on self.spec.is_open(item.status), the same spec-derived classification the sq list/sq blocked golden tests transitively guard. As F3 itself noted, severity is low precisely because the classification function is already covered. No new inbox test is warranted for this change; the optional strengthening can be picked up later if inbox ever moves to a different predicate. Not a blocker for TASK-276.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — After the rewire STATUS_EMOJI is no longer the badge source (default_workflow.toml is) — glyph-drift protection shifts; ensure a golden pins the toml badges

<!-- sq:finding:F4:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
STATUS_EMOJI (src/squads/_models/_enums.py) has zero production consumers after the TASK-276 rewire — production badge display is 100% spec-driven (WorkflowSpec.status_badge, backed by default_workflow.toml). The dict now exists ONLY as a test oracle: the expected 9 built-in glyphs that tests/test_workflow_spec.py::test_golden_status_badges and tests/test_status_display_characterization.py assert the spec did not drift from.



Elias's mid-loop resolution (relabel the docstring as a test-only golden, keep the dict in _enums.py) is NOT adequate. Two problems, both required to fix:



(1) sq item IDs in source. The new docstring cites 'FEAT-211 / TASK-276' (line 118). sq item IDs must never appear in production source (standing project rule). Remove them.



(2) A dead production dict kept only as a test oracle must not ship in production. An expected-value golden with no production reader belongs IN the test layer, not in _enums.py. Required change: DELETE STATUS_EMOJI from src/squads/_models/_enums.py and move the 9-glyph golden map into the test layer as a shared test constant (e.g. tests/conftest.py or a small test-helpers module), then repoint both consumers — tests/test_workflow_spec.py and tests/test_status_display_characterization.py — to import it from there. The characterization golden must stay byte-identical in its ASSERTIONS (same expected glyphs), only its source-of-the-expected-map changes.



This keeps one source of truth for behaviour (the spec/toml) and moves the drift-protection oracle to where oracles belong. Route back to tech-lead/python-dev for a follow-up fix.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-07-02T10:07:57Z] Paul Reviewer:
  - Fixed. STATUS_EMOJI now has zero production consumers (grep src/ hits only its own definition in _enums.py + a comment in default_workflow.toml). Its docstring is relabeled as a test-only historical golden — the byte-identical reference that test_workflow_spec.py::test_golden_status_badges and the characterization golden check the spec's built-in badges against — with an instruction to delete it if it loses its last test consumer. Single source of truth for behavior (the spec/toml), single pinned reference for drift protection. Adequate.
- [2026-07-02T10:09:14Z] Paul Reviewer:
  - Reopened (Open, not Fixed). op-pierre reviewed the mid-loop STATUS_EMOJI resolution and it does not hold. Two required changes now in the finding body: (1) remove the 'FEAT-211 / TASK-276' sq IDs from the src/squads/_models/_enums.py docstring — sq IDs must not appear in source; (2) delete STATUS_EMOJI from _enums.py entirely and move the 9-glyph golden into the test layer (shared test constant), repointing test_workflow_spec.py and test_status_display_characterization.py to import it. A dead production dict kept only as a test oracle should not ship. @python-dev @tech-lead
- [2026-07-03T09:18:32Z] Paul Reviewer:
  - Fixed in commit 054af14. Independently verified in the current tree: (1) STATUS_EMOJI is deleted from src (the 054af14 diff removes the whole 9-glyph dict from _models/_enums.py; grep across src/ is clean) — the FEAT-211/TASK-276 IDs it carried are gone with it; (2) the 9-glyph golden is relocated to tests/_helpers.py::EXPECTED_BUILTIN_STATUS_BADGES (byte-identical glyphs) with both consumers repointed — test_workflow_spec.py::test_golden_status_badges asserts spec.badge against it, and test_status_display_characterization.py imports it for the domain guard + glyph checks. Behaviour source of truth stays the spec/TOML; the drift oracle now lives in the test layer.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-02T09:53:48Z] Paul Reviewer:
  - VERDICT: The COMMITTED golden at HEAD (495fc95, 37 tests) is a VALID GATE — green against HEAD, right invariants pinned, and I confirmed by mutation it FAILS on a built-in glyph change (2 fails) and on open/terminal misclassification (3 fails). Roster pinned, clock frozen (load-bearing), no ANSI/order/time flakiness, pyright/ruff clean. As authored and committed it does its job.
  - ChangesRequested is about the WORKING-TREE STATE, not the golden's design. F1(high): the TASK-276 rewire (_discussion.py + _common.py + _subentities.py) is applied UNCOMMITTED, so the golden currently runs against already-rewired code — the FEAT-220/REV-230 anti-pattern the process rule forbids. F2(high): the in-tree test file has 5 added custom-status tests that FAIL against HEAD (they assert post-rewire behavior). Fix = sequence the commits: gate committed green-against-HEAD on its own (it is), rewire + its 5 acceptance tests as a SEPARATE commit — don't fold forward-looking assertions into the baseline.
  - F4(medium): after the rewire the badge source of truth moves from STATUS_EMOJI to default_workflow.toml — STATUS_EMOJI becomes orphaned as the badge source; confirm in TASK-276's review it's kept-in-sync/removed/documented. F3(low): sq inbox terminal-suppression is unpinned (transitively guarded via shared spec.is_open; optional 2-test strengthening). @tech-lead @manager to sequence the commits; @python-dev owns F2/F4 as part of TASK-276.
- [2026-07-02T10:08:06Z] Paul Reviewer:
  - Verdict: Approved. Re-reviewed the TASK-276 rewire (git diff 495fc95, read-only). _discussion._status_badge no longer calls Status(value); it resolves active_spec.status_badge(status_value) or the neutral _DEFAULT_BADGE ('⚪'), with spec=None falling back to bundled_spec() so the frozen migration runner is unaffected. The label-spacing regex is preserved. Spec is threaded, not globalized: self.spec at the service boundary (_refresh_head) and the pre-existing get_active_spec() at the CLI boundary (_subentity_pane_title_raw). No new reportPrivateUsage suppression (29 at HEAD, 29 now; the one in _subentity_pane_title_raw is pre-existing). AC#3 ruling (b) holds — _build_item_panel_rows still renders plain it.status, no top-level badge added. All four findings resolved (F1/F2/F4 Fixed, F3 waived). Targeted tests green: test_status_display_characterization.py + test_custom_status_badges.py + test_discussion.py = 51 passed; pyright + ruff clean on all touched files. TASK-276 is good to mark Done. @tech-lead @manager
- [2026-07-02T10:09:27Z] Paul Reviewer:
  - Verdict revised to ChangesRequested (correcting my earlier premature Approved). op-pierre reviewed F4's mid-loop resolution and it is not adequate — see F4 (reopened, Open) for the two required changes: (1) strip the 'FEAT-211 / TASK-276' sq IDs from the _enums.py docstring; (2) delete the dead STATUS_EMOJI dict from production and move its 9-glyph golden into the test layer, repointing test_workflow_spec.py and test_status_display_characterization.py.
  - 
  - Everything else in the review STANDS and re-verifies clean: the _status_badge crash fix is correct (spec-derived, '⚪' default, bundled fallback, no Status(value) parse); F1/F2 fixed (characterization golden byte-identical to 495fc95, custom-status tests in their own module); AC#3 (b) holds (no top-level badge; _build_item_panel_rows renders plain it.status); spec threaded, no new global; no new reportPrivateUsage suppression (29/29). Targeted tests green (51 passed).
  - 
  - TASK-276 is NOT Done until F4's follow-up fix lands and passes re-review. @tech-lead @python-dev @manager
- [2026-07-02T10:09:46Z] Catherine Manager:
  - F4 reopened beyond Paul's approval, per op-pierre: the 'keep STATUS_EMOJI + document it' resolution is not accepted. Required: (a) remove the ticket IDs (FEAT-211/TASK-276) from the _enums.py docstring — sq IDs must not appear in source; (b) delete the dead STATUS_EMOJI dict from production and relocate the 9-glyph golden reference into the test layer. Fix routed to python-dev; TASK-276 held InReview until verified.
- [2026-07-02T10:22:08Z] Catherine Manager:
  - F4 verified fixed: STATUS_EMOJI deleted from src (grep-clean), ticket IDs removed, the 9-glyph golden reference relocated to tests/_helpers.py::EXPECTED_BUILTIN_STATUS_BADGES with both test consumers repointed. Rendered-output golden (tests/goldens/) untouched and _EXPECTED_BADGES literals unchanged — built-in behavior byte-identical; 70 targeted tests green. TASK-276 → Done.
- [2026-07-03T09:18:40Z] Paul Reviewer:
  - Closing out: all findings resolved — F1 Fixed, F2 Fixed, F3 WontFix (deliberate, transitively guarded via shared spec.is_open), F4 Fixed (verified against commit 054af14). The review's substance landed with FEAT-211/EPIC-206 (both closed Done): the _status_badge crash is fixed spec-driven with a neutral default, the characterization gate is byte-identical to its HEAD baseline, custom-status acceptance tests are split into their own module, and the dead STATUS_EMOJI oracle is relocated to the test layer. Moving to Approved.
<!-- sq:discussion:end -->
