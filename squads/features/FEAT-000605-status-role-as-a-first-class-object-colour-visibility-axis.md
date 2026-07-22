---
id: FEAT-605
sequence_id: 605
type: feature
title: 'Status role as a first-class object: colour + visibility axis'
status: Done
parent: EPIC-538
author: product-owner
refs:
- ADR-604:implements
subentities:
- local_id: US1
  title: Role-object model, derivation, Plane-1 validation
  status: Done
- local_id: US2
  title: sq workflow roles --json + statuses catalog change + goldens
  status: Done
- local_id: US3
  title: CLI colour rendering + is_open drop across list/tree/mine/workload/cheatsheet
  status: Done
created_at: '2026-07-22T15:29:57Z'
updated_at: '2026-07-22T16:57:05Z'
---
<!-- sq:body -->
## Capability

A status's `role` becomes a first-class object — not a string marker — carrying the
behaviour that today is split across three overlapping inputs (`terminal`, `is_open`,
ad-hoc role checks). A role declares `settled` (is this a resting state?), `hidden`
(hidden from the default view?), and `color` (a semantic colour intent). A status
references one role; every consumer that needs "is this terminal", "is this open",
or "what colour" reads it off the role instead of re-deriving its own answer.

Roles are an open, adopter-definable vocabulary (discoverable via `--json`, same as
the type/category/collection catalogs); `color` is a closed semantic-intent palette
(`positive`/`danger`/`warning`/`muted`/`neutral`/`info`) so every client can render
any role safely, with a neutral fallback for an intent it doesn't recognise. An
absent role on a status resolves to the bundled `pending` role (neutral, live,
shown) — fail-safe-visible.

## Why

Colour and default-visibility decisions for a status are currently driven by
overlapping, independently-maintained inputs (`terminal`, `is_open`, per-status
`role` markers used only for a couple of special-cased engine rules) that each
client re-blends its own way. Consolidating onto one role object removes the
duplication, gives adopters an open vocabulary for custom lifecycles, and gives
every surface (CLI, TUI, VS Code) the same single source for terminal/open/hidden/
colour.

## Scope

- New `RoleSpec` model (`settled: bool`, `hidden: bool`, `color: <intent>`) and
  `WorkflowSpec.roles: dict[str, RoleSpec]`, loaded from `[roles.<name>]` in the
  workflow spec. The bundled `default_workflow.toml` is regenerated with the eight
  catalog roles and each status's `role` reference; the per-status `terminal` field
  is removed.
- `StatusSpec.terminal` is dropped. `terminal`/`is_open`/default-visibility become
  reads of the referenced role: `role.settled`, `not role.settled`, `role.hidden`.
  The `TERMINAL` golden-lock export and `terminal_set()` are recomputed from role
  membership rather than a hardcoded set. The reachable-terminal lifecycle lint is
  retargeted to "every lifecycle must reach a status whose role is settled".
- Plane-1 spec validation: every `status.role` must name a declared role; every
  `role.color` must be one of the closed intent palette — an unknown intent fails
  closed at load time.
- `sq workflow roles --json` (new catalog command): one row per role,
  `{role, settled, hidden, color}`. `sq workflow statuses --json` drops `terminal`,
  keeps the `role` reference and `badge`.
- Status colour rendering across `sq list`, `sq tree`, `sq mine`, `sq workload`,
  and the workflow cheatsheet template: keyed on `role.color` intent, mapped to a
  concrete `rich` colour with a neutral fallback for unrecognised intents.
  `is_open` is dropped from every `--json` item payload that currently carries it.
- Service-level open/closed reads (roster bucket, blocker traversal, the open-item
  collaboration guard) switch from the old terminal/is_open inputs to
  `not role.settled`.
- Goldens: regenerate `workflow_statuses.json` (drop `terminal`), add a new
  `workflow_roles.json`; re-express the terminal/settled unit tests against the
  role-derived set.

