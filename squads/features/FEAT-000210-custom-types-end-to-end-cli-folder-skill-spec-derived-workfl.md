---
id: FEAT-000210
sequence_id: 210
type: feature
title: 'Custom types end-to-end: CLI, folder, skill, spec-derived workflow renderer'
status: InProgress
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
updated_at: '2026-06-30T12:35:16Z'
---
<!-- sq:body -->
## What this delivers

**F4 is the first user-visible value in this epic.** After F1–F3, the workflow is spec-driven and a project can write a custom type in `.overrides/workflow.toml`. F4 makes that custom type fully usable end-to-end: a `sq <custom-type>` CLI command is available, the folder is auto-created, items can be created and tracked, refs work, and the agents know about the new type because `sq workflow` and the managed CLAUDE.md section now render from the live spec.

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

1. A team that adds `[workflow.types.incident]` to `.overrides/workflow.toml` (with prefix, folder, machine) can run `sq incident create "…"` and `sq list -t incident` without any code change.
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
As a project admin, I want `sq <my-type> create`, `sq <my-type> show`, `sq <my-type> list`, `sq <my-type> update`, and related commands to work for any type I declared in `.overrides/workflow.toml`, so that my team can track custom-vocabulary items with the same CLI they use for built-in types.

**Acceptance:** after adding `[workflow.types.incident]` to `.overrides/workflow.toml`, `sq incident create "DB timeout" --author tech-lead` succeeds and `sq list -t incident` returns the item; IDs like `INC-000001` parse correctly; `sq check` is green.
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
- [2026-06-30T12:04:14Z] Olivia Lead:
  - **Breakdown into tasks (Olivia Lead).** FEAT-210 → 7 tasks, all left Draft. Sequence (depends-on edges recorded in frontmatter):
  - TASK-000256 — Characterization goldens FIRST (GATING): pin current `sq workflow`, CLAUDE.md + AGENTS.md workflow sections, and every bundled `sq-<type>` skill body, with roster/clock/flags frozen. No upstream deps; gates 257/260/261. (AC#7/#8 enforcement.)
  - TASK-000258 — Spec-aware folder/prefix mapping in `_paths` (+ spec-driven folder scaffold in `_service`). ID allocation already custom-tolerant (verified — confirm round-trip). (AC#2.)
  - TASK-000257 — Dynamic CLI build from spec: app-build loop iterates `spec.managed_types`, alias registration reads `ItemSpec.aliases`, `TYPE_ALIASES` retires. The startup-ordering crux. **BLOCKED ON ADR** (below). Depends 256, 258. (US1/AC#1.)
  - TASK-000259 — RESERVED_TYPES enforcement + meta-machinery robustness. The invariant is ALREADY enforced at spec-load (§5-6a/b); this confirms end-to-end + hardens PLAYBOOK/roster/lint against custom types. (Additive-only invariant.)
  - TASK-000262 — Lifecycle auto-linearization helper (BFS spine + side states), pure utility. Blocks 260, 261. (See FEAT-211 boundary below.)
  - TASK-000260 — Auto-generated thin `sq-<type>` skill, lexical-by-slug via the FEAT-178 primitive (Done). Depends 262, 258, 256. (US3/AC#5/#6.)
  - TASK-000261 — Spec-derived `sq workflow` renderer + CLAUDE.md/AGENTS.md section with the **static/dynamic split** (FEAT-013 ref-kinds/retype/remove-vs-cancel prose stays literal, never config-editable). Depends 262, 257, 256. (US2/US3/AC#3/#4.)
  - **Hard constraint placed in 257/260/261:** non-custom squads see byte-identical behaviour/output; the TASK-256 characterization golden gates each rewire (AC#7/#8).
  - **ADR VERDICT — YES, the startup-ordering change needs an ADR.** @architect input requested. The Typer app tree is built at IMPORT time, but custom type command NAMES come from a squad-dir-dependent spec resolved only inside the root `--dir` callback — which Click runs AFTER parsing argv and resolving the subcommand. So `sq incident …` is rejected by Click before the spec exists. FEAT-250 solved per-invocation *value parsing* (parse_type/parse_status on already-routed commands); it does NOT solve registering a new top-level command NAME ahead of Click's command resolution.
  - ADR scope: ≥3 viable approaches (resolve-spec-at-import; pre-scan argv for `--dir` in `main()` before building the tree; a lazy `TyperGroup.get_command` that registers an unknown-prefix sub-app on demand, à la the existing `AddressDispatchGroup`) + a behaviour question (how `sq <unknown>` behaves, how `--help` enumerates dynamic types before `--dir` resolves). Recommend the architect writes a short ADR before TASK-000257 starts; 256/258/259/262 proceed in parallel meanwhile.
  - **FEAT-178 coordination:** Done — the lexical-by-slug SKILL allocator (`bundled_skill_slugs()` + `seed_bundled_skills`) already exists. TASK-000260 EXTENDS that slug set for custom types; it does NOT build a new allocator (AC#6 = no SKILL-id churn).
  - **FEAT-211 seam (deconflict):** 'lifecycle auto-linearization' appears in BOTH FEAT-210 (slice 6) and FEAT-211's scope; FEAT-211 depends-on FEAT-210. Resolution: TASK-000262 builds the core BFS-spine helper (F4 needs it to render at all); FEAT-211 CONSUMES + HARDENS it across status surfaces (filters/inbox/blocked/badge fallback for custom statuses). Boundary recorded in 262 + 261 bodies.
  - **Risks:** (1) import-time vs parse-time ordering (the ADR subject) — highest, all of 257 hinges on it. (2) golden drift in 262: built-in derived lifecycle strings must reconcile with the PLAYBOOK prose the golden captures — resolve explicitly. (3) two-backend coverage (CLAUDE.md AND AGENTS.md) in 261 — easy to miss agents_md. (4) `_paths` import-cycle risk in 258 — prefer threading the spec from the caller over a second filesystem load.
- [2026-06-30T12:17:31Z] Nina Product:
  - Workflow-override location reconciliation pass complete (Nina Product). This is the same fix applied to FEAT-000209 on 2026-06-30 — the factual error '.squads.toml' as the workflow override location was still present in FEAT-000210, FEAT-000211, FEAT-000212, and EPIC-000206.
  - Changes made (surgical — only workflow-override-location references; all general .squads.toml config references left intact):
  - FEAT-000210 body (2 hits): 'a project can write a custom type in .squads.toml' → '.overrides/workflow.toml'; AC#1 '[workflow.types.incident] to .squads.toml' → '.overrides/workflow.toml'.
  - FEAT-000210 US1 body (2 hits): 'declared in .squads.toml' → '.overrides/workflow.toml'; acceptance '[workflow.types.incident] to .squads.toml' → '.overrides/workflow.toml'.
  - FEAT-000211 body (1 hit): AC#1 'custom status Triage declared in .squads.toml' → '.overrides/workflow.toml'.
  - FEAT-000212 US1 body (1 hit): 'declare a custom sub-entity kind in .squads.toml' → '.overrides/workflow.toml'.
  - EPIC-000206 body (1 hit): success criterion #1 'entirely in .squads.toml' → '.overrides/workflow.toml'.
  - Left unchanged — confirmed legitimate: ADR-000214 line re ADR-000179's .squads.toml knobs (global ID prefix / flat-layout — general project config, not the workflow override). FEAT-000209 hits are all in immutable discussion comments (reviewer/QA records); the 209 body/stories were already corrected in the earlier pass.
- [2026-06-30T12:35:16Z] Elias Python:
  - @manager: TASK-000258, TASK-000259, and TASK-000262 are Done. All gates clean (pyright 0 errors, ruff check clean, ruff format clean). 72 new tests, all passing in under 1 second.
  - TASK-258 (_paths.py spec-aware): folder_for/squad_relative/type_for_id accept optional spec= arg; builtins are byte-identical (AC#7 confirmed); custom types dispatch through spec.items[type].folder / spec.prefix_to_type. Import of WorkflowSpec in _paths.py is safe — no cycle. _iter_item_files() widened to yield str (not ItemType) to support custom folder scans.
  - TASK-259 (RESERVED_TYPES): the invariant was already fail-closed; tests prove it parametrically for all ItemType members and 12 floor statuses. Graceful degradation confirmed (no KeyError for custom work types absent from PLAYBOOK).
  - TASK-262 (linearize_lifecycle): signature is linearize_lifecycle(machine: Lifecycle) -> str, exported from squads._workflow. Algorithm is greedy spine + BFS side states. One option-b divergence on the review lifecycle is documented in both the test and the function docstring.
  - Risky/notable: the _iter_item_files() type change touches repair/renumber — existing tests for those paths still pass. Custom type write/repair round-trips bypass create() (no template yet, that's TASK-260); tests use write_new() + manual index transaction directly.
<!-- sq:discussion:end -->
