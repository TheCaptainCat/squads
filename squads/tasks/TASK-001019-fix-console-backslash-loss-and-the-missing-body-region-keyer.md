---
id: TASK-1019
sequence_id: 1019
type: task
title: Fix console backslash loss and the missing-body-region KeyError
status: InProgress
author: tech-lead
assignee: python-dev
refs:
- BUG-1011:fixes
- BUG-1012:fixes
- MILE-934:targets
description: e() round-trips backslashes before brackets; body -m on a file with no
  body region fails cleanly and sq check reports it
subentities:
- local_id: ST1
  title: Make e() round-trip backslashes before brackets
  status: Todo
- local_id: ST2
  title: Fail body writes cleanly on a missing body region
  status: Todo
created_at: '2026-10-15T20:23:28Z'
updated_at: '2026-10-15T20:25:21Z'
---
<!-- sq:body -->
Two small, pre-existing defects, one subtask each. Neither has a feature parent: both are fixes linked by `fixes` refs to the bugs that describe them.

- **ST1** fixes BUG-1011: console text printed through `e()` loses a backslash that sits before a `[`.
- **ST2** fixes BUG-1012: `sq <type> <n> body -m` on an item file with no body marker region raises a raw `KeyError`, and `sq check` is silent about the missing region.

## Working tree

Work in an isolated git worktree. Another developer is working in the main tree on TASK-1018, which touches `src/squads/_paths.py`, `src/squads/_cli/__init__.py`, and the help detection in `src/squads/_cli/_common.py`. ST1 also edits `_cli/_common.py`, so keep that diff to the body of `e()`. Put the new escaping logic in its own private module (for example `src/squads/_cli/_markup.py`) and have `e()` call it, so the change in `_common.py` is about two lines and well away from the help-detection code. ST2 does not touch `_cli/`.

## Done when

- Both subtasks meet their acceptance criteria and every test in their tables passes.
- Each fix test has been seen failing with its fix reverted. Record the reverted run (the rows that failed) in the subtask's discussion.
- The fast gates are clean: `uv run --all-extras pyright`, `uv run --all-extras ruff check .`, `uv run --all-extras ruff format --check .`, and `uv run --all-extras pytest tests/meta`. A new module-level constant, such as a compiled regex, has to pass the mutable-state guard in `tests/meta`.
- Each fix has its entry in the unreleased CHANGELOG section.
- `sq check` is clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1019 add-subtask "<title>"`; track with `sq task 1019 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Make e() round-trip backslashes before brackets

<!-- sq:subtask:ST1:body -->
## Cause, verified on rich 15.0.0

There are two separate gaps between `rich.markup.escape` and Rich's renderer:

