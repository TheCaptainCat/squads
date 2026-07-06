---
id: TASK-227
sequence_id: 227
type: task
title: Build PlaybookSpec/ItemPlaybookSpec/RoleGuideSpec models and author bundled
  playbook.toml
status: Done
parent: FEAT-220
author: tech-lead
subentities:
- local_id: ST1
  title: PlaybookSpec/ItemPlaybookSpec/RoleGuideSpec models, extra=forbid, ordered
    guides
  status: Todo
  story: US1
- local_id: ST2
  title: Author bundled playbook.toml transcribing today's 7 work-type entries
  status: Todo
  story: US1
created_at: '2026-06-26T08:04:10Z'
updated_at: '2026-07-06T15:20:58Z'
---
<!-- sq:body -->
## Goal

Build the pyright-strict `PlaybookSpec` / `ItemPlaybookSpec` / `RoleGuideSpec` pydantic v2 value
objects per ADR-226 §1, and author the bundled `playbook.toml` encoding today's EXACT `PLAYBOOK`.
Data + shape foundation for FEAT-220 (FP). Playbook-content externalization only, enums-intact era.

**Apply `extra="forbid"` on every model from the start** — this is the FEAT-219 nit lesson; a typo'd
TOML key must error, not be silently dropped.

Sequence: **first** task. The loader/rewire (TASK-228) and two-layer golden-lock (TASK-229) both
consume these models and this TOML.

## What to build

- **Models (ADR §1 shape, pyright-strict, `model_config = ConfigDict(extra="forbid")`):**
  - `PlaybookSpec`: `types: dict[ItemType, ItemPlaybookSpec]` (keyed by item type; work types only).
  - `ItemPlaybookSpec`: `overview: str`, `lifecycle: str` (human lifecycle line),
    `commands: list[str]`, `roles: list[RoleGuideSpec]` — **ORDERED** (section order in the generated
    skill is significant).
  - `RoleGuideSpec`: `slug: str` (a role slug, or the `*dev` DEV sentinel), `enter: list[str] = []`,
    `do: list[str] = []`, `handoff: list[str] = []`, `watch: list[str] = []`.
  - Today's `RoleGuide` uses `tuple[str, ...]`; the spec uses `list[str]` (TOML arrays). The golden
    compares by value so ordering/content are preserved.
- **Bundled TOML** at `src/squads/_interactions/playbook.toml` — promote `_interactions.py` into an
  `_interactions/` package (`__init__.py` re-exporting current public names so import sites are
  unchanged), TOML beside the loader. Shipped as package data (swept into the wheel by
  `packages = ["src/squads"]`; packaging *verification* is TASK-229). Encode, **transcribed not
  paraphrased**, every current `ItemPlaybook` entry for the **7 work types** (task, bug, feature,
  epic, decision, review, guide), each with overview / lifecycle / commands and its ORDERED per-role
  guides including the `*dev` sentinel. Use **array-of-tables** (`[[types.<t>.roles]]`) to preserve
  role-guide order; absent guide sections default to empty lists.
  - Note for implementer: read values directly from `_interactions.py`'s `PLAYBOOK` — preserve exact
    string content (backticks, `@mentions`, `sq …` snippets). The meta types role/skill/operator are
    deliberately ABSENT today — do not invent entries for them.
- The `DEV = "*dev"` sentinel is carried through as a literal slug value (resolved to "developers" at
  render time) — exempt from the role-catalog slug check (that's TASK-228's validation).

## Design constraints (ADR-226)

- §1 shape exactly; `extra="forbid"`; work types only (meta types absent). Enums-intact: no custom
  types, no de-typing, no overrides. `CREATE_LANES`/`LANED_TYPES` stay in Python (out of scope).

## Acceptance

1. `PlaybookSpec`/`ItemPlaybookSpec`/`RoleGuideSpec` exist, pyright-strict-clean, `extra="forbid"`,
   role guides ordered (list, not set).
2. `src/squads/_interactions/playbook.toml` exists encoding all 7 work-type entries with ordered
   per-role guides incl. `*dev`; `_interactions.py` promoted to `_interactions/` package with
   re-exported names (import sites unchanged).
3. `tomllib`-parseable; round-trips into the models without error.
4. pyright/ruff clean. (Equality-with-today + byte-identical skill output asserted by TASK-229.)
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 227 add-subtask "<title>"`; track with `sq task 227 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | PlaybookSpec/ItemPlaybookSpec/RoleGuideSpec models, extra=forbid, ordered guides | US1 |
| ST2 | Todo |  | Author bundled playbook.toml transcribing today's 7 work-type entries | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — PlaybookSpec/ItemPlaybookSpec/RoleGuideSpec models, extra=forbid, ordered guides

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — As a maintainer, I want the PLAYBOOK loaded from playbook.toml so skill content lives in data not code
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Covers the pyright-strict pydantic v2 playbook value objects per ADR-226 §1, all with `model_config = ConfigDict(extra="forbid")` (the FEAT-219 nit lesson): `PlaybookSpec` (`types: dict[ItemType, ItemPlaybookSpec]`, work types only), `ItemPlaybookSpec` (overview/lifecycle/commands + ORDERED `roles: list[RoleGuideSpec]`), and `RoleGuideSpec` (slug or the `*dev` sentinel + enter/do/handoff/watch lists). Guides are lists, not sets, so section order in the generated skill is preserved. (US1)
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Author bundled playbook.toml transcribing today's 7 work-type entries

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US1 — As a maintainer, I want the PLAYBOOK loaded from playbook.toml so skill content lives in data not code
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Covers authoring the bundled `src/squads/_interactions/playbook.toml` — promoting `_interactions.py` into an `_interactions/` package (re-exporting current public names so import sites are unchanged) with the TOML beside the loader. Transcribes (not paraphrases) today's `PLAYBOOK` for all 7 work types (task/bug/feature/epic/decision/review/guide) with overview/lifecycle/commands and each type's ORDERED per-role guides (incl. the `*dev` sentinel) via array-of-tables. Meta types role/skill/operator stay deliberately absent. (US1)
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
