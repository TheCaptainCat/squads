---
id: TASK-1309
sequence_id: 1309
type: task
title: Keep titles and raw row values on one line
status: Ready
parent: FEAT-1290
author: tech-lead
assignee: python-dev
refs:
- REV-1307:addresses
description: Refuse a line break in a title; tidy the raw row join
subentities:
- local_id: ST1
  title: Refuse a line break in a title
  status: Todo
  assignee: python-dev
- local_id: ST2
  title: Join raw row lines with splitlines and strip
  status: Todo
  assignee: python-dev
created_at: '2026-11-05T04:04:09Z'
updated_at: '2026-11-05T04:12:52Z'
---
<!-- sq:body -->
Two core-side defects REV-1307 found on the `--raw` path after TASK-1308.

- ST1: a title with a line break is accepted and stored, and splits the raw heading (REV-1307 F4).
- ST2: the raw row join keeps a CR, doubles spaces on a blank line and keeps indentation (REV-1307 F5).

A Python developer is moving test files under `tests/cli/` at the same time. Put each new test where that layout puts its command; if a new module is needed, name it by the behaviour it tests, never after a current source or test module.

Gates: `uv run --all-extras pyright`, `ruff check`, `ruff format --check` clean on the touched files; the touched test modules, `tests/check` and `tests/meta` pass; `sq check` clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1309 add-subtask "<title>"`; track with `sq task 1309 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Refuse a line break in a title

<!-- sq:subtask:ST1:body -->
`sq create`, `update --title` and `add-<kind>` accept a line break in a title, for an item and for a sub-entity, and store it (`show --json` title is `"T\nsecond"`). Under `--raw` the heading then splits: `# TASK-12 — T`, then `second` as a bare line, and the VS Code preview renders the whole dossier as body.

Refuse it at input. `require_title` in `src/squads/_services/_base.py` is the guard every title write passes (item create, item rename on `update --title`, sub-entity add and update), so add the check there:
- a line break is any separator `str.splitlines` splits on (LF, CR, CRLF, VT, FF, U+0085, U+2028, U+2029, ...); test it as `title.splitlines() != [title]`, which also catches a trailing newline;
- one `SquadsError` line naming the input: `--title` for `update --title`, the title argument for `create` and `add-<kind>`. Thread the name through the existing `what` parameter from each caller; do not add a second guard beside `require_title`.

`sq import` and `sq pull` reach the same create and update cores, so they refuse a multi-line title too. Check that the import reports it as that event's error and a pull as that issue's error, without aborting the run.

**Stored titles.** Measured with the dev `sq` on a scratch squad: an item title `"T\nsecond"` and a sub-entity title `"x\ny"` are written, survive `sq repair`, and `sq check` reports nothing about either. The input guard does not reach a squad that already holds one (written before this fix or edited by hand), and `update --title` is the only repair. So a check rule is needed: add `title_single_line` to `COMMON_CORE` in `src/squads/_workflow/_validator_names.py` (every category, roster included), default level `warn` like the other title rules, reporting the item's title and each sub-entity's title, with the remediation `sq <type> <n> update --title "…"` (or the sub-entity form). Register it in `VALIDATOR_NAMES`, the default-level table and the dispatch table in `_services/_validators.py`, and list it in `docs/overrides.md` beside the other always-on rules.

Acceptance:
- create, `update --title` and `add-<kind>` each refuse a title holding LF, CR and U+2028 with one line naming `--title` or the title argument, and write nothing; one CLI test per command, each failing with the check reverted.
- a breach test in `tests/check` (`@pytest.mark.breaches("title_single_line")`) for an item title and a sub-entity title written to the file directly, asserting the whole issue list.
- `sq import` of an event whose title has a line break reports that event's error.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Join raw row lines with splitlines and strip

<!-- sq:subtask:ST2:body -->
`raw_lines` in `src/squads/_cli/_render/_rows.py` joins a row value with `" ".join(row.plain.split("\n"))`. Driven with `--desc "a<CR><LF>b<LF><LF>c<LF>  d"`, `--raw` prints `- **summary:** a<CR>b  c   d`: the CR stays (in a terminal it overwrites the start of the row), a blank line gives two spaces, and indentation is kept. A CRLF is likely in text taken from a tracker.

Rule: split the value with `splitlines()`, strip each piece, drop the empty pieces, and join the rest with one space. That handles CRLF, CR, blank lines and indentation, and leaves whitespace inside a line alone. Keep the docstring to what it does.

Acceptance:
- `show --raw` of an item whose `--desc` is `a<CR><LF>b<LF><LF>c<LF>  d` prints `- **summary:** a b c d`; the test compares the whole raw output and fails with the old join.
- a value with a tab inside a line keeps it.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