1. **A `[` that is not a tag.** `escape` only acts on a `[` that the tag pattern `[a-z#/@][^[]*?]` matches. Rich's `render` (`rich/markup.py`) then runs `plain_text.replace("\\[", "[")` on every stretch of non-tag text, which removes one backslash before **any** `[`. So `\[A-Z]` prints as `[A-Z]`, and `\\[A-Z]` prints as `\[A-Z]`.
2. **A trailing backslash.** `escape` adds one backslash when the string ends in a single `\`. That is correct when a markup tag follows (`[red]{e(x)}[/red]`) but doubles the backslash when nothing or plain text follows (`trail\` prints as `trail\\`). `e()` cannot know what follows it, so its output must be correct in every context.

A probe showed that one encoding satisfies both contexts: double the trailing run and follow it with an empty tag pair (`trail\\[bold][/bold]`). That prints `trail\` alone, before plain text, and inside `[red]…[/red]`. Any encoding that passes the table below is acceptable.

## Acceptance

For every string `s` in the tables below and every context `C` (alone: `"{}"`; before plain text: `"{} tail"`; inside a style pair: `"[red]{}[/red]"`), printing `C.format(e(s))` through a Rich `Console` produces `C` with the tags removed and `s` filled in, **byte for byte**. Check this in two ways: with `color_system=None`, and with colour on, after stripping ANSI. Do not check it by comparing escaped strings: what has to be right is the rendered output.

**Fix table.** Each of these rows must fail with `e()` reverted to plain `escape`:

| `s` (Python raw literal) | stock output, alone |
|---|---|
| `r"\[A-Z]"` | `[A-Z]` |
| `r"\\[A-Z]"` | `\[A-Z]` |
| `r"\[[A-Z]+-\d+\]"` (the BUG-1011 report) | `[[A-Z]+-\d+\]` |
| `"trail\\"` (one trailing backslash) | `trail\\` |
| `"a\\\\"` (two trailing backslashes), inside `[red]…[/red]` | `a\` |

**Guard table.** Plain `escape` already handles these. They stay green both before and after the fix, so they check that nothing regresses. They are not tests of the fix.

| `s` | why it is here |
|---|---|
| `"[x]"` | lowercase tag shape |
| `"[/x]"` | closing-tag shape |
| `r"\[x]"` | one backslash before a tag shape |
| `r"\\\[x]"` | odd run before a tag shape |
| `"[[x]"` | non-tag `[` right before a tag shape |
| `"plain"`, `""` | no-op |

## Tests

- **Unit:** a table-driven test over strings × contexts, for example `tests/unit/test_console_escape_round_trip.py`. Name the file after the behaviour and keep ticket IDs out of the code.
- **CLI, through the real error path:** `sq create task t --author tech-lead`, then `sq task <n> add-subtask x --story '\[A-Z]+-\d+\]'`. The error message must contain the story text exactly as the user typed it, upper-cased (the story id is upper-cased, so `\d` becomes `\D`). It must fail with `e()` reverted.
- **Remove the strict xfail** on `test_check_text_shows_a_pattern_with_an_escaped_bracket_intact` in `tests/cli/test_external_id_not_in_title_cli.py`. With the fix in place, a strict xfail turns into an XPASS failure. With the fix reverted and the marker removed, the test must fail. This is its red check.
- `tests/cli/test_show_command_renders_body_and_subentities.py::test_bracket_bearing_titles_and_comment_headers_never_leak_an_escape_backslash` must stay green.

## Scope

Change only `e()`. Callers that deliberately print raw values with `markup=False` already bypass it, so leave them alone. Keep the change in `_cli/_common.py` to the body of `e()` (see the task body for the overlap with TASK-1018).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Fail body writes cleanly on a missing body region

<!-- sq:subtask:ST2:body -->
## Cause

The body write closure in `ItemsMixin._body_mutate` (`src/squads/_services/_items.py`) reads the region with `sections.get_section(text, markers.BODY) or ""`. A missing region therefore reads as an empty body, and the write then fails at `sections.replace_section`, which raises `KeyError("section 'body' not found")`. The CLI's `@handle_errors` only catches `SquadsError`, so the user sees a traceback. `--append` goes through the same closure, and so does the bulk importer's `body` op.

## Acceptance: the write

When the item file has no complete `sq:body` region, `body -m` and `body --append -m` raise a `SquadsError` before anything is written. The message names:
- the item ID and the file path,
- the missing region (`sq:body`),
- a remedy: restore the `sq:body` / `sq:body:end` marker pair in that file, for example from git, and run the command again.

The CLI prints one clean `error:` line and exits 1, with no traceback and no `KeyError` text. The file is left exactly as it was, byte for byte, and neither its `updated_at` nor the index changes.

Detect the missing region inside the closure, before the `or ""` fallback hides it. Do not change `_sections.replace_section`'s `KeyError` contract, because other callers rely on it.

| file state | `body -m` | `body --append -m` |
|---|---|---|
| both markers absent | SquadsError, file unchanged | SquadsError, file unchanged |
| only the open marker | SquadsError, file unchanged | SquadsError, file unchanged |
| only the close marker | SquadsError, file unchanged | SquadsError, file unchanged |
| region intact (control) | writes | appends |

Run each failing row at service level and through the CLI (exit 1, an `error:` line naming the file, no `Traceback`). Every failing row must fail with the guard reverted, and the control row must pass both ways.

## Acceptance: sq check

**What exists today.** `_absent_body_region_issues` in `_services/_maintenance.py` is a file-level check that runs in `_scan_for_check`, below the per-item `CATALOG`. It reports a body region that is missing outright, but only for **role and skill** files: it returns `[]` for every other type. `_marker_issues` reports an unbalanced pair (one marker of the two) for every type. So a work item (task, bug, feature, and so on) whose `sq:body` open and close markers are **both** missing gets no finding.

Extend that same check rather than adding a catalog validator, for the reason given in `_validators.py`'s module docstring: the finding is about one file, applies to every type, and holds whether or not the frontmatter parses. A work item file with no `sq:body` pair at all gets one **error** finding. It names the missing region, and its remedy is the same one the write error gives. Keep the role/skill messages and their `view add`/`view disable` remedies unchanged. Do not report a region twice: a file with exactly one marker is still reported only by `_marker_issues`.

| file | expected `sq check` finding |
|---|---|
| task with both body markers absent | one error naming the missing `sq:body` region (fails with the fix reverted) |
| bug with both body markers absent | the same, so the check is not limited to tasks (fails with the fix reverted) |
| task with only the open marker | the existing `unclosed marker` error only, no second finding |
| role with both absent | the existing role message, unchanged |
| intact task (control) | no finding |

Confirm that the scan's file loop does not cover board notices or memory entries. Those files carry no body region, and the live repo has 22 board notices today. Check this against the live repo: `sq check` must stay clean on it.

## Tests

Add a service-level test and a CLI smoke test, for example `tests/cli/test_body_write_without_a_body_region.py` and a `sq check` case next to the existing absent-body-region tests. Name the files after the behaviour and keep ticket IDs out of the code.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-15T20:24:49Z] Olivia Lead:
  - @manager TASK-1019 is drafted and left at Draft: ST1 fixes BUG-1011 (e() round-trip), ST2 fixes BUG-1012 (a clean error on a missing body region, plus a sq check finding). Refs: fixes BUG-1011 and BUG-1012, targets MILE-934. No feature parent, because both are bug fixes.
  - Existing check: _absent_body_region_issues in _services/_maintenance.py covers only role and skill files, and _marker_issues covers only an unbalanced pair. A work item with both body markers gone gets no finding today, so ST2 extends _absent_body_region_issues to work items.
  - BUG-1011 has two causes, both seen on rich 15.0.0: render() removes one backslash before any non-tag [, and escape() doubles a trailing backslash when no tag follows it. The ST1 table checks the rendered output in three contexts and keeps the fix rows (which fail on the old code) apart from the regression guards. The strict xfail to remove is in tests/cli/test_external_id_not_in_title_cli.py.
  - Overlap with TASK-1018: ST1 edits _cli/_common.py, so the brief puts the logic in a new private module and changes only the body of e(). Work in a worktree.
<!-- sq:discussion:end -->
