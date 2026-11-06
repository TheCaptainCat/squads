---
id: FEAT-1320
sequence_id: 1320
type: feature
title: Opt-in status map on sources
status: Draft
parent: EPIC-1268
author: product-owner
refs:
- MILE-1319:targets
- ADR-1274:addresses
description: A per-source map from tracker state to workflow status, declared in sources.toml
subentities:
- local_id: US1
  title: As an adopter, I declare a status map on a source
  status: Todo
- local_id: US2
  title: As an adopter, a closed issue closes its item
  status: Todo
- local_id: US3
  title: As an adopter, a source without a map is unchanged
  status: Todo
- local_id: US4
  title: As an adopter, a bad map is refused when the spec loads
  status: Todo
- local_id: US5
  title: As an adopter, I read which side owns status
  status: Todo
created_at: '2026-11-06T15:08:03Z'
updated_at: '2026-11-06T15:11:09Z'
---
<!-- sq:body -->
A source can opt in to a status map: a table in `sources.toml` that sends the tracker's issue state to a workflow status. When the pull sees an issue's state change, the item's status moves to the mapped status, so a closed issue closes its item. A source with no map behaves as in 0.20.0: the tracker's state lands in the `source` record and the item's status is the squad's alone.

This changes the ownership line drawn in FEAT-1271 and ADR-1274, where the squad owns status. With a map declared, the map is the one place a pull may write status, and only for the states the map names. ADR-1274 is being amended for the exact map shape and when it applies.

## Outcome

An adopter who wants a closed issue to close its item declares that once, per source, in the sources spec. Nothing is hardcoded: the map names workflow statuses from the squad's own workflow spec, so a renamed or customised lifecycle works, and a status the workflow does not declare is refused when the spec loads.

## In scope

- A per-source, opt-in map from tracker state to workflow status, declared in `sources.toml` beside the type, field and link maps.
- Validation at load against the workflow spec, naming the source, the map and the value on failure.
- The pull applying the map when an issue's state changes, reported on the source's pull line.
- The docs and the source description view telling an adopter which side owns status for a source with a map.
- Behaviour on a hosted squad identical to a local one: the map is spec data read where the squad is served, and the pull runs there.

## Out of scope

- Writing status back to the tracker.
- A default map in the bundled connector defaults: no source moves status unless its adopter declares a map.
- Mapping anything other than status (types, fields and links already have maps).
- Moving items on the squad side without a pull (daemon-triggered pulls stay out of scope).

## Open points for the architect

Raised as questions on the feature discussion and settled in ADR-1274, not decided here.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1320 add-story "As a <role>, I want … so that …"`; track with `sq feature 1320 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As an adopter, I declare a status map on a source

<!-- sq:story:US1:body -->
Done when:
- A source in `sources.toml` can declare a status map from the tracker's states to workflow statuses; the shape follows ADR-1274.
- The map is per source: two sources of one connector can differ, and a connector default may not turn it on.
- `sq override` scaffolds and diffs it with the rest of the document, and `sq source list` shows whether a source has one.
- No status name appears in code: every target is read from the declaring squad's spec.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As an adopter, a closed issue closes its item

<!-- sq:story:US2:body -->
Done when:
- On a source with a map, a pull that sees the issue's state change to a state the map names sets the item's status to the mapped status, and says so on the source's pull line.
- A state the map does not name leaves the status alone.
- A second pull with nothing changed writes nothing.
- A status transition the workflow refuses is reported on the issue's line and does not abort the rest of the pull; the next pull retries.
- Whether the map also applies at item creation, to a reopened issue, and to `out-of-filter` and `gone` items is settled in ADR-1274 and tested as written there.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As an adopter, a source without a map is unchanged

<!-- sq:story:US3:body -->
Done when:
- A source that declares no status map pulls exactly as in 0.20.0: the tracker's state lands in the `source` record and no pull writes the item's status.
- A squad on 0.20.0 gains no map and no behaviour change by upgrading, and no migration is needed for it.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — As an adopter, a bad map is refused when the spec loads

<!-- sq:story:US4:body -->
Done when:
- A map naming a status the workflow spec does not declare for the item types the source creates fails when the spec loads, with a message naming the source, the map and the value.
- A map naming a tracker state the connector cannot report is refused the same way.
- A map that makes an item type's lifecycle unreachable from the mapped status is refused or reported as ADR-1274 settles.
- The failure is on the sources document only: the squad's other commands keep working, as for any bad sources override.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — As an adopter, I read which side owns status

<!-- sq:story:US5:body -->
Done when:
- `docs/sources.md` states that status is squad-owned by default and tracker-driven only for a source whose map declares it, in the ownership section, the pull state table and the per-connector open or closed lines.
- The source description view shows the tracker's state beside the item's status, so a reader sees both.
- A local write to status on a mapped source is handled as ADR-1274 settles, and the refusal or the next-pull overwrite is explained in the message the adopter sees.
- The 0.20.1 changelog entry describes what an adopter now does differently, written by the tech writer.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-06T15:08:23Z] `product-owner` Nina Product:
  - Drafted under EPIC-1268, targeting MILE-1319 (0.20.1), five stories at behaviour level. @architect questions for the ADR-1274 amendment, not decided here:
    
    - Shape: is the map keyed by the source record's `state` values (`open`, `closed`), by raw tracker states, or by both? What does it do with `out-of-filter` and `gone`?
    - When it applies: at creation, on a state change only, or on every pull? Does a reopened issue move a Done item back?
    - Does a local status change on a mapped source get refused (like the other source-owned fields) or overwritten by the next change on the tracker? A status the squad set after the tracker's last change must not be clobbered by an unchanged pull.
    - A mapped status the lifecycle cannot reach from the current one: refuse, report and keep, or force?
    - Hosted squad: confirm the map is pure spec data and the pull applies it on the serving side (board notice 21).
    - Does this need a schema bump, or is it spec-only and so migration-free?
    
    @manager the feature and milestone are drafted, no tasks cut. Status is unchanged: FEAT-1320 Draft, MILE-1319 Draft.
- [2026-11-06T15:09:14Z] `op-pierre` Pierre Chat:
  - Status map design: track the status with labels, like the type map does today (a label side mapping tracker labels to workflow statuses). Labels can map to a terminal status too, and the closed state can map to a status. When both apply, closed takes precedence over the labels. @architect fold this into the ADR-1274 amendment.
- [2026-11-06T15:10:01Z] `op-pierre` Pierre Chat:
  - Correction to my earlier comment: Jira has no closed state, so the side that wins over the labels is a per-connector setting, like the sides of the other maps. Each connector version declares its own (for example the closed state on GitLab and GitHub, the status or its category on Jira). @architect
- [2026-11-06T15:11:09Z] `op-pierre` Pierre Chat:
  - Simpler: no special precedence rule. The precedence is the order in which the sides are checked, either first-match-wins or last-overwrites (architect to pick). On GitLab and GitHub the closed state then simply comes before the labels. @architect
<!-- sq:discussion:end -->
