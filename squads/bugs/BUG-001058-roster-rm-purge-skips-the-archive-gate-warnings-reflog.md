---
id: BUG-1058
sequence_id: 1058
type: bug
title: Roster rm --purge skips the archive gate, warnings, reflog
status: Fixed
author: qa
priority: medium
refs:
- REV-1053
- MILE-934:targets
created_at: '2026-10-16T12:21:18Z'
updated_at: '2026-10-16T18:23:26Z'
---
<!-- sq:body -->
`sq role|skill <addr> rm --purge` bypasses the retirement gate and warnings that `status Archived` applies, and writes no reflog entry. Since plain `rm` now always refuses, `--purge` is the only delete path.

Reproduced with the dev build (HEAD ad2cbbe9) in a fresh `sq init` scratch squad (default roster) containing `TASK-21` authored by `manager`:

1. `sq role manager status Archived` -> `ROLE-1 -> Archived` plus `warning: ROLE-1 (manager) carried the default-role designation; no live role carries it now ...`
2. `sq role manager rm --purge` -> prints only `removed ROLE-1`, no warning. `sq check` then warns `TASK-21: author 'manager' is not a registered agent or operator`.
3. `sq skill squads status Archived` -> refused: `SKILL-20: not live (status 'Archived') but every role preloads it unconditionally ... no remedy exists`
4. `sq skill squads rm --purge` -> `removed SKILL-20` (succeeds). `sq skill sq-task rm --purge` -> `removed SKILL-19` (succeeds).
5. `squads/.reflog.jsonl` is 21 lines before and after steps 2 and 4; no remove entries (work-item `remove` does write one).

Not reproduced: the open-assigned-work warning on archive (assigning a role to the task did not work in my scratch, so only the default-role warning was compared).

Expected: a purge is checked at least as strictly as an archive (refuse the same structurally invalid cases, or at minimum print the same warnings), and every roster removal appends a reflog entry.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T18:23:26Z] Elias Python:
  - Fixed in a3f3090b: rm (with or without --purge) on a live roster entry is now held to the same retirement clauses as status Archived, so it is refused for the last live role and for skills the roles or types rely on; it prints the same warnings and writes a remove reflog entry. An already-archived entry is removed unchecked. The refusal text reads 'cannot remove', but its finding lines still say 'not live (status Archived)' and one remedy says 'make the skill live again'; wording left as is. 17 tests; falsification 16 of 17 fail with the gate, warnings and reflog removed (1 control). CHANGELOG entry left to the writer.
<!-- sq:discussion:end -->
