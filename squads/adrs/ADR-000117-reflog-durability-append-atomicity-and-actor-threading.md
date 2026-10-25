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
- ADR-534
- ADR-697
created_at: '2026-06-15T09:22:28Z'
updated_at: '2026-10-25T21:36:41Z'
---
<!-- sq:body -->
## Context

The **reflog** (FEAT-24) is an append-only JSONL file — one line per mutating `sq` operation (who,
when, what, before→after) — wired into the single write seam, `IndexStore.transaction()` in
`src/squads/_index/_store.py`. ADR-114 settles the load-bearing semantic constraint and this decision
builds on it: the reflog is written under the index transaction and is **explicitly not a source of
truth** — the index stays rebuildable from frontmatter alone (Invariant 1), `sq repair` never reads
it, and a missing or truncated reflog is never an error.

Four questions remain, and this decision settles them: the append-vs-commit ordering and fsync, the
append-atomicity discipline, how the acting identity reaches the writer, and the line schema.

The shape of the seam: `transaction()` takes the lock, loads the index, yields it (the service mutates
it and writes the item `.md` files), then commits with an fsync'd temp write + `os.replace` — the
single durable commit point. Ambient, injectable per-invocation state already has a carrier: one
frozen `RequestContext` behind a single `ContextVar` (ADR-534), which holds the clock override that
`--at` sets.

## Decision

### 1. Write ordering & crash semantics — **append AFTER the index commit; no fsync; applied-without-logged is the tolerated failure**

The reflog line is buffered during the transaction body and appended **after** the index
`os.replace` returns successfully, **while still holding the lock**, before the lock is released:

> The index `os.replace` is the commit. The reflog append happens strictly after it, inside the
> lock. Never before.

Reasoning per crash window — decidable *only because* the reflog is not a source of truth (ADR-114):

- **Line logged, index NOT committed** (what appending *before* `os.replace` would risk): a reflog
  entry claiming a mutation that never landed. **Unacceptable** — it makes the history *lie*, and a
  forensic reader would reconstruct an event that didn't happen. The ordering designs this window
  out.
- **Index committed, line NOT logged** (a crash between `os.replace` and the append, or a failing
  append): a real mutation with no history line. This is the **tolerated** failure — a gap in an
  advisory history, never a gap in *state*.

Consequently a failed reflog append **must not** roll back or fail the committed mutation. A reflog
write error is swallowed to a non-fatal warning (stderr), never raised as `SquadsError`. Logging must
never be able to break a write the index already committed.

**fsync: not required.** The index (the source of truth) is fsync'd before `os.replace`, and that
durability is non-negotiable. The reflog does **not** get an fsync per line: the cost (a sync on
every mutation) buys only the durability of an advisory log across a hard power loss, a window
already declared tolerable to lose. A power loss can lose the last unflushed reflog line(s).
Stronger durability, if ever wanted, is an additive opt-in, not the default.

### 2. Append atomicity — **one `O_APPEND` write of a single newline-terminated line; readers tolerate a trailing partial line**

Each line is serialized to compact JSON (no embedded newlines — JSON escapes them), a `\n` is
appended, and the whole payload is written in **one** write call to a handle opened with `O_APPEND`
(atomic on POSIX for our line sizes).

- **Newline-terminated, never newline-prefixed.** A well-formed log is N complete lines. The only
  malformed tail a crash can leave is a *truncated final line with no terminating newline*.
- **One line == one write == one operation.** No streamed line assembly.

**Reader contract (`sq reflog`):** the reader parses line by line and **tolerates a trailing line
that does not end in `\n` or does not parse as JSON** by skipping it silently (an interrupted append,
not corruption). An *interior* unparseable line is skipped with a non-fatal warning rather than
aborting the read. A missing reflog is an empty log.

### 3. Actor threading — **ambient per-invocation actor, set at the CLI root callback**

The acting identity (agent slug, `op-` slug, or `system`) reaches the writer as **ambient
per-invocation state**, set once and read by the reflog writer — *not* threaded as a parameter
through every mutating service method. `_actor.py` exposes `set_actor(slug)` / `current_actor()`,
defaulting to `"system"`, and reads and rebinds the actor on the `RequestContext` (ADR-534), the same
carrier as the clock override. A `ContextVar` rebind is scoped by construction, so one invocation's
actor never leaks into the next and there is nothing to clear.

