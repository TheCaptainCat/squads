---
summary: CI-only help-text failures are typer forcing color
created_at: '2026-08-15T20:27:19Z'
---
`typer.rich_utils` sets `FORCE_TERMINAL = True` whenever `GITHUB_ACTIONS`,
`FORCE_COLOR` or `PY_COLORS` is in the environment, latched into a module
constant at import time. A forced-terminal help render styles `-` and
`--flag` with two overlapping highlighter patterns, so Rich splits the
token — `--unlink` comes out as `ESC[36m-ESC[0mESC[36m-unlink`, and a
literal `"--unlink" in result.output` finds nothing. Symptom: help-text
assertions that are green locally and red on every GitHub runner.

Reproduce locally with `GITHUB_ACTIONS=true uv run --all-extras pytest <module>`.

The root conftest pins the console back to non-terminal
(`_TYPER_FORCE_DISABLE_TERMINAL=1`, `TTY_COMPATIBLE=0`, and
`typer.rich_utils.FORCE_TERMINAL = False` on the module for import-order
safety). Fix it there, never by relaxing the assertions.