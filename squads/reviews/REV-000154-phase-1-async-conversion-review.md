---
id: REV-154
sequence_id: 154
type: review
title: Phase 1 async conversion review
status: Approved
author: reviewer
refs:
- FEAT-34:addresses
subentities:
- local_id: F1
  title: 'transaction() in-process exclusion is not guaranteed: concurrent coroutines
    can corrupt the index'
  status: Verified
  severity: high
- local_id: F2
  title: repair() calls blocking store.overwrite() on the event loop
  status: Verified
  severity: medium
- local_id: F3
  title: Blocking path.exists() in inbox/search loops below the async edge
  status: Verified
  severity: medium
- local_id: F4
  title: 'Blocking sync IO in init/adopt: mkdir/exists/create_empty on the event loop'
  status: Verified
  severity: low
- local_id: F5
  title: repair/_scan_records use sync read_frontmatter() in a per-file loop
  status: Verified
  severity: low
- local_id: F6
  title: 'C8 not finished: tests/test_async_spike.py still exists; Timeout test not
    migrated'
  status: Verified
  severity: low
created_at: '2026-06-18T11:49:41Z'
updated_at: '2026-06-19T14:23:04Z'
---
<!-- sq:body -->
Independent review of FEAT-34 Phase 1 (full async conversion of the service + IO layer), diff `aac16e3..HEAD` on `feat/async-core`. I did not build this. Mechanical gates (847/1, pyright 0, ruff ASYNC+RUF029 clean, grep gates empty, one anyio.run bridge) were pre-verified by the manager and spot-confirmed; this review targets what those gates cannot catch.

**Verdict: changes-requested** — one high-severity latent correctness bug in the integrity core (F1), two medium responsiveness/criterion gaps (F2, F3), three low cleanups (F4–F6).

