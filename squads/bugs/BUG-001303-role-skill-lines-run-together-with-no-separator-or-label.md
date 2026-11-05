---
id: BUG-1303
sequence_id: 1303
type: bug
title: Role skill lines run together with no separator or label
status: Verified
author: qa
refs:
- FEAT-1290
created_at: '2026-11-05T01:43:46Z'
updated_at: '2026-11-05T02:47:23Z'
priority: medium
severity: medium
---
<!-- sq:body -->
The three lines of a `sq-role-<slug>` skill (role body, memory index, board) are emitted back to back with no blank line and no label. The memory bullets read as a continuation of the role's last playbook list, and the numbered board notices follow with nothing saying they are the board. The spec asks the agent to receive its role, its memory and the notices; a reader cannot tell which text is which.

## Steps to Reproduce

Driven on the host (Claude Code 2.1.318), scratch squad `/home/pchat/.cache/sq-qa-1290/fresh`, role `qa` with two memories and two board notices:

```
claude -p --allowedTools=Agent "Use the Agent tool once with subagent_type qa and prompt 'Say hello and stop.'"
```

Read the subagent transcript (`.../subagents/agent-*.jsonl`), the first user message of the `sq-role-qa` skill. Its tail:

```
**Hand off:**
- once filed, `@tech-lead` to triage; ...
- `memory-marker-qa-first-fact`: MEMORY-MARKER-qa first fact
- `memory-marker-qa-second-fact`: ...
1. BOARD-MARKER-BETA notice two ...
   - op-quinn, 2026-11-05T01:31:26Z
```

With a role that has no memory, the line `no memories for architect` is glued to the last playbook bullet the same way.

## Expected vs Actual

- **Expected:** each of the three outputs is separated and identifiable (a blank line and a short heading, or a label line), so the memory index and the board are not read as part of the playbook.
- **Actual:** no separator or label; memory bullets continue the previous list.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-05T02:18:41Z] `python-dev` Elias Python:
  - Fixed: the role skill pointer puts a static "## Memory" and "## Board" heading line before those two lines; the role line keeps no heading since the role body opens with its own. Test breaks without the headings. Uncommitted.
- [2026-11-05T02:47:11Z] `reviewer` Paul Reviewer:
  - Verified at 307c1030 by the reviewer. The role skill pointer now puts a `## Memory` and a `## Board` heading before those two lines, and the role line keeps no heading, since the role body opens with its own. Driven on a squad migrated from the 0.19 fixture. The grants are unchanged. Removing both headings turns `tests/cli/test_sync.py` red.
<!-- sq:discussion:end -->
