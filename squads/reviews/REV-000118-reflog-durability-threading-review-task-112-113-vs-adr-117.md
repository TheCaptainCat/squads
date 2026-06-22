---
id: REV-000118
sequence_id: 118
type: review
title: Reflog durability/threading review (TASK-112/113 vs ADR-117)
status: Approved
author: reviewer
refs:
- TASK-000112
- TASK-000113
- FEAT-000024
- ADR-000117
description: Narrow durability/threading correctness review of the reflog core + read
  command against ADR-000117 and ADR-000114.
subentities:
- local_id: F1
  title: 'Check 1 — Write ordering (ADR-117 §1): PASS'
  status: Open
  severity: info
- local_id: F2
  title: 'Check 2 — Append atomicity (ADR-117 §2): PASS'
  status: Open
  severity: info
- local_id: F3
  title: 'Check 3 — Actor threading (ADR-117 §3): PASS'
  status: Open
  severity: info
- local_id: F4
  title: 'Check 4 — Invariant 1 / not-source-of-truth (ADR-114): PASS'
  status: Open
  severity: info
- local_id: F5
  title: 'Check 5 — Schema + version field + golden (ADR-117 §4): PASS'
  status: Open
  severity: info
- local_id: F6
  title: json.dumps outside append_line swallow could break committed write
  status: Fixed
  severity: low
- local_id: F7
  title: 'Dead test: test_failed_reflog_append_does_not_rollback_mutation asserts
    nothing meaningful'
  status: Fixed
  severity: low
- local_id: F8
  title: Stale doc comments + minor op-naming nit (non-blocking)
  status: Open
  severity: info
created_at: '2026-06-15T09:57:14Z'
updated_at: '2026-06-23T10:00:09Z'
---
<!-- sq:body -->
Narrow durability/threading correctness review of the reflog implementation for FEAT-000024 (TASK-000112 reflog core, TASK-000113 read command), reviewed against ADR-000117 (durability/append-atomicity/actor-threading) and ADR-000114 (removal trace / NOT-source-of-truth).

Gate: `uv run pytest` (all pass, 1 skip) + `uv run pyright` (0 errors) + `uv run ruff check .` (clean) + `uv run ruff format --check .` (clean) — all green.

Verdict: APPROVED. All five ADR rulings are honored in the code (verified by reading, not the summary). One low-severity robustness gap and minor doc/test nits logged below; none block approval because no live code path triggers the gap.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 118 add-finding "…" --severity high`; track with `sq review 118 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🔵 info | Open |  | Check 1 — Write ordering (ADR-117 §1): PASS |
| F2 | 🔵 info | Open |  | Check 2 — Append atomicity (ADR-117 §2): PASS |
| F3 | 🔵 info | Open |  | Check 3 — Actor threading (ADR-117 §3): PASS |
| F4 | 🔵 info | Open |  | Check 4 — Invariant 1 / not-source-of-truth (ADR-114): PASS |
| F5 | 🔵 info | Open |  | Check 5 — Schema + version field + golden (ADR-117 §4): PASS |
| F6 | 🟢 low | Fixed |  | json.dumps outside append_line swallow could break committed write |
| F7 | 🟢 low | Fixed |  | Dead test: test_failed_reflog_append_does_not_rollback_mutation asserts nothing meaningful |
| F8 | 🔵 info | Open |  | Stale doc comments + minor op-naming nit (non-blocking) |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Check 1 — Write ordering (ADR-117 §1): PASS

<!-- sq:finding:F1:head -->
**Status:** 🔴 Open
**Severity:** 🔵 Info
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
_store.py transaction(): reflog ops are buffered on _TransactionCtx during the body and flushed only AFTER _atomic_write()'s os.replace, inside the same `with self._lock` block (lines 116-131). Append cannot run before commit — logged-without-applied is structurally impossible. No per-line fsync on the reflog (only the index is fsync'd in _atomic_write). append_line swallows OSError to a stderr warning and never raises (lines 89-97). Confirmed by test_create_emits_reflog_line + reading the seam.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Check 2 — Append atomicity (ADR-117 §2): PASS

