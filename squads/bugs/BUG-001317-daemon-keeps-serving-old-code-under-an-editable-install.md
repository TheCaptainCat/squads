---
id: BUG-1317
sequence_id: 1317
type: bug
title: Daemon keeps serving old code under an editable install
status: Open
author: qa
description: The daemon fingerprint covers config and overrides only, so a code change
  is invisible to it.
created_at: '2026-11-05T09:24:18Z'
updated_at: '2026-11-05T09:24:18Z'
severity: medium
---
<!-- sq:body -->
## Steps
1. Copy `src/` to a scratch dir and point `PYTHONPATH` at the copy (the shared tree is untouched), `sq init` a scratch squad, then `python -m squads board list` (starts a daemon). (driven)
2. Edit the copy: change the empty-board line in `_cli/_render/_board.py` to "NEW CODE: no current notices". (driven)
3. Run `python -m squads board list` again. (driven)

## Expected
The daemon notices its code is stale and retires or restarts, so the command shows the new code.

## Actual
- Step 3 printed "no current notices": the old code, served by the same daemon (pid unchanged, `sq daemon status` still "running"). (driven)
- The same command run in-process (daemon off) printed "NEW CODE: ...". (driven)
- After `sq daemon stop`, the next command started a fresh daemon and printed the new code. (driven)
- This is the manager's "No such option: --full" case: the CLI command tree lives in the daemon process. (inferred from the same mechanism)

## Cause
- The daemon key is a hash of squad path + `squads.__version__` + package directory (`_endpoint.py::squad_key`). None of these change when source files change under an editable install. (read)
- Retirement compares `fingerprint()` (`_daemon/_lifecycle.py`), which covers only the bytes of `.squads.toml` and the files under `<squad-dir>/.overrides/`. It cannot see code changes. (read)
- A released install is protected only because upgrading changes the version, so the key changes. (read)

## Suggested direction
Fold a code identity into the fingerprint or key for editable installs (for example the newest mtime of `*.py` under the package, computed once per request or at a cheap interval). Or document `sq daemon stop` as part of the dev loop and set `[daemon] enabled = false` for development.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
