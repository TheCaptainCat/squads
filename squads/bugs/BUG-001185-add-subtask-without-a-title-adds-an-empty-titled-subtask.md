---
id: BUG-1185
sequence_id: 1185
type: bug
title: add-subtask without a title adds an empty-titled subtask
status: Open
author: qa
severity: medium
refs:
- FEAT-1173
created_at: '2026-10-27T23:37:32Z'
updated_at: '2026-10-27T23:37:51Z'
---
<!-- sq:body -->
Found while writing the CLI surface tests (FEAT-1173). Reproduced on the release/0.17 dev tree.

## Command
`sq task 21 add-subtask` (no TITLE argument)

## Observed
```
added ST1 to TASK-21
  set its body:  sq task 21 subtask ST1 body -m "…"  (or --file body.md / --file -)
```
Exit code 0. `sq task 21 show --full` then lists `ST1  Todo  <empty title>`.

## Expected
Typer should refuse the missing required argument (exit 2), or the service should refuse an empty title, as it does for other required text. A subtask with an empty title is unusable in listings.

## Severity
medium
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
