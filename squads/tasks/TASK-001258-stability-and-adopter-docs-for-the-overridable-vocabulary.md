---
id: TASK-1258
sequence_id: 1258
type: task
title: Stability and adopter docs for the overridable vocabulary
status: InReview
parent: FEAT-1249
author: tech-lead
assignee: tech-writer
priority: high
refs:
- ADR-1250:implements
- MILE-1241:targets
- TASK-1253:depends-on
- TASK-1254:depends-on
- TASK-1255:depends-on
description: stability.md tiers, adopter docs, heading key and the 0.19.0 CHANGELOG
  entries
subentities:
- local_id: ST1
  title: Stability tiers and adopter docs
  status: Done
  story: US7
- local_id: ST2
  title: Document the heading key
  status: Done
  story: US5
- local_id: ST3
  title: 0.19.0 CHANGELOG entries
  status: Done
  story: US7
created_at: '2026-10-29T19:55:13Z'
updated_at: '2026-10-29T23:56:14Z'
---
<!-- sq:body -->
## Goal

The stability contract, the adopter docs and the CHANGELOG describe the overridable vocabulary as delivered (ADR-1250, architect comment ed5d07a for the stability entries; FEAT-1249 US5 and US7 documentation).

## Scope

- `docs/stability.md`: Tier 1 "Sub-entity state lives in frontmatter" and "Frontmatter is flat"; Tier 2 aliases, the migrate sub-app's `rename-field`, bulk import's `add-<kind>`, `<kind>` selector and `maps_to`, a new badge-options entry; Tier 3 item rows, tree and graph nodes, sub-entity objects and display, the subentity-kinds catalog column.
- `docs/workflow.md`, `docs/overrides.md` (including the `heading` key on `[subentity_kinds.<kind>]` and the derived options), `docs/adoption.md` (one `add-<kind>` row).
- `CHANGELOG.md` 0.19.0 entries from the developers' handback reports, including the removed hidden `--priority` flag as a fix and the 0.19 schema migration.

## Expected files

- `docs/stability.md`, `docs/workflow.md`, `docs/overrides.md`, `docs/adoption.md`, `CHANGELOG.md`

## Working rules

- Work from the delivered behaviour: run the commands on the override test squad and a bundled squad (dev tree on a scratch squad under the session scratchpad), and read the developers' handback comments on this feature's tasks.
- Adopter docs describe the tool: no item IDs, no repository process, no history beyond the CHANGELOG and the migration step.
- `sq check` clean for the items you touched.

## Size

M.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1258 add-subtask "<title>"`; track with `sq task 1258 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Stability tiers and adopter docs

<!-- sq:subtask:ST1:body -->
`docs/stability.md` records the Tier 1, Tier 2 and Tier 3 entries listed in architect comment ed5d07a on ADR-1250, matching the delivered shapes, and `docs/workflow.md`, `docs/overrides.md` and `docs/adoption.md` match: derived `--<code>`, `--no-<code>` and `--min-<code>`; the mapping option named after the target kind; one `add-<kind>` row with the bundled kinds as examples.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Document the heading key

<!-- sq:subtask:ST2:body -->
`docs/overrides.md` documents the `heading` key on `[subentity_kinds.<kind>]` and its default, the title-cased `plural`.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — 0.19.0 CHANGELOG entries

<!-- sq:subtask:ST3:body -->
`CHANGELOG.md` 0.19.0 carries the adopter-visible changes reported by the developers: derived badge options and mapping option, reusable aliases of dropped types, import per declared kind, flat storage and the 0.19 schema migration, the new `--json` shapes, `sq migrate rename-field`, `sq check` on sub-entity keys, and the removed hidden `--priority` flag recorded as a fix.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T23:36:36Z] `tech-writer` Theo Writer:
  - - @manager Docs and CHANGELOG for the overridable vocabulary are in the working tree, uncommitted: `docs/stability.md`, `docs/overrides.md`, `docs/workflow.md`, `docs/adoption.md`, `docs/faq.md`, `docs/internals.md`, `CHANGELOG.md`, the repo `CLAUDE.md` outside the managed region, and one comment in `src/squads/_cli/_items.py`.
    - Every claim was checked by running the dev tree on scratch squads: a bundled one, one built from `tests/fixtures/override_squad`, and a 0.17 squad made by the released tool and migrated with `sq migrate up`. The refusal messages in the docs and CHANGELOG are copied from that output.
    - stability.md: Tier 1 sub-entity entries (flat, `maps_to`, attributes, the three stored spellings) and flat frontmatter (no `priority`/`severity` core keys). Tier 2: a new "Badge-field options" section, the alias table frozen for the bundled spec only, `rename-field` (with scopes) and `rename-kind` in the migrate sub-app, and the bulk-import `add-<kind>`, `<kind>` selector and `add-sub` `maps_to`/`fields`. Tier 3: the sub-entity object shape, `display.maps_to` and `maps_to_kind`, tree and graph nodes without `priority`, item rows, and the `subentity-kinds` catalog (`label`, `maps_to_parent`). Also the kind grammar, derived names and neutral grammar names under Project-level overrides.
    - overrides.md: a new "Sub-entity kinds" section (all keys, including `label` and `heading` with their defaults, mapping and target kind, stored spellings), derived options and the collision refusals under Collections, the badge column, the renamed validator, `subentity_kind_mismatch`, new rows in the load-refusal table, and alias reuse.
    - workflow.md: the "Renaming a badge field" and "Renaming a sub-entity kind" sections, alias resolution, and the derived options. adoption.md: one `add-<kind>` row plus the refusal example. CHANGELOG 0.19.0: a Migration section, Added entries, BREAKING entries first under Changed (with What to do), and two Fixed entries.
    - Two things in delivered behaviour look wrong (not doc issues): (1) the Click unknown-option suggestion now prints `No such option: --sorx ('(Possible options: --json, --sort)',)`, where 0.17.0 prints `(Possible options: --json, --sort)`; (2) on a bundled type, an override's kind `label` does not reach the option help (`--story` help still says `Story` with `label = "Need"`), although the table header and the show line do use it.
- [2026-10-29T23:56:14Z] `reviewer` Paul Reviewer:
  - Reviewed in REV-1259 (fifth pass): F29 (medium, subentity_kind_mismatch now runs by default) and F30 are for this task. The BREAKING entries and stability tiers hold when driven.
<!-- sq:discussion:end -->
