---
id: BUG-1195
sequence_id: 1195
type: bug
title: reflog --op accepts an unknown operation
status: Fixed
author: qa
priority: low
severity: low
refs:
- FEAT-1173
- MILE-1241:targets
created_at: '2026-10-27T23:37:42Z'
updated_at: '2026-10-29T16:48:11Z'
---
<!-- sq:body -->
Found while writing the CLI surface tests (FEAT-1173). Reproduced on the release/0.17 dev tree.

## Command
`sq reflog --op ghost`

## Observed
`no reflog entries`, exit 0. The `--op` help lists the valid operations (`REFLOG_OPS`).

## Expected
Refuse an operation not in `REFLOG_OPS` (exit 1, listing the valid ones); an empty result for a typo is indistinguishable from a quiet log.

## Code
`src/squads/_cli/_main.py` `reflog`, `--op` option (about line 1220).

## Severity
low
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
