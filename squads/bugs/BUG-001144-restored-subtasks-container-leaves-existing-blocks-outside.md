---
id: BUG-1144
sequence_id: 1144
type: bug
title: Restored subtasks container leaves existing blocks outside
status: Open
author: qa
priority: low
refs:
- TASK-1135
created_at: '2026-10-25T17:53:49Z'
updated_at: '2026-10-25T17:53:49Z'
---
<!-- sq:body -->
## Reproduction

Dev build at release/0.17 HEAD 68e96aea, fresh scratch squad (`sq init --backend none --roles minimal --default-names`):

1. `sq create task t --author manager` (TASK-2), then `sq task 2 add-subtask st`.
2. Delete the two lines for the container pair (tags `sq:subtasks` and `sq:subtasks:end`) from the task file, leaving the ST1 block, then `sq repair`.
3. `sq task 2 subtask 1 body -m x`.
4. Read the file: the ST1 block still sits above a new, empty `## Subtasks` heading with a fresh `sq:subtasks` pair appended near the end of the file.
5. `sq task 2 add-subtask second`: ST2 goes inside the new container, ST1 stays outside it.

## Expected

The restored container wraps the existing sub-entity blocks (or the write refuses with one error line), so every declared sub-entity block sits inside its container. One `## Subtasks` heading.

## Actual

The write succeeds. The existing block stays outside the new container, and the file ends up with a duplicate `## Subtasks` heading. `sq check` reports no issue, and `sq task 2 show` lists both subtasks. Found while verifying BUG-1022 (TASK-1135 restores missing regions on write).

## Bounded

Driven once, on the subtask kind with the container pair removed by hand. Not driven: story or finding containers, or a container removed together with its block.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
