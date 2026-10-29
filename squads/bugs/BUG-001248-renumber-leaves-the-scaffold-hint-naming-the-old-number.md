---
id: BUG-1248
sequence_id: 1248
type: bug
title: Renumber leaves the scaffold hint naming the old number
status: Verified
author: qa
priority: low
severity: medium
refs:
- REV-1247
- MILE-1241:targets
created_at: '2026-10-29T17:11:35Z'
updated_at: '2026-10-29T20:40:36Z'
---
<!-- sq:body -->
## Summary

Both `sq repair --renumber` and `sq renumber` move an item to a new number but leave the scaffolded hint above the sub-entity region naming the old number. The command in the hint then addresses a different item, or none.

## Steps to reproduce (driven, dev tree, scratch squad)

1. `sq init`, then `sq create task 'Alpha task' --author manager` (TASK-2) and `sq task 2 add-subtask 'First sub'`.
2. Create BUG-3 and rename its file and frontmatter `id`/`sequence_id` to 2, so TASK-2 and BUG-2 share a number (a hand edit is the only way to arrange the collision).
3. Run `sq repair --renumber`. Output: TASK-2 becomes TASK-3, BUG-2 keeps 2.
4. Read `squads/tasks/TASK-000003-alpha-task.md`.

Separate pre-merge path: `sq create task 'Gamma'` (TASK-14), `sq renumber --from 14 --by 20` answers `TASK-14 -> TASK-34`; the file still holds the same hint.

## Expected

The hint names the item's current number: `sq task 3 add-subtask "<title>"; track with sq task 3 subtask <n> update ...`.

## Actual

```
_Add with `sq task 2 add-subtask "<title>"`; track with `sq task 2 subtask <n> update --status <Status>`._
```

in TASK-3 (collision case), and `sq task 14 ...` inside TASK-34 (renumber case). After the collision case, `sq task 2` addresses BUG-2, so following the hint acts on the wrong item. The id, `sequence_id`, filename and index are all correct; only the hint is stale. A new `add-subtask` on the moved item works and does not refresh the hint.

## Scope of the sweep

- Driven, stale: the hint line in a task (both commands, both renumber paths).
- Driven, not stale: the sub-entity table in `show` (rendered from frontmatter) and the sub-entity blocks and heads in the file (no item number in them).
- Driven, left alone by design: a discussion comment that quotes `sq task 2 show` is authored prose; it is not rewritten, which is expected.
- Inferred, not driven: other item types scaffold the same hint with their own verb (for example a feature's `add-story`), so the same stale number is expected there. The fix should cover every hint rendered from the item templates, not only the task one.

The renumber code must re-render that scaffold line (or the template should not carry the number at all) wherever it rewrites an item's id. Pre-existing; found in REV-1247 F11.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T19:11:29Z] `reviewer` Paul Reviewer:
  - Re-falsified at cc772bc0 for REV-1247 F11: driven on a scratch squad (repair --renumber moved TASK-22 to 23 and its hint now names 23), and with _rehint short-circuited in a scratch worktree the surface and regression cases go red, green once restored. Verification of the bug itself stays with @qa.
- [2026-10-29T20:40:36Z] `reviewer` Paul Reviewer:
  - Verified under REV-1247 (Approved at a56413b4).
<!-- sq:discussion:end -->
