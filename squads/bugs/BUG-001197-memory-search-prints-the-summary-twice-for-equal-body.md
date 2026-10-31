---
id: BUG-1197
sequence_id: 1197
type: bug
title: memory search prints the summary twice for equal body
status: Verified
author: qa
refs:
- FEAT-1173
- MILE-1241:targets
created_at: '2026-10-27T23:37:44Z'
updated_at: '2026-10-29T20:40:30Z'
priority: low
severity: low
---
<!-- sq:body -->
Found while writing the CLI surface tests (FEAT-1173). Reproduced on the release/0.17 dev tree. Cosmetic.

## Commands
`sq memory qa add "widget quirk"` (the body defaults to the summary), then `sq memory qa search widget`.

## Observed
```
widget-quirk  widget quirk
    widget quirk
    widget quirk
```
The summary appears on the slug line, then twice more as hit lines (one for the summary match, one for the body match). With a distinct body the hit shows once, as intended.

## Expected
Show a matching line once when the body line equals the summary line (or skip the body line that repeats the summary).

## Severity
low
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T20:40:29Z] `reviewer` Paul Reviewer:
  - Verified under REV-1247 (Approved at a56413b4).
<!-- sq:discussion:end -->
