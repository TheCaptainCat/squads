---
id: BUG-999
sequence_id: 999
type: bug
title: sq import orders one item's warnings differently than 0.15.0
status: Open
author: qa
priority: low
refs:
- FEAT-899
- MILE-1051:targets
created_at: '2026-10-12T05:33:56Z'
updated_at: '2026-10-16T12:24:10Z'
---
<!-- sq:body -->
## Reproduction

A scratch squad whose workflow override selects `no_status_banner` and `subentity_title_max:120` on feature, task and bug (the selection this repository carries). The title lines below are 121 `q` characters, shortened here.

Events (`imp.jsonl`):

```
{"op": "create", "type": "feature", "title": "Imp F", "handle": "f1", "as": "product-owner", "body": "## Status\n\nx"}
{"op": "add-story", "target": "f1", "title": "<121 x q>", "handle": "s1"}
{"op": "create", "type": "task", "title": "Imp T", "handle": "t1", "parent": "f1", "as": "tech-lead", "body": "STATUS: x"}
{"op": "add-subtask", "target": "t1", "title": "<121 x q>"}
{"op": "create", "type": "bug", "title": "Imp B", "as": "qa", "body": "STATUS: x"}
```

Run `sq import imp.jsonl` with the released 0.15.0 tool, then with the current build, each in its own fresh squad carrying the same override.

Per-item warnings, released tool:

```
warning: FEAT-21: body opens with a status/lifecycle banner — move state to frontmatter or a dated discussion comment
warning: FEAT-21: US1 body is unwritten (still the placeholder stub)
warning: FEAT-21: advisory: story US1 title is 121 chars (threshold: 120) — a sub-entity title is a one-line handle; put the detail in the body
warning: TASK-22: body opens with a status/lifecycle banner — move state to frontmatter or a dated discussion comment
warning: TASK-22: ST1 body is unwritten (still the placeholder stub)
warning: TASK-22: advisory: subtask ST1 title is 121 chars (threshold: 120) — a sub-entity title is a one-line handle; put the detail in the body
warning: BUG-23: body opens with a status/lifecycle banner — move state to frontmatter or a dated discussion comment
imported 5 event(s)
```

Per-item warnings, current build:

```
warning: FEAT-21: US1 body is unwritten (still the placeholder stub)
warning: FEAT-21: body opens with a status/lifecycle banner — move state to frontmatter or a dated discussion comment
warning: FEAT-21: advisory: story US1 title is 121 chars (threshold: 120) — a sub-entity title is a one-line handle; put the detail in the body
warning: TASK-22: ST1 body is unwritten (still the placeholder stub)
warning: TASK-22: body opens with a status/lifecycle banner — move state to frontmatter or a dated discussion comment
warning: TASK-22: advisory: subtask ST1 title is 121 chars (threshold: 120) — a sub-entity title is a one-line handle; put the detail in the body
warning: BUG-23: body opens with a status/lifecycle banner — move state to frontmatter or a dated discussion comment
imported 5 event(s)
```

## Expected versus actual

Expected: the warnings for an item appear in the order the released tool printed them (the banner warning before the unwritten-body warning).

Actual: for FEAT-21 and TASK-22 the unwritten-body warning is printed before the banner warning. The set of warnings is identical in both builds (the sorted outputs are equal); only the order differs.

## Cause and scope

The import warnings follow the type's effective validator list. `no_status_banner` used to sit in the always-on floor, so it ran first; as a selected name it now comes after the bundled members. `sq check` is unaffected because it sorts its findings. `sq import` is read by scripts, so the order is observable output.

Sorting the import warnings the way `sq check` sorts its findings would make the order independent of the validator list. The choice of fix is open.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
