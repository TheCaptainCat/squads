---
id: FEAT-000037
sequence_id: 37
type: feature
title: 'Ref graph view: sq graph <item>'
status: Done
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
  title: Depth-bounded dependency tree for one item before greenlighting
  status: Todo
- local_id: US2
  title: Filter graph by kind and direction to pull only relevant context
  status: Todo
- local_id: US3
  title: dot/mermaid export for full-graph rendering outside the terminal
  status: Todo
created_at: '2026-06-11T07:45:02Z'
updated_at: '2026-06-24T12:26:00Z'
---
<!-- sq:body -->
## Problem

The squad is a graph — parent edges, typed refs, computed backrefs — but every
view of it is either one hop (`sq <type> <n> refs`) or one dimension (`sq tree`
walks parents only; `sq blocked` reads one kind, flat). There is no way to ask the
questions a connected backlog raises constantly: *what does this item
transitively wait on? what leans on it? what context travels with it?* The full
graph is not the answer — even our own young backlog would render as noise in a
terminal.

## Value

`sq graph <item>` makes the ref web navigable where people actually stand: on one
item. Operators sequence greenlights from it, the manager briefs from it, agents
discover the context an item carries without spelunking. The deliberate *non-goal*
— rendering the whole graph in the terminal — gets its escape hatch instead: an
export to standard formats, rendered by tools built for it (and someday by `sq ui`
/ `sq web`, natural consumers of the same traversal).

