---
id: EPIC-316
sequence_id: 316
type: epic
title: Shared team knowledge — agent memory and the bulletin board
status: Done
author: product-owner
created_at: '2026-07-06T16:08:36Z'
updated_at: '2026-07-15T11:09:25Z'
---
<!-- sq:body -->
# Shared team knowledge

Two complementary, lighter-than-item surfaces that give a squad a durable, shared home for the
knowledge that today either lives locally in an agent's per-machine memory or gets lost in the noise
of a formal repo intro and long item discussions:

- **Agent memory** — a per-role, committed notebook of small, *descriptive* facts an agent has
  learned. Each role owns its pool; the index is surfaced at boot so facts don't slip. *What I
  learned.*
- **Bulletin board** — a team-scoped, everyone-reads broadcast of *prescriptive*, usually time-bound
  notices. Cross-cutting facts live here once rather than duplicated into every role's memory. *What
  we all need to know right now.*

The dividing line: **personal-learned → memory; cross-cutting/announcement → board.** Both are
committed to the repo (so knowledge travels with the project and across teammates), both sit off the
global counter and outside `.squads.json`, and both are lighter tiers than items — see the storage
decision for the shared mechanics.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
