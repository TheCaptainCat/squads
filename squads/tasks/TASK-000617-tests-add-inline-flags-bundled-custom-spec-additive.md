---
id: TASK-617
sequence_id: 617
type: task
title: 'Tests: add-* inline flags (bundled + custom spec, additive)'
status: Done
parent: FEAT-571
author: tech-lead
priority: low
refs:
- TASK-616:depends-on
description: 'Service + CLI smoke: bundled --status/field parity, custom-spec flag
  derivation'
created_at: '2026-07-22T18:05:31Z'
updated_at: '2026-07-22T18:22:58Z'
---
<!-- sq:body -->
Prove the `add-<kind>` inline-flag surface across the bundled spec and a custom
spec — a service-level test plus a CLI smoke test, per repo convention.

## Bundled spec
- Each of `add-finding` / `add-story` / `add-subtask` exposes `--status` inline
  and seeds the provided (valid) status at creation; the resulting sub-entity
  round-trips that status in frontmatter.
- `add-finding --severity` is unchanged (still generated from the declared field,
  same validation/default behaviour).
- A `--status` value that is not a declared state of that kind's lifecycle fails
  loud with a clean error (and, e.g., a story-only status is rejected on a
  finding — the kind-scoped check, not just global status membership).
- Additive proof: an `add-<kind>` invocation with no new flags behaves exactly as
  before (initial status seeded, no error).

## Custom spec
- Drive an override spec that renames/relabels a badge collection (or adds a new
  field to a sub-entity kind) and confirm the generated per-field flags follow the
  spec — the flag name comes from the declared field code, with no hardcoded
  field name anywhere in the command builder. (The field-flag mechanism already
  exists; this locks it against a custom vocabulary alongside the new `--status`.)
- Confirm `--status` works on the custom kind and validates against that kind's
  own declared lifecycle.

## Conventions
- Name tests by behaviour, not by ticket ID (no ticket IDs in test names or
  bodies; keep the ticket pointer in the sq ref/comment).
- Custom-spec tests build the spec via `.overrides` in a temp squad (as the
  existing custom-subentity-kind CLI test does), holding the roster constant so
  generated-surface assertions do not drift.
- Run the `tests/meta` suite as part of the gate if the implementation task added
  any module-level constant. Run the full suite once, redirect to a file, read the
  file.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 617 add-subtask "<title>"`; track with `sq task 617 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T18:13:30Z] Elias Python:
  - Added tests/service/test_add_subentity_seeds_status_inline.py (add_story/add_subtask/add_finding seed --status, severity default/flag unchanged, flagless-add unchanged, cross-lifecycle rejection both directions: story-status-on-finding and finding-status-on-story).
  - Added tests/cli/test_add_subentity_status_flag_cli.py: CLI smoke for --status on all three bundled kinds + additive flagless case + clean (no-traceback) rejection of an out-of-lifecycle value.
  - Extended tests/cli/test_custom_subentity_kind_cli.py (existing custom-spec 'action' kind, held roster constant) with two --status cases: seeds a non-initial custom-lifecycle status, and rejects a globally-valid-but-out-of-kind status ('Blocked') cleanly — proves the per-field flag derivation is unaffected and --status generalizes to a custom kind.
  - Gates: pyright/ruff/ruff-format clean; targeted pytest (62 tests, all new+touched files) + tests/meta green; sq check clean.
<!-- sq:discussion:end -->
