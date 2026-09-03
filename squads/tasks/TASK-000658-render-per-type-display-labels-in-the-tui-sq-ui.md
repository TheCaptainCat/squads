---
id: TASK-658
sequence_id: 658
type: task
title: Render per-type display labels in the TUI (sq ui)
status: Done
parent: FEAT-647
author: tech-lead
refs:
- ADR-646:addresses
subentities:
- local_id: ST1
  title: Filter dropdown + any other TUI type-display via label_for
  status: Done
  story: US4
created_at: '2026-07-27T07:51:30Z'
updated_at: '2026-07-27T08:05:03Z'
---
<!-- sq:body -->
Route every user-visible item-type name in the terminal TUI (`sq ui`) through the display-label resolver `label_for(type, form, spec)`, so the TUI matches the labelling the VS Code client already applies.

## Known site
`src/squads/_tui/_filter.py` builds the filter-by-type dropdown as `[(t, t) for t in sorted(spec.non_roster_types())]` — the shown label is the raw lowercase type. Route the display through the resolver while keeping `t` as the option **value** (filtering keys on the raw type):

```python
[(label_for(t, "singular", spec), t) for t in sorted(spec.non_roster_types())]
```

## Sweep
Grep the whole `src/squads/_tui/` tree for any OTHER place that shows a raw item-type name to the user — reader/detail panel, search results, status bar, column headers — and route each real one through `label_for` with the appropriate form (singular/plural). Do not assume a site exists without confirming it in the code.

## Tests
Add a service/TUI-level test asserting the filter options render the **resolved** label while the option value stays the raw type: a type with a pinned/overridden label shows that label, a bundled type shows its derived label.

## Scope
Python, terminal text only. No schema bump. No operator visual gate needed — behaviour is verifiable in tests, so the task follows the normal reviewed path (InReview → Done).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 658 add-subtask "<title>"`; track with `sq task 658 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Filter dropdown + any other TUI type-display via label_for

<!-- sq:subtask:ST1:body -->
Routed the filter dropdown, search-type dropdown, and search-hit type badge through label_for; added TUI tests.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-27T07:58:03Z] Elias Python:
  - Routed _tui/_filter.py's type-filter dropdown, _tui/_search.py's search-type dropdown, and the search hit row's ($type) badge through label_for(singular). Reader/tree/status-bar have no raw-type display (checked, none found). Tests added in tests/tui/test_filter_screen.py and tests/tui/test_search_screen.py; pyright/ruff clean; tests/tui green (47 passed).
<!-- sq:discussion:end -->
