---
id: BUG-1186
sequence_id: 1186
type: bug
title: subtask comment on a missing subtask leaks internal error
status: Verified
author: qa
refs:
- FEAT-1173
- MILE-1241:targets
created_at: '2026-10-27T23:37:33Z'
updated_at: '2026-10-29T20:40:08Z'
priority: low
severity: low
---
<!-- sq:body -->
Found while writing the CLI surface tests (FEAT-1173). Reproduced on the release/0.17 dev tree.

## Command
`sq task 21 subtask 9 comment --as qa -m x` (TASK-21 has only ST1). `subtask ST9` behaves the same.

## Observed
```
error: no discussion section 'subtask:ST9:discussion' in TASK-21 (was it scaffolded?)
```
Exit code 1.

## Expected
The message the sibling verbs give: `sq task 21 subtask 9 body -m x` prints `error: no subtask ST9 in TASK-21`. The comment path leaks the internal marker name and a "was it scaffolded?" hint for what is a user typo.

## Severity
low
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T20:40:08Z] `reviewer` Paul Reviewer:
  - Verified under REV-1247 (Approved at a56413b4).
<!-- sq:discussion:end -->
