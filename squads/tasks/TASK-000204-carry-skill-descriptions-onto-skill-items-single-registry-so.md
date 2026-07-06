---
id: TASK-204
sequence_id: 204
type: task
title: Carry skill descriptions onto SKILL items (single registry) so pointers/list
  keep rich text
status: Done
parent: FEAT-178
author: tech-lead
subentities:
- local_id: ST1
  title: Single slug->description registry in _interactions; backend reads it for
    pointers; descriptions on items
  status: Todo
  story: US1
- local_id: ST2
  title: Migration stamps and backfills descriptions onto skill items
  status: Todo
  story: US2
- local_id: ST3
  title: Fresh sq init stamps skill descriptions from the registry
  status: Todo
  story: US3
created_at: '2026-06-25T09:28:03Z'
updated_at: '2026-07-06T15:19:56Z'
---
<!-- sq:body -->
## Goal

Corrective fix on FEAT-178: SKILL items were created with an **empty `description`**, so
`generate_skill_entry` (`_backends/_claude_code/_backend.py`) computes
`description = item.extra.get(DESCRIPTION) or item.description or item.title` and **falls through to
`item.title`** (the slug). Result: the `.claude/skills/<slug>/SKILL.md` pointer descriptions degraded
from rich text (e.g. "Working with bug items in this squad: lifecycle, commands, and role-specific
guidance.") to bare slugs ("sq-bug"). Claude Code keys skill-loading/discoverability on that
description, so this regression breaks skill discovery. Restore rich descriptions by carrying them
onto the SKILL items (frontmatter-as-source-of-truth, like ROLE items already do).

## Scope

- **Single source-of-truth registry.** Establish ONE slug→description registry for the 9 bundled
  skills, placed alongside `bundled_skill_slugs()` in `_interactions.py` (the home of the per-type
  skill machinery): bespoke text for `squads` and `greeting` (currently at `_backend.py:72-91`), and
  the templated `f"Working with {item_type.value} items in this squad: …"` for each `sq-<type>`
  (currently `_backend.py:238`). After this task there is exactly one place these strings live.
- **Both producers consume the one registry — no duplicated strings.** The backend
  `write_managed`/`_write_item_skills` path AND `seed_bundled_skills`/the 0.4→0.5 migration both read
  descriptions from the registry. Remove the now-duplicated literal strings from the backend.
- **Stamp `item.description` from the registry.** Seeding and the migration set `item.description` on
  the SKILL item so it carries its description in frontmatter, mirroring how ROLE items already do.
  `generate_skill_entry` then reads a populated `item.description` → correct pointer; `sq list -t
  skill` / `sq skill show` show real descriptions instead of blank/slug.
- **Migration backfills existing items.** The 0.4→0.5 migration must also BACKFILL the description
  onto already-stamped-but-description-less skill items (this repo's current state), not only
  freshly-stamped ones. Idempotent: re-running changes nothing once descriptions are present.

## Design constraints

- Frontmatter-as-source-of-truth (invariant 1): the description lives on the SKILL item's frontmatter;
  `sq repair` reconstructs it. The pointer/list derive from the item, not from a backend literal.
- No string duplication: the registry is the single source; backend reads it.
- Marker-safe / frontmatter-preserving regen (invariant 3, ADR-181 #3) and once-only id allocation
  (ADR #4) are unchanged by this task — it touches description only.

## Acceptance

1. After fresh `sq init`, each `.claude/skills/<slug>/SKILL.md` pointer description == the registry
   text (NOT the slug); `sq list -t skill` shows the real descriptions. (US3 / US1.)
2. After `sq migrate up`, every skill item carries its description in frontmatter and its pointer
   shows registry text; backfill of an already-stamped, description-less item works. (US2.)
3. Exactly one slug→description registry exists (in `_interactions.py`); the backend's former literal
   strings are removed and the backend reads the registry.
4. `sq skill <n> show` displays the real description. (US1.)
5. `sq repair` and `sq check` clean after init and migrate; migration is idempotent.
6. pyright/ruff clean; service + CLI smoke tests added per project convention.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 204 add-subtask "<title>"`; track with `sq task 204 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Single slug->description registry in _interactions; backend reads it for pointers; descriptions on items | US1 |
| ST2 | Todo |  | Migration stamps and backfills descriptions onto skill items | US2 |
| ST3 | Todo |  | Fresh sq init stamps skill descriptions from the registry | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Single slug->description registry in _interactions; backend reads it for pointers; descriptions on items

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — Stable SKILL-… ID per skill for cross-entity referencing
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Covers establishing ONE slug→description registry for the 9 bundled skills alongside bundled_skill_slugs() in _interactions.py (bespoke text for squads/greeting, the templated 'Working with <type> items…' for each sq-<type>), removing the now-duplicated literal strings from the backend so it reads the registry, and stamping item.description from it so generate_skill_entry reads a populated description (correct pointer) instead of falling through to the slug title.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Migration stamps and backfills descriptions onto skill items

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US2 — Automatic migration retrofits existing skills with IDs on sq migrate up
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Covers the 0.4→0.5 migration setting item.description from the registry AND backfilling it onto already-stamped-but-description-less skill items (this repo's current state), not only freshly-stamped ones — idempotent once descriptions are present. Frontmatter-as-source-of-truth (invariant 1); sq repair reconstructs it.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Fresh sq init stamps skill descriptions from the registry

<!-- sq:subtask:ST3:head -->
**Status:** ⚪ Todo
**Implements:** US3 — Fresh sq init produces skills already carrying IDs from the start
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Covers fresh sq init (seeding) stamping each SKILL item's description from the single registry so the .claude pointer description and sq list -t skill / sq skill show all show the real rich text rather than the bare slug.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-25T09:41:31Z] Elias Python:
  - TASK-204 complete. Full suite: 1141 passed, 1 skipped. pyright 0 errors, ruff clean.
  - **Registry** (ST1): Added SKILL_DESCRIPTIONS: dict[str, str] and skill_description(slug) to _interactions.py beside bundled_skill_slugs(). Bespoke text for 'squads' and 'greeting' moved from the backend; templated text for each sq-<type> generated from ItemType (excluding ROLE/SKILL/OPERATOR). The two hardcoded description strings in _backend.py write_managed and _write_item_skills are replaced with interactions.skill_description(name) — single source.
  - **Seeding** (ST3): seed_bundled_skills() now sets description=skill_description(slug) on the Item, so fresh sq init stamps the real description onto each SKILL item's frontmatter. The legacy inner import of number_for_id cleaned up.
  - **Migration backfill** (ST2): _v0_4_to_v0_5.migrate() gains a new case at the top of the per-slug loop: if a convention file exists but description is empty/missing, _backfill_description() fills it and rewrites the .claude pointer. Idempotent: if description is already set, the slug is skipped entirely (acted=0 on re-run). Both stamped-legacy and unstamped paths also set description=desc. Extracted _backfill_description() and _rename_stamped_legacy() helpers to stay under PLR0915.
  - **Corpus fixture** updated: v0_5 greeting+squads files now carry the real YAML-serialized description strings instead of ''.
  - **Tests added**: test_init_seeds_skill_descriptions, test_init_skill_pointer_description_matches_registry, test_cli_list_t_skill_shows_non_empty_descriptions (seeding.py); test_migration_stamps_description_on_unstamped_file, test_migration_backfills_description_on_already_stamped_convention_file, test_migration_backfill_idempotent, test_migration_pointer_description_matches_registry (migration.py). 7 new tests.
  - TASK-204 stays InProgress. @manager
- [2026-06-25T09:57:39Z] Elias Python:
  - REV-205 nits F2+F3 applied. Targeted tests: 46 passed. pyright 0 errors, ruff clean.
  - **F2**: The sq-<type> comprehension in SKILL_DESCRIPTIONS now iterates PLAYBOOK directly (same source as managed_item_types() / bundled_skill_slugs()) — no hand-written exclusion list. Both the registry and bundled_skill_slugs() are locked to the same derivation; confirmed registry == bundled_skill_slugs() in sorted order.
  - **F3**: _rename_stamped_legacy now fills description only when it's empty/missing (guards with 'if not fm.get("description")'). Consistent with _backfill_description; a future operator edit to a skill description is never clobbered by a re-run.
  - TASK-204 stays InProgress. @manager
<!-- sq:discussion:end -->
