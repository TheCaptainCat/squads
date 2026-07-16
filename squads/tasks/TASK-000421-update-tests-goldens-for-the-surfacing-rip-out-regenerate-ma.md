---
id: TASK-421
sequence_id: 421
type: task
title: Update tests + goldens for the surfacing rip-out; regenerate manifest
status: Done
parent: FEAT-315
author: tech-lead
assignee: python-dev
refs:
- REV-419:addresses
- FEAT-317:addresses
- FEAT-416:addresses
- TASK-420:depends-on
created_at: '2026-07-15T12:42:17Z'
updated_at: '2026-07-15T13:14:42Z'
---
<!-- sq:body -->
# Scope

Sibling to the source rip-out task: update/delete the tests and generated fixtures the rip-out
invalidates, regenerate the template manifest, and hand full-suite + golden verification to the
main loop. Same dev, sequential — this pass turns the suite back green. No production code changes
here beyond the regenerated manifest artifact.

## Delete outright

- `tests/unit/test_content_index_generator.py` — the generator is gone.

## Boot-surfacing tests — `tests/integration/test_backend_lifecycle_contract.py`

- Delete `TestMemoryBootSurfacing` and `TestBoardBootSurfacing` in full (push-into-managed-files
  no longer exists).

## Storage/index-regeneration service tests

- `tests/service/test_memory_storage_and_index_regeneration.py` — drop every test that asserts on
  index regeneration or index conflict resolution: the whole-index/header/one-entry-per-memory
  tests, the `forget` re-regeneration test, and the `sync`/`repair` index tests (missing / stale /
  deleted-out-from-under / git-conflict-marker / read-survives-conflict). Keep the pure storage
  tests (slug `.md` file written, frontmatter/body, no markers, short-slug/override/collision,
  forget deletes the file, unknown-slug errors, empty pool, independent pools, off-counter /
  `.squads.json`-untouched, `repair` never touches content files).
- `tests/service/test_board_storage_and_index_regeneration.py` — same treatment: drop the
  index-regeneration and index-order and sync/repair-index and clear-ordinal-matches-index-line
  tests; keep the storage/post/list/clear/expiry/off-counter tests. **The `clear <n>` ordinal now
  resolves against the live sorted-unexpired listing directly** (not an index line) — any test that
  asserted the ordinal maps to a physical index-file line should assert against the live listing
  instead, not be deleted if it still covers real ordinal behaviour.
- Both files are misnamed once index regeneration is gone — rename them to drop
  `_and_index_regeneration` (e.g. `test_memory_storage.py` / `test_board_storage.py`). Name by
  behaviour, no ticket IDs.

## Git-merge behaviour tests

- `tests/integration/test_memory_git_merge_behavior.py` and
  `tests/integration/test_board_git_merge_behavior.py` — keep the `.md`-files-merge-clean assertions
  (independent adds merge, same-entry edit conflicts honestly, deletes merge). Remove the parts that
  assert on the committed index conflicting / being resolved by regeneration — that surface no
  longer exists.

## Role-directive test — `tests/integration/test_role_body_content_generation.py`

- Update the assertion from the old "review your `## Your memory` / `## Board` surfaced earlier"
  wording to the new pull instruction: the generated role body tells the agent to run
  `sq memory <slug> list` and `sq board list` at the start of a run. Also drop any assertion on a
  rendered `memory_lines` / `## Your memory` section in this file's fixtures.

## Golden fixtures passing `memory_lines` / `board_lines`

- `tests/unit/test_managed_section_and_cheatsheet_goldens.py`,
  `tests/unit/test_authoring_prose_derives_from_spec.py`,
  `tests/unit/test_dropped_type_authoring_prose_no_crash.py`,
  `tests/integration/test_backend_lifecycle_contract.py`,
  `tests/integration/test_role_body_content_generation.py` — remove `memory_lines=` / `board_lines=`
  from any render/golden fixture, and update the expected managed-section / pointer / AGENTS.md
  golden text so the `## Board` / `## Your memory` / per-role **Memory** blocks are gone.

## Manifest

- Regenerate `src/squads/_rendering/templates_manifest.json` with `scripts/gen_template_manifest.py`
  (freshness is checked by `tests/meta/test_override_manifest_and_stamp_freshness.py`).

## Verification

- Fast, targeted gates while iterating (`uv run pytest <path> -x`, `--lf`), plus
  `uv run pyright && uv run ruff check . && uv run ruff format --check .` and `uv run sq check`
  clean.
- The `sq memory list` / `sq board list` / managed-section goldens churn broadly. Hand the
  authoritative **full-suite** run (`uv run pytest`, and `--run-slow`) and final golden sign-off to
  the main loop — note in the handoff comment which golden files you regenerated and why.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 397 add-subtask "<title>"`; track with `sq task 397 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-15T13:00:20Z] Elias Python:
  - Deleted tests/unit/test_content_index_generator.py; deleted TestMemoryBootSurfacing/TestBoardBootSurfacing from test_backend_lifecycle_contract.py.
  - Renamed+trimmed the two storage test files (dropped _and_index_regeneration): test_memory_storage.py, test_board_storage.py — kept pure storage/off-counter/repair-neutral tests, dropped all index-regen/conflict/BUG-414 tests.
  - Git-merge tests (memory+board) keep the .md-files-merge-cleanly assertions; dropped the index-conflict/sync-resolves parts and renamed the distinct-post test names to drop the index framing.
  - Flipped test_role_body_content_generation.py's directive test to assert the pull form (sq memory <slug> list / sq board list).
  - Cleared memory_lines/board_lines fixtures from test_managed_section_and_cheatsheet_goldens.py, test_authoring_prose_derives_from_spec.py, test_dropped_type_authoring_prose_no_crash.py — goldens unchanged (those sections were always empty-list renders, confirmed via UPDATE_GOLDENS=1 diff).
  - Regenerated templates_manifest.json (scripts/gen_template_manifest.py) — only the 4 touched templates' hashes changed.
  - Gates: pyright 0 errors, ruff check + format clean, sq check clean, tests/meta 23 passed. Targeted run (memory/board storage+git-merge+backend-lifecycle+role-body+memory-skill+goldens+CLI) 134 passed. Full-suite sign-off left to the main loop per instructions.
<!-- sq:discussion:end -->
