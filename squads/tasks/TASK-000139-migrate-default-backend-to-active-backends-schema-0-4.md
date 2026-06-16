---
id: TASK-000139
sequence_id: 139
type: task
title: Migrate default_backend to active_backends (schema 0.4)
status: Cancelled
parent: FEAT-000138
author: tech-lead
priority: high
subentities:
- local_id: ST1
  title: Bump SCHEMA_VERSION 0.3→0.4, add _v0_3_to_v0_4 runner (default_backend→active_backends
    in .squads.toml) + register it, commit a v0_4 corpus fixture and wire it into
    _CORPUS_CASES
  status: Done
  story: US3
created_at: '2026-06-16T09:39:30Z'
updated_at: '2026-06-16T12:43:45Z'
---
<!-- sq:body -->
## Goal

Bump the durable schema for the `default_backend` → `active_backends` shape and
prove the migration with a corpus fixture. This is the data-migration half of
FEAT-000138; the runtime/config-consumer half is TASK-000140.

## Work

- **`SCHEMA_VERSION` bump** `0.3` → `0.4` in `src/squads/_models/_schema.py`
  (single source of truth; compare with `schema_tuple`, never raw string).
- **New migration runner** `src/squads/_migrations/_v0_3_to_v0_4.py` with
  `migrate(paths) -> int` + a `MANUAL` runbook string, then register it in
  `src/squads/_migrations/_registry.py::MIGRATIONS` (release `version`, `0.3`→
  `0.4`, one-line `summary`). The transform rewrites `.squads.toml`:
  `default_backend = "X"` → `active_backends = ["X"]`. Decide (per ADR) how a
  missing/empty source maps — likely `[]` only if explicitly empty, else the
  single value. Migration touches `.squads.toml`, not item frontmatter, so the
  returned count reflects configs rewritten.
- **Corpus fixture** (FEAT-000017 standing rule, `tests/fixtures/corpus/README.md`):
  copy current `v0_3` as `v0_4` representing the *new* current schema, keep `v0_3`
  as the now-previous from-schema, add `("0.3", "v0_3")` (and the new current) to
  `_CORPUS_CASES` in `tests/test_migration_corpus.py`; verify
  `test_corpus_migrates_to_current_and_passes_check` green for all entries. The
  v0_3 fixture's `.squads.toml` must carry the singular `default_backend` so the
  new runner is actually exercised (not vacuous — REV-000130 lesson).

## Coordination

The config-model change (`SquadsConfig.default_backend` → `active_backends`)
lives in TASK-000140 and is the shared seam: this task's migration writes the new
TOML key, TASK-000140's model reads it. Land 139's schema bump + runner first (or
in lock-step) so the corpus migrates to a shape 140's model can parse. Expect an
ADR to fix the exact mapping before either starts.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 139 add-subtask "<title>"`; track with `sq task 139 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Bump SCHEMA_VERSION 0.3→0.4, add _v0_3_to_v0_4 runner (default_backend→active_backends in .squads.toml) + register it, commit a v0_4 corpus fixture and wire it into _CORPUS_CASES | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Bump SCHEMA_VERSION 0.3→0.4, add _v0_3_to_v0_4 runner (default_backend→active_backends in .squads.toml) + register it, commit a v0_4 corpus fixture and wire it into _CORPUS_CASES

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
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
- [2026-06-16T12:27:21Z] Elias Python:
  - Implemented TASK-000139 (schema 0.3→0.4 migration) per ADR-000141.
  - SCHEMA_VERSION bumped 0.3→0.4 in _models/_schema.py.
  - New runner _migrations/_v0_3_to_v0_4.py: rewrites .squads.toml only, mapping default_backend='X'→active_backends=['X']; missing/empty default_backend→['claude_code'] (ADR-141 §1 — never silently orphan a CLAUDE.md; empty is reachable only by deliberate operator intent, not migration). Idempotent: if active_backends already present, leaves it untouched.
  - Registered in _migrations/_registry.py as Migration(version='0.4.0', from_schema='0.3', to_schema='0.4').
  - Corpus fixture: v0_3 kept with singular default_backend (runner is non-vacuous — REV-130 lesson); v0_4 added with active_backends=['claude_code'] and schema_version='0.4'. Added ('0.4','v0_4') to _CORPUS_CASES in test_migration_corpus.py. Added minimal CLAUDE.md/.claude/settings.json stubs to all corpus fixtures so the new backend-present check passes (ADR-141 §4).
  - Full gate: 808 passed, 1 skipped. Pyright 0 errors. Ruff clean.
  - @reviewer ready for review. @qa please verify corpus migration runs and check passes.
- [2026-06-16T12:32:04Z] Elias Python:
  - TASK-139 final state: corpus migration now fully non-vacuous. v0_3 fixture retains default_backend='claude_code' (triggers the 0.3→0.4 runner). v0_4 fixture has active_backends=['claude_code']. All corpus test cases pass. Gate: 821 passed, 1 skipped.
- [2026-06-16T12:43:45Z] Catherine Manager:
  - Cancelled per op-pierre (2026-06-16): we stay on schema 0.3 — no 0.4 bump, no migration. The active_backends change folds into the in-development 0.3 schema via the config's transparent legacy default_backend read (delivered in TASK-000140), so this migration task is void.
<!-- sq:discussion:end -->
