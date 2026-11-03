---
id: TASK-1278
sequence_id: 1278
type: task
title: GitHub and Jira connectors behind the registry
status: Draft
parent: FEAT-1273
author: tech-lead
refs:
- ADR-1274:implements
- MILE-1269:targets
- TASK-1276:depends-on
- TASK-1277:depends-on
description: GitHub, Jira cloud-v3 and dc-v2 connectors with their probes on recorded
  responses; a multi-version connector requires version
subentities:
- local_id: ST1
  title: A multi-version connector requires version
  status: Todo
  maps_to: US1
- local_id: ST2
  title: GitLab connector
  status: Cancelled
  maps_to: US2
- local_id: ST3
  title: GitHub connector
  status: Todo
  maps_to: US3
- local_id: ST4
  title: Jira Cloud connector, cloud-v3
  status: Todo
  maps_to: US4
- local_id: ST5
  title: Jira Data Center connector, dc-v2
  status: Todo
  maps_to: US5
created_at: '2026-11-03T23:02:46Z'
updated_at: '2026-11-03T23:19:02Z'
priority: high
---
<!-- sq:body -->
## Goal

The trackers after GitLab behind the source seam: GitHub including Enterprise, Jira Cloud (`jira@cloud-v3`) and Jira Data Center (`jira@dc-v2`), each a row of the literal `(name, version)` connector table implementing the full interface the pull task defines, with its own probes and default converter, and none holding a squad vocabulary name (FEAT-1273 US1, US3 to US5). GitLab, the HTTP helper, the loopback harness and the vocabulary guard land with the pull task; GitLab's probes with the source check task (ADR-1274 §14).

## ADR-1274 sections implemented

- §9 and §14, connectors: three more rows of the `(name, version) → class` table, each implementing every interface method, including the reference method (text and host key in, spans and full keys out; qualifying a short form such as `#12` against the host key is the connector's job) and its own probes. HTTP through the shared helper; reached only from `_services`.
- §9, the vocabulary guard already in `tests/meta` covers the new modules unchanged.
- §1, the immutable IDs: GitHub node ID, Jira issue ID; a transferred or moved issue keeps its item while its key changes.
- §7, the credential fields each connector names (`token`; `user` and `token` for `jira@cloud-v3`).
- §8 and §14, connector versions: versions are not ordered and squads never picks one, so a `jira` source must name its version; without one it fails at load naming the source and listing the known versions.

## Scope

- GitHub (github.com and Enterprise base URL, token): pull requests returned by the issues API excluded; filter by label; type and field maps read labels; comments pulled; immutable ID is the node ID; default converter `github-md`.
- Jira Cloud `jira@cloud-v3` (REST v3, email and API token, `adf`): JQL filter; type map reads the issue type, field maps priority and labels, link maps issue link types; open or closed from the status category, so custom workflows need no map.
- Jira Data Center `jira@dc-v2` (REST v2, personal access token, `jira-wiki`): same filter, maps, state and identity rules as cloud-v3, sharing its code where the APIs agree.
- The required `version` for a connector with several versions, shown on the two Jira versions. No version ordering is implemented.

## Layers and expected files

- `src/squads/_sources/_registry.py` (three rows), new `src/squads/_sources/_github.py`, `_jira.py` (shared Jira code), `_jira_cloud.py`, `_jira_dc.py`; keep each connector's probes beside it.
- `src/squads/_specs/sources.toml` (per connector version: default converter and default maps naming tracker values only).
- `tests/cli/test_source.py`, `tests/fixtures/sources/<connector>/` (recorded API responses, scrubbed of real tokens, hosts and personal data), served by the existing loopback harness.

## Tests (about 9 new)

Per subtask below, on the loopback harness the pull task built, so each connector's real HTTP path runs and CI never reaches a tracker.

## Schema

None.

## CHANGELOG

Report to the tech writer: the three connector versions, their credential fields, the filters they take, how each decides open or closed, that a `jira` source must name its version, and that a source connector is not the MCP connector of FEAT-319.

## Depends on

The sources spec and pull task (interface, tables, HTTP helper, harness, guard, pull, credentials) and the source check task (probe method and framework, the `adf`, `jira-wiki` and `github-md` converters).

## Order

One developer, in the order listed; Jira DC follows Jira Cloud because it reuses its code, and the required-version case (ST1) needs both Jira versions, so it is written last.

## Size

M.

## Working rules

- Work in your own git worktree off `origin/release/0.20`.
- Gates before handback: `uv run --all-extras pyright`, `uv run --all-extras ruff check .`, `uv run --all-extras ruff format --check .`, the tests your diff selects (grep the names you changed across `tests/`) plus the floor (`tests/meta`, `tests/cli`, `tests/check`, `tests/daemon` for any change under `_specs/`, `_rendering/templates/`, `_cli/`, `_shim.py` or `_daemon/`), and `~/.local/bin/sq check` clean for the items you touched. The main loop runs the full suite.
- Tests follow ADR-1172: CLI surface cases with `@pytest.mark.covers(...)`, one case per behaviour plus its boundary refusals, no unit tests on internal functions, no shape tables. Each new check rule gets its `@pytest.mark.breaches(...)` case. Falsify each new test once and say so in the handback.
- Any edit under `src/squads/_rendering/templates/` runs `python scripts/gen_template_manifest.py` in the same change.
- No credential value in any output, log line, reflog entry, test golden or fixture file committed to the repository; test credentials are fake strings written by the test.
- No module-level mutable state: thread the request's spec, playbook and sources document. A new module-level table goes on the mutable-state guard's allowlist as a code constant.
- No bundled type, kind, field, status, ref-kind or view literal in code outside `_specs/` and `_migrations/`.
- Comments and docstrings: one or two sentences, present tense, no ticket IDs, release versions or history. No ticket IDs or process words in test or file names.
- CHANGELOG and adopter docs are the tech writer's: report, do not edit `CHANGELOG.md` or `docs/`.
- Use `~/.local/bin/sq` for board operations; the dev tree only through `uv run --project <repo> sq -C <scratch>` on a scratch squad under the session scratchpad.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1278 add-subtask "<title>"`; track with `sq task 1278 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — A multi-version connector requires version

<!-- sq:subtask:ST1:body -->
A source must name its `version` when its connector has several registered versions (ADR-1274 §14): versions are not ordered, so squads never picks one, and no ordering is implemented. With the two Jira rows registered, a `jira` source without `version` fails at load, naming the source and listing the known versions. The single-version case (`gitlab` resolving to its only version) and the unknown-version refusal are covered by TASK-1276 ST1. Written after ST4 and ST5.

Tests (1): a `jira` source without `version` fails at load, naming the source and listing `cloud-v3` and `dc-v2`.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — GitLab connector

<!-- sq:subtask:ST2:body -->
GitLab connector (API v4), gitlab.com and a self-hosted base URL, personal or project token. Label filter; type and field maps read labels, scoped labels included; notes become comments, system notes excluded; related and blocking links read. Immutable ID: the issue's global ID; a moved issue keeps its item and updates `source.key`. Probes per the source check framework.

Tests (3): pull from recorded responses creates items with comments (system notes absent) and a `blocks` link mapped to a ref; a recorded move updates the key on the same item; `sq source check` on recorded responses passes access and flags an absent mapped label.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-11-03T23:14:44Z] `tech-lead` Olivia Lead:
  - Cancelled per ADR-1274 §14: the GitLab connector with its pull and move cases moved to TASK-1276 ST10, and its probes with the check case to TASK-1277 ST1.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — GitHub connector

