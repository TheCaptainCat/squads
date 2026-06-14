---
id: TASK-000091
sequence_id: 91
type: task
title: Document the override mechanism + add override layout to the 1.0 contract doc
status: Done
parent: FEAT-000014
author: tech-lead
priority: medium
description: Docs/guide for overrides + naming; list the .overrides layout among the
  durable surfaces in the FEAT-13 contract doc
subentities:
- local_id: ST1
  title: Document override + naming mechanism in guide/skill surface
  status: Done
  story: US3
- local_id: ST2
  title: List the .overrides layout among durable surfaces in the contract doc
  status: Done
  story: US3
created_at: '2026-06-12T20:57:40Z'
updated_at: '2026-06-12T22:05:47Z'
---
<!-- sq:body -->
Docs + contract task for FEAT-000014 (feature Acceptance: 'sq check/docs explain the mechanism' and 'the contract doc lists the override layout among the durable surfaces'; ADR-000085 §5).

**Goal.** Explain the override + naming mechanism to teams, and freeze the contracted surfaces verbatim in the FEAT-000013 durable-contract doc.

**Scope — docs.** Document, in the appropriate guide/skill surface: the `.overrides/{templates,roles}/` layout and per-file precedence; the `sq override` workflow (scaffold → edit → `sq check` warns on drift → `sq override diff` two deltas → hand-merge → `sq override update` re-stamp); and the naming surface (`--name slug=…`, `[init.names]`, TTY prompt/`--default-names`, `extra.full_name`, canonical non-renamable slugs).

**Scope — contract doc (ADR §5, verbatim).** Add to the FEAT-000013 contract doc: (1) the override root + tree `<squad-dir>/.overrides/{templates,roles}/` (templates mirror bundled names 1:1, roles as `<slug>.toml`); (2) the precedence rule (per-file, project → bundled; presence is the override; templates whole-file, roles merge field-wise by slug); (3) the staleness+update contract (`squads:override-base:<version>` stamp; `sq check` warns on version drift / errors on missing markers; valid overrides always render; `sq migrate` never rewrites; the `sq override` group — scaffold/diff/update/list — as the entire upgrade path, incl. diff's two deltas and update's re-stamp); (4) the naming contract (names in `extra.full_name`, canonical slugs, pool fallback, the init naming surface). Note what is **deliberately NOT** frozen: additional `.overrides/` categories, and the exact prompt wording/layout.

**Acceptance.** The mechanism is documented where users will find it; the contract doc lists the four frozen surfaces above. Co-author with @architect (the contract-doc owner).

**Dependencies.** Should land LAST — after T1–T4 so the documented behaviour matches what shipped. Depends on the contract doc existing (FEAT-000013).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 91 add-subtask "<title>"`; track with `sq task 91 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Document override + naming mechanism in guide/skill surface | US3 |
| ST2 | Done |  | List the .overrides layout among durable surfaces in the contract doc | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Document override + naming mechanism in guide/skill surface

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US3 — As a maintainer upgrading squads, I want defined precedence and staleness behaviour for my overrides, so that an upgrade never silently breaks them
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — List the .overrides layout among durable surfaces in the contract doc

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US3 — As a maintainer upgrading squads, I want defined precedence and staleness behaviour for my overrides, so that an upgrade never silently breaks them
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T22:05:47Z] Theo Writer:
  - Complete: wrote docs/overrides.md (ST1) covering .overrides/ layout, precedence, staleness detection, the sq override command workflow, and agent naming at init. Accessible via 'sq docs overrides' and linked from docs/README.md. All CLI surfaces verified against shipped code.
  - Contract doc deferral complete (ST2): confirmed FEAT-000013 has the four override contract surfaces from TASK-089 (Elias, 2026-06-12T21:54:21Z), added tech-writer comment flagging that docs/overrides.md now documents these for users. Ready for FEAT-000013 author to synthesize into the stability.md tier when writing that feature.
<!-- sq:discussion:end -->