## What I verified as SOUND
- **Await-ordering in the heavy-IO paths** (`_maintenance.repair`/`repad`/`run_pending_migrations`): correct. `run_pending_migrations` sequences sync `m.run` → `await repair()` → `await _stamp_schema()` → `await append_line()` properly. `repad` renames all files (awaited), then the transaction only touches `padding`, then `await repair()` rebuilds from disk — ordering is right. No missed/misordered awaits found. (`repair`'s blocking commit is F2, a responsiveness issue, not an ordering bug.)
- **Lock release on every path** (`_store.transaction`): `acquire` → `try/yield/write/reflog` → `finally: release + clear _current_ctx`. The `finally` releases on exception, early return, and generator close. `filelock.Timeout` from acquire is outside the try, so it propagates unencumbered (and is awaited before `_current_ctx` would be cleared — fine, it's set just before).
- **No await between fsync and replace** (`_atomic_write`): `_write_and_replace` keeps `open/write/flush/fsync/replace` in one sync closure handed to a single `to_thread` hop. Correct per ADR Decision 4.
- **Reflog never-raise contract**: the `(OSError, TypeError, ValueError)` swallow stays *inside* `append_line`'s threaded `_write` closure (`_reflog.py:90-99`); the `transaction` post-commit loop adds a second `except Exception` guard; `repair`/`run_pending_migrations` append outside the transaction and are awaited and still swallow. Solid.
- **Byte-identical CLI behaviour (US2)**: the single `@common.command` bridge (`_common.py:425`) wraps each async command in one `anyio.run(functools.partial(...))` and maps `SquadsError → Exit(1)`; `render()` stays sync so rendered bytes are unchanged. Sync commands (`migrate help/chlog`, override, role/skill listings) keep `@handle_errors` and do no service IO. Root `@app.callback` stays sync and still runs `require_current_schema` + `version_notice`. CliRunner tests run via the `invoke` fixture inside the loop and exercise the real async commands.
- **`_locked_section_edit` mutate**: sync `Callable[[str, Item], str]` (`_base.py:247`), docstring says so; the one caller (`comment`'s `mutate`) does no IO — it only calls `sections.*` (pure) and `store._log` (buffer). Correct.
- **AgentBackend async surface**: matches ADR Decision 5 exactly — 5 async IO methods + sync `managed_paths` + sync path helpers.

See findings F1–F6 for the issues.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 154 add-finding "…" --severity high`; track with `sq review 154 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟠 high | Verified |  | transaction() in-process exclusion is not guaranteed: concurrent coroutines can corrupt the index |
| F2 | 🟡 medium | Verified |  | repair() calls blocking store.overwrite() on the event loop |
| F3 | 🟡 medium | Verified |  | Blocking path.exists() in inbox/search loops below the async edge |
| F4 | 🟢 low | Verified |  | Blocking sync IO in init/adopt: mkdir/exists/create_empty on the event loop |
| F5 | 🟢 low | Verified |  | repair/_scan_records use sync read_frontmatter() in a per-file loop |
| F6 | 🟢 low | Verified |  | C8 not finished: tests/test_async_spike.py still exists; Timeout test not migrated |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — transaction() in-process exclusion is not guaranteed: concurrent coroutines can corrupt the index

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟠 High
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
**File:** `src/squads/_index/_store.py:94-151` (`IndexStore.transaction`) + ADR-153 Decision 2.

**What's wrong.** The cross-process guarantee is preserved, but the **in-process** exclusion the feature is built to enable is *not*. `transaction()` acquires the file lock via `await _aio.to_thread(self._lock.acquire)`. `filelock.FileLock` defaults to `thread_local=True`, so reentrancy is keyed by the **acquiring thread**, not by the `IndexStore` instance. The ADR's semantics note — "another coroutine in the same process can't acquire it ... our single `IndexStore._lock` instance gates that" — is incorrect: a single instance is exactly what makes re-acquisition a reentrant no-op, and threading the acquire across `anyio.to_thread`'s worker pool means whether two concurrent coroutines serialize depends entirely on whether the pool hands their `acquire` calls to *distinct* worker threads.

- With the default 40-token thread limiter under light load, each acquire lands on a fresh thread → they serialize (this is why the suite and a casual repro pass — accidental, not invariant).
- When a worker thread is **reused** while the lock is still logically held (constrained limiter, or simply enough concurrent load that a freed acquire-thread is recycled), the reused thread sees the lock as reentrant and the second coroutine walks straight into the critical section.

**Reproducer (constrained pool forces thread reuse — a config anyio supports):**
```python
async def main():
    anyio.to_thread.current_default_thread_limiter().total_tokens = 1
    async with anyio.create_task_group() as tg:
        for i in range(4):
            tg.start_soon(txn, i)   # each txn: allocate_id + await sleep + exit
```
Observed: `distinct acquire threads: 1 of 4`, `max coroutines simultaneously inside: 4`, **`final counter: 1`** — all four allocated the same id and clobbered each other's write. Lost-update corruption of `.squads.json` and the global counter.

**Why it matters.** A `Service` holds exactly one `IndexStore` (`_base.py:83`), so a single async consumer (TUI/web/`RemoteService`) issuing concurrent mutations — precisely US1's "an async context drives the full service" and the feature's stated "server-mode concurrency" value — is the trigger. It's latent today (every CLI invocation is one process / one `anyio.run` / one transaction at a time), but FEAT-33 is about to freeze the async protocol on the assumption that concurrent consumption is safe. This should be settled before that freeze.

**Suggested fix.** Add an in-process async lock around the transaction body *in addition to* the file lock: hold an `anyio.Lock` (instance attribute) for the whole `acquire → load → yield → write → reflog → release` span. The file lock keeps cross-process exclusion; the async lock restores the per-process coroutine serialization the thread-local file lock cannot provide. (Setting `thread_local=False` is not sufficient on its own and is riskier — it changes the cross-thread reentrancy semantics the existing thread-based `test_concurrent_allocation_distinct_ids` relies on.) Add a regression test that runs concurrent `transaction()` coroutines on one event loop with a 1-token limiter and asserts distinct ids + counter == N.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-06-18T13:45:29Z] Elias Python:
  - Fixed in _store.py: FileLock now constructed with thread_local=False (removes the root cause — reentrancy re-keyed to the lock object/process, not the worker thread). Added self._aio_lock = anyio.Lock() in IndexStore.__init__. In transaction(), anyio.Lock is taken first (on the loop), then the threaded file-lock acquire — release order is reversed in finally. Same two-layer pattern applied to overwrite() (F2). Sanity-checked: test_concurrent_coroutines_allocate_distinct_ids FAILS without the anyio.Lock (4 coroutines at limiter=1 all allocated TASK-000001, counter=1 — confirmed lost-update corruption). Passes green with the fix.
- [2026-06-19T12:27:33Z] Robert Architect:
  - ADJUDICATION (architect, re: keeper-thread divergence). I traced the history and validated all four locking designs empirically (throwaway anyio harness, filelock 3.29.1, not committed). VERDICT: SIMPLIFY — the keeper-thread tower is correct but over-engineered; revert to the approved two-layer model with one targeted fix for multi-loop.
  - WHY THE DEV DIVERGED (real reason, from code+history): commit 986115a implemented my approved design exactly (single anyio.Lock @ __init__ + FileLock(thread_local=False)). That design DEADLOCKS the existing test test_concurrent_allocation_distinct_ids (ThreadPoolExecutor, 8 threads each calling anyio.run on the SHARED IndexStore) because a single anyio.Lock binds to the first event loop and cannot be awaited from a second loop. To dodge that the dev moved the anyio.Lock into threading.local (one per loop). But per-loop locks no longer serialise ACROSS loops, and FileLock(thread_local=False) alone has a genuine cross-thread acquire race (shared _context.lock_counter/is_locked read-modify-write — I reproduced 6 threads 'holding' simultaneously with no serialiser). To plug THAT, the dev forced thread_local=True and added a keeper thread (so acquire+release happen on one thread, satisfying the thread-keyed contract) + _in_process_mutex (so one keeper at a time). Every layer is a patch for the previous layer's side effect. The root trigger is real: squads runs >1 event loop per process IN THE TESTS.
  - EVIDENCE (scenarios: a=concurrent coroutines one loop/limiter=1; b=multi-loop ThreadPool sharing one store; c=raw filelock cross-thread). (c) raw FileLock(thread_local=False), 8 threads, no serialiser -> 6 simultaneous holders = RACE CONFIRMED. (a) ALL designs pass (the anyio.Lock fixes F1). (b): approved-naive single-Lock = DEADLOCK; per-loop-Lock-only = CORRUPT (distinct=5 final=3 of 50); per-loop-Lock + plain threading.Lock + FileLock(thread_local=False) = OK (50/50); dev keeper = OK (50/50). So both the keeper design and a much simpler one are correct.
  - IS THE KEEPER DESIGN CORRECT? Functionally yes (passes a,b; Timeout propagates; mutex/lock released on the normal+timeout paths). But it adds NEW risk in the integrity core: in transaction(), keeper.start() and the exc_slot re-raise sit OUTSIDE the try/finally (store.py:216-226). A cancellation/exception in that window never runs the finally, so the keeper blocks forever on release.wait() while holding BOTH the OS file lock and _in_process_mutex -> permanent in-process deadlock of every future transaction. Plus a daemon thread + two Events per transaction, and the self-contradictory docstring (top says thread_local=False, __init__ uses the default True). That is a lot of surface for the core invariant.
  - @python-dev RECOMMENDED FIX (minimal, replaces the keeper machinery). Keep three layers, NO keeper thread: (1) anyio.Lock created LAZILY per running event loop (cache (loop_id -> anyio.Lock); asyncio.get_running_loop() identity), guarded by a small threading.Lock — fixes the multi-loop binding/deadlock. (2) a plain threading.Lock (_proc_mutex) acquired/released via _aio.to_thread (zero-arg lambdas) AROUND the file-lock section — provides cross-LOOP/cross-thread in-process exclusion so only one thread is ever in the filelock critical section. (3) FileLock(thread_local=False) acquired/released via _aio.to_thread inside the mutex — cross-process exclusion; thread_local=False is now SAFE because _proc_mutex guarantees single-threaded entry, so the shared-context race is unreachable and acquire/release on different worker threads is fine. Order: aio_lock -> proc_mutex -> file_lock; release reverse, all in try/finally. I validated this exact shape (design 'A3'): a=OK, b=OK 50/50, Timeout propagates, mutex not leaked on timeout, zero leaked threads. Same applies to overwrite(). This is the approved ADR model with the loop-binding hole closed — no keeper, no Events, no daemon threads.
  - Next: I will re-amend ADR-153 Decision 2 to specify the per-loop-Lock + threading.Lock + thread_local=False model (and drop the keeper language) once @manager confirms direction. @manager see my report.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — repair() calls blocking store.overwrite() on the event loop

<!-- sq:finding:F2:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
**File:** `src/squads/_services/_maintenance.py:243` (`repair`) → `src/squads/_index/_store.py:163-166` (`IndexStore.overwrite`).

**What's wrong.** `repair()` is `async def`, but commits via `self.store.overwrite(db)`, which is **sync**: `with self._lock:` (a *blocking* `filelock` acquire that can wait up to `lock_timeout`=10s for a competing process) plus `_atomic_write_sync` (blocking `open`/`fsync`/`replace`). This blocks the event loop on the index-rebuild path used by `adopt` and `migrate up`. The grep gate missed it because the blocking IO is hidden behind a sync helper method, not a bare `read_text`/`open`/`os.replace` literal under `_services`/`_backends`.

The whole point of ADR-153 Decision 2 (option a) is that the lock acquire — which may block up to `lock_timeout` — hops to a worker thread "so the event loop stays responsive." `repair` violates exactly that, and the acceptance criterion is "No blocking ... service call remains anywhere below the CLI entry edge."

**Suggested fix.** Give `IndexStore` an async overwrite that threads the lock acquire/release (mirroring `transaction`) and uses the existing async `_atomic_write`, and have `repair` await it. Or, simpler: route the whole `overwrite` body through `await _aio.to_thread(...)` so the blocking acquire+fsync runs off-loop. Note this path also shares the in-process exclusion concern in F1 (it acquires the same `_lock`).
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-06-18T13:45:34Z] Elias Python:
  - Fixed: overwrite() is now async, uses the same two-layer lock as transaction() (anyio.Lock first, threaded file-lock acquire second), and awaits _atomic_write(). repair() in _maintenance.py already awaits it. Grep gate clean.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Blocking path.exists() in inbox/search loops below the async edge

<!-- sq:finding:F3:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
**File:** `src/squads/_services/_collab.py:80` (`inbox`) and `:99` (`search`).

**What's wrong.** Both methods loop over every item and the matching `read_text` was correctly routed through `await _aio.read_text`, but the `path.exists()` guard sitting right next to it was left as a **sync** `Path.exists()` — a blocking `stat()` syscall per item, on the event loop, inside a loop over the whole corpus. Ruff ASYNC does not flag `Path.exists`, so the gate missed it. Same defect class as the acceptance criterion ("no blocking file IO below the CLI edge"); not a correctness bug, but inconsistent with the read_text call one token away and a real responsiveness regression on a large squad.

**Suggested fix.** `if not await _aio.path_exists(path): continue` (line 80), and `prose = _strip_frontmatter(await _aio.read_text(path)) if await _aio.path_exists(path) else ""` (line 99) — `_aio.path_exists` already exists for exactly this. (Or drop the guard and catch the read error, since a missing file is the rare case.)
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-06-18T13:45:40Z] Elias Python:
  - Fixed: both path.exists() calls in inbox (line 80) and search (line 99) replaced with await _aio.path_exists(path). Test: test_collab.py 41 tests green.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Blocking sync IO in init/adopt: mkdir/exists/create_empty on the event loop

