---
id: TASK-1279
sequence_id: 1279
type: task
title: Adopter docs, stability guide and changelog for sources
status: Draft
parent: FEAT-1273
author: tech-lead
assignee: tech-writer
refs:
- ADR-1274:implements
- MILE-1269:targets
- TASK-1275:depends-on
description: Stability contracts, the external sources adopter page, connector docs
  and the 0.20 changelog section
subentities:
- local_id: ST1
  title: Stability guide contracts
  status: Todo
- local_id: ST2
  title: Adopter page for external sources
  status: Todo
- local_id: ST3
  title: CHANGELOG 0.20 section
  status: Todo
- local_id: ST4
  title: Connector documentation
  status: Todo
  maps_to: US1
created_at: '2026-11-03T23:02:46Z'
updated_at: '2026-11-03T23:19:03Z'
priority: medium
---
<!-- sq:body -->
## Goal

Adopters can declare a source, store its credential, pull, check and work on sourced items from the documentation alone, and `docs/stability.md` states every contract the epic adds. The CHANGELOG's 0.20 section carries each feature's entry as its developer task lands. Owner: the technical writer. It sits under the connectors feature because the adopter path is complete only once a real tracker can be pulled; it documents the whole epic.

## ADR-1274 sections documented

The Consequences section's list: in `docs/stability.md`, the nested-record rule (§2), the `map` kind (§2), the `source` record (§1), the namespaced author grammar and the reserved `source` slug (§6), the paired view tag and its escape (§4), the comment-attribute line (§5), the `sources.toml` grammar (§8) and the credential store's location and permissions (§7). In the adopter docs: that squads may reserve more author words and each is refused as a role slug from the release that reserves it (§6); that a source connector is not the MCP connector of FEAT-319 (FEAT-1273); that a pull holds the daemon's serial lock for its whole run (Consequences).

## Expected files

- `docs/stability.md`
- `docs/overrides.md` (`sources.toml` beside the other three documents; `stored = true` in the views grammar)
- `docs/workflow.md` (the `map` kind, `identities` on operators)
- `docs/recipes.md` or a new adopter page for external sources: declaring a source, `sq source credential set`, `sq source check`, `sq source pull`, `show --refresh`, `source unlink|relink`, trust and the untrusted notice
- `docs/daemon.md` (source commands run where the squad is served; credential verbs only on the owner-only listener; the serial lock)
- `docs/migration.md` (0.20 and its `manual` steps)
- `CHANGELOG.md` (the 0.20 section)

## Inputs

Each developer task's handback comment lists its adopter-visible changes. Read the code and the CLI help for the final wording; do not copy implementer prose.

## Rules

- User-facing docs describe the tool for adopters: no item IDs (the FEAT-319 reference above is for you, not for the page), no repo or dev-process content.
- Present truth only: no "changed in", "used to", "no longer" about the thing itself (CHANGELOG and migration steps excepted).
- Each subtask starts when the developer task it documents is Done; the CHANGELOG subtask grows with each one.
- Run `~/.local/bin/sq check` before handback.

## Depends on

The stored view bodies task (the first to land). The later subtasks wait on their own developer task, as the subtask bodies say.

## Size

M.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1279 add-subtask "<title>"`; track with `sq task 1279 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Stability guide contracts

<!-- sq:subtask:ST1:body -->
Add to `docs/stability.md` every contract ADR-1274's Consequences list: the nested-record rule and the `map` kind, the `source` record and its keys, the namespaced author grammar and the reserved `source` slug, the paired view tag with its escape grammar, the comment-attribute line, the `sources.toml` grammar and the credential store's location and permissions. Each part starts once its developer task is Done: the paired tag after stored view bodies, the rest after the sources spec and pull task.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Adopter page for external sources

<!-- sq:subtask:ST2:body -->
An adopter page for external sources (a new `docs/` page or a section of `docs/recipes.md`), plus the touches in `docs/overrides.md`, `docs/workflow.md`, `docs/daemon.md` and `docs/migration.md`: declare a source in `squads/.overrides/sources.toml`, store its credential, check it, pull, read a sourced item and its untrusted notice, refresh, unlink and relink, and set an operator's `identities` by handle. State that a pull holds the daemon's serial lock for its whole run, that the credential verbs run only on the owner-only local listener or in process, and that squads may reserve more author words. Starts once the source check task is Done.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — CHANGELOG 0.20 section

<!-- sq:subtask:ST3:body -->
Keep the CHANGELOG's 0.20 section current: add each feature's entry when its developer task reaches Done, from that task's handback and the code, written for what an adopter now does or sees differently. Include the schema 0.20 bump and point to its `manual` steps. Done when all four developer tasks are.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Connector documentation

<!-- sq:subtask:ST4:body -->
Document the four connector versions (`gitlab`, `github`, `jira@cloud-v3`, `jira@dc-v2`): base URLs, credential fields, filters, how each decides open or closed, its default converter, and that a source must name its `version` when its connector has several (Jira), while a single-version connector needs none. Say plainly where both appear that a source connector is not the MCP connector the docs describe elsewhere. Starts once the connectors task is Done.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
