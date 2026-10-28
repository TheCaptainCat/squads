---
id: BUG-1191
sequence_id: 1191
type: bug
title: repair silently drops one of two files sharing a number
status: Open
author: qa
severity: medium
refs:
- FEAT-1173
created_at: '2026-10-27T23:37:38Z'
updated_at: '2026-10-27T23:37:57Z'
---
<!-- sq:body -->
Found while writing the CLI surface tests (FEAT-1173). Reproduced on the release/0.17 dev tree.

## Setup
Scratch squad with TASK-21. Copy its file to `squads/bugs/BUG-000021-two.md`, edit the frontmatter to `id: BUG-21`, `type: bug`, `status: Open` (distinct ids, same number 21).

## Command
`sq repair`

## Observed
```
rebuilt index: 22 items, counter=22
```
Exit code 0. `sq list -a` then shows only `BUG-21 bug Open one`; TASK-21 is gone from the listing (the index is keyed by the number). Only `sq check` reports it: `error #21: 2 files carry number 21 under different ids (bugs/BUG-000021-two.md, tasks/TASK-000021-one.md); run sq repair --renumber ...` (exit 3).

## Expected
The FAQ (`sq docs faq`, "Handling ID collisions") says plain `sq repair` on the same ID in two files names the files and exits 1. The distinct-ids-same-number case is documented only for `--renumber`, but plain `repair` should treat it the same way: report the collision and exit 1 rather than silently dropping one file from the index with a clean exit, since the file exists on disk but is invisible to `list`.

## Severity
medium
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
