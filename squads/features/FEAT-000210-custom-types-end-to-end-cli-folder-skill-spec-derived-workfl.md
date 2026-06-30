---
id: FEAT-000210
sequence_id: 210
type: feature
title: 'Custom types end-to-end: CLI, folder, skill, spec-derived workflow renderer'
status: Ready
parent: EPIC-000206
author: product-owner
refs:
- FEAT-000209:depends-on
- FEAT-000220
- FEAT-000250:depends-on
subentities:
- local_id: US1
  title: As a project admin, I want sq <my-type> create/list/show/update to work for
    a type I defined in TOML
  status: Todo
- local_id: US2
  title: As a project admin, I want sq workflow to show my custom type and its lifecycle
    in the team cheatsheet
  status: Todo
- local_id: US3
  title: AI agents learn custom vocab from CLAUDE.md after sq sync
  status: Todo
created_at: '2026-06-25T13:19:37Z'
updated_at: '2026-06-30T09:52:57Z'
---
<!-- sq:body -->
## What this delivers

**F4 is the first user-visible value in this epic.** After F1–F3, the workflow is spec-driven and a project can write a custom type in `.squads.toml`. F4 makes that custom type fully usable end-to-end: a `sq <custom-type>` CLI command is available, the folder is auto-created, items can be created and tracked, refs work, and the agents know about the new type because `sq workflow` and the managed CLAUDE.md section now render from the live spec.

A team that adds an `incident` type will see `sq incident create "DB timeout"` work, `sq list -t incident` return results, `sq workflow` list the incident lifecycle, and their AI agent context (CLAUDE.md) reflect the custom type after `sq sync`.

**Minimum-viable custom type scope:** prefix + folder + state machine + optional parent rules/aliases/badges + auto-generated thin `sq-<type>` skill. Brand-new sub-entity kinds are explicitly out of scope for this feature (see F6).

## Scope

### Dynamic CLI build from spec
The `for _type in WORK_TYPES` app-build loop in `_cli/__init__.py` must iterate `spec.managed_types()` instead of a static tuple. This means the `WorkflowSpec` must be loaded before the CLI app tree is built — a startup-ordering change from today's lazy-per-command config load. Custom types register their `sq <type>` Typer app (with `create`, `show`, `list`, `update`, `status`, `ref`, `comment`, `body`, `remove`, `retype`) dynamically at startup.

### Folder and prefix management
Auto-create the type's folder (`agents/skills/` analog but for custom types) if it does not exist. Register the prefix→type reverse mapping in the spec so IDs like `INC-000001` parse correctly. Enforce prefix and folder uniqueness at spec-load time (F3's validator covers this).

### ID allocation
Custom types allocate IDs through `IndexStore.transaction()` like every built-in type. No special path.

