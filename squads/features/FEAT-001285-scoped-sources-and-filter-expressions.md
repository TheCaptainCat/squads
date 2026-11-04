---
id: FEAT-1285
sequence_id: 1285
type: feature
title: Scoped sources and filter expressions
status: Done
parent: EPIC-1268
author: product-owner
refs:
- BUG-1284:implements
- ADR-1274
description: Sources name a scope; squads filters; links span a tracker's sources
subentities:
- local_id: US1
  title: Scope keys replace the label filter
  status: Todo
- local_id: US2
  title: Filter expressions and pull report
  status: Todo
- local_id: US3
  title: Links resolve across a tracker's sources
  status: Todo
- local_id: US4
  title: Docs and changelog for scoped sources
  status: Todo
created_at: '2026-11-04T09:54:38Z'
updated_at: '2026-11-04T16:45:59Z'
---
<!-- sq:body -->
## Outcome

An adopter points a source at a scope on the tracker (a GitLab project or group, a GitHub repository, a Jira query) and the pull fetches every issue of that scope. No label has to be put on the tracker. Which issues become items is decided in squads: the type map says what is an item, and an optional filter expression narrows it further. Links between issues resolve across every source of one tracker, so a project covered by several sources keeps the epic-to-story links between them (BUG-1284). The grammar, report wording and edge cases are settled in ADR-1274 section 14 (the 2026-11-04 source-selection entries); this feature builds and documents that.

## Acceptance criteria

- Each source declares exactly one scope key, required: gitlab `project` or `group` (subgroups included), github `repository`, jira `jql`. A source with none, or more than one, is refused at load with a message naming the valid keys. No single-label filter remains in the spec, the docs or the sources shipped with the package.
- `filter` is optional, a table of one boolean expression per side. Expressions use `or`, `and`, `not` and parentheses with the precedence ruled in section 14. A malformed expression is refused at load, with the line and column of the fault. The sides a filter names are ANDed.
- A pull lists the whole scope and applies the filter in squads. The report counts what it did not turn into items: issues the filter rejects are counted as filtered out, issues that map to no type as `skipped <n> (no type)`, and an issue that maps to two types is named on its own line.
- A held issue that the filter now rejects, or that left the scope, is reported as out-of-filter; one deleted on the tracker is reported as gone. The two read differently on the report.
- Restricted issues (GitLab confidential issues and internal notes, Jira issues with a security level) are skipped with no opt-out, and the report says how many.
- Links resolve across every source with the same base URL: BUG-1284's scenario (an epics source and a stories source on one tracker) produces the ref on the first pull of the second source, and an earlier-dropped link heals on a later pull without the host issue changing. A mapped link whose target is held nowhere is named on the report instead of dropped silently.
- Docs and CHANGELOG describe scopes, filter expressions, the report lines and cross-source links for adopters, per the list of owed items in section 14, with no internal references.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1285 add-story "As a <role>, I want … so that …"`; track with `sq feature 1285 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Scope keys replace the label filter

<!-- sq:story:US1:body -->
As an adopter, I declare one scope per source and the pull fetches all of it, with no label on the tracker.

- gitlab `project` or `group`, github `repository`, jira `jql`; exactly one, required, refused at load otherwise.
- No label filter remains anywhere, shipped defaults and docs included.
- A pull with no filter turns every issue whose type maps into an item.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Filter expressions and pull report

<!-- sq:story:US2:body -->
As an adopter, I narrow what becomes an item with a filter expression per tracker side, and I can read what the pull did with the rest.

- Grammar and precedence as in ADR-1274 section 14; a malformed expression is refused at load with line and column.
- The report counts filtered out and `skipped <n> (no type)`, and names an issue mapped to two types.
- Out-of-filter (held, now rejected or left the scope) reads differently from gone (deleted on the tracker).
- Restricted issues are skipped with no opt-out and counted.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Links resolve across a tracker's sources

<!-- sq:story:US3:body -->
As an adopter with several sources on one tracker, I keep the links between their issues.

- Issue identity, link targets and reference translation span every source with the same base URL.
- BUG-1284's scenario (epics source and stories source) yields the ref on the second pull, and a link dropped on an earlier pull heals on a later pull without the host issue changing.
- A mapped link with no held target is named on the report.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Docs and changelog for scoped sources

<!-- sq:story:US4:body -->
As an adopter, I find the new source selection explained, and I know what changed.

- Docs describe scope keys per connector, the filter grammar with examples, the report lines and cross-source links.
- CHANGELOG entry for the unreleased version, written for adopters, no internal references.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-04T16:42:28Z] `tech-writer` Theo Writer:
  - Narration sweep done for the scoped-sources and re-export increments. Docs and CHANGELOG were clean apart from F14 (fixed). I reworded history phrasing in the bodies of FEAT-1285 (outcome, US1, US3), TASK-1286 (ST4, ST6) and TASK-1289. The code comments to fix are listed in the handback to @manager.
- [2026-11-04T16:45:59Z] `manager` Catherine Manager:
  - Done: TASK-1286 delivered, REV-1292 approved, BUG-1284 verified. Live check against a real GitLab instance still to run (TASK-1278).
<!-- sq:discussion:end -->
