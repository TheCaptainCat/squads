---
id: TASK-1113
sequence_id: 1113
type: task
title: Rebuild the integrity core tests and retire their old files
status: Draft
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
  title: Rebuild the migration, reconcile, corpus-fit, repair and renumber tests
  status: Todo
  story: US6
- local_id: ST3
  title: Prove integrity-core parity and delete the old files it covers
  status: Todo
  story: US9
created_at: '2026-10-24T13:42:15Z'
updated_at: '2026-10-24T14:34:03Z'
---
<!-- sq:body -->
Rebuild the integrity core in the new root, deepest layering first: index store, global counter, transactions, markers and `reject_markers`, the `abspath` traversal guard, the write-once guard, migrations, reconcile, corpus-fit, repair and renumber (US6), then prove parity and delete the old files this area covers (US9).

**Measured:** about 2,190 old tests in 115 files sit in this area by filename (index, store, counter, lock, marker, migrate, reconcile, repair, renumber, schema, frontmatter, collision). The largest are `tests/integration/test_migrate_up_checks_the_corpus_before_the_runners.py` (104), `tests/service/test_index_reconcile_entry_rules.py` (102) and `tests/integration/test_migrate_up_reconciles_before_the_runners.py` (90).

Ledger classes owned here: migration edges (forward-only, repair idempotency, no data loss on schema bump, reconcile and corpus-fit); markdown never behind the index; marker-safe edits; `reject_markers` on every prose input; path traversal; counter allocation only inside a transaction; ID collision and renumber; write-once guard; preserved line endings.

**Parity proof before deletion.** For every ledger entry of this area, apply its recorded break in a scratch worktree, run only the old test ids the ledger lists and the new test that owns the entry, and record that both go red (or that the old suite had a gap). Only then are the old files covering the area deleted, in this increment, in one reviewed commit. An old file that still covers an entry outside this area stays until that area lands.

**Acceptance**

- Every integrity-core ledger entry has a named test or `tests/meta` guard in the new root with its break recorded red.
- Migration, repair idempotency, corpus-fit and write-once behaviour are each covered once; no cross-product table, checked in review.
- "Every prose input passes `reject_markers`" is one `tests/meta` guard over the input sites, not one test per verb.
- The old files covering only this area are deleted; the CI time per OS after this increment is recorded and is not above the time before it.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1113 add-subtask "<title>"`; track with `sq task 1113 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Rebuild the store, counter, marker, path-guard and write-once tests

<!-- sq:subtask:ST1:body -->
Rebuild the store and write-path tests: atomic read-modify-write, counter allocation only inside a transaction, markdown written before the index commit, marker-safe edits and `reject_markers` as one guard, the `abspath` traversal guard, the write-once guard, and preserved line endings. Boundary and failure rows only; the deepest tier, so unit and service layers both apply where the seams differ.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Rebuild the migration, reconcile, corpus-fit, repair and renumber tests

<!-- sq:subtask:ST2:body -->
Rebuild migrations, reconcile, corpus-fit, repair and renumber: forward-only runs, a schema bump that loses no data, repair idempotent on a second run, reconcile and corpus-fit refusals at their boundary. Use one pinned migrated corpus (`tests/goldens/migrated_corpus`) copied per row rather than a fresh build per row.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Prove integrity-core parity and delete the old files it covers

<!-- sq:subtask:ST3:body -->
Apply each integrity-core entry's recorded break in a scratch worktree, show the listed old tests and the new owner both red, record the result in the ledger, then delete the old files this area alone covers in one reviewed commit. Record CI time per OS after the increment.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
