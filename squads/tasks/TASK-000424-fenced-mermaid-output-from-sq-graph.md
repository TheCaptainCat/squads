---
id: TASK-424
sequence_id: 424
type: task
title: Fenced Mermaid output from sq graph
status: Done
parent: FEAT-377
author: tech-lead
assignee: python-dev
subentities:
- local_id: ST1
  title: Pre-fenced Mermaid variant of graph_to_mermaid + CLI smoke test
  status: Done
  story: US1
created_at: '2026-07-15T14:02:32Z'
updated_at: '2026-07-15T14:44:34Z'
---
<!-- sq:body -->
# Fenced Mermaid output from `sq graph`

`sq graph --format mermaid` already emits a valid Mermaid graph body via `graph_to_mermaid` (`src/squads/_services/_refs.py`), but raw — meant for piping to `mmdc` or pasting into Mermaid Live, not wrapped in a markdown fence. This task adds a pre-fenced variant so the output drops straight into a doc, PR description, or issue and renders inline.

## Scope

- Add a way to get the existing `graph_to_mermaid` output pre-fenced in a ```` ```mermaid ```` / ```` ``` ```` block. Either a new `--md`/`--markdown` flag, or a new `mermaid-md` value alongside `dot`/`mermaid` in the existing `--format` option in the `graph` command (`src/squads/_cli/_main.py`). Pick whichever reads cleanest against the current `--format` validation there (which today rejects anything but `dot`/`mermaid`); a `mermaid-md` format value keeps the surface to one option.
- Underlying graph serialization is unchanged — this only wraps the existing `graph_to_mermaid` output in a fence. Do not touch the serializer or the traversal.
- Keep the fenced output escaped-safe / `markup=False` like the existing `dot`/`mermaid` branches (they print with `markup=False, highlight=False`).

## Tests

CLI smoke test asserting the fence lines (opening ```` ```mermaid ```` and closing ```` ``` ````) wrap the serialized body. Name the test by behavior.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 400 add-subtask "<title>"`; track with `sq task 400 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Pre-fenced Mermaid variant of graph_to_mermaid + CLI smoke test | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Pre-fenced Mermaid variant of graph_to_mermaid + CLI smoke test

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — Fenced Mermaid output from sq graph
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Wrap the existing `graph_to_mermaid` output in a ```mermaid fence via a new `mermaid-md` format value (or `--md` flag) in the `graph` command. Serializer unchanged; print with `markup=False`. CLI smoke test asserts the fence lines.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-15T14:30:35Z] Elias Python:
  - Added --format mermaid-md to sq graph: wraps graph_to_mermaid output in a ```mermaid fence, printed markup=False/highlight=False. Serializer untouched.
  - Tests: tests/cli/test_graph_command_cli.py — fence-lines smoke test + an invalid --format rejection test. No golden churn.
<!-- sq:discussion:end -->
