---
id: FEAT-317
sequence_id: 317
type: feature
title: Team bulletin board — broadcast notices with expiry
status: InProgress
parent: EPIC-316
author: product-owner
refs:
- ADR-314:implements
subentities:
- local_id: US1
  title: As a lead or operator, I can post a notice to the board with an optional
    expiry so the team sees it
  status: Todo
- local_id: US2
  title: As any agent, current board notices are surfaced at the start of a run so
    I'm aware of standing notices
  status: Todo
- local_id: US3
  title: As anyone, I can list current notices to see what's active
  status: Todo
- local_id: US4
  title: As a lead or operator, I can clear a notice that no longer applies
  status: Todo
- local_id: US5
  title: As an agent, a guiding skill teaches board posting discipline and the memory-vs-board
    boundary
  status: Todo
created_at: '2026-07-06T16:08:53Z'
updated_at: '2026-07-15T11:04:55Z'
---
<!-- sq:body -->
# Team bulletin board

A team-scoped, everyone-reads broadcast surface for short, *prescriptive* notices — "what we all need
to know right now" — that a human or lead posts and that usually come down on their own via an
expiry. Cross-cutting facts (a repo-wide convention, a temporary freeze, "read this before touching
X") live here **once**, rather than duplicated into every role's memory.

## Why

It's the complement to agent memory. Memory holds what a single agent *learned* (descriptive,
per-role); the board holds what the *whole team* needs to be aware of *right now* (prescriptive,
shared, time-bound). The dividing line: **personal-learned → memory; cross-cutting/announcement →
board.**

## Shape

- **Storage** is fixed by the accompanying decision: its own lighter store under `squads/board/`, one
  file per notice with a short-hash id plus author / posted-at / optional `until` / body — off the
  global counter and outside `.squads.json`. `squads/board/` also carries a generated `.index.jsonl`
  roll-up (same format as memory: one line per notice, entry schema `{slug, filename, description}`,
  `slug` here being the notice's stable hash id).
- **Expiry does real work.** Expired notices are filtered out at read time (listing and boot
  surfacing); physical removal only happens on an explicit `clear`, never as a side effect of a read.
- **Boot surfacing.** Unlike memory (index-only, content-on-recall), the board's notices are short
  and prescriptive, so they can be surfaced *content and all* at boot — with `--until` keeping that
  boot payload bounded, not just tidy.
- **Command surface:**

  ```
  sq board post -m "<notice>" [--until 2026-07-10]   # post
  sq board list                                       # current (unexpired) notices
  sq board clear <n>                                  # take one down
  ```

  `clear <n>` is an ephemeral positional ordinal that is the n-th **entry line** of the generated
  `squads/board/.index.jsonl` (header line excluded), resolved against the current sorted, unexpired
  listing to the notice's stable hash id — the ordinal is a display affordance derived from the
  generated index, not persisted meaning.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 317 add-story "As a <role>, I want … so that …"`; track with `sq feature 317 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a lead or operator, I can post a notice to the board with an optional expiry so the team sees it |
| US2 | Todo |  | As any agent, current board notices are surfaced at the start of a run so I'm aware of standing notices |
| US3 | Todo |  | As anyone, I can list current notices to see what's active |
| US4 | Todo |  | As a lead or operator, I can clear a notice that no longer applies |
| US5 | Todo |  | As an agent, a guiding skill teaches board posting discipline and the memory-vs-board boundary |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a lead or operator, I can post a notice to the board with an optional expiry so the team sees it

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a lead or operator, I want to post a notice to the board with an optional expiry so the whole team sees it.

**Acceptance**
- `sq board post -m "<text>"` creates a notice file under `squads/board/` with a short-hash id plus author, posted-at, and body; NO global-counter id.
- `--until <date>` records an expiry.
- The post is attributable to its author (operator via `--as op-<slug>` / agent role).
- Two notices posted on separate branches get distinct hash ids and the notice files merge cleanly, but the committed `board/.index.jsonl` conflicts on the distinct posts — resolved mechanically by re-running `sq sync`/`repair` to regenerate it.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As any agent, current board notices are surfaced at the start of a run so I'm aware of standing notices

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As any agent, I want current board notices surfaced at the start of a run so I am aware of standing team notices.

**Acceptance**
- At boot, unexpired notices are surfaced into the agent's context through the active backend — content and all (they are short and prescriptive), not just an index.
- Expired notices are excluded from boot surfacing.
- An empty or all-expired board surfaces nothing.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As anyone, I can list current notices to see what's active

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As anyone on the team, I want to list current notices so I can see what is active.

**Acceptance**
- `sq board list` shows unexpired notices with an ephemeral positional ordinal, author, posted-at, and expiry (if set).
- The ordinal is the notice's entry-line position in the generated `squads/board/.index.jsonl` (header line excluded; entry line n = ordinal n).
- Expired notices are filtered out at read time (excluded from the index and the listing).
- Listing never mutates git-tracked files (no spurious diffs).
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — As a lead or operator, I can clear a notice that no longer applies

<!-- sq:story:US4:head -->
**Status:** ⚪ Todo
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
As a lead or operator, I want to clear a notice that no longer applies so the board stays current.

**Acceptance**
- `sq board clear <n>` resolves `<n>` as the n-th entry line of the generated `squads/board/.index.jsonl` (header line excluded) to that notice's stable hash id, and removes its file.
- Resolution is against the live index at the moment `clear` runs (documented behaviour); an out-of-range ordinal errors cleanly.
- Removal is a real git file deletion, never a side effect of a read.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — As an agent, a guiding skill teaches board posting discipline and the memory-vs-board boundary

<!-- sq:story:US5:head -->
**Status:** ⚪ Todo
<!-- sq:story:US5:head:end -->

<!-- sq:story:US5:body -->
As an agent, I want a guiding skill to teach board posting discipline and the memory-vs-board boundary so notices stay useful and land in the right place.

**Acceptance**
- A managed skill documents: keep notices short and prescriptive; set `--until` so they come down; clear when stale.
- It states the boundary: cross-cutting/announcement -> board; personal-learned -> memory.
- Whether this is its own `sq-board` skill or folded into the shared knowledge skill is left to implementation.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-13T09:10:34Z] Nina Product:
  - Aligned to ADR-314's accepted design: board also has a generated .index.jsonl roll-up under squads/board/; clear <n> ordinal is now concrete = n-th entry line (header excluded). Shape + US3/US4 updated.
