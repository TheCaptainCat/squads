---
id: FEAT-377
sequence_id: 377
type: feature
title: Inline Mermaid diagrams across sq markdown surfaces
status: Done
author: product-owner
subentities:
- local_id: US1
  title: Fenced Mermaid output from sq graph
  status: Done
- local_id: US2
  title: Derived per-item Mermaid graph section in the item dossier
  status: Cancelled
- local_id: US3
  title: Spec-derived Mermaid diagrams in docs and the workflow cheatsheet
  status: Done
created_at: '2026-07-10T09:04:53Z'
updated_at: '2026-07-15T14:45:04Z'
---
<!-- sq:body -->
VSCode, GitHub, PyCharm etc. already render a fenced ```mermaid block inline in any .md file. sq graph --format mermaid already emits a valid Mermaid graph body (graph_to_mermaid in _services/_refs.py) but it's raw, meant for piping to mmdc or pasting into Mermaid Live — not wrapped in a markdown fence. Wrapping that existing serializer in a fence, and reusing it in a couple more places, gets us free inline diagrams across sq's generated markdown with no new rendering engine.

Three independent slices (op-pierre approved, backlog priority — this is post-FEAT-231 work, not scheduled now):
1. Markdown-fenced sq graph output — smallest slice, wraps the existing serializer.
2. A derived per-item :graph section in the item dossier, following the same managed-region/marker precedent as the sub-entity summary table (_discussion.build_block / render_summary). This one touches the managed-region and marker-safety invariants directly (frontmatter is source of truth, body is marker-safe-edit-only) — flag for an architect design pass, possibly an ADR, before implementation.
3. Spec-derived diagrams (item-type hierarchy + per-type lifecycle state machines) embedded in docs/ and/or the workflow cheatsheet. Vocabulary is fully spec-driven now (EPIC-325/EPIC-335), so these must derive from the active spec, not hardcoded types — ties into the FEAT-334 cheatsheet work.

No implementation in this drafting pass — feature stays Draft, no tasks created.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 377 add-story "As a <role>, I want … so that …"`; track with `sq feature 377 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | Fenced Mermaid output from sq graph |
| US2 | Cancelled |  | Derived per-item Mermaid graph section in the item dossier |
| US3 | Done |  | Spec-derived Mermaid diagrams in docs and the workflow cheatsheet |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Fenced Mermaid output from sq graph

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As an operator, I want sq graph output already wrapped in a ```mermaid fence so I can drop it straight into a doc, PR description, or issue and have it render inline — no manual fencing.

Acceptance:
- A way to get the existing graph_to_mermaid output pre-fenced (e.g. --md/--markdown flag, or a 'mermaid-md' format value alongside dot/mermaid).
- Underlying graph serialization unchanged; this only wraps the existing output.
- Covered by a CLI smoke test asserting the fence lines are present.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Derived per-item Mermaid graph section in the item dossier

<!-- sq:story:US2:head -->
**Status:** ⚫ Cancelled
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As anyone opening an item's .md file in VSCode/GitHub, I want a derived :graph section showing that item's dependency/subtree shape as fenced Mermaid, so the shape renders inline without running sq.

Acceptance:
- A new sq-managed marker region (analogous to the sub-entity :summary block built by _discussion.build_block/render_summary) holding fenced Mermaid derived from the item's refs/subtree.
- Purely derived + regenerated on mutation, like the existing :head/:summary regions — never hand-edited, nothing new stored in frontmatter (frontmatter stays the source of truth; the section is rebuilt from it).

Open design question — flag before implementation: this is the slice most likely to need an architect design pass (possibly an ADR) given it's a new managed-region kind on every item file, not just sub-entities — needs a call on placement, refresh triggers, and blast radius on existing templates before a task is cut.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Spec-derived Mermaid diagrams in docs and the workflow cheatsheet

<!-- sq:story:US3:head -->
**Status:** 🟢 Done
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As a contributor reading docs/ or the workflow cheatsheet, I want auto-generated Mermaid diagrams of the item-type hierarchy and per-type lifecycle state machines, so the docs show the shape of the spec instead of just prose describing it.

Acceptance:
- Diagrams are generated from the active spec (item-type parent/child hierarchy, per-type status machine from _workflow.py), not hardcoded — must stay correct for a customized vocab (spec-driven per EPIC-325/EPIC-335), same discipline as FEAT-334's cheatsheet genericization.
- Embedded as fenced Mermaid in docs/ and/or workflow.md.j2 (open question for op-pierre: which surface(s) — see feature comment).
- Regenerated by sq sync like other generated/managed content, not hand-authored.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-10T09:05:45Z] Pierre Chat:
  - Requested this after noticing VSCode/GitHub render ```mermaid fenced blocks inline — three slices approved: fenced graph output, per-item derived graph section, spec-derived diagrams in docs/cheatsheet. Backlog, drafting only.
- [2026-07-15T13:51:58Z] Pierre Chat:
  - Greenlit for 0.9 — full feature, all three slices including US2 (the per-item derived :graph managed region), which I know needs the architect design pass / possible ADR. Run search (FEAT-318) + full Mermaid together as one loop.
- [2026-07-15T14:00:31Z] Pierre Chat:
  - Cancelled US2 (per-item derived :graph region) per ADR-422. The premise is wrong — a ref graph is non-local (depends on other items' refs/backrefs/open-closed status), so the cheap :summary-style mutation-refresh isn't achievable, every persistence option is flawed, and the value is marginal (most items have 0-2 refs; useful graphs are subtrees). US1's on-demand fenced graph serves that need. Proceeding with US1 + US3 only.
- [2026-07-15T14:43:32Z] Paul Reviewer:
  - Reviewed TASK-424 (fenced sq graph) + TASK-425 (spec-derived diagrams). APPROVED — no findings. US2 correctly out of scope (Cancelled per ADR-422).
  - TASK-424: 'mermaid-md' added as a --format value (single-option surface, per task guidance), wraps graph_to_mermaid in a ```mermaid fence, printed markup=False; serializer untouched; invalid --format rejected. CLI smoke test asserts the fence lines.
  - TASK-425: genuinely spec-driven — hierarchy flowchart from parent_chain/spec.items, per-type stateDiagram-v2 from lifecycle_edges/lifecycle_states_in_order. Verified on a renamed vocab (task->ticket) and a custom lifecycle: real names show, no bundled literal leaks. Determinism handled correctly — helpers BFS from initial over the ordered transition lists and never iterate the Lifecycle.states frozenset, so render is byte-stable (test asserts repeated renders equal; golden stable). mermaid_id sanitizes to [A-Za-z0-9_] with the real name kept as the node label. Degrades to a plain fenced block in the Rich terminal (sq workflow renders, exit 0). ADR-422 honored: workflow.md.j2 only, not docs/; regenerated by sq sync; templates_manifest regenerated.
  - Gates: ruff/pyright/format clean, sq check clean, workflow + golden + agents_md tests green (agents_md/search goldens additive/documented-shape). @tech-lead TASK-424 + TASK-425 verified — clear to close.
<!-- sq:discussion:end -->
