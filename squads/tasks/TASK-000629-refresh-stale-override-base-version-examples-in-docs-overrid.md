---
id: TASK-629
sequence_id: 629
type: task
title: Refresh stale override-base version examples in docs/overrides.md
status: Done
parent: FEAT-574
author: tech-lead
description: 'US2: replace 0.4.2-era example strings; prefer version-agnostic phrasing'
created_at: '2026-07-23T08:03:50Z'
updated_at: '2026-07-23T09:50:15Z'
---
<!-- sq:body -->
Implements FEAT-574 **US2**. Refresh the stale `override-base` version example strings
in `docs/overrides.md` so they stop reading as an old release.

## Scope

- `docs/overrides.md` cites `0.4.2` in several worked examples (around lines 412, 416,
  427, 431) — the installed version is well past that, so the examples read as stale.
- Prefer **version-agnostic** phrasing where practical so the examples can never drift
  again: e.g. a `<version>` / `<current-version>` placeholder in the stamp
  (`<!-- squads:override-base:<version> -->`) and prose that refers to "the version you
  scaffolded at" rather than a hardcoded number. `docs/stability.md` line ~78 already
  uses the `<version>` placeholder form — mirror that style.
- Where a concrete number genuinely aids the walkthrough (showing a diff between two
  versions), keep it illustrative but make it obviously an example, not a claim about
  the current release.

## Constraints

- Adopter-facing docs: no sq item / ticket / dev-process references.
- The FEAT-574 US4 drift-guard test should ideally also catch version-string drift —
  coordinate so the phrasing you choose is what that test asserts against (or is
  exempt by being an obvious placeholder).

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

_Add with `sq task 629 add-subtask "<title>"`; track with `sq task 629 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-23T09:28:39Z] Elias Python:
  - Replaced the stale 0.4.2/0.4.3 override-base examples in docs/overrides.md with the <version> placeholder form (mirrors stability.md's existing convention), for both the provenance-stamp comment and the sq check drift-warning example.
  - Also caught and fixed the same class of drift the guard's secondary check targets: docs/migration.md claimed schema_version is currently "0.2" in one place and "0.3" in another (both stale -- it's 0.11); replaced with a pointer to _models/_schema.py / sq migrate help instead of a number that goes stale again.
<!-- sq:discussion:end -->
