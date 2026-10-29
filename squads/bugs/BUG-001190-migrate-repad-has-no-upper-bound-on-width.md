---
id: BUG-1190
sequence_id: 1190
type: bug
title: migrate repad has no upper bound on WIDTH
status: Fixed
author: qa
priority: medium
severity: medium
refs:
- FEAT-1173
- MILE-1241:targets
created_at: '2026-10-27T23:37:37Z'
updated_at: '2026-10-29T16:51:02Z'
---
<!-- sq:body -->
Found while writing the CLI surface tests (FEAT-1173). Reproduced on the release/0.17 dev tree.

## Commands and observed
- `sq migrate repad 99` on a 23-file squad: `repad done: padding 6 → 99; 23 file(s) renamed; index rebuilt`, exit 0. The change is one-way (`--help`: "the padding cannot be narrowed again"; `repad 0` then refuses as narrowing), so the squad is stuck with 99-digit filenames.
- `sq migrate repad 300` in a fresh squad: unhandled traceback ending `OSError: [Errno 36] File name too long`, exit 1 (the check afterwards is clean, the files kept their names).

## Expected
A sane upper bound on WIDTH (the filename limit is 255 bytes) refused up front with a `SquadsError` before anything is renamed. The new width cannot be undone, so accepting an absurd one is worse than a typical missing validation.

## Note
`migrate rename-status task Nope Draft` (unknown OLD status) exiting 0 with `0 item(s) renamed` was considered and left alone: renaming a status that is no longer in the lifecycle is the purpose of that verb, and the output states the count.

## Severity
medium
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
