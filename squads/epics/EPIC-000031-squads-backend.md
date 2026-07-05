---
id: EPIC-31
sequence_id: 31
type: epic
title: Squads backend
status: Draft
author: product-owner
description: Umbrella for technical work on the sq engine itself — services, index,
  models, workflow, rendering, agent-backend plumbing — as opposed to product surfaces
  like the CLI grammar, TUI or web
created_at: '2026-06-10T15:21:51Z'
updated_at: '2026-06-10T15:21:51Z'
---
<!-- sq:body -->
## Outcome

The engine under `sq` stays healthy as the product grows: the index store, the service layer, the
models and workflow machinery, the rendering pipeline and the agent-backend plumbing evolve
deliberately — with their own backlog home — instead of riding along as afterthoughts inside
user-facing features.

## What belongs here

Technical features whose user is *the codebase and the team that works on it*, not an end user:

- index & store robustness (locking, atomicity, counter integrity — e.g. the BUG-22 class of
  work), repair/check depth;
- the shared resolver and other cross-cutting service infrastructure;
- model/schema evolution mechanics, migration framework improvements;
- rendering/template engine internals;
- `AgentBackend` ABC and backend-registry plumbing (the *infrastructure* — a concrete new backend
  that users ask for, like AGENTS.md, stays a product feature);
- performance, typing, refactors big enough to deserve a feature rather than a drive-by.

## What doesn't

Anything a user would notice as a capability: CLI grammar and output (Road to 1.0 — EPIC-12),
the TUI (EPIC-28), the web view (EPIC-29). Those epics own their features; this one owns
the ground they stand on. Disambiguation: "backend" here means the sq engine — not `sq web`'s
server, and not only the `_backends/` agent-tool adapters.

## Working agreement

Purely-technical tasks need no feature parent (the workflow allows it) — but when internal work
grows beyond one task, the tech-lead/architect should shape it as a feature under this epic so it
gets stories'-worth of scrutiny and a place in prioritization.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
