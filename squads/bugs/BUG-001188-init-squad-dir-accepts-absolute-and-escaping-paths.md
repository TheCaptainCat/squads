---
id: BUG-1188
sequence_id: 1188
type: bug
title: init --squad-dir accepts absolute and escaping paths
status: Fixed
author: qa
priority: medium
severity: medium
refs:
- FEAT-1173
- MILE-1241:targets
created_at: '2026-10-27T23:37:35Z'
updated_at: '2026-10-29T16:50:58Z'
---
<!-- sq:body -->
Found while writing the CLI surface tests (FEAT-1173). Reproduced on the release/0.17 dev tree in an empty git repo.

## Commands and observed
- `sq -C P init --default-names --squad-dir /abs`: unhandled traceback ending `PermissionError: [Errno 13] Permission denied: '/abs'`, exit 1. `.squads.toml` (with `squad_dir = "/abs"`) and `.gitignore` were written first, so a retry says `.squads.toml already exists`.
- `sq -C P init --default-names --squad-dir ''`: raw pydantic traceback (`squad_dir  String should have at least 1 character [type=string_too_short]`), exit 1. No files written.
- `sq -C P/proj init --default-names --squad-dir ../up`: exit 0 and the squad is created at `P/up`, outside the project directory, with `squad_dir = "../up"` in `.squads.toml`.

## Expected
`--squad-dir` should be validated before any write: refuse an absolute path, an empty value and a path that escapes the project root with a one-line `SquadsError` (exit 1), leaving nothing behind. The project's own invariant is that `abspath` is guarded against path traversal.

## Severity
medium
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