<!-- sq:finding:F2:head -->
**Status:** 🔴 Open
**Severity:** 🔵 Info
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
_reflog.py append_line(): one compact json.dumps line (separators (',',':'), no embedded newlines — json escapes them) + '\n', written in a single fh.write() under open(path,'a') (O_APPEND). read_lines() tolerates all three required cases: missing file → [] (line 107-108); trailing partial line with no terminating newline → silently skipped (lines 119-123, no warning); interior malformed line → warn+skip (lines 142-147); never raises (OSError on read → [] at 112-113). Covered by test_read_lines_* tests.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Check 3 — Actor threading (ADR-117 §3): PASS

<!-- sq:finding:F3:head -->
**Status:** 🔴 Open
**Severity:** 🔵 Info
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
_actor.py mirrors _clock exactly: module-global _override, set_actor/current_actor, default 'system'. Root callback (_cli/__init__.py:69) calls set_actor('system') first thing on every invocation; comment/create/status call sites override via set_actor(slug) before the mutation (_items.py:209,677; _create.py:60). op + before→after delta are captured at each CALL SITE (not ambient) and buffered via store._log — verified across _base/_items/_refs/_subentities/_collab/_maintenance.

CRITICAL actor-leak check (the subtlety the architect flagged): VERIFIED CLEAN. Empirically ran four separate CLI invocations — create --author manager, status (no --as), comment --as manager — and the status line correctly logged actor='system', NOT leaking 'manager' from the prior invocation. The implementation resets at the START of each invocation rather than the ADR's literal try/finally-clear, but the behavior is equivalent and mirrors the established _clock precedent (apply_timestamp also resets-at-start, never clears at end).
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Check 4 — Invariant 1 / not-source-of-truth (ADR-114): PASS

<!-- sq:finding:F4:head -->
**Status:** 🔴 Open
**Severity:** 🔵 Info
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
Nothing makes the index depend on the reflog. repair() (_maintenance.py:182-252) rebuilds db purely from .md frontmatter and never calls read_lines; it appends a 'repair' reflog line at the END via the bare append_line (after store.overwrite). repad() renames files, runs a transaction to set padding (buffering a repad reflog op), then repair(). migrate appends after repair completes. All three run outside transaction() and use the error-swallowing append_line, so a missing/unwritable reflog is never an error. test_reflog_not_consulted_by_repair corrupts the reflog and proves repair still succeeds; test_no_reflog_squad_is_backward_compatible proves a reflog-less squad is unaffected. The remove line carries the ADR-114 gone-item snapshot {type,title,status,severed_refs} (_items.py:312-321).
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Check 5 — Schema + version field + golden (ADR-117 §4): PASS

<!-- sq:finding:F5:head -->
**Status:** 🔴 Open
**Severity:** 🔵 Info
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
Every line carries v=SCHEMA_VERSION ('0.3'), present from line one (_reflog.py:80). The documented shape (docs/workflow.md 'Operation reflog' section: fields v/ts/actor/op/target/delta + op vocabulary + delta-additive stability note deferring the freeze to FEAT-000013) matches the golden tests/goldens/reflog_shape.json (fields list, schema_version 0.3, example_ops). Golden + --json shape exercised by test_golden_reflog_json and test_cli_reflog_json_shape.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — json.dumps outside append_line swallow could break committed write

<!-- sq:finding:F6:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F6:head:end -->

<!-- sq:finding:F6:body -->
ADR-117 §1 rules that 'logging must never be able to break a write that the index already committed' and a failed append must warn/swallow, never fail the mutation. In _reflog.py append_line, json.dumps(record, ...) is at line 88, BEFORE the try/except OSError block (89-97). The store's transaction() append loop (_store.py:123-131) runs AFTER os.replace with no try/except of its own. So if any delta value were non-JSON-serializable (e.g. a Status enum or datetime), json.dumps would raise TypeError, escape append_line's OSError-only guard, and propagate out of transaction() — surfacing the already-committed mutation as a failure to the caller. That is precisely the failure mode the ADR designs out.

Severity LOW, not blocking: every current call site builds deltas from JSON-safe primitives (strings, .value strings, lists of strings, ints, None), so no live path triggers this and the gate is green. But the swallow is structurally too narrow — it guards the file write, not the serialization. Recommend hardening: move json.dumps inside the try and broaden the except to also catch (TypeError, ValueError) (or wrap the whole append_line body), so a future call site that drops a non-serializable object into a delta degrades to a warning instead of breaking a committed write. @python-dev
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Dead test: test_failed_reflog_append_does_not_rollback_mutation asserts nothing meaningful

<!-- sq:finding:F7:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F7:head:end -->

