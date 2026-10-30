---
id: BUG-993
sequence_id: 993
type: bug
title: check after a number clash blames a missing subtasks section
status: Verified
author: qa
refs:
- BUG-994
- MILE-1051:targets
created_at: '2026-10-11T20:18:02Z'
updated_at: '2026-10-25T17:52:36Z'
priority: medium
---
<!-- sq:body -->
## Reproduction

Driven on the released tool, squads 0.15.0 (`~/.local/bin/sq`), in scratch squads. Squad A has TASK-21 and a referrer TASK-22, no workflow override, and `sq check` is clean (control, exit 0). Then copy a valid `BUG-000021-from-branch-b.md` (created by `sq create bug` in a second squad) into `squads/bugs/`, so the index does not know about it, and run `sq check`:

```
error TASK-21: no 'subtasks' container section -- 'subtask' declares plural 'subtasks', so `sq task 21 add-subtask` cannot write here. Revert subentity_kinds.subtask.plural in the workflow override, or change it only while no task items exist
exit 3
```

`list -a` meanwhile shows only TASK-21, and `sq bug 21 show` exits 1 with "21 is TASK-21 (task), not a bug". After `sq repair` the message is gone.

## Expected versus actual

Expected: the error, if any, names the real cause (a second item file carrying number 21, or a stale index).
Actual: it blames a missing `subtasks` container and tells the operator to revert `subentity_kinds.subtask.plural` in a workflow override. No override exists in the squad, and TASK-21's file is intact. The remedy sends the operator after a setting that is not there.

## Bounded

Reproduced once, task plus bug sharing number 21, index not yet rebuilt. The clean control is the same squad before the copy. Not driven: other type pairs, or whether the message appears for a task without a number clash.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T17:52:09Z] `qa` Mara Tester:
  - Verified on release/0.17 HEAD 68e96aea (dev build, scratch squads). Task TASK-2 indexed plus a valid BUG-2 file copied in: check exits 3 with only "2 files carry number 2 under different ids (bugs/..., tasks/...); run sq repair --renumber"; no subtasks-container message. Reverse (BUG indexed, TASK file copied) gives the same single error. Control before the copy exits 0.
<!-- sq:discussion:end -->
