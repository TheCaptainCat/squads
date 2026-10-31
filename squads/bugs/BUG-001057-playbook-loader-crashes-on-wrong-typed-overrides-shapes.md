---
id: BUG-1057
sequence_id: 1057
type: bug
title: Playbook loader crashes on wrong-typed overrides shapes
status: Verified
author: qa
refs:
- REV-1050
- MILE-934:targets
created_at: '2026-10-16T12:21:17Z'
updated_at: '2026-10-16T19:08:35Z'
priority: medium
---
<!-- sq:body -->
The playbook loader raises an uncaught `AttributeError` on a wrong-typed top-level shape in `.overrides/playbook.toml`, so `sq check` prints a traceback and exits 1 instead of reporting a clean error. Same crash class the role catalog loader just fixed.

Reproduced with the dev build (HEAD ad2cbbe9) on a fresh `sq init` squad in a git-inited scratch dir, with each of these as the whole of `squads/.overrides/playbook.toml`, then `sq -C <scratch> check --json`:

- `types = 3` -> exit 1, `AttributeError: 'int' object has no attribute 'items'`
- `types = [1]` -> exit 1, `AttributeError: 'list' object has no attribute 'items'`
- `[types]` with `epic = 3` -> exit 1, `AttributeError: 'int' object has no attribute 'get'`

The traceback runs through `resolve_playbook` (called from the service open path), so every command that opens the service is likely affected, not only `check`.

Expected: the loader turns these into a `SquadsError` (as the workflow loader does for `items = [1]`, which gives `workflow config invalid` at exit 3) and `sq check` reports it as an error on the overrides file, with no traceback.

Note: on this build `statuses = 3` in `.overrides/workflow.toml` also crashes `sq check` (`TypeError: 'int' object is not iterable`, via `_workflow/_loader.py`), contrary to the review's claim that every workflow shape is reported cleanly. `items = [1]` is reported cleanly. The fix should cover that shape too, or split it out.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T18:08:22Z] `python-dev` Elias Python:
  - Fixed in the commit "Rejected wrong-typed playbook and workflow override shapes without a traceback". Playbook build now shape-checks types, each entry and its roles; the workflow drift check skips non-table sections. Probing also found roles = 3 (playbook) and items/collections/lifecycles = 3 (workflow) crashing; all fixed. Table of 13 shapes; falsification 11 of 13 fail on the old loaders (2 were already clean controls).
- [2026-10-16T18:23:29Z] `python-dev` Elias Python:
  - Commit 501e42d7 on branch worktree-agent-a2f892de06784925e.
- [2026-10-16T19:08:35Z] `manager` Catherine Manager:
  - Verified: fix approved on REV-1067 and merged into release/0.16 at 977730ec; full suite 11471 passed, 0 failed.
<!-- sq:discussion:end -->
