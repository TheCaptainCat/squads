---
id: BUG-1085
sequence_id: 1085
type: bug
title: update --assignee "" is a silent no-op
status: Open
parent: MILE-1051
author: qa
created_at: '2026-10-16T22:52:23Z'
updated_at: '2026-10-16T22:52:28Z'
---
<!-- sq:body -->
## Repro
Scratch squad, clean export of HEAD 0e6e52cf, and released 0.15.0 (same result).

    sq bug 21 update --assignee qa     -> updated BUG-21
    sq bug 21 update --assignee ""     -> updated BUG-21   (exit 0)
    sq bug 21 show                     -> assignee: qa     (unchanged)

Same with `assignee_present@error` selected on bug (override workflow.toml): after `update --status InProgress`, `update --assignee ""` prints "updated BUG-21" and the assignee stays qa, so the validator is never tripped. `update --assignee "" --status Fixed` also leaves the assignee.

Sub-entity: `sq task 22 subtask 1 update --assignee ""` -> `error: nothing to update (pass at least one field, e.g. --title/--status)` (exit 1); assignee stays qa. Not silent, but the message is wrong: a field was passed.

## Expected
An empty --assignee clears the assignee (or is refused with a clear message), and the output never says "updated" when nothing changed. The subtask verb should behave the same as the item verb.

## Actual
Empty string is treated as "not passed": item update reports success and changes nothing; subtask update says nothing to update. No other verb clears an assignee, so an assignee cannot be removed through the CLI.

## Impact
Docs follow the build: the clearing refusal in the assignee_present table cannot be driven. Found by the writer on TASK-1002.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
