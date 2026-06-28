---
id: FEAT-000209
sequence_id: 209
type: feature
title: Project override of workflow spec (additive-only) + sq workflow lint
status: Draft
parent: EPIC-000206
author: product-owner
refs:
- FEAT-000208:depends-on
subentities:
- local_id: US1
  title: Project admin can add custom types and statuses via .squads.toml
  status: Todo
- local_id: US2
  title: As a project admin, I want sq workflow lint to validate my spec config and
    report every error clearly before I commit it
  status: Todo
- local_id: US3
  title: Broken workflow spec hard-stops sq with a clear actionable error
  status: Todo
created_at: '2026-06-25T13:18:46Z'
updated_at: '2026-06-26T09:27:26Z'
---
<!-- sq:body -->
## What this delivers

After F1 and F2, the workflow is spec-driven and the models accept string-typed vocabulary. F3 is the first feature a project admin actually uses: it lets a team extend squads' vocabulary by writing a `[workflow.*]` block in `.squads.toml` (or a sibling `.squads.workflow.toml`) that is merged over the bundled default.

In v1 the override is **additive-only**: a project may add new types, statuses, and machines — it may not silently mutate a built-in type's state machine or remove built-in vocabulary. This keeps the compat contract simple and the risk manageable; full replace-semantics are explicitly deferred.

F3 also ships `sq workflow lint`, the friendly, verbose validation surface for authors editing the spec. It runs the same `WorkflowSpec.validate()` that `open_service` runs fail-closed, but prints every error and warning with context rather than aborting.

**This is the first feature with a project-admin user story** — a real person can now write TOML that changes what squads knows, and get actionable feedback if the config is wrong.

## Scope

- Implement the config loader merge: load bundled default, then merge the project's `[workflow.*]` block (from `.squads.toml` or the sibling override file) additively. Additive-only semantics: new keys are accepted; shadowing an existing built-in type/status/machine raises a `SquadsError` at load time.
- Reuse the existing `_overrides/` + `sq override` machinery: the workflow spec becomes the third overridable artifact (alongside templates and roles). `sq override scaffold workflow` scaffolds a starter config; `sq override diff workflow` shows project deviation from the bundled default; `sq override drift workflow` detects staleness.
- Implement **load-time fail-closed validation** in `WorkflowSpec.validate()`: invalid transitions, missing machine references, non-unique prefixes/folders/aliases, parent-cycle detection, and removal of a status/type still referenced by live index items (cross-checks `.squads.json`). A broken spec hard-stops with a `SquadsError` and a clear "run `sq workflow lint` to see details" message.
- Implement `sq workflow lint` as a new verb under `sq workflow`: runs `WorkflowSpec.validate()` in verbose mode, printing every error and warning with line context and a fix suggestion. Reports "OK" when clean.
- `sq check` calls `WorkflowSpec.validate()` and surfaces a one-line "workflow config invalid — run `sq workflow lint`" if it fails, rather than silently passing.
- Documentation: `sq docs workflow` covers the override format, additive-only rules, and a worked example.

## Dependencies

Requires F2 (FEAT-000208). The model must accept string-typed vocabulary before an override spec can introduce new vocabulary strings.

## Acceptance criteria

1. A project admin can add a `[workflow.types.incident]` block in `.squads.toml` and `open_service` merges it over the bundled default without error.
2. Attempting to redefine a built-in type's state machine in the override raises a clear `SquadsError` at load time.
3. `sq workflow lint` reports every validation error with actionable context; exits 0 on a clean spec.
4. `sq check` surfaces a one-line warning when the workflow spec is invalid.
5. Removing a status from the override that is still in use by live index items fails closed with a list of offending items.
6. `sq override scaffold workflow` / `diff workflow` / `drift workflow` work for the workflow artifact.
7. The F1 golden test remains green (default behavior unchanged for squads with no override).
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 209 add-story "As a <role>, I want … so that …"`; track with `sq feature 209 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Project admin can add custom types and statuses via .squads.toml |
| US2 | Todo |  | As a project admin, I want sq workflow lint to validate my spec config and report every error clearly before I commit it |
| US3 | Todo |  | Broken workflow spec hard-stops sq with a clear actionable error |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Project admin can add custom types and statuses via .squads.toml

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a project admin, I want to add new item types, statuses, and state machines in a `[workflow.*]` block in `.squads.toml`, so that my team can use custom vocabulary (e.g. an `incident` type with `Triage → Mitigating → Resolved`) without forking squads or writing Python.

**Acceptance:** a `[workflow.types.incident]` block added to `.squads.toml` is merged addively over the bundled default; `sq list -t incident` works; attempting to redefine `task`'s machine raises a clear error.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a project admin, I want sq workflow lint to validate my spec config and report every error clearly before I commit it

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a project admin, I want `sq workflow lint` to validate my override spec and print every error and warning with context, so I can fix config problems before they reach the team.

**Acceptance:** `sq workflow lint` exits 0 on a valid spec with an OK message; on an invalid spec it prints each error with the offending config key and a fix hint; exit code 1.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Broken workflow spec hard-stops sq with a clear actionable error

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As a team member using a squad with a custom workflow, I want a broken spec to hard-stop `sq` with an actionable error message rather than silently running with invalid configuration.

**Acceptance:** a spec that fails `WorkflowSpec.validate()` causes `open_service` to raise `SquadsError` with a message pointing to `sq workflow lint`; no command proceeds with an invalid spec.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-26T09:27:26Z] Catherine Manager:
  - Prereq surfaced in REV-000230 (FEAT-220): the FEAT-207 workflow spec models (_workflow/_models.py: WorkflowSpec/ItemSpec/StatusSpec/Lifecycle) carry only ConfigDict(frozen=True) — NO extra='forbid' — so a typo'd key in the workflow TOML is SILENTLY IGNORED (verified: ItemSpec accepts a bogus key). Fine for the golden-locked bundled default, but THIS feature makes the workflow TOML project-editable, so add extra='forbid' to those models (+ route the loader through model_validate) for fail-closed parity with the now-hardened roles/playbook loaders. Do it as part of (or before) this feature.
<!-- sq:discussion:end -->
