---
id: FEAT-000178
sequence_id: 178
type: feature
title: Skills as first-class ID'd entities (SKILL-… prefix, migration)
status: Done
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
updated_at: '2026-06-25T09:59:02Z'
---
<!-- sq:body -->
## Problem

Skills today are untracked second-class citizens: they live as managed files under `agents/skills/` with thin pointers in `.claude/`, but they carry no ID, appear nowhere in `.squads.json`, and cannot be referenced, linked, or queried like any other entity. The index has no knowledge that a skill exists.

## Goal

Make skills first-class ID'd entities: a `SKILL-…` prefix drawn from the **single global counter**, tracked in `.squads.json`, queryable with `sq` commands. A migration (`sq migrate up`) retrofits every existing bundled skill into an id'd file so the transition is automatic and non-breaking.

## Schema version

This feature bumps `SCHEMA_VERSION` to the next release's schema — currently anticipated **0.5**, but whatever the release number is when this actually lands — paired with an ordered migration that retrofits existing skills into id'd files. The version number is **unpinned** here; it is set at release cut time, not at authoring time.

## Scope

- `SKILL` already exists as an entry in `_models/_enums.py` (prefix `SKILL`, folder `agents/skills/`) — no new enum entry is needed. The real work is seeding and migration: an ordered migration runner entry that walks `agents/skills/` in lexical-by-slug order, allocates IDs through `IndexStore.transaction()`, and stamps sq frontmatter (id, sequence_id, title, status, author, schema_version) onto each skill file, leaving skill bodies and pointer files intact. `sq init` seeds bundled skills in the same lexical order so fresh squads are consistent with migrated ones.

- The global-counter invariant is preserved: skill IDs are allocated through `IndexStore.transaction()` like every other type.

- Frontmatter ↔ model mapping: skill files carry sq frontmatter (id, title, status, author, schema_version) so `sq repair` can reconstruct the index from files alone.

- Status profile: `Active` / `Archived` (meta-type profile, matching the role/operator pattern) — no work lifecycle, no sub-entities.

- `sq list -t skill`, `sq skill <n> show`, basic ref support (`sq <type> <n> ref add SKILL-…`) so skills can be linked from features, tasks, or roles.

- `sq sync` must be frontmatter-preserving and marker-safe for skill body files: the skill-body regen path must replace only the `sq:body` region (as roles already do via `_regen_role_body`) rather than performing a full-file overwrite. This is required so that the stamped `id`/`sequence_id`/`schema_version` frontmatter is not wiped on the next `sq sync` run. A skill's `id`/`sequence_id` are allocated exactly once and never reallocated; re-running `sq sync` on an already-stamped skill updates only the body region.

## Design decision (ADR-000181)

The model-design question posed in the original backlog — full `Item` type vs. lighter id'd entity "the way operators currently are" — is settled by ADR-000181 (currently Proposed; implementation is gated on it reaching Approved per US4).

**Decision:** A skill is a full `Item` of the existing `ItemType.SKILL`, following the role/operator meta-type pattern. The premise of the original question was inaccurate: operators and roles are already full `Item`s in the index today (`SKILL` likewise already exists in `ItemType`), so there is no lighter non-`Item` alternative to choose. The genuine choice was the weight of the Item profile — and the ADR settles it as the meta-type profile (Active/Archived, no sub-entities, no work lifecycle), not the work-item profile.

Frontmatter is stamped onto the existing `agents/skills/<slug>.md` body file — one file per skill, pointers unchanged (invariant 5). The skill-body regen path must become frontmatter-preserving/marker-safe before implementation proceeds, per the ADR.

See ADR-000181 for full context, trade-off analysis, and consequences.

## Acceptance criteria

1. `sq list -t skill` returns the bundled skills after `sq migrate up` on an existing squad dir.

2. Each skill file carries valid sq frontmatter with a unique `SKILL-…` id; `sq repair` rebuilds the index cleanly from files.

3. `sq check` is green; no dangling refs, no index drift.

4. Running `sq sync` twice on a squad whose skills are already stamped leaves every skill's `id`/`sequence_id` unchanged — idempotent sync is verified by a test.

5. Migration and fresh-init produce the same relative allocation order (lexical-by-slug): a squad upgraded via `sq migrate up` and a squad created fresh with `sq init` place the same skill in the same ordinal position. Identical numeric ids are not required (the single global counter makes that impossible on an already-populated squad); ordering parity is the assertion.

6. The architect ADR (ADR-000181) is Approved before implementation begins.
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
As the team, we want the architect ADR (ADR-000181) to reach Approved status before any implementation code is written, so that the settled model-design decision is on the record and the implementation does not need to be reversed.