This is a spec-format and `--json`-contract change only — no `SCHEMA_VERSION` bump,
no `sq migrate` data migration. `terminal`/`is_open` never appear in item
frontmatter or the index; role/the new catalog are workflow-spec vocabulary.

## Acceptance

- Bundled default behaviour is preserved for every status except one deliberate
  change: `Accepted`/`Published` stay visible by default, `Done`/`Verified` still
  hide, `Superseded`/`Deprecated` still hide, and `Rejected` now also hides
  (previously shown).
- `sq workflow roles --json` and the updated `sq workflow statuses --json` are
  correct and covered by goldens.
- `sq check` is clean; the full pyright/ruff/pytest gate is green.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 605 add-story "As a <role>, I want … so that …"`; track with `sq feature 605 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | Role-object model, derivation, Plane-1 validation |
| US2 | Done |  | sq workflow roles --json + statuses catalog change + goldens |
| US3 | Done |  | CLI colour rendering + is_open drop across list/tree/mine/workload/cheatsheet |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Role-object model, derivation, Plane-1 validation

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
New RoleSpec model (settled/hidden/color) + WorkflowSpec.roles loaded from [roles.<name>]; bundled default_workflow.toml regenerated with the 8-role catalog, each status's role reference, and terminal lines removed.

StatusSpec.terminal removed; terminal/is_open/hidden_by_default become reads of the role (role.settled, not role.settled, role.hidden). TERMINAL golden export and terminal_set() recomputed from role membership. Reachable-terminal lint retargeted to 'reach a status whose role is settled'.

Plane-1 validation: every status.role names a declared role; every role.color is one of the closed intent palette (positive/danger/warning/muted/neutral/info); unknown intent fails closed. A status with no role resolves to the bundled pending role.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — sq workflow roles --json + statuses catalog change + goldens

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
sq workflow roles --json (new): one row per role, {role, settled, hidden, color}.

sq workflow statuses --json drops terminal, keeps the role reference and badge.

Goldens: regenerate workflow_statuses.json (drop terminal, populate role); add a new workflow_roles.json golden. Re-express the terminal/settled unit tests against the role-derived set.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — CLI colour rendering + is_open drop across list/tree/mine/workload/cheatsheet

<!-- sq:story:US3:head -->
**Status:** 🟢 Done
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
Status colour in sq list/tree/mine/workload and the workflow cheatsheet template: keyed on role.color intent, mapped to a concrete rich colour per surface, with a neutral fallback for an unrecognised intent.

is_open dropped from every --json item payload that currently carries it (list/tree/mine).

Service-level open/closed reads (_roster bucket, _refs blocker traversal + RefContext.is_open, _collab open-item guard) switch to not role.settled.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T15:37:46Z] Olivia Lead:
  - Task breakdown (execution order = sequence order): US1 TASK-606 (role catalog + regen spec) -> 607 (drop terminal, derive from role) -> 608 (Plane-1 validation) -> 609 (service reads); US2 TASK-610 (roles --json + goldens); US3 TASK-611 (CLI colour + is_open drop). TASK-606/607 (the role model + derivation) MUST land before FEAT-570's US1 rework — FEAT-570 consumes role.hidden/role.color from this trunk. Implemented from the current dirty tree in one coherent change: superseded RETIRED_STATUS_ROLES + the hidden_by_default category-branch are replaced by the role catalog; the orthogonal survivors (CATEGORIES, --category filter, --json category, empty-view hint) are carried forward and land with FEAT-605.
- [2026-07-22T16:57:04Z] Catherine Manager:
  - FEAT-605 complete: ADR-604 role-object model landed across two reviewed+verified increments (REV-612/613, both Approved), full suite green. CLI status colour is live (positive=green, in_force/Accepted=cyan, danger=red, muted=grey, neutral=default) — accepted to Done under the standing non-visual delegation; palette is adjustable if the operator wants a different intent→colour on eyeball. Note: the is_open --json drop requires FEAT-570 US3 (VS Code client migration) to ship in the same 0.12 release.
<!-- sq:discussion:end -->
