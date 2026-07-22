---
id: TASK-521
sequence_id: 521
type: task
title: 'Repo-wide comment sweep: strip over-commenting in code and config'
status: Done
author: manager
assignee: python-dev
priority: medium
refs:
- FEAT-237
description: Complete tour of every code/config comment; remove ID refs, verbose narration,
  and restate-the-obvious comments
created_at: '2026-07-21T09:35:58Z'
updated_at: '2026-07-22T00:23:45Z'
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
- [2026-07-22T00:09:59Z] Elias Python:
  - Swept 29 files (0 executable-code changes; comments/docstrings only).
  - ID-citation strips: ADR-427 (pyproject.toml x2), ADR-322 (tests/_helpers.py x5 docstrings, substance kept), AC#5/#6/#7/#8 + F3/F4 (src/_cli/__init__.py, _cli/_create.py, _cli/_main.py, _services/_service.py, _services/_maintenance.py, _backends/_claude_code/_backend.py, tests/meta/test_no_unallowlisted_module_level_mutable_state.py).
  - Local sub-entity ID annotations stripped from ~16 test files (# US1/# ST1/# FEAT-2/# TASK-3/etc trailing comments on create/add-story/add-subtask calls) — redundant with adjacent code.
  - Verbose multi-line narration condensed (substance kept): .github/workflows/test.yml and vscode-client.yml top-of-file blocks, src/_interactions/__init__.py (3 section blocks), src/_workflow/_models.py (2 long comments).
  - Kept: all noqa/type:ignore/pyright:ignore/fmt:skip pragmas, non-obvious gotchas/invariants (e.g. _rendering/_engine.py thread-safety note, conftest.py FORCE_COLOR ordering note, test_item_lifecycle_edge_operations.py:52 spine-breaking gotcha), section-divider labels, module/durable docstrings.
  - Gates: uv run pyright (0 errors), uv run ruff check . (all checks passed), uv run ruff format --check . (341 files formatted), uv run pytest -q (full default suite, exit 0, all dots/skips no failures).
- [2026-07-22T00:21:45Z] Elias Python:
  - Addressed REV-564 F1/F2 (task stays InReview):
  - F1 — restored the dropped 'which check owns what' half-line in src/squads/_workflow/_models.py's reserved-vocab comment.
  - F2a — added the terse-comment bar to CONTRIBUTING.md's Conventions section (default no comment; one short line only if genuinely non-obvious; no ticket/ADR IDs in code/config comments).
  - F2b — extended tests/meta/test_source_and_new_test_tree_have_no_stray_ticket_references.py: new tokenize-based _comment_violations scan over src/+tests/ (catches # comments, never string-literal test data), and widened _NAME_AND_DOCSTRING_ROOTS to all of tests/ (old flat suite that justified the narrower list is gone). Caught 2 more real leaks in tests/conftest.py (REV-93/FEAT-178 docstrings) and forced a reword of the kept US1 gotcha comment in test_item_lifecycle_edge_operations.py — all fixed, no IDs left.
  - Gates: uv run pyright (0 errors), uv run ruff check . (clean), uv run ruff format --check . (341 files formatted), uv run pytest -q (full suite, exit 0). tests/meta/ run explicitly (-v): 10/10 in the extended hygiene file including the new planted-FEAT-999-in-a-comment detection test.
  - sq check clean. No commit made.
<!-- sq:discussion:end -->
