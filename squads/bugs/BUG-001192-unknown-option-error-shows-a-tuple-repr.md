---
id: BUG-1192
sequence_id: 1192
type: bug
title: Unknown-option error shows a tuple repr
status: Fixed
author: qa
refs:
- FEAT-1173
- MILE-1241:targets
created_at: '2026-10-27T23:37:39Z'
updated_at: '2026-10-30T00:40:42Z'
priority: low
severity: low
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
- [2026-10-29T16:42:44Z] `op-pierre` Pierre Chat:
  - 2026-10-29: fixed upstream by typer 0.27.3; the surface test lands with the typer upgrade in TASK-1243, not in TASK-1245.
- [2026-10-30T00:05:35Z] `python-dev` Elias Python:
  - Fixed by typer 0.27.3 (locked in 8ef0e05e); surface test in ced7f061 is green on 0.27.3 and red on 0.26.7.
- [2026-10-30T00:40:42Z] `manager` Catherine Manager:
  - The dedicated test was dropped as a duplicate (REV-1260 F5). The plain-text suggestion is pinned by tests/cli/test_item_verbs.py::test_update_sets_and_clears_a_field_only_some_types_declare and tests/cli/test_subentity_verbs.py::test_a_required_field_has_no_clear_flag, which fail on typer 0.26.7 and pass on 0.27.3 (verified by the reviewer).
<!-- sq:discussion:end -->
