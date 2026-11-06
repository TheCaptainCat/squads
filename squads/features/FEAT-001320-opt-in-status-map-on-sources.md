---
id: FEAT-1320
sequence_id: 1320
type: feature
title: Opt-in status map on sources
status: InProgress
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
- local_id: US6
  title: As an adopter, I apply the map to every held item with a full pull
  status: Todo
created_at: '2026-11-06T15:08:03Z'
updated_at: '2026-11-06T15:37:56Z'
---
<!-- sq:body -->
A source can opt in to a status map: a table in `sources.toml` that sends tracker values to workflow statuses. When the pull takes an issue from the tracker, the item's status moves to the mapped status, so a closed issue closes its item. A source with no map behaves as in 0.20.0: the tracker's state lands in the `source` record and no pull writes the item's status.

The exact shape, precedence and timing are ADR-1274 section 15; this feature delivers it.

## Outcome

An adopter who wants a closed issue to close its item declares that once, per source, in the sources spec. Nothing is hardcoded: the map names statuses from the squad's own workflow spec, so a customised lifecycle works, and a status the workflow does not declare is refused when the spec loads. Items pulled before the map was declared can be brought in line in one command.

## In scope

- A per-source, opt-in map from tracker values to ordered lists of workflow statuses, declared in `sources.toml` beside the type, field and link maps.
- Validation at load against the workflow spec.
- The pull applying the map when it takes an issue from the tracker, without the transition rule, reported on the issue's line.
- `sq source pull --full`, which applies the map to every held item at once.
- The docs and a warning on manual status changes telling an adopter which side owns status for a mapped source.
- Identical behaviour on a hosted squad: the map is spec data read where the squad is served.

## Out of scope

- Writing status back to the tracker.
- A default map in the connector defaults: no source moves status unless its adopter declares a map.
- Mapping `out-of-filter` and `gone`, which are squad states.
- A map per item type, and a bulk command apart from the pull.
- A schema change or migration.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1320 add-story "As a <role>, I want … so that …"`; track with `sq feature 1320 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As an adopter, I declare a status map on a source

<!-- sq:story:US1:body -->
Done when:
- A source in `sources.toml` can declare `maps.statuses`, per side of its connector, from tracker values to statuses; the shape and the sides per connector are ADR-1274 section 15.
- Each mapped value takes an ordered list of statuses, and the first one that is a state of the item type's lifecycle wins; a bare string is a one-element list, so one list covers every type of a squad with several lifecycles.
- The sides are checked in the connector's declared order and the first side that maps one of the issue's values decides; a value a side does not map falls through to the next side.
- The map is per source: it is refused under a connector default, and no status name appears in code.
- `sq override` scaffolds and diffs it with the rest of the document, and `sq source list` shows whether a source has one.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As an adopter, a closed issue closes its item

<!-- sq:story:US2:body -->
Done when:
- On a source with a map, the pull sets the item's status to the mapped one when it creates the item and when the issue changes (its listed update time or state differs from the record), ignoring the lifecycle's allowed transitions, as `status --force` does; the status must still be one of the item type's lifecycle.
- A status set by hand holds until the issue next changes: a pull of an unchanged issue writes nothing.
- A state the map does not name leaves the status alone, and an item whose type's lifecycle holds none of the listed statuses is left alone and reported on the issue's line.
- A status move is named on the issue's line, and `--dry-run` says what it would move.
- An `out-of-filter` or `gone` item is not moved.
- A second pull with nothing changed writes nothing.
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
- At load, every status listed in the map must exist in the workflow spec; a misspelled one fails with a message naming the source, the side, the key and the status.
- An empty list, an empty status name and a status listed twice in one list are refused.
- A side the connector version does not have, and a `state` or `category` key outside its enum, are refused, listing what is valid.
- The failure is on the sources document only: the squad's other commands keep working, and `sq check` reports it.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — As an adopter, I read which side owns status

