---
id: FEAT-000178
sequence_id: 178
type: feature
title: Skills as first-class ID'd entities (SKILL-… prefix, migration)
status: Draft
parent: EPIC-000031
author: product-owner
refs:
- FEAT-000176
- FEAT-000177
subentities:
- local_id: US1
  title: Stable SKILL-… ID per skill for cross-entity referencing
  status: Todo
- local_id: US2
  title: Automatic migration retrofits existing skills with IDs on sq migrate up
  status: Todo
- local_id: US3
  title: Fresh sq init produces skills already carrying IDs from the start
  status: Todo
- local_id: US4
  title: Architect ADR approved before implementation begins
  status: Todo
created_at: '2026-06-23T12:51:19Z'
updated_at: '2026-06-23T12:59:54Z'
---
<!-- sq:body -->
## Problem

Skills today are untracked second-class citizens: they live as managed files under `agents/skills/` with thin pointers in `.claude/`, but they carry no ID, appear nowhere in `.squads.json`, and cannot be referenced, linked, or queried like any other entity. The index has no knowledge that a skill exists.

## Goal

Make skills first-class ID'd entities: a `SKILL-…` prefix drawn from the **single global counter**, tracked in `.squads.json`, queryable with `sq` commands. A migration (`sq migrate up`) retrofits every existing bundled skill into an id'd file so the transition is automatic and non-breaking.

## Schema version

This feature bumps `SCHEMA_VERSION` to the next release's schema — currently anticipated **0.5**, but whatever the release number is when this actually lands — paired with an ordered migration that retrofits existing skills into id'd files. The version number is **unpinned** here; it is set at release cut time, not at authoring time.

## Scope

- New `SKILL` entry in `_models/_enums.py`: prefix `SKILL`, folder mapping under `agents/skills/`.

- The global-counter invariant is preserved: skill IDs are allocated through `IndexStore.transaction()` like every other type.

- Frontmatter ↔ model mapping: skill files carry sq frontmatter (id, title, status, author, schema_version) so `sq repair` can reconstruct the index from files alone.

- Migration: an ordered migration runner entry that walks the existing `agents/skills/` directory, allocates IDs, and stamps frontmatter into each skill file, leaving the skill bodies and pointer files intact.

- `sq list -t skill`, `sq skill <n> show`, basic ref support (`sq <type> <n> ref add SKILL-…`) so skills can be linked from features, tasks, or roles.

## Open question — architect ADR required (prerequisite dependency)

Before implementation begins, an **architect ADR is required** on the model-design choice: is a `Skill` a full `Item` type (same pydantic model, same sub-entity machinery, same workflow states), or a lighter id'd entity the way operators currently are? This choice drives the weight of the schema change and how much of the existing item pipeline skills reuse. **This feature depends on that ADR — do not start implementation until it is approved.**

Key trade-offs to address in the ADR:

- Full `Item` type: reuses `_itemfile.py`, `_sections.py`, the rendering pipeline, and the workflow engine. Heavier, but skills get stories, comments, lifecycle transitions.

- Lighter id'd entity (operator-style): smaller surface, no workflow, just an indexed record. Faster to land, but forfeits extensibility.

## Acceptance criteria

1. `sq list -t skill` returns the bundled skills after `sq migrate up` on an existing squad dir.

2. Each skill file carries valid sq frontmatter with a unique `SKILL-…` id; `sq repair` rebuilds the index cleanly from files.

3. `sq check` is green; no dangling refs, no index drift.

4. An existing squad upgraded via `sq migrate up` is indistinguishable from a fresh `sq init` squad (same structure, same ids for the same skills — or a defined deterministic ordering).

5. The architect ADR is Approved before implementation begins.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 178 add-story "As a <role>, I want … so that …"`; track with `sq feature 178 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Stable SKILL-… ID per skill for cross-entity referencing |
| US2 | Todo |  | Automatic migration retrofits existing skills with IDs on sq migrate up |
| US3 | Todo |  | Fresh sq init produces skills already carrying IDs from the start |
| US4 | Todo |  | Architect ADR approved before implementation begins |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Stable SKILL-… ID per skill for cross-entity referencing

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a squad member, I want each skill to carry a stable `SKILL-…` ID so that I can reference it from a feature, task, or decision without ambiguity — and so the reference survives renames of the underlying file.

**Acceptance:** `sq list -t skill` returns every bundled skill with its ID; `sq <type> <n> ref add SKILL-… --kind related` succeeds; the ref appears in `sq <type> <n> show`.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Automatic migration retrofits existing skills with IDs on sq migrate up

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a team using an existing squad directory, I want `sq migrate up` to automatically stamp SKILL IDs into all existing skill files so that I don't have to do anything manual to get skills into the index.

**Acceptance:** running `sq migrate up` on a pre-0.5 squad dir results in every skill file carrying valid sq frontmatter with a unique `SKILL-…` id; `sq repair` after migration rebuilds the index cleanly; `sq check` is green.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Fresh sq init produces skills already carrying IDs from the start

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As a new user running `sq init`, I want the bundled skills to already carry `SKILL-…` IDs from the moment the squad is created, so that skills are first-class from day one without needing a migration step.

**Acceptance:** `sq init` produces a squad dir where `sq list -t skill` is non-empty and every skill file has valid frontmatter; the index and file state match `sq repair`'s reconstruction exactly.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Architect ADR approved before implementation begins

<!-- sq:story:US4:head -->
**Status:** ⚪ Todo
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
As the team, we want an architect ADR to settle whether a Skill is a full Item type or a lighter id'd entity (operator-style) before any code is written, so that the model design is deliberate and the implementation doesn't need to be reversed.

**Acceptance:** an ADR item exists, is linked to this feature, and its status is Approved before FEAT-000178 moves to InProgress. Implementation tasks must not be created until that ADR is closed.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-23T12:52:51Z] Nina Product:
  - @architect — FEAT-000178 (Skills as first-class ID'd entities) has an open design question that needs an ADR before implementation can begin.
  - The question: is a Skill a full Item type (same pydantic model, workflow states, sub-entity machinery, rendering pipeline as tasks/features/bugs) — or a lighter id'd entity analogous to how operators are currently tracked (indexed record, no workflow, minimal surface)?
  - The choice drives how much of the existing item pipeline skills reuse, the weight of the schema change, and whether skills get lifecycle transitions/comments/stories in the future. US4 gates implementation on your ADR being Approved. Please author a decision item and link it to this feature.
- [2026-06-23T12:59:54Z] Robert Architect:
  - @product-owner ADR-000181 now exists, settling the model-design question. One grounding note worth flagging: operators and roles are already full Items in the index today (and SKILL already exists as an ItemType), so the real choice is the weight of the Item profile, not Item-vs-lighter. Recommendation: a skill is a full Item of type SKILL on the role/operator META-type profile — Active/Archived, no sub-entities, no work lifecycle — with migration stamping frontmatter onto the existing skill body file. Left Proposed for review — not Accepted, no tasks created.
<!-- sq:discussion:end -->
