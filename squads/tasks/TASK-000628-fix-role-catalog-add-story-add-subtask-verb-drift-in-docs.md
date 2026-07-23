---
id: TASK-628
sequence_id: 628
type: task
title: Fix role-catalog/add-story/add-subtask verb drift in docs
status: Draft
parent: FEAT-574
author: tech-lead
description: 'US1: correct non-existent verbs in roles/recipes/agents/adoption/tutorial
  docs (after 575)'
created_at: '2026-07-23T08:03:50Z'
updated_at: '2026-07-23T08:03:50Z'
---
<!-- sq:body -->
Implements FEAT-574 **US1**. Correct the CLI-verb drift in the shipped docs so every
documented invocation names a verb that actually resolves. Doc correction only — the
verbs themselves are added by FEAT-575.

**Build order:** runs **after** FEAT-575 lands. `sq role list` and `sq operator list`
only become real verbs there; the doc fixes below point at them.

## Fixes

- `docs/roles.md` (lines ~55-56): `sq role list` and `sq role list --available`.
  After FEAT-575, `sq role list` is a real verb for the **active roster** — keep that
  line, it is now correct. `sq role list --available` (the bundled catalog) has no
  such flag; replace it with `sq role catalog`.
- `docs/recipes.md`, `docs/agents.md`: any `sq role list --available` / non-existent
  role-listing invocation → `sq role catalog` for the bundled catalog, `sq role list`
  for the active roster.
- `docs/adoption.md` (lines ~57-58): `story add FEAT-7 "…"` → `sq feature 7 add-story
  "…"`; `subtask add TASK-8 "…"` → `sq task 8 add-subtask "…"`.
- `docs/tutorial.md` (line ~66): the `story add`/`subtask add` prose → the real
  `add-story` / `add-subtask` verbs on the addressed item.

## Constraints

- These are **adopter-facing** docs: describe the tool for adopters — no sq item /
  ticket / GitHub references, and no repo/dev-process content (CI, dogfood, packaging,
  test internals).
- Verify every `sq …` invocation you write resolves against the current CLI (the
  FEAT-574 US4 drift-guard test will enforce this mechanically once it lands).

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

_Add with `sq task 628 add-subtask "<title>"`; track with `sq task 628 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