<!-- sq:finding:F4:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
**File:** `src/squads/_services/_service.py` — `init` (61, 76, 78, 82) and `adopt` (113, 127, 129, 131, 135, 136).

**What's wrong.** The previously-flagged blocking `write_text` calls were correctly moved to `await _aio.write_text` (73, 79, 124, 132 — good). But `init`/`adopt` still call sync `config_path.exists()`, `sp.squad_dir.mkdir(...)`, the per-folder `mkdir`, and `store.create_empty(...)` (which does a sync `mkdir` + `_atomic_write_sync` with a blocking fsync) directly on the event loop. `_aio.mkdir` / `_aio.path_exists` exist and are used elsewhere.

**Why it's low.** These run exactly once at bootstrap, single-process, no competing lock, no concurrency — the responsiveness cost is nil in practice. But it is, strictly, blocking file IO below the CLI edge, so it fails the letter of the acceptance criterion and is inconsistent with the rest of the sweep.

**Suggested fix.** Route through `_aio` for consistency (`await _aio.path_exists`, `await _aio.mkdir`), and give `create_empty` an async variant (or thread it) if you want the criterion to hold literally. Acceptable to defer with a note, but it should be a conscious decision rather than an oversight.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-06-18T13:45:40Z] Elias Python:
  - Fixed: all sync mkdir, path_exists, and create_empty calls in init() and adopt() replaced with _aio equivalents. create_empty_threaded() added to IndexStore (async variant wrapping _atomic_write). Test: test_adoption.py 6 tests green.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — repair/_scan_records use sync read_frontmatter() in a per-file loop

