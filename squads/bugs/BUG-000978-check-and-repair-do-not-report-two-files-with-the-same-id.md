---
id: BUG-978
sequence_id: 978
type: bug
title: check and repair do not report two files with the same id
status: Verified
author: qa
priority: medium
severity: medium
refs:
- REV-975:addresses
- MILE-934:targets
description: check and repair stay silent when two files carry one id
created_at: '2026-09-29T14:25:57Z'
updated_at: '2026-10-09T15:38:07Z'
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
- [2026-09-29T15:17:37Z] `python-dev` Elias Python:
  - Fixed: one shared detector; check errors, repair refuses, --renumber renumbers different slugs and lists references, show warns, writes refuse.
- [2026-09-29T16:23:17Z] `python-dev` Elias Python:
  - Review round 3: one identity rule for detector and guard, renumber keeps the indexed file, every write checks before touching a file.
- [2026-09-29T16:52:00Z] `python-dev` Elias Python:
  - Review round 4: the write guard is proportional to one item; scan state is passed, not kept.
- [2026-10-09T15:38:03Z] `qa` Mara Tester:
  - Verified at HEAD 7cd45323. Driven (real CLI, dev build, one scratch squad per row, referrers present: a `refs` edge, a `parent` edge, a body mention, a comment mention and a subtask body all pointing at TASK-21). Every duplicate row: `check` exit 3 naming every file; plain `repair` exit 1 naming every file and leaving all markdown byte-identical; `list -a` shows one row; `show` exit 0 with a stderr warning naming the files; `comment` and `update` on the id exit 1 ("refusing to write") with no file changed.
    
    Rows:
    - identical copy, same folder (`alpha-copy`): as above; `repair --renumber` exit 1, refuses, nothing renamed.
    - skill, same id (`sq-task-copy`): as above, including `skill 19 status` refusing (exit 1); renumber refuses.
    - same id, different slug and title: as above; `repair --renumber` exit 1 (references exist) listing the kept file (the indexed one), the renumbered file with its new id/path, and one line per reference (body, refs, comment, parent); only the renumbered file changed on disk, no reference rewritten; then check exit 0, repair exit 0 (stable). With no referrers: exit 0, "no references".
    - same id and same file name in another type folder (`bugs/TASK-...`): as above; renumber refuses (exit 1).
    - copy under another type prefix, same id (`bugs/BUG-000021-alpha.md` carrying id TASK-21): as above; renumber refuses.
    - padded vs unpadded id spelling (`id: TASK-021`; also `TASK-21-alpha.md` name with differing content): detected as one id; renumber refuses when the slug matches or the file sits outside its folder, renumbers when the slugs differ.
    - three files, all slugs different: renumber keeps one, renumbers two with consecutive new numbers, lists references, exit 1; check/repair clean afterwards.
    - file whose slug sorts first (`aaa`) while the index points at `alpha`: renumber keeps the indexed `alpha`, not the first path.
    - no previous index: repair leaves the id out of the index and exits 1.
    - distinct ids sharing a number (TASK-21 and a BUG-21 file): behaves as before (no duplicate-id error), as the task requires.
    
    Targeted tests: 114 passed (4 files, run once).
    Observations, not defects against the stated acceptance: (1) renumber keeps the file the index points at, not "first path" as the ST6 text says; the dev's round-3 comment says this is deliberate. (2) A group of three where two files are byte-identical but have different file-name slugs (`other`, `other-copy`) is renumbered, because slugs differ and the group is not all-identical; the ticket text says to refuse any group with two equal slugs, and these two differ by name. (3) When a stripped managed skill is renamed and sync writes a fresh canonical file, `sq check` on the renamed file only says "file has no id in frontmatter", with no remedy; deleting it fixes it.
    Not covered: reversed filesystem scan order (not drivable from the CLI), a subtask field that references the id in a sub-entity frontmatter field.
<!-- sq:discussion:end -->
