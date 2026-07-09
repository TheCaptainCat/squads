---
id: TASK-354
sequence_id: 354
type: task
title: Vulture ignore-names reconcile + full-suite/golden/lint verification
status: Draft
parent: FEAT-212
author: tech-lead
refs:
- TASK-351:depends-on
- TASK-353:depends-on
created_at: '2026-07-09T21:31:33Z'
updated_at: '2026-07-09T21:33:38Z'
---
<!-- sq:body -->
Closeout: reconcile the vulture ignore_names against the retired CLI dispatch, and run the authoritative full-suite/golden/lint gates for FEAT-212 (AC4/AC5). No product-source change beyond pyproject config.

## Scope

The per-kind service wrappers survive as delegators (TASK-351) but the CLI's per-kind getattr dispatch is gone (TASK-353). Update the vulture [tool.vulture].ignore_names block in pyproject.toml accordingly: the list_stories/list_subtasks/list_findings/get_subtask/get_story/get_finding/set_*_body entries were justified by CLI getattr dispatch, which is now stale. Reconcile: if the wrappers are now referenced only from tests (vulture scans src/squads only), keep the entries but correct the comment to 'test-only public service API'; if TASK-351 dropped any wrapper, remove its entry. Add ignore_names for any NEW generic public methods only if vulture flags them and they are genuinely reached dynamically (prefer a real static reference over a suppression).

Run vulture and confirm near-pure signal (no genuinely-dead symbol left un-triaged).

Run the authoritative gates once, redirected to a file per CLAUDE.md (pyright, then ruff check, then ruff format --check, then the full test suite). Confirm AC4 (built-in behaviour byte-identical, all prior tests green incl. the F1 golden) and AC5 (sq workflow lint catches a custom-kind machine referencing an out-of-vocabulary status).

## Files owned

- pyproject.toml ([tool.vulture].ignore_names reconcile)

## Acceptance

- vulture reports no untriaged dead symbol from this feature; ignore_names comments are accurate.

- pyright + ruff clean; full suite green; sq workflow lint AC5 demonstrated.

## Depends on

TASK-351 + TASK-353 (wrappers/dispatch settled). Runs last.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 354 add-subtask "<title>"`; track with `sq task 354 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
