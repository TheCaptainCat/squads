---
id: TASK-1279
sequence_id: 1279
type: task
title: Adopter docs, stability guide and changelog for sources
status: InProgress
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
  status: Done
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
updated_at: '2026-11-04T03:26:48Z'
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
- [2026-11-04T00:08:54Z] `tech-writer` Theo Writer:
  - Progress from @tech-writer: the stored view bodies portion is written (uncommitted; CHANGELOG.md and docs/ only).
    
    - CHANGELOG `## [0.20.0]`: a Migration block (schema 0.19 to 0.20, writes no item file, the three refusals with their output and remedies) and seven Added entries: stored views and the pair, the escape and LF rule, body writes keeping pairs and their refusals, view add completing an open-only tag, the four markers_balanced findings, the template/transform `body` keyword, and the `show --json` stored entry.
    - docs/workflow.md: new "Stored views" section; the computed-every-time, show --json, field reference, template context and transform call/output text cover stored views.
    - docs/stability.md: new Tier 1 section "View tags and stored view bodies"; the `body` and `views` rows of show --json (REV-1280 F2) and the self-source note.
    - docs/overrides.md: `stored` in the view grammar, the computed-on-every-request paragraph and the template context.
    - docs/migration.md: new "Upgrading to 0.20: the schema step".
    - No subtask is marked: ST1 and ST3 grow with the later tasks, ST2 and ST4 have not started. Nothing about sources, connectors, credentials, pulls or the `source` view kind is written.
    - Open points for @manager: (1) the altered-pair refusal names `sq <type> <n> show --refresh`, which no build has yet, and the docs quote that message as-is; (2) the migration's manual text says to give a `source` role another slug, but no command changes a slug (stability.md, "A roster slug never changes"), so the remedy needs a real procedure; (3) `sq workflow views --json` rows carry no `stored` key.
- [2026-11-04T03:26:48Z] `tech-writer` Theo Writer:
  - Progress from @tech-writer: the sources pull and source check part is written (uncommitted; CHANGELOG.md and docs/ only).
    
    - New adopter page docs/sources.md: sources.toml and the connector-defaults key form, the version rule, credentials (location, modes), source list, check, pull (listing diff, per-issue drop and retry, states), reading a pulled item (notice, `trusted`, `--json` comment keys), ownership refusals, unlink and relink, `show --refresh`, `identities`, the eight check rules, the GitLab connector, the converters, redirects, where the commands run. Indexed in docs/README.md.
    - docs/stability.md: `source` core key and the nested-record rule; the namespaced author and the reserved `source` word; the attribute line; the sources.toml grammar; the credential store; the source commands (Tier 2); JSON rows for item `source`, discussion entries, inbox `untrusted`, operator `identities`, `sq source` shapes and the views catalog `stored`.
    - docs/overrides.md (sources.toml in the layout and scaffold, the `map` kind, `source` core key, `identities` on operator, the source check rules), docs/workflow.md (pulled items, the bundled `source_description` view, who writes a stored body), docs/daemon.md (long commands, source commands and credentials), docs/adoption.md (no `as` names a source), docs/migration.md (the `source` type or alias load refusal and its steps).
    - CHANGELOG 0.20.0: the stale migration remedies and the stored-body writer fixed; Added and Changed entries for sources, credentials, pull, check, list, ownership, refresh/unlink/relink, map and identities, converters, check rules, redirects, the reserved word, JSON changes and the wider marker refusal.
    - ST1 is Done. ST2 stays open: I could not verify that a pull holds the daemon's serial lock for its whole run, so the page does not state it. ST3 and ST4 wait on the Jira and GitHub connectors.
    - Held back as asked: the sourced-comment author display and the `kind = "source"` view grammar.
    - For @manager: (1) the altered-pair refusal for a stored view that no source feeds still names `sq <type> <n> show --refresh`, which refuses an item with no source record; (2) `sq workflow views --json` adds `stored` before `transform`, not after the last field as the additive rule in stability.md says.
<!-- sq:discussion:end -->
