---
id: BUG-1090
sequence_id: 1090
type: bug
title: Config stamp rewrites .squads.toml, dropping comments and unknown keys
status: Open
author: qa
priority: medium
refs:
- REV-1089
- MILE-1051:targets
created_at: '2026-10-17T02:50:08Z'
updated_at: '2026-10-17T02:50:25Z'
---
<!-- sq:body -->
## Repro (released sq 0.15.0, scratch squad, `sq --dir <squad>/squads sync`)

`.squads.toml` before:

```
# my team notes: do not touch
squads_version = "0.15.0"
my_custom_key = "keep-me"   # unknown top-level key
active_backends = ["claude_code"]
squad_dir = "squads"
schema_version = "0.15"
```

Run `sq sync`, then diff before/after.

## Expected

Stamping the version or schema changes only that value. Comments, unknown keys and key order survive.

## Actual

The file is regenerated from the model. The comment and the unknown key `my_custom_key` are deleted without any report, and keys are reordered to the model order:

```
1,5c1
< # my team notes: do not touch
< squads_version = "0.15.0"
< my_custom_key = "keep-me"   # unknown top-level key
< active_backends = ["claude_code"]
< squad_dir = "squads"
---
> # squads project configuration
6a3,5
> squad_dir = "squads"
> active_backends = ["claude_code"]
> squads_version = "0.15.0"
```

Rewritten even when the stamped value is already current (sync with squads_version 0.15.0 already in the file).

## Commands that rewrite the file

Driven (0.15.0): `sq sync`.

Driven, no rewrite: `repair`, `check`, `list`, `migrate up` (nothing to migrate), `migrate help`, `operator list`, `role list`. Note `migrate up` with nothing pending exited 2 in one run with a pre-stamped file; not investigated.

Read from source, not driven: `_stamp_schema` (`sq migrate up` when a migration is pending), and init/adopt (`--force` overwrites `.squads.toml`). All go through `SquadsConfig.to_toml` (`_services/_maintenance.py` `_stamp_version`, `_stamp_schema`; `_services/_service.py`).

## Fix direction

Update the single value in place (line-level or tomlkit round-trip) instead of re-serializing the model. Found by REV-1089 F1.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
