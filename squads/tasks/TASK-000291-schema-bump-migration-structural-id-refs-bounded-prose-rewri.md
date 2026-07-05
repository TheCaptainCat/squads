---
id: TASK-291
sequence_id: 291
type: task
title: 'Schema bump + migration: structural id/refs + bounded prose rewrite'
status: Done
parent: FEAT-283
author: tech-lead
refs:
- ADR-282
subentities:
- local_id: ST1
  title: Bump SCHEMA_VERSION; register Migration record + runner
  status: Done
  story: US3
- local_id: ST2
  title: 'Runner: structural id/refs + bounded, fence-skipping prose rewrite'
  status: Done
  story: US3
- local_id: ST3
  title: 'Migration test: mixed fixture, unpadded outside fences, idempotent'
  status: Done
  story: US3
created_at: '2026-07-04T20:45:37Z'
updated_at: '2026-07-04T23:23:27Z'
---
<!-- sq:body -->
## Scope

Ship the one-way migration that flips an existing squad's on-disk content to the unpadded
form, gated on a schema bump. Depends on the core display-unpadding task — the target form
(what the code now renders) must exist first. Filenames are left untouched. Authoritative
design: ADR-282; acceptance in FEAT-283 US3.

## Schema bump + registration

- Bump `_models/_schema.py::SCHEMA_VERSION` past `0.5` (compare via `schema_tuple`, never raw
  string `<`/`>`). The root CLI callback already hard-stops on a schema mismatch until
  `sq migrate up` runs — no callback change needed.
- Add a `Migration` record to `_migrations/_registry.py::MIGRATIONS` (from `0.5` → the new
  version) plus a private `_v0_5_to_v<new>.py` runner exposing `migrate(paths)` / async runner
  and a `MANUAL` runbook string, wired the same way as the existing entries. Never invoke the
  runner via `python -m` — only through `sq migrate`.

## Runner behaviour

1. Structural (deterministic): rewrite each item's frontmatter `id:` and every `refs:` entry to
   the unpadded form, driven by the stored `sequence_id`. Parent fields too if they carry a
   padded id.
2. Prose (bounded): rewrite padded ID mentions in body prose to unpadded — the same class of
   whole-word edit as the renumber path's `rewrite_ids` (`_itemfile.py:45`, `\bOLD\b → NEW`).
   Bound it to the exact old-form strings the migration already knows: iterate the index's
   `{padded → unpadded}` map per item and substitute those literals only. NEVER a blind
   "collapse any run of zeros" pattern — that could maul unrelated text. Skip fenced code blocks
   and inline code, where an ID may be a literal example, matching how retype/renumber already
   scope their mention rewrites.
3. Filenames untouched — they are already width-6 and stay width-6. No renames, so no git-rename
   churn and no path rewrite beyond `repair`.
4. Trailing `repair` rebuilds `.squads.json`, re-deriving both the display constant and the
   filename width from disk.
5. `MANUAL` runbook note: the prose rewrite is best-effort and worth an eyeball on
   mention-heavy bodies.

## Tests expected

- Migration test (behaviour-named, no ticket ID in the filename) over a mixed fixture: padded
  frontmatter `id:`, padded refs, padded prose mentions, AND a fenced code block containing a
  padded id that MUST be left alone. Assert the result is fully unpadded outside the fence, the
  fence content is untouched, and filenames are unchanged.