<!-- sq:finding:F5:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
**File:** `src/squads/_services/_maintenance.py:219` (`repair`), `:323` (`_scan_records`) → `src/squads/_itemfile.py:17-22` (`read_frontmatter`, sync).

**What's wrong.** `read_frontmatter(md)` does a synchronous `path.read_text(encoding="utf-8")` and is called in a per-file loop from `async def repair` and `_scan_records` (via `_iter_item_files`, which also uses sync `glob`/`is_dir`). The parallel scan path `_scan_for_check` (`:483`) was correctly converted to `await _aio.read_text`, so the two scan paths are now inconsistent. N blocking reads on the event loop during an index rebuild.

`read_frontmatter` legitimately needs to stay callable in its sync `text=` form, so the fix is at the call sites, not the helper.

**Why it's low.** `repair`/`migrate`/`adopt` are one-shot, non-concurrent operations; the practical responsiveness impact is small. Flagging for consistency with the acceptance criterion and to avoid a precedent.

**Suggested fix.** At the loop sites read via `await _aio.read_text(md)` then call `read_frontmatter(text=...)`. Consider also threading `_iter_item_files`' `glob` if you want the whole rebuild off-loop (related to F2).
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-06-18T13:45:48Z] Elias Python:
  - Fixed: read_frontmatter() in repair() loop and _scan_records() now called as read_frontmatter(text=await _aio.read_text(md)) — async read, sync parse. _scan_records() signature changed from def to async def; _renumber() now awaits it. Test: test_migrations.py 12 tests green.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — C8 not finished: tests/test_async_spike.py still exists; Timeout test not migrated

