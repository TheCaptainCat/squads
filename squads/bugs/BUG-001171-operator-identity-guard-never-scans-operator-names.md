---
id: BUG-1171
sequence_id: 1171
type: bug
title: Operator-identity guard never scans operator names
status: Fixed
author: qa
priority: low
severity: low
refs:
- MILE-1051:targets
description: 'Guard reads full_name: but operators store title:, so a first-name leak
  in a template passes.'
created_at: '2026-10-26T17:36:27Z'
updated_at: '2026-10-26T19:48:44Z'
---
<!-- sq:body -->
The meta guard `tests/meta/test_bundled_templates_carry_no_operator_identity.py` is meant to fail when a bundled template names one of this squad's operators. It reads each operator's name with `_FULL_NAME_RE = ^\s*full_name:\s*(.+?)\s*$`, but the operator files under `squads/operators/` carry the name under `title:` (for example `title: Pierre Chat`) and have no `full_name:` key.

Result: the scanned identities are only the `op-` slugs. Reproduced on a scratch worktree: appending the line `Pierre` to `src/squads/_rendering/templates/workflow.md.j2` leaves all 3 tests green; appending `greet op-pierre` turns `test_no_bundled_template_names_one_of_this_squads_operators` red. A first-name or full-name leak into shipped package data passes the gate today.

Expected: the guard reads the name from `title:` as well, and a first-name leak goes red. Falsify after the fix by appending the first name to a template. Found by the old-suite falsification audit (TASK-1111 ST2). Low severity: the guard is a repo-hygiene gate, no runtime effect.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-26T19:48:42Z] `manager` Catherine Manager:
  - Fixed in 47efa336 (TASK-1112 ST2): the guard, now in tests_next/meta, reads title: as well as full_name:, and its floor requires a non-slug name; a planted first name turns it red. Needs QA verification.
<!-- sq:discussion:end -->
