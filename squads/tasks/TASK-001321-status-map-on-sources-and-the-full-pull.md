---
id: TASK-1321
sequence_id: 1321
type: task
title: Status map on sources and the full pull
status: Done
parent: FEAT-1320
author: tech-lead
assignee: python-dev
refs:
- MILE-1319:targets
- REV-1323:addresses
description: maps.statuses per source, applied by the pull, plus sq source pull --full
subentities:
- local_id: ST1
  title: Declare maps.statuses and the status sides
  status: Done
  assignee: python-dev
  maps_to: US1
- local_id: ST2
  title: Validate the status map at load and in the probes
  status: Done
  assignee: python-dev
  maps_to: US4
- local_id: ST3
  title: Apply the status map in the pull compiler
  status: Done
  assignee: python-dev
  maps_to: US2
- local_id: ST4
  title: Keep a source without a map unchanged
  status: Done
  assignee: python-dev
  maps_to: US3
- local_id: ST5
  title: Warn on a manual status move on a mapped item
  status: Done
  assignee: python-dev
  maps_to: US5
- local_id: ST6
  title: Add sq source pull --full
  status: Done
  assignee: python-dev
  maps_to: US6
created_at: '2026-11-06T15:26:05Z'
updated_at: '2026-11-06T16:33:09Z'
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
`sq source pull --full [<source>]` reads every held, selected issue in detail and applies the map to their items.

