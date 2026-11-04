---
id: FEAT-1273
sequence_id: 1273
type: feature
title: 'Connectors: GitLab, GitHub and Jira'
status: Done
parent: EPIC-1268
author: product-owner
refs:
- MILE-1269:targets
- FEAT-1271:depends-on
- FEAT-1272:depends-on
description: The first connectors, registered by name and version
subentities:
- local_id: US1
  title: Connector registry by name and version
  status: Todo
- local_id: US2
  title: GitLab connector, any instance
  status: Todo
- local_id: US3
  title: GitHub connector, including Enterprise
  status: Todo
- local_id: US4
  title: Jira Cloud connector (cloud-v3)
  status: Todo
- local_id: US5
  title: Jira Data Center connector (dc-v2)
  status: Todo
created_at: '2026-11-03T15:57:08Z'
updated_at: '2026-11-04T08:29:06Z'
---
<!-- sq:body -->
The trackers the first release supports, each behind the source seam: GitLab on any instance, GitHub including Enterprise, and Jira Cloud and Data Center. Connectors are registered by name and version in a literal table; a version is a separate connector behind a shared name, picked by the source's `version` (default: newest), and carries its own default converter and probes.

No connector contains a squad vocabulary name (item type, badge field or value, ref kind, status): that vocabulary comes from the maps in `sources.toml`. Tests run against recorded API responses, so CI never reaches a real tracker.

A source connector is not the MCP connector of FEAT-319; the documentation says so where both appear.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1273 add-story "As a <role>, I want … so that …"`; track with `sq feature 1273 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Connector registry by name and version

<!-- sq:story:US1:body -->
As the source seam, I find a connector by name and version.

Done when:
- A literal `(name, version)` to connector table, with no registration side effect; adding a connector or a version is one row.
- A source may omit `version` only when its connector has exactly one registered version; otherwise it fails at spec load, listing the known versions. An unknown name or version fails at spec load, listing the known ones.
- The connector interface covers: fetch issues changed since a cursor, list the IDs matching the filter, fetch one issue, fetch comments and links, derive an issue's URL from the base URL and its key and a user's from their handle, resolve a handle to an immutable user ID, the probes for `sq source check`, and the default converter.
- A guard keeps squad vocabulary literals (item types, badge fields and values, ref kinds, statuses) out of connector modules; tracker API names a connector legitimately reads (`issuetype`, Jira's `done` status category) are allowed.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — GitLab connector, any instance

<!-- sq:story:US2:body -->
As an operator on any GitLab instance, I pull issues carrying the opt-in label.

Done when:
- Works against gitlab.com and a self-hosted base URL (API v4), with a personal or project token.
- Filter by label; type and field maps read labels (including scoped labels); notes become comments, system notes excluded; related and blocking links are read.
- The immutable ID is the issue's global ID; a moved issue keeps its item.
- Pull and probes are tested against recorded responses.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — GitHub connector, including Enterprise

<!-- sq:story:US3:body -->
As an operator on GitHub, I pull issues carrying the opt-in label.

Done when:
- Works against github.com and an Enterprise base URL, with a token.
- Pull requests returned by the issues API are excluded.
- Filter by label; type and field maps read labels; comments are pulled; the immutable ID is the issue's node ID, so a transferred issue keeps its item.
- Pull and probes are tested against recorded responses.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Jira Cloud connector (cloud-v3)

<!-- sq:story:US4:body -->
As an operator on Jira Cloud, I pull the issues my JQL selects.

Done when:
- `jira@cloud-v3`: REST API v3 with an email and API token; descriptions and comments converted with `adf`.
- The filter is JQL; the type map reads the issue type, field maps read priority and labels, link maps read issue link types.
- Open or closed comes from the status category, so custom workflows need no map.
- The immutable ID is the issue ID, so a move to another project keeps the item while its key changes.
- Pull and probes are tested against recorded responses.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Jira Data Center connector (dc-v2)

<!-- sq:story:US5:body -->
As an operator on Jira Data Center, I pull the issues my JQL selects.

Done when:
- `jira@dc-v2`: REST API v2 with a personal access token; text converted with `jira-wiki`.
- Same filter, maps, state and identity rules as `jira@cloud-v3`, sharing its code where the APIs agree.
- Pull and probes are tested against recorded responses.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-03T15:57:37Z] `op-pierre` Pierre Chat:
  - Rulings (2026-11-03): connectors can have versions; behind the curtain they are different connectors, presented as versions of one parent connector (e.g. `jira@cloud-v3`, `jira@dc-v2`).
- [2026-11-03T16:17:50Z] `architect` Robert Architect:
  - @product-owner board check:
    - US1, the guard needs a scope: squad vocabulary is out, but connectors legitimately name tracker API fields (`issuetype`, Jira's `done` status category).
    - "Connector" already names the MCP connector of FEAT-319, a different thing; worth a line in the docs to keep the two apart.
- [2026-11-03T23:18:12Z] `product-owner` Nina Product:
  - US1 reworded per ADR-1274 section 14: version may be omitted only when the connector has one registered version; otherwise the source fails at load listing known versions.
- [2026-11-04T08:29:06Z] `manager` Catherine Manager:
  - Done: connectors approved (REV-1283), docs and changelog complete.
<!-- sq:discussion:end -->
