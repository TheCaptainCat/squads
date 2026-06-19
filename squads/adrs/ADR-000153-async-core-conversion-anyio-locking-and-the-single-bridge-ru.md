---
id: ADR-000153
sequence_id: 153
type: decision
title: 'Async-core conversion: anyio, locking, and the single-bridge rule'
status: Accepted
author: architect
refs:
- FEAT-000034:addresses
created_at: '2026-06-17T20:29:57Z'
updated_at: '2026-06-19T14:05:33Z'
---
<!-- sq:body -->
## Context

Every layer of `squads` below the CLI is synchronous: the service mixins, the index store's
locked transactions, and all file IO. Every consumer on the roadmap is async-native — Textual
(`sq ui`, EPIC-000028), FastAPI (`sq web`, EPIC-000029), and an HTTP `RemoteService`
(FEAT-000033). If the core stays sync, each consumer must wrap every call in executor threads
forever. The timing is the driver: **FEAT-000033 is about to freeze the calling convention into
typed Protocols.** Whether those methods are `def` or `async def` is a now-or-painful decision —
retrofitting async under a frozen sync protocol is the painful kind. FEAT-000034 gates that
freeze, and this ADR locks the load-bearing patterns so the Phase 0 spike can validate them before
the atomic sweep.

**Honesty clause (carry into the PR description):** this makes nothing faster for a single CLI
invocation — it may add a microsecond of event-loop startup. The value is purely architectural:
one async calling convention for the whole stack, native consumption by the TUI/web/remote layers,
and server-mode concurrency without a thread pool bolted to a blocking core.

This ADR records five decisions. Decision 2 (locking) is the crux and gets the most space.

---

## Decision 1 — anyio over raw asyncio

**Chosen: anyio (`anyio>=4`).**

Rationale:
- **Structured concurrency** (task groups, cancellation scopes) — the shape FastAPI and Textual
  both already live in; consuming the service from either is then native.
- **Backend-agnostic.** anyio runs on asyncio *or* trio. Raw `asyncio` would pin the entire core
  to one event loop forever; anyio keeps the door open and costs nothing today (we pin the test
  backend to `"asyncio"`, no trio dependency).
- **Built-in `to_thread.run_sync`** — exactly the primitive we need for the blocking `filelock`
  acquire and for the atomic-write closure (Decisions 2 and 4). No bespoke executor management.
- **One `anyio.run` bridge** is all the sync edge needs (Decision 3); the equivalent asyncio
  story (`asyncio.run` + manual loop policy) is the same line count with none of the portability.

**Why not bare asyncio:** it offers no structured-concurrency primitives without extra scaffolding,
pins the core to a single loop implementation, and gains us nothing the anyio facade doesn't already
wrap. The only "cost" of anyio is one dependency, which the roadmap (TUI/web) pulls in regardless.

---

## Decision 2 — Locking strategy (the crux)

The index transaction (`src/squads/_index/_store.py::transaction()`) is the integrity core: every
allocation of the global counter and every read-modify-write of `.squads.json` happens inside it.
Once the service is async the mutation body runs `await`s (item-file IO in `_locked_section_edit`,
the reflog append), so the lock is now **held across `await` points** and the transaction must be
exclusive on three distinct axes:

1. **Concurrent coroutines on one event loop** — a TUI/web/`RemoteService` driving the single
   `Service` → single `IndexStore` instance with overlapping mutations (this is exactly the
   server-mode concurrency the feature exists to enable, US1).
2. **Multiple event loops in one process** — *not* hypothetical: the test suite runs N threads,
   each with its own `anyio.run`, over one shared `IndexStore`. Any in-loop primitive is bound to
   the loop it was first used on and cannot serialise a second loop.
3. **Separate OS processes** — parallel `sq` subagent invocations must never corrupt `.squads.json`
   or collide on the global counter.

And the blocking `filelock` acquire/release must never run on the event loop.

No single primitive covers all three: an `anyio.Lock` is loop-bound (fails axis 2), a
`threading.Lock` knows nothing of coroutines (fails axis 1), and `filelock` is an OS advisory lock
mediated through a shared worker-thread pool whose in-process reentrancy is keyed by the acquiring
thread, not the process (fails axes 1 and 2). So the decision is a **three-layer model**, taken in
one fixed order and released in reverse, all in `try/finally`.

