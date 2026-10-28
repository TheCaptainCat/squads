---
id: BUG-1193
sequence_id: 1193
type: bug
title: list/tree --sort accepts an unknown badge field
status: Open
author: qa
severity: low
refs:
- FEAT-1173
created_at: '2026-10-27T23:37:40Z'
updated_at: '2026-10-27T23:37:59Z'
---
<!-- sq:body -->
Found while writing the CLI surface tests (FEAT-1173). Reproduced on the release/0.17 dev tree.

## Commands
`sq list --sort ghost`, `sq tree --sort ghost`

## Observed
Both exit 0 and print the usual listing in default order; no message. (`--sort priority` sorts as documented.)

## Expected
`--sort` takes "an ordered badge field's rank"; a code that is not a declared badge field should be refused with the list of valid codes, as `--priority ghost` is (`error: unknown priority 'ghost' (one of: ...)`).

## Code
Both commands share `_badge_rank` in `src/squads/_cli/_main.py`, which returns `math.inf` for every item when the field or collection is unresolvable, so a typo is a silent no-op. One root cause, one bug.

## Severity
low
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
