---
id: ADR-622
sequence_id: 622
type: decision
title: Bulk event import (sq import)
status: Proposed
author: architect
refs:
- REV-565
description: A JSONL event-import command that replays a project's history in one
  process, with per-event timestamps and attribution, to replace hundreds of per-mutation
  sq calls.
created_at: '2026-07-23T07:56:31Z'
updated_at: '2026-07-23T07:56:55Z'
---
<!-- sq:body -->
## Context

Replaying an existing project's revision history into a squad — dated item creations, status
moves, attributed discussion handoffs, refs, and sub-entity states — is today one `sq` call per
mutation. `--at` forges one timestamp per invocation and does its job well, but a faithful
migration of a mature corpus (dozens of items, hundreds of dated comments) becomes hundreds of
separate process spawns, each paying full interpreter + spec-load startup, and forces every
migrator to hand-roll a subprocess driver. Adopting squads into a pre-existing project is the
same shape of problem from the other end: onboarding a project's accumulated history is a bulk
load, not an interactive session.

The primitive that dissolves this is a single-process **bulk event import**: the migrator emits
one file describing every mutation with its own timestamp and actor, and one command replays it.
The dominant cost — per-mutation process startup — collapses to one process; per-event time and
attribution stay faithful because a single process can rebind the ambient clock/actor per event
(the request-scoped `RequestContext` seam already supports this in-process; only the CLI edge
previously exercised it, once per invocation).

## Decision

Add `sq import <file>`: a JSONL event stream where each line is one mutation
`{"op": …, "at": …, "as": …, …}`, replayed in a single process against the active squad. Item
files remain the source of truth; the index is written once at the end as its derived commit.

### Event schema

One JSON object per line (JSONL — a partial write leaves the last line parseably broken, and the
format streams). Fields common to every event:

- `op` (required) — the mutation verb (enumerated below).
- `at` (optional, ISO-8601 UTC) — the forged timestamp for this event. When omitted, the event
  inherits the previous event's `at` (or a file/CLI-level default), so a burst at one moment need
  not repeat it. `at` drives `clock` for that event only — the per-event equivalent of `--at`.
- `as` (optional) — the acting slug (a registered role or operator). Drives attribution
  (comment author, `updated_at` session) and, for `create`, the default author. Inherits the
  prior event's value or the CLI default.

**Application order is file order, authoritatively.** A `create` must precede any event that
targets it; the importer does not reorder by `at`. `at` values are data recorded onto the items,
not a sort key — real history legitimately contains out-of-order dated backfills. A
`--check-monotonic` flag can advise on non-decreasing `at`, but never reorders.

### Addressing: client-supplied handles

Events reference their target through a **local handle** — a client-chosen label, file-scoped,
namespaced away from real IDs. A creating op (`create`, `add-story`/`add-subtask`/`add-finding`)
may carry `"handle": "<label>"`; the importer records `handle → allocated-id` (and, for
sub-entities, `handle → (parent-id, local-id)`) as it applies. Any later event's `target`/`to`/
`parent` resolves against the handle map first, then falls back to a literal existing ID. This is
what lets a `create` and a later `comment`/`status`/`ref` on the same new item compose within one
file without the client predicting the number the counter will hand out. Handles also unify item
and sub-entity addressing — a story created with a handle is addressable by that handle in a later
`sub-status`/`comment`, so the client never has to predict `US`/`ST`/`F` local numbers either.

### ID allocation

Import **always allocates fresh IDs from the single global counter**, inside the one import
transaction, via the same `db.allocate_id` every interactive `create` uses. IDs written into the
file (if any) are ignored for allocation; cross-references travel by handle, never by a predicted
number. This keeps the counter monotonic and globally unique (an imported file cannot dictate or
collide with the counter) and keeps allocation where the invariant requires it — inside a
transaction. Preserving a *source* project's original IDs (migrating between squads instances) is
a distinct, harder problem and is out of scope here.

### The v1 op set

Every op carries the common `op`/`at`/`as` fields above; per-op fields:

- **`create`** — `type`, `title`; optional `description`, `parent`, `labels`, `refs`
  (`["ID-or-handle", "ID-or-handle:kind"]`), `assignee`, badge fields (`priority`, `severity`, …),
  `status` (initial-status override), `slug`, `body`, `handle`. Allocates a fresh ID.
