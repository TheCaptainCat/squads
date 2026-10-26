---
id: TASK-1113
sequence_id: 1113
type: task
title: Rebuild the integrity core tests and retire their old files
status: Ready
parent: FEAT-1096
author: tech-lead
assignee: python-dev
priority: high
refs:
- TASK-1112:depends-on
description: Store, counter, markers, path guard, write-once, migrations and repair;
  parity then deletion.
subentities:
- local_id: ST1
  title: Rebuild the store, counter, marker, path-guard and write-once tests
  status: Todo
  story: US6
- local_id: ST2
  title: Rebuild migration, reconcile, corpus-fit, repair and renumber tests
  status: Todo
  story: US6
- local_id: ST3
  title: Prove integrity-core parity and delete the old files it covers
  status: Todo
  story: US9
- local_id: ST4
  title: Rebuild line-ending preservation and container restore tests
  status: Todo
  story: US6
created_at: '2026-10-24T13:42:15Z'
updated_at: '2026-10-26T09:29:18Z'
---
<!-- sq:body -->
Rebuild the integrity core in the new root, deepest layering first: index store, global counter, transactions, markers and `reject_markers`, the `abspath` traversal guard, the write-once guard, preserved line endings on every file write (item files, skill files, managed regions and `.squads.toml`), sub-entity container restore, migrations, including the 0.16 to 0.17 role step, reconcile, corpus-fit, repair and renumber (US6), then prove parity and delete the old files this area covers (US9). This is the first of the three area increments; the engine and backend areas follow it one at a time, so each increment's CI measurement and deletion commit stands alone.

