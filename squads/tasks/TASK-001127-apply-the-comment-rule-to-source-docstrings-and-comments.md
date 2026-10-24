---
id: TASK-1127
sequence_id: 1127
type: task
title: Apply the comment rule to source docstrings and comments
status: Ready
parent: FEAT-1092
author: tech-lead
priority: medium
refs:
- REV-956:addresses
- TASK-1126:depends-on
description: 'REV-956 F18: per-package prose sweep of src/ against the comment rule,
  plus a release-version guard.'
subentities:
- local_id: ST1
  title: Re-run the comment scan and add the version guard
  status: Todo
  story: US6
- local_id: ST2
  title: Sweep the services package
  status: Todo
  story: US6
- local_id: ST3
  title: Sweep workflow, overrides, index, models and migrations
  status: Todo
  story: US6
- local_id: ST4
  title: Sweep the CLI and TUI, leaving help docstrings
  status: Todo
  story: US6
- local_id: ST5
  title: Sweep the remaining packages and report the after-count
  status: Todo
  story: US6
created_at: '2026-10-24T21:54:04Z'
updated_at: '2026-10-24T21:55:45Z'
---
<!-- sq:body -->
## Goal

Bring the docstrings and comments under `src/squads/` within the project comment rule: a docstring is one or two sentences of what and why, a comment that restates the code is deleted, and there are no release versions, ticket ids or history outside migration runners. Finding F18. Test prose (F19) is not swept here: it rides the test-suite rebuild, which writes the new suite to the rule from the start (TASK-1112).

## Measure first

REV-956 drove the checks on 2026-10-09 and re-drove the docstring check on 2026-10-17: 627 docstrings over five non-blank lines in 95 of 137 files. The structural tasks before this one split and move the largest files, so ST1 re-runs the review's mechanical scan on the tree as it stands then. The scan uses `ast` plus `tokenize` over whole docstrings and comment runs with whitespace collapsed, so a line-wrapped token is not missed. Its checks: a docstring over five non-blank lines, a comment run over three lines, a release version outside `_migrations/`, a ticket-id shape, history phrasing. The re-run per-file table is the worklist and is posted as a comment here. The review's table (largest first: `_services/`, `_workflow/`, `_cli/`, `_interactions/`) is only the seed.

## Approach

- One pass per package group (ST2 to ST5), largest first, not one item per file.
- The rewrite is a judgement, not a truncation. Every long docstring holds a real constraint somewhere, so keep that constraint in one or two present-tense sentences and drop the rest. Apply the board's stranger test per sentence: if only someone who had just made the edit could have written it, it goes. Design history, rejected alternatives, citations of test paths, and names of methods that do not exist move out of the code; the commit message carries anything worth keeping.
- **Out of the sweep:** Typer command callbacks under `src/squads/_cli/`, whose docstrings are the `--help` text adopters read. Changing them is a CLI output change, owned by the writer and pinned by help goldens, so they are left alone here. Migration runners keep their version references. Jinja templates are not in scope.
- After rewriting a recurring claim, grep a distinctive fragment of the old wording across `src/` to close its copies.

## Tests

- **One `tests/meta` guard:** no release-version string (`0.N`, `v0.N.N`) in a comment or docstring outside `src/squads/_migrations/`. It uses the same `ast` plus `tokenize` scan, has a liveness row that plants a version and sees it fail, and lands after the hits are cleared, with no allowlist. The ticket-id guard already exists.
- No docstring-length guard yet: with today's counts it would only be an allowlist. Report the after-count so the operator can decide whether a ceiling earns a guard.
- The suite, pyright and ruff stay clean. No assertion is edited, since prose changes no behaviour.

## Generated output

None. Help text is excluded, so no CLI output changes, and no template is touched.

## CHANGELOG substance

None for adopters; report that to the writer.

## Order

After the check-rule task, so every file is swept once, after it has moved. Nothing in the test rebuild waits on this task, and the two can run side by side: this one edits only `src/` prose, which moves no seam the rebuild ports.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1127 add-subtask "<title>"`; track with `sq task 1127 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Re-run the comment scan and add the version guard

<!-- sq:subtask:ST1:body -->
Re-run REV-956's mechanical comment scan (`ast` plus `tokenize`, whitespace collapsed) over `src/squads/` on the tree as it stands. Checks: docstrings over five non-blank lines, comment runs over three lines, versions outside `_migrations/`, ticket ids, history phrases. Post the per-file table as a comment here as the worklist, then add the release-version guard once ST2 to ST5 have cleared its hits.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Sweep the services package

<!-- sq:subtask:ST2:body -->
Sweep `src/squads/_services/` against the comment rule using the ST1 worklist: one or two present-tense sentences per docstring, no restating comments, no history or versions. Apply the stranger test per sentence.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Sweep workflow, overrides, index, models and migrations

<!-- sq:subtask:ST3:body -->
Sweep `src/squads/_workflow/`, `_specmerge.py`, `_overrides/`, `_index/`, `_models/` and `_migrations/` against the comment rule. Migration runners keep their version references.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Sweep the CLI and TUI, leaving help docstrings

<!-- sq:subtask:ST4:body -->
Sweep `src/squads/_cli/` and `_tui/` against the comment rule, except Typer command callbacks, whose docstrings are `--help` text and stay as they are.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Sweep the remaining packages and report the after-count

<!-- sq:subtask:ST5:body -->
Sweep the remaining packages and top-level modules (`_interactions/`, `_roles/`, `_backends/`, `_rendering/`, `_views.py`, `_discussion.py`, `_badges.py`, `_sections.py`, `_itemfile.py` and the rest) against the comment rule. Post the after-count of docstrings over five lines.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
