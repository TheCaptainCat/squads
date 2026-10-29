---
id: FEAT-1242
sequence_id: 1242
type: feature
title: Dependencies current and tested
status: Draft
author: product-owner
priority: high
refs:
- MILE-1241:targets
description: 'The versions an adopter installs are the versions the suite runs: runtime
  and dev dependencies upgraded, lower bounds raised'
subentities:
- local_id: US1
  title: Runtime dependencies upgraded, bounds raised to what is tested
  status: Todo
- local_id: US2
  title: Development tools current, gates clean
  status: Todo
created_at: '2026-10-29T12:59:18Z'
updated_at: '2026-10-29T12:59:54Z'
---
<!-- sq:body -->
## Problem

The lower bounds in `pyproject.toml` are older than the versions this project's lock file installs and its suite runs. An adopter whose resolver picks a bound, or a newer major, gets a combination nobody tested. Several runtime dependencies have moved: typer 0.27 changes its error wording and the names it gives refused parameters, which the CLI's usage errors print; filelock 4 is a major version and holds the index lock that keeps concurrent writers safe; pydantic 2.14 and anyio carry the models and the store's locking. The development tools (ruff 0.17, pyright, pytest) are behind too, so the gates check against rules adopters' contributors no longer run.

## Goal

The versions an adopter installs are the versions the suite runs.

## Scope

- Runtime dependencies upgraded to their current releases: typer 0.27, filelock 4, pydantic 2.14, anyio, and the daemon's server dependencies at the versions the daemon ships with.
- Development tools upgraded: ruff 0.17, pyright, pytest and its plugins, with the code brought clean under their new rules.
- Every lower bound in `pyproject.toml` raised to the version the suite runs.

## Non-goals

- New features or behaviour changes beyond what an upgrade forces.
- Supporting older versions than the raised bounds.

## Acceptance criteria

- The full suite, pyright, ruff and `sq check` pass on Linux, macOS and native Windows with the upgraded versions.
- Every declared lower bound is a version the suite ran against.
- Any adopter-visible change an upgrade causes (an error message, a usage-error parameter name) is either kept identical or listed in the changelog.
- Concurrent writers stay safe under the new index lock: the store's lock tests pass, and the lock still releases on process death.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1242 add-story "As a <role>, I want … so that …"`; track with `sq feature 1242 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Runtime dependencies upgraded, bounds raised to what is tested

<!-- sq:story:US1:body -->
As an adopter, I install squads with any versions its declared bounds allow and get the behaviour the suite tested, error messages included.

Done when:
- typer 0.27, filelock 4, pydantic 2.14 and current anyio are the locked versions, and the full suite passes on Linux, macOS and native Windows.
- Every runtime lower bound in `pyproject.toml` is raised to the version the suite runs.
- Usage errors keep their exit code 2; where typer 0.27 changes their wording or the name of a refused parameter, the surface tests assert the new text and the changelog lists the change for adopters who match on it.
- Two concurrent writers still serialise on the index lock under filelock 4, its wait notice and timeout behave as before, and the lock is released when its holder dies.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Development tools current, gates clean

<!-- sq:story:US2:body -->
As a contributor, the gates I run locally are the ones CI runs, on current tools.

Done when:
- ruff 0.17, current pyright and current pytest with its plugins are the locked development versions, and their lower bounds are raised to match.
- `pyright`, `ruff check`, `ruff format --check` and the full suite are clean under them, with any newly reported issue fixed in code rather than silenced, unless a suppression carries a one-line reason.
- CI installs the same locked versions.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T12:59:54Z] `product-owner` Nina Product:
  - Created 2026-10-29 per op-pierre e9859e1 for 0.18.1 (MILE-1241). US1 runtime upgrades and raised bounds (typer 0.27, filelock 4, pydantic 2.14, anyio), US2 dev tools (ruff 0.17, pyright, pytest). No epic fits, so it has no parent. @tech-lead please break it into tasks.
<!-- sq:discussion:end -->