### The three-layer model (definitive)

**Layer 1 — per-loop `anyio.Lock` (serialises coroutines).** An `anyio.Lock` binds to the event
loop it is first used on, so a single shared instance cannot span loops. We therefore keep a
**cache of `anyio.Lock` keyed by running-loop identity** and fetch (or lazily create) the lock for
the *current* loop, guarded by a small `threading.Lock` so the cache itself is safe across threads.
This lock is taken **first**, on the loop, and serialises all coroutines running on that loop.
Sidestepping the loop-binding constraint this way is what makes axis 2 tractable.

**Layer 2 — in-process `threading.Lock` (proc-mutex, cross-loop / cross-thread).** A plain
`threading.Lock` instance attribute (the *proc-mutex*), acquired and released via
`anyio.to_thread`, wraps the file-lock section. It guarantees that **only one thread in the whole
process** is ever inside the filelock critical section — across every event loop and every worker
thread. This is the layer that closes axis 2 (and the cross-thread part of axis 1) that no in-loop
primitive can.

**Layer 3 — `FileLock(thread_local=False)` (cross-process).** The `filelock.FileLock`, acquired and
released via `anyio.to_thread`, **inside** the proc-mutex, provides axis 3. Constructing it with
`thread_local=False` keys its reentrancy to the lock object/process rather than the acquiring worker
thread. This is safe **precisely because** the proc-mutex guarantees single-threaded entry: the
filelock shared-state race (concurrent acquisition from different worker threads) is then
unreachable, so the one documented failure mode of `thread_local=False` cannot occur.

```
async with self._loop_lock():                     # Layer 1 — per-loop anyio.Lock, on the loop, FIRST
    await _aio.to_thread(self._proc_mutex.acquire) # Layer 2 — proc-mutex, off-loop
    try:
        await _aio.to_thread(self._lock.acquire)   # Layer 3 — filelock; may raise Timeout, propagates
        try:
            ctx.db = await load(...)
            yield ctx.db                            # awaited service mutation runs here
            await self._atomic_write(ctx.db)        # one thread hop, fsync+replace, no await between
            ... reflog append (never-raise, inside its threaded closure) ...
        finally:
            await _aio.to_thread(self._lock.release)    # Layer 3 release
    finally:
        await _aio.to_thread(self._proc_mutex.release)  # Layer 2 release
                                                         # Layer 1 released by `async with` exit
```

Lock order is always **`anyio.Lock → proc_mutex → file_lock`**, release reverse, every step in
`try/finally`. **No deadlock:** every path takes the same single lock triple in the same global
order, so the two preconditions for deadlock (multiple parties, inconsistent order) are both absent.
`transaction` is a `@contextlib.asynccontextmanager` annotated `AsyncGenerator[SquadsDB]`; the
blocking `with self._lock:` sugar is gone (its `__enter__` would run on the loop), replaced by the
hand-rolled ordered acquire/finally above. The **same lock triple guards `overwrite()`** (the
index-rebuild commit path used by `repair`/`adopt`/`migrate up`), so that path is exclusive on all
three axes too and never blocks the loop.

### Why not the keeper-thread design (rejected, for the record)

An earlier implementation routed the file lock through a dedicated long-lived *keeper thread* so
that acquire and release always happened on the same thread. It was functionally correct but
**over-engineered** — three mechanisms each undoing the previous one's side effect — and it
introduced a **latent deadlock** (the lock acquire started outside the `try/finally`, so a failure
between acquire and the guard leaked the lock). The three-layer model above is simpler, has a single
consistent lock order, and is safe by construction. Rejected.

> Also rejected: an **async-native file-lock library** — it would swap the single most
> integrity-critical primitive (battle-tested across POSIX/Windows; BUG-000151 was exactly this
> surface) for a less-proven dependency, and its acquire still blocks on an OS syscall, so it either
> threads it (no gain) or polls (worse).

### Validated empirically

The model was validated end-to-end: **50/50 distinct allocations** under both the
concurrent-coroutine-on-one-loop case and the multi-loop-shared-store case. The negative control was
also reproduced — `FileLock(thread_local=False)` **alone** (without the proc-mutex) is unsafe under
concurrent acquisition from the shared worker pool, which is exactly the failure the proc-mutex
exists to prevent.

