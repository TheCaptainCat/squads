---
id: BUG-620
sequence_id: 620
type: bug
title: Flaky TUI scroll test races reader async load
status: Verified
author: qa
created_at: '2026-07-22T20:28:06Z'
updated_at: '2026-07-22T20:35:53Z'
---
<!-- sq:body -->
Symptom: tests/tui/test_browse_screen.py::test_body_tab_scrolls_to_reach_content_below_the_fold intermittently failed under pytest -n auto (parallel), always passed in isolation.

Root cause: selecting a tree node drives Tree.NodeHighlighted -> BrowseScreen.on_tree_node_highlighted -> ReaderPanel.load(), which awaits Markdown.update() for the body/sub-entities/discussion views. Markdown.update() hands its parse off to a thread-pool executor (run_in_executor). Textual's Pilot.pause() (no delay) returns once the process merely *looks* CPU-idle (comparing wall-clock vs process CPU time) -- under machine-wide contention (many parallel xdist workers), that executor thread can be scheduled late enough that pause() declares idle and returns before the reader's async load chain has actually finished mounting content. The test then asserted on VerticalScroll#body-scroll.max_scroll_y (and later scroll_y) before the layout had settled, so max_scroll_y read back as 0 or scroll_y hadn't reached max_scroll_y yet.

Same root cause reproduced (under synthetic CPU-contention stress) in test_selecting_a_node_loads_its_detail_and_reselection_refreshes_it in the same file -- single pilot.pause() after setting tree.cursor_line, then an immediate assertion on body._markdown.

Fix (test-only, tests/tui/test_browse_screen.py): added a _wait_until(pilot, predicate, timeout=5.0) poll helper that repeats pilot.pause() until the real postcondition holds (max_scroll_y > 0; scroll_y == max_scroll_y; body._markdown contains the expected text) instead of trusting a single pause. This is a deterministic, condition-based wait -- no fixed sleep, no weakening of what the test verifies. No src/squads/_tui app code changed; this is purely a test-timing fix.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T20:35:13Z] Mara Tester:
  - Verified: 20/20 clean runs of 'pytest tests/tui -q -n auto' under synthetic heavy CPU contention (20-28 competing busy processes on a 14-core box) -- the same conditions that reliably reproduced both races before the fix (0/many clean previously). Also confirmed 0 stress processes remain and only tests/tui/test_browse_screen.py changed (no src/squads/_tui/ app code touched). pyright/ruff check/ruff format clean on the touched file.
- [2026-07-22T20:35:53Z] Catherine Manager:
  - Manager verification: _wait_until polls the real postcondition (max_wait 5s) rather than trusting a single pilot.pause() — the correct fix for the executor-thread race; test-only, no app change. Ran tests/tui -n auto 3x, all green. Verified.
<!-- sq:discussion:end -->