**Acceptance:** ADR-000181 exists (it does — filed as a ref on this feature) and its status is Approved before FEAT-000178 moves to InProgress. ADR-000181 is currently Proposed; implementation tasks must not be created until it is Approved.
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
- [2026-06-24T15:11:53Z] Nina Product:
  - Reconciled feature body and acceptance criteria against the revised ADR-000181.
  - Scope updated: removed the stale 'New SKILL entry in _models/_enums.py' bullet (SKILL already exists); replaced with accurate scope covering seeding/migration in lexical-by-slug order, status profile (Active/Archived), sq skill show / sq list -t skill / basic refs, and the new frontmatter-preserving/marker-safe/idempotent sq sync requirement.
  - Open question section replaced with a 'Design decision (ADR-000181)' section stating the decision is made (full Item of type SKILL on the meta-type profile) and noting ADR-000181 is currently Proposed — implementation remains gated on it reaching Approved (US4 unchanged).
  - AC#4 tightened to ordering parity (lexical-by-slug): identical numeric ids are not asserted (the global counter makes that impossible on a populated squad); the assertion is that migration and fresh-init place the same skill in the same ordinal position. New AC#4 added for idempotent sync (sq sync twice leaves id/sequence_id unchanged); old AC#4 becomes AC#5; old AC#5 (ADR gate) becomes AC#6. US4 body updated to reflect ADR-000181 exists at Proposed status.
- [2026-06-24T18:45:19Z] Catherine Manager:
  - ADR-000181 accepted and FEAT-000178 moved to Ready per @op-pierre's greenlight. US4's gate (architect ADR Approved) is now satisfied. Feature is queued for breakdown; no implementation tasks created yet — tech-lead to break it into tasks when work is scheduled.
- [2026-06-24T18:48:41Z] Olivia Lead:
  - Broke FEAT-000178 into 4 implementation tasks (TASK-000187..190), conforming to ADR-000181.
  - TASK-000187 make skill-body regen frontmatter-preserving/marker-safe (the riskiest piece, ADR #3) with a dedicated idempotence test [US1]; TASK-000188 lexical-by-slug allocation + sq init seeding via the one shared ordering primitive [US1, US3]; TASK-000189 ordered _migrations runner that retrofits agents/skills, allocates via IndexStore.transaction, stamps frontmatter, repairs + bumps schema [US2]; TASK-000190 wiring sq list -t skill / sq skill show / SKILL ref support [US1].
  - Suggested order: 187 first (regen safety is a prerequisite — without it the next sync wipes stamped ids), then 188 (allocation/seeding, also a prereq for migration), then 189 (migration reuses 188's ordering for parity). 190 can land in parallel once 187 is in. US4 is already satisfied (ADR Accepted) so it has no implementation subtask. Tasks left at initial status; no code written, no devs spawned.
  - @manager breakdown done and sq check green — ready to schedule the build.
- [2026-06-24T21:10:26Z] Catherine Manager:
  - Implementation complete and closed. ADR-000181 Accepted; 4 tasks Done (187 regen-safety, 188 seeding+lexical allocation, 189 migration, 190 wiring); 2 independent reviews Approved (REV-191, REV-201). All acceptance criteria verified hands-on: fresh init seeds 9 stamped SKILL items in lexical order, sq migrate up retrofits a 0.4 squad with ordering parity + idempotence, double-sync preserves ids, sq skill show / refs --in/--out + SKILL ref round-trip work, repair/check green. Schema bumped to 0.5; package __version__ 0.5.0. NOTE: this repo's own squad is migrated (schema 0.5, SKILL-192..200) but managed files still stamped 0.4.1 — a sq sync is the pending refresh step.
- [2026-06-25T07:55:28Z] Catherine Manager:
  - Reopening: skill body files were left slug-named (greeting.md) instead of following the SKILL-NNNNNN-<slug>.md convention that every other type uses — including the role/operator meta-types this feature was modeled on (ROLE-000001-manager.md, OP-000010-op-pierre.md). Per @op-pierre: the 0.5 migration must RENAME the files and update the .claude skill pointer to match. Corrective task incoming under this feature; ADR-181 #3 to be amended for the filename convention.
- [2026-06-25T09:23:57Z] Catherine Manager:
  - Filename-convention gap (caught by @op-pierre) fixed and verified. TASK-202 Done, REV-203 Approved. Skill files now follow SKILL-NNNNNN-slug.md like ROLE/OP across fresh init AND migration; .claude pointers rewritten to match and resolve; F3 layering fixed (backend no longer reads IndexStore — skill paths flow via BackendContext). Our own repo re-migrated in place: 9 files renamed, ids 192-200 preserved (no realloc), pointers resolve, check/repair clean. Feature complete.
- [2026-06-25T09:27:39Z] Catherine Manager:
  - Reopening again (caught by @op-pierre): SKILL items carry empty descriptions, so generate_skill_entry falls back to item.title (the slug) and the .claude pointer descriptions degraded from rich text ('Working with bug items… lifecycle, commands, role-specific guidance') to bare slugs — breaking skill discoverability (Claude Code keys skill-loading on that description). Root cause: skills became items but their descriptions were never carried onto the item (they're generated in the backend). Fix: single slug→description registry as source of truth, used by backend write_managed AND seeding/migration to stamp item.description — mirroring how ROLE items already carry descriptions in frontmatter (frontmatter-as-truth). Corrective task incoming.
- [2026-06-25T09:59:02Z] Catherine Manager:
  - Description regression fixed and verified. TASK-204 Done, REV-205 Approved. Single SKILL_DESCRIPTIONS registry (one source, derived from PLAYBOOK) feeds backend + seeding + migration; descriptions stamped onto SKILL items (frontmatter-as-truth, like ROLE). Live repo re-migrated: 9/9 skill descriptions backfilled, ids 192-200 + convention filenames preserved, all .claude pointers resolve with rich descriptions, check/repair clean. Feature complete.
<!-- sq:discussion:end -->