- `SourcePullRequest.full` and the `--full` option (`src/squads/_cli/_source.py`). Without a name it covers every enabled source, as a plain pull does.
- `src/squads/_services/_fetch.py`: with `full`, `_triage` sends every held issue the source selects to the detail fetch, instead of counting it `untouched`. Unheld issues (filtered out, without a type, or held elsewhere) and held items missing from the listing are handled as in a plain pull. The fetch stays outside every lock.
- The compiler is unchanged. It writes only what differs, so a second full pull of an unchanged tracker writes nothing. Comment edits and deletions, and links added, are picked up because `--full` compiles every held, selected issue.
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
- [2026-11-06T15:54:39Z] `python-dev` Elias Python:
  - @manager TASK-1321 is implemented, ST1 to ST6 are Done. Not committed, not pushed; full suite not run.
    
    **ST3 answer.** The importer's create accepts any state of the item type's lifecycle with no transition rule (`_create_model` takes `status`, and only the catalog gate checks it is a state of the type). So `Compiler.create` sets `CreateEvent.status` directly and no forced status event follows. A refresh emits `StatusEvent(force=True)`.
    
    **Files changed (src)**
    - `_sources/`: `_spec.py` (`SourceMaps.statuses`, a bare string normalised to a list), `_registry.py` (`status_sides`, `status_enums`), `_connector.py` (side names), `_maps.py` (`mapped_status`, `StatusChoice`), `_loader.py` (load checks, connector-default refusal), `_tracker_probes.py`, `_jira/_probes.py`, `_jira/_connector.py`, `_gitlab/_connector.py`, `_github/_connector.py`, `__init__.py`.
    - `_services/`: `_pull.py` (create and refresh hook, dry-run wording), `_fetch.py` (`full` in `_triage`/`fetch_source`), `_source_links.py` (`status_map` on the list row), `_tracker_owned.py` (`status_follow_warning`), `_item_ops.py` and `_item_write_ops.py` (the warning).
    - `_api/_dto/_sources.py` (`SourcePullRequest.full`, `SourceRow.status_map`), `_cli/_source.py` (`--full`), `_cli/_render/_sources.py` (Status map column), `_overrides/_service.py` (scaffold rule and example).
    - The shim already treats `source pull` as a long command and the operation has `Timeout.LONG`, so nothing changed there. No schema bump, no migration.
    
    **Tests added (7 new cases; the existing `source list` cases gained the `status_map` key)**
    - `tests/cli/test_source_pull.py`: creation at the mapped status (list form, state before labels, label fall-through); no-fit and conflict lines, no fall-through, out-of-filter not moved; move on change, `--dry-run`, unchanged pull, hand-set status holds; Jira status before category; `--full` (moves, comment edit picked up, dry-run writes nothing, second full pull writes nothing, detail reads only under `--full`).
    - `tests/cli/test_source_list.py`: mapped and unmapped source (text and `--json`); a document holding every load refusal.
    - `tests/cli/test_source_check.py`: unknown Jira status is blocking.
    - `tests/cli/test_item_source.py`: the warning (mapped, unmapped, unchanged status); `show --refresh` and `relink` apply the map.
    - Support: `tests/_profile.py` (`working`, `done`, `foreign`) plus its meta check, `tests/cli/_source_pulls.py` helpers, and a recorded `/rest/api/3/status` route in `tests/fixtures/sources/jira-cloud/routes.json`.
    - Falsified: 16 breaks, each turned its test red (create status, out-of-filter guard, dry-run wording, unchanged-issue shortcut, `--full` shortcut, Jira order, no-fit fall-through, conflict, state/labels order, list flag, enum check, connector-default refusal, Jira probe, warning, refresh hook, Jira side value). After restoring, green. One trap for anyone redoing this: `uv run` rebuilds the package by mtime, so a restored file must be touched or the stale broken build stays installed.
    
    **Gates**
    - `uv run --all-extras pyright`: `0 errors, 0 warnings, 0 informations`
    - `uv run --all-extras ruff check .`: `All checks passed!`
    - `uv run --all-extras ruff format --check .`: `676 files already formatted`
    - `pytest tests/meta tests/cli/{test_source_pull,test_source_list,test_source_check,test_item_source,test_show,test_item_verbs,test_override,test_comment_verbs,test_check}.py -n 4`: `1122 passed in 44.84s`
    - Same source modules with `--squad override`: `103 passed in 19.88s`
    - `~/.local/bin/sq check`: `no issues`
    
    **Adopter-visible changes for the writer**
    1. `maps.statuses.<side>` in `sources.toml`, per source only. Value is a status or an ordered list; the first status the item type's lifecycle has wins. Sides, checked in order, first match wins: `state` then `labels` (GitLab, GitHub); `status`, `category` then `labels` (Jira). A value a side does not map falls through; a side that maps a value but gives no status for the type stops the walk. Two labels that resolve to different statuses set nothing. `state` keys: `opened`/`closed` (GitLab), `open`/`closed` (GitHub); `category` keys: `new`/`indeterminate`/`done`.
    2. When it applies: at creation, when a pull fetches a changed issue while the source selects it, on every `show --refresh` and `relink`, and for every held selected issue under `--full`. The status is set without the transition rule. `out-of-filter` and `gone` items are never moved. A source without the map pulls as before.
    3. Load errors (the sources document fails, `sq check` reports it under `sources_loads`):
       - `connectors.gitlab.v4: maps.statuses is declared per source, not as a connector default; move it under [sources.<name>.maps.statuses]`
       - `source '<n>': maps.statuses.<side>: the connector has no side '<side>' for the status map (sides: state, labels)`
       - `... : '<key>' is not a state of the tracker (valid: opened, closed)` (`category` for Jira)
       - `... : '<key>' -> '<status>' is not a status of the workflow`
       - `... : '<key>' lists no status`, `lists an empty status name`, `lists '<status>' twice`
       - `source '<n>': maps.statuses.<key> is a value, not a side: write it under maps.statuses.<side>, one of: state, labels`
    4. Report lines, on the issue's line (also in `show --refresh` and `relink` output):
       - `<key>: <ID> moved to <Status> (<side> <value>)`, and `would move to` under `--dry-run`, for example `platform/api#13: TASK-3 moved to Done (state closed)`.
       - `<key>: <value> maps to A, B, none of which is a status of <type>; left alone`
       - `<key>: status left alone, its labels map to A, B`
       - A status write counts the issue as `refreshed`. When the move happens, the old `<state>; <ID> stays` line is not printed.
    5. New `sq source pull --full [<source>]`, composable with `--dry-run` and `--json`. It reads every held, selected issue in detail (comments and links), writes only what differs, applies the map to every held item (overriding hand-set statuses on a mapped source) and picks up comment edits that a plain pull misses. No warning before the fetch, as ruled. Unheld issues cost only their listing row.
    6. Warning, never a refusal: `sq <type> <n> status <s>` and `update --status <s>` on an item whose source declares `maps.statuses` print `warning: the status follows source '<name>' again when issue <key> next changes`. There is none when the status does not change, the item has no record, the source has no map, or the writer is the source itself. Status is not in the tracker-owned refusals.
    7. `sq source list`: new `Status map` column (`yes` or `-`), and `status_map` (bool) on each row of `--json`. `docs/sources.md:348` shows the old table.
    8. `sq override scaffold sources`: the commented rules and worked example gain the status map. The worked example is loaded by a test.
    9. `sq source check` on Jira: `maps.statuses.status` keys are checked against `GET /rest/api/<n>/status`, blocking when absent (`maps.statuses.status: '<key>' is not among the tracker's statuses`); `labels` keys follow the existing per-side rule.
    10. Risk for the upgrade note: a squad that declares the map can no longer load its sources on a 0.20.0 build (extra key), which fails only the source commands.
