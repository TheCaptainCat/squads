---
id: BUG-1000
sequence_id: 1000
type: bug
title: add-<kind> body hint names a command that does not exist
status: Verified
author: qa
priority: medium
refs:
- MILE-934:targets
created_at: '2026-10-12T05:38:08Z'
updated_at: '2026-10-16T19:08:33Z'
---
<!-- sq:body -->
## Reproduction

Released 0.15.0 tool, fresh squad (`sq init --default-names`), a feature, a task under it and a review. Then each `add-<kind>` verb, and each command its confirmation hints at:

```
$ sq feature <n> add-story S
added US1 to FEAT-<n>
  set its body:  sq story body FEAT-<n> US1 -m "…"  (or --file body.md / --file -)
$ sq story body FEAT-<n> US1 -m x
Error: No such command 'story'.          (exit 2)

$ sq task <n> add-subtask S
added ST1 to TASK-<n>
  set its body:  sq subtask body TASK-<n> ST1 -m "…"  (or --file body.md / --file -)
$ sq subtask body TASK-<n> ST1 -m x
Error: No such command 'subtask'. Did you mean 'task'?   (exit 2)

$ sq review <n> add-finding S
added F1 to REV-<n>
  set its body:  sq finding body REV-<n> F1 -m "…"  (or --file body.md / --file -)
$ sq finding body REV-<n> F1 -m x
Error: No such command 'finding'.        (exit 2)
```

The form that works is addressed through the parent, and it is the one the title advisory prints for an over-long title:

```
$ sq feature <n> story US1 body -m x
FEAT-<n> US1: body set                   (exit 0)
```

The hint is built in one place, `src/squads/_cli/_common.py` (the line formatting `sq {kind} body {parent_id} {local_id}`), shared by every `add-<kind>` verb, so all of them print the unusable form. No other verb prints a body hint.

## Expected versus actual

Expected: the hinted command runs, in the parent-addressed form `sq <parent-type> <n> <kind> <k> body -m "…"`.

Actual: the hinted command exits 2 with "No such command" for every kind. An agent or script following the tool's own output gets an error.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T17:55:00Z] Elias Python:
  - Fixed in f47c926a: the hint is built service-side beside the title advisory as sq <type> <n> <kind> <k> body. Table test over story, subtask, finding runs the hinted command; falsification 3 of 3 fail on the old line.
- [2026-10-16T18:23:27Z] Elias Python:
  - Commit f47c926a on branch worktree-agent-a2f892de06784925e.
- [2026-10-16T19:08:33Z] Catherine Manager:
  - Verified: fix approved on REV-1067 and merged into release/0.16 at 977730ec; full suite 11471 passed, 0 failed.
<!-- sq:discussion:end -->