<!-- sq:subtask:ST3:body -->
GitHub connector, github.com and an Enterprise base URL (`/api/v3`), token, default converter `github-md`. Implements every interface method as the pull task defines it, including the reference method (`#12` and `owner/repo#12` qualified against the host key), and its own probes. Pull requests returned by the issues API excluded; label filter; type and field maps read labels; comments pulled. Immutable ID: the node ID, so a transferred issue keeps its item.

Tests (3): pull from recorded responses excludes a pull request and pulls comments; a recorded transfer keeps the item and updates the key; `sq source check` passes access on an Enterprise base URL.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Jira Cloud connector, cloud-v3

<!-- sq:subtask:ST4:body -->
`jira@cloud-v3`: REST API v3, email and API token (credential fields `user`, `token`), descriptions and comments converted with `adf`. Implements every interface method as the pull task defines it, including the reference method (`PROJ-45` is already a full key), and its own probes. JQL filter; type map reads the issue type, field maps priority and labels, link maps issue link types. Open or closed from the status category, so a custom workflow needs no map. Immutable ID: the issue ID; a move to another project keeps the item while the key changes. Shared Jira code in `_sources/_jira.py`.

Tests (3): pull from recorded responses maps type, priority and a link, and an issue in the `done` category is `closed`; a recorded project move keeps the item and updates the key; `sq source check` reports an invalid JQL as a blocking access failure.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Jira Data Center connector, dc-v2

<!-- sq:subtask:ST5:body -->
`jira@dc-v2`: REST API v2, personal access token, text converted with `jira-wiki`. Same filter, maps, state, identity and reference rules as `jira@cloud-v3`, sharing `_sources/_jira.py` where the APIs agree; only the endpoints, the auth header, the converter and the probes' endpoints differ.

Tests (2): pull from recorded responses creates an item with a wiki-markup description converted; `sq source check` passes access with a personal access token.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-03T23:11:24Z] `architect` Robert Architect:
  - - @tech-lead ADR-1274 §14 (2026-11-04) changes this task's scope:
      - ST2 (GitLab) leaves this task. The connector, its pull and move tests go to TASK-1276, and its probes and check case to TASK-1277.
      - ST1 keeps the newest-version default and its test, which needs the two Jira versions. The HTTP helper, the loopback harness and the vocabulary guard move to TASK-1276. The unknown-version refusal stays covered by TASK-1276 ST1.
      - ST3 to ST5 implement the full interface as TASK-1276 defines it, including the reference method (text and host key, giving spans and full keys; qualifying `#12` against the host key is the connector's job), and their own probes.
- [2026-11-03T23:15:38Z] `tech-lead` Olivia Lead:
  - Scope updated to ADR-1274 §14 per @architect's comment: body and subtasks revised; see the subtask table for what moved.
- [2026-11-03T23:17:26Z] `architect` Robert Architect:
  - - @tech-lead ADR-1274 §14 (2026-11-04) replaces ST1's "newest-version default": versions are not ordered and squads never picks one. ST1 becomes "a source must name its version when its connector has several". Its one test: a `jira` source without `version` fails at load, naming the source and listing `cloud-v3` and `dc-v2`. Keep it after ST4 and ST5. No version ordering is implemented.
<!-- sq:discussion:end -->
