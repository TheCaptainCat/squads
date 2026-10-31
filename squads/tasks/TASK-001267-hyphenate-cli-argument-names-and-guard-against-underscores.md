---
id: TASK-1267
sequence_id: 1267
type: task
title: Hyphenate CLI argument names and guard against underscores
status: Done
author: tech-lead
assignee: python-dev
refs:
- ADR-1172
- REV-1260:addresses
description: Rename the five underscore argument names to hyphens; tests/meta guard
  over the command tree.
subentities:
- local_id: ST1
  title: Declare hyphenated metavars on the five arguments; update markers, usage
    assertions, docs
  status: Done
- local_id: ST2
  title: 'tests/meta guard: no underscore in any argument name, falsified'
  status: Done
- local_id: ST3
  title: Positional-invocation check and CHANGELOG 0.19.0 strings for the writer
  status: Done
created_at: '2026-10-31T08:20:14Z'
updated_at: '2026-10-31T08:38:50Z'
priority: medium
---
<!-- sq:body -->
## Why

The operator ruled on 2026-10-31 (op-pierre comment on ADR-1172) that CLI argument names use hyphens, never underscores. REV-1260 noted the mix: `{new-type}` and `{local-id}` beside `{old_status}`, `{new_status}` and `[root_id]`. Typer names an argument without a `metavar=` after its Python parameter, so an underscore leaks into the shown name; a declared metavar copies whatever is written. ADR-1172 already rules lower case and naming by `human_readable_name`.

## Inventory (measured 2026-10-31)

Walking `tests/_help_tree.command_nodes(include_hidden=True)` on this repository's squad: 282 arguments, five with an underscore in `human_readable_name` or `metavar`:

| Command | Python parameter | Shown today | Target |
|---|---|---|---|
| `sq migrate rename-status` | `old_status` | `{old_status}` (declared metavar) | `{old-status}` |
| `sq migrate rename-status` | `new_status` | `{new_status}` (declared metavar) | `{new-status}` |
| `sq migrate rename-type` | `old_type` | `{old_type}` (declared metavar) | `{old-type}` |
| `sq migrate rename-type` | `new_type` | `{new_type}` (declared metavar) | `{new-type}` |
| `sq tree` | `root_id` | `[root_id]` (no metavar) | `[root-id]` |

The item `move` commands (`_cli/_items.py`, `_cli/_roster.py`) already declare `metavar="status"` and are clean. Re-run the walk before starting: a tree built from an override squad must give the same answer, since argument names come from code.

## Scope

1. Declare the hyphenated metavar on each of the five arguments (`src/squads/_cli/_migrate.py`, `src/squads/_cli/_main.py`). The Python parameter names stay.
2. Every place the old shown name appears follows: usage lines and `Missing argument '…'` errors (both read `human_readable_name`), the `@pytest.mark.covers(...)` markers keyed on the argument name (`tests/cli/test_migrate.py`, `tests/cli/test_tree.py`), the usage-line assertions (`tests/cli/test_tree.py`, `tests/regressions/test_an_unknown_value_is_refused_not_answered_empty.py`), and the docs: `README.md` (`sq tree [root_id]`), `docs/workflow.md` (the `rename-type` / `rename-status` entries), `docs/migration.md` (`<new_type>`). Completion offers no argument names (positional), so nothing changes there; confirm it.
3. Guard in `tests/meta`: one test over the built command tree (`command_nodes(include_hidden=True)`) that fails on an underscore in any argument's `human_readable_name` or declared `metavar`, naming the command and argument. Falsify it: drop one fixed metavar, see it red with that command named, restore. Record the falsification in the handback.
4. Leave alone: JSON field names (`old_status` in `retype --json`, `docs/stability.md`), option names (already hyphenated by Typer), Python parameter names.

## Surface change for adopters

Usage text and the missing-argument error text change; nothing an invocation types does. All five are click positional arguments, which have no named form, so every existing invocation keeps working. Verify that claim in the handback: run `sq migrate rename-status`, `sq migrate rename-type` and `sq tree <id>` positionally on a scratch squad before and after, same result. It is an adopter-visible text change, so the 0.19.0 section of `CHANGELOG.md` needs it: line 94 already lists `{old_status} {new_status}` and `[root_id]` as the new usage form and must show the hyphenated names. That prose goes through the writer (`tech-writer`); the dev reports the exact new strings.

## Acceptance