- [2026-11-06T16:14:04Z] `python-dev` Elias Python:
  - @manager REV-1323 F1 and F3 (code part) fixed, both set Fixed on the review. Not committed. F1: src/squads/_services/_pull.py (Compiler.refusal, gate in move_status and create; description converted before the move line). New case test_a_status_a_validator_refuses_is_left_alone_and_the_rest_of_the_issue_lands in tests/cli/test_source_pull.py (bundled only, assignee_present@error): falsified on both the refresh and create paths. New adopter-visible line: '<key>: status left alone, <Status> is refused: <reason>'; the item is created at its initial status in that case. F3: src/squads/_cli/_source.py help. Writer: CHANGELOG 'every held item under --full' -> 'every held issue the source selects'; F2 stays with the writer. Gates: pyright 0 errors, ruff check All checks passed!, ruff format 676 files already formatted. Tests (tests/meta plus source, show, override cli modules, -n 4): 924 passed. sq check clean.
- [2026-11-06T16:21:23Z] `python-dev` Elias Python:
  - @manager REV-1323 F3 (reopened) and F4 fixed and set Fixed. Not committed. F3: --full help in src/squads/_cli/_source.py now 'Read every held issue the source selects in detail, not only the changed ones, and apply the status map to it.' F4: src/squads/_services/_pull.py, create and refresh report 'status left alone, X is refused' only when the item passes before the move and fails after; otherwise only the existing dropped line prints. Adopter-visible for the writer: that line no longer appears when the refusal holds at any status (it was never a documented line beyond F1's wording). Test: test_a_refusal_that_holds_at_every_status_is_not_blamed_on_the_mapped_status in tests/cli/test_source_pull.py, falsified (red without the base check). Gates: pyright 0 errors, ruff check clean, ruff format 676 files already formatted; tests/meta + source/show/override cli, -n 4: see handback. sq check clean.
- [2026-11-06T16:26:08Z] `python-dev` Elias Python:
  - @manager REV-1323 F5 fixed and set Fixed. Not committed. Compiler.move_status now decides on the mapped status (move if it passes; left-alone line only if it fails while the current status passes; no status line if both fail), restoring the move of an unassigned InProgress task whose issue closes under assignee_present@error. Case test_an_item_failing_a_validator_at_its_status_still_moves_to_one_that_passes in tests/cli/test_source_pull.py, red with the old early return. No adopter-visible text change. Gates: pyright 0 errors, ruff check clean, ruff format clean; tests/meta + source/show/override cli -n 4 passed. sq check clean.
<!-- sq:discussion:end -->
