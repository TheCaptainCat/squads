---
id: FEAT-574
sequence_id: 574
type: feature
title: Docs accuracy + drift guard for CLI verbs
status: Draft
author: product-owner
refs:
- REV-565
subentities:
- local_id: US1
  title: Fix role-catalog/add-story/add-subtask verb drift in docs
  status: Todo
- local_id: US2
  title: Refresh stale override-base version examples in docs/overrides.md
  status: Todo
- local_id: US3
  title: Cross-link the custom-role path for non-code/designer roles
  status: Todo
- local_id: US4
  title: Add a docs command-test that shells documented verbs against the live CLI
  status: Todo
created_at: '2026-07-22T08:40:00Z'
updated_at: '2026-07-22T08:40:55Z'
---
<!-- sq:body -->
## Capability

Correct the CLI-verb and version drift in the shipped docs, and add a mechanical
guard so this class of drift can't silently recur.

Concretely:
- `docs/roles.md`, `docs/recipes.md`, `docs/agents.md`: replace the non-existent
  `sq role list` / `sq role list --available` with `sq role catalog` (bundled
  catalog) — the active roster is enumerated a different way (see FEAT-575 for
  the `sq role list` verb gap itself; this feature is the doc correction only).
- `docs/adoption.md`, `docs/tutorial.md`: replace `story add FEAT-7 "…"` / `subtask
  add TASK-8 "…"` with the real verbs, `sq feature 7 add-story "…"` / `sq task 8
  add-subtask "…"`.
- `docs/overrides.md`: refresh the stale `override-base:0.4.2` example strings
  (installed version is well past that) — either bump the examples to track the
  current release or make them version-agnostic so they stop reading as an old
  release.
- `docs/roles.md` / `docs/agents.md`: document the custom-role path
  (`.overrides/roles/<slug>.toml` scaffold + `sq role activate`) as the answer
  for a non-code/designer/UX-style role — the walkthrough already exists in
  `docs/overrides.md` (the `compliance-officer` example); this is a cross-link
  from the "I need a role that isn't a coding `--tech`" spot, not new mechanism.
- A **docs command-test**: a test that extracts the exact `sq …` invocations
  shown in the docs (or a curated subset of verb-name assertions) and shells
  them against the current CLI's `--help` tree, failing the build if a
  documented verb no longer exists. This is the durable part — it's what stops
  the verb drift (and ideally the version-string drift) from recurring
  unnoticed between releases.

## Why

Adopter field report REV-565 (Nabudoc migration, squads 0.11.1) hit three
separate doc/CLI mismatches while following the shipped docs verbatim: `sq role
list --available` and `story add`/`subtask add` don't exist, and the
override-base example version reads as stale. Each individually is a low-medium
severity nuisance, but together they eroded trust in the docs during a
first-adoption session — exactly when an adopter has the least slack to
debug drift themselves. A mechanical guard is worth more than a one-time fix:
without it, the same class of drift will recur at the next verb rename.

## Acceptance

- No occurrence of `role list`, `--available`, `story add`, or `subtask add` as
  a documented invocation remains in `docs/`.
- `docs/overrides.md`'s override-base examples no longer cite a version behind
  the current release (or are phrased so they never can).
- `docs/roles.md` or `docs/agents.md` has a short pointer to the
  `.overrides/roles/<slug>.toml` + `sq role activate` path for a role that
  isn't a coding `--tech`.
- A new test shells the verb sequences documented for role/story/subtask
  creation against the live CLI and fails if any no longer resolves; it runs
  as part of the normal `uv run pytest` gate (not a separate opt-in step).
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 574 add-story "As a <role>, I want … so that …"`; track with `sq feature 574 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Fix role-catalog/add-story/add-subtask verb drift in docs |
| US2 | Todo |  | Refresh stale override-base version examples in docs/overrides.md |
| US3 | Todo |  | Cross-link the custom-role path for non-code/designer roles |
| US4 | Todo |  | Add a docs command-test that shells documented verbs against the live CLI |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Fix role-catalog/add-story/add-subtask verb drift in docs

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
Correct docs/roles.md, docs/recipes.md, docs/agents.md, docs/adoption.md, docs/tutorial.md to use the real verbs (sq role catalog; add-story/add-subtask on the addressed item), not the non-existent ones (F3, F5).
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Refresh stale override-base version examples in docs/overrides.md

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
Replace the 0.4.2-era example strings so they don't read as an old release; prefer a version-agnostic phrasing where practical (F6).
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Cross-link the custom-role path for non-code/designer roles

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
Add a short pointer in docs/roles.md or docs/agents.md to the .overrides/roles/<slug>.toml + sq role activate walkthrough already in docs/overrides.md, for a role that isn't a coding --tech (F7 doc note).
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Add a docs command-test that shells documented verbs against the live CLI

<!-- sq:story:US4:head -->
**Status:** ⚪ Todo
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
Mechanical guard: extract/assert the sq invocations shown in the docs and fail the build if a documented verb no longer resolves (covers F3+F5+F6 recurrence).
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
