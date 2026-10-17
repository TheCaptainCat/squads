---
id: BUG-1057
sequence_id: 1057
type: bug
title: Playbook loader crashes on wrong-typed overrides shapes
status: Open
author: qa
priority: medium
refs:
- REV-1050
- MILE-934:targets
created_at: '2026-10-16T12:21:17Z'
updated_at: '2026-10-16T12:23:58Z'
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
<!-- sq:discussion:end -->
