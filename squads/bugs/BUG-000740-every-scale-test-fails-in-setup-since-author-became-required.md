---
id: BUG-740
sequence_id: 740
type: bug
title: Every scale test fails in setup since author became required
status: Verified
author: qa
description: tests/test_scale.py has been red on release/0.13 since 2026-07-31 and
  is invisible because the slow tests are skipped by default
created_at: '2026-08-06T19:51:56Z'
updated_at: '2026-08-15T13:01:59Z'
---
<!-- sq:body -->
All five tests in tests/test_scale.py fail in their own setup with `squads._errors.SquadsError: author is required: the actor's slug`, raised from _services/_base.py. The fixture builds its corpus without passing an author.

Driven: reproduced at HEAD and independently at 59fd0eb, which predates the current fix waves, so this is not caused by them. Traced to c9cc1b4 (2026-07-31, "Required an explicit actor and reported an unusable index cleanly"), which made the author mandatory without updating the scale fixture. `git branch --contains` puts that commit on release/0.13 only.

Failing: test_scale_list_completes_within_bound, test_scale_search_completes_within_bound, test_scale_repair_completes_within_bound, test_scale_cli_list_completes_within_bound, test_scale_cli_tree_completes_within_bound.

The fix is to give the fixture an explicit author. The reason it matters more than a fixture edit: these tests are skipped by default via the conftest hook, so a bare `uv run pytest` has reported green for six days over a suite that cannot run at all. Every scale bound this release claims to hold is currently unmeasured -- including the search bound, on a release that just changed how search reads the corpus. Whatever pins this should make the breakage visible without requiring someone to remember --run-slow.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-06T19:52:22Z] Catherine Manager:
  - Found while running the slow suite as the gate for TASK-737 ST1. The ST1 dev flagged one failing scale test as pre-existing; it is five, and his pre-existing claim is correct.
- [2026-08-06T20:15:14Z] Elias Python:
  - Fixed: tests/test_scale.py's create() calls now pass author=DEFAULT_TEST_AUTHOR (the shared tests/_helpers.py constant, "manager", already registered by roles_spec="minimal"). All 5 scale tests pass with --run-slow.
  - Added a fast, unmarked canary in the same module (test_scale_fixture_builds_without_error) that runs the identical setup path at 1 item/type -- ~0.05s, always collected by a bare uv run pytest, no --run-slow needed. Falsified it first (removed the author kwargs, watched it fail with the exact original SquadsError, restored) before trusting it.
  - Generalised the pattern as a repo-wide guard: tests/meta/test_slow_marked_modules_always_keep_a_fast_canary.py AST-scans every tests/**/test_*.py module and fails if every test in it is @pytest.mark.slow (i.e. the module can go fully dark to the default run). Also falsified (renamed the canary so it wasn't collected, watched the guard catch it, restored).
  - Measured what the bounds now actually check, at the real ~1001-item corpus: list_items 0.021s (bound 5s), search 0.337s (bound 5s, correctly destructures the new (results, unreadable) tuple -- that adaptation already existed pre-fix, it just never ran), repair 0.662s (bound 10s), sq list --all 0.445s (bound 10s), sq tree --all 0.140s / --json 0.093s (bound 10s each). All comfortably within bound; none of the five needed retuning -- the search bound in particular is measuring the current per-file-degrading search correctly, not a stale shape.
  - Confirmed CI never ran these either: .github/workflows/test.yml's test job runs bare 'uv run pytest' (no --run-slow), so the scale suite was equally invisible there -- the new canary now runs in that same job by default.
  - Body's claims all held up against the code/history (c9cc1b4 traced correctly, 6-day-invisible window correct, search-shape caveat correct) -- no correction needed.
  - Files: tests/test_scale.py, tests/meta/test_slow_marked_modules_always_keep_a_fast_canary.py. sq check clean.
- [2026-08-06T20:28:14Z] Catherine Manager:
  - Retrying a comment that failed earlier when sq was briefly unrunnable mid-edit by another agent. CI never runs --run-slow at all (driven -- no occurrence anywhere in .github/), so the scale BOUNDS have never been enforced in CI, as distinct from the six-day setup rot this bug covers. The canary closes the rot, which was the real failure mode. Enforcing the bounds costs roughly two extra minutes across a three-OS matrix -- a cost decision for op-pierre rather than a correctness one. Measured values are far under bound (search 0.337s against 5s, repair 0.662s against 10s), so nothing is at risk today; the question is whether we want to know when that changes.
- [2026-08-15T13:01:58Z] Catherine Manager:
  - Verified by driving, not by reading the fix. tests/test_scale.py --run-slow: 6 passed (the five originals plus the new canary). Bare pytest on the same module: 1 passed, 5 skipped -- so the canary genuinely runs in the default fast suite while the slow bounds still skip, which is the property that was missing and the reason this rotted unseen for six days. tests/meta/test_slow_marked_modules_always_keep_a_fast_canary.py: 5 passed, so the shape cannot recur in another module.
  - Also confirmed in the authoritative gate: the full suite with --run-slow is 3449 passed, 1 skipped, 0 failed at 2fed334, with the scale bounds measuring for the first time since 2026-07-31.
<!-- sq:discussion:end -->
