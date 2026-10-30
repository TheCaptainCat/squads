---
id: TASK-1263
sequence_id: 1263
type: task
title: 'Daemon cache of parsed files: index, frontmatter, override check'
status: Done
parent: FEAT-1140
author: tech-lead
refs:
- ADR-1261:implements
description: Content-keyed cache of the index, item frontmatter and the override's
  index check, threaded through the request context, reads only
subentities:
- local_id: ST1
  title: Cache on the daemon state, threaded through the request
  status: Done
  maps_to: US2
- local_id: ST2
  title: Index and frontmatter keyed by content digest
  status: Done
  maps_to: US2
- local_id: ST3
  title: Override-check memo and the start-up spec
  status: Done
  maps_to: US2
created_at: '2026-10-30T20:30:25Z'
updated_at: '2026-10-30T23:45:26Z'
priority: high
---
<!-- sq:body -->
## Goal

The daemon's cache of parsed files (ADR-1261 point 7): the validated index, each item file's frontmatter, and the outcome of the override's check against the index, kept across requests, keyed by the content just read, never a source of truth. It serves every daemon request, routes and served commands alike, and gives local mode nothing and changes nothing there. Measured in the prototype: `task show`'s handler 250-320 ms to 126 ms, `check` 7.0 s to 1.6 s with warm caches.

## Scope

- **Where it lives** (point 7, "Threaded, not global"): on the daemon's state, reaching the store through the `RequestContext`; no module-level state; local mode has none.
- **The index:** `IndexStore.load` reads `.squads.json`, hashes the bytes (BLAKE2b) and skips the parse on a digest hit. `transaction()` keeps re-reading under the file lock and never consults the cache. One request receives one index value shared by every load in that request (frozen, or one copy per request), never a copy per load: a copy costs about 13 ms at this corpus size.
- **Item frontmatter:** the item-file read path hashes the bytes it has just read and returns the cached parsed mapping on a hit; a copy per hit is cheap enough. Entries cannot be mutated through what a caller receives.
- **The override's check against the index** (`validate_against_index_fail_closed`): its outcome, success or the refusal, memoised by the index's digest and the identity of the daemon's spec, so the two runs per command (root callback, command resolution) and the service composition cost one check per index state.
- **The merged spec** is taken from the daemon's start-up documents (the retirement fingerprint ties them to disk), not re-read from disk per request.
- **Bounds:** one entry per path, replaced when its digest changes; an entry for a path no longer read is dropped when the daemon next scans the corpus.
- Out of scope: `check`'s rule results.

## Modules touched

`src/squads/_index/_store.py`, the item-file read path (`_itemfile.py`/`_corpus_files.py`/`_sections.py`, wherever frontmatter is parsed), `src/squads/_workflow/_loader.py` (the memo and the start-up spec), `src/squads/_context.py`, `src/squads/_daemon/_state.py`, `tests/daemon/`. The prototype at commit 046144f7 (`src/squads/_parse_cache.py` and its edits to `_store.py`, `_sections.py`, `_loader.py`) is a reference only: it keyed the index by a single slot and had no eviction scan. Any module-level constant you add trips the mutable-state guard: run `tests/meta` after adding one.

## Acceptance

- ADR-1261 point 7 in full; Invariant 1 of CLAUDE.md holds: dropping the cache at any moment changes nothing but time, and `sq repair` on a squad written through the daemon has nothing to fix.
- A write made outside the daemon (a local-mode `sq`, git, an editor) is seen by the next daemon request with no invalidation step, including a same-size rewrite within one timestamp tick.
- Gates: `uv run --all-extras pyright`, `uv run --all-extras ruff check .`, `uv run --all-extras ruff format --check .`, `uv run --all-extras pytest -n 6` (one full run, to a file), `--api-mode remote tests/cli` and `--api-mode remote --squad override tests/cli`, `-n0 tests/cross_process`, `python scripts/gen_template_manifest.py --check`, `~/.local/bin/sq check` clean.
- Report the handler time of `task <n> show` and `check` on a copy of this repository's squad, before and after, 31 interleaved runs, medians with p25-p75, host load average stated. A daemon only ever on the copy, never on this repository's squad.

## Test approach (ADR-1172)

