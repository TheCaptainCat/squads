---
id: GUIDE-79
sequence_id: 79
type: guide
title: 'squads architecture: layering, data model, and the marker mechanism'
status: Published
author: architect
refs:
- ADR-71
- ADR-72
- ADR-73
- ADR-74
- ADR-75
- ADR-76
- ADR-77
- ADR-78
- ADR-49
description: 'A standalone-readable map of how squads is built: the cli to services
  to index/backends/rendering layering, the item/sub-entity/index data model, and
  the marker mechanism — pointing at sq docs internals for depth and citing the standing
  ADRs.'
created_at: '2026-06-12T14:25:59Z'
updated_at: '2026-06-12T14:28:33Z'
extra:
  tech: python
  tags:
  - architecture
---
<!-- sq:body -->
squads is a Typer CLI that tracks a team of AI agents and their work as identified markdown. This guide is the map: enough to grasp the system's shape without reading source. It explains how the code is layered, what the data model is, and how the tool edits files without trampling the prose agents write into them. For the full depth — worked lifecycles, every helper, the playbook — see `sq docs internals`; this guide points there rather than duplicating it.

## 1. The layering

The code is a strict stack: each layer depends only on the ones below it, and `_models` sits at the bottom with no internal dependencies. The import direction is always downward, which keeps the graph acyclic.

**CLI (`src/squads/_cli`).** The top layer is the Typer app: one module per command group (`task`, `feature`, `decision`, `guide`, `migrate`, …), a `--dir` callback that resolves the active squad, and shared console/error/parse helpers in `_common.py`. Its only job is to parse arguments, call the service, and render results. It owns no business logic.

**Services (`src/squads/_services`).** The orchestration layer — the logic behind every command. A shared `ServiceCore` (create/get/list, backend and role/skill lookups, the roster) is composed with one concern mixin per file (items, collaboration, sub-entities, refs, roster, maintenance) into a flat `Service` façade. The CLI talks to this façade; the façade coordinates the layers below.

**Index store (`src/squads/_index`).** The integrity core. It owns `.squads.json`: a filelock'd, atomic read-modify-write of the index, plus the single global ID counter allocated inside a transaction. Everything that must be durable and consistent funnels through here.

**Backends (`src/squads/_backends`).** The pluggable harness layer — an `AgentBackend` ABC and a registry. Claude Code is the first backend; it writes pointer files and managed skills into `.claude/`. Nothing outside a backend reaches into `.claude/`; callers go through the ABC.

**Rendering (`src/squads/_rendering`).** Jinja2 with `StrictUndefined`. Item files and sub-entity blocks render from templates shipped as package data. This layer turns model state into the markdown a human reads.

**Models (`src/squads/_models`).** The shared, dependency-free base every layer above builds on: pydantic v2 types for the `Item`, its sub-entities, the index, the enums (item types and statuses), the config, and the marker tags. It imports nothing internal — that is what lets it be the foundation.

## 2. The data model

**Items.** Everything tracked — epic, feature, task, bug, ADR, review, guide, role, skill — is an `Item`: one markdown file with YAML frontmatter. IDs are JIRA-like (`TASK-000070`) and their number comes from one global monotonic counter, so every number is unique across all types (ADR-72). The formatted `id` is computed from the type and the stored `sequence_id`; both are persisted in frontmatter.

**Sub-entities.** Stories, subtasks, and findings don't get their own files — they ride on a parent item as typed entries in its frontmatter (`Item.subentities`), each carrying its own status, assignee, severity, mapped story, and title. The parent's body holds only their prose; their machine state is single-sourced in the parent's frontmatter and re-rendered into the human-readable head badge and roll-up summary on every change.

**The index.** `.squads.json` caches all item state plus the counter for fast queries and atomic ID allocation — but it stores nothing that can't be reconstructed from the `.md` files. Frontmatter is the source of truth; the index is a rebuildable derivative, and `sq repair` proves it by rescanning the files and rebuilding the index from scratch (ADR-71). A merge conflict in the index is therefore a non-event.

**Refs.** Items link to each other with typed references. Only outgoing (forward) edges are stored, in the item's frontmatter, with the kind carried inline on each entry (`ID` or `ID:kind`). Backrefs are never persisted — they're computed by inverting the forward edges across the index (ADR-73). The kind vocabulary is a closed, validated set (ADR-49).

## 3. The marker mechanism and cross-cutting decisions

squads and the agents working through it share the same files: the tool writes frontmatter, headings, status badges, and summary tables, while agents author prose. The boundary is drawn with invisible HTML-comment anchors that delimit each region the tool owns (a sq:body region, a sq:discussion region, the sub-entity block regions).

All file content is mutated through the sections layer (`_sections.py`) and only there; agents never touch the `.md` directly — they author through commands like `sq body` and `sq comment`, which route to that layer. Everything between an agent's anchors is preserved verbatim, never regenerated. The marker regex is deliberately strict so that prose mentioning anchor syntax in backticks is not mistaken for a real marker (ADR-74).

**Backends and pointers.** Harnesses sit behind the `AgentBackend` ABC; the real role and skill definitions live under the squad folder, and `.claude/` holds only thin pointers to them (ADR-75).

**How versions move.** The on-disk schema is versioned with a dotted 0.x string naming the release that introduced it, compared as a tuple (never as a raw string), and a squad is moved forward through the ordered `sq migrate` runner — each step a recorded, testable transformation with a manual runbook for the parts a machine can't do (ADR-76).

**Cross-cutting conventions.** Time is injectable: all timestamps route through a single clock module so tests can freeze it and adoption can forge history with `--at` (ADR-77). And every implementation module is private — leading-underscore names, with package inits that don't re-export — so a 1.0 release freezes no accidental public API (ADR-78).

## Going deeper

This guide is the shape; the depth lives elsewhere.

- `sq docs internals` — the index and counter, frontmatter-as-truth, markers, refs, the backend and pointers, the playbook, and a worked item lifecycle.
- `sq docs README` — the documentation map and the shape diagram.
- `CLAUDE.md` — the working guide for the codebase: the architecture-and-layering section and the invariants these ADRs put on the record.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
