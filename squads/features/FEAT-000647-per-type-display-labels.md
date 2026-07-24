---
id: FEAT-647
sequence_id: 647
type: feature
title: Per-type display labels
status: InProgress
author: product-owner
refs:
- ADR-646:addresses
subentities:
- local_id: US1
  title: Labels schema field + label_for resolver
  status: Done
- local_id: US2
  title: Retarget display-name consumers through the resolver
  status: Done
- local_id: US3
  title: Clients render per-type display labels
  status: Todo
created_at: '2026-07-24T11:47:44Z'
updated_at: '2026-07-24T12:57:20Z'
---
<!-- sq:body -->
Adopters can declare a human-readable display name per item type, so clients render "Decisions"/"ADRs" instead of the bare lowercase type key, with acronym types kept correctly capitalized.

An optional [items.<type>.labels] table in workflow.toml carries four independent, individually-optional forms — singular, plural, singular_lower, plural_lower. Any omitted form falls back to a value computed from the type name (capitalize/lower/naive +s), so ordinary types need zero config and only irregular or acronym types (ADR, PRD) pin the forms derivation would get wrong.

A single resolver becomes the one authority for a type's display name in any form; every place that currently derives a display label ad hoc (e.g. capitalizing the type key for a section title, tree/list view header, or CLI grouping header) is retargeted to call it instead, so acronym and irregular types render correctly everywhere at once.

Acceptance: an unconfigured type still resolves all four forms exactly as before (derived); a type with a partial labels override resolves only the pinned forms from config and the rest from derivation; an acronym type with all four forms pinned renders its acronym capitalization in every consuming surface; a misspelled labels sub-key is rejected; the change is additive with no schema/version bump.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 647 add-story "As a <role>, I want … so that …"`; track with `sq feature 647 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | Labels schema field + label_for resolver |
| US2 | Done |  | Retarget display-name consumers through the resolver |
| US3 | Todo |  | Clients render per-type display labels |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Labels schema field + label_for resolver

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
Add LabelSpec (frozen, extra=forbid; singular/plural/singular_lower/plural_lower, all optional str) to ItemSpec.labels, plus the label_for(type_str, form, spec) resolver in _models/_vocab.py implementing pin-else-derive for each form.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Retarget display-name consumers through the resolver

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
Replace ad-hoc .capitalize()/.title() type-name display derivations (Claude Code backend per-type section titles, VS Code tree/list views, CLI per-type grouping headers) with calls to label_for, so acronym/irregular labels render correctly everywhere.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Clients render per-type display labels

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
Resolved display labels are exposed on the sq JSON surface and clients render them: the Records tree shows pretty per-type names instead of the raw lowercase type key, matching the Roster tree's pretty Roles/Skills.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
