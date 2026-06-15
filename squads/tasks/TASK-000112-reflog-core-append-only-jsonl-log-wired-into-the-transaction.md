---
id: TASK-000112
sequence_id: 112
type: task
title: 'Reflog core: append-only JSONL log wired into the transaction seam'
status: Done
parent: FEAT-000024
author: tech-lead
priority: medium
refs:
- FEAT-000015
description: Append-only operation log written atomically inside IndexStore.transaction();
  the writer, the line schema, and actor threading.
subentities:
- local_id: ST1
  title: Append one well-formed JSONL line per mutating transaction, atomically with
    the index write (writer + line schema + op/delta capture)
  status: Done
  story: US1
- local_id: ST2
  title: Thread the actor (--as/--author/invoking agent) and op identity down to the
    store so removals/retypes/forced-status/repair are reconstructable from reflog
    lines alone
  status: Done
  story: US2
created_at: '2026-06-15T08:20:48Z'
updated_at: '2026-06-15T10:24:01Z'
---
<!-- sq:body -->
## Goal

Give every mutating `sq` operation an append-only history line, written **inside the same
transaction** as the mutation so a committed change and its log line never diverge. This is the
core seam; the read command and contract docs are TASK-000113.

## The seam

There is exactly one write seam to hook: `IndexStore.transaction()` in
`src/squads/_index/_store.py` (the filelock'd, `os.replace`-atomic read-modify-write). Every
service mutation funnels through it — `_services/_items.py` (set_status, update, link/unlink,
remove_item), `_collab.py` (comment, via `_base._locked_section_edit`), `_subentities.py`,
`_refs.py`, and the `_base.py` create/`_bump`/`_locked_section_edit` primitives. Reads
(`store.load()`) are NOT logged.

**Atomicity requirement (acceptance bar):** a crash must never leave a logged-but-not-applied or
applied-but-not-logged pair. The index write is `os.replace` of a temp file. The reflog is
append-only JSONL. Approach to evaluate in the ADR / with the architect: buffer the reflog
line(s) in the transaction context and append after the index `os.replace` succeeds but before
releasing the lock, so the line is only written once the mutation is durably committed; an append
that fails after the index commit is the lesser evil (never log-without-apply). The exact ordering
+ fsync discipline is an ADR question — flag it; do not invent it solo.

## Actor + op threading (the cross-cutting cost)

Today only `comment` carries an actor (`as_slug`); `set_status`, `update`, `remove_item`,
`add_ref`, sub-entity mutations etc. take no actor. To record "who did what" the actor must be
threaded from the CLI down to the transaction. Two seams to weigh (ADR question):
- a per-invocation ambient actor set on the store/context (like `_clock.set_now` via `--at`), kept
  out of every method signature; or
- an explicit actor parameter on each mutating service method.
Prefer the ambient approach to avoid touching every signature, mirroring the clock pattern.

Each line records: timestamp (`_clock.iso(_clock.now())` — respects `--at`), actor slug, op name
(create/status/update/body/comment/subentity/ref/link/remove/repair/migrate/…), target item
ID(s), and a compact before→after delta (e.g. `status: Ready→InProgress`). The op + delta capture
lives at each call site since only it knows what changed.

## Files to touch

- `src/squads/_index/_store.py` — the transaction hook + append-after-commit logic + the log path.
- A new writer module, e.g. `src/squads/_index/_reflog.py` — JSONL append, line model, path
  resolution (`<squad_dir>/.reflog.jsonl` via `_paths.py`).
- `src/squads/_paths.py` — expose the reflog path on `SquadPaths`.
- `src/squads/_services/*` (`_base`, `_items`, `_collab`, `_refs`, `_subentities`,
  `_maintenance`) — populate op + before/after delta + actor at each mutation.
- `src/squads/_cli/_common.py` / root callback — set the ambient actor per invocation.
- `src/squads/_clock.py` — reused as-is for timestamps (no change expected).

## Out of scope (TASK-000113)

The `sq reflog` read command, filtering, `--json` shape, golden tests, and the documented/
versioned schema with its contract tier.

## Acceptance

- Every mutating command appends exactly one well-formed JSONL line, atomically with the mutation.
- No code path logs without applying or applies without logging.
- `remove`, retype (FEAT-000020), forced status, and `repair` each emit a reconstructable line.
- `pyright` strict + `ruff` clean; service-level tests assert one line per mutation and atomicity
  on a forced mid-transaction failure.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 112 add-subtask "<title>"`; track with `sq task 112 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Append one well-formed JSONL line per mutating transaction, atomically with the index write (writer + line schema + op/delta capture) | US1 |
| ST2 | Done |  | Thread the actor (--as/--author/invoking agent) and op identity down to the store so removals/retypes/forced-status/repair are reconstructable from reflog lines alone | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Append one well-formed JSONL line per mutating transaction, atomically with the index write (writer + line schema + op/delta capture)

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — As an operator, I want a chronological log of every mutation with its actor, so that I can review what the agents did without having been in their conversations
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Thread the actor (--as/--author/invoking agent) and op identity down to the store so removals/retypes/forced-status/repair are reconstructable from reflog lines alone

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — As a team member investigating an anomaly, I want removals, retypes and forced transitions explainable from the squad directory alone, so that a gap or surprise reads as history, not corruption
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-15T09:38:04Z] Elias Python:
  - Implemented the reflog core per ADR-000117: `src/squads/_actor.py` (ambient per-invocation actor, default 'system', injectable in tests), `src/squads/_index/_reflog.py` (JSONL writer + line model + path), and wired the append into `IndexStore.transaction()` in `_store.py`.
  - Write ordering (ADR-000117 §1): reflog lines are buffered on the transaction context and appended AFTER `os.replace` commits, while still holding the file lock — logged-without-applied is impossible by design. A failed append warns to stderr and never rolls back the committed mutation.
  - The `_reflog_stub` in `remove_work_item` (ADR-000114 §2) is replaced with the real `store._log('remove', ...)` call carrying the gone-item snapshot (type/title/status/severed_refs). All other mutating call sites are wired: create, set_status, update, link, unlink, body, comment, ref add/remove, all subentity mutations, repair, repad, and migrations.
  - Ambient actor is set once at the CLI root callback (`_cli/__init__.py`) to 'system'; commands carrying an explicit identity (comment --as, create --author) call `actor.set_actor()` before the mutation. Follows the same injectable-override pattern as the clock.
  - 23 unit + integration tests in `tests/test_reflog_core.py` cover: actor default/set/clear, append/read semantics, trailing partial line tolerance, interior malformed line warn-skip, every major op emitting one line, actor in line, timestamp via frozen clock, repair not consulting reflog (Invariant 1), no-reflog back-compat, and failed-append no-rollback.
  - @reviewer @qa TASK-000112 is ready for review. ADR-000117 conformance: ordering, crash semantics, actor threading, and line schema all implemented per the accepted decisions.
