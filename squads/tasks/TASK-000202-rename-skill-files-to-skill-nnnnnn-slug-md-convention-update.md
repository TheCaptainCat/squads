---
id: TASK-000202
sequence_id: 202
type: task
title: Rename skill files to SKILL-NNNNNN-slug.md convention + update .claude pointer
status: Done
parent: FEAT-000178
author: tech-lead
subentities:
- local_id: ST1
  title: Migration renames legacy slug-named files to SKILL-NNNNNN-slug.md idempotently
  status: Done
  story: US2
- local_id: ST2
  title: Fresh sq init seeds skill files with the SKILL-NNNNNN-slug.md convention
  status: Done
  story: US3
- local_id: ST3
  title: Backend derives body path from id; .claude pointer resolves to renamed file
  status: Done
  story: US1
created_at: '2026-06-25T07:56:03Z'
updated_at: '2026-06-25T09:22:45Z'
---
<!-- sq:body -->
## Goal

Corrective fix on FEAT-000178: skill body files were left **slug-named** (`agents/skills/greeting.md`)
instead of following the `<PREFIX>-<NUM>-<slug>.md` convention every other type uses — including the
meta-types skills were modeled on (`ROLE-000001-manager.md`, `OP-000010-op-pierre.md`). ADR-000181 #3
is being amended (by the architect) to require `agents/skills/SKILL-<NNNNNN>-<slug>.md`. This task
makes the file naming conform across the backend, fresh init, and the migration.

This is purely a file-naming/path-derivation correction; identity allocation (lexical-by-slug),
status profile, and idempotence are unchanged from the original tasks.

## Scope