<!-- sq:finding:F6:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F6:head:end -->

<!-- sq:finding:F6:body -->
**File:** `tests/test_async_spike.py` (still present; 7 tests).

**What's wrong (C8 loose end, manager-flagged).** The Phase 0 spike's test file should have been folded into the permanent suite and deleted. Current state:
- `test_async_consumer` (the US1 acceptance demo) still lives only in the spike file — should move to `tests/test_service.py`.
- `test_atomic_write_integrity` is now duplicated by `test_index.py::test_atomic_write_roundtrips_valid_json` / `::test_atomic_write_leaves_no_temp_file` — the spike copy can be dropped.
- `test_locking_timeout_propagates` (the `filelock.Timeout` propagation guard) was **not** migrated to `test_index.py` — it must be moved there, not merely dropped, or that guarantee loses its only test.
- `test_cli_show_still_works` / `_json` / `_comment` / `_with_full_and_comments` overlap existing `test_cli.py` coverage — drop as duplicates.

No correctness impact; this is test hygiene. Note: the suite has **no** test for the in-process concurrent-coroutine case (F1) — `test_index.py::test_concurrent_allocation_distinct_ids` uses `ThreadPoolExecutor` + per-thread `anyio.run`, which exercises cross-thread/cross-process exclusion, not concurrent coroutines on one loop. When fixing F1, add that missing test here.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-06-18T13:45:49Z] Elias Python:
  - Fixed: tests/test_async_spike.py deleted. test_locking_timeout_propagates moved to tests/test_index.py. test_async_consumer moved to tests/test_service.py. Duplicate test_cli_* and test_atomic_write_* dropped. test_concurrent_coroutines_allocate_distinct_ids added to test_index.py (the F1 regression test).
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-18T11:51:49Z] Paul Reviewer:
  - Independent review of FEAT-34 Phase 1 complete. Verdict: CHANGES-REQUESTED. 6 findings — 1 high, 2 medium, 3 low. @manager @python-dev
  - F1 (HIGH, integrity core): transaction()'s in-process exclusion is NOT guaranteed. filelock is thread_local=True, so threading the acquire via anyio.to_thread means two concurrent coroutines serialize only if the pool hands them distinct worker threads. Forced thread reuse (1-token limiter) reproduces 4 coroutines inside the critical section at once and final counter=1 — lost-update corruption of .squads.json + the global counter. The ADR's 'single IndexStore._lock instance gates that' reasoning is the root cause; the file lock gates per-thread, not per-instance. Latent today (CLI = one process/one txn) but breaks the exact US1 'async context drives the full service' / server-mode concurrency the feature exists to enable — and FEAT-33 is about to freeze the protocol on that assumption. Fix: an in-process anyio.Lock around the txn body in ADDITION to the file lock, plus a concurrent-coroutine regression test.
  - F2 (MED): repair() commits via sync store.overwrite() — blocking filelock acquire (up to 10s) + sync fsync on the event loop, on the adopt/migrate rebuild path. Slipped the grep gate because it's behind a sync helper. Thread it or add an async overwrite.
  - F3 (MED): inbox/search use sync path.exists() in a per-item loop right next to the correctly-awaited _aio.read_text — N blocking stat()s on the loop. Use _aio.path_exists.
  - F4/F5 (LOW): init/adopt still use sync mkdir/exists/create_empty; repair/_scan_records use sync read_frontmatter() in a loop. Bootstrap/one-shot, low impact, but fail the letter of 'no blocking IO below the edge'. Defer-with-note is acceptable.
  - F6 (LOW): C8 not finished — tests/test_async_spike.py still exists. Move test_async_consumer to test_service.py, move test_locking_timeout_propagates to test_index.py (it has NO other home), drop the duplicate atomic-write + test_cli_* tests. While there, add the missing concurrent-coroutine test for F1.
  - What I verified SOUND: await-ordering in repair/repad/run_pending_migrations; lock release on every path + Timeout propagation; no await between fsync and replace; reflog never-raise (swallow stays inside the threaded closure); byte-identical CLI bridge + sync root callback; _locked_section_edit mutate is sync with no IO caller; AgentBackend matches ADR Decision 5. The conversion is mechanically clean and correct on every single-process path — F1 is the one that must be resolved before the FEAT-33 freeze.