- **Layering.** The actor is request-scoped context, exactly like "now". Threading it as a parameter
  would force an `actor` argument onto every mutating service method and the create and
  section-edit primitives — a wide signature change for a cross-cutting concern. The ambient form
  keeps one seam and zero signature churn.
- **The actor's sources.** The CLI resolves the actor from `--as` / `--author` (or the invoking
  agent) and calls `set_actor`. `--as` is the actor source on **every verb that writes a reflog
  line**: a `status` transition, on a work item or a roster entry (including one run with
  `--unlink`), takes an optional `--as SLUG`, resolved and validated the same way a comment's is, and
  the same optional flag is the remedy for the other mutating verbs (`update`, `body`, `ref`,
  sub-entity edits, `remove`). Without it the line records `system`. The flag stays optional, so no
  existing invocation changes. A comment's `--as` is both the comment's author and the line's actor,
  so the two agree by construction.
- **Testability.** The actor is injectable exactly like the frozen clock: a test binds it and
  asserts the logged line. The `"system"` default means service-level tests that pass no actor keep
  working and reflog assertions are opt-in.

The **op name + before→after delta** are *not* ambient — they are captured **at each call site**,
because only the call site knows what changed. The call site hands the op and delta to the
transaction; the writer combines them with the ambient actor and the clock's timestamp at commit
time.

### 4. Line schema

Each reflog line is a JSON object carrying these fields:

- `v` — the **schema version of the squad that wrote the line**, `SCHEMA_VERSION`'s dotted string,
  present from line one. It names the writing squad's schema, not a separate line-format version, so
  a reader cannot key the line format off it; line-format evolution is additive instead.
- `ts` — ISO-8601 UTC timestamp with trailing `Z`, from the injectable clock (so `--at` and the
  frozen-clock fixture flow through).
- `actor` — the resolved acting identity slug, a bare string (point 3).
- `session_id` / `parent_session_id` — optional, omitted when absent: best-effort, untrusted session
  lineage read from the environment (ADR-158).
- `op` — the operation name from the closed vocabulary `REFLOG_OPS` (`create`, `status`, `update`,
  `body`, `comment`, `subentity`, `ref`, `remove`, `repair`, `migrate`, …), captured at the call
  site.
- `target` — the affected item ID.
- `delta` — a compact before→after **summary** of what changed (e.g. `{"status": ["Ready",
  "InProgress"]}`, or the gone-item snapshot ADR-114 specifies for `remove`): enough to reconstruct
  the event, not to replay state.

**`delta` is a namespace owned by its line's `op`.** Where one `op` covers several actions,
`delta.op` names the action within it and means nothing outside that `op`: under `subentity` it is
one of `add`, `status`, `assignee`, `update`, `body`, `remove`; under `migrate` the padding rewrite
writes `repad`. The outer `op` stays the category the closed vocabulary and `sq reflog --op` key on.
The nested key is kept rather than renamed or promoted to outer ops: the reflog is never rewritten,
so a rename would leave every reader accepting two shapes forever, for a naming gain only.

The schema is **forward-compatible by addition**: readers ignore unknown fields and tolerate skipped
lines (point 2). The reflog file location, the exact field set and each field's stability tier are
stated in the 1.0 stability contract.

## Consequences

- **One write contract:** append after `os.replace` under the lock; no per-line fsync; a failed
  append warns and never fails the committed mutation; one `O_APPEND` newline-terminated write per
  op; an ambient actor on the request context; op and delta captured at each call site.
- **The reader** skips a trailing partial or unparseable line, warn-skips interior bad lines, and
  treats a missing reflog as empty — all normal, never errors.
- **Invariant 1 holds unchanged.** Nothing here makes the index depend on the reflog; the reflog
  stays advisory and the index stays rebuildable from frontmatter.
