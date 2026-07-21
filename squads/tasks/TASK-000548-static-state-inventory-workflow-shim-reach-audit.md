---
id: TASK-548
sequence_id: 548
type: task
title: Static-state inventory + workflow-shim reach audit
status: Done
parent: FEAT-533
author: tech-lead
assignee: python-dev
description: 'US1: definitive data-vs-code triage of engine module-level bindings;
  audit-only shim confirmation'
created_at: '2026-07-21T21:33:12Z'
updated_at: '2026-07-21T22:07:40Z'
---
<!-- sq:body -->
Implements FEAT-533 **US1** (inventory half). ADR-534 is the rule this proves against.

## Scope

Produce the definitive **data-vs-code triage** of every module-level binding in the engine,
each classified **data** (must become per-request) or **code/definition** (may stay,
allowlisted). The classification is the durable artifact the US1 guard (TASK-549) enforces
against, and the triage rule it documents.

Cover at least:

- `_clock.py::_override` → **data** (forged/frozen time).
- `_actor.py::_override`, `_session_id`, `_parent_session_id` → **data** (attribution + lineage).
- `_cli/_common.py::_active_spec`, `_active_dir` → **data** (active squad spec + resolved dir).
- `_paths.py::resolve()` / `find_config()` `Path.cwd()` default → **data** (client cwd is an input).
- `_backends/_registry.py::_REGISTRY`, `_loaded` + the import-time `register()` side-effect
  in `_backends/_claude_code/__init__.py` → **code** (backend classes, instantiated fresh).
- `_workflow/__init__.py::_BUNDLED_SPEC` + derived `WORKFLOWS`, `SUBENTITY_WORKFLOWS`,
  `ALLOWED_PARENTS`, `TERMINAL` + the free-function shims → **code** (immutable bundled default).
- `_roles/_catalog.py::_CATALOG`, `_BY_SLUG`, `_PREDEFINED_BY_SLUG` → **code**.
- `_interactions/__init__.py::_PLAYBOOK_SPEC` → **code**.
- `_cli/_create.py::_create_spec`; `_cli/__init__.py::_spec`, `_STATIC_TYPES` → **code** (bundled).
- `_rendering/_engine.py::_env_cache` → **code** (per-squad compiled Jinja envs; resource-bounded
  by TASK-554, not a correctness offender).
- `_overrides/_manifest.py::_manifest_cache` → **code**.

## Workflow-shim reach is AUDIT-ONLY here

Confirm — by grep over `src/` — that **no production caller** reaches the module-level
free-function shims (`workflow.can_transition()`, `is_open`, `parent_allowed`, …) or the derived
constants (`WORKFLOWS`/`SUBENTITY_WORKFLOWS`/`ALLOWED_PARENTS`/`TERMINAL`) as if they were the
*active* spec. Expected finding: only the golden-lock tests reference them; the service layer
routes through `Service.spec` and the CLI edge through `get_active_spec()`. Record the grep and
its result.

Do **not** reroute anything. The customization-exposed reroute (honouring a customized squad's
own vocabulary off `WORKFLOWS`/`ALLOWED_PARENTS`/`TERMINAL`/`_PLAYBOOK_SPEC`) is a consumer audit
owned by EPIC-538, explicitly out of scope for this feature.

## Deliverable

The triage classification + the one grep-audit result, delivered as the task's handoff (a comment
on this task and/or feeding TASK-549's docstring/allowlist). No code change lands here.

## Acceptance

- Every binding above is classified data or code with a one-line reason.
- The grep audit is recorded and shows zero production consumers of the bundled workflow
  shims/constants as an active spec (or, if any is found, it is named for TASK-552 to route).
- The sanctioned-code allowlist for TASK-549 is enumerated exactly (the code-classified bindings).

## Dependencies / order

First task in the feature — no code prerequisites. Its output seeds TASK-549 (guard) and orients
TASK-550/552/553.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 548 add-subtask "<title>"`; track with `sq task 548 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T21:40:00Z] Elias Python:
  - DATA (per-request, must move): _clock._override (forged/--at time); _actor._override/_session_id/_parent_session_id (actor id + session lineage); _cli/_common._active_spec/_active_dir (US5/TASK-552, unchanged here); _paths.resolve()/find_config() Path.cwd() default (US3/TASK-553, unchanged here).
  - CODE/definition (stays, allowlisted): _backends/_registry._REGISTRY+_loaded+register() side-effect (backend classes, instantiated fresh); _workflow/__init__._BUNDLED_SPEC + WORKFLOWS/SUBENTITY_WORKFLOWS/ALLOWED_PARENTS/TERMINAL + free-fn shims (immutable bundled default); _roles/_catalog._CATALOG/_BY_SLUG/_PREDEFINED_BY_SLUG (bundled catalog); _interactions.__init__._PLAYBOOK_SPEC (bundled playbook); _cli/_create._create_spec + _cli/__init__._spec/_STATIC_TYPES (bundled spec, static Typer registration); _rendering/_engine._env_cache (per-squad-dir keyed Jinja cache, bounded by TASK-554); _overrides/_manifest._manifest_cache (parsed-manifest cache with its own invalidate()).
  - Triage rule: value varies per request/squad/test -> DATA, lives in RequestContext; value is an immutable spec/class/definition loaded once and safe to share -> CODE, may stay module-level. Recorded verbatim as the _context.py module docstring (TASK-550).
  - Shim-reach grep: grep -rn 'workflow.can_transition|workflow.is_open|workflow.parent_allowed|workflow.parent_hint|WORKFLOWS\b|ALLOWED_PARENTS\b|TERMINAL\b|SUBENTITY_WORKFLOWS' src/ -> only the definition site (_workflow/__init__.py) and its __all__ export; zero production callers. Every service/CLI call site (_base, _items, _refs, _collab, _maintenance, _retype, _rename, _roster, _cli/_main) routes through self.spec.<method>()/spec.<method>()/get_active_spec().<method>().
  - Only golden-lock tests reference the bundled constants directly (test_workflow_spec_artifact, test_parent_allowed_rule_table, test_status_machine_transitions, test_accepted_and_published_are_terminal, test_terminal_status_reopen_and_unblock, test_identity) - expected, out of scope. Conclusion: zero production reroute risk; nothing to name for TASK-552.
- [2026-07-21T21:40:04Z] Elias Python:
  - Audit-only, no code change. Ready for review.
<!-- sq:discussion:end -->
