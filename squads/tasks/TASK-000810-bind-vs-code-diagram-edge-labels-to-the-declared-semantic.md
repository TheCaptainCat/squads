---
id: TASK-810
sequence_id: 810
type: task
title: Bind VS Code diagram edge labels to the declared semantic
status: Done
parent: FEAT-790
author: tech-lead
assignee: typescript-dev
priority: low
refs:
- ADR-775:implements
- REV-808:addresses
- TASK-797:depends-on
description: Convert the VS Code client's graph edge labelling from a literal kind
  name to the declared semantic, and cover it in the client's own suite
subentities:
- local_id: ST1
  title: Branch edge labelling on the declared semantic
  status: Done
  story: US2
- local_id: ST2
  title: Client-side coverage for the semantic edge binding
  status: Done
  story: US2
created_at: '2026-08-25T17:56:43Z'
updated_at: '2026-08-25T23:39:57Z'
---
<!-- sq:body -->
## Scope

ADR-775 §2 and amendment A2, on FEAT-790 US2 — the client half of binding ref-kind behaviour to
a declared semantic instead of a spelling.

`clients/vscode/src/domain/graphDiagrams.ts:130-134` (verified) decides an edge's display label
by comparing the kind against a literal:

```
function edgeLabel(edgeKind: string, direction: 'in' | 'out'): string {
  if (edgeKind === 'depends-on') {
    return direction === 'out' ? 'depends on' : 'required by';
  }
  return edgeKind;
}
```

and its docstring above (`:120-129`) states the literal as the contract. Under a project that
renames its dependency kind, the diagram silently drops the direction-aware label and prints the
raw key in both directions. This is the declared-but-found-by-literal shape ADR-775 §2 removes
from the engine — and A2 added `edge_semantic` to the graph JSON precisely because "emitting
only the spelling would leave every agent testing `edge_kind == 'depends-on'`". A client is one
of those consumers.

## Why this is its own item and not a line in the engine conversion

Two reasons, and only the second is about scope.

- **The owner differs.** This is TypeScript in `clients/vscode/`, with its own toolchain,
  type-aware lint gate and test suite. The engine conversion's acceptance is the Python gate and
  does not reach here.
- **The anti-drift mechanism cannot reach it.** The engine conversion's guard is a `tests/meta`
  AST scan over `src/squads/`, which is a Python parser walking Python files. It is not that
  this call site was left out of a list — it is outside the mechanism by construction, and will
  still be here after that scan passes clean.

## The conversion

`SqGraphNode` (`clients/vscode/src/types.ts:34-43`) carries `edge_kind: string | null` and
`direction`. A2 adds `edge_semantic` — the edge kind's declared semantic role, or null for a
navigational kind — and that is the field a consumer branches on. `edge_kind` keeps emitting a
declared kind key, which is what the label falls back to and what the display shows.

So: branch on the semantic, render from the spelling.

**The client already has this exact pattern and it is the model to follow.**
`clients/vscode/src/domain/statusRole.ts` resolves a status's behaviour through its declared
role rather than a literal status name, and stays defensive about values it does not recognise
(`toColorIntent` falls back rather than breaking rendering). Do the same here: an edge whose
semantic the client does not recognise renders its spelling, exactly as today's fallback branch
does.

The type guard `isSqGraphNode` (`clients/vscode/src/sqAdapter.ts:156-172`) validates
`edge_kind`; the new field needs the same treatment, and must tolerate its absence rather than
reject the node — the client is expected to run against a squads CLI that predates the field.

## Dependency

This cannot land before `edge_semantic` exists on `sq graph --json`, which the engine
conversion ships. Until then there is nothing to branch on. Recorded as a `depends-on` ref.

## Traps

- **Do not re-derive the semantic client-side** by matching the kind key against a list the
  client holds. That is the same defect one layer down.
- **The two exports must keep reading the same way.** The docstring at `:120-129` ties this
  label convention to the core CLI's `graph_to_mermaid`, so if the engine's label branch changes
  shape, this one follows it rather than diverging.
- **The docstring is part of the change.** It currently states the literal as the contract; it
  has to state the semantic instead, or it re-teaches the defect to the next reader.

## Acceptance

- `edgeLabel` decides direction-aware labelling from the edge's declared semantic, and no
  literal kind name appears in the branch.
- A graph node whose dependency kind is named something other than the bundled spelling still
  renders "depends on" / "required by" in the right directions.
- A navigational kind, and a semantic the client does not recognise, both render the kind's
  spelling as they do today.
- `isSqGraphNode` accepts a node with the new field, and accepts one without it rather than
  rejecting the whole graph.
- `clients/vscode/test/graphDiagrams.test.ts` covers the renamed-kind case, the navigational
  case and the missing-field case.
- The docstring above `edgeLabel` states the semantic binding rather than naming a kind as the
  contract.
