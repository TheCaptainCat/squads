---
id: TASK-807
sequence_id: 807
type: task
title: sq graph traverses undeclared-kind edges instead of dropping them
status: Done
parent: FEAT-790
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-775:implements
- BUG-804:fixes
- TASK-797:depends-on
description: Stop sq graph silently dropping an edge whose kind the merged spec does
  not declare; it traverses and reports a null semantic
subentities:
- local_id: ST1
  title: Split the declared-vocabulary drop from the --kind filter
  status: Done
  story: US2
- local_id: ST2
  title: Emit a null semantic and hold the four surfaces in agreement
  status: Done
  story: US2
created_at: '2026-08-25T15:57:21Z'
updated_at: '2026-08-25T23:39:53Z'
---
<!-- sq:body -->
## Scope

ADR-775 amendment A3's closing clause, on FEAT-790 US2. `sq graph` silently deletes any edge whose
kind the merged spec does not declare, while two other surfaces answer the same question
differently.

`_out_neighbours` and `_in_neighbours` (`_services/_refs.py:60-120`) both do:

```
kind = kind or ctx.spec.default_ref_kind()
if kind not in ctx.kinds:
    continue
```

Three surfaces, three answers to one question: `refs --in`/`--all` list the edge under its stale
name, `sq check` warns on it, `sq graph` deletes it with no signal — not an error, not a note in
the output, just absent.

**This needs no legacy fold to reach.** Any undeclared-kind edge does: one arriving from an
import, from a git merge, or authored before a `[selected]` deselect dropped the kind. The
vocabulary becoming renameable and deselectable is what makes a previously-valid edge reachable
here, which is why it surfaces now.

## The shape is ruled, not open

A3 settles it so it does not reopen as a design question: **`sq graph` answers what is connected
to an item, so it may not omit an edge it can see.** An undeclared-kind edge traverses, and its
node reports no declared semantic in the `edge_semantic` key A2 adds. Absence of a declaration is
a value to emit, never grounds to delete the node.

## The trap: `ctx.kinds` is doing two jobs

`_TraversalCtx.kinds` is documented as "effective filter; declared entries of `spec.ref_kinds`",
and it is built in `graph()` as `effective_kinds = declared_kinds` when the caller passes no
`--kind`, or the caller's requested set otherwise (with `unknown = kinds - declared_kinds`
refused up front).

So the single `if kind not in ctx.kinds: continue` serves **two purposes at once**:

1. honouring an explicit `--kind` filter — legitimate, and must keep working exactly as it does;
2. dropping edges whose kind is not declared — the defect.

Removing the `continue` outright would silently break `--kind` filtering. Separate the two: the
declared set is a lookup for resolving an edge's semantic, never a gate on whether the edge is
seen; the requested set stays a gate. A test must cover both halves, because the naive fix passes
the new case and regresses the old one.

Residue worth knowing rather than fixing here: because `graph --kind` refuses a kind the spec does
not declare, there is no way to filter *to* an undeclared kind. That is consistent with the
refusal shape everywhere else and is not in scope.

## Sequencing

Depends on TASK-797, which introduces `edge_semantic` under A2 — an undeclared-kind edge's node
reports `null` there, so the field has to exist before this can emit it. It also converts the
`kind == "blocks"` / `"depends-on"` literals in these same two functions, so the two must not run
concurrently on `_services/_refs.py`.

Separate from TASK-806 by A3's own ruling: that one enforces an on-disk encoding invariant, this
one fixes a consumer that drops what it can see. Neither subsumes the other — TASK-806 stops the
stale spelling being created, and this stops an edge already carrying one from vanishing.

## Acceptance

- An edge whose kind the merged spec does not declare appears in `sq graph` traversal, in both
  directions, in the Rich tree and in `--json`.
- Its node carries `edge_semantic: null` and its `edge_kind` is the stored spelling, so a consumer
  can tell a declared navigational kind from an undeclared one without guessing.
- `graph --kind <declared>` still filters to exactly the requested kinds, and an edge of another
  kind — declared or not — is excluded.
- `graph --kind` still refuses a kind the merged spec does not declare, naming the accepted set.
- Across a default-kind rename, a legacy-spelled edge and a natively bare edge to the same target
  both appear, and `refs --in`, `refs --all`, `graph --json` and `sq check` agree on which edges
  exist.
- Nothing is reported twice: an item authored with both dependency spellings still dedupes to one
  edge.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite are clean; `sq check` is clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 807 add-subtask "<title>"`; track with `sq task 807 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Split the declared-vocabulary drop from the --kind filter

<!-- sq:subtask:ST1:body -->
`_TraversalCtx.kinds` is doing two jobs at once, and the single
`if kind not in ctx.kinds: continue` in both `_out_neighbours` and `_in_neighbours` conflates them:

1. honouring an explicit `graph --kind` filter — legitimate, and must keep working unchanged;
2. dropping any edge whose kind the merged spec does not declare — the defect.

