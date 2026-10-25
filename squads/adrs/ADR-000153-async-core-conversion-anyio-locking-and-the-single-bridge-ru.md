---
id: ADR-153
sequence_id: 153
type: decision
title: 'Async-core conversion: anyio, locking, and the single-bridge rule'
status: Accepted
author: architect
refs:
- FEAT-34:addresses
- ADR-663
created_at: '2026-06-17T20:29:57Z'
updated_at: '2026-10-25T21:36:47Z'
---
<!-- sq:body -->
## Context

The consumers on squads' roadmap are async-native — Textual (`sq ui`), a web front end, and an HTTP
remote service (FEAT-33). A synchronous core would force each of them to wrap every call in executor
threads forever, and the calling convention a remote protocol freezes is a now-or-painful choice:
retrofitting async under a frozen sync protocol is the painful kind. So every layer below the CLI —
the service mixins, the index store's locked transactions, and all file IO — is async.

**Honesty clause:** this makes nothing faster for a single CLI invocation — it may add a microsecond
of event-loop startup. The value is purely architectural: one async calling convention for the whole
stack, native consumption by the TUI/web/remote layers, and server-mode concurrency without a thread
pool bolted to a blocking core.

This decision records five rulings. Decision 2 (locking) is the crux and gets the most space.

---

## Decision 1 — anyio over raw asyncio

**Chosen: anyio (`anyio>=4`).**

- **Structured concurrency** (task groups, cancellation scopes) — the shape FastAPI and Textual
  both live in; consuming the service from either is native.
- **Backend-agnostic.** anyio runs on asyncio *or* trio. Raw `asyncio` would pin the entire core
  to one event loop forever; anyio keeps the door open and costs nothing (the test backend is pinned
  to `"asyncio"`).
- **Built-in `to_thread.run_sync`** — exactly the primitive needed for the blocking `filelock`
  acquire and for the atomic-write closure (Decisions 2 and 4). No bespoke executor management.
- **One `anyio.run` bridge** is all the sync edge needs (Decision 3).

**Why not bare asyncio:** it offers no structured-concurrency primitives without extra scaffolding,
pins the core to a single loop implementation, and gains nothing the anyio facade doesn't wrap.

---

## Decision 2 — Locking strategy (the crux)

The index transaction (`src/squads/_index/_store.py::transaction()`) is the integrity core: every
allocation of the global counter and every read-modify-write of `.squads.json` happens inside it.
The mutation body runs `await`s (item-file IO, the reflog append), so the lock is **held across
`await` points** and the transaction must be exclusive on three distinct axes:

1. **Concurrent coroutines on one event loop** — a TUI/web/remote consumer driving one `Service` →
   one `IndexStore` with overlapping mutations.
2. **Multiple event loops in one process** — the test suite runs N threads, each with its own
   `anyio.run`, over one shared `IndexStore`. Any in-loop primitive is bound to the loop it was
   first used on and cannot serialise a second loop.
3. **Separate OS processes** — parallel `sq` subagent invocations must never corrupt `.squads.json`
   or collide on the global counter.

And the blocking `filelock` acquire/release must never run on the event loop.

No single primitive covers all three: an `anyio.Lock` is loop-bound (fails axis 2), a
`threading.Lock` knows nothing of coroutines (fails axis 1), and `filelock` is an OS advisory lock
mediated through a shared worker-thread pool whose in-process reentrancy is keyed by the acquiring
thread (fails axes 1 and 2). So the decision is a **three-layer model**, taken in one fixed order and
released in reverse, all in `try/finally`.

### The three-layer model

**Layer 1 — per-loop `anyio.Lock` (serialises coroutines).** An `anyio.Lock` binds to the event loop
it is first used on, so a single shared instance cannot span loops. The store keeps a **cache of
`anyio.Lock` keyed by running-loop identity** and fetches (or lazily creates) the lock for the
*current* loop, guarded by a small `threading.Lock` so the cache itself is safe across threads. This
lock is taken **first**, on the loop, and serialises all coroutines running on that loop.

**Layer 2 — in-process `threading.Lock` (the proc-mutex).** Acquired and released via
`anyio.to_thread`, it wraps the file-lock section and guarantees that **only one thread in the whole
process** is ever inside the file-lock critical section — across every event loop and every worker
thread. This is the layer that closes axis 2 (and the cross-thread part of axis 1).

