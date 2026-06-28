---
id: FEAT-000207
sequence_id: 207
type: feature
title: Externalize hardcoded workflow into a bundled spec (enums intact)
status: Done
parent: EPIC-000206
author: product-owner
subentities:
- local_id: US1
  title: As a maintainer, I want workflow spec loaded from TOML so behavior is in
    data not code
  status: Todo
- local_id: US2
  title: As a maintainer, I want a golden test asserting default spec == today's behavior
    so regressions are caught immediately
  status: Todo
created_at: '2026-06-25T13:17:00Z'
updated_at: '2026-06-25T15:17:09Z'
---
<!-- sq:body -->
## What this delivers

Today the entire workflow vocabulary — type state machines, the terminal set, parent rules, prefix/folder/alias mappings, and status badges — is scattered across hardcoded Python in `_workflow.py` and `_models/_enums.py`. There is no single "what the workflow is" artifact; knowledge is implicit in enum declarations and dict literals.

F1 creates that artifact: a single loaded, validated **`WorkflowSpec`** value object built from a bundled-default TOML file. The enums are **not changed** in this feature — they remain and are used to generate the bundled default. This feature is the de-risking foundation for the entire epic.

**This feature delivers no user-visible change.** Any squad that runs after F1 ships sees behavior identical to before. That is the point: the golden-locked test proves that the externalization is behavior-preserving before any custom vocabulary is attempted.

## Scope

- Design and implement the `WorkflowSpec`, `TypeSpec`, `StatusSpec`, and `StateMachine` pydantic value objects (pyright-strict, no new fields beyond what `_workflow.py`/`_enums.py` already express).
- Author a **bundled-default TOML** (under `_rendering/` or `_workflow/`, shipped as package data) that encodes every current type, status, state machine, terminal marker, parent rule, alias, prefix, folder, and badge in config. The TOML is the single source of truth from this point forward for what the default workflow is.
- Make the existing free functions (`can_transition`, `workflow_for`, `initial_status`, `parent_allowed`, `is_open`, `parent_hint`, `TERMINAL`) callable as methods on `WorkflowSpec` — the free-function interface survives as thin shims during the transition so call sites do not break wholesale.
- Load the spec once per `Service` instantiation and pass it explicitly to all surfaces that today import `_workflow`/`_enums` tables directly.
- **Golden test:** assert that the loaded default `WorkflowSpec` equals a frozen snapshot of today's enum/workflow state. This test is the regression gate for every subsequent feature — if any later change accidentally shifts the default, the golden fails.
- `uv run pyright && ruff && pytest` all pass with no behavioral regressions.

## Dependencies and sequencing

F1 is the first feature. It unblocks F2 (de-typing). No prior feature is required.

The spike gate (see EPIC-000206) covers F1+F2 together: do not commit either to implementation until the throwaway spike proves the de-typing path is clean under pyright-strict.

## Acceptance criteria

1. A `WorkflowSpec` value object (pydantic, pyright-strict) exists and is loaded from the bundled-default TOML at `Service` init time.
2. The golden test passes: loaded default spec == frozen snapshot of today's `WORKFLOWS`, `TERMINAL`, `ALLOWED_PARENTS`, `PREFIX_BY_TYPE`, `FOLDER_BY_TYPE`, `TYPE_ALIASES`, `STATUS_EMOJI`.
3. All existing tests pass unchanged — no behavioral difference for any existing squad or command.
4. `sq workflow` output is unchanged (still renders the same cheatsheet).
5. `uv run pyright && uv run ruff check . && uv run pytest` all green.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 207 add-story "As a <role>, I want … so that …"`; track with `sq feature 207 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a maintainer, I want workflow spec loaded from TOML so behavior is in data not code |
| US2 | Todo |  | As a maintainer, I want a golden test asserting default spec == today's behavior so regressions are caught immediately |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a maintainer, I want workflow spec loaded from TOML so behavior is in data not code

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a squads maintainer, I want the entire workflow definition (types, state machines, statuses, parent rules, prefixes, folders, aliases, badges) loaded from a bundled TOML file at runtime, so that workflow knowledge lives in data rather than scattered Python enum declarations and dict literals.

**Acceptance:** a `WorkflowSpec` pydantic value object loads from a bundled-default TOML; the spec exposes `can_transition`, `parent_allowed`, `is_open`, `managed_types` and equivalents as typed methods; all existing tests pass.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a maintainer, I want a golden test asserting default spec == today's behavior so regressions are caught immediately

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a squads maintainer, I want a golden test that asserts the loaded default `WorkflowSpec` is identical to a frozen snapshot of today's `WORKFLOWS`, `TERMINAL`, `ALLOWED_PARENTS`, and enum dicts, so that any accidental behavioral drift in the default is caught immediately as a test failure.

**Acceptance:** the golden test exists, is CI-enforced, and fails if any type/status/machine/terminal/parent-rule/badge in the default spec differs from the snapshot. It must remain green throughout F2–F5.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-25T14:20:50Z] Catherine Manager:
  - ADR-000214 accepted; FEAT-000207 → Ready. Building F1 full loop (Pierre greenlit). Scope reminder for the breakdown: externalize the workflow into a bundled WorkflowSpec loaded from default_workflow.toml, ItemType/Status enums STAY (spec coerced/validated against them, must equal not extend), golden-lock test that the loaded default == today's exact behavior. NO de-typing/overrides/custom-vocab (F2/F3/F4).
<!-- sq:discussion:end -->
