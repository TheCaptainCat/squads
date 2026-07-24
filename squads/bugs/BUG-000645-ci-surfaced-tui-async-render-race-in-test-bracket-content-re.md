---
id: BUG-645
sequence_id: 645
type: bug
title: CI-surfaced TUI async-render race in test_bracket_content_renders_safely.py
status: Verified
author: qa
refs:
- BUG-620
created_at: '2026-07-24T09:01:29Z'
updated_at: '2026-07-24T09:19:37Z'
---
<!-- sq:body -->
Symptom: CI's `test` job failed the release/0.12 PR on all 3 OS runners in
`tests/tui/test_bracket_content_renders_safely.py`:
- `test_a_sub_entity_body_with_brackets_renders_without_crashing` — `_BRACKETY in sub_view._markdown`
  asserted right after `pilot.pause()`, sometimes read back `''`.
- `test_a_search_snippet_with_brackets_renders_without_crashing` — `len(hits) == 1` asserted right
  after `pilot.press("enter")` + `pilot.pause()`, sometimes read back `0`.

Both passed reliably on a fast, uncontended local run — only a slow/loaded CI runner reproduced
them.

Root cause: the same class as BUG-620 — an assertion on post-action async state made right after
a single `pilot.pause()`, which only waits until the process *looks* CPU-idle rather than actually
awaiting the specific pending completion. Two distinct async hand-offs feed this:
- `Markdown.update()` offloads its parse to a thread-pool executor; under contention that thread
  can be scheduled late enough that `pause()` declares idle and returns first.
- `SearchScreen._run_search` is a `@work(exclusive=True)`-decorated, fire-and-forget worker
  (called, never awaited, from `_search()`) — its `ListView` population runs on its own schedule,
  independent of the message handler that triggered it.

BUG-620's fix (the `_wait_until` poll helper) was scoped too narrowly: it only touched
`tests/tui/test_browse_screen.py`, so `test_bracket_content_renders_safely.py` (same file's sub-entity-
body and search-snippet tests) and other racy sites elsewhere in `tests/tui/` were never covered.

Fix (test-only, `tests/tui/`, no `src/squads/_tui/` app code touched):
- Extracted the poll helper into a shared `tests/tui/_helpers.py::wait_until` (mirrors the existing
  `tests/_helpers.py` convention), imported via a package-relative `from ._helpers import wait_until`
  (the bare `_helpers` name collides with the top-level `tests/_helpers.py` once `tests/` is on
  `sys.path`).
- Fixed the two CI-failing tests plus every other site in `tests/tui/` asserting on post-action
  async state (Markdown `._markdown`/`.children`, ListView population, recorded search-spy calls)
  right after a single pause, by polling the real postcondition instead:
  - `tests/tui/test_bracket_content_renders_safely.py`: `test_a_sub_entity_body_with_brackets_renders_without_crashing`,
    `test_a_search_snippet_with_brackets_renders_without_crashing`, and
    `test_a_discussion_comment_with_brackets_renders_without_crashing` (same race, not yet failing
    in CI but same pattern).
  - `tests/tui/test_browse_screen.py`: lifted the local `_wait_until` into the shared helper;
    fixed `test_body_tab_renders_markdown_blocks_and_an_empty_state_for_a_blank_body`,
    `test_subentities_tab_shows_each_blocks_head_and_body_with_empty_states`,
    `test_discussion_tab_renders_markdown_ordered_comments_and_empty_state`.
  - `tests/tui/test_reader_screen.py`: `test_reader_screen_loads_the_item_and_pops_on_escape`.
  - `tests/tui/test_search_screen.py`: `test_submitting_a_query_lists_hits_with_id_type_title_and_snippets`,
    `test_a_query_with_no_matches_shows_a_clean_no_results_state`,
    `test_a_searching_state_is_shown_while_the_worker_runs`,
    `test_type_and_status_narrowing_are_forwarded_to_svc_search`,
    `test_selecting_a_hit_pushes_a_reader_screen_without_moving_browse_selection`.

No `sleep`-based masking anywhere — every wait polls a real, specific postcondition (the exact
content/count the test already asserted), so nothing verified is weakened. Sites that don't touch
async-offloaded state (`FilterScreen`, `_status_role_colour`, `_ui_command`, the `glance-header`
`Static` — set synchronously before any executor `await`) were left untouched; confirmed by reading
`src/squads/_tui/_filter.py`/`_reader.py`/`_search.py` for what's actually offloaded (only
`Markdown.update()`'s executor parse and `SearchScreen._run_search`'s `@work` fire-and-forget).

References BUG-620 (the original, narrower fix).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-24T09:19:37Z] Catherine Manager:
  - Manager verification: shared tests/tui/_helpers.py::wait_until (predicate + max_wait deadline + repeated pilot.pause(), raises on timeout — a real poll, no sleep) applied to the two CI-red bracket-render tests plus swept sites in test_browse_screen/reader_screen/search_screen. Full suite green on the fixed tree (0 failures, even under concurrent monitor load); 2/2 tui -n auto runs green. CI's OS matrix on the re-push is the authoritative confirmation. Verified.
<!-- sq:discussion:end -->