### Required behaviours to preserve (unchanged and still correct)

- **`lock_timeout` / `filelock.Timeout` must still propagate.** `FileLock(..., timeout=10.0,
  thread_local=False)` raises `filelock.Timeout` from `acquire` when a competing process holds the
  lock too long; threading the acquire via `to_thread` re-raises it on the loop unchanged. Do
  **not** wrap or swallow it. It is raised inside the proc-mutex (Layer 2 held), so the inner
  `finally` is a no-op (the file lock was never acquired) and the outer `finally` releases the
  proc-mutex; the `async with` releases the per-loop lock. No lock leaks on timeout.
- **Reflog never-raise contract.** The reflog append happens strictly **after** the index
  `os.replace` commits, while all locks are held (ADR-000117 §1). The `(OSError, TypeError,
  ValueError)` swallow must stay **inside** `append_line`'s threaded closure so an OSError never
  crosses the loop boundary; `transaction` additionally guards the append loop with
  `except Exception`. Degraded to a warning exactly as today, never failing an already-committed
  mutation.
- **`_atomic_write` stays one thread hop** (Decision 4) — fsync + replace together, no `await`
  between them.

### Regression tests (both required)

Two tests pin the model and must both pass:
- **Concurrent-coroutine, one loop** — on a single event loop launch N `transaction()` coroutines
  via `anyio.create_task_group()` (each allocates an id and `await`s inside the held lock), assert
  distinct ids and counter == N, with the default thread limiter **forced to 1 token** so a faulty
  single-layer model fails deterministically (must stay green at any limiter size).
- **Multi-loop, shared store** — N threads, each its own `anyio.run` over one shared `IndexStore`
  (the existing `test_concurrent_allocation_distinct_ids` shape), assert distinct ids and counter
  == N.

Keep the `filelock.Timeout`-propagation test alongside them.

> Footnote (2026-06-19): this Decision 2 supersedes the 2026-06-18 two-layer amendment and the
> keeper-thread implementation; see REV-000154.

---

## Decision 3 — The single-bridge rule

**Chosen: `anyio.run(...)` lives in exactly ONE place — a shared CLI command decorator in
`_cli/_common.py` that absorbs the existing `@handle_errors`.**

Today `handle_errors` (`_common.py:391`) wraps each command in a sync try/except that turns
`SquadsError` into a clean message + `typer.Exit(1)`. The new decorator folds that try/except in and
adds the one bridge:

```python
def command[**P](fn: Callable[P, Awaitable[None]]) -> Callable[P, None]:
    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
        try:
            anyio.run(functools.partial(fn, *args, **kwargs))   # the ONE bridge
        except SquadsError as exc:
            err_console.print(f"[red]error:[/red] {exc}")
            raise typer.Exit(1) from exc
    return wrapper
```

Each of the ~73 commands across the 11 `_cli/` modules becomes `async def`, swaps
`@handle_errors` → `@common.command`, and `await`s every `svc.*`/helper call. Because
`functools.wraps` + the `ParamSpec` preserve the signature and `wrapper` is a **sync** callable,
Typer's option parsing, `--help`, and `CliRunner` see an unchanged sync command — US2's
byte-identical-behaviour criterion is met by construction.

