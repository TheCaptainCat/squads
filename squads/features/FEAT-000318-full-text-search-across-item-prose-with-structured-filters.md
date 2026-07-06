---
id: FEAT-318
sequence_id: 318
type: feature
title: Full-text search across item prose, with structured filters
status: Draft
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
updated_at: '2026-07-07T07:16:52Z'
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

## User & moment

Deliberate and need-driven: **repo management and steering** — auditing, scoping future work, hunting
a stale decision. Not a routine step and not a boot ritual; you reach for it *because* you're managing
the repo.

## Shape

- `sq search "<query>"` scans the prose: item **bodies, discussion comments, sub-entity prose, and
  titles**.
- Composes with the structured filters we already have: `--type`, `--status`
  (e.g. `sq search "counter" --type decision --status Accepted`).
- Results show **where** it matched and with **what authority**: item id + type + status, the region
  (body / which discussion comment / which sub-entity), and a snippet with the match in context.
- A `--json` surface for agent consumption alongside the human-readable table.
- **Discovery only** — it locates buried/stale prose; superseding or fixing it is a separate act.

## Implementation note (not an ADR)

Content search reads the on-disk `.md` files — the `.squads.json` index carries only structured
fields, so it can't answer prose queries — as a plain scan, with **no new search index**. If scale
ever makes the scan too slow, an indexing decision can be raised as an ADR then; it isn't needed now.

## Skill

Guidance lives in the **`squads` skill** (a "finding things across the board" section), not a new
skill — search is a query verb, not a workflow. One line frames the moment: reach for it when
managing/scoping the repo, not as a routine step.
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
- `sq search "<query>"` matches across item bodies, discussion comments, sub-entity prose, and titles.
- Case-insensitive by default; the matching semantics (substring/keyword vs regex) are documented, with a stated default.
- No match yields a clean "no results" message and exit 0.
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

**Acceptance**
- Each result shows item id + type + status, and the region where it matched (body / a specific discussion comment / a named sub-entity).
- A snippet shows the matched text in context.
- Output is escaped for the console (Rich markup safety, per repo convention).
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
- `--type` and `--status` compose with the free-text query.
- e.g. `sq search "counter" --type decision --status Accepted` returns only matches in accepted ADRs.
- Text query and filters combine with AND semantics (documented).
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
- `--json` emits structured results (item id/type/status, matched region, snippet, locations) with NO ANSI.
- The JSON shape is stable and documented.
- Consistent with the repo's existing `--json` surfaces.
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

**Acceptance**
- The `squads` skill gains a "finding things across the board" section documenting `sq search`, its filters, and its output.
- It frames the moment: reach for it when managing/scoping the repo (hunting a prior decision, checking staleness), not as a routine boot step.
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
