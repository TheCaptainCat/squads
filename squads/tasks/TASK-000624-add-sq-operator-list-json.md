---
id: TASK-624
sequence_id: 624
type: task
title: Add sq operator list (+ --json)
status: Done
parent: FEAT-575
author: tech-lead
description: 'US2: sq operator list enumerates registered operators (+ --json); CLI-only'
created_at: '2026-07-23T08:03:02Z'
updated_at: '2026-07-23T08:40:45Z'
---
<!-- sq:body -->
Implements FEAT-575 **US2**. Add a `sq operator list` verb (+ `--json`) enumerating
the registered human operators. Today `sq operator` only exposes `add`/`show`/`rm` —
there is no way to enumerate operators at all.

## Scope

- New `operator list` command in `src/squads/_cli/_operator.py`, registered on
  `operator_app` alongside `add`. The service side already exists — `RosterMixin.list_operators()`
  returns the `OPERATOR` roster items — so this is a CLI-only add. Table (name, slug,
  id, status) + `--json`.
- `_OperatorDispatchGroup._ADDR_VERBS` and the group epilog currently name only `add`
  as the group verb. Adding `list` makes an operator whose slug is literally `list`
  unaddressable by slug (use full ID / bare number); extend the epilog note the same
  way `role`'s does.
- Escape every dynamic cell with `_cli._common.e()` before printing.

## --json + golden

- Add a parametrize row to `tests/cli/test_json_output_shape.py`
  (`("operator_list", ["operator", "list", "--json"])`) and generate
  `tests/goldens/operator_list.json` via `UPDATE_GOLDENS=1`; commit the golden. Match
  the field set already used by `operator … show --json` (id/slug/full_name/status)
  so the two shapes agree. Additive-only.

## docs/stability.md

The shared "standalone list commands removed" paragraph in `docs/stability.md` is
reconciled by the US1 task (it covers both `role list` and `operator list`). Do not
edit those lines here; coordinate ordering so US1's doc edit lands with (or before)
this verb, and confirm the paragraph reflects `operator list` once both land.

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

_Add with `sq task 624 add-subtask "<title>"`; track with `sq task 624 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-23T08:27:31Z] Elias Python:
  - Added `sq operator list` (+ --json), CLI-only over the existing list_operators(). --json field set matches operator show --json (id/slug/full_name/status). Golden: tests/goldens/operator_list.json. Gates green, sq check clean.
<!-- sq:discussion:end -->