**Layer 3 — `FileLock(thread_local=False)` (cross-process).** Acquired and released via
`anyio.to_thread`, **inside** the proc-mutex, it provides axis 3. `thread_local=False` keys its
reentrancy to the lock object rather than the acquiring worker thread, which is safe **precisely
because** the proc-mutex guarantees single-threaded entry: the one documented failure mode of
`thread_local=False` (concurrent acquisition from different worker threads) is unreachable.

```
async with self._loop_lock():                     # Layer 1 — per-loop anyio.Lock, on the loop, FIRST
    await _aio.to_thread(self._proc_mutex.acquire) # Layer 2 — proc-mutex, off-loop
    try:
        await _aio.to_thread(self._lock.acquire)   # Layer 3 — filelock; may raise Timeout, propagates
        try:
            db = await load(...)
            yield db                                # awaited service mutation runs here
            await self._atomic_write(db)            # one thread hop, fsync+replace, no await between
            ... reflog append (never-raise, inside its threaded closure) ...
        finally:
            await _aio.to_thread(self._lock.release)    # Layer 3 release
    finally:
        await _aio.to_thread(self._proc_mutex.release)  # Layer 2 release
                                                         # Layer 1 released by `async with` exit
```

Lock order is always **`anyio.Lock → proc_mutex → file_lock`**, released in reverse, every step in
`try/finally`. **No deadlock:** every path takes the same lock triple in the same global order.
`transaction` is a `@contextlib.asynccontextmanager` annotated `AsyncGenerator[SquadsDB]`; there is
no blocking `with self._lock:` (its `__enter__` would run on the loop). The **same lock triple guards
`overwrite()`** (the index-rebuild commit path used by `repair`/`adopt`/`migrate up`).

Per-transaction state does not live on `IndexStore` instance attributes: it is carried by a
task-local `ContextVar`, because an instance attribute is per-store and the state is per-task
(ADR-663 §4).

**Rejected:** a dedicated long-lived *keeper thread* for the file lock — functionally correct but
over-engineered, three mechanisms each undoing the previous one's side effect, and prone to a lock
leak when acquire starts outside the `try/finally`. Also rejected: an **async-native file-lock
library** — it would swap the most integrity-critical primitive (battle-tested across POSIX/Windows;
BUG-151 was exactly this surface) for a less-proven dependency, and its acquire still blocks on an OS
syscall, so it either threads it (no gain) or polls (worse).

**Validated:** distinct allocations under both the concurrent-coroutine-on-one-loop case and the
multi-loop-shared-store case, with the negative control — `FileLock(thread_local=False)` alone,
without the proc-mutex, is unsafe under concurrent acquisition from the shared worker pool.

### Behaviours the model preserves

- **`filelock.Timeout` propagates.** `FileLock(..., timeout=10.0, thread_local=False)` raises it from
  `acquire` when a competing process holds the lock too long; threading the acquire re-raises it on
  the loop unchanged, and it is never wrapped or swallowed. It is raised inside the proc-mutex, so the
  inner `finally` is a no-op, the outer `finally` releases the proc-mutex, and the `async with`
  releases the per-loop lock. No lock leaks on timeout.
- **The reflog never raises.** The append happens strictly **after** the index `os.replace` commits,
  while all locks are held (ADR-117 §1). The OS-error swallow stays **inside** the append's threaded
  closure so an `OSError` never crosses the loop boundary, and `transaction` additionally guards the
  append loop. A failure degrades to a warning, never failing a committed mutation.
- **`_atomic_write` stays one thread hop** (Decision 4) — fsync + replace together, no `await`
  between them.

Regression tests pin the model: N `transaction()` coroutines on one loop under a task group with the
default thread limiter forced to one token (so a faulty single-layer model fails deterministically),
N threads each with its own `anyio.run` over one shared store, and the `filelock.Timeout`
propagation test.

---

## Decision 3 — The single-bridge rule

**`anyio.run(...)` lives in exactly ONE place: the `command` decorator in `_cli/_common.py`**, which
also absorbs the error handling that turns `SquadsError` into a clean message + `typer.Exit(1)`:

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

