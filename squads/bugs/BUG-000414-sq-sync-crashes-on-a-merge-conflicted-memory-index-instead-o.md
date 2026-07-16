---
id: BUG-414
sequence_id: 414
type: bug
title: sq sync crashes on a merge-conflicted memory index instead of regenerating
  it
status: Verified
author: qa
assignee: python-dev
priority: medium
refs:
- FEAT-315
- REV-412
description: sync() regenerates role pointers (reading the index) before it regenerates
  content indexes, so a real git-conflicted .index.jsonl crashes sync with an unhandled
  JSONDecodeError; repair is unaffected
created_at: '2026-07-15T10:02:49Z'
updated_at: '2026-07-15T13:14:43Z'
---
<!-- sq:body -->
`sq sync` regenerates managed role pointers before it regenerates content indexes
(`MaintenanceMixin.sync` in `_services/_maintenance.py`: role-entry generation runs
early in the method and calls `memory_index_lines` -> `memory_store.read_index` ->
`_content_index.parse_index`, while `_regenerate_content_indexes()` — the fix that is
supposed to make `sync` resolve a conflicted memory index — runs at the very end of
the same method).

Reproduced at the service layer (no git needed): write a role's
`agents/memory/<role>/.index.jsonl` with real multi-line git conflict markers (the
exact shape left behind by a "distinct memory added on two branches" merge), then
call `svc.sync()`. It raises an unhandled `json.decoder.JSONDecodeError` (not a
`SquadsError`), so the CLI prints a raw traceback instead of a clean error — and,
per invariant, `sync()` never reaches its own regenerate-content-indexes step for
that role, so the index is left conflicted.

`sq repair` is unaffected (`MaintenanceMixin.repair` does not generate role
pointers, only rebuilds the counter-backed index then calls
`_regenerate_content_indexes()`), so the documented resolution path still works via
`repair` — but the `sq sync` half of "sq sync/repair mechanically regenerates the
index" (ADR-314, FEAT-315 US5, REV-412 F1/F2) does not currently hold.

Found while writing the FEAT-315 git-backed merge test for TASK-406/REV-412 F3.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-15T10:14:16Z] Catherine Manager:
  - Dispatching @python-dev. Fix: (1) reorder sync() so _regenerate_content_indexes() runs BEFORE the role-pointer generation that reads the index; (2) make parse_index/read_index defensive — a conflicted/unparseable .index.jsonl degrades to 'needs regeneration' (empty), never an unhandled crash (Paul flagged this exact fragility on TASK-402; the board will be the next heavy reader). Un-xfail Mara's sync-resolves-conflict test. Open→InProgress→Fixed.
- [2026-07-15T10:18:39Z] Operator:
  - Fixed: reordered sync() to run _regenerate_content_indexes() before role-pointer generation; made parse_index degrade to ({}, []) on JSONDecodeError/TypeError (conflict-marked or otherwise-corrupt index) instead of raising. Un-xfailed test_sync_resolves_a_roles_index_left_with_real_git_conflict_markers (now passes) + added defensive-parse unit tests + a read_index/memory_list service test. pyright/ruff/tests/meta/sq check all clean.
- [2026-07-15T13:14:43Z] Catherine Manager:
  - Obsolete: its subject — sq sync crashing on a merge-conflicted committed .index.jsonl — no longer exists; the REV-419 re-architecture removed the content index entirely. WontFix.
<!-- sq:discussion:end -->
