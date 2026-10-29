---
id: BUG-1240
sequence_id: 1240
type: bug
title: workflow view accepts a wrong ID prefix that show refuses
status: Open
author: qa
priority: low
severity: medium
created_at: '2026-10-29T12:25:03Z'
updated_at: '2026-10-29T12:25:03Z'
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
<!-- sq:discussion:end -->
