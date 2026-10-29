---
id: BUG-1240
sequence_id: 1240
type: bug
title: workflow view accepts a wrong ID prefix that show refuses
status: Open
author: qa
priority: low
severity: medium
refs:
- MILE-1241:targets
created_at: '2026-10-29T12:25:03Z'
updated_at: '2026-10-29T16:22:04Z'
---
<!-- sq:body -->
## Steps

Any squad: `sq show SKILL-2` and `sq workflow view memory_skill SKILL-2 --json` (SKILL-2 does not exist as a skill; number 2 is ROLE-2).

## Actual

`sq show SKILL-2` exits 1 with `error: SKILL-2 is ROLE-2 (role)`. `sq workflow view memory_skill SKILL-2 --json` exits 0 and prints ROLE-2 (Robert Architect). The same on released 0.17.0.

## Expected

Both resolve an ID the same way: a wrong prefix is refused, not resolved to the item that owns the number.

## Regression?

No, 0.17.0 behaves the same. Raised by the reviewer in REV-1235 for @qa.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T16:22:04Z] `qa` Mara Tester:
  - Sweep of the wrong-prefix gap, scratch squad (SKILL-2 given where number 2 is ROLE-2), released sq 0.17.0. All rows DRIVEN (run, exit code read bare, not through a pipe).
    
    Gap reproduced (workflow view only):
    - `sq workflow view memory_skill SKILL-2 --json` exits 0 and prints ROLE-2 (Robert Architect).
    - `sq workflow view role_definition SKILL-2 --json` exits 0 and prints the architect role (id ROLE-2).
    - `sq workflow view milestone_rollup SKILL-2 --json` (and TASK-2, TASK-21) exits 0 with `[]`: a ref view never checks the prefix, though it does refuse a number absent from the index (SKILL-999 exits 1, "no item ... in the index").
    
    Not affected, all refuse with `SKILL-2 is ROLE-2 (role)` and exit 1:
    - `sq show SKILL-2`
    - `sq tree SKILL-2` and `--json`
    - `sq task 21 ref add SKILL-2 --kind implements` (the target; the same call with ROLE-2 succeeds)
    - `sq role SKILL-2 show`, `sq skill SKILL-2 show`, `sq task SKILL-2 show`
    - `sq task SKILL-2 comment add ...`
    - `sq role SKILL-2 view role_definition`
    
    Conclusion: the gap is confined to `sq workflow view`'s ID resolution; the typed per-item routes and show/tree/ref add resolve through the checked path. Not driven: other workflow subcommands taking an ID (none found in `sq workflow --help`), the TUI and HTTP API (inferred unaffected, not run).
<!-- sq:discussion:end -->
