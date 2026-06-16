---
id: FEAT-000137
sequence_id: 137
type: feature
title: Manage backends on an existing squad
status: Draft
parent: EPIC-000136
author: product-owner
refs:
- FEAT-000016
- ADR-000133
- FEAT-000013
description: sq backend command group to add, switch, list, and remove backends with
  clean artifact transitions
subentities:
- local_id: US1
  title: As a developer switching agent tools, I want to run `sq backend switch <name>`
    on an existing squad so that my new tool's context file is generated and the old
    one is removed without leaving orphaned files on disk
  status: Todo
- local_id: US2
  title: As a team using mixed agent tooling, I want to list the backends configured
    on my squad so that I can see which is active and which are available
  status: Todo
- local_id: US3
  title: As a backend author, I want the registry to reject any backend that fails
    the conformance suite so that managed backends cannot be added in a broken state
  status: Todo
created_at: '2026-06-15T18:23:41Z'
updated_at: '2026-06-15T18:24:32Z'
---
<!-- sq:body -->
## Problem

A squad's backend is chosen once — at `sq init` or `sq adopt` via `--backend` — and stored as a singular `default_backend` string in `.squads.toml`. There is no command to list, add, switch, or remove backends after that point. The runtime resolves exactly one backend (`ServiceCore._backend()` → `get_backend(config.default_backend)`), so there is no way to run two at once.

Switching today requires hand-editing `.squads.toml` and re-running `sq sync`. That leaves the old backend's artifacts — `CLAUDE.md`, `.claude/` pointer files, or `AGENTS.md` — orphaned on disk: `remove_artifacts` is wired only for per-item removal, not backend-level cleanup. The result is an inconsistent tree with no supported recovery path.

## Value

Teams change tooling. A developer joins who uses Cursor; a project migrates from Claude Code to a generic AGENTS.md workflow; a new backend arrives that a team wants to trial alongside the existing one. Right now all of those scenarios are unsupported. A `sq backend` command group — list, add, switch, remove — makes backend management a first-class operation with the same hygiene guarantees as everything else sq does: atomic, auditable, no orphaned files.

## Scope

### In scope

- **List** currently configured backend(s) and their status (active / registered but inactive — if multi-active is supported).

- **Add / enable** a backend on an existing squad: run its artifact generation alongside any already-active backend.

- **Switch** the active backend: disable the current one (call its `remove_artifacts` for the squad-level files, not item-level), enable the new one, produce its artifacts. No orphaned files.

- **Remove** a backend: call its cleanup, remove its entry from `.squads.toml`.

- Any backend managed this way must pass the shared conformance suite (tests/test_backend_conformance.py, shipped as part of FEAT-000016 / ADR-000133). This is the safety net for new backends entering the registry.

### Out of scope

- Writing new backends (Cursor, Windsurf, etc.) — those are separate features under this epic.

- The ABC or registry plumbing itself — that belongs in EPIC-000031.

## Open questions (for triage)

**OQ-1 — CLI shape.** A `sq backend` command group (list / add / switch / remove) is a reasonable candidate, but the exact grammar is not mandated here. Should 'add' and 'switch' collapse into a single command? Does 'list' belong at top level as `sq backends`? To be decided by the architect and tech lead when this moves to Ready.

**OQ-2 — Single-active vs multiple-active (most consequential).** Should a squad be able to run MORE THAN ONE backend simultaneously — maintaining both `CLAUDE.md` and `AGENTS.md` for mixed-tooling teams? Currently `.squads.toml` carries a single `default_backend` string. Multi-active would require that field to become a list or set (e.g. `active_backends = ["claude_code", "agents_md"]`). Trade-offs:

  - Single-active is simpler: one source of truth, no conflict between backends writing overlapping files, easier to reason about sync. The current schema supports it with a rename (`default_backend` → `active_backend`).

  - Multiple-active unlocks real mixed-tooling scenarios (a team where half use Claude Code, half use Cursor) and avoids a second migration if the need arrives later. Cost: backends must not write conflicting paths; `sq sync` must fan out to all active ones; error surfaces multiply.

  - **This drives a FEAT-000013 / capstone decision (see below).** Don't decide it here — flag it for Pierre to triage.

**OQ-3 — Artifact ownership on switch.** When switching from backend A to B, who is responsible for calling A's cleanup? The service layer (neutral coordinator), or the new backend B (it 'takes over')? Matters for the remove_artifacts contract — currently only defined for per-item removal.

## Acceptance

- `sq backend list` (or equivalent) shows the configured backend(s) and which is active.

- Adding a backend on an existing squad produces its artifacts without touching the other backend's files.

- Switching backends leaves no orphaned files from the old backend (verified by a test that asserts CLAUDE.md is absent after switching away from claude_code, or AGENTS.md is absent after switching away from agents_md).

- Removing a backend cleans up its artifacts and removes it from `.squads.toml`.

- Any backend registered this way passes the conformance suite.

- `sq check` reports a clear error if `.squads.toml` references a backend that is not in the registry.

## FEAT-000013 (stability contract) heads-up

The `.squads.toml` `default_backend` field is about to freeze at 1.0 as part of the stability contract (FEAT-000013). If multiple-active backends are even plausibly in scope post-1.0, we should freeze the field in a forward-compatible shape right now — for example, accepting a string OR a list, so that adding multi-active later is not a breaking change. A string-or-list field reads as a single-element list at runtime; it is a backward-compatible extension. This is a design note for the capstone, not a change request on FEAT-000013. **Do NOT alter FEAT-000013 as part of this feature.**
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 137 add-story "As a <role>, I want … so that …"`; track with `sq feature 137 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a developer switching agent tools, I want to run `sq backend switch <name>` on an existing squad so that my new tool's context file is generated and the old one is removed without leaving orphaned files on disk |
| US2 | Todo |  | As a team using mixed agent tooling, I want to list the backends configured on my squad so that I can see which is active and which are available |
| US3 | Todo |  | As a backend author, I want the registry to reject any backend that fails the conformance suite so that managed backends cannot be added in a broken state |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a developer switching agent tools, I want to run `sq backend switch <name>` on an existing squad so that my new tool's context file is generated and the old one is removed without leaving orphaned files on disk

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
_Write the user story (e.g. “As an <role>, I want … so that …”) and its acceptance criteria here — free-form paragraphs or bullet lists._
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a team using mixed agent tooling, I want to list the backends configured on my squad so that I can see which is active and which are available

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
_Write the user story (e.g. “As an <role>, I want … so that …”) and its acceptance criteria here — free-form paragraphs or bullet lists._
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As a backend author, I want the registry to reject any backend that fails the conformance suite so that managed backends cannot be added in a broken state

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
_Write the user story (e.g. “As an <role>, I want … so that …”) and its acceptance criteria here — free-form paragraphs or bullet lists._
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