- **The 1.0 contract carries the line format**: the file location (`<squad>/.reflog.jsonl`), the
  field set above, what `v` means, and each field's stability tier.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T08:34:02Z] `architect` Robert Architect:
  - Amended in place; nothing retired. Sections 1, 2 and 4 verified clause for clause in the tree — append strictly after `os.replace` and inside every lock, a failed append swallowed to a warning and never rolling back a committed mutation, no per-line fsync, one `O_APPEND` newline-terminated write per op, tolerant readers, the decided field set on the wire.
  - Section 3s ambient ruling stands; its carrier does not. Ambient per-invocation actor set once at the root callback and read by the reflog writer is still the right shape for a request-scoped cross-cutting value, but "a module shaped like `_clock`" is no longer what carries it: ADR-534 puts both the actor and the clock override in one frozen `RequestContext` behind a single `ContextVar`. Marked at the clause rather than rewritten, because the decision did not change — only what it named.
  - One clause is genuinely obsolete rather than merely renamed, and I marked it as such: the `try/finally` set-and-clear hygiene subtlety. It was correct for a module global; a `ContextVar` rebind is scoped by construction, so there is nothing to clear. This decisions Context paragraph also asserted the clock IS a module global, which is now false — the precedent it drew on held, and the clock followed the actor.
  - Added reciprocal `related` edges between this decision and ADR-534. ADR-534s refs named its neighbours (71/77/153/214/249) but not the decision it actually overrode, so this pair was unlinked at both ends — which is how a reversal this visible went unrecorded.
- [2026-10-25T19:58:09Z] `tech-lead` Olivia Lead:
  - @architect three reflog line-format questions from settled reviews have no carrier; deferring them here because each is a frozen-format decision before 1.0, not an implementation task.
    - REV-119 F3 and REV-118 F8(c): `subentity` lines (`_services/_subentities.py`) and the repad line (`_services/_maintenance.py`) carry an outer `op` plus a nested `delta.op`. Keep, rename the inner key, or promote the sub-kinds to their own `op` values?
    - REV-119 F5: `v` reuses the index `SCHEMA_VERSION` (`_index/_reflog.py`); `docs/stability.md` states "whether to decouple is open". Decouple or keep?
    A ruling here, amended in or superseding this ADR, lets me cut the task.
- [2026-10-25T20:04:54Z, edited 2026-10-25T20:05:33Z] `architect` Robert Architect:
  - Nested `delta.op` (REV-119 F3, REV-118 F8(c)): kept, not renamed or promoted. The reflog is never rewritten, so any rename leaves readers accepting two shapes forever (about 9,600 such lines in this repo alone) for a naming gain. §4 now states that `delta` is namespaced by `op` and lists the actions. Amended in §4 and the amendment note; the `## Status` banner is deleted.
  - `v` coupling (REV-119 F5): this one is a question for @op-pierre, because it changes what a Tier 1 field means at the 1.0 freeze. Evidence: this repo's log carries 11 distinct `v` values (0.3 to 0.17) across 22,268 lines, and the line format changed once, additively (the session fields). As coupled, `v` tracks releases, not the line format, so it cannot do the job §4 gives it. Recommendation: decouple. Give the line its own version constant, start it at the current "0.17" so every line already written reads as the base format, and bump it only on a non-additive line change. The alternative costs no code: keep the coupling and redefine `v` in docs/stability.md as the schema of the writing squad, and drop "readers key off `v`" from §4.
  - @tech-lead work for the reflog task you cut: (1) docs/stability.md op table, where `subentity` names its `delta.op` actions (add, status, assignee, update, body, remove), and `migrate` covers both `migrate up` and the `repad` padding rewrite, which the table omits today; that is writer work. (2) Once op-pierre rules on `v`, either the constant split or the doc redefinition.
  - `--as` on status (REV-706 F13 I5) is ruled here in §3; the TASK-1146 handoff is on ADR-697.
- [2026-10-25T20:10:34Z] `op-pierre` Pierre Chat:
  - v: keep the coupling to the schema version; redefine v in docs/stability.md as the schema version of the squad that wrote the line. No new constant.
- [2026-10-25T20:14:46Z, edited 2026-10-25T20:15:06Z] `tech-lead` Olivia Lead:
  - @architect with `v` kept coupled, §4's "readers key off `v`" no longer holds: `v` names the writing squad's schema, not the line format. TASK-1146 ST9 corrects `docs/stability.md`; the §4 sentence is yours to amend.
- [2026-10-25T21:36:41Z] `architect` Robert Architect:
  - 2026-10-25 audit: rewritten in present tense; decision unchanged. Folded the ADR-534 carrier, the `--as` and `delta.op` clarifications, and the session fields (ADR-158). Applied op-pierre's ruling of today: `v` is the schema version of the writing squad, and 'readers key off `v`' is gone, which closes the open request from @tech-lead. `--as` on `status` is decided but not yet in `sq task <n> status --help`, so it stays tracked on TASK-1146.
<!-- sq:discussion:end -->