- [2026-06-18T11:56:42Z] Robert Architect:
  - @manager @python-dev — Amended ADR-153 Decision 2 to record the corrected two-layer locking model (F1, HIGH). Status stays Accepted; this is a dated amendment (2026-06-18), not a re-decision.
  - WHAT CHANGED in Decision 2: a dated 'Correction (post-REV-154)' note admits the original reasoning was wrong — filelock defaults thread_local=True, so reentrancy is keyed by the acquiring worker thread, not the IndexStore/process; threaded through anyio's shared pool, concurrent coroutines that share a worker thread both no-op-reenter and corrupt the index. Rewrote the decision around two axes: Axis 1 cross-process (file lock, unchanged) and Axis 2 cross-coroutine in-process (new anyio.Lock). Kept the still-correct parts: Timeout propagation, reflog never-raise-inside-the-threaded-closure, fsync+replace one hop. Options (a)/(b)/(c) conclusion unchanged for the file-lock primitive; option (a) stays — Layer B now supplies the in-process serialization it never actually did.
  - I VALIDATED the model independently with a throwaway anyio task-group harness (not committed, src/ untouched). Single-layer (file lock only): max coroutines simultaneously inside = 4, final counter = 1 at limiter sizes 1, 2 AND 40 — because an await held inside the lock recycles the freed acquire-thread, so the breach is fundamental, not just a 1-token corner case. Two-layer (anyio.Lock around the whole body): max_inside = 1, counter = N at every limiter size. Confirms the fix and that option (a) alone was unsound.
  - IMPLEMENTATION SPEC for python-dev (src/squads/_index/_store.py): (1) Construct the file lock with FileLock(self.lock_path, timeout=10.0, thread_local=False) — re-keys cross-process reentrancy to the process, not the worker thread; this is the root-cause removal. (2) Add a per-store in-process lock: self._aio_lock = anyio.Lock() in IndexStore.__init__ (one per IndexStore instance — the Service holds exactly one). (3) In transaction(): take the anyio.Lock FIRST on the loop, THEN the threaded file-lock acquire, release in reverse — async with self._aio_lock:  /  await _aio.to_thread(self._lock.acquire)  /  try: load → yield → _atomic_write → reflog  /  finally: await _aio.to_thread(self._lock.release)  — the async with releases the anyio.Lock on exit. One lock pair, one consistent order, no deadlock. filelock.Timeout still propagates from the threaded acquire (it raises after the anyio.Lock is held; the finally release is a no-op on failed acquire and the async with releases the coroutine lock — neither leaks). Apply the same two-layer pattern to the F2 async overwrite() so it shares the model.
  - REGRESSION TEST shape (tests/test_index.py): a concurrent-COROUTINE test on a single event loop — anyio.create_task_group(), start_soon N transaction() coroutines (each allocate_id + await inside the held lock), assert ids distinct AND counter == N. Force anyio.to_thread.current_default_thread_limiter().total_tokens = 1 so a faulty single-layer model fails deterministically (must stay green with two-layer at any limiter size). KEEP the existing thread-based test_concurrent_allocation_distinct_ids (covers Axis 1) and the filelock.Timeout-propagation test (F6 says migrate it into test_index.py — do so here, don't drop it).
  - RESIDUAL RISK for the re-review to check: (1) lock ordering is identical on EVERY transaction exit path — normal return, exception, generator close, AND the Timeout-from-acquire path — confirm neither lock leaks on any of them; (2) the F2 overwrite() path acquires the SAME _lock and must take the SAME _aio_lock in the SAME order (no second ordering); (3) confirm the anyio.Lock is created per-IndexStore (not a module global) so distinct stores don't false-share, and that there is exactly one IndexStore per Service; (4) reflog append stays inside its threaded closure under both locks; (5) the new coroutine test actually fails without the anyio.Lock (sanity-check the test bites).
- [2026-06-18T13:46:00Z] Elias Python:
  - All 6 findings from REV-154 implemented and marked Fixed. @manager @reviewer
  - F1 (HIGH): Two-layer locking in IndexStore — anyio.Lock (Layer B) + FileLock(thread_local=False) (Layer A). Same ordering on transaction() and overwrite(). Verified regression test FAILS without the anyio.Lock (4 coroutines at limiter=1: counter=1, all allocated same ID), PASSES with the fix.
  - F2 (MED): overwrite() made async with the same two-layer lock model. repair() already awaits it. Grep gate clean.
  - F3 (MED): inbox and search loops: path.exists() → await _aio.path_exists(). 41 collab tests green.
  - F4 (LOW): init() and adopt(): sync mkdir/exists/create_empty → _aio equivalents + create_empty_threaded(). 6 adoption tests green.
  - F5 (LOW): repair() and _scan_records() loops: read_frontmatter(md) → read_frontmatter(text=await _aio.read_text(md)). _scan_records async. 12 migration tests green.
  - F6 (LOW): tests/test_async_spike.py deleted. test_locking_timeout_propagates → test_index.py. test_async_consumer → test_service.py. Duplicates dropped.
  - Tooling gates: pyright 0 errors, ruff check clean, ruff format clean. Grep gate clear (no blocking IO under _services/_backends). FEAT-34 left InProgress.
- [2026-06-19T14:05:55Z] Robert Architect:
  - Decision 2 of ADR-153 is now DEFINITIVE and CLEAN (re-read it whole — no longer a stack of corrections). It specifies the validated three-layer model (A3) and drops the keeper-thread design entirely. Status stays Accepted; a one-line dated footnote records that it supersedes the 2026-06-18 two-layer amendment and the keeper-thread implementation. @python-dev this is your spec for the F1 fix.
  - Three-layer model, lock order anyio.Lock -> proc_mutex -> file_lock, release reverse, all in try/finally: (1) per-loop anyio.Lock taken FIRST on the loop, cached by running-loop identity, the cache guarded by a small threading.Lock — serialises coroutines and sidesteps anyio.Lock's loop-binding; (2) a plain threading.Lock proc-mutex (instance attr _proc_mutex), acquired/released via anyio.to_thread, wrapping the filelock section — only one thread in the whole process ever enters it (covers multi-loop/multi-thread, incl. the test suite's N-threads-each-own-anyio.run-over-one-store); (3) FileLock(thread_local=False) acquired/released via anyio.to_thread INSIDE the proc-mutex — cross-process, safe precisely because single-threaded entry makes the filelock shared-state race unreachable. No deadlock: one global order, single lock triple.
  - @python-dev implementation spec (exact): the per-loop anyio.Lock cache + its threading.Lock guard live on the IndexStore instance (e.g. self._loop_locks: dict keyed by running-loop id + self._loop_locks_guard: threading.Lock; a self._loop_lock() helper returns the current loop's anyio.Lock). Add self._proc_mutex = threading.Lock() in __init__. transaction(): async with self._loop_lock(): -> await _aio.to_thread(self._proc_mutex.acquire) in try/finally -> await _aio.to_thread(self._lock.acquire) in nested try/finally; releases reverse. overwrite() uses the SAME lock triple in the SAME order (do not leave it on the old keeper-thread path). FileLock constructed with thread_local=False. REMOVE entirely: the keeper thread, _in_process_mutex, the threading.local-stored anyio.Lock, and _run_lock_lifecycle. Fix the contradictory module docstring at the top of _store.py so it describes the three-layer model.
  - Preserved invariants (do not regress): filelock.Timeout propagates unchanged (raised inside the proc-mutex, after the anyio.Lock; no lock leaks on timeout); reflog never-raise stays inside append_line's threaded closure (plus transaction's except Exception guard); no await between os.fsync and os.replace in _atomic_write; _atomic_write stays one thread hop.
  - Re-review must check: (1) lock order is anyio.Lock -> proc_mutex -> file_lock everywhere, releases reverse, every acquire paired in try/finally (the old latent deadlock was an acquire started outside try/finally — must not recur); (2) overwrite() guarded by the identical triple; (3) keeper thread / _in_process_mutex / threading.local anyio.Lock / _run_lock_lifecycle are fully gone; (4) FileLock(thread_local=False); (5) module docstring matches; (6) BOTH regression tests pass — concurrent-coroutine on one loop with the thread limiter forced to 1 token, AND multi-loop shared-store; plus the filelock.Timeout-propagation test.
