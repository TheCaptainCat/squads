---
id: BUG-1090
sequence_id: 1090
type: bug
title: Config stamp rewrites .squads.toml, dropping comments and unknown keys
status: Verified
author: qa
refs:
- REV-1089
- MILE-1051:targets
- ADR-1119
created_at: '2026-10-17T02:50:08Z'
updated_at: '2026-10-24T19:45:02Z'
priority: medium
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
- [2026-10-17T03:10:55Z] `manager` Catherine Manager:
  - Also covers REV-1089 F5: the [display] preservation matches header lines instead of parsing TOML (multi-line string with a '[' line, quoted ["display"] header). A real round-trip fixes both.
- [2026-10-24T19:44:03Z] `manager` Catherine Manager:
  - Fixed by ADR-1119 (commits ab391d82, 1104c03f): sq sync no longer writes .squads.toml, and migrate up edits only the schema_version value or regenerates a legacy config. @qa please verify.
- [2026-10-24T19:45:01Z] `qa` Mara Tester:
  - Verified with the dev build in a scratch squad (git init, fresh sq init, then the report's file extended with a squads_version line, unknown key, trailing comments, working_language="fr", a multi-line string holding a "[not a table]" line, a [display] table with a quoted key and comment, and a [future] table). Driven: sq sync twice and sq migrate up (prints "already at schema v0.16; nothing to migrate"): .squads.toml byte-identical after each (cmp). sq list and sq check run without migrate up. Not driven: migrate up with a pending migration or legacy keys.
<!-- sq:discussion:end -->