`graph()` builds `effective_kinds = declared_kinds` when the caller passes no `--kind`, and the
caller's requested set otherwise (with `unknown = kinds - declared_kinds` refused up front). So
with no filter, "not requested" and "not declared" are the same frozenset and cannot be told apart
at the traversal site.

Separate them. The declared set becomes a lookup used to resolve an edge's semantic, never a gate
on whether the edge is seen; the requested set stays a gate. An undeclared-kind edge traverses in
both directions when no `--kind` filter is given.

Removing the `continue` outright passes the new case and silently breaks `--kind` filtering, so
cover both halves: a filtered traversal still returns exactly the requested kinds, and an
unfiltered one returns the undeclared edge too.

Keep the dependency-pair dedupe intact — an item authored with both spellings still collapses to
one edge.

Done when an undeclared-kind edge appears in an unfiltered traversal in both directions, and
`graph --kind <declared>` filters exactly as it does today.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Emit a null semantic and hold the four surfaces in agreement

<!-- sq:subtask:ST2:body -->
An undeclared-kind edge's node reports **no declared semantic**: `edge_semantic: null`, the key
A2 adds and TASK-797 introduces. Its `edge_kind` is the stored spelling, so a consumer can tell a
declared navigational kind from an undeclared one without guessing — both have no semantic, and
only the spelling distinguishes them.

Absence of a declaration is a value to emit, never grounds to delete the node. Do not invent a
third state, a warning row, or an `undeclared: true` flag — `edge_semantic: null` plus the stored
`edge_kind` is the whole contract, and the `--json` docstring states it.

The `--json` docstring already has to state both `edge_kind` and `edge_semantic` and which one to
branch on; extend it to say that a `null` semantic covers both a navigational kind and one the
merged spec does not declare.

**Assert the four surfaces agree**, because this defect was three surfaces answering one question
three ways. Across a default-kind rename, a legacy-spelled edge and a natively bare edge to the
same target: both appear in `refs --in`, both in `refs --all`, both in `graph --json`, and
`sq check`'s findings match what the other three show exists. Assert them in one test rather than
three, so a future divergence fails as a disagreement rather than as three independently-passing
tests.

Done when an undeclared-kind edge carries `edge_semantic: null` and its stored spelling, the
docstring covers the null case, and one test holds the four surfaces in agreement.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-25T16:00:37Z] Olivia Lead:
  - Scoped from ADR-775 A3 closing clause. Parented to FEAT-790 and mapped to US2 - the graph traversal filter is engine behaviour keyed on the declared set, and US2 is where edge_semantic lands. Kept separate from TASK-806 by A3 own routing: 806 stops a stale spelling being created, this stops an edge already carrying one from vanishing. Neither subsumes the other.
  - One trap I found by reading that A3 does not mention, written into ST1: _TraversalCtx.kinds is doing two jobs. graph() sets effective_kinds = declared_kinds when no --kind is passed, so at the traversal site "not requested" and "not declared" are the same frozenset. The single "if kind not in ctx.kinds: continue" is therefore both the legitimate --kind filter and the defect. Removing it outright passes the new case and silently breaks --kind filtering, so both halves need a test.
- [2026-08-25T20:42:30Z] Elias Python:
  - Separated the two jobs _TraversalCtx.kinds conflated: renamed to requested_kinds: frozenset[str] | None. None (no --kind) means no filter at all — every edge traverses, declared or not; a caller-supplied set is still the same gate as before (unknown kinds refused up front in graph()).
  - The two gate lines in _out_neighbours/_in_neighbours became 'if ctx.requested_kinds is not None and kind not in ctx.requested_kinds: continue' — the declared vocabulary is now consulted only in _edge_semantic (already null-safe for an undeclared kind via spec.ref_kinds.get) and never gates visibility.
  - Extended the GraphNode/edge_semantic and --json docstrings per ST2: null now documented as covering both a navigational kind and an undeclared one, distinguishable only via edge_kind's stored spelling.
  - Tests (tests/service/test_graph_traversal.py): test_an_undeclared_kind_edge_traverses_with_a_null_semantic_in_both_directions (an edge planted with an undeclared kind now appears out and in, edge_kind='banana', edge_semantic=None); test_kind_filter_still_gates_exactly_the_requested_kinds_declared_or_not (table: unfiltered sees a declared+another declared+undeclared edge, --kind={related} still excludes both the other declared kind and the undeclared one); test_undeclared_kind_edge_agrees_across_refs_and_check_after_a_default_kind_rename (BUG-804's scenario: a pre-rename stale-spelled edge and a post-rename native bare edge to the same target agree across refs_out/refs_in/graph/check).
  - No golden moved (docstring-only changes to the --json contract prose, not its shape); targeted: tests/service/test_graph_traversal.py (18 passed), plus test_ref_kinds_are_declared_spec_vocabulary.py, test_graph_command_cli.py, test_check_ref_kind_and_supersedes_warnings.py, tests/meta all green. pyright/ruff check/ruff format clean, sq check clean. Nothing left undone against ST1/ST2.
<!-- sq:discussion:end -->
