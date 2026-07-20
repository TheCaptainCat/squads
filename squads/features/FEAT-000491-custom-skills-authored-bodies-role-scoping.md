---
id: FEAT-491
sequence_id: 491
type: feature
title: 'Custom skills: authored bodies + role scoping'
status: Done
author: product-owner
refs:
- BUG-490:addresses
- ADR-492:implements
subentities:
- local_id: US1
  title: As a squad author, I want to write and edit a custom skill's body so my team
    has a real, persistent runbook
  status: Done
- local_id: US2
  title: As a squad author, I want custom skills distinguished from bundled ones
  status: Done
- local_id: US3
  title: As a squad author, I want to scope a custom skill to one or more roles so
    exactly those agents preload it
  status: Done
- local_id: US4
  title: As a squad author, I want role pointers to stay current when I link or unlink
    a skill without a manual full resync
  status: Done
- local_id: US5
  title: As a squad author upgrading a squad, I want existing skills preserved unchanged
  status: Done
created_at: '2026-07-20T08:41:10Z'
updated_at: '2026-07-20T12:33:20Z'
---
<!-- sq:body -->
## Outcome

A squad author can write a **custom skill** (`sq skill add`) with real, persistent instructions —
not just a regenerated skeleton — and can **scope it to the specific roles** that should preload it.
Custom skills become first-class authored content, on par with bundled skills, instead of a
placeholder that only carries a description.

## Motivating use case

A team wants a **release-process skill** — the gates, the prep steps, how to draft (not publish) a
release — preloaded for the manager, devops, and tech-writer roles, so those three agents follow one
shared runbook. Today neither half is possible (see BUG-490): the skill body can't hold real content,
and there's no way to say "these roles preload this skill."

## Value

- Squad authors capture team-specific process knowledge (release runbooks, house style, local
  conventions) as first-class skills instead of scattering it across CLAUDE.md prose or tribal
  memory.
- Skills reach only the agents who need them — a role's context stays focused instead of every
  custom skill landing on every agent regardless of relevance.
- Authored content is safe: running `sq sync`/`regen`/`repair` never silently discards what an
  author wrote.

## Out of scope

- The rendering/storage mechanism that distinguishes authored from generated skills, and how role
  pointers stay in sync — that's the architect's call, covered by an ADR in flight (see refs).
- Project-level template overrides for *bundled* skills (separately deferred, tracked elsewhere).
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 491 add-story "As a <role>, I want … so that …"`; track with `sq feature 491 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | As a squad author, I want to write and edit a custom skill's body so my team has a real, persistent runbook |
| US2 | Done |  | As a squad author, I want custom skills distinguished from bundled ones |
| US3 | Done |  | As a squad author, I want to scope a custom skill to one or more roles so exactly those agents preload it |
| US4 | Done |  | As a squad author, I want role pointers to stay current when I link or unlink a skill without a manual full resync |
| US5 | Done |  | As a squad author upgrading a squad, I want existing skills preserved unchanged |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a squad author, I want to write and edit a custom skill's body so my team has a real, persistent runbook

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
## Acceptance criteria

- I can set a custom skill's body with real, multi-paragraph instructional content (short message
  or a file), the same way I can for an item's body today.
- I can re-edit that body later and see my latest edit reflected — not a stale or reverted copy.
- Running `sq sync`, `sq skill <addr> regen`, or `sq repair` never replaces or wipes my authored
  body — my content survives every one of those operations unchanged.
- A freshly-added custom skill with no body yet renders as a coherent, if minimal, skill file — it
  doesn't error or leave a broken pointer.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a squad author, I want custom skills distinguished from bundled ones

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
## Acceptance criteria

- Listing/showing skills makes it obvious which ones are custom (author-owned) versus bundled
  (system-owned) — I don't have to guess or dig into file contents to tell them apart.
- `sq sync`/`regen`/`repair` continues to freely regenerate bundled/system skills from their
  templates, exactly as today — only custom skills get authored-content protection.
