---
id: BUG-1200
sequence_id: 1200
type: bug
title: 'sq import: unknown op error has stray colon and pydantic wording'
status: Verified
author: qa
priority: low
severity: low
refs:
- FEAT-1173
- MILE-1241:targets
created_at: '2026-10-28T00:28:17Z'
updated_at: '2026-10-29T20:40:32Z'
---
<!-- sq:body -->
## Defect

`sq import` reports an event with an unknown `op` as `line 2: : Input tag 'nope' ...`. The message starts with a stray `: ` and then leaks pydantic's raw wording instead of naming the problem in squads' own words.

## Reproduce

Scratch squad from `sq init --default-names`, file `ev.jsonl`:

```
{"op":"create","type":"task","title":"ok"}
{"op":"nope"}
```

Command: `sq -C <scratch> import ev.jsonl`

Observed (exit 1):

```
line 1: no actor: missing 'as'
line 2: : Input tag 'nope' found using 'op' does not match any of the expected tags: 'create', 'status', 'body', 'comment', 'ref', 'add-sub', 'add-story', 'add-subtask', 'add-finding', 'sub-status', 'sub-body', 'assign', 'update'
2 issue(s) found — nothing written.
```

(Line 1 is an unrelated missing `as` in my input; line 2 is the defect.)

## Expected

A clean message with no stray separator, in squads' own words, naming the unknown op and the valid ones, for example `line 2: unknown op 'nope'; valid ops: create, status, body, ...`.

## Cause

`src/squads/_services/_import_model.py` (around line 365):

```
loc = ".".join(str(p) for p in first["loc"])
issues.append(ImportIssue(line=line_no, message=f"{loc}: {first['msg']}"))
```

For a tag-discriminator error pydantic's `loc` is empty, so the message begins with `: `, and `msg` is pydantic's phrasing. Fix: omit the separator when `loc` is empty, and special-case the `union_tag_invalid` error type to build the message from the adapter's valid tags.

Found by REV-1198 finding 18; the CLI test `test_a_refused_line_leaves_the_valid_events_before_it_unapplied` currently pins the buggy line and must be updated with the fix.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T20:40:32Z] `reviewer` Paul Reviewer:
  - Verified under REV-1247 (Approved at a56413b4).
<!-- sq:discussion:end -->