- The walk in Inventory reports zero arguments with an underscore; the new guard is green and was seen red under falsification.
- `sq migrate rename-status --help` shows `{type} {old-status} {new-status}`; `sq migrate rename-type --help` shows `{old-type} {new-type}`; `sq tree --help` shows `[root-id]`.
- Docs and README carry no old argument name (grep `old_status|new_status|old_type|new_type|root_id` over `docs/` and `README.md` returns only JSON field names).
- CHANGELOG 0.19.0 entry corrected through the writer.
- Gates, each green: `uv run --all-extras pyright`, `uv run --all-extras ruff check .` and `ruff format --check .`; full `uv run --all-extras pytest -n 6`; `tests/cli` under `--api-mode remote` and the routes run; `tests/cli` under `--squad override`; `pytest -n0 tests/cross_process`; `gen_template_manifest --check`; `sq check` clean.
- Expected test count change: +1 guard test (plus its falsification witness if written as a second case); existing tests are edited, not added.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1267 add-subtask "<title>"`; track with `sq task 1267 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Declare hyphenated metavars on the five arguments; update markers, usage assertions, docs

<!-- sq:subtask:ST1:body -->
Add `metavar="old-status"`, `"new-status"`, `"old-type"`, `"new-type"` in `src/squads/_cli/_migrate.py` and `metavar="root-id"` on `sq tree` in `src/squads/_cli/_main.py`. Follow the new names through the `covers` markers in `tests/cli/test_migrate.py` and `tests/cli/test_tree.py`, the usage-line assertions (`tests/cli/test_tree.py`, `tests/regressions/test_an_unknown_value_is_refused_not_answered_empty.py`), `README.md`, `docs/workflow.md` and `docs/migration.md`. JSON field names stay.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — tests/meta guard: no underscore in any argument name, falsified

<!-- sq:subtask:ST2:body -->
One test in `tests/meta` over `tests/_help_tree.command_nodes(include_hidden=True)`: every argument's `human_readable_name` and declared `metavar` is free of `_`; a failure names the command and argument. Falsify by dropping one metavar from the first subtask (red, naming it), then restore.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Positional-invocation check and CHANGELOG 0.19.0 strings for the writer

<!-- sq:subtask:ST3:body -->
On a scratch squad (nested, not under /tmp root), run `sq migrate rename-status`, `sq migrate rename-type` and `sq tree <id>` positionally before and after: same result, which shows no invocation breaks. Report the new usage strings for the CHANGELOG 0.19.0 line that lists `{old_status} {new_status}` and `[root_id]`; the writer edits that prose.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-31T08:20:30Z] `tech-lead` Olivia Lead:
  - @architect Does ADR-1172 need a one-line amendment for the operator's hyphen ruling of 2026-10-31 (op-pierre comment on ADR-1172)? Rule "Parameter name" states argument names are lower case; this task adds hyphens-never-underscores in code and a tests/meta guard. If the rule should say it too, amend in place and note it here.
- [2026-10-31T08:32:41Z] `python-dev` Elias Python:
  - Done on the worktree branch, commit 218abb48. Guard: tests/meta/test_no_argument_name_carries_an_underscore.py (falsified by dropping the old-type metavar: red naming `sq migrate rename-type: 'old_type'`, restored green). Positional runs of tree, rename-status and rename-type on a scratch squad give identical output and exit codes before and after.
    
    For the writer, CHANGELOG 0.19.0:
    - line 94: `{old_status} {new_status}` -> `{old-status} {new-status}`; `[root_id]` -> `[root-id]`
    - line 16: `sq migrate rename-type daemon <new_type>` -> `<new-type>`
    - the usage strings now read: `sq migrate rename-type [OPTIONS] {old-type} {new-type}`, `sq migrate rename-status [OPTIONS] {type} {old-status} {new-status}`, `sq tree [OPTIONS] [root-id]`
- [2026-10-31T08:33:48Z] `architect` Robert Architect:
  - @tech-lead Yes. The rule "Parameter name" of ADR-1172 now says it (amended in place 2026-10-31): argument names are lower case with hyphens, never underscores, and the tests/meta guard holds it. The coverage markers name the hyphenated metavars.
- [2026-10-31T08:38:49Z] `manager` Catherine Manager:
  - Integrated on release/0.19 as 85c4926b. Gates: pyright 0, ruff clean, manifest current, full suite 1990 passed, remote 999, routes 999, override 840, cross-process 27. Accepted under the operator's ruling (2026-10-31); the CHANGELOG lines follow through the writer.
<!-- sq:discussion:end -->
