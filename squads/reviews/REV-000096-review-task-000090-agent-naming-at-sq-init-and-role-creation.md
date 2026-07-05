---
id: REV-96
sequence_id: 96
type: review
title: Review TASK-000090 agent naming at sq init and role creation
status: Approved
author: reviewer
refs:
- TASK-90
created_at: '2026-06-12T21:42:47Z'
updated_at: '2026-06-12T21:43:35Z'
---
<!-- sq:body -->
Review of TASK-90 — agent naming at `sq init` and role creation (FEAT-14, ADR-85 §4).

## Verdict: APPROVED

## Scope reviewed
Naming surface only: `_models/_config.py` (`init_names` + `[init.names]` round-trip), `_services/_roster.py` (`activate_role(slug, *, name=None)`), `_services/_service.py` (`init(names=…)`), `_cli/_main.py` (`--name`/`--default-names`, injectable `_is_tty`, prompt loop), `_cli/_role.py` (`sq role activate --name`), `tests/test_agent_naming.py` (31 tests). The unrelated T87/T88/T89 override-group changes in the tree were not part of this review.

## Correctness vs ADR §4 — all confirmed
- **Flags + config both work; flags win over config.** `combined_names = {**names_from_config, **names_from_flags}` — flag precedence is correct and covered by `test_flags_win_over_config_names`.
- **TTY prompts only for gaps.** `interactive = _is_tty() and not default_names`; the loop skips any slug already in `combined_names`, prompts the rest, and a blank answer falls through to the pool/bundled default (not added to the dict). Covered.
- **`--default-names` and non-TTY both skip prompting.** Both drive `interactive=False`. Covered by dedicated tests with `_is_tty` monkeypatched to both branches.
- **Fallback never blank.** Unnamed roles get `effective_names.get(slug)` → `None` → resolver/`PREDEFINED`/pool name. Covered.

## End-to-end flow — verified by running the CLI, not just stored in extra
Activated `reviewer --name "Helen Reviewer"` in a scratch squad and confirmed the name appears in: the ROLE item frontmatter (`extra.full_name`), the agent pointer file (`.claude/agents/reviewer.md`), AND the CLAUDE.md Agent roster section (`- **Helen Reviewer** — code reviewer (`reviewer`)`). The init path's CLAUDE.md flow is also covered by `test_names_flow_to_claude_md_roster`.

## `_is_tty` seam
Clean module-level injectable callable (`_default_is_tty` default; tests monkeypatch `main_mod._is_tty`). Both TTY and non-TTY branches are driven in tests.

## Malformed / unknown input
`_parse_name_flags` raises `SquadsError` for missing `=`, empty slug, empty name — `@handle_errors` turns these into a clean message + exit 1 (verified directly: real exit code 1, no traceback). Unknown slugs surface via the resolver's `RoleNotFoundError` (a `SquadsError`).

## Prior `_config.py` pyright errors — RESOLVED
The mid-flight pyright errors the T88 reviewer saw in `_config.py` are gone. `from_toml_dict` now hoists the nested `[init]` table with proper `cast`/`isinstance` narrowing; `init_names: dict[str, str] = Field(default_factory=dict)` is soundly typed. Whole-tree `uv run pyright` = 0 errors, 0 warnings.

## CLAUDE.md conventions
- `e()`-escaping: role activate output and the show card escape dynamic names; init prompt copy is static.
- Injectable clock honoured (tests use `frozen_time`); no `datetime.now()`.
- Private modules, no `from __future__`, strict typing all preserved.
- B008 under `_cli` is expected (Typer call-defaults).

## Verification
- `uv run pytest` — 477 passed, 1 skipped.
- `uv run pyright` — 0 errors (whole tree).
- `uv run ruff check .` — All checks passed.
- `uv run ruff format --check .` — 88 files already formatted.

## Minor (non-blocking) observation
`test_activate_name_flows_to_pointer_file` guards its assertion with `if pointer.exists()`. I verified the pointer path (`.claude/agents/<slug>.md`) is correct and the file is written, so the assertion does fire today — but the guard means a future regression that stopped writing the pointer would silently pass this test rather than fail. Worth tightening to an unconditional `assert pointer.exists()` if revisited; not a blocker.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 96 add-finding "…" --severity high`; track with `sq review 96 finding <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:findings -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
