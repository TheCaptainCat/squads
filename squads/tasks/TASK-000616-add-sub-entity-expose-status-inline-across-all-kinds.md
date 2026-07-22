---
id: TASK-616
sequence_id: 616
type: task
title: 'add-* sub-entity: expose --status inline across all kinds'
status: Done
parent: FEAT-571
author: tech-lead
priority: low
refs:
- REV-565
description: Inline --status on add-finding/story/subtask, at parity with update
created_at: '2026-07-22T18:05:31Z'
updated_at: '2026-07-22T18:44:16Z'
---
<!-- sq:body -->
Expose `--status` inline on the generic `add-<kind>` command builder so
`add-finding` / `add-story` / `add-subtask` can seed a non-initial status at
creation, at parity with `update`. Closes the remaining explicit gap: a
sub-entity's badge fields are already generated inline generically (one
`--<field-code>` per declared field, driven by `spec.fields_for(kind)` in the
CLI's dynamic-signature add builder), but status is a separate axis (the kind's
lifecycle machine, not a badge collection) and is currently only settable via a
follow-up `update`.

## What already exists (do NOT rebuild)
- The per-field flag derivation is already generic and spec-driven: the add
  builder appends one `--<field-code>` option per `spec.fields_for(kind)` entry,
  validated through the shared badge path (`resolve_collection` +
  `parse_badge_code`). `add-finding --severity` uses this path; `--severity` behaviour
  must stay byte-identical. No new field-flag mechanism is needed.

## Scope
- Service: the `add_block` entry point accepts an optional `status`. When absent,
  keep seeding the kind's initial status (unchanged). When provided, seed the
  fresh sub-entity directly at that status (creation seeds, it does not
  "transition" from a prior state — no `--force` on add).
- Validate a provided status against the kind's OWN lifecycle states, not the
  global status set. Note the CLI's `parse_status` only checks membership in the
  whole spec's status set, so `add_block` MUST additionally scope-check the value
  against the kind's lifecycle machine states (the accessor behind
  `subentity_initial`/`subentity_can_transition`) and raise a `SquadsError` (clean
  message, list the kind's valid states) if it is not a declared state of that
  kind — otherwise a finding could be seeded with a story-only status. Reuse the
  existing validation surface; do not add a parallel validation path.
- CLI: hoist a `--status` keyword option onto the shared `add-<kind>` builder
  (the same dynamic `inspect.Signature` construction the field flags already use),
  so all three kinds get it uniformly. Parse via the existing `parse_status`, pass
  through to `add_block`. Nothing per-kind or hardcoded to a field name.

## Additive / no-break
- Existing invocations without `--status` behave exactly as before (initial
  status seeded). No signature change visible to callers that omit the flag.

## Typer note
- No new dynamic-option awkwardness: the add builder already constructs its
  parameter list via `inspect.Signature` at command-registration time, so
  `--status` is just a fixed keyword parameter appended alongside the existing
  field params (mirroring how the update builder already carries `--status`).

## Gate reminder
- If you add any module-level constant (e.g. a lookup dict/set), run the
  `tests/meta` suite in your gate — the module-mutable-state guard fails the build
  on any new module-scope mutable lookup. Prefer a local/derived value or add the
  exact name to the guard's allowlist with a one-line reason.
- Full gate `uv run --all-extras pyright && ... ruff ...`; run the suite once to a
  file. No ticket IDs in code or test names; no lifecycle prose in any body.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 616 add-subtask "<title>"`; track with `sq task 616 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T18:13:22Z] Elias Python:
  - Added --status to the shared add-<kind> builder (_register_add in _cli/_items.py), threaded into Service.add_block/add_story/add_subtask/add_finding.
  - Validated in two layers: CLI parse_status (global status vocabulary, existing) + a new Service._resolve_add_status that scope-checks against spec.subentity_workflow(kind).states — the KIND'S OWN lifecycle, not can_transition (creation seeds, no prior state) — raising SquadsError listing that kind's valid states on mismatch. Omitted --status is untouched: still seeds subentity_initial(kind).
  - Gates: pyright/ruff/ruff-format clean; targeted pytest (62 tests) + tests/meta green; sq check clean.
<!-- sq:discussion:end -->
