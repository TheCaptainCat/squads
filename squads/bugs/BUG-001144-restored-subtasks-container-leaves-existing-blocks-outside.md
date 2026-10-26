---
id: BUG-1144
sequence_id: 1144
type: bug
title: Restored subtasks container leaves existing blocks outside
status: Verified
author: qa
priority: low
refs:
- TASK-1135
created_at: '2026-10-25T17:53:49Z'
updated_at: '2026-10-26T06:46:43Z'
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
- [2026-10-26T06:45:48Z] `qa` Mara Tester:
  - Verified on the dev build, original repro: fresh squad, TASK-2 with ST1, delete the sq:subtasks pair, `sq repair`, `subtask 1 body -m x`, `add-subtask second`.
    - Result: one `## Subtasks` heading, one container pair, ST1 and ST2 inside it, in order. `sq check` clean for the item.
    - Neighbours: (a) pair and heading both removed, two blocks, then body write and add-subtask s3 -> one heading, ST1..ST3 inside. (b) pair removed with stray prose between ST1 and ST2 -> `error: TASK-3: cannot restore the subtasks container, prose sits between its blocks -- restore the ... lines by hand`, rc 1, file byte-identical. (c) container removed together with its only block, then add-subtask -> one heading and one pair; ST1 is restored when it is next written (`subtask 1 body`), inside the pair. (d) stories container removed on a feature, add-story -> one `## User Stories`, US1 and US2 inside the pair. (e) a block moved outside an intact container -> new `sq check` warn `subtask block ST1 sits outside its 'subtasks' container`; a later add-subtask does not move it (check reports it).
    Moving to Verified.
<!-- sq:discussion:end -->
