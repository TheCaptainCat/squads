---
id: FEAT-000016
sequence_id: 16
type: feature
title: 'Second backend: generic AGENTS.md'
status: Ready
parent: EPIC-000012
author: product-owner
priority: medium
description: Prove the AgentBackend ABC with a cross-tool AGENTS.md implementation
  before the ABC freezes
subentities:
- local_id: US1
  title: As a team using a non-Claude agent tool, I want sq to generate an AGENTS.md,
    so that we can run squads with our own tooling
  status: Todo
- local_id: US2
  title: As a future backend implementer, I want a backend conformance test suite,
    so that I know exactly what the AgentBackend contract requires of me
  status: Todo
created_at: '2026-06-10T12:41:16Z'
updated_at: '2026-06-11T07:54:53Z'
---
<!-- sq:body -->
## Problem

`AgentBackend` is an ABC with exactly one implementation. An abstraction with one consumer is a
hypothesis, not a contract: Claude-isms (pointer-file layout, skill conventions, the CLAUDE.md
section) may be baked into the interface without anyone noticing, and we are about to freeze that
interface at 1.0.

## Value

A second, genuinely different backend is the cheapest honest test of the ABC. The cross-tool
`AGENTS.md` convention is the right candidate: it is real (adopted by multiple agent tools), simple
(one file, no pointer mechanics), and different enough from Claude Code to expose any leaked
assumptions. Users of non-Claude tooling get squads support; we get an ABC we can freeze with a
straight face.

## Scope

An `agents-md` backend implementing the `AgentBackend` ABC, writing/refreshing the project's
`AGENTS.md` (roster, workflow, skill content) from squad state — plus whatever ABC corrections the
exercise surfaces, made *before* 1.0.

## Acceptance

- `sq init`/`sq sync` can target the `agents-md` backend and produce a valid, useful `AGENTS.md`.
- Both backends pass a shared backend conformance test suite.
- Any ABC changes the work surfaced are merged and reflected in the stability contract.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 16 add-story "As a <role>, I want … so that …"`; track with `sq feature 16 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a team using a non-Claude agent tool, I want sq to generate an AGENTS.md, so that we can run squads with our own tooling |
| US2 | Todo |  | As a future backend implementer, I want a backend conformance test suite, so that I know exactly what the AgentBackend contract requires of me |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a team using a non-Claude agent tool, I want sq to generate an AGENTS.md, so that we can run squads with our own tooling

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
**Acceptance:** sq init / sq sync can target the agents-md backend and produce a valid AGENTS.md carrying roster, workflow and skill content; documented in the README.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a future backend implementer, I want a backend conformance test suite, so that I know exactly what the AgentBackend contract requires of me

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
**Acceptance:** a shared conformance suite runs against both backends and passes; any AgentBackend ABC changes surfaced by the second implementation are merged before 1.0.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
