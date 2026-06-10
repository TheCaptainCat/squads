---
id: FEAT-000037
sequence_id: 37
type: feature
title: 'Ref graph view: sq graph <item>'
status: Draft
parent: EPIC-000038
author: product-owner
priority: medium
refs:
- FEAT-000035:depends-on
- FEAT-000019:depends-on
- FEAT-000015
description: 'An ego-centric graph command: walk the ref edges from one item to a
  given depth, filtered by kind and direction, rendered as a tree — plus dot/mermaid
  export for the full picture'
subentities:
- local_id: US1
  title: As an operator sequencing work, I want the dependency tree of one item to
    a chosen depth, so that I can see what it waits on and what waits on it before
    greenlighting
  status: Todo
- local_id: US2
  title: As an agent briefing on an item, I want to filter the graph by kind and direction,
    so that I pull only the context that matters for my job
  status: Todo
- local_id: US3
  title: As a user wanting the big picture, I want a dot/mermaid export, so that the
    full graph renders in tools made for it instead of flooding my terminal
  status: Todo
created_at: '2026-06-11T07:45:02Z'
updated_at: '2026-06-11T07:57:11Z'
---
<!-- sq:body -->
## Problem

The squad is a graph — parent edges, typed refs, computed backrefs — but every view of it is
either one hop (`sq <type> <n> refs`) or one dimension (`sq tree` walks parents only;
`sq blocked` reads one kind, flat). There is no way to ask the questions a connected backlog
raises constantly: *what does this item transitively wait on? what leans on it? what context
travels with it?* The full graph is not the answer — even our own young backlog would render as
noise in a terminal.

## Value

`sq graph <item>` makes the ref web navigable where people actually stand: on one item. Operators
sequence greenlights from it, the manager briefs from it, agents discover the context an item
carries without spelunking. The deliberate *non-goal* — rendering the whole graph in the
terminal — gets its escape hatch instead: an export to standard formats, rendered by tools built
for it (and someday by `sq ui` / `sq web`, natural consumers of the same traversal).

## Scope

- **`sq graph <id|number>`** — breadth-first traversal of ref edges from the item, rendered as an
  indented tree with each node's status/priority badge and the edge kind on the branch. Bare
  numbers per FEAT-000019's resolver.
- **`--depth N`** (default 2) — the up-until-a-given-depth cutoff.
- **`--kind <k>`** (repeatable) — only follow these kinds; default all. `--direction out|in|both`
  (default both) — forward refs, backrefs, or the merged view.
- **Dependency normalization**: `A depends-on B` and `B blocks A` draw as the same arrow
  (FEAT-000035's equivalence), so a dependency tree reads uniformly regardless of which side
  authored the edge.
- **Graph honesty**: refs may cycle — revisited nodes render once and mark `(seen)`, traversal
  never recurses into them. Closed items hidden by default; `--all` includes them.
- **`--json`** (joins FEAT-000015's frozen shapes) and **`--format dot|mermaid`** for the full
  or filtered graph — the terminal stays ego-centric; the export is how you get the big picture.
- Out of scope: traversing *parent* edges (that's `sq tree`); any interactive navigation (that's
  EPIC-000028's TUI, which should reuse this traversal).

## Acceptance

- `sq graph 23` (depth 2, both directions) shows e.g. BUG-000022 via depends-on and any
  backrefs, with kinds labelled and statuses shown; depth/kind/direction filters behave.
- depends-on/blocks normalization verified with mixed-authorship fixtures.
- Cycles terminate with `(seen)` markers; closed items appear only with `--all`.
- `--json` shape documented + golden-tested; `--format dot` output renders in graphviz untouched.
- Traversal lives in the service layer (one implementation for CLI now, TUI/web later).
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 37 add-story "As a <role>, I want … so that …"`; track with `sq feature 37 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As an operator sequencing work, I want the dependency tree of one item to a chosen depth, so that I can see what it waits on and what waits on it before greenlighting |
| US2 | Todo |  | As an agent briefing on an item, I want to filter the graph by kind and direction, so that I pull only the context that matters for my job |
| US3 | Todo |  | As a user wanting the big picture, I want a dot/mermaid export, so that the full graph renders in tools made for it instead of flooding my terminal |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As an operator sequencing work, I want the dependency tree of one item to a chosen depth, so that I can see what it waits on and what waits on it before greenlighting

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
**Acceptance:** sq graph <item> --depth N walks both directions by default, labels edge kinds, badges status/priority per node, normalizes depends-on/blocks into one arrow, and marks revisited nodes (seen).
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As an agent briefing on an item, I want to filter the graph by kind and direction, so that I pull only the context that matters for my job

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
**Acceptance:** --kind (repeatable) and --direction out|in|both restrict traversal; defaults are all kinds, both directions, depth 2; closed items need --all.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As a user wanting the big picture, I want a dot/mermaid export, so that the full graph renders in tools made for it instead of flooding my terminal

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
**Acceptance:** --format dot|mermaid emits the filtered graph in valid syntax (graphviz/mermaid render untouched); --json is documented and golden-tested per FEAT-000015.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