- In-process tests in `tests/daemon/`, rules 4-6, no `covers` marker, through the route harness that already serves the daemon's application on a thread (no dependency on the command endpoint): an item file rewritten between two requests with the same size and timestamp (restored with `os.utime`), read back current (1); the same for the index (1); an override check refused, then answered once the index digest changes (1). Falsify each: key on `(size, mtime)` instead of the digest, or skip the memo's index digest, and see it go red.
- Parity: the existing remote-mode runs exercise the cache on every case; no new case.
- Expected: 3 tests, 0 guards.
- Order: runs in parallel with the command-endpoint task from the start; nothing depends on it except the dogfood trial.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1263 add-subtask "<title>"`; track with `sq task 1263 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Cache on the daemon state, threaded through the request

<!-- sq:subtask:ST1:body -->
The cache hangs off the daemon's state and reaches the store through the `RequestContext`; no module-level state, none in local mode. One entry per path, replaced when its digest changes; an entry for a path no longer read is dropped at the daemon's next corpus scan; entries cannot be mutated through what a caller receives.

Tests: held by ST2 and ST3's cases and the parity run; no case of its own.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Index and frontmatter keyed by content digest

<!-- sq:subtask:ST2:body -->
`IndexStore.load` and the item-file read hash the bytes they have just read (BLAKE2b) and skip the parse on a digest hit; `transaction()` re-reads under the file lock and never consults the cache. One index value per request, shared by every load in it (frozen, or one copy per request); a frontmatter copy per hit.

Tests: an item file rewritten between two requests with the same size and timestamp, read back current (1); the same for the index (1). Falsify by keying on size and mtime.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Override-check memo and the start-up spec

<!-- sq:subtask:ST3:body -->
The outcome of `validate_against_index_fail_closed` (success or the refusal) memoised by the index's digest and the identity of the daemon's spec; a daemon request takes the merged spec from the start-up documents instead of re-merging the override from disk. Report the handler time of `task <n> show` and `check` before and after on a copy of this repository's squad.

Tests: an override check refused, then answered once the index digest changes (1). Falsify by dropping the digest from the memo key.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-30T20:35:18Z] `python-dev` Elias Python:
  - Starting on the cache (ST1-ST3).
- [2026-10-30T20:54:36Z] `python-dev` Elias Python:
  - Cache delivered on the worktree branch (commit 89825e3b), not pushed.
    
    - `src/squads/_parse_cache.py`: `ParseCache`. Index and frontmatter entries are keyed by path and the BLAKE2b digest of the text just read, kept pickled, a fresh copy per hit. One slot holds the override-check outcome, keyed by index digest and the identity of the spec and the bundled spec. `begin_scan`/`end_scan` drop frontmatter entries a full corpus walk did not read.
    - Hung off `DaemonState`, passed to `RequestScope`, carried on `RequestContext.parse_cache`. Nothing at module level; `None` in local mode.
    - Read paths: `IndexStore.load` (never `transaction()`), `read_frontmatter`, `validate_against_index_fail_closed`. The routes already take the merged spec from the start-up documents.
    - Tests: tests/daemon/test_the_parse_cache.py, 3 tests, each falsified (digest check removed: red).
    - Measured on a copy of the squad under ~/.cache, handler time from Server-Timing, 31 interleaved warm runs, load 2.6: task show 89 (77-98) to 68 (55-95) ms; check 6314 (5861-6643) to 3732 (3520-3884) ms. Cold first request (7 runs): task show 107 to 95, check 6532 to 5428.
- [2026-10-30T21:14:55Z] `manager` Catherine Manager:
  - Integrated on release/0.19 as ff9784bf and 4585afec. Gates: pyright 0, ruff clean, full suite 1895 passed, remote 999 passed, override 840 passed, cross-process 22 passed, manifest current. Warm check handler 1.3-1.7 s, level with the prototype. Review joins TASK-1262's.
- [2026-10-30T23:45:25Z] `manager` Catherine Manager:
  - Accepted under the operator's overnight delegation (2026-10-31): REV-1223 is Approved with every finding Verified or Noted, and CI runs 41141368085 and 41145415746 are green on every job.
<!-- sq:discussion:end -->
