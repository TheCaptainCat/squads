---
id: REV-148
sequence_id: 148
type: review
title: 'Review: emit canonical active_backends in 0.2->0.3 migration (TASK-000147)'
status: Approved
author: reviewer
refs:
- TASK-147
- FEAT-138
- ADR-141
description: Independent review of the 0.2->0.3 TOML backend rewrite
subentities:
- local_id: F1
  title: 'Regression pin is vacuous: corpus test passes without _migrate_toml'
  status: Verified
  severity: medium
- local_id: F2
  title: 'Confirmed correct: round-trip preserves all config keys + schema stamp stays
    0.3'
  status: Open
  severity: info
created_at: '2026-06-16T14:35:57Z'
updated_at: '2026-06-16T14:58:51Z'
---
<!-- sq:body -->
Independent review of TASK-147: making _v0_2_to_v0_3 emit canonical active_backends in .squads.toml. Verified the migrated on-disk shape, schema stamp, idempotency, back-compat reader, and the full gate. Behavior is correct; one test-coverage finding on non-vacuousness.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 148 add-finding "…" --severity high`; track with `sq review 148 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Verified |  | Regression pin is vacuous: corpus test passes without _migrate_toml |
| F2 | 🔵 info | Open |  | Confirmed correct: round-trip preserves all config keys + schema stamp stays 0.3 |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Regression pin is vacuous: corpus test passes without _migrate_toml

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
test_v0_2_migration_rewrites_backend_key (tests/test_migration_corpus.py) is intended to pin the new _migrate_toml rewrite — the task acceptance states 'the corpus test would fail if the rewrite were removed.' Empirically it does NOT: I deleted the 'if _migrate_toml(paths): changed += 1' call from migrate() and the corpus test still passed, and the full migrate-up flow still produced a canonical active_backends toml.

Root cause: run_pending_migrations() (src/squads/_services/_maintenance.py:160-162) calls _stamp_schema(SCHEMA_VERSION) AFTER the runner, which re-serializes the config via SquadsConfig.to_toml(). to_toml() only ever emits active_backends (never default_backend), and from_toml_dict() already translated the legacy key on load. So the stamp path alone normalizes the toml — _migrate_toml is redundant for the real migrate flow, and no test exercises it in isolation (grep: zero direct references in tests/).

Impact: the rewrite behavior is correct and the acceptance end-state holds, but the test does not actually guard the helper. This is exactly the failure mode BUG-134 was raised for (a suite that tests mechanics, not the thing it claims to). Before the 1.0 freeze the pin should be real.

Suggested fix (small): add a direct unit test that calls _v0_2_to_v0_3._migrate_toml(paths) on a fixture toml carrying default_backend and asserts the file is rewritten to active_backends with default_backend gone and all other keys preserved — OR assert the byte-for-byte idempotency short-circuit (active_backends-only toml left unchanged) and the neither-key->['claude_code'] branch, which the stamp path cannot mask. Alternatively, document _migrate_toml explicitly as defensive/intent-only given the stamp already normalizes.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-06-16T14:49:50Z] Elias Python:
  - Addressed per op-pierre's decision: _migrate_toml removed as redundant. The helper was dead code — run_pending_migrations already canonicalizes the TOML via to_toml() in the stamp step, and from_toml_dict() already translates the legacy key on load. The corpus test test_v0_2_migration_rewrites_backend_key is kept (it still proves the end-to-end contract) with a comment explaining that the canonicalization comes from the schema-stamp re-serialization, not an explicit migration step. Back-compat reader tests (TestLegacyDefaultBackendRead) retained. Gate: 839 passed, 1 skipped; pyright 0 errors; ruff clean; sq check clean.
- [2026-06-16T14:58:28Z] Paul Reviewer:
  - Verified: _migrate_toml fully removed (grep: zero references in src/ or tests/). _v0_2_to_v0_3.py diff vs HEAD is docstring-only — migrate() is back to item-files-only, no logic change. Now-unused imports (tomllib, CONFIG_FILENAME, SquadsConfig) also gone. The end-to-end contract still holds via the schema-stamp path: to_toml() only emits active_backends, from_toml_dict() translates+discards legacy default_backend. test_v0_2_migration_rewrites_backend_key drives run_pending_migrations and asserts post has active_backends and NOT default_backend — a real regression guard at the flow level (fails if to_toml regresses or from_toml_dict stops translating). v0_3 fixture canonical, v0_2 stays legacy (non-vacuous). TestLegacyDefaultBackendRead retained and non-vacuous (agents_md non-default name). Gate green: 839 passed/1 skipped, pyright 0 errors, ruff + format clean, sq check clean.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Confirmed correct: round-trip preserves all config keys + schema stamp stays 0.3

<!-- sq:finding:F2:head -->
**Status:** 🔴 Open
**Severity:** 🔵 Info
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
Empirical check (copy tests/fixtures/corpus/v0_2, chdir, sq migrate up). Before: schema_version=0.2, default_backend=claude_code, squad_dir='.', default_role=manager, squads_version=0.2.0. After: schema_version="0.3", squad_dir=".", active_backends=["claude_code"], default_role="manager", squads_version="0.2.0". No keys dropped or corrupted; default_backend removed; schema stamped to 0.3 (re-stamped by _stamp_schema, not regressed by the rewrite). squads_version correctly NOT bumped (that is sq sync's job).

Idempotency confirmed two ways: (1) re-running sq migrate up on the migrated squad -> 'already at schema v0.3; nothing to migrate', toml unchanged; (2) migrating the v0_3 fixture (already active_backends) -> unchanged. The schema-version gate in run_pending_migrations prevents re-entry, and _migrate_toml's own active_backends-only short-circuit is belt-and-suspenders.

No-bump / no-runner confirmed: SCHEMA_VERSION still '0.3'; _migrations/_registry.py MIGRATIONS unchanged (no new entry); no _v0_3_to_v0_4 module. Corpus: v0_3 fixture canonical active_backends, v0_2 stays default_backend. Back-compat reader tests (TestLegacyDefaultBackendRead) are non-vacuous — the agents_md case (non-default name) genuinely fails if from_toml_dict translation is dropped; neither-key case proves never-silent-sq-only.

Gate: pyright 0 errors; ruff check passed; ruff format clean (112 files); sq check clean (no issues); pytest green (1 skipped). Behavior fully meets acceptance.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
