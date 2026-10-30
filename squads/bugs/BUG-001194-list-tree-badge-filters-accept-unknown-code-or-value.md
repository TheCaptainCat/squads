---
id: BUG-1194
sequence_id: 1194
type: bug
title: list/tree --badge filters accept unknown code or value
status: Verified
author: qa
refs:
- FEAT-1173
- MILE-1241:targets
created_at: '2026-10-27T23:37:41Z'
updated_at: '2026-10-29T20:40:23Z'
priority: low
severity: low
---
<!-- sq:body -->
Found while writing the CLI surface tests (FEAT-1173). Reproduced on the release/0.17 dev tree.

## Commands and observed
`sq list --badge priority=ghost`, `sq list --badge ghost=x`, `sq list --min-badge priority=ghost` all exit 0 printing `no items`. `sq list --priority ghost` is refused: `error: unknown priority 'ghost' (one of: urgent, high, medium, low)`, exit 1. `tree` takes the same options.

## Expected
Validate the CODE against the declared badge fields and the VALUE against that field's collection, with the same refusal as `--priority`. A typo currently reads as "no matching items".

## Code
`_build_badge_filters` / `_parse_badge_pairs` in `src/squads/_cli/_main.py` only check the `CODE=VALUE` shape. Only the `--priority` sugar goes through `parse_filter_badge_code`. One root cause for list and tree.

## Severity
low
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T20:40:23Z] `reviewer` Paul Reviewer:
  - Verified under REV-1247 (Approved at a56413b4).
<!-- sq:discussion:end -->
