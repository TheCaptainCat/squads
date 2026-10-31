---
id: BUG-1094
sequence_id: 1094
type: bug
title: Per-item verb help needs an existing item
status: Verified
author: qa
refs:
- REV-958
- MILE-1051:targets
created_at: '2026-10-17T05:06:10Z'
updated_at: '2026-10-25T11:11:36Z'
priority: medium
---
<!-- sq:body -->
`--help` on a per-item verb cannot be displayed unless the number resolves to an existing item of that type. Found in REV-958 F6; reproduced on release/0.16 HEAD 3c99dcc8 (clean export, fresh scratch squad) and on the released 0.15.0.

| Command | Actual |
|---|---|
| `sq task 1 show --help` | `error: 1 is ROLE-1 (role), not a task`, exit 1 |
| `sq task 999999 show --help` | `error: no item with number 999999 (use TASK-999999 or bare 999999)`, exit 1 |
| `sq task show --help` | help for the `task` group, not for `show` |
| `sq role nosuch show --help` | help for `show`, exit 0 |

Expected: `--help` on a leaf renders without resolving the address before it, as it already does for `role`, including before `sq init` completes any item of that type and in a squad with no item of the type yet.

Actual: the address is resolved first, so help for most per-type verbs (and the addressed `skill` verbs) is unreachable for a newcomer, and the root help advertises this route (`sq <command> --help`).

Text-only mitigation if the behaviour stays: one line in each type group's help saying any existing number of that type works as a placeholder.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T11:10:49Z] `qa` Mara Tester:
  - Verified at HEAD 091bfb77 (clean export): `task 1 show --help`, `task 999999 show --help`, `bug 1 update --help`, `skill nosuch show --help` all print leaf help, exit 0, no address resolved; `task show --help` prints the group help (N placeholder), exit 0.
<!-- sq:discussion:end -->
