---
id: TASK-1321
sequence_id: 1321
type: task
title: Status map on sources and the full pull
status: InProgress
parent: FEAT-1320
author: tech-lead
assignee: python-dev
refs:
- MILE-1319:targets
description: maps.statuses per source, applied by the pull, plus sq source pull --full
subentities:
- local_id: ST1
  title: Declare maps.statuses and the status sides
  status: Todo
  assignee: python-dev
  maps_to: US1
- local_id: ST2
  title: Validate the status map at load and in the probes
  status: Todo
  assignee: python-dev
  maps_to: US4
- local_id: ST3
  title: Apply the status map in the pull compiler
  status: Todo
  assignee: python-dev
  maps_to: US2
- local_id: ST4
  title: Keep a source without a map unchanged
  status: Todo
  assignee: python-dev
  maps_to: US3
- local_id: ST5
  title: Warn on a manual status move on a mapped item
  status: Todo
  assignee: python-dev
  maps_to: US5
- local_id: ST6
  title: Add sq source pull --full
  status: Todo
  assignee: python-dev
  maps_to: US6
created_at: '2026-11-06T15:26:05Z'
updated_at: '2026-11-06T15:37:56Z'
priority: high
---
<!-- sq:body -->
Implements the opt-in status map on sources, `maps.statuses` in `sources.toml`, and `sq source pull --full`. The design authority is ADR-1274 section 15, as amended per op-pierre rulings db47414 and e7fc5f9. Where an earlier architect comment on ADR-1274 differs, the section 15 body wins: the load check is that every listed status exists in the workflow spec, not that it belongs to a type `maps.types` targets.

## Approach

The map is spec data on `SourceSpec.maps`. One hook in the pull's `Compiler` (`src/squads/_services/_pull.py`) applies it. `create` and `refresh` are the only places an issue taken from the tracker is compiled, and the plain pull (changed issues only), `relink`, `show --refresh` and `--full` all reach them. Applying the map there therefore gives exactly the "when the map applies" moments of section 15, with no second write path. A status move is the importer's existing `status` op with `force=True`, under the `source:<name>` actor. On creation, it is the `status` of the `CreateEvent`.

- **Spec and registry.** `SourceMaps` gains `statuses: dict[str, dict[str, tuple[str, ...]]]` (side, then tracker value, then an ordered list), and a bare string normalises to a one-element list. `ConnectorEntry` gains `status_sides`, in the fixed order of section 15: `("state", "labels")` for `gitlab@v4` and `github@v3`, and `("status", "category", "labels")` for both Jira versions. `ConnectorDefaults` refuses `maps.statuses`.
- **Connectors.** The status sides read raw tracker values, not the record's normalised `open`/`closed`: GitLab's `opened`/`closed`, GitHub's `open`/`closed`, and Jira's status name and `statusCategory` key. Each connector adds them to `Issue.sides`. The filter, type and field sides stay `ConnectorEntry.sides`, so `state`, `status` and `category` are not filter or type sides.
- **Resolution.** One pure function in `src/squads/_sources/_maps.py` walks `status_sides` in order and stops at the first side that maps one of the issue's values. It resolves each mapped value's list against the item type's lifecycle (first listed status that is a state of it). The outcome is one of four: a status; nothing mapped; a side that maps but none of whose statuses fit the type (left alone, reported, no fall-through); or values on one side that resolve to different statuses (left alone, reported, naming the values). The status map has no "sides that disagree set nothing" rule; `maps.types` and `maps.fields` keep it.
- **Pull.** In `Compiler.create`, the created item takes the mapped status, or its type's initial status when nothing maps or nothing fits. In `Compiler.refresh`, a `StatusEvent(force=True)` is emitted only when the mapped status differs from the item's, and only when the compiled state is `open` or `closed` (never `out-of-filter` or `gone`). The issue's line reads `<key>: <ID> moved to <Status> (<side> <value>)`, and `would move` under `--dry-run`. The skip line follows section 15's wording. A status write counts the issue as `refreshed`.
- **Ownership warning.** On an item whose source declares `maps.statuses`, `sq <type> <n> status` and `update --status` succeed with a warning: the status follows source `<name>` again when issue `<key>` next changes. Writes by the source's own actor are not warned. Status is never added to `src/squads/_services/_tracker_owned.py`'s refusals.
- **Full pull.** `SourcePullRequest` gains `full: bool`, and `sq source pull --full`. `fetch_source`/`_triage` in `src/squads/_services/_fetch.py` drop the unchanged shortcut for held, selected issues when `full` is set. Unheld issues are handled as in a plain pull, so they cost only their listing row. There is no warning before the fetch: `--dry-run` previews the moves, and the pull report lists the moves made.

## Files

