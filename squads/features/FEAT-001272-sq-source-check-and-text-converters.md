---
id: FEAT-1272
sequence_id: 1272
type: feature
title: sq source check and text converters
status: Ready
parent: EPIC-1268
author: product-owner
refs:
- MILE-1269:targets
- FEAT-1271:depends-on
description: A per-source readiness checklist, and shared tracker-text converters
subentities:
- local_id: US1
  title: sq source check prints a checklist per source
  status: Todo
- local_id: US2
  title: A registry of named text converters
  status: Todo
created_at: '2026-11-03T15:57:08Z'
updated_at: '2026-11-03T22:54:55Z'
---
<!-- sq:body -->
Before pulling, an operator can see whether each declared source is usable and whether the squad's maps match what the tracker actually has: `sq source check [<name>]` runs each connector's probes and prints a checklist with a fix for every failure. It is distinct from `sq check`, which never calls the network.

Connectors also share the conversion of tracker text to markdown through a registry of named converters, so a connector picks a converter instead of embedding one.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1272 add-story "As a <role>, I want … so that …"`; track with `sq feature 1272 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — sq source check prints a checklist per source

<!-- sq:story:US1:body -->
As an operator, `sq source check` tells me, for each source, what works and what to fix.

Done when:
- The check runs where the squad is served and reads the same credential store as the pull, so every probe sees what the pull will see: reachability, permissions and credential.
- Each line is a pass, a blocking failure or a warning, and every failure is followed by a fix naming what to change on the tracker, in `sources.toml` or in the credential store.
- Access probes: credential present, host reachable, authenticated (as whom), project or filter valid, read permission; a source's list stops at its first blocking access failure.
- Vocabulary probes: every value a map names (label, issue type, priority, link type) exists on the tracker; a missing one is blocking.
- Coverage probes: tracker values in-filter issues carry that no map covers, authors or assignees whose immutable ID is in no operator's `identities`, and identities whose ID no longer resolves, are warnings.
- `--json` prints the checklist; the exit code is 1 on any blocking failure, 0 otherwise.
- `sq source pull` runs the access probes first and reports a failure with the same line.
- The command and probe framework is connector-neutral; each connector version supplies its probes.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — A registry of named text converters

<!-- sq:story:US2:body -->
As a connector, I convert tracker text to markdown through a shared, named converter.

Done when:
- A literal registry maps converter names to converters: `adf` (Atlassian Document Format), `jira-wiki` (Jira wiki markup), `gitlab-md` and `github-md` (relative upload and image links made absolute; nothing downloaded).
- Each connector version names its default converter; a source can override it in `sources.toml`, validated at load against the registry.
- Each converter is tested against recorded samples, including nested lists, code blocks, tables, links and mentions.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-03T15:57:37Z] `op-pierre` Pierre Chat:
  - Rulings (2026-11-03): one command per source checks availability and that the required labels, types and values exist, printed as a checklist. It is named `sq source check`.
- [2026-11-03T16:17:49Z] `architect` Robert Architect:
  - @product-owner board check: US1, `sq source check` reads the token like the pull, so the ADR-1261 conflict noted on FEAT-1271 applies here too (a served command does not see the client's `SQUADS_SOURCE_*` variables).
- [2026-11-03T21:25:41Z] `op-pierre` Pierre Chat:
  - Ruling (2026-11-03): `sq source check` runs where the squad is served and reads the same server-side credential store as the pull; see the ruling on FEAT-1271.
<!-- sq:discussion:end -->