- **Backend `_write_managed_skill` (+ the regen path):** build the skill body path from the skill's
  **ID** — resolving it from the index exactly as roles already do (`_regen_role_body`,
  `_services/_maintenance.py:125`) — not from the bare slug. The resulting body file is
  `agents/skills/SKILL-<NNNNNN>-<slug>.md`. Update the `.claude/skills/<slug>/SKILL.md` pointer so the
  body path it references points to the renamed file; the **pointer directory stays keyed by slug**
  (only the referenced body path changes). Stays marker-safe / frontmatter-preserving (invariant 3,
  ADR #3) and within the FEAT-000177 codec contract.
- **`seed_bundled_skills` (fresh `sq init`):** name files with the `SKILL-<NNNNNN>-<slug>.md`
  convention from the start, reusing the shared lexical-by-slug allocation.
- **The 0.4→0.5 migration (`_v0_4_to_v0_5`):** RENAME each legacy `agents/skills/<slug>.md` →
  `agents/skills/SKILL-<NNNNNN>-<slug>.md` (idempotently — skip files already at the convention) and
  rewrite the `.claude` pointer's body path. Reuse the existing lexical-by-slug allocation already in
  the migration; do not reallocate ids (ADR #4).

## Design constraints (ADR-000181, amended #3)

- #3 (amended): skill body file path is `agents/skills/SKILL-<NNNNNN>-<slug>.md`, derived from the
  skill's id resolved through the index (role pattern), not the bare slug. Regen stays body-region-only
  / frontmatter-preserving.
- #4: ids allocated once, never reallocated; rename must not churn the id.
- #5: lexical-by-slug ordering reused (init + migration share it) — ordering parity, not identical ids.

## Acceptance

1. After fresh `sq init`, every skill body file matches `agents/skills/SKILL-<NNNNNN>-<slug>.md`.
   (US3.)
2. After `sq migrate up` on a legacy (slug-named) squad, every skill file is renamed to the
   convention; the migration is idempotent (re-running renames nothing and changes no id). (US2.)
3. The `.claude/skills/<slug>/SKILL.md` pointer resolves to the renamed body file (pointer dir stays
   slug-keyed). (US1 — referenceability/pointer resolution.)
4. `sq repair` and `sq check` clean after both init and migrate; no index drift / dangling refs.
5. Double-`sq sync` still preserves each skill's `id`/`sequence_id` AND now also preserves its
   filename (no rename churn on re-sync).
6. pyright/ruff clean; service + CLI smoke tests added per project convention.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 202 add-subtask "<title>"`; track with `sq task 202 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Migration renames legacy slug-named files to SKILL-NNNNNN-slug.md idempotently | US2 |
| ST2 | Done |  | Fresh sq init seeds skill files with the SKILL-NNNNNN-slug.md convention | US3 |
| ST3 | Done |  | Backend derives body path from id; .claude pointer resolves to renamed file | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Migration renames legacy slug-named files to SKILL-NNNNNN-slug.md idempotently

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US2 — Automatic migration retrofits existing skills with IDs on sq migrate up
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Fresh sq init seeds skill files with the SKILL-NNNNNN-slug.md convention

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

<!-- sq:subtask:ST3 -->
### ST3 — Backend derives body path from id; .claude pointer resolves to renamed file

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US1 — Stable SKILL-… ID per skill for cross-entity referencing
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-25T08:19:28Z] Elias Python:
  - TASK-202 implementation complete.
  - Migration (_v0_4_to_v0_5.py): walk slug → check for SKILL-*-slug.md (idempotent); if slug.md stamped-already → rename + update path in frontmatter + rewrite .claude pointer; if slug.md unstamped → allocate via IndexStore.transaction() + stamp → write SKILL-NNNNNN-slug.md → unlink legacy + rewrite pointer. File-presence trigger: rename fires on existence of slug.md regardless of stamp state — covers the live-repo case (stamped-but-slug-named).
  - Seeding (_services/_maintenance.py, seed_bundled_skills): glob for SKILL-*-slug.md first (idempotent skip); allocate → compute SKILL-NNNNNN-slug.md → stamp → write convention file → unlink legacy slug.md.
  - Backend (_backends/_claude_code/_backend.py, _write_managed_skill): loads index on every call; resolves skill item by slug; uses item.path as body_path on sync path. Falls back to slug.md on first-write (before seeding). This means sync always writes to SKILL-NNNNNN-slug.md.
  - _iter_item_files: convention files via SKILL-*.md glob (primary); legacy slug.md files also yielded (fallback for pre-migration squads and pre-seeding project fixtures).
  - Tests added: test_migration_renames_already_stamped_slug_file, test_migration_rename_pointer_resolves, test_migration_rename_idempotent_on_already_renamed, test_init_skill_files_use_convention_name, test_double_sync_preserves_skill_ids_and_filenames. Existing tests updated to assert convention names.
  - Corpus v0_5: skill files renamed to SKILL-000007-greeting.md / SKILL-000008-squads.md; frontmatter paths and .squads.json updated.
  - Full suite: 1134 passed, 1 skipped. pyright 0 errors, ruff clean. @manager ready for review.
- [2026-06-25T08:36:38Z] Elias Python:
  - Bug fixed (dangling .claude pointer after sq init).
  - Root cause: write_managed wrote the pointer to slug.md before seeding; seed_bundled_skills renamed the body but never rewrote the pointer, leaving .claude/skills/<slug>/SKILL.md pointing at the unlinked slug file.
  - Fix (preferred approach): after path_unlink(legacy_path) in seed_bundled_skills, call backend.generate_skill_entry(ctx, item) on each active backend. generate_skill_entry uses ctx.root_relative(item) which reads item.path (= SKILL-NNNNNN-slug.md) and writes the correct pointer. One-liner addition in _services/_maintenance.py; no reordering of init steps.
  - Test: updated test_init_skill_files_use_convention_name to also assert the .claude pointer's @-line references SKILL- and that the referenced file actually exists on disk. Full suite: 1134 passed, 1 skipped. pyright clean, ruff clean. @manager ready for review.
- [2026-06-25T09:21:16Z] Elias Python:
  - REV-000203 nits F1+F3 applied — all clean.
  - **F3 (layering)**: Removed the IndexStore.load() call from _write_managed_skill entirely. Added skill_paths: dict[str, Path] to BackendContext (with __init__ defaulting to {} on first-write paths). refresh_managed() now calls _skill_paths() to build the slug->abspath map from index SKILL items and injects it into the context before calling write_managed. sync() does the same (previously it used the bare _ctx property, which exposed the same gap — caught by the test_skill_body_region_updated_on_sync test). The backend reads ctx.skill_paths.get(name); empty map -> slug-named fallback as before.
  - **F1 (bare except)**: Moot after F3 — the try/except block was removed wholesale along with the IndexStore import.
  - Full suite: 1134 passed, 1 skipped. pyright 0 errors, ruff clean. TASK-202 stays InProgress. @manager
<!-- sq:discussion:end -->
