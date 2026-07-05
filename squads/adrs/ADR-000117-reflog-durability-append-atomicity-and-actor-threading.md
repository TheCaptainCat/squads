---
id: ADR-117
sequence_id: 117
type: decision
title: Reflog durability, append atomicity, and actor threading
status: Accepted
author: architect
refs:
- FEAT-24
- TASK-112
- TASK-113
- ADR-114
created_at: '2026-06-15T09:22:28Z'
updated_at: '2026-06-15T09:23:44Z'
---
<!-- sq:body -->
## Context

FEAT-24 adds an append-only JSONL **reflog** — one line per mutating `sq` operation (who, when,
what, before→after) — wired into the single write seam, `IndexStore.transaction()` in
`src/squads/_index/_store.py`. ADR-114 already settled the load-bearing semantic constraint and
this ADR **builds on it, does not relitigate it**: the reflog is written *inside* the index
transaction and is **explicitly NOT a source of truth** — the index stays rebuildable from
frontmatter alone (Invariant 1), `sq repair` never reads it, and a missing or truncated reflog is
never an error.

Olivia Lead flagged three questions to the architect rather than deciding them in the breakdown
(see FEAT-24 discussion): exact append-vs-commit ordering + fsync, ambient-vs-explicit actor
threading, and the line-schema stability tier. This ADR settles those plus the append-atomicity
discipline, so TASK-112 can wire the hook against a fixed contract. The schema's *frozen field
tier* is a FEAT-13 deferral (stated at the end), not decided here.

The relevant shape of the seam today: `transaction()` takes the file lock, `db = self.load()`,
`yield db` (the service mutates `db` and writes the item `.md` files via `update_frontmatter`), then
`self._atomic_write(db)` does an fsync'd temp write + `os.replace` — the single durable commit
point. The clock (`src/squads/_clock.py`) is a module-global override (`set_now`/`now`) set
per-invocation by `--at`; it is the precedent for ambient, injectable per-invocation state.

## Decision

### 1. Write ordering & crash semantics — **append AFTER the index commit; no fsync; applied-without-logged is the tolerated failure**

The reflog line is buffered during the transaction body and appended **after** `_atomic_write`'s
`os.replace` returns successfully, **while still holding the file lock**, before the lock is
released. Ordering rule, unambiguous:

> The index `os.replace` is the commit. The reflog append happens strictly after it, inside the
> lock. Never before.

Reasoning per crash window — and this is decidable *only because* the reflog is not a source of
truth (ADR-114):

- **Line logged, index NOT committed** (would happen if we appended *before* `os.replace`): a
  reflog entry claiming a mutation that never landed. This is **unacceptable** — it makes the
  history *lie*, and a forensic reader (the entire point of US2) would reconstruct an event that
  didn't happen. We design this window out by ordering append strictly after commit.
- **Index committed, line NOT logged** (crash in the gap between `os.replace` and the append, or the
  append itself fails): a real mutation with no history line. This is the **tolerated** failure. It
  costs us one missing line in a log that is, by ADR-114, advisory — a gap in the history, never a
  gap in *state*. The index is correct; `sq check`/`repair` are unaffected; the only loss is an
  audit line, which is exactly the lesser evil the acceptance bar already names
  ("never log-without-apply").

Consequently a failed reflog append **must not** roll back or fail the committed mutation: the
mutation already succeeded and is durable. A reflog write error is swallowed to a non-fatal warning
(stderr), never raised as `SquadsError`. Logging must never be able to break a write that the index
already committed.

**fsync: not required.** `_atomic_write` already fsyncs the index (the source of truth) before
`os.replace`; that durability is non-negotiable and stays. The reflog, being non-authoritative, does
**not** get an fsync per line — the cost (a sync on every mutation, doubling the syscall pressure of
the hot path) buys only the durability of an advisory log across a hard power loss, a window we have
already declared tolerable to lose. We accept that a power loss can lose the last unflushed reflog
line(s); we do not accept paying an fsync on every `sq` mutation to prevent it. (If a future
operator wants stronger durability, that is an additive opt-in, not the 1.0 default.)

### 2. Append atomicity — **one `O_APPEND` write of a single newline-terminated line; readers tolerate a trailing partial line**

Each line is serialized to compact JSON (no embedded newlines — JSON escapes them), a `\n` is
appended, and the whole `bytes` payload is written in **one** `os.write` to a handle opened with
`O_APPEND` (`open(path, "a")` is acceptable on POSIX where a single `write` under `O_APPEND` is
atomic for our line sizes; the writer issues exactly one write call per line, not a buffered
sequence). Discipline:

- **Newline-terminated, never newline-prefixed.** Every complete line ends in `\n`; a well-formed
  log is N complete lines. The only malformed tail a crash can leave is a *truncated final line with
  no terminating newline* (we crashed mid-write or the line was never flushed).
- **One line == one write == one operation.** No partial/streamed line assembly. If a transaction
  conceptually produces multiple records (it should not for v1 — one op, one line), they are still
  each a single atomic append.

**Reader contract (binding on TASK-113 / `sq reflog`):** the reader parses line by line and
**must tolerate a trailing line that does not end in `\n` or does not parse as JSON** by skipping it
(it is an interrupted append, not corruption). A skipped tail line is never an error. Any
*interior* unparseable line is also skipped with a non-fatal warning rather than aborting the read —
the log is advisory, so one bad line never denies the operator the rest of the history.