## Scope

 - `sq graph <id|number>` — breadth-first traversal of ref edges from the item,
   rendered as an indented tree with each node's status/priority badge and the
   edge label on the branch. Bare numbers per FEAT-000019's resolver.
 - `--depth N` (default 2) — the up-until-a-given-depth cutoff.
 - `--kind <k>` (repeatable) — only follow these kinds; default all. `--direction
   out|in|both` (default both) — forward refs, backrefs, or the merged view.
 - **Dependency edge labels — two-way binding.** `depends-on` and `blocks` are two
   spellings of the same dependency (FEAT-000035's equivalence). In the graph tree
   they collapse to ONE uniform pair of human-readable labels, regardless of which
   item authored the edge:
   - The item on the *depending* end (the one that cannot proceed) is labelled
     **"depends on"**.
   - The item on the *blocking* end (the one being waited on) is labelled
     **"required by"**.
   So whether the edge on disk is `A depends-on B` or `B blocks A`, the tree
   always reads: A → "depends on" → B, and B → "required by" → A. The raw kind
   string (`depends-on` / `blocks`) is never shown for dependency edges.
 - **Symmetric and other edge labels.** For kinds where both ends are
   interchangeable (`related`, `duplicates`, `implements`, `fixes`, `addresses`,
   `supersedes`) the edge label is the kind name itself (e.g. "related to",
   "implements", "fixes"). Direction is implicit in traversal direction.
 - **Graph honesty**: refs may cycle — revisited nodes render once and mark `(seen)`,
   traversal never recurses into them. Closed items hidden by default; `--all`
   includes them.
 - `--json` (joins FEAT-000015's frozen shapes) and `--format dot|mermaid` for the
   full or filtered graph — the terminal stays ego-centric; the export is how
   you get the big picture.
 - Out of scope: traversing *parent* edges (that's `sq tree`); any interactive
   navigation (that's EPIC-000028's TUI, which should reuse this traversal).

## Acceptance

 - `sq graph 23` (depth 2, both directions) shows nodes with status/priority badges
   and edge labels; depth/kind/direction filters behave.
 - **Dependency label normalization:** given items A and B where `A depends-on B` is
   authored on A, the tree shows the label "depends on" from A's side and "required
   by" from B's side. Given items C and D where `C blocks D` is authored on C, the
   tree shows the same labels — "depends on" from D's side, "required by" from C's
   side. A `blocks` edge and a `depends-on` edge between the same two items must
   render identically in the tree (same label pair), verified with mixed-authorship
   fixtures.
 - The raw kind strings `depends-on` and `blocks` never appear as branch labels in
   tree output; they are always surfaced through the human-readable pair.
 - `related` and all other non-dependency kinds display the kind name as the branch
   label (not "in" / "out").
 - Cycles terminate with `(seen)` markers; closed items appear only with `--all`.
 - `--json` shape documented + golden-tested; `--format dot` output renders in
   graphviz untouched.
 - Traversal lives in the service layer (one implementation for CLI now, TUI/web
   later).
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 37 add-story "As a <role>, I want … so that …"`; track with `sq feature 37 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Depth-bounded dependency tree for one item before greenlighting |
| US2 | Todo |  | Filter graph by kind and direction to pull only relevant context |
| US3 | Todo |  | dot/mermaid export for full-graph rendering outside the terminal |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Depth-bounded dependency tree for one item before greenlighting

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As an operator sequencing work, I want the dependency tree of one item to a chosen depth, so that I can see what it waits on and what waits on it before greenlighting.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Filter graph by kind and direction to pull only relevant context

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As an agent briefing on an item, I want to filter the graph by kind and direction, so that I pull only the context that matters for my job.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — dot/mermaid export for full-graph rendering outside the terminal

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As a user wanting the big picture, I want a dot/mermaid export, so that the full graph renders in tools made for it instead of flooding my terminal.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-23T14:05:00Z] Olivia Lead:
  - Broke this down into TASK-000182 (Ready). One task, one subtask per story: ST1/US1 = depth-bounded BFS traversal in the service layer (RefsMixin.graph -> GraphNode), reusing the existing blocked() depends-on/blocks equivalence, with seen-marker cycle handling and closed-hidden-by-default; ST2/US2 = --kind (repeatable) + --direction out|in|both filters threaded through the one service method; ST3/US3 = --format dot|mermaid export of the same traversed graph.
  - Key constraint: the traversal is ONE service-layer implementation (in _services/_refs.py) so the TUI/web can reuse it later; the CLI graph command in _cli/_main.py is a thin Rich/JSON/export edge mirroring how tree is built. JSON shape is specified in the task body and must be golden-tested (FEAT-000015); normalization must be proven with mixed-authorship fixtures. @python-dev please pick up TASK-000182 — full module-by-module plan and acceptance mapping are in the task body.
- [2026-06-23T16:01:09Z] Catherine Manager:
  - First implementation attempt (TASK-000182) reverted and restarted. Recording the requirement clarification for the record: the depends-on/blocks normalization in Scope/Acceptance is mandatory — both spellings must render as ONE uniform dependency arrow (FEAT-000035 equivalence), not as distinct literal kinds. This was the gap that triggered the restart. Everything else in the first pass (BFS depth bound, kind/direction filters, cycle (seen) handling, closed-hiding, --json, dot/mermaid export) was sound and can be rebuilt the same way.
- [2026-06-23T16:35:45Z] Pierre Chat:
  - Tested the first pass briefly and didn't like the raw 'in/out' direction wording for dependency edges. Proposal: present the dependency relationship as a two-way binding with human labels instead — my starting suggestion is 'depends on' (this item depends on the other) and 'depended by' (the other depends on this one). This is also the normalization: a depends-on edge and a blocks edge are the same dependency, just authored from opposite ends, so they should read with this one pair of labels.
  - For symmetric refs like 'relates', keep in/out — both sides read identically so it doesn't matter.
  - English isn't my native language, so the product owner should feel free to propose better wording than 'depends on / depended by' — I care about the two-way-binding behaviour, not the exact words.
- [2026-06-23T16:37:16Z] Nina Product:
  - Wording decision — dependency edge labels for sq graph.
  - Pierre flagged 'in/out' as too raw for dependency edges and asked for human-readable two-way-binding labels. My proposal (and the new canonical wording in the Acceptance criteria): **'depends on'** for the dependent end and **'required by'** for the blocking end. Rationale: 'depends on' matches the kind name and is unambiguous; 'required by' is standard English used across package managers (apt, npm, conda) and reads naturally in a tree branch — it is shorter and more idiomatic than Pierre's draft 'depended by'.
  - Normalization: 'depends-on' and 'blocks' are two spellings of the same dependency (FEAT-000035). Both collapse to this one label pair — 'depends on' / 'required by' — regardless of which item authored the edge. The raw kind strings never appear as branch labels in tree output.
  - Symmetric kinds ('related', 'duplicates', 'implements', 'fixes', 'addresses', 'supersedes'): the edge label is the kind name itself. No 'in/out' raw direction labels for any kind.
  - @op-pierre — please confirm this label pair works for you. If you prefer different words the Acceptance criteria are easy to update before the build restarts.
  - @tech-lead and @python-dev — Acceptance criteria on FEAT-000037 have changed. The key testable requirement is: a blocks edge and a depends-on edge between the same two items must render with the same label pair ('depends on' / 'required by'), verified with mixed-authorship fixtures. The raw kind strings must never appear as branch labels.
- [2026-06-23T16:45:14Z] Pierre Chat:
  - Confirmed — happy with both: 'depends on' / 'required by' for the dependency two-way binding, and dropping 'in/out' entirely (symmetric kinds shown by their kind name). Thanks Nina, the wording is better than mine. Good to implement.
<!-- sq:discussion:end -->
