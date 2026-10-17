---
id: BUG-1039
sequence_id: 1039
type: bug
title: Fresh agents_md init warns of pre-existing AGENTS.md content
status: Open
author: qa
priority: low
refs:
- REV-1032
- MILE-1051:targets
created_at: '2026-10-16T09:01:11Z'
updated_at: '2026-10-16T12:24:18Z'
---
<!-- sq:body -->
## Repro

```
$ mkdir c && git init -q c
$ sq -C c init --backend agents_md
...
warning: AGENTS.md had pre-existing hand-written content with no squads markers; the managed section was inserted at the top — review it for possible contradiction with that content.
```

No AGENTS.md existed before the command. Same init with `--backend claude_code` prints no warning. The resulting AGENTS.md holds only the managed section (`sq check` clean).

## Expected

No warning on an empty directory. The warning should fire only for content the adopter wrote.

## Cause

`_backends/_agents_md/_backend.py` `ensure_scaffold` (~77-86) writes a stub ("# AGENTS.md — Project AI agent guidance ... Run `sq sync` ...") when the file is missing. `write_managed` then runs through `_managed_region.py` (~59-64), sees non-empty text with no markers and reports "pre-existing hand-written content". The stub is sq's own, so the warning is a false positive and trains adopters to ignore the real one.

Fix options: have the managed-region check recognise the scaffold stub, or have the scaffold write nothing and let `write_managed` create the file. Add a test that a fresh agents_md init emits no warning and one that a real pre-existing AGENTS.md still does.

Found in the docs audit (REV-1032 aside, REV-1034).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
