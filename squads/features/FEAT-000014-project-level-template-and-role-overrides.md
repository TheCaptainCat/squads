---
id: FEAT-000014
sequence_id: 14
type: feature
title: Project-level template and role overrides
status: Done
parent: EPIC-000012
author: product-owner
priority: high
description: squads/.templates/ overrides; lookup path and precedence join the durable
  contract, so it must land before 1.0
subentities:
- local_id: US1
  title: As a project lead, I want to override item templates from squads/.templates/,
    so that generated items follow our house format
  status: Todo
- local_id: US2
  title: As a project lead, I want to add or override role definitions for my project,
    so that the squad matches my actual team
  status: Todo
- local_id: US3
  title: As a maintainer upgrading squads, I want defined precedence and staleness
    behaviour for my overrides, so that an upgrade never silently breaks them
  status: Todo
- local_id: US4
  title: As a project lead, I want to supply each agent's name at init and at role
    creation, so that my squad's roster is named the way my team wants
  status: Todo
created_at: '2026-06-10T12:41:06Z'
updated_at: '2026-06-12T22:08:38Z'
---
<!-- sq:body -->
## Problem

Every squad gets the same bundled templates and roles. Teams that need their own item layouts,
extra roles, or house-style skill wording have no sanctioned hook — their only options are forking
or hand-editing managed files, both of which we tell them never to do. The agent names themselves
are imposed too: the roster comes from the bundled catalog and name pool, with no way to choose
who your team is called at init or role-creation time. This is the one explicitly-deferred feature
from the original plan.

## Value

Overrides are what make squads adaptable to a team instead of the other way round. And they are a
1.0 blocker for a structural reason: the **override lookup path and precedence rules become part of
the durable on-disk contract** the moment we ship them. Shipping them in 0.x lets us correct the
design while we still can; bolting them on after 1.0 would mean either breaking the contract or
living with a mistake forever.

## Scope

A `squads/.templates/` area (and the analogous role override location) where a project can shadow
bundled templates and roles; a defined lookup order (project override → bundled default); clear
behaviour for partial overrides and for overrides that go stale across upgrades.

Also part of the personalisation surface: **supplying agent names at creation time** — choose each
role's name when the squad is initialised (`sq init`) and when an individual role is created/added
later, instead of always drawing from the bundled name pool.

**This needs a design phase first** — the lookup path, precedence and upgrade story should go
through an ADR before implementation.

## Acceptance

- An ADR records the override locations, precedence and upgrade/staleness behaviour.
- A project can override at least item templates and role definitions without touching package data.
- Agent names can be supplied per role at `sq init` and at role creation; unnamed roles still fall
  back to the bundled pool.
- Overridden and bundled rendering are both covered by tests; `sq check`/docs explain the mechanism.
- The contract doc (stability feature) lists the override layout among the durable surfaces.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 14 add-story "As a <role>, I want … so that …"`; track with `sq feature 14 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a project lead, I want to override item templates from squads/.templates/, so that generated items follow our house format |
| US2 | Todo |  | As a project lead, I want to add or override role definitions for my project, so that the squad matches my actual team |
| US3 | Todo |  | As a maintainer upgrading squads, I want defined precedence and staleness behaviour for my overrides, so that an upgrade never silently breaks them |
| US4 | Todo |  | As a project lead, I want to supply each agent's name at init and at role creation, so that my squad's roster is named the way my team wants |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a project lead, I want to override item templates from squads/.templates/, so that generated items follow our house format

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
**Acceptance:** dropping a template under squads/.templates/ shadows the bundled one for item rendering, without touching package data; covered by a test.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a project lead, I want to add or override role definitions for my project, so that the squad matches my actual team

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
**Acceptance:** a project-local role definition is picked up by sync/spawn flows with the same precedence rule as templates; covered by a test.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As a maintainer upgrading squads, I want defined precedence and staleness behaviour for my overrides, so that an upgrade never silently breaks them

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
**Acceptance:** the ADR from the design phase defines lookup order (project override → bundled default), partial-override behaviour, and what happens when an override goes stale across an upgrade; sq surfaces stale overrides rather than failing silently.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — As a project lead, I want to supply each agent's name at init and at role creation, so that my squad's roster is named the way my team wants

<!-- sq:story:US4:head -->
**Status:** ⚪ Todo
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
**Acceptance:** `sq init` accepts per-role names (and the role-creation command accepts a name) instead of always drawing from the bundled pool; roles without a supplied name still get a pool name; the chosen names flow through to the roster, pointer files and CLAUDE.md section; covered by a test.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T15:25:19Z] Catherine Manager:
  - Kicking off the design phase per op-pierre's go (2026-06-12). @architect please draft the ADR: override locations, lookup precedence (project override → bundled default), partial-override behaviour, staleness across upgrades, and the agent-naming surface at init/role creation. Implementation waits for the accepted ADR.
  - The override layout joins the durable contract — leave a deferral comment on FEAT-000013 once the decision is proposed.
