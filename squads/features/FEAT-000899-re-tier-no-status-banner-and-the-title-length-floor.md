---
id: FEAT-899
sequence_id: 899
type: feature
title: Re-tier no_status_banner and the title-length floor
status: Draft
parent: EPIC-540
author: product-owner
priority: low
refs:
- ADR-864:implements
- FEAT-898:depends-on
- MILE-934:targets
description: Move two floor members that fail the catalog's own tiering test to catalog-only,
  declared thresholds, selected by our own spec
subentities:
- local_id: US1
  title: Move no_status_banner from floor to catalog-only
  status: Todo
- local_id: US2
  title: Move the sub-entity title threshold from floor to catalog-only
  status: Todo
- local_id: US3
  title: This project selects both, at today's strength, in its own spec
  status: Todo
created_at: '2026-09-03T09:02:32Z'
updated_at: '2026-09-09T14:46:04Z'
---
<!-- sq:body -->
## Why

Two floor members fail the tiering test ADR-864 proposes for the whole catalog (*can a
competent squad be in this state on purpose, indefinitely?*):

- **`no_status_banner`** — this project's house convention (frontmatter is the source of
  status truth, no `STATUS:`/`## Status` prose) shipped as a universal defect every squad
  inherits. A team whose ADR template has carried a `## Status` heading for a decade gets a
  permanent, un-subtractable warning.
- **The sub-entity title threshold** (`subentity_title_max`, currently 120 characters) — a
  module constant, not a spec field. Every squad gets our number.

Neither is wrong for *us* — both stay fully enforced by this project's own spec once
re-tiered. Depends on FEAT-898 (needs declared levels/thresholds to move).

## Scope

- Move both members from the floor to catalog-only.
- Declare the title threshold as a spec field (this feature, not FEAT-898, is where the
  120-character default gets carried forward as our own selection).
- Select both, at their current effective strength, in this project's own bundled/working spec
  — re-tiering must not weaken either rule *for this squad*.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 899 add-story "As a <role>, I want … so that …"`; track with `sq feature 899 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Move no_status_banner from floor to catalog-only

<!-- sq:story:US1:body -->
As an adopter whose document conventions carry a '## Status' heading or similar, I want no_status_banner off the floor and available as a catalog-only selection, so a house convention we don't share doesn't warn on every record I own.

Acceptance: no_status_banner is removed from COMMON_CORE (the floor) and from every category bundle (a bundle cannot be subtracted from, so relocating it into a bundle would not fix this); it remains a fully valid catalog member, selectable per type or squad-wide; no engine behaviour changes for a squad that selects it.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Move the sub-entity title threshold from floor to catalog-only

<!-- sq:story:US2:body -->
As an adopter, I want the sub-entity title-length advisory off the floor and available catalog-only with its own declared threshold, so I'm not stuck with squads' own number.

Acceptance: subentity_title_max leaves the floor; its threshold is a declared spec field (built by FEAT-898), not the TITLE_ADVISORY_MAX module constant; the message and mechanism are otherwise unchanged.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — This project selects both, at today's strength, in its own spec

<!-- sq:story:US3:body -->
As this project, I want both re-tiered members selected in our own spec at their current effective strength, so re-tiering demotes neither rule for us -- it is the difference between a policy we hold and a defect we assert on every adopter's behalf.

Acceptance: this project's working spec explicitly selects no_status_banner (on the types that carried it today) and subentity_title_max:120 (matching today's TITLE_ADVISORY_MAX); a bare uv run sq check on this repo reports the same issues before and after this feature lands.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