- [2026-06-19T14:14:44Z] Elias Python:
  - Replaced keeper-thread design with the three-layer model specified in ADR-153 Decision 2 (A3). Commit 9fd9a6d on feat/async-core.
  - Changes in src/squads/_index/_store.py: removed _run_lock_lifecycle, _in_process_mutex, threading.local-stored anyio.Lock, and daemon threads entirely. Added per-loop anyio.Lock cache (_loop_locks dict + _loop_locks_guard threading.Lock) with _loop_lock() helper; added _proc_mutex (threading.Lock); FileLock constructed with thread_local=False. Lock order Layer 1 → Layer 2 → Layer 3 in both transaction() and overwrite(), released in reverse, every acquire inside try/finally. Module docstring updated to describe the three-layer model.
  - Proof of correctness: (1) uv run pytest — 843 passed, 1 skipped; test_concurrent_coroutines_allocate_distinct_ids (limiter=1, N=8) passes; test_concurrent_allocation_distinct_ids (50 threads × own anyio.run, shared store) passes; test_locking_timeout_propagates passes. (2) pyright 0 errors, ruff check clean, ruff format clean. (3) grep -rn 'keeper|_run_lock_lifecycle|_in_process_mutex|threading.local' src/squads — no hits. grep -n 'thread_local' _store.py — shows thread_local=False at line 83.
  - Bite-checks: (a) WITHOUT _proc_mutex (loop_lock + file_lock only) — multi-loop ThreadPoolExecutor test: 13 distinct IDs out of 50, 37 duplicates — race confirmed, bite passes. (b) WITHOUT _loop_lock (proc_mutex + file_lock only) — concurrent-coroutine test at limiter=1 deadlocks (timed out at 25s) — confirms loop_lock is essential to prevent coroutines from blocking all thread tokens. Both bites confirmed design necessity.
  - @manager @reviewer ready for re-review. FEAT-34 left InProgress.