<!-- sq:finding:F7:body -->
tests/test_reflog_core.py:306 sets up a _boom monkeypatch that raises OSError (line 315) but then reverts it (line 323) BEFORE the create call (line 328), so the assertion runs against the REAL append_line. The test passes but never exercises an append failure reaching the store — it does not actually prove the no-rollback guarantee. Combined with finding F6, this is why the propagation gap went unnoticed. Recommend rewriting it to genuinely force append_line to fail (e.g. chmod the reflog read-only, or make the parent dir unwritable) and assert the mutation still committed + a stderr warning was emitted. @python-dev
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Stale doc comments + minor op-naming nit (non-blocking)

<!-- sq:finding:F8:head -->
**Status:** 🔴 Open
**Severity:** 🔵 Info
<!-- sq:finding:F8:head:end -->

<!-- sq:finding:F8:body -->
(a) _cli/__init__.py:67-68 comment claims 'The try/finally in the hook clears it per-invocation' — inaccurate: the try/finally in _store.transaction clears _current_ctx, not the actor; the actor is reset at the start of the next callback (set_actor('system')), not cleared at end. Reword to match the actual (clock-like) mechanism.

(b) _services/_items.py:249-251 (remove_work_item docstring) and _services/_results.py:77 still say the reflog writer 'is a no-op until TASK-000112 wires the FEAT-000024 writer' — stale now that 112 is done; the writer is live.

(c) repad logs op='migrate' with a nested delta={'op':'repad',...} (_maintenance.py:299-308) while docs/workflow.md maps 'migrate' to both 'migrate up' and 'migrate repad' — consistent with the doc and the closed vocab, but the double 'op' key (top-level op='migrate' + delta.op='repad') is slightly confusing for a reader. Optional: drop delta.op or promote repad to its own vocab entry in a future schema rev. None of these affect correctness. @python-dev
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-15T09:59:00Z] Paul Reviewer:
  - Verdict: APPROVED. All five ADR-117/114 checks PASS, verified by reading the code (not the summary), and the full gate is green (pytest/pyright/ruff check/ruff format).
  - @architect — the actor-leak you flagged in ADR-117 §3 is VERIFIED CLEAN: ran four real CLI invocations and the status line (no --as) logged actor='system', not leaking the prior invocation's 'manager'. The impl resets-at-start (mirroring _clock) rather than try/finally-clear, but the behavior is equivalent and follows the established clock precedent. Write ordering (append strictly after os.replace, inside the lock, no per-line fsync, failed append swallowed) is faithful.
  - @python-dev — two LOW non-blocking findings (F6, F7) + info nits (F8). F6 is the only substantive one: json.dumps sits OUTSIDE append_line's OSError-only swallow, so a future non-serializable delta would propagate past the committed mutation — exactly the failure mode ADR-117 §1 forbids. No live path triggers it today (all deltas are JSON-safe), so it does not block, but please harden the swallow (move json.dumps inside the try, broaden the except). F7: the no-rollback test reverts its own monkeypatch before asserting, so it proves nothing — please make it genuinely force a failed append.
- [2026-06-15T10:02:57Z] Robert Architect:
  - Addressed the two findings touching the ADR-117 §1 guarantee (gate green: pytest pass, pyright 0, ruff clean):
  - F6 (Fixed): moved json.dumps INSIDE append_line's try and broadened the except to (OSError, TypeError, ValueError) — a non-serializable delta now degrades to a stderr warning instead of raising past a committed mutation. Belt-and-suspenders: also wrapped the store-level append loop in transaction() (src/squads/_index/_store.py) in a catch-all that warns, so nothing in the post-commit reflog path can ever surface from an operation the index already applied — the literal ADR-117 §1 promise.
  - F7 (Fixed): rewrote the dead test. Now three real tests in tests/test_reflog_core.py — test_append_line_swallows_oserror (reflog path is a dir → IsADirectoryError), test_append_line_swallows_serialization_error (set delta → former F6 regression guard), and test_failed_reflog_append_does_not_rollback_mutation (patches append_line to raise OSError and asserts the created item is still readable after commit).
  - F8 left to @python-dev as cleanup: stale 'no-op until TASK-000112' docstrings (_items.py, _results.py), the inaccurate 'try/finally clears the actor' comment in _cli/__init__.py (reword to the clock-like reset-at-start mechanism), and the op='migrate'/delta.op='repad' double-key nit. None affect correctness; not gating.
<!-- sq:discussion:end -->
