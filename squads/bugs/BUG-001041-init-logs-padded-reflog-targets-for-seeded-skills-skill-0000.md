---
id: BUG-1041
sequence_id: 1041
type: bug
title: init logs padded reflog targets for seeded skills (SKILL-000009)
status: Verified
author: qa
priority: medium
refs:
- REV-1033
- MILE-1051:targets
created_at: '2026-10-16T09:01:15Z'
updated_at: '2026-10-25T19:52:15Z'
---
<!-- sq:body -->
## Repro

```
$ sq -C scratch init --roles all
$ python3 -c "import json;[print(json.loads(l)['target']) for l in open('scratch/squads/.reflog.jsonl') if json.loads(l)['op']=='create']"
ROLE-1 ... ROLE-8
SKILL-000009 ... SKILL-000017      <- padded
...
$ sq skill add deploy-x
created skill SKILL-25            <- reflog target SKILL-25, unpadded
```

`sq reflog` prints the same padded targets.

## Expected

Every reflog `target` is the formatted ID (`SKILL-9`), as docs/stability.md:234 (Tier 1 reflog schema) promises and as `sq skill add`, work items and roles already log. A consumer filtering on `target == "SKILL-9"` misses the skill's creation today.

## Cause

`src/squads/_services/_maintenance.py` ~1926 and ~2015 (the two skill-seeding sites) call `store.log("create", item_id, ...)` with the padded allocation string; `_services/_base.py` ~901 logs `item.id`. Log `item.id` at both sites and add a test asserting every reflog target round-trips through the unpadded formatter after `sq init`. Only the seeded skills were observed with the slip; `sq skill add` is fine.

Found in the docs audit (REV-1033, F2). Classified here as the home for that finding.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T19:52:12Z] `qa` Mara Tester:
  - Verified on sq 0.17.0. sq init --roles all and default init: reflog create targets for seeded skills are SKILL-9 .. SKILL-20, no padded target anywhere in .reflog.jsonl. Neighbours: sq skill add logs SKILL-21 (reflog and CLI consistent), sq adopt on a bare folder logs no padded target; sq check clean.
<!-- sq:discussion:end -->
