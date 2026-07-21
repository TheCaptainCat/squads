---
id: BUG-522
sequence_id: 522
type: bug
title: 'sq ui reader panel: body/sub-entities/discussion tabs don''t scroll on overflow'
status: Fixed
author: op-pierre
priority: high
refs:
- FEAT-514
description: Reader tab content taller than the pane clips with no way to scroll
created_at: '2026-07-21T11:43:25Z'
updated_at: '2026-07-21T12:00:29Z'
---
<!-- sq:body -->
**Repro.** Open `sq ui`, select an item whose body (or sub-entities/discussion) is taller than the reader pane. The content is clipped at the bottom with no way to scroll down.

**Expected.** Each reader tab scrolls (keyboard + scrollbar) to reach content below the fold.

**Likely cause.** The reader panel puts bare `Markdown` / `Static` widgets directly in the `TabPane`s; those don't scroll on their own in Textual, so overflowing content just clips. Fix direction: give each tab a scroll container (e.g. wrap the body/sub-entities/discussion views in a vertical-scroll container, or use `MarkdownViewer` for the body), and cover it with a Pilot test that asserts an over-tall panel is scrollable.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T11:48:52Z] Mara Tester:
  - Independently reproduced during EPIC-28 verification: TabbedContent/TabPane both default to height:auto (Textual's own DEFAULT_CSS) and none of the three tab views are wrapped in a scroll container, so an over-tall Markdown/Static grows its region unbounded; Screen.max_scroll_y stays 0 and no keyboard/scrollbar path reaches the clipped tail. Confirmed via a headless Pilot probe with a 200-paragraph body (deleted after use, not part of the shipped suite).
- [2026-07-21T12:00:29Z] Elias Python:
  - Fixed: each reader tab's view is wrapped in a VerticalScroll (body-scroll/sub-scroll/disc-scroll), plus ReaderPanel CSS overrides TabbedContent/TabPane from height:auto to 1fr so the scroll container actually gets bounded space to scroll within.
  - Verified: new Pilot test mounts a 200-paragraph body and asserts max_scroll_y > 0 and that the 'end' key scrolls to the tail (scroll_y == max_scroll_y).
<!-- sq:discussion:end -->