### 3. Actor threading — **ambient per-invocation actor, set at the CLI root callback, mirroring the clock**

The acting identity (agent slug, `op-` slug, or `system`) reaches the store as **ambient
per-invocation state**, set once and read by the reflog writer — *not* threaded as a parameter
through every mutating service method. A new module (e.g. `src/squads/_actor.py`, or actor state
co-located with the reflog writer) exposes the same shape as `_clock`:
`set_actor(slug)` / `current_actor() -> str`, with a sensible default (`"system"`) when unset.

Justified against the layering (`_cli → _services → store`) and testability:

- **Layering.** The actor is request-scoped context, exactly like "now". Threading it as a parameter
  would force an `actor` argument onto `set_status`, `update`, `remove_item`, `add_ref`, every
  sub-entity mutation and the `_base` create/`_bump`/`_locked_section_edit` primitives — a wide,
  invasive signature change for a cross-cutting concern, fighting the `_cli → _services → store`
  flow rather than respecting it. The ambient approach keeps the store's reflog hook reading
  `current_actor()` the same way `_atomic_write` reasons about "now" via the clock — one seam, zero
  signature churn. The CLI root callback (`_cli/__init__` / `_cli/_common.py`) resolves the actor
  once per invocation from `--as`/`--author`/the invoking agent and calls `set_actor`, the same
  place `--at` calls `clock.set_now`.
- **Testability.** It is injectable exactly like the frozen clock: a test sets the actor (or uses a
  fixture mirroring `frozen_time`) and asserts the logged line. This is *more* testable than a
  parameter, because service-level tests already exercise mutations without passing an actor today;
  the ambient default means existing tests keep working and reflog assertions are opt-in.
- **One subtlety, stated for the dev.** Ambient state must be **set and cleared per invocation** (a
  `try/finally` or context manager at the root callback), so a long-lived process or a test that
  reuses the interpreter never leaks one invocation's actor into the next — the same hygiene
  `clock.set_now(None)` requires. `comment`'s existing `as_slug` becomes the value the callback
  feeds into `set_actor`; the service method keeps using `as_slug` for the *comment author* and the
  store reads the same identity ambiently for the *log line* — they agree by construction.

The **op name + before→after delta** are *not* ambient — they are captured **at each call site**,
because only the call site knows what changed (e.g. `status: Ready→InProgress`). The call site hands
the op + delta to the transaction (buffered on the transaction context); the writer combines them
with the ambient actor + `clock.iso(clock.now())` timestamp at commit time.

### 4. Line schema + version field (shape only; frozen tier deferred to FEAT-13)

Each reflog line is a JSON object carrying **at least** these fields (names/types/exact tiering are
FEAT-13's to freeze):

- `v` — **schema version** of the line format (a short string, tracking the release that introduced
  the shape, consistent with the `SCHEMA_VERSION` dotted-string convention). Present from line one
  so the format can evolve additively without breaking readers.
- `ts` — ISO-8601 UTC timestamp with trailing `Z`, from `clock.iso(clock.now())` (so `--at` and the
  frozen-clock fixture flow through).
- `actor` — the resolved acting identity slug (agent slug, `op-…`, or `system`), from the ambient
  actor (point 3).
- `op` — the operation name from a closed vocabulary
  (`create`/`status`/`update`/`body`/`comment`/`subentity`/`ref`/`link`/`remove`/`repair`/`migrate`/…),
  captured at the call site.
- `target` — the affected item ID(s) (and, where cheap, `type`), e.g. the formatted `id`.
- `delta` — a compact before→after **summary** of what changed (e.g. `{"status": ["Ready",
  "InProgress"]}` or the gone-item snapshot ADR-114 specifies for `remove`). A *summary*, not a full
  document diff — enough to reconstruct the event, not to replay state (it is not a source of
  truth).

The schema is **versioned from day one and forward-compatible by addition**: readers key off `v`,
ignore unknown fields, and tolerate skipped lines (point 2). The **exact frozen field set and each
field's stability tier** (promised-stable-through-1.0 vs. additive) are **deferred to FEAT-13**,
which already owns the reflog schema promise (FEAT-24 US3 routes it there, and ADR-114 already
deferred the `remove`-line fields + the "gaps are sanctioned" guarantee onto the same contract).

## Consequences

- **TASK-112 is unblocked** with a fixed contract: append after `os.replace` under the lock; no
  per-line fsync; a failed append warns and never fails the committed mutation; one `O_APPEND`
  newline-terminated write per op; ambient actor via a `_clock`-shaped module set at the root
  callback; op+delta captured at each call site and buffered on the transaction context.
- **TASK-113's reader** must skip a trailing partial/unparseable line (and warn-skip interior bad
  lines) and treat a missing reflog as empty — both are normal, never errors.
- **Invariant 1 holds unchanged.** Nothing here makes the index depend on the reflog; the reflog
  stays advisory and the index stays rebuildable from frontmatter.
- **Deferred onto FEAT-13 (binding obligation):** the reflog file location
  (`<squad>/.reflog.jsonl`), the **exact line schema** (the field set sketched above), the **schema
  version field's** convention, and each field's **stability tier** through 1.0 must be stated in
  the 1.0 contract doc as part of FEAT-13's reflog-schema promise. This ADR fixes only the
  *shape*; FEAT-13 freezes it.

## Status

Accepted.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
