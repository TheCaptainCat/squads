---
id: BUG-994
sequence_id: 994
type: bug
title: check is clean when two ids share one number
status: Verified
author: qa
priority: medium
refs:
- MILE-934:targets
- BUG-993
created_at: '2026-10-11T20:18:04Z'
updated_at: '2026-10-16T19:08:31Z'
---
<!-- sq:body -->
## Reproduction

Driven on the released tool, squads 0.15.0 (`~/.local/bin/sq`), in scratch squads. Squad B: `sq init`, `sq create bug "from branch b"` gives BUG-21. Squad A: `sq init`, `sq create task "from branch a"` gives TASK-21, plus a referrer task with a `ref add TASK-21`. Copy `BUG-000021-from-branch-b.md` into A's `squads/bugs/` (the merged-tree state), then:

```
sq repair                # exit 0, "rebuilt index: 22 items"
sq check                 # exit 0, "no issues"
sq list -a               # BUG-21 and the referrer; TASK-21 is not listed
sq task 21 show          # exit 1: error: 21 is BUG-21 (bug), not a task
sq bug 21 show           # exit 0
sq repair --renumber     # exit 0; TASK-21 becomes TASK-23, the referrer's ref follows; check clean
```

## Expected versus actual

Expected: a sequence number is unique across the squad, so `sq check` reports that two items carry number 21 and names both files.
Actual: `check` is clean and one of the two items has vanished from `list` and `show`. Which one is visible depends on the scan, not on anything the operator did. Only `repair --renumber` resolves it, and an operator has no signal to run it. The docs tell people to spot the state by the number rather than by an error, so a squad can sit in it unnoticed.

## Bounded

Two distinct ids (task and bug), valid files, one copied across. `repair --renumber` rewrites the referrer's `refs` and body mention, as the FAQ describes. Not driven: three-way number collisions, or other type pairs.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T18:00:23Z] Elias Python:
  - Fixed in the commit "Made check report a number carried under different ids": check now errors on one number under different ids, naming every file, with the repair --renumber remedy. Table over task+bug, bug+task, task+feature, three-way plus a clean case; falsification 4 of 4 fail without the check.
- [2026-10-16T18:23:28Z] Elias Python:
  - Commit 05f2328f on branch worktree-agent-a2f892de06784925e.
- [2026-10-16T19:08:31Z] Catherine Manager:
  - Verified: fix approved on REV-1067 and merged into release/0.16 at 977730ec; full suite 11471 passed, 0 failed.
<!-- sq:discussion:end -->
