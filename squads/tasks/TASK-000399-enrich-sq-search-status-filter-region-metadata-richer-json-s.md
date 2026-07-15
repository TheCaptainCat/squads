---
id: TASK-399
sequence_id: 399
type: task
title: 'Enrich sq search: --status filter, region metadata, richer --json, skill section'
status: InReview
parent: FEAT-318
author: tech-lead
assignee: python-dev
subentities:
- local_id: ST1
  title: Add --status filter, AND-composed with query and --type
  status: Done
  story: US3
- local_id: ST2
  title: Return region/authority + snippet per hit; item type/status per result; console
    escaped
  status: Done
  story: US2
- local_id: ST3
  title: Richer --json superset shape (type/status/region/snippet/location), documented
    + stable
  status: Done
  story: US4
- local_id: ST4
  title: 'squads skill: finding things across the board section'
  status: Done
  story: US5
created_at: '2026-07-15T14:02:32Z'
updated_at: '2026-07-15T14:34:53Z'
---
<!-- sq:body -->
# Enrich `sq search`

The full-text scan already ships in `CollabMixin.search` (`src/squads/_services/_collab.py`) and the `search` CLI (`src/squads/_cli/_main.py`): it reads each item's whole post-frontmatter file, so titles, bodies, discussion comments, and sub-entity prose (story/subtask/finding blocks) are all already in scope, alongside `--type` and `--json`. This task is the enrichment delta on top of that; the shipped parts are verify-and-keep, not rebuild.

## Verify-and-keep (do not re-implement)

- Prose scan across titles/bodies/discussion/sub-entity blocks (whole-file scan, frontmatter stripped).
- Case-insensitive substring match; clean "no results" message at exit 0.
- `--type` filter composing with the query.
- The `--json` flag itself.

Add a targeted test if coverage is thin, but do not rework these.

## Delta to build

1. `--status` filter on `sq search`, AND-composed with the query and `--type`. `list_items` already accepts a `status=` filter dimension, so this threads an existing dimension into `search` — not a new mechanism. Reuse the same status parsing/validation the sibling `list`/`tree` commands use for their `--status` option.

2. Region/authority metadata + snippet in results. Today a result is `{id, title, hits[]}` — raw matching lines with no origin. Each result should carry the item's type and status; each hit should carry the region it matched (body / a specific discussion comment / a named sub-entity such as `story:S1`) and an in-context snippet around the match rather than the bare stripped line. This means the service returns a richer structured result instead of `list[tuple[Item, list[str]]]` — the whole-file scan needs to attribute each matched line to a region as it scans. Console output stays escaped through `e()` for Rich markup safety (as today).

3. Richer `--json` shape: a documented, stable superset of `{id, title, hits}` that adds type, status, and per-hit region + snippet/location. Keep it consistent with the other `--json` surfaces in `_main.py` (e.g. the `graph`/`tree` docstring-documented shapes) — document the shape in the command docstring.

4. `squads` skill gains a "finding things across the board" section documenting `sq search`, its filters (`--type`, `--status`), and its output including the region metadata. No new skill — search is a query verb, not a workflow. Frame the moment: reach for it when steering/scoping the repo (hunting a prior decision, checking staleness), not as a routine boot step.

## Tests

Service-level test for the structured result (region attribution + `--status` AND semantics) and a CLI smoke test for the human table and the `--json` shape. Name tests by behavior. Keep everything in the temp-dir fixtures.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 399 add-subtask "<title>"`; track with `sq task 399 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Add --status filter, AND-composed with query and --type | US3 |
| ST2 | Done |  | Return region/authority + snippet per hit; item type/status per result; console escaped | US2 |
| ST3 | Done |  | Richer --json superset shape (type/status/region/snippet/location), documented + stable | US4 |
| ST4 | Done |  | squads skill: finding things across the board section | US5 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add --status filter, AND-composed with query and --type

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US3 — As a steering user, I can narrow the search with structured filters so I can audit a slice
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Thread `list_items`'s existing `status=` dimension into search; AND with query and `--type`. Reuse the status parsing the `list`/`tree` commands use.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Return region/authority + snippet per hit; item type/status per result; console escaped

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — As a steering user, results show where each match is and its authority so I can judge relevance
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Change the service to return structured hits: each result carries item type + status, each hit carries its region (body / a specific discussion comment / a named sub-entity) and an in-context snippet. Attribute region during the whole-file scan. Console rendering stays escaped via `e()`.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Richer --json superset shape (type/status/region/snippet/location), documented + stable

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US4 — As an agent, I can get search results as JSON so a session can act on them programmatically
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Grow `--json` to a documented, stable superset of `{id,title,hits}` adding type/status and per-hit region + snippet/location. Match the shape/doc style of the other `--json` surfaces; document it in the command docstring.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — squads skill: finding things across the board section

<!-- sq:subtask:ST4:head -->
**Status:** 🟢 Done
**Implements:** US5 — As an agent, the squads skill teaches when to reach for search so it's used for steering not as a ritual
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
Add a 'finding things across the board' section to the squads skill: `sq search`, its `--type`/`--status` filters, and its output incl. region metadata. Frame it as a steering/scoping move, not a boot ritual. No new skill.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-15T14:05:33Z] Catherine Manager:
  - Dispatching @python-dev for TASK-399 + TASK-400 + TASK-401 in one coordinated pass (they share the template/manifest surface). Take each Ready→InProgress→InReview.
- [2026-07-15T14:30:34Z] Elias Python:
  - Added --status filter (AND with query/--type, reuses parse_status), region+snippet attribution per hit (title/description/body/discussion#n/<kind>:<local_id>/<kind>:<local_id>:discussion#n), richer --json (type/status/region/location/snippet), squads skill 'Finding things across the board' section.
  - Service: CollabMixin.search now returns list[SearchResult] (SearchHit: region/location/snippet) in _services/_collab.py + _results.py; region attribution via marker line-ranges (_sections.region_lines), no set-iteration nondeterminism.
  - Tests: tests/service/test_search_and_workload_views.py (status AND-filter, region attribution, type/status on result), tests/cli/test_blocked_workload_search_cli.py (--status CLI, --json shape). Golden churn: tests/goldens/search_login.json regenerated (additive: type/status/hits[].location+region+snippet).
- [2026-07-15T14:34:53Z] Elias Python:
  - Fixed a missed consumer of the old search tuple shape: tests/service/test_terminal_status_reopen_and_unblock.py used [i.id for i, _ in ...] — updated to r.item.id. Grepped tests/+src/ for other .search( call sites: only re.search (unrelated) and memory_store.search (different function) remain; no other consumers of the old shape.
<!-- sq:discussion:end -->
