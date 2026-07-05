---
id: TASK-188
sequence_id: 188
type: task
title: Lexical-by-slug SKILL id allocation, shared by init seeding and migration
status: Done
parent: FEAT-178
author: tech-lead
subentities:
- local_id: ST1
  title: Shared lexical-by-slug ordering primitive consumed by init and migration
  status: Done
  story: US1
- local_id: ST2
  title: sq init seeds bundled skills as SKILL Items via IndexStore.transaction
  status: Done
  story: US3
created_at: '2026-06-24T18:46:55Z'
updated_at: '2026-06-24T20:00:54Z'
---
<!-- sq:body -->
## Goal

Build the **deterministic lexical-by-slug** SKILL id allocation, and wire `sq init` to seed bundled
skills using it so fresh squads carry SKILL ids from day one. This produces the single shared
allocation order that the migration (TASK-189) reuses, guaranteeing **ordering parity** between a
migrated squad and a freshly-init'd one (ADR-181 decision #5).

Depends on TASK-187 (the regen path must be frontmatter-preserving before stamped frontmatter is
safe to write). Sequence after 187, before 189.

## What to build

- A single, shared ordering primitive: walk/enumerate `agents/skills/` (or the bundled skill set)
  in **lexical-by-slug** order. Both `sq init` seeding and the migration MUST consume this one
  ordering so the same skill lands in the same ordinal position in both paths.
- `sq init` seeds each bundled skill as a full `Item` of `ItemType.SKILL` (no new enum entry — SKILL
  already exists), allocating ids through `IndexStore.transaction()` (single global counter,
  invariant 2), stamping sq frontmatter (`id`, `sequence_id`, `type: skill`, `title`, `status`,
  `author`, `schema_version`) onto the existing `agents/skills/<slug>.md` body file — one file,
  pointers stay pointers (invariant 5).
- Status profile: `Active` / `Archived` (meta-type profile, like role/operator) — no sub-entities,
  no work lifecycle. Skills are excluded from `WORK_TYPES`/retype.
- Identity allocated **exactly once** at seeding; never reallocated (ADR decision #4).

## Design constraints (ADR-181)

- Decision #1/#2: full Item of ItemType.SKILL, meta-type profile (Active/Archived, no sub-entities).
- Decision #5: lexical-by-slug ordering, shared by init and migration; ordering parity, NOT identical
  numeric ids (the global counter makes identical numbers impossible on a populated squad).

## Acceptance

1. Fresh `sq init` produces a squad where `sq list -t skill` is non-empty and every skill file has
   valid sq frontmatter with a unique `SKILL-…` id. (FEAT-178 AC#1-adjacent, US3.)
2. `sq repair` after a fresh init reconstructs the index to match file state exactly. (AC#2.)
3. The allocation order is lexical-by-slug and exposed via one shared primitive consumed by both init
   and the migration. (Ordering-parity foundation for AC#5.)
4. `sq check` green; pyright/ruff clean; service + CLI smoke tests added.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 188 add-subtask "<title>"`; track with `sq task 188 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Shared lexical-by-slug ordering primitive consumed by init and migration | US1 |
| ST2 | Done |  | sq init seeds bundled skills as SKILL Items via IndexStore.transaction | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Shared lexical-by-slug ordering primitive consumed by init and migration

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — Stable SKILL-… ID per skill for cross-entity referencing
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — sq init seeds bundled skills as SKILL Items via IndexStore.transaction

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US3 — Fresh sq init produces skills already carrying IDs from the start
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-24T19:39:20Z] Elias Python:
  - Implementation complete. bundled_skill_slugs() added to _interactions.py as the single shared lexical-by-slug ordering primitive (ADR-181 decision #5). seed_bundled_skills() added to MaintenanceMixin in _maintenance.py: iterates slugs lexically, skips already-stamped files (idempotent, decision #4), allocates via IndexStore.transaction() (invariant 2), calls join_frontmatter to stamp id/sequence_id onto the existing body file. Called by service.init() after refresh_managed() so body files already exist at stamp time.
  - _iter_item_files extended to scan all *.md in agents/skills/ (not just SKILL-*.md) so sq repair works with slug-named files. _scan_for_check silently skips slug-named skill files without IDs (pre-migration). _check_items includes SKILL in registered set so no false warnings. _skip_skill_seed=True internal hook + --no-seed-skills hidden CLI flag added for backward-compatible testing.
  - 12 new tests in tests/test_skill_seeding.py: all pass. All 16 existing test files updated (--no-seed-skills). Golden json regenerated. Full suite green (exit 0). pyright 0 errors. ruff clean.
- [2026-06-24T19:39:25Z] Elias Python:
  - @manager TASK-187 and TASK-188 (FOUNDATION increment of FEAT-178) are ready for review. Both tasks remain InProgress per instructions. Key files: src/squads/_backends/_claude_code/_backend.py (frontmatter-preserving regen), src/squads/_services/_maintenance.py (seed_bundled_skills + _iter_item_files + _scan_for_check), src/squads/_interactions.py (bundled_skill_slugs), src/squads/_services/_service.py (_skip_skill_seed hook), src/squads/_cli/_main.py (--no-seed-skills flag), tests/test_skill_seeding.py (12 new tests). Pyright clean, ruff clean, full suite green.
<!-- sq:discussion:end -->
