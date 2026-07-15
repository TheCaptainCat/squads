---
id: TASK-382
sequence_id: 382
type: task
title: 'Memory tests: service + CLI, merge and off-counter invariants'
status: InReview
parent: FEAT-315
author: tech-lead
description: Service + CLI coverage for memory incl. merge behaviour and off-counter/outside-.squads.json
  invariants
subentities:
- local_id: ST1
  title: Test add writes file + regenerates index; no counter allocation
  status: Done
  story: US1
- local_id: ST2
  title: Test list/search/show and slug addressing
  status: Done
  story: US3
- local_id: ST3
  title: Test forget deletes + regenerates; clean error on missing slug
  status: Done
  story: US4
- local_id: ST4
  title: 'Test US5 merge: .md merges clean, committed index conflicts, sync/repair
    resolves'
  status: Done
  story: US5
created_at: '2026-07-15T07:47:41Z'
updated_at: '2026-07-15T10:11:53Z'
---
<!-- sq:body -->
Cover the memory behaviour through the service and CLI, per the repo testing conventions (all file generation in tmp dirs; assert generated files — valid frontmatter, JSONL header + entry lines, preserved bodies).

## Coverage

- **add** creates a slug-named file and regenerates the index; assert no global-counter allocation (counter unchanged).

- **list / search / show** behave as specified; `show` is slug-addressed, not index-position.

- **forget** deletes the file and regenerates the index; a missing slug raises a clean error.

- **Merge / invariants** — two branches each adding a distinct memory: the slug-named `.md` content files merge cleanly (no memory lost), while the committed `.index.jsonl` roll-up conflicts (both rewrote it whole); `sq sync`/`sq repair` mechanically regenerates the index from the `.md` files to resolve. Same-memory edits on both branches surface an honest `.md` conflict. Memory lives outside `.squads.json`; `sq repair` neither rebuilds nor disturbs the `.md` files, and rebuilds the index from them.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 382 add-subtask "<title>"`; track with `sq task 382 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Test add writes file + regenerates index; no counter allocation | US1 |
| ST2 | Done |  | Test list/search/show and slug addressing | US3 |
| ST3 | Done |  | Test forget deletes + regenerates; clean error on missing slug | US4 |
| ST4 | Done |  | Test US5 merge: .md merges clean, committed index conflicts, sync/repair resolves | US5 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Test add writes file + regenerates index; no counter allocation

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — As an agent, I can jot a small learned fact to my role's memory so it persists for future runs
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Add creates `<slug>.md` with light frontmatter and regenerates `.index.jsonl` (header line + one entry). Assert the global counter is not advanced.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Test list/search/show and slug addressing

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US3 — As an agent, I can list, search, and show my role's memories to pull full content when relevant
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
`list` reflects the index entries; `search` matches content; `show <slug>` returns the right body by slug, independent of line position.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Test forget deletes + regenerates; clean error on missing slug

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US4 — As an agent or operator, I can prune a stale or wrong memory so the pool stays trustworthy
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
`forget` removes the file and rewrites the index; forgetting an unknown slug raises a clean `SquadsError`.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Test US5 merge: .md merges clean, committed index conflicts, sync/repair resolves

<!-- sq:subtask:ST4:head -->
**Status:** 🟢 Done
**Implements:** US5 — As a teammate, committed per-role memory arrives on checkout and merges cleanly across branches
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
Two branches each adding a DISTINCT memory: the slug-named .md content files merge cleanly (no memory lost), while the committed .index.jsonl roll-up conflicts — both branches rewrote it whole with a different entry line. sq sync / sq repair then mechanically regenerates the index from the .md files to resolve the conflict (not: 'merges with no conflict').

Two branches editing the SAME memory surface an honest .md conflict (correct to resolve by hand).

Memory sits outside .squads.json; sq repair neither rebuilds nor disturbs the memory .md files, and rebuilds the index from them. Exercise with a git-backed test: init a repo in tmp_path, branch, add on each, merge — asserting the .md merge is clean, the index conflicts, and sync/repair regenerates it.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-15T09:57:17Z] Catherine Manager:
  - Dispatching @qa on the comprehensive memory tests + FEAT-315 acceptance pass. Key deliverable: the git-backed US5 merge test (closes REV-388 F3) proving option-B behavior. Also verify every US1-6 acceptance has a passing test; flag gaps. Take Ready→InProgress; hand to InReview.
- [2026-07-15T10:02:58Z] Mara Tester:
  - Found + filed BUG-390 while building the git-backed merge test: sq sync crashes (unhandled JSONDecodeError) on a real merge-conflicted memory index because it regenerates role pointers (which read the index) before regenerating content indexes; sq repair is unaffected. Writing the merge test against repair (matches the task's 'sync (or repair)' wording) and will note the sync gap in the acceptance verdict.
- [2026-07-15T10:11:46Z] Mara Tester:
  - Done. New tests: tests/integration/test_memory_git_merge_behavior.py (git-backed: distinct-branch adds merge .md/conflict index/repair resolves; same-memory edit conflicts honestly; committed-not-ignored; forget retains git history) + tests/service/test_memory_storage_and_index_regeneration.py (repair vs a real multi-line conflict-marker index) + tests/cli/test_memory_cli.py (show addressed by slug independent of list position).
  - Found + filed BUG-390 along the way: sq sync (not repair) crashes on a genuinely conflict-marked index — pinned as a strict xfail so it flips red once fixed. sq repair fully resolves every scenario tested, so the task's 'sync (or repair)' wording is satisfied.
  - US1-US6 acceptance: all backed by passing tests. US5's sync-side gap is the one open item, tracked by BUG-390, not a test gap.
  - Gates clean: pyright/ruff/ruff format/tests-meta/sq check all pass. New memory suite: 104 passed, 1 xfailed (expected).
<!-- sq:discussion:end -->
