---
id: TASK-70
sequence_id: 70
type: task
title: Write the architecture guide and cross-link it to the retroactive ADRs
status: Done
parent: FEAT-18
author: tech-lead
assignee: architect
priority: medium
subentities:
- local_id: ST1
  title: Draft the architecture guide covering layering, data model, and the marker
    mechanism
  status: Done
  story: US1
- local_id: ST2
  title: Cross-link the guide and the retroactive ADRs both directions with related
    refs
  status: Done
  story: US3
created_at: '2026-06-12T14:18:09Z'
updated_at: '2026-07-06T15:19:04Z'
---
<!-- sq:body -->
Content-only documentation work: zero code changes. Deliverable is ONE sq guide item plus cross-link refs, authored through the CLI. Tech-writer polishes after the architect drafts.

## What to produce

ONE guide item (`sq create guide`) with "architecture" in the title so `sq search architecture` finds it. It covers:

- **The layering** — `_cli` to `_services` to the index store / backends / rendering; models as the shared dependency-free base.
- **The data model** — items, sub-entities (story/subtask/finding state carried on the parent), and the index keyed by sequence number.
- **The marker mechanism** — how managed regions are delimited and edited safely so agent-authored prose is preserved.

Keep it lean and standalone-readable: enough for a new agent or contributor to grasp the system's shape without reading source. Point at `sq docs internals` for the deep version rather than duplicating it.

## Cross-linking (US3)

Once TASK-69's ADRs exist, ref every one of them from this guide plus ADR-49, all `--kind related`, and add the reverse refs so the links go both directions (guide cites ADRs, ADRs cite guide). This is the deliverable for US3.

## Source material

- `CLAUDE.md` (Architecture & layering section).
- `docs/internals.md` and `docs/README.md`.

## Watch for

This is documentation of what IS, not a redesign. No literal sq anchor tags in the guide text. Depends on TASK-69 for the ADR IDs to link — draft the guide prose in parallel, do the cross-link pass after the ADRs land.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 70 add-subtask "<title>"`; track with `sq task 70 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Draft the architecture guide covering layering, data model, and the marker mechanism | US1 |
| ST2 | Done |  | Cross-link the guide and the retroactive ADRs both directions with related refs | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Draft the architecture guide covering layering, data model, and the marker mechanism

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a new agent or contributor, I want an architecture guide readable through sq, so that I understand the system's shape without spelunking through git history
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Draft the single architecture guide item (sq create guide, 'architecture' in the title for searchability) covering the layering (_cli -> _services -> index store/backends/rendering, models as the dependency-free base), the data model (items, sub-entities carried on the parent, index keyed by sequence number), and the marker mechanism for safe managed-region edits. Lean and standalone-readable, pointing at sq docs internals for depth, no literal sq anchor tags (US1).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Cross-link the guide and the retroactive ADRs both directions with related refs

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US3 — As a team member working an item, I want guides and ADRs cross-linked by refs, so that the relevant context travels with the work
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
After TASK-69's ADRs land, cross-link the architecture guide and every retroactive ADR plus ADR-49 in both directions with --kind related refs (guide cites ADRs, ADRs cite guide), delivering US3.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T14:19:09Z] Olivia Lead:
  - @architect this is the guide + cross-link half of FEAT-18 (US1 + US3). ONE guide item with 'architecture' in the title (so sq search architecture finds it): the layering, the data model, the marker mechanism — lean and standalone-readable, pointing at sq docs internals for depth rather than duplicating it. Tech-writer polishes after you draft.
  - US3 is the cross-link pass: ref every TASK-69 ADR plus ADR-49 from the guide and back, all --kind related, both directions. That pass depends on TASK-69 landing for the IDs — draft the prose in parallel, link after. No literal sq anchor tags in the guide text.
<!-- sq:discussion:end -->
