---
id: FEAT-318
sequence_id: 318
type: feature
title: 'Enrich sq search: --status, region/authority, richer --json'
status: InProgress
parent: EPIC-38
author: product-owner
subentities:
- local_id: US1
  title: As a steering user, I can search item prose by free text so I can find buried
    context
  status: Todo
- local_id: US2
  title: As a steering user, results show where each match is and its authority so
    I can judge relevance
  status: Todo
- local_id: US3
  title: As a steering user, I can narrow the search with structured filters so I
    can audit a slice
  status: Todo
- local_id: US4
  title: As an agent, I can get search results as JSON so a session can act on them
    programmatically
  status: Todo
- local_id: US5
  title: As an agent, the squads skill teaches when to reach for search so it's used
    for steering not as a ritual
  status: Todo
created_at: '2026-07-07T07:15:49Z'
updated_at: '2026-07-15T13:54:49Z'
---
<!-- sq:body -->
# Search the board

A flashlight for whoever's steering the repo — a full-text search across the prose the structured
index can't reach, so a manager/PO (or a session doing that work) can find something buried: a prior
decision, a discussion that's gone stale, everywhere a topic was touched.

## Why

`sq list` / `tree` / `inbox` already answer *structured* questions — type, status, assignee. What they
can't answer is the *prose* question: "where have we discussed the global counter, and is any of it
obsolete now?" A decision goes stale silently — frontmatter still reads `Accepted` while a later ADR
quietly contradicts it; only the prose reveals the tension. Search is how you hunt that down instead
of stumbling onto it.

## Scope note

`sq search "<query>"` already exists and ships most of what this feature originally called for. This
is now an **enrichment** of that command, not a build from scratch — the acceptance below is written
against the delta only. Anything already provided is called out explicitly so it isn't re-implemented.

## Already provided (verify, keep, don't rebuild)

- The `search` verb itself, with `--json`, case-insensitive matching, a clean "no results" message at
  exit 0.
- `--type` filter, composable with the query.
- Coverage of item **titles, bodies, discussion comments, and sub-entity prose** — the scan reads the
  whole post-frontmatter file, so story/subtask/finding blocks and discussion are already in scope
  (confirmed against `CollabMixin.search`, which strips only the frontmatter before scanning).

## The delta (new work this feature covers)

- **`--status` filter**, composing with `--type` and the query as AND (`list_items` already accepts
  `status=`, so this threads an existing filter dimension into `search`, not a new one).
- **Result authority/region.** Today a result is just `{id, title, hits[]}` — raw matching lines, no
  indication of *where* a line came from. Extend results so each hit carries the item's type and
  status plus the region it matched (body / a specific discussion comment / a named sub-entity), and
  an in-context snippet around the match.
- **Richer `--json` shape** — a superset of today's `{id, title, hits}` adding type, status, and
  per-hit region + snippet/location, documented and stable, consistent with the repo's other `--json`
  surfaces.
- **`squads` skill section** — a "finding things across the board" section documenting `sq search`,
  its filters, and its output; no new skill (search is a query verb, not a workflow).

## Implementation note (not an ADR)

Content search reads the on-disk `.md` files — the `.squads.json` index carries only structured
fields, so it can't answer prose queries — as a plain scan, with **no new search index**. If scale
ever makes the scan too slow, an indexing decision can be raised as an ADR then; it isn't needed now.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 318 add-story "As a <role>, I want … so that …"`; track with `sq feature 318 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a steering user, I can search item prose by free text so I can find buried context |
| US2 | Todo |  | As a steering user, results show where each match is and its authority so I can judge relevance |
| US3 | Todo |  | As a steering user, I can narrow the search with structured filters so I can audit a slice |
| US4 | Todo |  | As an agent, I can get search results as JSON so a session can act on them programmatically |
| US5 | Todo |  | As an agent, the squads skill teaches when to reach for search so it's used for steering not as a ritual |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a steering user, I can search item prose by free text so I can find buried context

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a steering user, I want to search item prose by free text so I can find context buried on the board.

**Acceptance**
- Already shipped, verify and keep: `sq search "<query>"` matches across item titles, bodies,
  discussion comments, and sub-entity prose (confirmed — the scan reads the whole post-frontmatter
  file, so story/subtask/finding blocks and discussion are already covered, not scoped separately).
- Already shipped, verify and keep: case-insensitive substring match; a clean "no results" message at
  exit 0 when nothing matches.
- No new work required for this story; re-verify against the acceptance above rather than
  re-implementing.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a steering user, results show where each match is and its authority so I can judge relevance

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a steering user, I want each result to show where the match is and its authority so I can judge relevance at a glance.

**Acceptance (new work — today's result is just `{id, title, hits[]}`, raw matching lines)**
- Each result carries the item's id + type + status (today: id + title only; status appears in the
  human table but not the type, and neither appears in `--json`).
- Each hit carries the region it matched: body / a specific discussion comment / a named sub-entity
  (e.g. `story:S1`) — not just the raw source line with no origin.
- Each hit carries an in-context snippet (the match with surrounding text), not the bare line.
- Console output stays escaped for Rich markup safety (already true today — keep it that way).
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As a steering user, I can narrow the search with structured filters so I can audit a slice

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As a steering user, I want to narrow the search with the structured filters I already know so I can audit a slice of the board.

**Acceptance**
- Already shipped, verify and keep: `--type` composes with the free-text query.
- New work: a `--status` filter composes with `--type` and the query, AND semantics
  (e.g. `sq search "counter" --type decision --status Accepted` returns only matches in accepted
  ADRs). `list_items` already accepts a `status=` filter dimension — this threads it into `search`,
  it is not a new filtering mechanism.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — As an agent, I can get search results as JSON so a session can act on them programmatically

<!-- sq:story:US4:head -->
**Status:** ⚪ Todo
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
As an agent, I want search results as JSON so a session can act on them programmatically.

**Acceptance**
- Already shipped, verify and keep: `--json` emits structured results with no ANSI.
- New work: a richer, superset shape — today's `{id, title, hits}` grows to also carry type, status,
  and per-hit region + snippet/location — documented and stable, consistent with the repo's other
  `--json` surfaces.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — As an agent, the squads skill teaches when to reach for search so it's used for steering not as a ritual

<!-- sq:story:US5:head -->
**Status:** ⚪ Todo
<!-- sq:story:US5:head:end -->

<!-- sq:story:US5:body -->
As an agent, I want the squads skill to teach when to reach for search so it is used for steering, not as a ritual.

**Acceptance (new work — no existing skill content covers this)**
- The `squads` skill gains a "finding things across the board" section documenting `sq search`, its
  filters (`--type`, `--status`), and its output (including the region/authority metadata from US2).
- It frames the moment: reach for it when managing/scoping the repo (hunting a prior decision,
  checking staleness), not as a routine boot step.
- No new skill is created (search is a query verb, not a workflow).
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
