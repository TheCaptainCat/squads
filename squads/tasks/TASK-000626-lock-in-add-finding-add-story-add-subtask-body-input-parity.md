---
id: TASK-626
sequence_id: 626
type: task
title: Lock in add-finding/add-story/add-subtask body-input parity
status: Done
parent: FEAT-575
author: tech-lead
description: 'US5: regression-lock body input (-m/--file/stdin) + stub-warning-only-when-empty'
created_at: '2026-07-23T08:03:04Z'
updated_at: '2026-07-23T08:40:47Z'
---
<!-- sq:body -->
Implements FEAT-575 **US5**. Lock in body-input parity across `add-finding` /
`add-story` / `add-subtask`. This is a **regression / parity-lock-in** task — no new
mechanism. As verified against the current tree, all three already accept `-m`,
`--file`, and `--file -` (stdin) through the generic `add-<kind>` builder
(`_register_add` in `src/squads/_cli/_items.py`, body resolved by
`resolve_body_optional`). The ask is to guarantee this holds uniformly and never
regresses.

## Scope

- Add regression tests (service + CLI) asserting, for **each** of the three built-in
  kinds:
  - `-m "…"` sets the sub-entity body in one shot.
  - `--file <path>` sets it from a file.
  - `--file -` sets it from stdin.
  - The resulting body is the supplied text (markers intact, sibling blocks
    untouched).
- Pin the placeholder-stub behaviour: the `sq check` "unwritten sub-entity body"
  warning fires **only** when no body was supplied at creation (already the observed
  behaviour). Assert both directions: created with a body → no stub warning; created
  with no body → exactly that warning. This is the parity-lock the story is really
  about.
- `title` stays the positional argument on `add-<kind>`; body arrives via `-m`/`--file`.
  If any of the three diverges from the others in how it accepts body input, that
  divergence is the bug to fix — but the current builder is already unified, so the
  expected outcome is tests-only plus any small consistency fix they surface.

## Tests

- Name by behaviour (no ticket id in the filename). Parametrize across the three kinds
  where practical so the parity is asserted from one place.

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

_Add with `sq task 626 add-subtask "<title>"`; track with `sq task 626 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-23T08:27:35Z] Elias Python:
  - Regression-locked body-input parity across add-story/add-subtask/add-finding: -m, --file <path>, --file - (stdin), parametrized over all three kinds, plus the stub-warning-fires-only-when-empty pin (both directions) and a sibling-blocks-untouched check. No code changes needed — the existing generic add-<kind> builder was already unified. Gates green, sq check clean.
<!-- sq:discussion:end -->
