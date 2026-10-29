---
id: BUG-1184
sequence_id: 1184
type: bug
title: ref rm reports success for a ref the item lacks
status: Open
author: qa
priority: low
severity: low
refs:
- FEAT-1173
- MILE-1241:targets
created_at: '2026-10-27T23:37:31Z'
updated_at: '2026-10-29T16:31:24Z'
---
<!-- sq:body -->
Found while writing the CLI surface tests (FEAT-1173). Reproduced on the release/0.17 dev tree.

## Command and input
Scratch squad with TASK-21 and TASK-22; TASK-21 carries no ref to TASK-22.
`sq task 21 ref rm TASK-22`
`sq skill squads ref rm TASK-22` (same, from a skill that carries no such ref)

## Observed
```
removed TASK-21 → TASK-22
```
Exit code 0 (and `removed SKILL-20 → TASK-22`, exit 0, for the skill).

## Expected
A refusal (exit 1) such as "TASK-21 has no ref to TASK-22", since nothing was removed. The success line is false.

## Code
`src/squads/_cli/_items.py` `ref_rm` prints unconditionally after `svc.rm_ref(...)` (src/squads/_services/_refs.py `rm_ref`), which does not raise when the edge is absent.

## Severity
low
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
