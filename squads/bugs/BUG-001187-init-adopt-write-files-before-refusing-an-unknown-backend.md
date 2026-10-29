---
id: BUG-1187
sequence_id: 1187
type: bug
title: init/adopt write files before refusing an unknown backend
status: Fixed
author: qa
priority: medium
severity: medium
refs:
- FEAT-1173
- MILE-1241:targets
created_at: '2026-10-27T23:37:34Z'
updated_at: '2026-10-29T16:50:56Z'
---
<!-- sq:body -->
Found while writing the CLI surface tests (FEAT-1173). Reproduced on the release/0.17 dev tree in an empty git repo.

## Commands
1. `sq -C P init --backend bogus --default-names` then `sq -C P init --backend claude_code --default-names`
2. `sq -C Q adopt --backend bogus` then `sq -C Q adopt --backend claude_code`

## Observed
1. First call: `error: unknown backend 'bogus' (available: claude_code, agents_md)`, exit 1, but `.squads.toml`, `.gitignore`, `squads/.squads.json` and `squads/.gitignore` were already written. The retry fails: `error: .../.squads.toml already exists (use --force to overwrite)`, exit 1.
2. First call: same unknown-backend error, exit 1, but `.squads.toml` was written with `active_backends = ["bogus"]`. The retry with a valid backend fails with the same `unknown backend 'bogus'` because adopt reads the stored config.

## Expected
Validate the backend names before any file is written, so a refused call leaves the directory untouched and the corrected command works.

## Severity
medium
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
