---
id: TASK-521
sequence_id: 521
type: task
title: 'Repo-wide comment sweep: strip over-commenting in code and config'
status: Draft
author: manager
priority: medium
refs:
- FEAT-237
description: Complete tour of every code/config comment; remove ID refs, verbose narration,
  and restate-the-obvious comments
created_at: '2026-07-21T09:35:58Z'
updated_at: '2026-07-21T09:35:58Z'
---
<!-- sq:body -->
## Scope

A complete tour of **every comment in the repository** — Python source under `src/` and `tests/`,
and all config: `pyproject.toml`, CI/workflow YAML, and any other TOML/YAML/JSON that carries
comments. Bring the whole tree to the terse standard: default to **no comment**; keep one only
where something is genuinely non-obvious, and then a single short line.

## What to remove

- Comments that cite sq/ADR/task/feature/review IDs (behavior over provenance — the linkage lives
  in the item, not the source). This extends the item-ref strip already done to *non-item content*
  to now cover **inline code and config comments** too.
- Verbose, editorializing, multi-line narration that explains at essay length what a one-line read
  of the code/config already makes plain.
- Comments that merely restate the code or a self-evident name (e.g. an "optional TUI extra"
  narration above a `tui = ["textual…"]` line — the names already say it).

## What to keep

- A single-line comment where the *why* is genuinely non-obvious (a workaround, a non-local
  invariant, a gotcha that would otherwise trip a reader).
- Docstrings that document real behavior/contract — trimmed to the essential, not deleted; drop
  docstrings that only narrate.

## Acceptance

- Every source and config file's comments have been reviewed against the bar above and the cruft
  removed, in one reviewable sweep.
- The terse-comment standard is written down (a short line in the repo's conventions doc) so it
  doesn't regress, and the existing hygiene guard is checked for whether it can be extended to
  catch item-ref/over-comment regressions in code and config, not only in shipped docs.
- All gates stay green (`pyright`, `ruff`, the suite) — this is comments/docstrings only, no
  behavior change.

## Non-goals

- No code restructuring or behavior changes; no touching marker lines or generated/managed files.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 521 add-subtask "<title>"`; track with `sq task 521 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
