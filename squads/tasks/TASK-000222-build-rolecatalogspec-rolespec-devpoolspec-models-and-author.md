---
id: TASK-222
sequence_id: 222
type: task
title: Build RoleCatalogSpec/RoleSpec/DevPoolSpec models and author bundled roles.toml
status: Done
parent: FEAT-219
author: tech-lead
subentities:
- local_id: ST1
  title: RoleCatalogSpec/RoleSpec/DevPoolSpec models capturing full RoleDef field
    set
  status: Todo
  story: US1
- local_id: ST2
  title: Author bundled roles.toml encoding today's 8 roles + bundles + dev pool
  status: Todo
  story: US1
created_at: '2026-06-26T07:35:28Z'
updated_at: '2026-06-26T07:58:42Z'
---
<!-- sq:body -->
## Goal

Build the pyright-strict `RoleCatalogSpec` / `RoleSpec` / `DevPoolSpec` pydantic v2 value objects
capturing the FULL `RoleDef` field set per ADR-221 §1, and author the bundled `roles.toml`
encoding today's exact 8 roles + BUNDLES + dev pool/defaults. This is the data + shape foundation for
FEAT-219 (FR). Behavior-preserving, golden-locked era — role-content externalization only (no
de-typing, no overrides).

Sequence: **first** task. The loader/rewire (TASK-223) and golden-lock/packaging (TASK-224) both
consume these models and this TOML.

## What to build

- **Models (ADR §1 shape, pyright-strict) — capture EVERY RoleDef field or the golden lock fails:**
  - `RoleSpec`: `slug: str`, `full_name: str`, `title: str`, `description: str` (one-liner for the
    Claude pointer frontmatter), `mission: str`, `responsibilities: list[str] = []`,
    `agreements: list[str] = []` (e.g. reviewer's "file findings as sub-entities" agreement),
    `model: str | None = None`, `color: str | None = None`, `is_default: bool = False`,
    `can_spawn: bool = False`. Defaults must match today's dataclass defaults exactly.
  - `RoleCatalogSpec`: `roles: list[RoleSpec]` (8 bundled roles, declaration order preserved),
    `bundles: dict[str, list[str]]` (today's BUNDLES: all / core / minimal → slug lists),
    `dev: DevPoolSpec`.
  - `DevPoolSpec`: `name_pool: list[str]` (today's DEV_NAME_POOL — 12 first names),
    `model: str = "sonnet"`, `color: str = "green"` (the dev_role default model/color).
- **Bundled TOML** at `src/squads/_roles/roles.toml`, shipped as package data (swept into the wheel by
  the existing `packages = ["src/squads"]` rule — same mechanism as templates; packaging
  *verification* is TASK-224). Encode, byte-for-byte vs today's `_catalog.py`:
  - `[bundles]` all / core / minimal with exact membership (all == full role set);
  - `[dev]` model / color / name_pool (the 12 names);
  - `[[roles]]` for each of the 8 (manager, architect, tech-lead, reviewer, qa, devops,
    product-owner, tech-writer) with every field. Multi-line missions use TOML basic-multiline
    strings; reviewer's `agreements` prose encoded faithfully; absent optional fields fall back to
    `RoleSpec` defaults.
- NOTE for the implementer: read field values directly from `src/squads/_roles/_catalog.py`
  (`PREDEFINED`, `BUNDLES`, `DEV_NAME_POOL`, `dev_role`) — do not paraphrase missions/responsibilities.

## Design constraints (ADR-221)

- §1 shape exactly; full field set captured. Enums-intact era: no custom types, no de-typing, no
  overrides. Roles are not item types — workflow/prefix-folder invariants do not apply.
- `to_extra`/`from_extra` ExtraKey bridge and `dev_role()` LOGIC stay in Python (TASK-223) — this
  task only defines the models + data.

## Acceptance

1. `RoleCatalogSpec`/`RoleSpec`/`DevPoolSpec` exist, pyright-strict-clean, with every RoleDef field
   and correct defaults.
2. `src/squads/_roles/roles.toml` exists encoding all 8 roles + 3 bundles + dev pool/defaults.
3. `tomllib`-parseable; round-trips into the models without error.
4. pyright/ruff clean. (Equality-with-today asserted by TASK-224's golden test.)
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 222 add-subtask "<title>"`; track with `sq task 222 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | RoleCatalogSpec/RoleSpec/DevPoolSpec models capturing full RoleDef field set | US1 |
| ST2 | Todo |  | Author bundled roles.toml encoding today's 8 roles + bundles + dev pool | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — RoleCatalogSpec/RoleSpec/DevPoolSpec models capturing full RoleDef field set

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — As a maintainer, I want role definitions loaded from roles.toml so adding a role needs no Python edit
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Author bundled roles.toml encoding today's 8 roles + bundles + dev pool

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US1 — As a maintainer, I want role definitions loaded from roles.toml so adding a role needs no Python edit
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
<!-- sq:discussion:end -->