### Auto-generated `sq-<type>` skill
Each managed custom type gets a thin auto-generated `sq-<type>` skill (via `_write_item_skills`) containing: the lifecycle string (auto-derived from the spec's state machine), the basic command list, and any declared role interactions. Rich per-role playbook sections are not auto-generated (graceful degradation — the custom type skill is thinner than built-in skills but functional). This mints new SKILL items using the lexical-by-slug allocation shared with FEAT-000178.

### Spec-derived `sq workflow` renderer and CLAUDE.md section
`sq workflow` renders the live loaded spec instead of the static `workflow.md.j2` template. This means custom types and their lifecycles appear in the team cheatsheet. The renderer must **split**: spec-rendered machine/type/alias sections versus the static FEAT-000013 stability-contract prose (ref-kinds table, retype, remove-vs-cancel), which must never become config-editable.

`sq sync` regenerates the managed CLAUDE.md/AGENTS.md workflow section from the live spec, so agents always see current custom vocabulary.

### Lifecycle auto-linearization
Auto-derive a readable `A → B → C (+ D, E)` lifecycle string from an arbitrary transition graph for rendering. The heuristic: BFS from initial state for the "happy path" spine; remaining states as "(+ side states)".

## Dependencies

Requires F3 (FEAT-000209). The additive-only override must be in place so a custom type can be declared in config before the CLI tries to build an app for it.

Also interacts with FEAT-000178 (skill ID allocation for new managed types).

## Acceptance criteria

1. A team that adds `[workflow.types.incident]` to `.squads.toml` (with prefix, folder, machine) can run `sq incident create "…"` and `sq list -t incident` without any code change.
2. The custom type's folder is auto-created; IDs (`INC-000001`) parse correctly.
3. `sq workflow` renders a spec-derived cheatsheet that includes the custom type's lifecycle; the FEAT-000013 stability-contract prose sections remain static.
4. `sq sync` regenerates CLAUDE.md and the `squads` skill to reflect the custom type.
5. A thin `sq-incident` skill is auto-generated with the correct lifecycle string and command list.
6. No SKILL-id churn: the new managed-type skill is allocated in lexical-by-slug order consistent with FEAT-000178.
7. Existing (non-custom) squads see no change in behavior or rendered output.
8. The F1 golden test remains green.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 210 add-story "As a <role>, I want … so that …"`; track with `sq feature 210 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a project admin, I want sq <my-type> create/list/show/update to work for a type I defined in TOML |
| US2 | Todo |  | As a project admin, I want sq workflow to show my custom type and its lifecycle in the team cheatsheet |
| US3 | Todo |  | AI agents learn custom vocab from CLAUDE.md after sq sync |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a project admin, I want sq <my-type> create/list/show/update to work for a type I defined in TOML

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a project admin, I want `sq <my-type> create`, `sq <my-type> show`, `sq <my-type> list`, `sq <my-type> update`, and related commands to work for any type I declared in `.squads.toml`, so that my team can track custom-vocabulary items with the same CLI they use for built-in types.

**Acceptance:** after adding `[workflow.types.incident]` to `.squads.toml`, `sq incident create "DB timeout" --author tech-lead` succeeds and `sq list -t incident` returns the item; IDs like `INC-000001` parse correctly; `sq check` is green.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a project admin, I want sq workflow to show my custom type and its lifecycle in the team cheatsheet

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a project admin, I want `sq workflow` to render a live cheatsheet that includes my custom types and their state machine lifecycles, so the team always sees the current vocabulary.

**Acceptance:** `sq workflow` output includes the custom type's prefix, lifecycle string (auto-linearized from the machine), and aliases. The FEAT-000013 stability-contract sections (ref-kinds, retype, remove-vs-cancel) remain static and unchanged.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — AI agents learn custom vocab from CLAUDE.md after sq sync

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As an AI agent working in a squad with custom types, I want the managed CLAUDE.md workflow section and my `squads` skill to reflect the custom vocabulary after `sq sync`, so I know what types and lifecycles are available without reading the TOML directly.

**Acceptance:** running `sq sync` on a squad with a custom `incident` type regenerates the CLAUDE.md workflow section to include `incident`; a thin `sq-incident` skill is generated with the correct lifecycle and command list.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-26T07:31:05Z] Catherine Manager:
  - Design constraint (from op-pierre): custom types are ADDITIVE over the reserved core — a project may add types but may NOT drop the reserved meta-types (role/skill/operator) that the role backend / skill generation / operator machinery depend on. Enforce via the RESERVED_TYPES invariant introduced in FEAT-000208.
- [2026-06-26T09:44:13Z] Catherine Manager:
  - Process rule (from the FEAT-220 incident, REV-000230): for externalize/refactor-with-byte-identical-output work, the characterization golden must be authored FIRST — against HEAD, as a gating test — BEFORE the rewire, so the change runs under a passing guard rather than leaving the proof as a last task an agent can abandon. Pin ALL inputs (roster/flags/clock) for generated-artifact comparisons. See [[pin-roster-when-diffing-generated-skills]].
- [2026-06-26T15:22:23Z] Catherine Manager:
  - Implementation note (carry-forward from FEAT-208): the dynamic CLI build must source per-type ALIASES from the spec too, not just the type set. FEAT-208 added the aliases flag to TypeSpec (and encoded the built-in aliases as values in default_workflow.toml), but nothing consumes it yet — the alias registration in _cli/__init__.py still reads the hardcoded TYPE_ALIASES dict in _enums.py. So the dynamic build has two enum->spec swaps, not one: (1) the app-build loop iterates the loaded spec types instead of `for t in ItemType`, and (2) alias sub-app registration reads each TypeSpec.aliases instead of TYPE_ALIASES. After this, TYPE_ALIASES can be retired (its values now live in the spec). Same startup-ordering caveat applies (spec loaded before the app tree is built).
<!-- sq:discussion:end -->
