---
id: TASK-496
sequence_id: 496
type: task
title: Schema 0.10 to 0.11 no-op stamp migration
status: Done
parent: FEAT-491
author: tech-lead
refs:
- ADR-492:implements
- BUG-490:fixes
- TASK-494:depends-on
description: Bump SCHEMA_VERSION, add mechanical no-op runner + registry entry, CHANGELOG;
  verify clean upgrade + repair round-trip
subentities:
- local_id: ST1
  title: Upgrade preserves existing skills and scoping
  status: Done
  story: US5
created_at: '2026-07-20T08:59:20Z'
updated_at: '2026-07-20T10:48:51Z'
---
<!-- sq:body -->
## Scope

Bump the schema so a pre-`scopes` client is hard-stopped before it meets a `scopes` edge —
ADR-492's "Schema and migration" section. No frontmatter **shape** changes: the classification
is derived (nothing stamped) and the scope edge reuses the `ID:kind` ref shape. The only
forward-compat hazard is the new `scopes` ref kind, which an old client would `sq check`-warn on
and silently ignore — exactly what the schema gate exists to prevent. This must land coordinated
with the `scopes` kind (see the depends-on edge).

### 1. Bump `SCHEMA_VERSION`

`_models/_schema.py::SCHEMA_VERSION` 0.10 → 0.11. The root CLI callback then hard-stops an older
client with "run `sq migrate up`".

### 2. No-op stamp migration

Add a private runner `_migrations/_v0_10_to_v0_11.py` that touches no files and returns 0, with
`MANUAL = ""` (fully mechanical, no runbook). Append a `Migration` entry to
`_migrations/_registry.py` (`from_schema="0.10"`, `to_schema="0.11"`, one-line `summary`; the
`version` release string is a release-time decision — coordinate with the release owner). There
is no "flag bundled skills as system" step — the classification is derived, so there is nothing
to stamp. `run_pending_migrations` runs `repair` and stamps 0.11 as usual.

### 3. CHANGELOG

Add the changelog entry for the schema bump + the capability, following the project's changelog
conventions (adopter-facing wording — describe the tool, no repo/sq-internal refs).

## Acceptance

- `sq migrate up` on an existing squad moves it to schema 0.11 with every skill (bundled and any
  pre-existing custom) present and functionally unchanged — nothing disappears, is renamed, or
  loses its description/when-to-use.
- No role's preloaded-skill set changes as a side effect of the upgrade alone (scoping changes
  only on explicit link/unlink).
- `sq check` stays clean on an upgraded squad (no new warnings).
- `sq repair` round-trips an authored custom-skill body (left untouched) and the `scopes` edges
  (read back from frontmatter refs) — proving invariant #1 holds for the skill file type.
- Tests: a migration/meta test upgrading a fixture squad; a repair round-trip covering an
  authored body + a scopes edge. Name tests by behaviour, not by ticket id.

## Code sites

- `src/squads/_models/_schema.py` — `SCHEMA_VERSION`.
- `src/squads/_migrations/_v0_10_to_v0_11.py` (new) + `_migrations/_registry.py`.
- `CHANGELOG.md`.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 496 add-subtask "<title>"`; track with `sq task 496 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Upgrade preserves existing skills and scoping | US5 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Upgrade preserves existing skills and scoping

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US5 — As a squad author upgrading a squad, I want existing skills preserved unchanged
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Schema 0.10->0.11 no-op stamp migration: every existing skill stays present/unchanged, no role's preload set changes from the upgrade alone, sq check stays clean, and repair round-trips authored bodies + scopes edges.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-20T10:35:56Z] Elias Python:
  - @manager Bumped SCHEMA_VERSION 0.10->0.11; added the no-op runner (_v0_10_to_v0_11.py, touches no files) + registry entry (version 0.11.0).
  - Migrated THIS repo up (sq migrate up): squads/.squads.toml + .squads.json now stamp 0.11; sq check clean; normal sq commands work.
  - Tests: new tests/integration/test_schema_upgrade_preserves_skills_and_scoping.py proves the runner is a genuine no-op, a downgraded-to-0.10 squad reaches 0.11 idempotently, an authored custom-skill body + scopes edges to two roles survive the upgrade unchanged (no role's resolved skill set shifts), and a pre-0.11 stamp hard-stops with a clear 'sq migrate up' pointer. Added a v0_11 corpus fixture + registered it in the corpus parametrize list per the corpus README's standing rule. Fixed two now-stale hardcoded SCHEMA_VERSION=="0.10" assertions (test_v0_3_migration_chain_reaches_current_schema.py, test_memory_skill_migration.py).
  - Gates: pyright + ruff clean; tests/meta green; targeted -k "migrat or schema or repair or skill" green (146 passed, 1 skipped). CHANGELOG has the Migration note under Unreleased. Did not touch pyproject.toml/templates_manifest.json (release-prep, separate).
- [2026-07-20T10:42:16Z] Elias Python:
  - @manager Fixed the golden miss: tests/goldens/reflog_shape.json pinned schema_version "0.10", now "0.11" (test_reflog_cli.py asserts it equals SCHEMA_VERSION).
  - Swept for other stale schema pins (grep '"0.10"|0.10\b' across tests/ + src/squads/): everything else checks out as intentional — the v0_10 corpus fixture (old-schema by design), the 0.8->0.10 from/to_schema registry entries and docstrings, the migration-chain test's intermediate 0.10 step, and my own TASK-496 test's deliberate downgrade-to-0.10 simulations. Only the reflog golden was stale; nothing else needed bumping.
  - Re-verified: pyright + ruff clean; tests/meta green (23); tests/cli/test_reflog_cli.py green (11); -k "golden or schema or reflog" green (all passed). Did not run the full suite.
<!-- sq:discussion:end -->