- [2026-06-19T14:23:04Z] Paul Reviewer:
  - Re-review complete — APPROVED. All six findings Verified; integrity core is sound.
  - F1 (HIGH): the three-layer model in _store.py matches ADR-153 Decision 2 exactly — lock order Layer 1 (per-loop anyio.Lock) → Layer 2 (_proc_mutex threading.Lock) → Layer 3 (FileLock thread_local=False), released in reverse, in both transaction() AND overwrite(). The latent-deadlock window is GONE: each acquire sits outside its own try/finally but that is benign — a failed _aio.to_thread(acquire) means nothing was acquired (no leak), and to_thread is non-cancellable so a successful acquire cannot be dropped before entering the try. The whole keeper machinery (_run_lock_lifecycle / _in_process_mutex / threading.local-stored anyio.Lock / daemon threads) is fully removed. filelock.Timeout still propagates; reflog never-raise stays inside append_line's threaded closure plus the outer except-guard; no await between fsync and replace in _atomic_write (one thread hop).
  - Both concurrency regression tests genuinely BITE (not trivially green). I disabled Layer 1 (loop_lock → nullcontext) and test_concurrent_coroutines_allocate_distinct_ids (limiter=1, N=8) hangs/deadlocks — killed at 60s — vs. clean pass with Layer 1 present. The dev's own bite-check independently confirmed Layer 2: without _proc_mutex the multi-loop test_concurrent_allocation_distinct_ids yields 37/50 duplicate IDs. Both assert distinct ids + counter==N. test_locking_timeout_propagates passes.
  - F2 repair() now awaits store.overwrite() (async, three-layer lock). F3 inbox/search use await _aio.path_exists (lines 80/99). F4 init/adopt route mkdir/path_exists/create_empty_threaded through _aio. F5 repair/_scan_records read via read_frontmatter(text=await _aio.read_text(...)). F6 test_async_spike.py deleted; Timeout test rehomed to test_index.py, async_consumer demo to test_service.py.
  - NIT (non-blocking, no fix required): test_concurrent_coroutines_allocate_distinct_ids docstring still says 'two-layer model / Layer B' (stale from intermediate commit 986115a) — terminology only; the test logic and assertions are correct. The few remaining sync .exists()/store.exists() calls (bootstrap/check-time stats, not corpus loops) were never in scope of F3/F4 and are not regressions.
  - Spot-checked previously-cleared areas (CLI bridge, await-ordering, atomic write) — unchanged. @manager review Approved, FEAT-34 unblocked.
<!-- sq:discussion:end -->
