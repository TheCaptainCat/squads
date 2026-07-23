---
id: TASK-625
sequence_id: 625
type: task
title: Add sq <type> <n> comments read-back verb (+ --json)
status: Done
parent: FEAT-575
author: tech-lead
description: 'US4: sq <type> <n> comments — read an item''s discussion (+ --json)'
created_at: '2026-07-23T08:03:03Z'
updated_at: '2026-07-23T08:40:46Z'
---
<!-- sq:body -->
Implements FEAT-575 **US4**. Add a focused `sq <type> <n> comments` read-back verb
(+ `--json`) that lists an item's top-level discussion, so verifying/scripting against
comment history doesn't require `show --json` plus manually indexing the `discussion[]`
array. `show --comments` already renders the discussion inline — this is the dedicated,
machine-readable verb, not a replacement for it.

## Scope

- New `comments` command on the per-item Typer group in `src/squads/_cli/_items.py`
  (near `show`), so it applies to every work-item type generically. Human output: the
  timestamped comments rendered as panes (reuse the same rendering `show --comments`
  uses). `--json`: an array of `{timestamp, author, body}`.
- Service side is already 90% there: `ItemsMixin.read_discussion(item_id)` returns the
  item's `:discussion` region string, and `_discussion.split_discussion(region)` parses
  it into `Comment(timestamp, author, body)` dataclasses — the exact `--json` shape.
  Add a thin service method (e.g. `comments(item_id) -> list[Comment]`) that composes
  those two rather than re-parsing at the CLI edge.
- Scope to the **item's** top-level discussion (matching `show --comments`' default).
  Sub-entity discussions are out of scope for this verb.
- Escape dynamic content via `_cli._common.e()` in the human path.

## --json + golden

- Add a parametrize row to `tests/cli/test_json_output_shape.py`
  (`("comments", ["task", "3", "comments", "--json"])` — the golden squad seeds a
  comment on TASK-3) and generate `tests/goldens/comments.json` via `UPDATE_GOLDENS=1`;
  commit the golden. Additive-only shape. Confirm the field names match the
  `discussion[]` entries already emitted by `show --json` so the two agree.

## Tests

- Service + CLI: an item with several comments returns them in file order with correct
  author/timestamp/body; an empty discussion returns `[]` (and the human path prints a
  clean "no comments" line, not an error); a multi-line / fenced-code comment body
  round-trips intact through `split_discussion`.

## Conventions (apply to every deliverable)

- No status/lifecycle prose in any body/doc (frontmatter `status:` is the single
  source of truth). The category term is **roster**, never "meta".
- No ticket IDs in source or test names — name by behaviour; keep the pointer in the
  sq ref/comment. Use PEP-695 `type X = …` for any alias. User-facing errors are the
  `SquadsError` family. Escape console output via `_cli._common.e()`.
- If you add any module-level constant, run `tests/meta` in your gate (the
  mutable-state guard has tripped repeatedly). Run all gates with `uv run --all-extras`
  (pyright/ruff/pytest) — a bare `uv run` prunes the `tui` extra and floods false
  errors.
- Set sq bodies via the CLI only; if you use `--file`, verify `grep -c '</\?content>'`
  == 0 on the written body. Run `uv run sq check` clean before handing off.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 625 add-subtask "<title>"`; track with `sq task 625 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-23T08:27:33Z] Elias Python:
  - Added `sq <type> <n> comments` (+ --json), generic over every item type. New Service.comments() composes read_discussion + split_discussion; CLI reuses show --comments' rendering (new common.print_comments) and prints a clean 'no comments' line when empty. --json field names (author/ts/body) match show --json's discussion[] entries exactly (asserted equal in tests). Golden: tests/goldens/comments.json. Gates green, sq check clean.
<!-- sq:discussion:end -->
