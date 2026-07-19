---
id: BUG-183
sequence_id: 183
type: bug
title: sq --json emits ANSI and breaks JSON parsing when FORCE_COLOR is set
status: Verified
author: manager
severity: medium
refs:
- FEAT-15
created_at: '2026-06-24T09:46:27Z'
updated_at: '2026-07-19T19:05:16Z'
---
<!-- sq:body -->
## Symptom

`sq <cmd> --json` emits ANSI color escape codes into stdout when a color-forcing
environment variable (`FORCE_COLOR`, `CLICOLOR_FORCE`, or `PY_COLORS`) is set — even
when the output is piped/redirected. The result is **not valid JSON**: a consumer gets
`json.decoder.JSONDecodeError: Expecting value: line 1 column 1` because byte 0 is `\x1b`.

## Repro

```
FORCE_COLOR=3 sq list --json | python3 -c "import sys, json; json.load(sys.stdin)"
# -> JSONDecodeError
```

## Root cause

The CLI's shared rich `Console` (`src/squads/_cli/_common.py:38`, module-level `console = Console()`)
honours `FORCE_COLOR` and reports `is_terminal=True` even when stdout is piped, so
`console.print_json(...)` colorizes. The `--json` surface must be color-free **unconditionally** —
it is a machine surface, not human output.

## Impact

Breaks any programmatic consumer of `sq --json` whose environment forces color — common in CI,
some interactive shells, and agent harnesses (the Claude Code background harness exports
`FORCE_COLOR=3`, which is how this was found). This undermines the frozen `--json` shapes that the
1.0 stability contract and the frontend epics (sq ui / sq web / VS Code, EPIC-28/29/99) all
depend on parsing.

## Proposed fix direction

Route all `--json` output through a color-disabled path independent of env/tty — e.g. a dedicated
`Console(no_color=True)` for JSON, or `print(json.dumps(..., indent=2))`. Separately consider
whether plain/piped human output should also ignore `FORCE_COLOR` (a user may legitimately want
forced color for human output, but `--json` must never colorize). Add a regression test that runs a
`--json` command with `FORCE_COLOR` set and asserts the output parses.

## Related (already applied)

The test suite was green in normal shells but red (106 failures) under `FORCE_COLOR` because the
module-level Console latched forced color at import. Fixed test determinism in `tests/conftest.py`
(strip `FORCE_COLOR`/`CLICOLOR_FORCE`/`PY_COLORS` at import + an autouse backstop). That hardens the
**tests**; this bug tracks hardening the actual **`--json` output**.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-24T10:12:12Z] Elias Python:
  - Fixed by adding `print_json_clean(s: str) -> None` in `src/squads/_cli/_common.py`. It uses `print(json.dumps(json.loads(s), indent=2))` — plain Python print, immune to FORCE_COLOR/CLICOLOR_FORCE/PY_COLORS by construction. 2-space indent matches what Rich print_json produced in non-terminal mode, so golden test shapes are byte-for-byte identical.
  - --json paths touched: `_common.py` (print_block), `_create.py` (create + create guide), `_items.py` (show, remove, refs, list-sub-entities), `_main.py` (list, tree, inbox, search, blocked, workload, mine, show, check), `_operator.py` (operator show), `_override.py` (override list, override diff), `_role.py` (role catalog, role show), `_skill.py` (skill show). All 22 `console.print_json()` call sites replaced. The shared `console` object is left unchanged for human output.
  - Regression test: `test_json_output_is_ansi_free_under_force_color` in `tests/test_json_no_ansi.py`. Sets FORCE_COLOR=3 mid-fixture, runs `sq list --json` via CliRunner, asserts (a) output json.loads cleanly and (b) no \\x1b in raw output.
  - Gate: 1026 passed, 1 skipped; pyright 0 errors; ruff check + format clean.
- [2026-07-19T19:05:16Z] Mara Tester:
  - print_json_clean present in _cli/_common.py; no console.print_json call sites remain in src/. Original test file was relocated by the FEAT-231 suite rebuild — coverage now lives at tests/cli/test_json_output_is_ansi_free.py (test_json_output_has_no_ansi_escapes_under_forced_color), which passes.
<!-- sq:discussion:end -->