- Attempting to hand-author a body onto a bundled/system skill is rejected with a clear message,
  not silently accepted and then discarded on the next regen.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As a squad author, I want to scope a custom skill to one or more roles so exactly those agents preload it

<!-- sq:story:US3:head -->
**Status:** 🟢 Done
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
## Acceptance criteria

- I can link a custom skill to one or more roles, and only those roles' agents preload it —
  unrelated roles are unaffected.
- I can unlink a skill from a role, and that role stops preloading it.
- Unscoping a skill entirely (removing its last role link) removes it from every role that had it,
  leaving no orphaned reference.
- A skill can be scoped to more than one role at once (the release-process use case: manager,
  devops, and tech-writer all preload the same skill).
- Trying to scope a skill to a role that doesn't exist gives a clear error, not a silently accepted
  broken link.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — As a squad author, I want role pointers to stay current when I link or unlink a skill without a manual full resync

<!-- sq:story:US4:head -->
**Status:** 🟢 Done
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
## Acceptance criteria

- Linking or unlinking a skill to/from a role updates that role's agent-facing pointer/skill list
  immediately, as part of the link/unlink command — I don't have to separately remember to run a
  full resync for the change to take effect.
- Only the affected role(s) are touched — other roles' pointers are left exactly as they were.
- The result is identical whether I reach the same end state via the targeted link/unlink command or
  via a full `sq sync` afterward — no drift between the two paths.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — As a squad author upgrading a squad, I want existing skills preserved unchanged

<!-- sq:story:US5:head -->
**Status:** 🟢 Done
<!-- sq:story:US5:head:end -->

<!-- sq:story:US5:body -->
## Acceptance criteria

- Running the upgrade/migration for this capability on an existing squad leaves every current
  skill (bundled and any pre-existing custom ones) present and functionally unchanged afterward —
  no skill disappears, gets renamed, or loses its existing description/when-to-use metadata.
- No existing role's preloaded-skill set changes as a side effect of the upgrade alone — role
  scoping only changes when I explicitly link/unlink a skill.
- `sq check` stays clean on an upgraded squad — the upgrade introduces no new warnings.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-20T08:42:22Z] Nina Product:
  - @manager FEAT-491 authored: custom-skill authored bodies + role scoping (5 stories, standalone — no epic fits: EPIC-31 is engine-internal only, EPIC-136 is post-1.0 backend-management). Refs BUG-490 (addresses). Architect's ADR (in flight) owns the mechanism — hold dispatch until it's accepted.
- [2026-07-20T09:02:22Z] Olivia Lead:
  - @manager FEAT-491 broken into 5 tasks (all Draft, refs ADR-492:implements + BUG-490:fixes). Breakdown for your build loop:
  - TASK-493 Authored custom-skill body (US1+US2): sq skill body verb + relax set_body meta-guard via derived is_system_skill(slug,spec); show labels system/custom. No deps — start here.
  - TASK-494 scopes ref kind + role→skill resolver (US3 data path): add scopes to VALID_REF_KINDS; service resolver unions system membership + inverted scopes backrefs, flows via BackendContext to BOTH pointer skills: YAML and role body ## Skills; AGENTS.md consistency test. No deps — parallel with 493.
  - TASK-495 link-role/unlink-role verbs + partial-sync hook (US3 verbs + US4). depends-on 494.
  - TASK-496 Schema 0.10→0.11 no-op stamp migration + CHANGELOG (US5). depends-on 494 (schema gate coordinated with the scopes kind).
  - TASK-497 Dogfood: author the release-process skill scoped to manager/devops/tech-writer — end-to-end proof, uses only the new surface. depends-on 493 + 495. NOTE: runbook CONTENT is yours to supply (prep-not-publish); the task validates the mechanism.
  - Ordering: 493 ∥ 494 first → 495 & 496 after 494 → 497 last. Left all Draft for you to promote+dispatch. Two under-specified points from the ADR flagged to me — see my return notes; neither blocks starting 493.
<!-- sq:discussion:end -->
