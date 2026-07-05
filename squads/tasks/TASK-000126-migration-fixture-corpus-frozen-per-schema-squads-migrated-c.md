---
id: TASK-126
sequence_id: 126
type: task
title: 'Migration fixture corpus: frozen per-schema squads migrated + checked in CI'
status: Done
parent: FEAT-17
author: tech-lead
created_at: '2026-06-15T12:10:12Z'
updated_at: '2026-06-15T12:31:51Z'
---
<!-- sq:body -->
## Approach

Today migrations are exercised only by synthetic 'devolve-in-test' fixtures (tests/test_migrations.py reconstructs a 0.2/0.1 shape from a live item, then migrates). FEAT-17 wants the real promise tested: a frozen, committed squad per released schema version, migrated up to current and `sq check`-ed, run in CI on every push.

Build a committed corpus of full squad trees, one per released schema version (currently 0.1, 0.2, 0.3), under a new fixtures dir (e.g. tests/fixtures/corpus/v0_1/, v0_2/, v0_3/ — each a complete squad: squads/ tree + .squads.json). A pytest test parametrized over the corpus dirs that, for each: copies it to tmp_path, runs the migration chain (svc.run_pending_migrations() via _services/_maintenance.py, the same path `sq migrate up` uses), then runs svc.check() and asserts zero error-level issues. A CLI smoke test mirroring it via `sq migrate up` + `sq check` (exit 0) with CliRunner.

Document the 'add a fixture on every schema bump' rule next to the migration registry contract — when SCHEMA_VERSION bumps and a runner is appended to _migrations/_registry.py::MIGRATIONS, a new vN_M fixture must be committed. Add a short note in tests/fixtures/corpus/README.md and/or the migrations runbook so future bumps don't skip it.

## Files / dirs to touch
- NEW: tests/fixtures/corpus/v0_1/, v0_2/, v0_3/ (frozen committed squad trees, one per released schema)
- NEW: tests/test_migration_corpus.py (parametrized: copy → run_pending_migrations → check, asserts no errors; + a CLI smoke via 'sq migrate up' && 'sq check')
- NEW: tests/fixtures/corpus/README.md (the 'add a fixture per schema bump' rule)
- READ-ONLY seams: src/squads/_migrations/_registry.py (MIGRATIONS), src/squads/_services/_maintenance.py (run_pending_migrations/repair), src/squads/_cli/_migrate.py, src/squads/_cli/_main.py::check
- Possibly .github/workflows/test.yml ONLY IF the corpus must be a distinct CI step — by default it runs inside the existing 'uv run pytest', so prefer NOT touching CI.

## Acceptance (from FEAT-17)
CI runs the fixture corpus: every released schema migrates to current and passes `sq check`. A new fixture is added with every future schema bump (documented as a standing rule).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 126 add-subtask "<title>"`; track with `sq task 126 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-15T12:22:21Z] Mara Tester:
  - Implemented migration fixture corpus for FEAT-17 hardening.
  - Created 3 frozen squads under tests/fixtures/corpus/: v0_1 (schema 0.1 — legacy heading-encoded sub-entities, bare refs + extra.ref_kinds), v0_2 (schema 0.2 — :meta body regions, inline ref kinds, findings skeleton), v0_3 (schema 0.3 — current: sequence_id in frontmatter, subentities list, :head regions). Each corpus dir has .squads.toml, .squads.json, and item md files authored at that schema's on-disk shape.
  - tests/test_migration_corpus.py has 6 tests parametrized over all three versions: a service-level test (copies corpus → run_pending_migrations → asserts schema reaches 0.3 + sq check has zero errors) and a CLI smoke test (monkeypatch.chdir → sq migrate up → sq check, both exit 0).
  - Gate: 713 passed, 1 skipped (all pre-existing); pyright 0 errors; ruff clean. No out-of-scope failures.
  - @reviewer please review tests/test_migration_corpus.py and tests/fixtures/corpus/ before merging.
- [2026-06-15T12:30:15Z] Paul Reviewer:
  - REV-130: APPROVED. Migration fixture corpus is non-vacuous — verified independently. v0_1 genuinely starts at schema 0.1 (extra.ref_kinds, legacy '[ ] … (→ US1)' checkbox headings, no sequence_id/:meta) and a real 'sq migrate up' fires BOTH the 0.1->0.2 and 0.2->0.3 runners to reach 0.3; v0_2 genuinely starts at 0.2 (inline ID:kind refs, :meta regions, no subentities/sequence_id) and exercises the 0.2->0.3 lift; v0_3 is a legitimate current no-op. Test asserts reaching SCHEMA_VERSION + a clean check (service + CLI smoke). One LOW finding (F1): the corpus does not exercise the 0.1->0.2 review findings-skeleton branch (v0_1/reviews/ is empty; v0_2's review already has a :findings container). Non-blocking — that branch has unit coverage in test_migrations.py and the acceptance bar is met. Optional follow-up to close the gap. @tech-lead
<!-- sq:discussion:end -->