- [2026-07-15T09:29:39Z] Operator:
  - Realigned US1 acceptance to ADR-314's option-B amendment (REV-388): notice files merge cleanly; committed board/.index.jsonl conflicts on distinct posts, resolved by re-running sq sync/repair.
- [2026-07-15T09:29:59Z] Nina Product:
  - Re-post with correct attribution — see above: realigned US1 acceptance to ADR-314's option-B amendment (REV-388).
- [2026-07-15T11:04:55Z] Paul Reviewer:
  - Feature-level review done (REV-391, Approved). Reviewed board-specific code only (shared _content_index generator was already vetted via REV-388/BUG-390).
  - APPROVE. All of US1-US5 hold: post writes a hash-named marker-free .md + regenerates the index off the global counter (US1); unexpired notices surface content-and-all through both backends' ## Board section, empty/all-expired → nothing (US2); list shows the ephemeral ordinal read-only (US3); clear resolves the n-th live-listing entry to the stable hash and does a real file delete (US4); the sq-memory skill teaches the board discipline + memory-vs-board boundary (US5).
  - Correctness confirmed on the flagged risk areas: (a) id stability — the id is the filename stem (authoritative), never recomputed on regen, so it is stable across sync/repair/merge; distinct notices need a 40-bit hash collision to clash and even then _unique_id appends -2 with no clobber; same-second/author/body double-post → -2 (verified manually). (b) ordinal contract — list, regenerate_index and clear all derive from the same list_notices() (sorted (posted_at,id), expiry-filtered), so the display ordinal == the index entry-line position (header excluded); clear recomputes the listing directly rather than trusting the on-disk index, so it is self-consistent even mid-conflict. (c) expiry is a read-time filter only (never mutates on read; until<=now boundary; tz-aware both sides via the clock). (d) option-B merge genuinely holds — the git integration test proves .md files merge, the index conflicts (AA), and sq sync regenerates it in chronological order.
  - Gates clean: ruff + pyright(strict) + format on the board modules, sq check, and all 44 board tests (service/CLI/git-merge/backend-contract) pass. No ticket refs in source, no stray content tags, content files marker-free.
  - Two low-severity non-blocking follow-ups recorded as REV-391 findings (not gating): F1 board notice frontmatter stores a redundant 'id' that is derivable from the filename stem and never read back (memory omits its slug for exactly this reason); F2 the _unique_id anti-clobber path has no automated test though the memory analogue does. @tech-lead / @python-dev can pick these up as cleanup whenever convenient.
<!-- sq:discussion:end -->