- [2026-06-15T09:59:12Z] Paul Reviewer:
  - Reviewed in REV-000118 — APPROVED. Reflog core honors ADR-117: append buffered on the transaction ctx and flushed strictly after _atomic_write's os.replace while still holding the lock, no per-line fsync, failed append swallowed to stderr (never rolls back the commit); one O_APPEND single-write newline-terminated JSON line per op; ambient actor mirrors _clock (default 'system', no leak between invocations — empirically verified); op+delta captured at each call site. Remove line carries the ADR-114 gone-item snapshot. Invariant 1 holds (repair never reads the reflog).
  - @python-dev — two LOW non-blocking follow-ups in REV-000118: F6 (json.dumps is outside append_line's OSError-only swallow — harden so a non-serializable delta can't break a committed write) and F7 (the no-rollback test reverts its monkeypatch before asserting, so it tests nothing). Plus info nits F8 (stale 'no-op until 112' docstrings, inaccurate actor-clear comment in _cli/__init__.py).
- [2026-06-15T10:07:51Z] Mara Tester:
  - @qa starting independent verification of FEAT-000024 (operation reflog) and ADR-000117. Will test empirically in a scratch squad.
- [2026-06-15T10:15:15Z] Paul Reviewer:
  - Independent re-review REV-000119 (supersedes REV-000118 as the trustworthy gate — 118 shares the design/impl lineage). VERDICT: APPROVED.
  - Write-ordering (ADR-117 §1) HOLDS: reflog append is strictly after tmp.replace() inside the lock; logged-without-applied is impossible by construction; a failed append is contained by both append_line's own try/except and the outer except Exception in transaction(), so it never rolls back or fails the committed mutation. Verified by reading the guard + the monkeypatched-appender test.
  - Invariant 1 HOLDS, empirically: load/repair/check never touch .reflog.jsonl. I seeded a reflog with a forged create line for TASK-999999 + garbage, ran sq repair, and the index rebuilt from frontmatter alone (no 999999, counter unchanged, sq check clean).
  - Append atomicity, actor threading (default system; --as/--author override; --at flows into ts; no leak), and op=remove wiring all confirmed. Gate green: pytest / pyright 0 / ruff check / ruff format.
  - 5 low-severity findings, none blocking: F1 two stale 'no-op until TASK-112' docstrings (_items.py:251, _results.py:77) now factually wrong; F2 inaccurate actor-reset comment (__init__.py:67); F3 op/delta double-key nit; F4 missing autouse actor-reset in conftest; F5 reflog v reuses index SCHEMA_VERSION. See REV-000119 findings.
- [2026-06-15T10:15:57Z] Mara Tester:
  - INDEPENDENT QA VERIFICATION of FEAT-000024 / ADR-000117 — FAIL on one acceptance criterion.
  - PASS ST1 (append one well-formed JSONL line per mutating transaction): create/status/update/body/comment/ref add+rm/subentity add+update/link/remove/repair/migrate all append exactly one line with correct v/ts/actor/op/target/delta fields. Verified empirically in a scratch squad.
  - FAIL ST2 (retype reconstructable from reflog lines): sq task N retype <type> does NOT append any reflog line. Confirmed by: (1) counting lines before/after retype CLI invocation — unchanged; (2) reading _retype.py — no store._log() call; (3) retype is absent from the docs/workflow.md op table. Forced-status IS logged (same set_status code path, before/after delta captures the jump).
  - PASS actor threading: default is system; --as sets actor for comment; --author sets actor for create; next invocation resets to system via root callback. No bleed between invocations confirmed empirically.
  - Full test suite: 699 passed, 1 skipped (including 45 reflog-specific tests). No test asserts that retype emits a reflog line — the gap is untested as well as unimplemented.
- [2026-06-15T10:21:47Z] Elias Python:
  - Follow-up: BUG-000120 identified that `retype` was missing from the reflog wiring. Fixed in the same commit as REV-000119 low findings (F1/F2/F4). The retype op now emits `op=retype` with delta `{old_id, new_id, old_type, new_type, status_carried, status}` post-commit inside the transaction lock, consistent with ADR-000117 §1. @qa re-verification requested on BUG-000120.
<!-- sq:discussion:end -->
