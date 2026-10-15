---
id: BUG-1021
sequence_id: 1021
type: bug
title: Custom-type command cache leaks between in-process runs
status: Open
author: qa
priority: low
refs:
- TASK-1018
description: Class-level cache keeps one squad's custom type and aliases for later
  -C runs
created_at: '2026-10-15T20:51:06Z'
updated_at: '2026-10-15T20:51:06Z'
---
<!-- sq:body -->
## Summary

`_CustomTypeGroup._custom_cmd_cache` (a class-level `ClassVar` dict in `src/squads/_cli/__init__.py`) is keyed by type name and never invalidated, so it carries a command built from one squad's spec into later in-process runs against another squad. Two squads that declare the same custom type with different aliases then disagree. A one-shot `sq` process cannot hit it; in-process callers can (tests, a future server). Found while reviewing TASK-1018.

## Reproduction

Dev tree at 953a07ae (the `-C` option is unreleased), `uv run --project /home/pchat/projects/squads python repro.py <dir>`, one process, two scratch squads A and B. Each squad's `squads/.overrides/workflow.toml` declares:

```toml
[items.widget]
prefix = "WID"
folder = "widgets"
lifecycle = "work"
aliases = ["wa"]   # "wb" in squad B
```

Each squad also holds one widget, WID-2. The script uses `typer.testing.CliRunner` against `squads._cli:app`:

```python
r = CliRunner()
r.invoke(app, ["-C", "A", "wa", "2", "show"])   # exit 0
r.invoke(app, ["-C", "B", "wb", "2", "show"])   # exit 2
```

## Expected

Each run resolves `widget` and its aliases from the squad named by `-C`, so the second call shows WID-2 in B (exit 0).

## Actual

The second call exits 2 with `No such command 'wb'. Did you mean 'b'?`. The cached `widget` command was built from A's spec, and only A's aliases were registered in the cache, so B's alias is unknown. The same call run first, in a fresh process, succeeds.

## Notes

`_create.py` has a second class-level cache of the same shape (`_custom_cmd_cache`, built per canonical name) that likely leaks the same way; not driven.

## Versions

Dev tree at 953a07ae (`squads` 0.15.0 package version); the cache itself is not reachable from the released one-shot `sq`.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
