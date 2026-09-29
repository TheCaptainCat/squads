---
id: BUG-978
sequence_id: 978
type: bug
title: check and repair do not report two files with the same id
status: Fixed
author: qa
priority: medium
severity: medium
refs:
- REV-975:addresses
- MILE-934:targets
description: check and repair stay silent when two files carry one id
created_at: '2026-09-29T14:25:57Z'
updated_at: '2026-09-29T16:52:00Z'
---
<!-- sq:body -->
## Summary

Two item files carrying the same `id` are never reported. `sq check` prints "no issues" and exits 0, `sq repair` rebuilds the index and exits 0, and `sq list -a` shows one row. The other file is silently shadowed. Driven on the released squads 0.15.0.

## Reproduction

Scratch squad (`sq init --default-names --backend claude_code`, three items created), one copy of a file per shape, then run `sq check`, `sq repair`, `sq list -a` and `sq task 21 show` in each.

| Shape | Setup | check | repair | list -a / show |
|---|---|---|---|---|
| Work item, same id, same slug | `cp TASK-000021-alpha.md TASK-000021-alpha-copy.md` | "no issues", exit 0 | rebuilt index, exit 0, both files kept | one TASK-21 row (alpha) |
| Skill, same id | `cp SKILL-000019-sq-task.md SKILL-000019-sq-task-copy.md` | "no issues", exit 0 | exit 0, both files kept | not separately listed |
| Same id, different slug | copy of TASK-21 named `TASK-000021-other.md` with `slug: other`, `title: other` | "no issues", exit 0 | exit 0, both files kept | one TASK-21 row, titled "other": the copy shadows the original |
| Same id, different type folder | `cp tasks/TASK-000021-alpha.md bugs/TASK-000021-alpha.md` | "no issues", exit 0 | exit 0, both files kept | one TASK-21 row (alpha) |

## Expected

`sq check` reports an error naming every file that carries the same `id`. `sq repair` names the collision and does not silently pick one file.

## Impact

Silent identity loss: which copy wins is decided by scan order, so edits and reads can land on the wrong file. It is the precondition for REV-975 F3, where the restamp turns a reported state into a silent duplicate id.

## Not tested

Status transitions or writes against a duplicated item, and which file wins when the two differ in shape 1 (the copies were identical).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-29T15:17:37Z] Elias Python:
  - Fixed: one shared detector; check errors, repair refuses, --renumber renumbers different slugs and lists references, show warns, writes refuse.
- [2026-09-29T16:23:17Z] Elias Python:
  - Review round 3: one identity rule for detector and guard, renumber keeps the indexed file, every write checks before touching a file.
- [2026-09-29T16:52:00Z] Elias Python:
  - Review round 4: the write guard is proportional to one item; scan state is passed, not kept.
<!-- sq:discussion:end -->
