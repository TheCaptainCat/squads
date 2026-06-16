---
id: TASK-000147
sequence_id: 147
type: task
title: Emit canonical active_backends in the 0.2->0.3 migration
status: Done
parent: FEAT-000138
author: tech-lead
subentities:
- local_id: ST1
  title: Rewrite default_backend to active_backends in 0.2->0.3 migration
  status: Todo
  story: US3
created_at: '2026-06-16T14:18:32Z'
updated_at: '2026-06-16T14:59:43Z'
---
<!-- sq:body -->
## Problem

FEAT-000138 made `active_backends` the canonical 0.3 backend shape (no schema
bump — the config reader still reads legacy `default_backend` transparently).
But the `_v0_2_to_v0_3` migration (`src/squads/_migrations/_v0_2_to_v0_3.py`)
only transforms item `.md` files — it never rewrites `.squads.toml`'s backend
config. So a **migrated** 0.3 squad keeps the legacy `default_backend = "X"`
key on disk, while a **freshly `sq init`-ed** 0.3 squad writes
`active_backends = ["X"]`. Two on-disk shapes for the same schema: functional
(back-compat read, `sq check` clean) but untidy for a surface FEAT-000013
freezes at 1.0.

## Work

1. **Migration** — in `src/squads/_migrations/_v0_2_to_v0_3.py`, also rewrite
   `.squads.toml`'s `default_backend = "X"` → `active_backends = ["X"]`.
   - Idempotent: a toml already on `active_backends` is left untouched.
   - STAY on schema 0.3 — **no `SCHEMA_VERSION` bump, no new runner**. This is
     a tightening of the existing 0.2→0.3 runner, not a new migration step.
2. **Corpus fixture** — flip `tests/fixtures/corpus/v0_3/.squads.toml` to the
   canonical `active_backends` form (the canonical post-migration shape).
3. **Safety net** — keep the config reader's legacy-`default_backend`
   translation in place as a defensive read path, and pin it with a dedicated
   unit test proving a **hand-written legacy toml** (`default_backend = "X"`)
   still loads as `active_backends`.

## Acceptance

- A v0.2 squad migrated via `sq migrate up` ends with
  `active_backends = [...]` (and **no** `default_backend`) in `.squads.toml`,
  schema 0.3.
- Migration is idempotent: re-running over a toml already on `active_backends`
  leaves it unchanged.
- The migration-corpus tests pass against the updated `v0_3` fixture.
- A unit test proves the config reader still loads a legacy `default_backend`
  toml as `active_backends` (safety net intact).
- `sq check` clean; full gate green
  (`uv run pyright && uv run ruff check . && uv run ruff format --check . &&
  uv run pytest`).
- `SCHEMA_VERSION` is still `"0.3"`.

## Out of scope / no ADR needed

Design is settled by ADR-000141 (multi-active design) and op-pierre's no-bump
decision (active_backends is the canonical 0.3 shape; legacy `default_backend`
read transparently). This task is the tidy-up that makes the migrated on-disk
shape match the freshly-init'd one before the 1.0 freeze — no architecture
decision required.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 147 add-subtask "<title>"`; track with `sq task 147 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Rewrite default_backend to active_backends in 0.2->0.3 migration | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Rewrite default_backend to active_backends in 0.2->0.3 migration

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US3 — Migrate existing squads to active_backends schema
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-16T14:28:02Z] Elias Python:
  - Implementation complete. Gate: 839 passed, 1 skipped; pyright clean; ruff clean; sq check clean.
  - Migration rewrite (_v0_2_to_v0_3.py): added _migrate_toml() which reads .squads.toml via tomllib, checks for the idempotency condition (active_backends present + no default_backend → skip), then delegates normalisation to SquadsConfig.from_toml_dict() + to_toml() round-trip. The neither-key fallback resolves to active_backends = ["claude_code"] via the existing config model default. SCHEMA_VERSION stays 0.3; no new registry entry.
  - Corpus: tests/fixtures/corpus/v0_3/.squads.toml flipped to active_backends = ["claude_code"] (canonical post-migration shape). v0_2 fixture left with default_backend (keeps the migration non-vacuous).
  - Tests: test_v0_2_migration_rewrites_backend_key in test_migration_corpus.py — asserts precondition (v0_2 has default_backend, no active_backends), runs migration, then asserts post state has active_backends = ["claude_code"] and no default_backend. TestLegacyDefaultBackendRead in test_multi_active_backends.py — two tests: (1) legacy default_backend = "agents_md" (non-default name, non-vacuous) loads as active_backends = ["agents_md"]; (2) neither-key toml defaults to ["claude_code"].
  - @reviewer ready for review.
