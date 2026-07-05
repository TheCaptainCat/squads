---
id: EPIC-136
sequence_id: 136
type: epic
title: Agent backends — management and ecosystem
status: Draft
author: product-owner
refs:
- FEAT-16
- ADR-133
description: 'Post-1.0 umbrella: manage, switch, and grow the ecosystem of agent backends
  on a live squad'
created_at: '2026-06-15T18:23:19Z'
updated_at: '2026-06-15T18:23:37Z'
---
<!-- sq:body -->
## Outcome

Squads supports a growing ecosystem of agent backends — Claude Code, generic AGENTS.md, and future tools like Cursor, Windsurf, or other AGENTS.md consumers — managed on a live squad rather than fixed at initialisation time. Teams can add, switch, and remove backends through first-class commands, with clean artifact transitions and no orphaned files.

## Predecessor

FEAT-16 (shipped: second backend — generic AGENTS.md) is what makes this possible. That work proved the `AgentBackend` ABC with a genuinely different implementation, yielded the shared conformance suite, and produced ADR-133 (de-Claude-ify the ABC before the 1.0 freeze). The foundation — a registry that holds multiple backends, an honest ABC tested against two real implementations — now exists. This epic builds the management layer on top of it.

## Scope

Features in this epic answer the question: once a squad exists, how do users manage which backends are active? That includes switching, adding, removing, and (open question) whether more than one backend can run simultaneously. The ABC and registry plumbing that underpins any of this belongs in EPIC-31 (Squads backend — the engine); this epic is about the user-facing product surface.

## Distinction from EPIC-31

EPIC-31 ('Squads backend') is the engine epic: index store, service layer, `AgentBackend` ABC and registry *infrastructure*. This epic is different: it covers the product-facing management story for backends — commands users run, the schema that records which backends a squad has enabled, and the UX of transitions. A new backend that users ask for (e.g. a Cursor backend) would also live here, not in EPIC-31.

## Post-1.0 positioning

Nothing in this epic ships before 1.0. The ABC and `.squads.toml` backend-selection schema freeze at 1.0; this epic's work begins after that freeze is in place. FEAT-13 (stability contract) must close first.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
