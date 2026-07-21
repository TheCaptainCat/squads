---
id: TASK-549
sequence_id: 549
type: task
title: AST guard for module-level mutable state + triage rule
status: Draft
parent: FEAT-533
author: tech-lead
description: 'US1: meta-test failing the build on new module-scope mutable bindings
  outside the allowlist'
created_at: '2026-07-21T21:33:13Z'
updated_at: '2026-07-21T21:35:43Z'
---
<!-- sq:body -->
Implements FEAT-533 **US1** (guard half). The durable, lasting output of the feature — a guard,
not a one-time sweep. ADR-534 rule 1 is what it enforces.

## Scope

Ship an **AST meta-test** that scans the engine modules (`src/squads/**`) for two constructs at
**module scope** and fails when a hit is not on an explicit allowlist:

1. Top-level assignments binding a **mutable type** — a `dict`/`list`/`set` literal or a
   `dict()`/`list()`/`set()` constructor call.
2. `global` statements.

Walk each module with the `ast` module; only module-scope nodes count (skip bindings inside
functions/methods/classes — those are not module globals). Match by fully-qualified
`module::name`.

## The allowlist (sanctioned CODE caches — the ONLY accepted module-level mutable bindings)

Sourced from TASK-548's triage:

- `_backends/_registry.py`: `_REGISTRY`, `_loaded`
- `_workflow/__init__.py`: `_BUNDLED_SPEC` + derived `WORKFLOWS`, `SUBENTITY_WORKFLOWS`,
  `ALLOWED_PARENTS`, `TERMINAL`
- `_rendering/_engine.py`: `_env_cache`
- `_roles/_catalog.py`: `_CATALOG`, `_BY_SLUG` (+ `_PREDEFINED_BY_SLUG` if present)
- `_interactions/__init__.py`: `_PLAYBOOK_SPEC`
- `_cli/_create.py`: `_create_spec`
- `_cli/__init__.py`: `_spec`, `_STATIC_TYPES` (+ the `_CustomTypeGroup._custom_cmd_cache`
  ClassVar and `_CustomCreateGroup._custom_cmd_cache` — class-scope caches, in-process CLI-surface
  code caches; allowlist them explicitly or scope the AST walk to true module scope so ClassVars
  are out of band)
- `_overrides/_manifest.py`: `_manifest_cache`

## Assertion

**No NEW module-level mutable binding exists outside that allowlist.** After TASK-550/551/552/553
land, `_clock._override`, `_actor._override`/`_session_id`/`_parent_session_id`,
`_cli/_common._active_spec`/`_active_dir` must NO LONGER be module globals (they live on
RequestContext), so they must not appear as allowlisted survivors — their absence is part of the
proof. Adding a convenient module global later fails the build until it is either moved to the
request-scoped context or (if genuinely a code/definition cache) added to the allowlist with a
one-line justification comment.

## Documented triage rule

Alongside the test, ship a short written rule (module docstring on the meta-test, or a
CONTRIBUTING/contributor-doc note): **data → per-request context; code/definition → module level,
allowlisted**, and the convention that the request-scoped context is a **single RequestContext
object, not per-value ContextVars** (per ADR-534 + Robert's US2 design decision). This is where
that convention is captured so it does not rot.

## Acceptance

- The meta-test passes on the migrated tree (allowlist matches reality exactly — no missing, no
  extra).
- A deliberately-added `_leak: dict = {}` at module scope in any engine module makes it fail
  (prove with a temporary local edit, then revert).
- The triage rule text is present and names the single-RequestContext convention.
- Full suite green; `sq check` clean.

## Dependencies / order

**Last** — lands after TASK-550/551/552/553 have migrated the data seams off module globals, so
the allowlist reflects the final state and the assertion is meaningful. Consumes TASK-548's
allowlist enumeration.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 549 add-subtask "<title>"`; track with `sq task 549 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