- [2026-06-16T14:37:22Z] Paul Reviewer:
  - @tech-lead @python-dev Reviewed in REV-000148 — verdict ChangesRequested. The shipped behavior is correct on every acceptance criterion: a v0.2 squad migrated via sq migrate up ends with active_backends=["claude_code"], no default_backend, schema_version "0.3", all other keys (squad_dir, default_role, squads_version) preserved intact; idempotent; SCHEMA_VERSION still 0.3, no new registry entry, no _v0_3_to_v0_4; back-compat reader tests are non-vacuous; full gate green (pyright/ruff/format/pytest) and sq check clean.
  - One Medium finding (F1): the regression pin is vacuous. test_v0_2_migration_rewrites_backend_key does NOT fail if _migrate_toml is removed — I deleted the call and both the corpus test and the full migrate-up flow still produced a canonical active_backends toml. Reason: _stamp_schema(SCHEMA_VERSION) re-serializes via to_toml() (which only ever emits active_backends) after the runner, and from_toml_dict() already translated the legacy key on load — so the stamp path normalizes the toml on its own. _migrate_toml has zero direct test coverage. The task acceptance claims 'the corpus test would fail if the rewrite were removed' — that is not true. This is the same failure mode as BUG-000134 (a test of mechanics, not the thing it claims to pin).
  - Small fix: add a direct unit test of _migrate_toml(paths) — assert (a) a default_backend toml is rewritten to active_backends with the legacy key gone and all other keys preserved, (b) the active_backends-only idempotency short-circuit leaves the file unchanged, and (c) the neither-key->["claude_code"] branch. These exercise the helper without the stamp masking it. (Or, if _migrate_toml is intended purely as defensive intent given the stamp already normalizes, say so explicitly and pin (b)/(c).) See REV-000148 F1/F2 for detail.
- [2026-06-16T14:50:03Z] Elias Python:
  - REV-000148 F1 addressed: removed the _migrate_toml helper and its call in migrate() from src/squads/_migrations/_v0_2_to_v0_3.py. The helper was redundant — run_pending_migrations calls _stamp_schema(SCHEMA_VERSION) after the runner, which re-serializes the config via SquadsConfig.to_toml() (only ever emits active_backends), and from_toml_dict() already translates the legacy default_backend key on load. The stamp path alone canonicalizes the TOML; no explicit runner step is needed.
  - Also removed the now-unused imports: tomllib, CONFIG_FILENAME, SquadsConfig.
  - Kept: tests/fixtures/corpus/v0_3/.squads.toml with canonical active_backends = ['claude_code']. Kept: test_v0_2_migration_rewrites_backend_key (pins the end-to-end contract via the stamp — updated docstring to explain the mechanism). Kept: TestLegacyDefaultBackendRead (non-vacuous back-compat reader tests).
  - Gate: 839 passed, 1 skipped; pyright 0 errors; ruff check clean; ruff format clean (112 files); sq check clean. @reviewer ready for re-review.
- [2026-06-16T14:59:02Z] Paul Reviewer:
  - @tech-lead @python-dev Re-review complete — REV-000148 APPROVED, F1 Verified. Cleared for Done.
  - F1 resolution confirmed: the redundant _migrate_toml helper and its call are fully removed (grep: zero references in src/ or tests/), along with the now-unused tomllib/CONFIG_FILENAME/SquadsConfig imports. The _v0_2_to_v0_3.py diff vs HEAD is docstring-only; migrate() is back to item-files-only with no logic change.
  - The canonical-active_backends contract is still pinned — now at the flow level, which is the correct place. test_v0_2_migration_rewrites_backend_key copies the v0_2 fixture, runs run_pending_migrations(), and asserts the migrated .squads.toml carries active_backends=['claude_code'] and NO default_backend. That guard fails if the stamp path ever stops normalizing (to_toml() emitting default_backend, or from_toml_dict() dropping the legacy translation), so it is a real regression pin, not vacuous. The redundant helper that masked it is gone.
  - Fixtures: v0_3 stays canonical (active_backends), v0_2 stays legacy (default_backend) — keeps the migration non-vacuous. TestLegacyDefaultBackendRead retained and non-vacuous (uses agents_md, a non-default name the model default can't fake).
  - Confirmed: SCHEMA_VERSION still '0.3'; _registry.py and _schema.py unchanged (no new runner).
  - Gate green: 839 passed / 1 skipped; pyright 0 errors; ruff check clean; ruff format clean (112 files); sq check clean.
<!-- sq:discussion:end -->