- **`status`** — `target`, `status`; optional `force`. Transition-checked against the type's
  workflow (same gate as the interactive verb).
- **`body`** — `target`, `body` (markdown); optional `append`. Marker-safe.
- **`comment`** — `target`, `messages` (list) or `message`; optional sub-entity selector
  (`story`/`subtask`/`finding`, or the generic `sub: [kind, local-or-handle]`). `as` is the author.
- **`ref`** — `target` (source), `to` (target ID/handle), `kind` (one of the valid ref kinds).
  Forward edge only; a later `"remove": true` variant is possible but a `create`-time `refs` list
  covers the migration path.
- **`add-story` / `add-subtask` / `add-finding`** — `target` (the parent feature/task/review
  ID/handle), `title`; optional `assignee`, `status`, `body`, `handle`; `add-subtask` also takes
  `story` (map to a parent story by handle/local), `add-finding` also takes `severity`. These are
  ergonomic fronts over one generic form, **`add-sub`** with an explicit `kind`, which covers any
  project-declared custom sub-entity kind (maps to the service's `add_block`).
- **`sub-status`** — `target` (parent), `kind`, `local` (or a sub-handle), `status`; optional
  `force`.
- **`sub-body`** — `target`, `kind`, `local`/handle, `body`; optional `append`. Marker-safe.
- **`assign`** — `target` (item, or a sub via `kind`+`local`), `assignee`.
- **`update`** — the general metadata escape hatch: `target` plus any of
  `title`/`description`/`assignee`/`priority`/`labels` (add/remove)/`parent`/`status`/badge
  set-unset. `assign`/`status`/`body` are named conveniences over the hot-path subset of this.

Sub-entity **prose** (`body`/comment) is marker-owned in the parent body; sub-entity **state**
(status/assignee/severity/story mapping) is frontmatter — the ops above mutate exactly those
seams, never a hand-authored body region directly.

### Atomicity, validation, idempotency

**Validate-first, then apply.** A pre-pass resolves handles, simulates ID allocation, and checks
every event — type/status vocabulary, transition legality, parent eligibility, ref kinds, actor
registration, marker-safety of every prose field — against the active spec, writing nothing and
collecting *all* errors (not just the first) before reporting. `--dry-run` stops exactly here and
prints the projected `handle → id` plan and per-op counts. Only a fully clean pre-pass proceeds to
apply.

**Apply is one index transaction.** The apply pass runs inside a single `IndexStore.transaction()`:
it mutates the loaded `db` in memory, allocates IDs from its counter, and writes each item's `.md`
through the marker-safe section/frontmatter helpers, committing the index once at the end. Because
the pre-pass already caught every logical/authoring error, an apply-time failure can only be I/O.
The safe-failure direction is preserved (files-then-index, as elsewhere): if the process dies
mid-flush, the index simply isn't committed and `sq repair` reconciles the index to whatever files
exist. Net contract: **all-or-nothing for the common (validation) failures — nothing is written
unless the whole file validates; crash-safe-and-repairable for I/O failures.**

Every applied event still emits its reflog op (`create`/`status`/`comment`/`ref`/…) with the
event's own actor/session, so the imported history is captured in the reflog exactly as
interactive work is.

**Idempotency is not automatic in v1.** Re-running a file allocates fresh IDs and duplicates its
items — handle addressing makes a file internally self-consistent, not self-deduplicating.
`--dry-run` is the guard against an accidental second run. Deterministic, resumable re-import
(honoring a client `key`/`import_id` for dedup/resume) needs durable applied-import state; the
index cannot hold it (it must stay rebuildable from the `.md` files, invariant #1), so it is
deferred to a later revision and flagged below as carrying a schema implication.

**Interaction with `sq check`.** Import does not bypass the catalog gate: every created/updated
item passes the same `ValidatorEngine.gate()` the interactive commands run, so a clean import
leaves `sq check` clean. Board-debt conditions `sq check` reports (unwritten sub-entity bodies,
over-long finding/story titles) surface as import warnings so a migration does not silently import
debt.

### CLI surface

`sq import <file>` (top-level; `-` reads JSONL from stdin). Flags:

- `--dry-run` — run the validate pre-pass only; write nothing; print the `handle → id` plan and
  per-op counts.
- `--json` — structured result: per-op counts, the resolved `handle → id` map, and the ordered
  error list on failure.
- `--at` / `--as` — supply the file-level defaults events inherit when they omit their own.
- `--dir` — the usual squad selector.

On any validation error: exit non-zero, write nothing, list every error with its line number.

### Invariants honored

- **Frontmatter is the source of truth** — import writes `.md` files; the index is the derived
  commit and is `repair`-rebuildable from them.
- **Marker-safe edits only** — every body/comment field goes through the section helpers and the
  marker-rejection guard; no agent-authored region is rewritten wholesale.
- **One global counter** — fresh IDs from `db.allocate_id` inside the single transaction; the file
  never dictates the counter.
- **Forward edges only** — the `ref` op and `create.refs` write outgoing edges; backrefs stay
  computed by inversion.

### Scope

**v1:** the op set above; JSONL; file-order application; per-event `at`/`as`; validate-first with
`--dry-run`; fresh-ID allocation with handle addressing; single-transaction apply with the
all-or-nothing-for-validation contract; `--json`.

**Deferred:** idempotent/resumable re-import via client keys (carries a schema implication — see
below); preserving a source squad's original IDs; delete/`rm` ops (deliberately excluded — bulk
deletion by file is high-risk and out of the migration use case); reordering by `at`; a companion
`sq export` that emits a JSONL stream from an existing squad (the natural round-trip, worth its own
scoping); streaming apply for files beyond in-memory scale (v1 buffers, which is ample for the
thousands-of-events corpus this targets).

### Schema and migration

This is additive — a new command and a new *input* file format. It does **not** change
`SCHEMA_VERSION` or the `.squads.json` shape, so it needs no migration. The one deferred item that
*would* carry a schema implication is durable applied-import state for idempotent re-import; that
is not assumed here and must be decided explicitly if and when idempotency is taken up.

### Implementation note (for scoping, not contract)

The interactive service methods each open their own `transaction()`, so they cannot be called
inside the import's single open transaction (the lock is not reentrant). The clean shape is to
factor each op's mutation core into a `db`-taking apply-helper that both the existing single-op
method and the import loop call — keeping one code path per mutation rather than a parallel
importer that could drift from the interactive behavior.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-23T07:56:55Z] Robert Architect:
  - Adjacent adoption recommendations from the same field report (for tech-lead scoping — kept here, not spun into separate ADRs).
  - F8 (init/adopt into a pre-existing non-squads project): don't design a new ADR — scope a detect-and-warn enhancement to init/adopt. (a) When the target CLAUDE.md exists with no squads markers but real content, still insert the managed region but emit a prominent warning naming the file: the hand-written operating model may contradict the managed block and needs manual reconciliation; consider placing the managed region at the TOP so authoritative instructions lead. Never auto-delete hand-written prose. (b) Scan .claude/agents (and skills) for pointer files squads did NOT generate this run (no managed marker / not in roster) and list them as candidate orphans with exact paths — warn only, no auto-delete (a backend nuking files it doesn't own crosses the ownership boundary and risks real user content). Add a documented 'adopting into an existing CLAUDE.md/.claude' runbook. Only the managed-block-placement rule (top vs bottom) is contract-worthy enough to consider an ADR line; the rest is a scoped task.
  - F7 (bundled designer/ux role vs dev add for non-code specialties): recommend loosening 'dev add' over bundling a role. FEAT-543 already ships custom non-dev role scaffolding via .overrides/roles, so the capability exists — the friction is being forced to hand-write a .toml override. Add 'sq dev add --tech ux --kind design' (a --kind/non-code path) that scaffolds the same role through the ergonomic verb without asserting a coding stack. Do NOT bundle a designer/ux role: the bundled set is a deliberately small canonical core, and bundling one specialty invites bundling every one (data/SRE/security/…); spec-driven customization (EPIC-538) plus FEAT-543 is the sanctioned extension path. Optionally ship a documented ux example in docs rather than an always-on role.
<!-- sq:discussion:end -->