- Idempotence: a second run is a no-op.
- Full suite green; `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean.

## Out of scope

The display-unpadding code change, filename-seam fixes, and managed-artifact/golden regen —
those are the core task this one depends on.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 291 add-subtask "<title>"`; track with `sq task 291 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Bump SCHEMA_VERSION; register Migration record + runner | US3 |
| ST2 | Done |  | Runner: structural id/refs + bounded, fence-skipping prose rewrite | US3 |
| ST3 | Done |  | Migration test: mixed fixture, unpadded outside fences, idempotent | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Bump SCHEMA_VERSION; register Migration record + runner

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US3 — An existing squad migrates cleanly: structural id/refs + bounded prose rewrite, code fences untouched
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Bump _models/_schema.py::SCHEMA_VERSION past 0.5 (compare via schema_tuple, never raw string </>). The root CLI callback already hard-stops on a schema mismatch until sq migrate up runs, so no callback change is needed. Add a Migration record to _migrations/_registry.py::MIGRATIONS (from_schema 0.5 → the new version) plus a private _v0_5_to_v<new>.py runner exposing migrate(paths) and a MANUAL runbook string, wired like the existing entries (async or _wrap_sync). Never run the runner via python -m — only through sq migrate.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Runner: structural id/refs + bounded, fence-skipping prose rewrite

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US3 — An existing squad migrates cleanly: structural id/refs + bounded prose rewrite, code fences untouched
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Implement the runner. (1) Structural, deterministic: rewrite each item's frontmatter id: and every refs: entry (and any padded parent) to the unpadded form, driven by the stored sequence_id. (2) Prose, bounded: rewrite padded ID mentions in body prose to unpadded — the same whole-word class of edit as the renumber path's rewrite_ids (_itemfile.py:45, \bOLD\b → NEW). Bound it to the exact old-form strings the migration knows: iterate the index's {padded → unpadded} map per item and substitute those literals only — NEVER a blind zero-collapsing pattern. Skip fenced code blocks and inline code, matching how retype/renumber scope their mention rewrites. (3) Filenames untouched (already width-6). (4) Trailing repair rebuilds .squads.json, re-deriving both widths from disk. (5) MANUAL note: the prose rewrite is best-effort and worth an eyeball on mention-heavy bodies.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Migration test: mixed fixture, unpadded outside fences, idempotent

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US3 — An existing squad migrates cleanly: structural id/refs + bounded prose rewrite, code fences untouched
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Add a migration test (behaviour-named, no ticket ID in the filename) over a mixed fixture: padded frontmatter id:, padded refs, padded prose mentions, AND a fenced code block containing a padded id that must be left alone. Assert the result is fully unpadded outside the fence, the fence content is untouched, and filenames are unchanged. Assert idempotence: a second run is a no-op. Full suite green; uv run pyright && uv run ruff check . && uv run ruff format --check . clean.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-04T20:47:34Z] Olivia Lead:
  - Sequencing: depends on TASK-000290 (core display-unpadding). The migration rewrites on-disk content to the unpadded target form the code produces, so land TASK-000290 first; the schema bump here then hard-stops existing squads (including this repo's dogfood squad) until sq migrate up runs.
  - Split rationale: golden/managed-artifact regen lives in TASK-000290, not here — flipping display to unpadded breaks output-asserting goldens immediately, so the regen must ride in the same green PR as the code change. This task is cleanly separable (schema bump + runner + fixture test) and comes after.
- [2026-07-04T22:52:54Z] Elias Python:
  - Done: schema bumped 0.5 → 0.7 (_models/_schema.py); new runner _migrations/_v0_5_to_v0_7.py registered in _registry.py (version 0.7.0, from 0.5 to 0.7).
  - Runner rewrites every item's frontmatter id/refs/parent to the unpadded form (driven by sequence_id, width-tolerant ref reparse — no cross-file lookup needed) plus body-prose ID mentions, bounded to a discovery map built from each item's own prior frontmatter id, skipping fenced code blocks and inline code spans. Filenames untouched; idempotent (second pass returns 0).
  - Test: tests/test_unpadded_id_migration.py::test_migrate_unpads_frontmatter_refs_and_prose_but_skips_code_spans — mixed fixture (padded frontmatter id/parent/refs + a real prose mention + a fenced code block + an inline code span, both carrying a padded id) asserts everything outside code spans is unpadded, both code spans are byte-identical, filenames unchanged, edges still resolve, sq check is clean, and a second run is a no-op.
  - Also added corpus fixture tests/fixtures/corpus/v0_7 (frozen at schema 0.7) per the standing rule in tests/fixtures/corpus/README.md, wired into test_migration_corpus.py's _CORPUS_CASES; and fixed the schema-bump fallout in 6 pre-existing tests that pinned the old '0.5' literal (test_session_lineage.py x2, test_reflog_core.py, test_reflog_read.py x2 incl. the reflog_shape.json golden regen, test_cli.py::test_schema_gate_blocks_until_migrate).
  - Dogfooded on this repo: sq migrate up rewrote 287 of 291 item files (the other 4 were created after TASK-290 landed and were already unpadded); sq check clean (only pre-existing title-length advisories, no errors); sq list / sq tree EPIC-12 render unpadded and resolve; spot-checked FEAT-283/TASK-291 — frontmatter id unpadded, filename stays padded (FEAT-000283-...md). Ran sq sync after.
  - Gates: pyright 0 errors, ruff check + format clean, full suite green (exit 0, no failures) — logs at scratchpad/pytest-291.log (pre-migration run, 12 expected/fixed failures) and pytest-291-round2.log (post-dogfood-migration, clean).
  - sq migrate chlog v0.6.0..v0.7.0 surfaces the MANUAL runbook (prose rewrite is best-effort — worth an eyeball on mention-heavy bodies).
  - Moved TASK-291 to InReview; all 3 subtasks Done. @reviewer please review; @manager fyi. Did not self-review, did not commit, did not touch FEAT-283's status.
<!-- sq:discussion:end -->
