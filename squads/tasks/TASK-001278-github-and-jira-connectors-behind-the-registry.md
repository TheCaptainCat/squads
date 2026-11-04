---
id: TASK-1278
sequence_id: 1278
type: task
title: GitHub and Jira connectors behind the registry
status: Done
parent: FEAT-1273
author: tech-lead
assignee: python-dev
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
  status: Done
  maps_to: US1
- local_id: ST2
  title: GitLab connector
  status: Cancelled
  maps_to: US2
- local_id: ST3
  title: GitHub connector
  status: Done
  maps_to: US3
- local_id: ST4
  title: Jira Cloud connector, cloud-v3
  status: Done
  maps_to: US4
- local_id: ST5
  title: Jira Data Center connector, dc-v2
  status: Done
  maps_to: US5
created_at: '2026-11-03T23:02:46Z'
updated_at: '2026-11-04T08:42:49Z'
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
- [2026-11-04T04:33:57Z] `python-dev` Elias Python:
  - - ST1, ST3, ST4, ST5 done (not committed). Gates: pyright 0 errors, ruff check and format clean, `tests/meta` 729 passed, `tests/cli tests/check tests/daemon` 1328 passed / 2 skipped, `sq check` clean. CLI start still imports no connector, urllib, http.client or ssl (`-X importtime`).
    - Rows: `github@v3`, `jira@cloud-v3`, `jira@dc-v2` in `_registry.py`; defaults in `_specs/sources.toml`; manifest regenerated, content store rebuilt.
    - New: `_github.py`, `_github_probes.py`, `_jira.py` (shared), `_jira_cloud.py`, `_jira_dc.py`, `_jira_probes.py`, `_tracker_probes.py` (the probe framework GitLab, GitHub and Jira share; GitLab's probes now sit on it, output unchanged), `_records.py` (tolerant JSON readers).
    - Changed: `_http.py` (generic `paged`, Link-header paging, 403 with Retry-After or exhausted limit is a rate limit and retried, 410 as not found, non-JSON and wrong-shape answers raise a named error, HTTP error reason from the body), `_gitlab.py` (uses `_records`), `tests/meta/_vocabulary.py` (one exemption: `_ISSUE_FIELDS` in `_jira.py`, Jira field names, one of which spells like a badge field).
    - Tests: `tests/cli/test_source_connectors.py`, 9 cases, fixtures under `tests/fixtures/sources/{github,jira-cloud,jira-dc}`. Each killed by a mutation (12 mutations run).
    - Decisions to confirm: Jira link types are keyed by the directional phrase ("blocks", "is blocked by"), so an inward link never makes a reverse ref; Jira field maps key on a label or the priority name; Jira Cloud handle is the accountId; comments with `visibility` or `jsdPublic: false` are not pulled; GitHub link types are `blocked_by` and `blocking`; a Jira source needs a `filter`.
    - Open: a listed issue whose comments 404 between listing and detail aborts the source's pull with a bare not-found message (shared fetch phase, GitLab too).
    @tech-writer: docs rows are in the handback report.
- [2026-11-04T04:34:07Z] `python-dev` Elias Python:
  - - Docs rows for @tech-writer:
      - Connectors: `github@v3`, `jira@cloud-v3`, `jira@dc-v2` (a source connector is not the MCP connector). A `jira` source must name `version`; without it the load fails listing `cloud-v3, dc-v2`.
      - Credentials: `github` token; `jira@cloud-v3` `user` (email) and `token` (basic auth); `jira@dc-v2` `token` (personal access token, bearer).
      - `base_url`: github.com, or an Enterprise `https://host` or `https://host/api/v3`; Jira site or Data Center URL (context path allowed).
      - Filters: GitHub a label (all issues the token sees); Jira a JQL query, required.
      - Open or closed: GitHub `state`; Jira `statusCategory` done is closed, so custom workflows need no map.
      - Maps: GitHub types and fields read labels (and the issue type name when present), links `blocked_by` and `blocking` (default `blocking = blocks`); Jira types read the issue type name or a label, fields read labels and the priority name, links read the directional phrase (default `blocks = blocks`).
      - Pull requests are skipped; Jira comments restricted by visibility or hidden from customers are not pulled; Jira Cloud shows the accountId as the handle, DC the username.
      - Default converters: `github-md`, `adf`, `jira-wiki`.
    - API shapes not confirmed against a live tracker (recorded from documentation only):
      - GitHub: `GET /issues?filter=all` as the cross-repository listing; Link-header paging; the issue `type` object; `/dependencies/blocked_by|blocking` and their absence (404) on older Enterprise; a transferred issue keeping its node ID and the old URL redirecting; `/meta`, `/user/{id}`; `github.com` base mapping to api.github.com (no test); installation tokens cannot call `/user`.
      - Jira Cloud: `/search/jql` with `nextPageToken` and `isLast`; `fields` selecting what comes back; `/label` paging; `/user/search` and `/user?accountId`; comment `visibility` and `jsdPublic`.
      - Jira DC: `/search` capping `maxResults`; `/user?key=` and `?username=`; `key` present on current DC; no label listing endpoint is used, so a mapped label no in-filter issue carries is reported missing.
- [2026-11-04T05:00:41Z] `architect` Robert Architect:
  - - @python-dev ADR-1274 §14 (2026-11-04) rules on REV-1283 F7. Exact changes; (b) also touches GitLab and the loader from earlier tasks, and this task owns it:
      - **(b) Maps keyed by tracker side** (fixes F6):
        - `maps.types.<side>` and `maps.fields.<badge field>.<side>` replace the flat tables. Each connector version declares its sides as a class constant: every connector has `labels`, GitLab and GitHub add `type`, and Jira adds `type` and `priority`. Add each to the vocabulary guard's exemption table if its names collide.
        - At load (`_sources/_spec.py`), refuse a side the version does not declare, listing the known ones. Overlay connector defaults per side, per key.
        - `Issue` carries each non-label side as its own value (for example `sides = {"type": "Bug", "priority": "High"}`), and Jira no longer appends the priority to `labels`.
        - `mapped_type` and `mapped_fields` collect the values from every side. If they disagree, nothing is set and the pull reports the values (the type case already does this).
        - Probes check each key against its side only (`/priority` for `priority`, labels for `labels`, the issue-type list for `type`).
        - Migrate the bundled `sources.toml` defaults and every fixture.
        - Test: the reviewer's F6 case. The label `High` with priority `Low` and `maps.fields.priority.priority = { Low = "low" }` sets `low`, and the label does not count.
      - **(c)** `@<accountId>` resolves by exact lookup (F4's fix), with no search.
      - **(d)** F3's DC fix as the reviewer wrote it: `expand=properties`, skip `sd.public.comment.internal == true`, behind a per-version method, plus fixture comments for both versions.
      - **(e)** Jira's `author_id` and `author_handle` come from `creator`, not `reporter`, with no fallback. Test: an issue whose reporter differs from its creator is attributed to the creator.
      - **(f)** `filter` is required and non-empty for every source, refused at load naming the source. Drop the run-time Jira-only refusal. Test: a GitHub source without `filter` fails `sq source list`.
- [2026-11-04T05:16:30Z] `python-dev` Elias Python:
  - - REV-1283 F1 to F6, F8, F9 and the architect's rulings (b) to (f) are done, not committed. Gates: pyright 0, ruff check and format clean, `tests/cli tests/check tests/daemon tests/meta` 2063 passed / 2 skipped, `sq check` clean, CLI start still imports no connector or urllib. Each new behaviour killed by a mutation.
    - Maps are now keyed by side. The sides each version declares are in the connector registry (`ConnectorEntry.sides`), not a class constant, because the loader must not import connector classes. Bundled `sources.toml` needed no change (links only); the override scaffold and every test fixture were migrated.
    - `filter` is required at load for every connector (the Jira run-time refusal is gone). Tests that declared a source without one were given a filter.
    - Link keys are checked against `/issueLinkType` (already in place).
    - Untested: GitHub's 403 secondary-limit message path (the backoff would sleep), `*.ghe.com` mapping and `github.com` mapping (no loopback host). A DC label no in-filter issue carries is a warning; GitHub types likewise.
    - Unconfirmed API: `expand=properties` on the DC comment listing returning `sd.public.comment`.
- [2026-11-04T05:38:55Z] `manager` Catherine Manager:
  - Accepted: REV-1283 approved with all findings verified; full suite 2117 passed; gates and sq check clean. Moved to Done under the operator's delegation of the loop.
- [2026-11-04T08:35:10Z] `manager` Catherine Manager:
  - Correction: GitLab is in the same position as GitHub and Jira. Its fixtures (tests/fixtures/sources/gitlab/routes.json) are hand-written from the API documentation and served on a loopback port; no pull has run against a live GitLab instance.
- [2026-11-04T08:42:49Z] `manager` Catherine Manager:
  - Live run (2026-11-04) on a private self-hosted GitLab 19.5 instance, from throwaway squads: source check, dry-run, pull, second pull (all unchanged), show --refresh, the title ownership refusal and sq repair (equal index) all behave as documented. Live shapes confirmed: /version, /user, labels, the instance-wide /issues listing by label, issue links, /users?username handle resolution, global issue IDs.
  - Gap found: a link becomes a ref only when both issues belong to the same source (_services/_pull.py links(), keyed on source name + issue ID). With one source per label (epics, stories), every epic-to-story link was dropped silently; one source covering both kept them.
  - Not exercised live: comments (the issues had none), closed, out-of-filter and gone issues, the type side, rate limits.
<!-- sq:discussion:end -->
