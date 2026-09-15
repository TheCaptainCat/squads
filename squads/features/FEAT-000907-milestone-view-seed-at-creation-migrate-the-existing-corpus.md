---
id: FEAT-907
sequence_id: 907
type: feature
title: 'Milestone view: seed at creation, migrate the existing corpus once'
status: Done
parent: EPIC-897
author: product-owner
priority: medium
refs:
- MILE-867:targets
- ADR-880:implements
- FEAT-905:depends-on
description: templates/items/milestone.md.j2 seeds the tag; a one-time bulk run of
  the placement verb retrofits existing milestones
subentities:
- local_id: US1
  title: Milestone creation template seeds the roll-up tag
  status: Done
- local_id: US2
  title: One-time migration retrofits the tag via the placement verb
  status: Done
- local_id: US3
  title: Migration reports the count of bodies it changed
  status: Done
- local_id: US4
  title: 'The roll-up tag is required: refused on write, reported when absent'
  status: Cancelled
created_at: '2026-09-03T09:11:01Z'
updated_at: '2026-09-15T09:36:11Z'
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
- Whether a document must keep this tag once seeded, and what enforces that, is a separate
  concern this feature does not cover — it belongs to FEAT-948, the view mechanism's integrity
  half.
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
### US4 — The roll-up tag is required: refused on write, reported when absent

<!-- sq:story:US4:body -->
As the owner of a milestone, I want the roll-up tag to be a requirement of the view declaration
rather than a convention, so a body write cannot silently produce a milestone with no roll-up and
a milestone that has lost its tag is reported.

Acceptance: the view declaration carries a `required` flag (default off) and `milestone_rollup`
declares it on; the hosts it binds are exactly the documents the tool's own placement seeds the
tag onto, derived from the creation template rather than declared per type; a body **replace** on
such a milestone is refused, independently of `--force` and of the authored-body protection,
while `--append` still works; `sq view rm` will not take the tag off it; and `sq check` reports
error-level on a host that lacks it, naming the placement verb as the remedy. Nothing is stored
to detect it, and nothing is reported for a view that is not required.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
- [2026-09-15T08:03:05Z] Olivia Lead:
  - Cancelled here rather than removed: the scope is not abandoned, it moved. FEAT-948 carries it as a five-story breakdown, broadened past the milestone-only frame this story was written in, and TASK-942 is reparented there with its subtasks remapped onto those stories. Cancelling keeps the move legible from this feature; removing would leave the Scope section's pointer to FEAT-948 referring to something with no trace here.
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-14T12:21:16Z] Olivia Lead:
  - Broken into two tasks, both Draft (promotion at dispatch is mine): TASK-941 the seeding and the
    one-time migration (US1/US2/US3), TASK-942 the `sq check` advisory (US4).
    
    Two surfaces, not four tasks: 941 is the corpus-write surface (creation template, migration
    runner, registry step, schema bump) and 942 is the validator-catalog surface. Disjoint modules,
    different dependency sets, and 942 can ship without 941 having reached the corpus.
    
    One shared seam pulled into 941 rather than duplicated: **which view names a type's creation
    template currently seeds**, resolved override-aware through the same template resolution the
    create path uses. Both the migration and the advisory read it — ADR-880 keys both on the same
    template-as-it-currently-stands condition, and two answers to that question is exactly the drift
    that condition exists to prevent. That makes 941 gate 942, recorded as a `depends-on`.
    
    **Build order: TASK-941, then TASK-942. Not parallel.**
    
    Three things I want on the record rather than found in review:
    
    - **The migration needs a schema bump** (0.14 to 0.15: a new runner, its registry step, and
      `SCHEMA_VERSION`). That is what makes it run exactly once by gate rather than as a recurring
      sweep, which is the ADR's whole distinction from `sq repair`'s roster convergence. Consequence:
      the landing commit hard-stops every `sq` command in this tree until `sq migrate up` runs, for
      everyone. I fenced the dev out of running it against our own corpus — sequencing the real run
      is yours and op-pierre's.
    - **The double render is corpus-wide and transient, and is not a bug.** FEAT-904 depends on
      FEAT-907, not the reverse (I checked the edge direction; I briefly added a backwards
      `depends-on` on TASK-941 and removed it again — that is the only ref churn on this pass). So
      seeding lands while `[items.milestone]` still carries `views = ["milestone_rollup"]`, and after
      941 every milestone renders its roll-up twice on `show --full` until FEAT-904 deletes the
      attachment. Fenced in the task body: no test may assert a single render.
    - **One call for you, on TASK-942 ST3.** Selecting the advisory means creating this repository's
      **first** `.overrides/workflow.toml` — we have no overrides at all today, and a workflow
      override is a standing maintenance cost (drift against the bundled base to reconcile at every
      release). The catalog member is unambiguous and lands either way; only the selection is in
      question. Ship the member unselected, or take the override? I have held ST3 behind that
      confirmation.
    
    `sq check` clean. @manager both ready for dispatch in that order; I hold the Draft-to-Ready gate.
- [2026-09-14T13:50:14Z] Pierre Chat:
  - Three rulings on this feature's build:
    
    - **Schema bump**: build it and run it in-session. The 0.14 to 0.15 runner, registry step and
      SCHEMA_VERSION bump land as designed, and the real `sq migrate up` is sequenced against this
      corpus as soon as the code is in, rather than being left for a later controlled moment.
    - **Double-render window**: close it in the migration task. It also drops the bundled
      `views = ["milestone_rollup"]` declaration as it seeds the tag, so no milestone ever renders
      its roll-up twice. This moves one line of FEAT-904's scope earlier, deliberately.
    - **The sq check advisory's selection**: catalog member only. The validator lands in the
      catalog, but this repo does NOT select it in its own spec, so no `.overrides/workflow.toml`
      is created here. The advisory will not fire in this repo; that is accepted.
- [2026-09-15T07:20:25Z] Nina Product:
  - Corrected the Scope section: removed the deleted warn-level, catalog-only sq check advisory bullet (and its ADR-864/FEAT-898 framing), replaced with a pointer to FEAT-948, which now owns the required-view requirement half per op-pierre's ADR-880 fourth amendment. US1-US3 and the discussion are untouched.
  - FEAT-948 (Required views: a declared, enforced document invariant) is the new home for that scope, under EPIC-897. @manager
- [2026-09-15T08:03:13Z] Olivia Lead:
  - Dropped the stale `FEAT-898 (depends-on)` ref. Confirmed from the record rather than assumed: commit 3b6aeed6 added that edge in the same hunk as the Scope bullet 'Declared through ADR-864's declared-level assignment grammar (FEAT-898)' and US4's acceptance clause 'requires ADR-864's declared-level grammar (FEAT-898) to exist as a catalog member'. Both texts are gone — the fourth amendment's tier-1 ruling deleted the catalog advisory — and nothing left in US1-US3 (creation template, migration runner, changed-body count) touches validator-assignment grammar. FEAT-948 does not inherit it: a tier-1 finding is unconditional and takes no declared level.
  - US4 moved to Cancelled with the reason on the story. It is not abandoned — FEAT-948 owns it as five stories, and TASK-942 is reparented there. Cancelling rather than removing keeps the move legible from this feature, which the Scope section now points at.
  - @manager FEAT-907's remaining scope is US1-US3 only; nothing here is blocked by the required-view work any more.
<!-- sq:discussion:end -->