- [2026-06-12T15:30:16Z] Robert Architect:
  - Design phase done: ADR-000085 is Proposed (refs this feature). Proposal in brief — (1) Locations: one umbrella `<squad-dir>/.overrides/` with `templates/` (mirrors the bundled template tree 1:1, override key = existing render() name) and `roles/<slug>.toml` (structured, feeds RoleDef). Chose `.overrides` over the body's `.templates` because scope is broader than templates and one named root is cleaner for the contract; under the squad folder so it travels with the data and reuses the existing path resolution + traversal guard. (2) Precedence: per-file, project → bundled, presence is the override (no all-or-nothing, no manifest). Templates override whole-file; roles merge field-wise by slug (rename/remodel a bundled role, or define a new one). Engine: PackageLoader → squad-aware ChoiceLoader, render() and all call sites unchanged. (3) Staleness: `squads:override-base:<version>` stamp + a shipped per-template content-hash manifest; `sq check` WARNS on version drift, ERRORS on a missing required marker; valid overrides always render; `sq migrate` never rewrites them. (4) Naming: names become input at `sq init` (`--name slug=Full Name` + optional `[init.names]`) and at `sq role activate`/`sq dev add`; unnamed → bundled pool; the name rides the existing `extra.full_name` channel to roster/pointers/CLAUDE.md; slugs stay canonical and non-renamable.
  - Open questions for acceptance (op-pierre / @manager): (a) `.overrides` vs the body's `.templates` name — confirm the rename. (b) Naming UX at init: is repeatable `--name slug=Name` the right surface, or do we want an interactive prompt for 1.0? (b is deferrable; the contract only freezes that names live in extra.) (c) The drift check needs a per-release content-hash manifest shipped as package data — acceptable build cost, or prefer a coarser 'base-version older than current' warning with no per-file precision? (d) Confirm slugs are frozen as non-renamable (teams rename who the architect IS, not the architect slot). Left at Proposed deliberately — acceptance is yours. @manager
- [2026-06-12T15:45:34Z] Robert Architect:
  - @manager @op-pierre ADR-000085 is revised and ready for acceptance — still Proposed (acceptance is op-pierre's call).
  - Both requested revisions are integrated: (1) §3 spells out the stale-override update loop end-to-end — sq check warns on real drift → `sq override diff` shows BOTH deltas (what you changed vs current bundled, AND what the upgrade changed: base-bundled vs current bundled) → you merge by hand (never auto-rewritten) → `sq override update` re-stamps and clears the warning. The command group is scaffold/diff/update/list and joins the durable contract. (2) §4 naming UX: at a TTY sq init prompts for missing names unless --default-names; non-TTY implies --default-names; --name flags and [init.names] stay declarative and pre-answer prompts.
  - The confirmed rulings (.overrides/ location, frozen canonical slugs) are folded in too. Review with: uv run sq decision 85 show --full --comments.
- [2026-06-12T20:58:40Z] Olivia Lead:
  - Broke FEAT-000014 down into 5 tasks against accepted ADR-000085, all now **Ready**, sq check clean. Story mapping (subtasks):
  - • **TASK-000087** — Override loader + precedence plumbing (US1). ChoiceLoader engine swap (PackageLoader → squad-aware ChoiceLoader), squad-keyed Environment cache, .overrides/ path resolution + traversal guard. The foundation both template and role overrides sit on.
  - • **TASK-000088** — Role override resolver (US2). Field-wise roles/<slug>.toml merge over PREDEFINED + new-slug admission; activate_role/add_dev read through it; full_name seed.
  - • **TASK-000089** — sq override group + staleness (US3). override-base stamp, per-release content-hash manifest in package data, sq check version-drift warn + missing-marker error, and the scaffold/diff/update/list command group (the durable-contract surface; diff shows both Δ-mine and Δ-upgrade, update re-stamps only).
  - • **TASK-000090** — Agent naming at init/role creation (US4). --name slug=… flags + [init.names] + TTY prompt/--default-names (non-TTY implies default); flows to extra.full_name → roster/pointers/CLAUDE.md. Slugs stay canonical.
  - • **TASK-000091** — Docs + contract doc (US3). Document the override + naming mechanism; list the .overrides layout among the durable surfaces in the FEAT-000013 contract doc. Co-author with @architect. Lands last.
  - **Recommended order (blocks edges set):** T87 first (foundation) → T88 + T89 build on it (T89 also wants T88's role surface for scaffold --role / list, so T89 lands after or alongside T88's resolver) → T90 runs in parallel from the start (one coordination point: T88's roles/<slug>.toml full_name seed) → T91 last, after T87–T90 ship.
  - **Flag — nothing blocks a dev from starting T87.** Two things worth confirming before T89/T91 land, neither a blocker: (1) the per-release content-hash manifest is a new build artifact — @devops should be aware it joins package data and the build must generate+verify it (ADR Consequences). (2) T91's contract doc edit assumes the FEAT-000013 contract doc exists and is the right home — @architect owns it, please confirm. The ADR itself is fully decided; no open design questions remain.
<!-- sq:discussion:end -->
