---
id: BUG-1306
sequence_id: 1306
type: bug
title: Docs still send agents to sq-type skills and old names
status: Verified
author: qa
refs:
- FEAT-1290
created_at: '2026-11-05T01:43:47Z'
updated_at: '2026-11-05T02:47:24Z'
priority: medium
severity: medium
---
<!-- sq:body -->
Text an agent is told to read still directs it to the retired per-type skills and the old base-skill names. Role bodies point agents to `sq docs agents` (and `sq docs` topics are the "moved behind sq docs" home of the trimmed skills), so these pages are delivered guidance. US3 requires that no delivered text tells an agent to open an `sq-<type>` skill; US5/TASK-1298 covers the docs, so this may be the pending docs pass rather than a regression, but it is true of the build at 542beb09.

## Steps to Reproduce

On any squad built with the dev build at 542beb09:

```
sq docs agents | sed -n 18,25p
sq docs roles | grep -n "sq-epic\|sq-task"
sq docs internals | grep -n "item skills\|sq-<type>"
```

`sq docs agents` says: "Each role's Claude pointer preloads the `squads`, `greeting` and `sq-memory` skills, plus the item-type skills that role manages ... **Open the relevant `sq-<type>` skill** for role-directed guidance before you work an item of that type." It also says the `greeting` skill greets, and tells subagents nothing about `sq-role-<slug>`. `sq docs roles` lists `sq-<type>` skills per role and `sq skill greeting update --operator-invocable` examples; `sq docs README`/`internals` draw `skills/sq-task/SKILL.md` pointers. Delivered pointers, role bodies, CLAUDE.md and AGENTS.md themselves are clean (scanned).

Also: `sq migrate up` ends with "run `sq sync` to regenerate the agent files" although the run has already rewritten them; a following `sq sync` changes nothing (driven on `/home/pchat/.cache/sq-qa-1290/old` and `mig_a`).

## Expected vs Actual

- **Expected:** no shipped doc names an `sq-<type>` skill to open or the old `greeting`/`squads` names; the migrate output does not ask for a sync that is already done.
- **Actual:** as above.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-05T02:18:43Z] `python-dev` Elias Python:
  - Code half fixed: migrate up prints "agent files regenerated" instead of asking for sq sync when a step refreshed the backend (new agents_refreshed on the migration report), and the stripped-regions notice now counts only files that lost a retired region or key, not body-tag placement. docs/migration.md sample updated. The docs half was the earlier docs pass. Uncommitted.
- [2026-11-05T02:47:13Z] `reviewer` Paul Reviewer:
  - Verified the code half at 307c1030 (reviewer). `migrate up` on the 0.19 fixture now ends with "migrated to schema v0.20; index rebuilt — agent files regenerated", with no request for `sq sync`. The "stripped retired regions" notice no longer counts files that only gained the playbook tag. The docs half landed with the earlier docs pass. The remaining mentions of `greeting`, `squads` and `sq-<type>` in docs/migration.md belong to the upgrade sections of older releases and tell no agent to open a per-type skill.
<!-- sq:discussion:end -->