**Why native `async def` Typer commands are rejected:** Typer (via its asyncclick/anyio handling)
would `asyncio.run` each command itself — that is **73 implicit bridges**, one per command. It pins
us to the asyncio backend (defeating Decision 1's portability), scatters the sync↔async seam across
the whole CLI surface instead of one auditable line, and breaks the "single `anyio.run` per
invocation" acceptance criterion (US2). One explicit bridge we control beats 73 implicit ones we
don't.

**Consequence — the print/resolve helpers go async too.** The helpers in `_common.py` that call the
service must become `async` and run inside the command coroutine (awaited by the command):
`print_item`, `print_subentity`, `_print_item_content`, `_print_full_panes`, `_print_discussion`,
`_print_subentity_summary` (these read bodies/discussion via `svc.*`), and the resolvers
`resolve_item_id_typed`, `resolve_item_id_any`, `resolve_agent_addr` (they call `svc.store.load()`
and the per-type slug lookups). The pure formatters (`e`, `priority_badge`, `parse_*`,
`_build_item_panel_rows`, `_subentity_pane_title_raw`, `resolve_body*`, `resolve_local_id`) stay
sync.

- **`get_service()` (`_common.py:387`) stays sync** — it only constructs `Service` via
  `open_service`; IO lives in the awaited service methods, so no async variant is needed.
- **Root `@app.callback` stays sync** — `set_active_dir`/`apply_timestamp`/`set_actor` are pure
  state-setters; `require_current_schema`/`version_notice` do only cheap `resolve()` config reads.
  It is not a command edge; keeping it sync avoids a second bridge.

---

## Decision 4 — IO abstraction: thin `_aio.py`, not `anyio.Path`

**Chosen: a thin `src/squads/_aio.py` of `to_thread`-wrapped awaitables** — `read_text(path)`,
`write_text(path, text)`, `path_exists(path)`, and a typed `to_thread[T](fn, *args) -> T` helper.
**Not `anyio.Path`.**

Rationale:
- **`anyio.Path` leaks `Any` under pyright strict.** Its methods are typed loosely enough that
  results widen to `Any`, violating the "pyright strict stays clean, no `Any` leaks through
  awaitables" acceptance criterion. A hand-rolled `_aio` with explicit signatures keeps the types
  pinned.
- **The atomic write cannot be expressed by `anyio.Path`.** `_store._atomic_write` does
  tmp-open → write → `flush()` → `os.fsync(fh.fileno())` → `tmp.replace(self.index_path)`. The
  fsync and the replace **must stay on one thread hop with no `await` between them** — an `await`
  there would let another coroutine interleave between the durability barrier and the rename, which
  is exactly the window the atomic-write design closes. So `_atomic_write` becomes a single sync
  closure handed to `_aio.to_thread`; `anyio.Path` would force a hop (and an `await`) per operation
  and can't keep fsync+replace atomic.

`_aio.to_thread` must be called with **zero-arg lambdas or `functools.partial`** (positional forms
widen `T` to `Any` under pyright strict — see the pyright notes below); the `to_thread[T]` helper
is where the return type is pinned for every caller.

**`_rendering/_engine.py::render()` stays sync.** It is already pure — it returns rendered strings
and does no IO. Callers `await _aio.write_text(path, render(...))`. Keeping `render` sync guarantees
the rendered bytes are identical to today (US2).

---

## Decision 5 — FEAT-000033 alignment (the AgentBackend async surface)

The `AgentBackend` ABC in `src/squads/_backends/_base.py` is the surface FEAT-000033 will freeze into
typed Protocols. Its abstract methods that perform IO become **`async def`**:

- `ensure_scaffold(ctx) -> list[Artifact]` → `async def`
- `write_managed(ctx, roster, operators) -> list[Artifact]` → `async def`
- `generate_role_entry(ctx, item, role) -> Artifact` → `async def`
- `generate_skill_entry(ctx, item) -> Artifact` → `async def`
- `remove_artifacts(ctx, item) -> None` → `async def`

**Path-only computation stays sync:**

- `managed_paths(ctx) -> list[str]` — its docstring already guarantees it is **read-only and must
  not create or modify any file**; it only computes the root-relative paths `sq check` expects. It
  stays a plain `def`.
- The `BackendContext` helpers (`rel`, `root_relative`, `root`, `squad_dir`) are pure path math —
  sync.
- `get_backend` / the backend registry stay sync (instantiation only, no IO).

This async signature set — five `async def` IO methods + one sync `managed_paths` — is exactly what
FEAT-000033 freezes into the `AgentBackend` Protocol. Naming it precisely here is the point of the
ADR: the protocol freeze waits on these signatures.

---

## Cross-cutting notes

### Ruff lint groups
- **Enable the `ASYNC` group** — it flags blocking calls inside `async` functions (e.g. a bare
  `path.read_text()` below the CLI edge), which is the *exact* defect class this conversion must not
  reintroduce. It directly enforces the "no blocking IO below the CLI edge" acceptance criterion and
  complements the review-time grep gate. Add `"ASYNC"` to `[tool.ruff.lint] select`. *(Note,
  post-REV-000154: `ASYNC` does not flag `Path.exists`/`Path.mkdir`/sync helper methods — F3/F4/F5
  show the gate is necessary but not sufficient; the review-time read still matters.)*
- **`RUF029` (async function without `await`)** — **enable it.** It catches functions colored
  `async` that don't actually await anything (dead async, an easy mistake during a mechanical
  sweep). It is in the `RUF` family already selected, but call it out so the spike confirms it
  doesn't false-positive on the thin `_aio` wrappers (they do await `to_thread`). Allow targeted
  `# noqa: RUF029` only where a method must match an async Protocol signature but legitimately has no
  await.