- The client's own lint, type-check and test gates are clean; `sq check` is clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 810 add-subtask "<title>"`; track with `sq task 810 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Branch edge labelling on the declared semantic | US2 |
| ST2 | Done |  | Client-side coverage for the semantic edge binding | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Branch edge labelling on the declared semantic

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US2 — Bind engine behaviour to declared semantics, not literals
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Convert `edgeLabel` (`clients/vscode/src/domain/graphDiagrams.ts:130-134`) to branch on the
edge's declared semantic instead of comparing the kind to `'depends-on'`, and rewrite the
docstring above it (`:120-129`), which currently states the literal as the contract.

`SqGraphNode` gains `edge_semantic` — the declared semantic role, or null for a navigational
kind. Branch on that; render from `edge_kind`, which keeps emitting a declared kind key so a
project sees its own spelling.

Follow `clients/vscode/src/domain/statusRole.ts`, which already does exactly this for statuses:
resolve behaviour through the declared role, and stay defensive about values the client does not
recognise rather than breaking rendering. An edge whose semantic is unrecognised renders its
spelling, the way today's fallback branch does.

Update the type in `clients/vscode/src/types.ts:34-43` and the guard `isSqGraphNode`
(`clients/vscode/src/sqAdapter.ts:156-172`). The guard must **tolerate the field's absence**
rather than reject the node: the client is expected to run against a squads CLI that predates
it.

Do not re-derive the semantic client-side by matching the kind key against a list the client
holds — that is the same defect one layer down.

Done when a renamed dependency kind still renders "depends on" / "required by" in the right
directions, a navigational and an unrecognised kind render their spelling, the guard accepts a
node with and without the field, and no literal kind name appears in the branch.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Client-side coverage for the semantic edge binding

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — Bind engine behaviour to declared semantics, not literals
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Cover the conversion in `clients/vscode/test/graphDiagrams.test.ts`, in the client's own suite,
because the engine's anti-drift guard cannot reach this file.

That guard is a `tests/meta` AST scan over `src/squads/` — a Python parser over Python files.
This call site is outside it by construction, not by omission, and will still be outside it when
that scan passes clean. Whatever keeps this binding honest has to live in the client's own
toolchain.

Cases:

- a dependency edge whose kind is named something other than the bundled spelling, in both
  directions, rendering the direction-aware labels;
- a navigational edge, rendering its spelling;
- an edge carrying a semantic the client does not recognise, rendering its spelling rather than
  throwing or blanking;
- a node with the field absent, accepted by the type guard.

Keep the two exports reading the same way: the label convention here is tied to the core CLI's
`graph_to_mermaid` by the docstring above `edgeLabel`, so the assertions should describe the
shared convention rather than a client-only one.

Done when all four cases are covered and the client's lint, type-check and test gates are clean.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-25T18:00:53Z] Olivia Lead:
  - Authored from REV-808 F8. Verified the citation: edgeLabel at clients/vscode/src/domain/graphDiagrams.ts:130-134 compares the kind against the literal depends-on, and the docstring above it at :120-129 states that literal as the contract; the call site is :159.
  - Why a separate task rather than a line in TASK-797 scope. The owner role differs - typescript-dev, a different toolchain and gate, and 797 acceptance is the Python gate. And 797 anti-drift mechanism is a tests/meta AST scan over src/squads, a Python parser over Python files: this call site is outside it by construction, not by omission, and will still be there when that scan passes clean. Adding a scan root cannot reach TypeScript.
  - Depends-on TASK-797: there is nothing to branch on until edge_semantic ships on sq graph --json (ADR-775 A2). Low priority, and it should land right behind 797 rather than drifting.
  - The client already has the pattern to copy - clients/vscode/src/domain/statusRole.ts resolves a status through its declared role rather than a literal name, with a defensive fallback for values it does not recognise. @typescript-dev that file is the model, not a fresh design.
- [2026-08-25T21:14:26Z] Ada Typescript:
  - edgeLabel now branches on node.edge_semantic === 'dependency' (fallback null via ?? for an sq predating the field); edge_kind is only ever rendered, never compared. Docstring above edgeLabel restates the semantic binding.
  - SqGraphNode.edge_semantic added as string|null, optional; isSqGraphNode tolerates absence.
  - Verified against this squad's own sq graph --json: FEAT-790's related edges report edge_semantic: default (not one of dependency/preload/supersession/null) - confirmed the client only special-cases 'dependency' and falls through to spelling for anything else, same as the core CLI's _collect_edges.
  - graphDiagrams.test.ts: renamed dependency kind (both directions), navigational edge, unrecognised-semantic edge (preload/supersession/default), and edge_semantic-absent node accepted by isSqGraphNode. Reverting edgeLabel to the literal 'depends-on' check locally reproduces exactly one failure in the renamed-kind test; restored after confirming.
  - Gates: npm run check (typecheck+lint+format:check) clean; npm test 618/618; npm run test:canary 19/19 against live sq. No changes outside clients/vscode/.
<!-- sq:discussion:end -->
