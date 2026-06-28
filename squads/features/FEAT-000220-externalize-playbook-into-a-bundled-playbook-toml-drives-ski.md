---
id: FEAT-000220
sequence_id: 220
type: feature
title: Externalize playbook into a bundled playbook.toml; drives skill generation
status: Done
parent: EPIC-000206
author: product-owner
refs:
- FEAT-000219:depends-on
- FEAT-000207:depends-on
subentities:
- local_id: US1
  title: As a maintainer, I want the PLAYBOOK loaded from playbook.toml so skill content
    lives in data not code
  status: Todo
- local_id: US2
  title: Project admin can add playbook entries for custom types so generated skills
    have role guidance
  status: Todo
- local_id: US3
  title: As a maintainer, I want a golden test asserting generated skills are byte-identical
    before and after this change
  status: Todo
created_at: '2026-06-26T07:17:58Z'
updated_at: '2026-06-26T09:27:33Z'
---
<!-- sq:body -->
## What this delivers

Today the `PLAYBOOK` dict in `src/squads/_interactions.py` hardcodes, for each item type, a rich `ItemPlaybook`: an overview paragraph, lifecycle text, command examples, and per-role `RoleGuide`s (`enter` / `do` / `handoff` / `watch` sections). This `PLAYBOOK` is the source of truth for every generated `sq-<type>` skill file and for `skills_for_role()` — the map from a role to which item-type skills it should have.

This feature moves the playbook to a bundled `playbook.toml`, loaded and validated as a `PlaybookSpec` pydantic value object. Default behavior is **byte-identical to today** (golden-locked against a frozen snapshot of `_interactions.py`). The Python `PLAYBOOK` dict is retired.

**Why this matters for custom types (FEAT-000210):** today a custom type gets only a thin auto-generated skill because there is no playbook entry for it. Once the playbook is config-driven, a project can add a `[playbook.types.incident]` block with an overview and per-role guides, and the generated `sq-incident` skill will carry rich, actionable role guidance — the same quality as built-in types. This is what bridges "minimum-viable custom type" (F4) to "fully-integrated custom type with role playbook" (the complete vision).

## Scope

- Design and implement the `PlaybookSpec`, `ItemPlaybook`, and `RoleGuide` pydantic value objects. Fields on `ItemPlaybook`: overview, lifecycle (string), commands (list), roles (dict[slug, RoleGuide]). Fields on `RoleGuide`: enter, do, handoff, watch (all optional strings).
- Author a bundled `playbook.toml` under `src/squads/_interactions/` (or `_roles/`) encoding every current `ItemPlaybook` entry for task, bug, feature, epic, decision, review, guide, skill, role, operator. The TOML becomes the source of truth; the `PLAYBOOK` dict in `_interactions.py` is retired.
- Load `PlaybookSpec` once per `Service` instantiation. Pass explicitly to `_write_item_skills`, `skills_for_role()`, `managed_item_types()`, and any other surface that today reads `PLAYBOOK` or `SKILL_DESCRIPTIONS`.
- Role slug references in `playbook.toml` are validated against the loaded `RoleCatalogSpec` at load time — an unknown role slug in a playbook entry is a spec error.
- **Golden test:** assert the loaded `PlaybookSpec` equals a frozen snapshot of today's `PLAYBOOK` dict (all types, all role guides, all lifecycle/command text). This is the regression gate for skill content.
- All existing generated skill files remain identical after the change (`sq sync` produces the same output). All existing tests pass.

## Connection to custom types (FEAT-000210)

Once FP lands, a project adding a custom type in `.squads.toml` can also add `[playbook.types.incident]` entries in their playbook override. The `sq-incident` skill will then carry per-role enter/do/handoff/watch guidance instead of the thin auto-generated default. FEAT-000210 should note this as the upgrade path from thin-skill to full playbook.

## Dependencies and sequencing

FP depends on FEAT-000219 (FR — role catalog must be externalized first, since playbook entries reference role slugs that must be validated). FP also depends on FEAT-000207 (the spec loader/validation pattern).

FP relates to FEAT-000210 (custom types): FP is not a blocker for F4, but F4's thin-skill limitation is resolved by FP. The two can land independently; FP is the upgrade path.

FP can proceed in parallel with F2–F5 once FR and the F1 loader pattern exist.

## Acceptance criteria

1. A `PlaybookSpec` pydantic value object loads from `playbook.toml`; all current item types have their `ItemPlaybook` entry including per-role `RoleGuide`s.
2. The golden test passes: loaded `PlaybookSpec` == frozen snapshot of today's `PLAYBOOK` dict (every type, every role guide, all lifecycle/command text).
3. `_interactions.py`'s `PLAYBOOK` dict is retired; `skills_for_role()` and skill generation route through the loaded spec.
4. `sq sync` produces identical generated skill files before and after this change (no content drift).
5. A project can add `[playbook.types.incident]` entries in their playbook override and the resulting `sq-incident` skill reflects the declared role guides.
6. Role slug references in `playbook.toml` are validated against `RoleCatalogSpec` at load time; an unknown slug raises a `SquadsError`.
7. All existing tests pass unchanged; `uv run pyright && uv run ruff check . && uv run pytest` all green.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 220 add-story "As a <role>, I want … so that …"`; track with `sq feature 220 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a maintainer, I want the PLAYBOOK loaded from playbook.toml so skill content lives in data not code |
| US2 | Todo |  | Project admin can add playbook entries for custom types so generated skills have role guidance |
| US3 | Todo |  | As a maintainer, I want a golden test asserting generated skills are byte-identical before and after this change |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a maintainer, I want the PLAYBOOK loaded from playbook.toml so skill content lives in data not code

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a squads maintainer, I want the entire `PLAYBOOK` dict (per-type overview, lifecycle text, commands, and per-role enter/do/handoff/watch guides) loaded from a `playbook.toml` at runtime, so that skill content lives in data rather than a hardcoded Python module.

**Acceptance:** a `PlaybookSpec` loads from `playbook.toml`; all current item types have their `ItemPlaybook` entry; `skills_for_role()` and `_write_item_skills` route through the loaded spec; the `PLAYBOOK` dict in `_interactions.py` is retired.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Project admin can add playbook entries for custom types so generated skills have role guidance

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a project admin with a custom type, I want to add `[playbook.types.incident]` entries in my playbook override file (per-role enter/do/handoff/watch text), so the generated `sq-incident` skill carries proper, actionable role guidance rather than the thin auto-generated default.

**Acceptance:** adding a `[playbook.types.incident]` block with role guides to the project's playbook override causes `sq sync` to regenerate the `sq-incident` skill with those role sections present; role slug references are validated against `RoleCatalogSpec` at load time.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As a maintainer, I want a golden test asserting generated skills are byte-identical before and after this change

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As a squads maintainer, I want a golden test that asserts `sq sync` produces byte-identical skill files before and after the playbook externalization, so that no skill content drifts during the migration.

**Acceptance:** the golden test runs `sq sync` and diffs every generated skill file against a frozen snapshot; it is CI-enforced and fails on any content difference.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-26T07:31:06Z] Catherine Manager:
  - Scope note (from op-pierre): playbook entries are required ONLY for non-meta (work) item types — epic/feature/task/bug/decision/review/guide. The meta-types role/skill/operator are deliberately ABSENT from the playbook (they get no sq-<type> skill or role-interaction guide); playbook.toml validation must NOT require entries for them.
<!-- sq:discussion:end -->
