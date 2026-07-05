---
id: FEAT-219
sequence_id: 219
type: feature
title: Externalize role catalog into a bundled roles.toml (golden-locked)
status: Done
parent: EPIC-206
author: product-owner
refs:
- FEAT-207:depends-on
subentities:
- local_id: US1
  title: As a maintainer, I want role definitions loaded from roles.toml so adding
    a role needs no Python edit
  status: Todo
- local_id: US2
  title: As a maintainer, I want a golden test asserting the loaded catalog == today's
    hardcoded roles so regressions are caught
  status: Todo
created_at: '2026-06-26T07:17:14Z'
updated_at: '2026-06-26T07:58:45Z'
---
<!-- sq:body -->
## What this delivers

Today the 8 bundled roles — their slugs, full names, titles, missions, and responsibility lists — are hardcoded in `src/squads/_roles/_catalog.py` as Python `RoleDef` dataclass instances. The stack-dev name pool and `dev_role()` factory are also in that file. Adding a new bundled role, updating a responsibility description, or letting a project define custom roles requires modifying Python source.

This feature moves the role catalog to a bundled `roles.toml` file (under `src/squads/_roles/`), loaded and validated at runtime as a `RoleCatalogSpec` pydantic value object. The default behavior is **byte-identical to today** (golden-locked against a frozen snapshot of `_catalog.py`). The Python catalog is retired once the TOML is the source of truth.

This is the **same load-and-validate pattern** established by FEAT-207 for the workflow spec: a bundled default TOML, a validated pydantic model, and a golden test asserting the loaded spec equals the frozen snapshot.

**This feature delivers no user-visible change** — existing roles, their names, and their behavior are unchanged. It is the prerequisite for FP (playbook externalization), which references role slugs, and for eventually letting projects define custom role vocabulary.

## Scope

- Design and implement the `RoleCatalogSpec` and `RoleDef` (loaded) pydantic value objects. Fields: slug, full_name, title, mission, responsibilities (list of strings). The dev-name pool and `dev_role()` factory become derived from the spec.
- Author a bundled `roles.toml` under `src/squads/_roles/` encoding all 8 current roles (manager, architect, tech-lead, reviewer, qa, devops, product-owner, tech-writer) plus the dev-name pool. The TOML becomes the source of truth; `_catalog.py` is retired.
- Load `RoleCatalogSpec` once per `Service` instantiation (or lazily on first use) via the same loader pattern as `WorkflowSpec`. Pass explicitly to anything that today imports from `_catalog.py`.
- **Golden test:** assert the loaded `RoleCatalogSpec` equals a frozen snapshot of today's `_catalog.py` RoleDefs. This is the regression gate.
- All existing tests pass; `uv run pyright && ruff check . && pytest` all green.

## Dependencies and sequencing

FR depends on FEAT-207 (the spec loader/validation pattern is established there; FR reuses it). FR does not depend on F2 (no model de-typing needed — roles are not item fields). FR is a prerequisite for FP (playbook externalization), which references role slugs from the catalog.

FR can proceed in parallel with F2–F5 once the loader pattern from F1/FEAT-207 exists.

## Acceptance criteria

1. A `RoleCatalogSpec` pydantic value object loads from `roles.toml`; all 8 roles are represented with their current slugs, names, titles, missions, and responsibilities.
2. The golden test passes: loaded `RoleCatalogSpec` == frozen snapshot of today's `_catalog.py`.
3. `_catalog.py` is retired (or reduced to a thin shim delegating to the loaded spec); no remaining hardcoded `RoleDef` instances outside the TOML.
4. `dev_role()` and the dev-name pool are spec-derived.
5. All existing tests pass unchanged — no behavioral difference for role resolution, roster, or skill generation.
6. `uv run pyright && uv run ruff check . && uv run pytest` all green.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 219 add-story "As a <role>, I want … so that …"`; track with `sq feature 219 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a maintainer, I want role definitions loaded from roles.toml so adding a role needs no Python edit |
| US2 | Todo |  | As a maintainer, I want a golden test asserting the loaded catalog == today's hardcoded roles so regressions are caught |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a maintainer, I want role definitions loaded from roles.toml so adding a role needs no Python edit

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a squads maintainer, I want the 8 bundled role definitions (slug, name, title, mission, responsibilities) and the dev-name pool loaded from a `roles.toml` at runtime, so that role content lives in data rather than a hardcoded Python module and can be updated without a code change.

**Acceptance:** a `RoleCatalogSpec` loads from `roles.toml`; all 8 current roles are represented; `dev_role()` and the dev-name pool are derived from the spec; `_catalog.py` is retired.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a maintainer, I want a golden test asserting the loaded catalog == today's hardcoded roles so regressions are caught

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a squads maintainer, I want a golden test that asserts the loaded `RoleCatalogSpec` is identical to a frozen snapshot of today's `_catalog.py` role definitions, so that any accidental drift in the bundled catalog is caught as a test failure before it reaches users.

**Acceptance:** the golden test exists, is CI-enforced, and fails if any role slug/name/title/mission/responsibilities in the loaded spec differs from the snapshot.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
