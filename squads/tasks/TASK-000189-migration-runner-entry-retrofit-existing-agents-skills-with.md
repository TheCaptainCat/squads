---
id: TASK-189
sequence_id: 189
type: task
title: 'Migration runner entry: retrofit existing agents/skills with SKILL ids'
status: Done
parent: FEAT-178
author: tech-lead
subentities:
- local_id: ST1
  title: Ordered migration walks agents/skills, allocates ids, stamps frontmatter
  status: Done
  story: US2
- local_id: ST2
  title: Migration runs repair, stamps schema bump, ordering parity with init
  status: Done
  story: US2
created_at: '2026-06-24T18:46:56Z'
updated_at: '2026-07-06T15:19:52Z'
---
<!-- sq:body -->
## Goal

Add an ordered `_migrations` runner entry that retrofits every existing skill under `agents/skills/`
into an id'd SKILL item on `sq migrate up`, so existing squads pick up skill ids automatically and
non-breakingly. Bumps `SCHEMA_VERSION` (unpinned — set at release cut).

Depends on TASK-187 (frontmatter-preserving regen) and TASK-188 (shared lexical-by-slug
allocation primitive). Sequence last among the core three.

## What to build

- A new ordered migration in `_migrations` (registered in `_migrations/_registry.py::MIGRATIONS` as a
  `Migration` record with a private `_vN_M_to_vP_Q.py` `migrate(paths) -> int` and a `manual` runbook
  string). Never run via `python -m` — only through `sq migrate up`.
- The `migrate(paths)` walks `agents/skills/` in the **shared lexical-by-slug order** from
  TASK-188, allocates a `SKILL-…` id per skill through `IndexStore.transaction()` (global counter,
  invariant 2), and stamps sq frontmatter (`id`, `sequence_id`, `type: skill`, `title`, `status:
  Active`, `author`, `schema_version`) onto each existing skill body file — bodies and `.claude/`
  pointers left intact (invariant 5).
- After stamping, `sq migrate up` runs `repair` and stamps the new `SCHEMA_VERSION`. Schema version is
  **unpinned** here (feature anticipates 0.5; set at release-cut). `_models/_schema.py` is the single
  source of truth; compare with `schema_tuple`.
- Skip/no-op skills already carrying a SKILL id (idempotent migration; do not reallocate — ADR #4).
- Provide the `manual` runbook string and ensure it surfaces in `sq migrate chlog`.

## Design constraints (ADR-181)

- Decision #5: same lexical-by-slug ordering as init → ordering parity, not identical numbers.
- Decision #6: schema bump unpinned, set at release cut.
- Decision #4: allocate once, never reallocate.

## Acceptance

1. `sq migrate up` on a pre-bump squad dir results in every skill file carrying valid sq frontmatter
   with a unique `SKILL-…` id. (FEAT-178 AC#1, US2.)
2. `sq repair` after migration rebuilds the index cleanly; `sq check` green; no dangling refs / index
   drift. (AC#2, AC#3.)
3. **Ordering-parity test**: a squad upgraded via `sq migrate up` and a fresh `sq init` squad place
   the same skill in the same ordinal position (lexical-by-slug). Identical numeric ids are NOT
   asserted. (AC#5, US2/US3.)
4. Migration is idempotent: re-running `sq migrate up` does not reallocate stamped skills.
5. pyright/ruff clean; suite green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 189 add-subtask "<title>"`; track with `sq task 189 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Ordered migration walks agents/skills, allocates ids, stamps frontmatter | US2 |
| ST2 | Done |  | Migration runs repair, stamps schema bump, ordering parity with init | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Ordered migration walks agents/skills, allocates ids, stamps frontmatter

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US2 — Automatic migration retrofits existing skills with IDs on sq migrate up
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Covers the new ordered migration runner (private _vN_M_to_vP_Q.py registered in MIGRATIONS, run only via sq migrate up) that walks agents/skills/ in the shared lexical-by-slug order from TASK-188, allocates a SKILL-… id per skill through IndexStore.transaction() (invariant 2), and stamps sq frontmatter onto each existing skill body file leaving bodies and .claude/ pointers intact (invariant 5). Skips skills already carrying a SKILL id (idempotent, ADR #4).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Migration runs repair, stamps schema bump, ordering parity with init

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — Automatic migration retrofits existing skills with IDs on sq migrate up
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Covers the migration's finalization: sq migrate up runs repair and stamps the new (release-cut-pinned) SCHEMA_VERSION after retrofitting, plus the ordering-parity test proving a migrated squad and a fresh sq init squad place the same skill in the same ordinal position (lexical-by-slug; identical numeric ids NOT asserted, per ADR #5). Includes the manual runbook surfacing in sq migrate chlog.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-24T20:15:23Z] Elias Python:
  - Implementation complete. Migration runner _v0_4_to_v0_5.py added to _migrations/. Registry entry added (version=0.5.0, from_schema=0.4, to_schema=0.5). SCHEMA_VERSION bumped from 0.4→0.5 in _models/_schema.py.
  - Runner walks agents/skills/ in bundled_skill_slugs() lexical order, reads .squads.json sync, allocates ids (counter+padding from index), stamps frontmatter via sections.join_frontmatter(), writes back atomically. Idempotent: skips files with existing id field. repair() called by run_pending_migrations afterwards rebuilds the index. Corpus fixture v0_5 added (2 unstamped skill files). _CORPUS_CASES updated.
  - Tests: 6 tests in tests/test_skill_migration.py covering: stamps all bundled skills, idempotent, repair rebuilds cleanly, lexical ordering parity with init, CLI smoke (sq migrate up), CLI idempotent (second run = noop). Also updated test_session_lineage.py (test_schema_version_is_0_5, test_v0_3_migration_stamps_current_schema) and reflog tests for 0.5 schema version string.
- [2026-06-24T21:04:09Z] Elias Python:
  - REV-201 nits F1-F4 fixed.
  - F2+F3 (_v0_4_to_v0_5.py): rewrote migrate() as async; removed _read_index_sync/_write_index_sync entirely. Each skill id is now allocated through IndexStore.transaction() + db.allocate_id() — same pattern as seed_bundled_skills(). Migration.run type changed to Callable[[SquadPaths], Awaitable[int]] in _registry.py; sync runners wrapped via _wrap_sync(). run_pending_migrations now awaits m.run(paths). repair() recovers the counter high-water mark from max(seq) as designed — no manual index surgery needed.
  - F1 (__init__.py): __version__ bumped 0.4.1 → 0.5.0. sq migrate chlog v0.4.1..v0.5.0 now prints the 0.5 MANUAL cleanly (verified).
  - F4 (corpus/v0_5): corpus is now schema_version=0.5 with SKILL-000007/SKILL-000008 stamped frontmatter on greeting.md and squads.md — a genuine post-migration snapshot. migrate up on v0_5 is a no-op (all corpus tests pass).
  - Collateral: templates_manifest.json regenerated for v0.5.0 (required by test_override_commands/test_golden_json); override golden files updated (base_version 0.4.1 → 0.5.0). Full suite: 1129 passed, 1 skipped. Pyright clean, ruff clean.
<!-- sq:discussion:end -->
