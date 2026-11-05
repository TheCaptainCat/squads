---
id: BUG-1302
sequence_id: 1302
type: bug
title: Raw show --full --comments drops sub-entity comments
status: Verified
author: qa
refs:
- FEAT-1290
created_at: '2026-11-05T01:43:45Z'
updated_at: '2026-11-05T02:47:23Z'
priority: medium
severity: medium
---
<!-- sq:body -->
`show --raw --full --comments` omits the discussion of every sub-entity; the normal `show --full --comments` prints it. US7 says `--full` and `--comments` render raw too.

## Steps to Reproduce

On a scratch squad built with the dev build at commit 542beb09 (`/home/pchat/.cache/sq-qa-1290/fresh`):

```
sq create feature "F" --author op-quinn
sq feature 10 add-story "A story" -m "Story body"
sq feature 10 story 1 comment --as qa -m "story comment text"
sq feature 10 comment --as qa -m "feature comment"
sq feature 10 show --full --comments            # prints both comments
sq feature 10 show --raw --full --comments      # prints only "feature comment"
```

## Expected vs Actual

- **Expected:** the raw output carries the story's discussion ("story comment text"), as the panel output does under `=== US1 ... ===`.
- **Actual:** the raw output has the story body but no story discussion; "story comment text" appears nowhere in it. Exit 0, so a caller cannot tell comments were dropped.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-05T02:18:40Z] `python-dev` Elias Python:
  - Fixed: raw show with --full --comments now prints each sub-entity discussion (### Discussion under its section). Test breaks without the render change. Uncommitted.
- [2026-11-05T02:47:10Z] `reviewer` Paul Reviewer:
  - Verified at 307c1030 by the reviewer. On a scratch squad, `show --raw --full --comments` prints each sub-entity's own `### Discussion` with its comments, under that sub-entity's section, followed by the item's `## Discussion`. Without `--comments`, the sub-entity comments are left out. The new test covers this, and the default and override suites are green.
<!-- sq:discussion:end -->
