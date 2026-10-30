---
id: BUG-987
sequence_id: 987
type: bug
title: 'Renamed stripped managed skill file: check gives no remedy'
status: Verified
author: qa
refs:
- MILE-1051:targets
created_at: '2026-10-09T20:19:45Z'
updated_at: '2026-10-25T17:52:43Z'
priority: low
---
<!-- sq:body -->
## Reproduction

Scratch squad (`sq init --default-names --backend claude_code`, dev build at HEAD d07b0e50):

```
mv squads/agents/skills/SKILL-000019-sq-task.md squads/agents/skills/SKILL-000019-sq-task-renamed.md
# strip the frontmatter block from the renamed file (body kept)
sq sync      # exit 0, "synced managed files to this squads version"; writes a fresh SKILL-000019-sq-task.md
sq check     # exit 3: error SKILL-000019-sq-task-renamed.md: file has no `id` in frontmatter
sq repair    # exit 1: ... file has no `id` in frontmatter -- its previous index entry, if any, was carried forward as-is; fix the file and repair again
sq sync      # exit 0, no change
sq check     # exit 3, same line
sq skill 19 regen   # exit 0, no change to the stray file; check still exit 3
```

The same shape with the stripped file left at its canonical name is recovered by `sq sync` and its check message says "run `sq sync`". Here, after the rename, `sq sync` has already written a fresh canonical file with full frontmatter, so the stray file now only duplicates a skill that is healthy.

## Expected versus actual

Expected: the message for the stray file tells the operator what state it is in and what to do about it.
Actual: `check` says only that the file has no `id`. `repair` says "fix the file and repair again", and no `sq` command can put frontmatter on that file. `sync` reports success and `check` stays at exit 3 forever. From the output alone an operator cannot tell that the skill itself is fine, that a second file carrying the same skill exists, or that the stray file has to be deleted (deleting it makes check and repair clean, driven). It reads as a permanently broken skill.

## Bounded

Driven on the `sq-task` skill only, one pass, frontmatter stripped. With the frontmatter left intact instead, `sync` warns and `check` names both files, so that shape is fine. Not driven: the `squads` system skill, other rename suffixes, or a user-authored skill.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T17:52:13Z] `qa` Mara Tester:
  - Verified on release/0.17 HEAD 68e96aea. Renamed+stripped sq-task skill after sync: check says "stray copy of managed skill sq-task, healthy in SKILL-000019-sq-task.md; delete this file"; deleting it makes check exit 0. Renamed+stripped with no canonical file: "no healthy file holds managed skill sq-bug; delete this file and run sq sync to write it"; after both steps check is clean. User-authored stripped skill gets no managed-skill remedy.
<!-- sq:discussion:end -->