<!-- sq:story:US5:body -->
Done when:
- `docs/sources.md` states that status is squad-owned by default and tracker-driven only for a source whose map declares it, in the ownership section, the pull report and each connector's open or closed line, and explains the list form and the precedence of the sides.
- A manual status change on an item of a mapped source succeeds with a warning that the status follows the source again when the issue next changes; it is never refused.
- The upgrade note says items pulled before the map was declared move with `sq source pull --full`, at their issue's next change, or on `show --refresh`.
- The 0.20.1 changelog entry describes what an adopter now does differently, written by the tech writer.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — As an adopter, I apply the map to every held item with a full pull

<!-- sq:story:US6:body -->
Done when:
- `sq source pull --full [<source>]` reads every held, selected issue in detail, with no shortcut for unchanged issues, and applies the status map to every held item; without a name it covers every enabled source.
- It writes only what differs, so a second full pull of an unchanged tracker writes nothing.
- On a source with a status map it overrides statuses set by hand, and the docs say so.
- `--dry-run` lists every move and writes nothing; the pull report lists the moves made.
- It also picks up what a plain pull misses until the issue next changes: an edited or deleted comment, or a link added.
- The docs state its cost: one detail read per held issue (comments and links, often several requests) on top of the listing, subject to the tracker's rate limits, and advise naming one source.
- It stores nothing and needs no migration.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->
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
- [2026-11-06T15:20:49Z] `product-owner` Nina Product:
  - The open design points are closed: ADR-1274 section 15 settles every one of them, with op-pierre rulings db47414 and e7fc5f9. FEAT-1320 is aligned to it.
    - US1: ordered status lists per value, sides checked in the connector's order, first match wins.
    - US2: the pull sets status without the transition rule, on creation and when the issue changes; a hand-set status holds until then.
    - US4: load check is that every listed status exists in the workflow; empty list, empty name and duplicates are refused.
    - US5: a manual status change warns and is never refused.
    - US6 (new): `sq source pull --full`, with its warning, `--dry-run` and its cost.
    @manager ready for the tech lead to cut tasks.
- [2026-11-06T15:27:17Z] `tech-lead` Olivia Lead:
  - - Broken down into two Draft tasks, both targeting MILE-1319:
      - TASK-1321 (python-dev): six subtasks, ST1 to ST6, mapped to US1, US4, US2, US3, US5 (the warning only) and US6.
      - TASK-1322 (tech-writer): docs/sources.md, docs/stability.md and the 0.20.1 CHANGELOG entry. It depends on TASK-1321.
    - Approach: one hook in the pull's `Compiler` (`create`/`refresh`) covers the pull, `relink`, `show --refresh` and `--full`, with a forced importer `status` op. No schema bump. About 12 to 14 CLI cases on recorded responses.
    - Open points:
      1. @product-owner the feature's in-scope list names "the source view" as telling the adopter who owns status, but neither US5 nor ADR-1274 section 15 asks for a view change, so no work is planned for it. Confirm, or say what the view should show.
      2. The `--full` warning must come before the fetch. The plan has the CLI read `SOURCE_LIST` (which gains `status_map`) and warn before it calls `SOURCE_PULL`, since response warnings arrive only after the fetch. @architect flag it if you want another route.
      3. Risk: a squad that declares the map can no longer pull on a 0.20.0 build; the CHANGELOG entry says so.
    - @manager both tasks are ready to promote at dispatch, TASK-1321 first.
- [2026-11-06T15:36:37Z] `op-pierre` Pierre Chat:
  - Drop both: no change to the source view (the docs say which side owns status), and no warning before sq source pull --full fetches (--dry-run previews the moves, and the pull report lists the moves made). @architect @product-owner @tech-lead align ADR-1274 section 15, this feature and TASK-1321.
- [2026-11-06T15:37:06Z] `product-owner` Nina Product:
  - Aligned to the ruling 10b7aa9: the source view is out of scope and US6 has no pre-fetch warning; --dry-run previews the moves and the pull report lists them. @manager
<!-- sq:discussion:end -->