### pyright-strict notes
- `anyio.to_thread.run_sync` widens `T` to `Any` when given positional args; always pass a zero-arg
  `lambda` or `functools.partial`. The `_aio.to_thread[T]` helper is the single place that pins the
  return type, so callers stay strict-clean.
- `transaction` must be annotated `AsyncGenerator[SquadsDB]` under
  `@contextlib.asynccontextmanager` (single type-arg form, valid on Python 3.14). Note it currently
  yields `ctx.db` (a `SquadsDB`) while exposing `_current_ctx` on `self` — that internal pattern is
  unchanged; only the decorator and the generator's return annotation change.
- No `Any` may leak through an awaitable: every `_aio` signature is explicitly typed; `anyio.Path`
  is rejected precisely because it would.

### One atomic PR
Async is **transitive** — coloring `transaction` async forces the service async, which forces the
CLI commands async; the suite is red at any half-way point. The conversion therefore lands as **one
atomic PR**, with commits sequenced bottom-up *within* the PR for reviewability (IO leaves → store →
backend → service → CLI → tests) but merged together. The Phase 0 spike de-risks this by proving the
three load-bearing patterns (threaded lock acquire, the single bridge, the one-hop atomic write) on a
thin vertical slice — `_aio.py` + `_store.py` + `_itemfile.py` + one read command (`show`) + one
mutation (`comment`, which exercises `_locked_section_edit` + reflog under the lock) — green before
the full sweep commits.

## Consequences

- FEAT-000033 can freeze the `AgentBackend` Protocol on the async signatures named in Decision 5.
- The cross-process integrity guarantee is preserved unchanged (same `filelock` primitive,
  now `thread_local=False`, safe behind the proc-mutex).
- **Exclusion holds on all three axes** — concurrent coroutines on one loop (per-loop `anyio.Lock`),
  multiple loops / threads in one process (the `threading.Lock` proc-mutex), and separate processes
  (the file lock) — for both `transaction()` and `overwrite()`.
- CLI behaviour is byte-identical (Decision 3's sync wrapper + Decision 4's sync `render`).
- One new runtime dependency (`anyio>=4`); test config gains `anyio_mode = "auto"` + an
  `anyio_backend` fixture pinned to `"asyncio"`.
- Status **Accepted**.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-17T20:31:43Z] Robert Architect:
  - ADR drafted (status Proposed) — covers all five decisions, verified against the live source under src/squads/. Crux is decision 2 (locking): chose option (a) — keep blocking filelock.FileLock, thread only acquire/release via anyio.to_thread, async IO inside the held lock; cross-process exclusion preserved (hard req for parallel subagents), loop stays responsive, transaction becomes @asynccontextmanager AsyncGenerator[SquadsDB]. Rejected (b) whole-tx-in-thread (can't yield an async mutation out of a sync worker closure) and (c) async-lock lib (swaps the most integrity-critical primitive for a 2-hop saving). Other picks: anyio over asyncio; single anyio.run bridge in a _cli/_common.py command decorator absorbing handle_errors (native async Typer commands rejected = 73 implicit bridges); thin _aio.py over anyio.Path (Any leaks + fsync/replace must stay one hop); AgentBackend IO methods (ensure_scaffold/write_managed/generate_role_entry/generate_skill_entry/remove_artifacts) → async def, managed_paths stays sync — that's the FEAT-000033 freeze surface. Recommend enabling ruff ASYNC + RUF029. One atomic PR, de-risked by the spike.
  - @manager ADR-000153 ready for review/acceptance. Once Pierre/I accept it, hand the spike slice (show + comment, proving the three patterns) to @python-dev. Spike risk to flag below.
- [2026-06-18T07:10:21Z] Pierre Chat:
  - Accepted. The spike validated every decision — anyio, locking option (a), the single bridge, _aio.py, and the async AgentBackend surface. Cleared for Phase 1.
<!-- sq:discussion:end -->
