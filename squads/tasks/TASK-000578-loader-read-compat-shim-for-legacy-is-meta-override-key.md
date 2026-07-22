---
id: TASK-578
sequence_id: 578
type: task
title: Loader read-compat shim for legacy is_meta override key
status: Done
parent: FEAT-567
author: tech-lead
description: 'US1: pop legacy is_meta before model_validate (bundled + override parsers);
  false/absent -> category work, true on non-roster -> clean SquadsError; CHANGELOG
  deprecation note'
created_at: '2026-07-22T09:26:38Z'
updated_at: '2026-07-22T10:25:29Z'
---
<!-- sq:body -->
Story US1 (category axis). Add the transitional read-compat shim so an adopter override carrying a legacy `is_meta` key still loads after the axis rename, and record the deprecation. Behaviour-preserving / no-enforcement (Phase A). Depends on the sibling axis task (the `category` field must already exist).

## Why

`ItemSpec` is `extra="forbid"`, so once `is_meta` is removed a lingering `is_meta` key in an adopter's `.overrides/workflow.toml` would hard-`SquadsError` on load. Overrides are additive-only, so `is_meta` can only appear on a custom type the adopter added; `is_meta = false` is the default (redundant to write) and `is_meta = true` on a non-roster type was never really supported (roster is closed/locked). Per ADR-541 the fix is a read-compat shim, not a schema/version bump — no `SCHEMA_VERSION` change, no data migration, no `_migrations/` runner (`is_meta` never appears in item frontmatter or the index).

## Scope

- `_workflow/_loader.py`: in the item parser used for overrides (`_parse_item_spec_str`) AND the bundled item loop in `_build_spec`, POP a legacy `is_meta` key from the raw data before `model_validate` (keeping `extra="forbid"` intact for every other unknown key):
  - `is_meta` absent or `false` → let `category` fall to its `"work"` default (no-op).
  - `is_meta = true` on a type that is not one of the roster types → raise a clean `SquadsError` pointing the author at `category` and the roster-locked rule (roster is closed; a custom type cannot be roster). Keep the message a `SquadsError`, never a traceback.
- CHANGELOG (`## [Unreleased]`): add a deprecation note that the `is_meta` override key is deprecated in favour of `category`, read transparently for now via a compat shim, and slated for removal at 1.0.

## AST guard

No new module-level state expected; no allowlist change anticipated.

## Acceptance

- An override declaring a custom type with `is_meta = false` (or omitting it) loads clean, the type resolving to `category = "work"`.
- An override with a bare unrelated unknown key still fails via `extra="forbid"` (the shim pops only `is_meta`).
- An override custom type with `is_meta = true` fails with a clean `SquadsError` naming `category`/roster-locked.
- CHANGELOG Unreleased carries the deprecation + 1.0-removal note.
- `uv run pytest` green (add loader tests for the three shim branches); `sq check` byte-identical.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 578 add-subtask "<title>"`; track with `sq task 578 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T09:37:26Z] Elias Python:
  - loader read-compat shim added (_pop_legacy_is_meta, wired in both bundled + override item parsers), CHANGELOG Unreleased deprecation note, 4 new tests for the three branches + unknown-key control; sq check byte-identical.
<!-- sq:discussion:end -->