Every CLI command is `async def`, wrapped by `@common.command`, and `await`s every service call.
Because `functools.wraps` + the `ParamSpec` preserve the signature and `wrapper` is a **sync**
callable, Typer's option parsing, `--help`, and `CliRunner` see an ordinary sync command. An
addressed-item command (`sq <type> <n> <verb>`) crosses the bridge twice, sequentially — once for the
group's id-resolving callback and once for the verb — never nested. `sq ui` runs Textual's own event
loop and calls the async service natively, without the bridge.

**Why native `async def` Typer commands are rejected:** Typer would run each command's event loop
itself — one implicit bridge per command. It pins the asyncio backend (defeating Decision 1's
portability) and scatters the sync↔async seam across the whole CLI surface instead of one auditable
line.

**Consequence — the CLI helpers that call the service are async** and run inside the command
coroutine: the item/sub-entity printers that read bodies and discussions, and the id/slug resolvers
that load the index. Pure formatters and parsers stay sync. `get_service()` stays sync — it only
constructs the `Service`; IO lives in the awaited service methods. The root `@app.callback` stays
sync — it only binds per-invocation state and reads config cheaply — so it is not a second bridge.

---

## Decision 4 — IO abstraction: thin `_aio.py`, not `anyio.Path`

**Chosen: a thin `src/squads/_aio.py` of `to_thread`-wrapped awaitables** — `read_text(path)`,
`write_text(path, text)`, `path_exists(path)`, a typed `to_thread[T](fn) -> T` helper, and
`atomic_replace_sync` for the one-hop atomic write. **Not `anyio.Path`.**

- **`anyio.Path` leaks `Any` under pyright strict.** Its results widen to `Any`; a hand-rolled `_aio`
  with explicit signatures keeps the types pinned.
- **The atomic write cannot be expressed by `anyio.Path`.** The index write does tmp-open → write →
  `flush()` → `os.fsync` → replace. The fsync and the replace **must stay on one thread hop with no
  `await` between them** — an `await` there would let another coroutine interleave between the
  durability barrier and the rename, which is exactly the window the atomic-write design closes. So
  the write is a single sync closure handed to `_aio.to_thread`.

`_aio.to_thread` takes a **zero-arg callable** (a lambda or `functools.partial`), because positional
forms widen `T` to `Any` under pyright strict; the helper is where the return type is pinned for every
caller.

**`_rendering/_engine.py::render()` stays sync.** It is pure — it returns rendered strings and does no
IO. Callers `await _aio.write_text(path, render(...))`.

---

## Decision 5 — The AgentBackend async surface

The `AgentBackend` ABC in `src/squads/_backends/_base.py` is the surface any typed or remote
protocol freezes. Its abstract methods that perform IO are **`async def`**: `ensure_scaffold`,
`write_managed`, `generate_role_entry`, `generate_skill_entry`, `remove_artifacts` and
`candidate_orphans`.

**Path-only computation stays sync:** `managed_paths(ctx)` (read-only by contract — it only computes
the root-relative paths `sq check` expects), the per-entry path helpers, the `BackendContext` path
helpers (`rel`, `root_relative`, `root`, `squad_dir`), and the registry lookup (instantiation only,
no IO).

---

## Cross-cutting notes

### Ruff lint groups
- **The `ASYNC` group is selected** — it flags blocking calls inside `async` functions (e.g. a bare
  `path.read_text()` below the CLI edge), the defect class this design must not reintroduce. It does
  not flag `Path.exists`/`Path.mkdir` or sync helper methods, so it is necessary but not sufficient;
  review still reads for blocking IO.
- **`RUF029` (async function without `await`) belongs in the lint set**: it catches functions
  colored `async` that don't await anything. It is a ruff preview rule, so it runs only with preview
  enabled for it. A targeted `# noqa: RUF029` is allowed only where a method must match an async signature
  but legitimately has no await.

### pyright-strict notes
- `anyio.to_thread.run_sync` widens `T` to `Any` when given positional args; always pass a zero-arg
  callable. The `_aio.to_thread[T]` helper is the single place that pins the return type.
- `transaction` is annotated `AsyncGenerator[SquadsDB]` under `@contextlib.asynccontextmanager`
  (single type-arg form, valid on Python 3.14).