- `src/squads/_sources/_spec.py`, `_registry.py`, `_maps.py`, `_loader.py`, `_tracker_probes.py`
- `src/squads/_sources/_gitlab/_connector.py`, `_github/_connector.py`, `_jira/_connector.py`, `_jira/_probes.py`
- `src/squads/_services/_pull.py`, `_fetch.py`, `_source_links.py` (`list_sources`), `_item_ops.py` and the `update --status` handler in `_item_write_ops.py`
- `src/squads/_api/_dto/_sources.py` (`SourcePullRequest.full`, and `SourceRow.status_map` for `sq source list`)
- `src/squads/_cli/_source.py` and its renderer under `_cli/_render/`
- `src/squads/_overrides/_service.py` (the `sq override scaffold sources` commented example)

## Tests

Tests follow ADR-1172: CLI surface, and few. There are no unit tests. Each case runs the real command against the loopback tracker in `tests/_tracker_harness.py`, which serves recorded API responses from `tests/fixtures/sources/`. A new route (for example Jira's status list for the probe) is a recorded response in the tracker's real shape, never an invented one. Cases go in `tests/cli/test_source_pull.py`, `test_source_list.py`, `test_source_check.py` and `test_item_source.py`. Expect about 12 to 14 cases; each subtask names its own. Declare each new pair with `@pytest.mark.covers(...)`: `("source pull", "--full")` is new. Falsify each test before handing back: break the code, watch the test go red, restore it.

## Gates

- `uv run --all-extras pyright`
- `uv run --all-extras ruff check .`
- `uv run --all-extras ruff format --check .`
- The selected tests, with `-n 4`, plus `tests/meta` (a new module-level constant may need its allowlist entry). The full suite is run by the main loop.
- `~/.local/bin/sq check` clean for the work touched.

## Constraints

- No schema bump and no migration: 0.20.1 is a patch, the item files keep their shape, and the `source` record keeps its seven keys.
- No status name in code: every target is read from the source's declaration.
- No ticket IDs in code or test names; comments and docstrings are one or two sentences of what and why.
- CHANGELOG.md and the adopter docs belong to the tech writer's task. Report every adopter-visible change in the handback, including message texts and the report line format.

## Acceptance

- Every Done-when of US1, US2, US3, US4 and US6, and the warning bullet of US5, holds and is shown by a CLI case.
- A source without `maps.statuses` pulls byte-identically to 0.20.0. The existing source tests pass unchanged.
- The gates are clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1321 add-subtask "<title>"`; track with `sq task 1321 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Declare maps.statuses and the status sides

<!-- sq:subtask:ST1:body -->
Lets a source declare `maps.statuses`, and exposes the tracker values it reads.

- `SourceMaps.statuses` (`src/squads/_sources/_spec.py`): side, then tracker value, then an ordered tuple of status names. A bare string normalises to a one-element tuple. No connector default and no overlay: the source's own declaration is the map.
- `ConnectorEntry.status_sides` (`_registry.py`), in section 15's fixed order: `state`, `labels` for GitLab and GitHub; `status`, `category`, `labels` for both Jira versions.
- The connectors add the raw status-side values to `Issue.sides`: GitLab `state` (`opened`/`closed`), GitHub `state` (`open`/`closed`), Jira `status` (the name as the instance spells it) and `category` (the `statusCategory` key). `Issue.state` stays normalised for the record.
- `SourceRow.status_map: bool`, shown by `sq source list` and its `--json` (US1). Nothing else reads it.
- `sq override scaffold sources`: the commented example in `src/squads/_overrides/_service.py` gains a `maps.statuses` example with the list form. `sq override diff` needs no code, since the map is document data.

Tests: one `sq source list` case showing a mapped and an unmapped source (text and `--json`).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Validate the status map at load and in the probes

<!-- sq:subtask:ST2:body -->
Refuses a bad map when `sources.toml` loads, and checks tracker-dependent keys in the probes.

At load (`src/squads/_sources/_loader.py`), the failures are collected with the other map checks, and each names the source, the side, the key and the status:
- a side outside the connector version's `status_sides` (listing them);
- a `state` key outside the connector's enum (`opened`/`closed` on GitLab, `open`/`closed` on GitHub) or a `category` key outside `new`/`indeterminate`/`done` (listing the enum);
- a listed status the workflow spec does not declare;
- an empty list, an empty name, or a status listed twice in one list;
- `maps.statuses` under `[connectors.<name>.<version>]`;
- a value that is a table where a side is due, through the existing `_side_shape_problems`.

Whether a listed status suits a type is not a load check; the pull decides that per item.

A failure fails the sources document only. The other commands keep working, and `sq check` reports it under the existing `sources_loads` rule, so no new check rule is needed.

Probes (`_tracker_probes.py`, `_jira/_probes.py`): `maps.statuses.status` keys are checked against Jira's status list and are blocking when absent; `labels` keys follow the existing per-side rule of section 14. This needs a recorded Jira status-list response.

Tests: one `sq source list` (or `sq check`) case loading a document that holds every refusal at once and asserting each message; one `sq source check` case for an unknown Jira status key.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Apply the status map in the pull compiler

<!-- sq:subtask:ST3:body -->
Applies the map whenever the pull takes an issue from the tracker.

- A pure resolver in `src/squads/_sources/_maps.py` walks `status_sides` in order, first match wins. A value a side does not map falls through to the next side. A side that maps a value decides even when none of its listed statuses fits the type (no fall-through). Values on one side that resolve to different statuses for the type set nothing.
- `Compiler.create` (`src/squads/_services/_pull.py`) sets `CreateEvent.status` to the mapped status for the created type. With nothing mapped, or nothing fitting (reported), it leaves the type's initial status. Check that the importer's create accepts any state of the lifecycle; if it applies the transition rule, a forced status event follows instead.
- `Compiler.refresh` emits `StatusEvent(force=True)` only when the mapped status differs from the item's, and only for a compiled state of `open` or `closed`. The list resolves against the item's current type, so a retyped item takes its own lifecycle's status.
- Report lines on the issue: `moved to <Status> (<side> <value>)` (`would move` under `--dry-run`); `<value> maps to A, B, none of which is a status of <type>; left alone`; and a line naming the values that conflict. A status write counts as `refreshed`. A skip is standing: the record's `updated_at` is still written, so the issue is not refetched.
- `relink` and `show --refresh` reach the same `Compiler`, so they apply the map each time with no extra code. Each needs one case.

Tests, in `tests/cli/test_source_pull.py` on recorded responses:
- a GitLab issue closing moves its held item to `Done`, and `--dry-run` says `would move` and writes nothing;
- a hand-set status holds over a pull of the unchanged issue;
- a created item takes its mapped status;
- `closed = ["Done", "Verified"]` closes a task as Done and a bug as Verified, and a type holding neither is left alone and reported;
- a label conflict, and state before labels;
- an `out-of-filter` item is not moved;
- a Jira `status`/`category` case;
- one `show --refresh` case and one `relink` case.
Merge cases where one scenario shows several behaviours.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Keep a source without a map unchanged

<!-- sq:subtask:ST4:body -->
Holds a source without `maps.statuses` to 0.20.0 behaviour. The tracker's state lands only in the `source` record, and no pull, relink or refresh writes the item's status.

Code: the resolver returns nothing when `maps.statuses` is empty, and the compiler emits no status event and no status line. Upgrading needs no migration and no document change.

Tests: the existing source tests pass unchanged, and serve as the guard. Add an assertion that a closed issue on an unmapped source leaves the item's status alone only if no existing case asserts it already. Look first; do not add a case for it.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Warn on a manual status move on a mapped item

<!-- sq:subtask:ST5:body -->
Warns, and never refuses, when the squad moves the status of an item whose source declares `maps.statuses`.

- `move_item_status` (`src/squads/_services/_item_ops.py`) and the `update --status` path in `_item_write_ops.py` return a warning in the `Response`: the status follows source `<name>` again when issue `<key>` next changes.
- There is no warning for an item without a record, for an item whose source has no map or is undeclared, or when the `sources.toml` document fails to load. Reuse the tolerant read of `mapped_field_codes` in `_tracker_owned.py`.
- No warning when the writer is the source's own actor (`source:<name>`).
- `_tracker_owned.py`'s refusals stay unchanged: status is not tracker-owned.

The docs side of US5 is the tech writer's task. Report the exact warning text in the handback.

Tests: one `tests/cli/test_item_source.py` case, a status move on a mapped item succeeding with the warning, and none on an unmapped one.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Add sq source pull --full

<!-- sq:subtask:ST6:body -->
`sq source pull --full [<source>]` reads every held, selected issue in detail and applies the map to every held item.

- `SourcePullRequest.full` and the `--full` option (`src/squads/_cli/_source.py`). Without a name it covers every enabled source, as a plain pull does.
- `src/squads/_services/_fetch.py`: with `full`, `_triage` sends every held issue the source selects to the detail fetch, instead of counting it `untouched`. Unheld issues (filtered out, without a type, or held elsewhere) and held items missing from the listing are handled as in a plain pull. The fetch stays outside every lock.
- The compiler is unchanged. It writes only what differs, so a second full pull of an unchanged tracker writes nothing. Comment edits and deletions, and links added, are picked up because every held issue is now compiled.
- No warning before the fetch. Under `--dry-run` the report lists every move and nothing is written; without it, the report lists the moves made. The CLI makes one call, `SOURCE_PULL`, so it works the same on a hosted squad.
- Check that the shim already treats `source pull` as a long command, and that the operation's timeout suits a full read.

Tests: one case per behaviour, merged where a scenario allows:
- a full pull moves an item whose hand-set status differs, names the move in the report, and picks up an edited comment;
- `--dry-run` lists the move and writes nothing;
- a second full pull writes nothing.
Declare `@pytest.mark.covers("source pull", "--full")`.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-06T15:37:28Z] `tech-lead` Olivia Lead:
  - Aligned to op-pierre ruling 10b7aa9: no source-view change, and no warning before sq source pull --full fetches (ST6 and the body updated; --dry-run and the report list the moves). SourceRow.status_map stays, for the sq source list line of US1 only; the pre-pull SOURCE_LIST call is gone. @product-owner US6 still says the full pull warns before it fetches.
<!-- sq:discussion:end -->
