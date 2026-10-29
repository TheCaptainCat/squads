---
id: BUG-1192
sequence_id: 1192
type: bug
title: Unknown-option error shows a tuple repr
status: Open
author: qa
priority: low
severity: low
refs:
- FEAT-1173
- MILE-1241:targets
created_at: '2026-10-27T23:37:39Z'
updated_at: '2026-10-29T16:31:28Z'
---
<!-- sq:body -->
Found while writing the CLI surface tests (FEAT-1173). Reproduced on the release/0.17 dev tree.

## Commands
`sq role activate --slug x`, `sq create guide "g" --author architect --label x`

## Observed
```
Usage: sq role activate [OPTIONS] [SLUG]
╭─ Error ─╮
│ No such option: --slug ('(Possible options: --as)',) │
```
Exit code 2. The suggestion is wrapped as a Python tuple repr: `('(Possible options: --as)',)`, on every unknown-option error that has suggestions.

## Cause
Third-party: typer 0.26.7, `typer/_click/exceptions.py` `NoSuchOption.format_message` builds `suggest = (f"(Possible options: {possibility_str})",)`, a one-element tuple with a trailing comma, then interpolates it. squads has no handler of its own for it (no NoSuchOption / UsageError use under src/squads).

## Expected
`No such option: --slug (Possible options: --as)`. Fix by pinning/upgrading typer or formatting the usage error in the squads CLI error hook.

## Severity
low
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