**Measured** (2026-10-26, the 2026-10-24 keyword lists re-run over per-file collected counts, this area matched first): about 2,285 old tests in 113 files (index, store, counter, lock, marker, migrate, reconcile, repair, renumber, schema, frontmatter, collision). The largest are `tests/service/test_type_invalid_frontmatter_load_boundary.py` (386, matched here by name, but its class is the engine area's load boundary), `tests/integration/test_migrate_up_checks_the_corpus_before_the_runners.py` (104), `tests/service/test_index_reconcile_entry_rules.py` (102) and `tests/integration/test_migrate_up_reconciles_before_the_runners.py` (90). `tests/test_scale.py` (6 `slow` tests: list, search, repair, `sq list` and `sq tree` on a 1,000-item squad) belongs here too.

Code added or reshaped since the plan was written that lands here: the line-ending seam (`_aio.read_text` LF for readers and verbatim for the write seam, `_sections.conform_line_endings` and its unique-line alignment, `_itemfile.write_text`, `update_frontmatter`, `rewrite_ids`, the skill restamp, the Claude Code skill-body repair, `_backends/_managed_region.inject`, view-tag placement), container restore (`_discussion.restore_regions` and `restore_container` on the edit and add paths, the half-present refusal), and the 0.16 to 0.17 role step in `_migrations/_v0_16_to_v0_17.py` (template stamp, definitions moved from per-slug files into items, mirrored-model drop with its report, the `[dev]` refusal). The `block_in_container` check rule is a check rule and belongs to the engine area. Their tests today are `tests/service/test_a_write_keeps_the_files_line_endings.py`, `tests/service/test_repair_writers_keep_the_files_line_endings.py`, `tests/unit/test_conform_line_endings.py`, `tests/cli/test_a_crlf_item_reads_like_its_lf_twin_cli.py`, `tests/service/test_a_restored_container_encloses_its_blocks.py`, `tests/cli/test_a_write_restores_the_region_it_needs_cli.py`, `tests/cli/test_region_restore_is_marker_safe_cli.py`, `tests/cli/test_the_0_17_migration_moves_roles_onto_their_base_cli.py` and `tests/cli/test_a_016_squad_migrates_to_017_without_touching_an_item_file_cli.py`.

Ledger classes owned here: migration edges (forward-only, repair idempotency, no data loss on schema bump, reconcile and corpus-fit); markdown never behind the index; marker-safe edits; `reject_markers` on every prose input; path traversal; counter allocation only inside a transaction; ID collision and renumber; write-once guard; preserved line endings, with readers seeing LF and every writer conforming through the one seam; a block never outside its container; a migration step safe to re-apply, which reports every value it drops and keeps no legacy mirrored value as a winning setting; corpus filters that name the expected finding set exactly instead of tolerating a rule.

**Parity proof before deletion.** For every ledger entry of this area, apply its recorded break in a scratch worktree, run only the old test ids the ledger lists and the new test that owns the entry, and record that both go red (or that the old suite had a gap). Only then are the old files covering the area deleted, in this increment, in one reviewed commit. An old file that still covers an entry outside this area stays until that area lands.

**Acceptance**

- Every integrity-core ledger entry has a named test or `tests_next/meta` guard with its break recorded red in the ledger.
- Migration, repair idempotency, corpus-fit and write-once behaviour are each covered once; no cross-product table, checked in review.
- "Every writer of an item, skill or managed-region file conforms its line endings" is one `tests_next/meta` guard over the write sites plus one CRLF twin table for the readers; the alignment keeps its tiling property and a linear-time row.
- "Every prose input passes `reject_markers`" is one `tests_next/meta` guard over the input sites, not one test per verb.
- The scale bounds run in the new root under `--run-slow`, still skipped by default.
- The goldens and fixtures this area uses (`tests/goldens/migrated_corpus`, `tests/fixtures/corpus`) are ported to the new root under the golden protocol; the engine area's `-C` and gate tests reuse the ported corpus.
- The old files covering only this area are deleted; the CI time per OS after this increment is recorded and is not above the time before it.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1113 add-subtask "<title>"`; track with `sq task 1113 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Rebuild the store, counter, marker, path-guard and write-once tests

<!-- sq:subtask:ST1:body -->
Rebuild the store and write-path tests: atomic read-modify-write, counter allocation only inside a transaction, markdown written before the index commit, marker-safe edits and `reject_markers` as one guard, the `abspath` traversal guard and the write-once guard. Port the scale bounds of `tests/test_scale.py` under `--run-slow`. Boundary and failure rows only; the deepest tier, so unit and service layers both apply where the seams differ. Line endings and container restore are ST4's.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Rebuild migration, reconcile, corpus-fit, repair and renumber tests

<!-- sq:subtask:ST2:body -->
Rebuild migrations, reconcile, corpus-fit, repair and renumber: forward-only runs, a schema bump that loses no data, repair idempotent on a second run, reconcile and corpus-fit refusals at their boundary. Port `tests/goldens/migrated_corpus` and `tests/fixtures/corpus` under the golden protocol and copy one pinned corpus per row rather than building one per row. Include the 0.16 to 0.17 role step: developers gain `template: dev`, file-only roles move their definition into the item, a catalog role's stored model is dropped only when it equals the catalog's and the report names it, a differing or orphan model is kept and reported, a 0.13-shaped mirrored model does not survive, `[dev]` is refused with nothing written, and a re-apply at the current schema loses no operator setting. Corpus checks after migration assert the exact set of expected orphan roles, never every finding of a rule.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Prove integrity-core parity and delete the old files it covers

<!-- sq:subtask:ST3:body -->
Apply each integrity-core entry's recorded break in a scratch worktree, show the listed old tests and the new owner both red, record the result in the ledger, then delete the old files this area alone covers in one reviewed commit. Record CI time per OS after the increment. Runs after ST1, ST2 and ST4.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Rebuild line-ending preservation and container restore tests

<!-- sq:subtask:ST4:body -->
Rebuild line-ending preservation and region restore. Readers see LF: a CRLF item reads byte-identical to its LF twin on show, `--json`, sub-entity show and the template-body guard. Every writer of an item, skill or managed-region file conforms to the on-disk endings through the one seam, held by a guard over the write sites (frontmatter update, id rewrite, skill restamp, backend skill-body repair, managed-region inject, view-tag placement), with one CRLF row per writer kind and a mixed-ending row. `conform_line_endings` keeps the tiling property on swaps and duplicates, every untouched line keeps its ending, and one row bounds the large-file time. Container restore: a lost pair is restored around the surviving blocks on both the edit and the add path, one heading, never inside another region; prose between blocks and a half-present pair refuse with one error line and leave the file byte-identical.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T19:48:44Z] `tech-lead` Olivia Lead:
  - Re-read for Ready on 2026-10-24: added tests/test_scale.py, line endings on .squads.toml writes, and the corpus goldens and fixtures to port. The three area tasks now run one at a time (TASK-1114 depends on this one, TASK-1115 on TASK-1114), so each CI measurement and deletion commit stands alone. Moved to Ready.
<!-- sq:discussion:end -->
