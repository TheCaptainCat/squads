---
id: BUG-1044
sequence_id: 1044
type: bug
title: 'create --help understates --author/--assignee: op slug accepted'
status: Open
author: qa
priority: low
refs:
- REV-1036
created_at: '2026-10-16T09:09:24Z'
updated_at: '2026-10-16T09:09:24Z'
---
<!-- sq:body -->
Reproduced on the dev build in a scratch squad.

    $ sq create bug --help
    --author    Authoring agent (role slug); must be registered.
    --assignee  Role slug or ID.

Both accept an operator slug in practice: after `sq operator add "Alice Tester"`, `sq create bug probe --author op-alice --assignee op-alice` succeeds and `sq bug 22 show` reports `assignee: op-alice`.

Checked for the same understatement:
- `sq <type> <n> comment --as`: help says "a role slug or 'op-<slug>'", correct.
- `sq create <type> --assignee`: "Role slug or ID." omits `op-<slug>`.
- `sq <type> <n> update --assignee`: no help text at all.

Expected: `--author` help says "role slug or op-<slug>", and the `--assignee` helps (create, update) say the same, matching `--as`.

Found while auditing the docs (REV-1036).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
