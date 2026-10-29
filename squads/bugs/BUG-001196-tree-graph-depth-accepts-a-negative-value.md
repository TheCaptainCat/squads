---
id: BUG-1196
sequence_id: 1196
type: bug
title: tree/graph --depth accepts a negative value
status: Fixed
author: qa
priority: low
severity: low
refs:
- FEAT-1173
- MILE-1241:targets
created_at: '2026-10-27T23:37:43Z'
updated_at: '2026-10-29T16:48:12Z'
---
<!-- sq:body -->
Found while writing the CLI surface tests (FEAT-1173). Reproduced on the release/0.17 dev tree.

## Commands and observed
`sq tree --depth -1`, `sq tree --depth -5` exit 0 and print the tree; `sq graph 21 --depth -1` exits 0 and prints only `TASK-21 Draft`. No message.

## Expected
`--depth` is documented as "How many levels below the root to show; 0 shows only the root". A negative value has no meaning and should be refused (exit 1 or a Typer `min=0` bound), not silently treated as unlimited (tree) or as 0 (graph).

## Code
Both commands use `common.depth_option` in `src/squads/_cli/_common.py`, an unbounded `typer.Option`; adding `min=0` there fixes both.

## Severity
low
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
