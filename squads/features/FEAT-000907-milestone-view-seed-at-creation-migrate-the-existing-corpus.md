---
id: FEAT-907
sequence_id: 907
type: feature
title: 'Milestone view: seed at creation, migrate the existing corpus once'
status: Draft
parent: EPIC-897
author: product-owner
priority: medium
refs:
- MILE-867:targets
- ADR-880:implements
- FEAT-905:depends-on
- FEAT-898:depends-on
description: templates/items/milestone.md.j2 seeds the tag; a one-time bulk run of
  the placement verb retrofits existing milestones
subentities:
- local_id: US1
  title: Milestone creation template seeds the roll-up tag
  status: Todo
- local_id: US2
  title: One-time migration retrofits the tag via the placement verb
  status: Todo
- local_id: US3
  title: Migration reports the count of bodies it changed
  status: Todo
- local_id: US4
  title: 'sq check advisory: a template-seeded tag missing from the body'
  status: Todo
created_at: '2026-09-03T09:11:01Z'
updated_at: '2026-09-03T09:44:42Z'
---
<!-- sq:body -->
## Why

Type-attachment applied retroactively to every existing item; a tag does not. Without a
migration, every milestone already on disk quietly loses its roll-up. ADR-880's amendment
changes *how* this happens, materially: the migration is no longer a bespoke write into
authored prose — it runs through FEAT-905's own placement verb, in bulk. It is the tool's own
operation applied at scale, not a special-cased writer of its own.

## Scope

- `templates/items/milestone.md.j2` seeds `sq:view:milestone_rollup` at creation (via the
  template, which is a different, already-sanctioned path from the placement verb — not
  through `reject_markers` at all, since it writes the initial file rather than mutating one).
- A one-time migration calls FEAT-905's placement verb once per existing milestone that doesn't
  already carry the tag. Because it goes through that verb rather than a bespoke writer, the
  closed condition set ADR-880 ruled is inherited from the verb's own contract rather than
  reimplemented here:
  - insert-only — the verb never rewrites, reorders, or removes authored text;
  - one deterministic anchor (the verb's default position, the end of `:body`);
  - idempotent — the verb no-ops on a body already carrying the tag;
  - runs only against milestones (the one type whose template seeds the tag today);
  - reports how many bodies it changed.
- An author who later removes the tag (via FEAT-905's remove verb, or by a body replace that
  drops it) keeps it removed — this migration runs once and is not a precedent for retrofitting
  a future bundled view onto existing documents.
- A warn-level, catalog-only `sq check` advisory fires when an item whose **type's creation
  template, as it currently stands,** seeds a tag that the item's body no longer carries. The
  condition is keyed on the template, never on how the tag arrived — that single condition
  correctly covers both a migrated milestone and a freshly-created one, because the migration
  touches exactly the types whose template seeds the tag. A hand-placed tag on a type whose
  template does not seed it is the author's own; losing it is an ordinary, unflagged body edit.
  Declared through ADR-864's declared-level assignment grammar (FEAT-898); this project selects
  it in its own spec.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 907 add-story "As a <role>, I want … so that …"`; track with `sq feature 907 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Milestone creation template seeds the roll-up tag

<!-- sq:story:US1:body -->
As the owner of a newly-created milestone, I want the creation template to seed sq:view:milestone_rollup automatically, so a new milestone works with no migration step ever needed for it.

Acceptance: a freshly created milestone's body carries the tag; sq milestone <n> show --full renders the roll-up immediately.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — One-time migration retrofits the tag via the placement verb

<!-- sq:story:US2:body -->
As the owner of the existing milestone corpus, I want a one-time migration that places the tag on every existing milestone that lacks it, using FEAT-905's own placement verb rather than a bespoke writer, so the roll-up keeps working for milestones created before this change.

Acceptance: runs FEAT-905's insert operation once per milestone lacking the tag; inherits insert-only, single-deterministic-anchor, and idempotent-skip behaviour from that verb instead of reimplementing them; touches only milestones (the one type whose template seeds the tag today); a milestone whose author already removed the tag is left alone by a re-run, since the insert verb only acts where the tag is absent and this migration runs once, deliberately, not on a schedule.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Migration reports the count of bodies it changed

<!-- sq:story:US3:body -->
As op-pierre or a future auditor, I want the migration run to report how many milestone bodies it changed, so the write is visible in the run output and in the corpus diff, not silent.

Acceptance: the migration prints/returns a count of bodies changed; a re-run against an already-migrated corpus reports zero.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — sq check advisory: a template-seeded tag missing from the body

<!-- sq:story:US4:body -->
As anyone running sq check, I want a warn-level advisory when a milestone's body no longer carries the tag its creation template currently seeds, so a dropped tag (by any means -- a body replace, a manual removal) is visible instead of silently losing the roll-up.

Acceptance: catalog-only, warn; condition is 'this item's type's creation template, as it stands today, seeds a tag this body lacks' -- never keyed on provenance, so it covers migrated and freshly-created milestones identically; requires ADR-864's declared-level grammar (FEAT-898) to exist as a catalog member; this project selects it in its own spec; nothing is stored to detect it.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
