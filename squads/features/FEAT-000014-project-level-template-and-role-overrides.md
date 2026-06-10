---
id: FEAT-000014
sequence_id: 14
type: feature
title: Project-level template and role overrides
status: Ready
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
updated_at: '2026-06-11T07:54:52Z'
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
<!-- sq:discussion:end -->
