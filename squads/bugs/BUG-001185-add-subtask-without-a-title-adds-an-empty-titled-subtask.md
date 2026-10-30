---
id: BUG-1185
sequence_id: 1185
type: bug
title: add-subtask without a title adds an empty-titled subtask
status: Verified
author: qa
refs:
- FEAT-1173
- MILE-1241:targets
created_at: '2026-10-27T23:37:32Z'
updated_at: '2026-10-29T20:40:06Z'
priority: low
severity: medium
---
<!-- sq:body -->
Found while writing the CLI surface tests (FEAT-1173). Reproduced on the release/0.17 dev tree.

## Command
`sq task 21 add-subtask` (no TITLE argument)

## Observed
```
added ST1 to TASK-21
  set its body:  sq task 21 subtask ST1 body -m "…"  (or --file body.md / --file -)
```
Exit code 0. `sq task 21 show --full` then lists `ST1  Todo  <empty title>`.

## Expected
Typer should refuse the missing required argument (exit 2), or the service should refuse an empty title, as it does for other required text. A subtask with an empty title is unusable in listings.

## Severity
medium
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T16:31:59Z] `tech-lead` Olivia Lead:
  - Planned as TASK-1246 ST3, but this needs a product call before any code. A sub-entity title is optional by documented design: the add-<kind> help says "Optional short title", subentity_title in _services/_base.py stores a blank title as none on purpose, and docs/adoption.md says a sub-entity title is optional. @product-owner decide: WontFix citing that rule, or make the title required on every path (add, import, update) with docs and help changed.
- [2026-10-29T16:42:42Z] `op-pierre` Pierre Chat:
  - 2026-10-29: a sub-entity title becomes required on every path (add, import, update): refuse a missing or blank title, and change the help and docs/adoption.md to match. Adopter-visible, so it gets a changelog line.
- [2026-10-29T20:40:06Z] `reviewer` Paul Reviewer:
  - Verified under REV-1247 (Approved at a56413b4).
<!-- sq:discussion:end -->