- No `Any` may leak through an awaitable: every `_aio` signature is explicitly typed.

## Consequences

- A remote or typed protocol can freeze the `AgentBackend` surface on the async signatures named in
  Decision 5.
- The cross-process integrity guarantee is the same `filelock` primitive, with `thread_local=False`
  made safe by the proc-mutex.
- **Exclusion holds on all three axes** — concurrent coroutines on one loop (per-loop `anyio.Lock`),
  multiple loops / threads in one process (the proc-mutex), and separate processes (the file lock) —
  for both `transaction()` and `overwrite()`.
- CLI behaviour is unchanged by the async core (Decision 3's sync wrapper + Decision 4's sync
  `render`).
- One runtime dependency (`anyio>=4`); the test config runs async tests under anyio with the backend
  pinned to `"asyncio"`.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-17T20:31:43Z] `architect` Robert Architect:
  - ADR drafted (status Proposed) — covers all five decisions, verified against the live source under src/squads/. Crux is decision 2 (locking): chose option (a) — keep blocking filelock.FileLock, thread only acquire/release via anyio.to_thread, async IO inside the held lock; cross-process exclusion preserved (hard req for parallel subagents), loop stays responsive, transaction becomes @asynccontextmanager AsyncGenerator[SquadsDB]. Rejected (b) whole-tx-in-thread (can't yield an async mutation out of a sync worker closure) and (c) async-lock lib (swaps the most integrity-critical primitive for a 2-hop saving). Other picks: anyio over asyncio; single anyio.run bridge in a _cli/_common.py command decorator absorbing handle_errors (native async Typer commands rejected = 73 implicit bridges); thin _aio.py over anyio.Path (Any leaks + fsync/replace must stay one hop); AgentBackend IO methods (ensure_scaffold/write_managed/generate_role_entry/generate_skill_entry/remove_artifacts) → async def, managed_paths stays sync — that's the FEAT-33 freeze surface. Recommend enabling ruff ASYNC + RUF029. One atomic PR, de-risked by the spike.
  - @manager ADR-153 ready for review/acceptance. Once Pierre/I accept it, hand the spike slice (show + comment, proving the three patterns) to @python-dev. Spike risk to flag below.
- [2026-06-18T07:10:21Z] `op-pierre` Pierre Chat:
  - Accepted. The spike validated every decision — anyio, locking option (a), the single bridge, _aio.py, and the async AgentBackend surface. Cleared for Phase 1.
- [2026-08-03T08:34:48Z] `architect` Robert Architect:
  - Amended in place; nothing retired. Every decision here verified in the tree: anyio, the three-layer exclusion verbatim in `_store.py`, exactly one `anyio.run` in the codebase at `_cli/_common.py:685`, `_aio.py` with `atomic_replace_sync` keeping fsync and replace on one hop, the async ABC with `managed_paths` left sync, ruff `ASYNC` selected.
  - One clause withdrawn, and it is worth separating from the rest: a pyright note that read as an observation while doing the work of a ruling. It blessed `transaction` exposing `_current_ctx` on `self` as "unchanged". ADR-663 section 4 replaces that with a task-local `ContextVar` and derives the rule that no per-transaction state may live on `IndexStore` instance attributes — an instance attribute is per-store, a task-local is per-task, and those coincide only while one store serves one task. The pattern this note declared unchanged was the defect, and the note is why it looked settled.
  - The annotation requirement the note existed to carry (`AsyncGenerator[SquadsDB]` under `@asynccontextmanager`, single type-arg form) is untouched. Added reciprocal `related` edges with ADR-663, which named ADR-534 and ADR-249 but not the decision it overrode.
- [2026-10-25T21:36:47Z] `architect` Robert Architect:
  - 2026-10-25 audit: rewritten; decisions unchanged. Folded the ADR-663 ContextVar rule. Decision 5 now lists six async methods (`candidate_orphans` too). Noted that `sq <type> <n> <verb>` crosses the single bridge twice in sequence (`_cli/_common.py` `command`). Dropped the Accepted banner, the PR and spike plan, and the footnote. Code gap reported to the manager: RUF029 is a ruff preview rule and is not active.
<!-- sq:discussion:end -->
