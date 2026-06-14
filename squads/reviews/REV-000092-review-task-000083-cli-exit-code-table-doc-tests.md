---
id: REV-000092
sequence_id: 92
type: review
title: Review TASK-000083 — CLI exit-code table doc + tests
status: Approved
author: reviewer
created_at: '2026-06-12T21:03:00Z'
updated_at: '2026-06-12T21:03:26Z'
---
<!-- sq:body -->
## Scope

Review of the working-tree change for TASK-000083 (FEAT-000015, US2): the documented CLI exit-code contract and its test coverage.

Files reviewed:
- `src/squads/_cli/_main.py` — `check` docstring documents exit 0 / exit 3 and points at `sq docs faq`.
- `docs/faq.md` — new "What exit codes does `sq` use?" entry with the four-row table (0/1/2/3).
- `tests/test_cli.py` — 8 new tests (section TASK-000083) asserting each code across table and --json paths.

## Verdict: Approved

### Correctness against the settled contract (0/1/2/3)
- Exit 3 fires on both the table path (`_main.py:469-470`) and the `--json` path (`_main.py:457-459`), gated on `level == "error"` only — warnings never trigger 3. Matches the frozen contract.
- Exit 1 paths (SquadsError via `@handle_errors`, schema-mismatch hard-stop at `_common.py:450`, dispatch error at `_common.py:617`) are unchanged and remain 1.
- Exit 2 (`--at` parse at `_common.py:61`, plus Typer/Click usage errors) unchanged.

### Test coverage — each code genuinely exercised
- 0: clean read; clean check; **warnings-only check** (Superseded decision w/o supersedes edge → asserts `"warn" in output` AND exit 0 — proves a warning is present yet does not escalate to 3).
- 1: unknown ID (SquadsError); schema mismatch (rewrites `.squads.toml` 0.3→0.1, asserts `"migrate"` in output).
- 2: bad `--at` timestamp.
- 3: error-level issue (ghost index entry → "in index but no markdown file found") on both the table path and `--json` path (the latter asserts an `error`-level issue object).
- The exit-3-not-on-warnings requirement is directly proven by `test_exit_code_0_check_warnings_only`.

### Documentation accuracy
- FAQ table matches the contract exactly, including the explicit "warn-level-only results still exit 0" note and the FEAT-000013 forward-link for the formal stability doc.
- Docstring cross-reference `sq docs faq` resolves and renders the exit-code section (verified live).

### CLAUDE.md conventions
- No `<!-- sq:* -->` markers hand-edited. No Rich `e()` escaping concerns (test/docstring only). No SquadsError contract changed. pyright/ruff strict clean.

### Verification (run locally)
- `uv run pytest` → 395 passed, 1 skipped.
- `uv run pyright` → 0 errors. `uv run ruff check .` → clean. `uv run ruff format --check .` → clean.
- 8 new tests pass in isolation (`-k exit_code`).

### Non-blocking note (no finding filed)
The contract row for code 2 mentions Typer/Click usage errors (unknown option / missing arg); only the `--at` path is asserted. The documented behavior is correct and Typer's exit-2 is its own well-tested guarantee, so this is acceptable coverage — flagging only as a future nicety, not a change request.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 92 add-finding "…" --severity high`; track with `sq review 92 finding <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:findings -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T21:03:26Z] Paul Reviewer:
  - Approved. Contract (0/1/2/3) implemented and documented correctly; exit 3 fires only on error-level check issues — warnings-only exits 0 (proven by test_exit_code_0_check_warnings_only). All 8 tests pass, pytest 395 passed/1 skipped, pyright+ruff clean. No findings.
<!-- sq:discussion:end -->
