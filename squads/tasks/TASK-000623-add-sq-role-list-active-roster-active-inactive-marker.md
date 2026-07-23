---
id: TASK-623
sequence_id: 623
type: task
title: Add sq role list (active roster + active/inactive marker)
status: Done
parent: FEAT-575
author: tech-lead
description: 'US1: sq role list — active roster verb (+ --json), distinct from role
  catalog'
created_at: '2026-07-23T08:03:01Z'
updated_at: '2026-07-23T08:40:44Z'
---
<!-- sq:body -->
Implements FEAT-575 **US1**. Add a real `sq role list` verb that enumerates the
**active roster** (the activated `ROLE` items in the index), distinct from `sq role
catalog` (the bundled-but-not-necessarily-active catalog, which stays unchanged).

## Scope

- New `role list` command in `src/squads/_cli/_role.py`, registered on `role_app`
  alongside `catalog`/`activate`. A table with an **active/inactive marker** column;
  `--json` for the machine shape. Adding `list` as a group verb makes a role whose
  slug is literally `list` unaddressable by slug (use full ID / bare number) — the
  same rule already noted in the group epilog for `catalog`/`activate`; extend that
  note.
- Source rows from a service call listing roster roles — `list_items(item_type=ROSTER_ROLE)`
  (see `_services/_roster.py`, which already exposes `list_operators()` the same way).
  If a thin `list_roles()` reads cleaner at the CLI edge, add it to `RosterMixin`
  mirroring `list_operators()`.
- Columns: name, slug, title (resolve via the item's `extra`/`RoleDef` the way
  `role … show` does), plus the active/inactive marker. "Active" = the item's status
  is the roster active status (`STATUS_ACTIVE`); derive the marker generically off
  status — do not hardcode a second notion of "active".
- Escape every dynamic cell with `_cli._common.e()` before printing (Rich markup).

## --json + golden

- Add a parametrize row to `tests/cli/test_json_output_shape.py`
  (`("role_list", ["role", "list", "--json"])`) and generate
  `tests/goldens/role_list.json` via `UPDATE_GOLDENS=1`, then commit the golden. Keep
  the JSON shape additive-only (fields may be added later, never removed/renamed) —
  it is a public read shape.

## docs/stability.md reconciliation (in scope here)

`docs/stability.md` currently states standalone list commands were **removed pre-1.0**
in favour of `sq list -t <type>` (around lines 171 and 176-177; the JSON-shapes
section near line 266 also lists the catalog viewers). Shipping `role list` (and
`operator list` in US2) reverses that call, so this task must update those lines so
the doc stops contradicting the shipped CLI. This reverses a prior deliberate
decision — coordinate with the architect first (an ADR amendment may be warranted);
land the doc edit only once that is settled. This task owns the shared "removed list
commands" paragraph for both `role list` and `operator list`; the US2 task defers to
it. Keep the doc adopter-facing: describe the verb for adopters, no sq item / ticket /
dev-process references.

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

_Add with `sq task 623 add-subtask "<title>"`; track with `sq task 623 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-23T08:27:30Z] Elias Python:
  - Added `sq role list` (+ --json) listing the active roster with a status-derived active/inactive marker; new `RosterMixin.list_roles()`. Reversed the docs/stability.md 'standalone list commands removed' paragraph (role/operator only — skill list stays absent) per op-pierre's REV-565 triage (F3/F4). Golden: tests/goldens/role_list.json. Gates green, sq check clean.
<!-- sq:discussion:end -->
