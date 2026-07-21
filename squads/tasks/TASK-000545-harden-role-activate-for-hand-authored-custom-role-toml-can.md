---
id: TASK-545
sequence_id: 545
type: task
title: Harden role activate for hand-authored custom-role TOML + can_spawn opt-in
status: Done
parent: FEAT-543
author: tech-lead
assignee: python-dev
created_at: '2026-07-21T20:57:08Z'
updated_at: '2026-07-21T21:30:11Z'
---
<!-- sq:body -->
Maps to FEAT-543 US2 (Activate a custom role end-to-end, incl. can_spawn opt-in).

## Scope

Confirm and harden the `sq role activate <slug>` path for a **hand-edited
net-new** role TOML (the file produced by TASK-544), and wire the `can_spawn`
opt-in. The resolver new-slug path and activation already work end-to-end
(proved by hand-authoring `security-analyst`); this task locks that behaviour
under test and closes any rough edges.

1. **Activation coverage.** With a filled `.overrides/roles/<slug>.toml` for a
   slug absent from `PREDEFINED`, `sq role activate <slug>` must create the
   tracked ROLE item and the `.claude/` backend pointer, exactly as it does for
   a bundled slug — resolving fields through `resolve_role`
   (`src/squads/_roles/_resolver.py`). Verify the ROLE item's `extra` carries
   the custom `full_name`/`title`/`mission`/etc., and that `sq role <slug> show`
   renders the custom card (not the bundled fallback).

2. **`can_spawn` opt-in.** `can_spawn = true` in the TOML must flow through
   `_apply_override` → `RoleDef.can_spawn` → the activated item's
   `extra[X.CAN_SPAWN]`, and surface in `sq role <slug> show` / `--json`. Default
   is `false` (RoleDef default). This is the deliberately permissive policy from
   the feature decision — opt-in and allowed, in tension with ADR-155's
   leaf-roles-can't-spawn stance; do NOT add a warning or gate.

3. **Scaffold flag (only if it lands cleanly).** If it fits without complicating
   the TASK-544 scaffolder, add a `--can-spawn` flag to `sq override scaffold
   --new` that emits `can_spawn = true` as an active key instead of the commented
   default. If it adds meaningful complexity, leave `can_spawn` as the commented
   advanced field and note that here in a comment — the TOML route is the
   contract; the flag is a convenience.

Do not add a one-shot `sq role add`; create-surface stays scaffold-then-activate.

## Acceptance

- Activating a filled custom-slug TOML creates the ROLE item + `.claude/` pointer
  and the item's fields match the TOML (not bundled defaults).
- `can_spawn = true` in the TOML is honoured: the activated role reports
  `can spawn: yes` in `sq role <slug> show` and `can_spawn: true` in `--json`;
  omitting it defaults to false.
- No warning/gate is emitted for a spawn-capable custom role.
- If added, `sq override scaffold --new <slug> --can-spawn` writes an active
  `can_spawn = true`.
- `pyright` + `ruff` clean; `sq check` clean.

## Tests (service + CLI smoke)

- Service/integration: end-to-end scaffold(TASK-544) → fill → `activate_role` →
  assert ROLE item created, pointer written, custom fields present; `can_spawn`
  true and false paths both asserted.
- CLI smoke: `sq role activate <custom-slug>` exits 0 and prints the activated
  name/id; `sq role <slug> show --json` reflects `can_spawn`.
- If the `--can-spawn` flag lands, a CLI smoke asserting the emitted TOML key.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 545 add-subtask "<title>"`; track with `sq task 545 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T21:07:16Z] Elias Python:
  - Confirmed/locked the existing new-slug activate_role path under test: filled custom-role TOML -> activate_role creates the ROLE item + .claude/ pointer with custom full_name/title/mission (not a bundled fallback). can_spawn was already wired resolver->RoleDef->extra->show/--json (RoleDef.to_extra/from_extra, backend pointer denylist); added coverage for default-false and true-opt-in on a *custom* role specifically (pointer disallowedTools + sq role show --json).
  - Added --can-spawn to sq override scaffold --new (emits active can_spawn = true), landed cleanly on 544's scaffolder.
  - Files: src/squads/_overrides/_service.py, src/squads/_cli/_override.py (already touched in TASK-544); new test file tests/integration/test_custom_role_activation.py; CLI smoke added to tests/cli/test_override_commands_cli.py.
  - Gates: pyright clean, ruff check+format clean, targeted pytest (new file + override CLI + can_spawn surfaces + role/dev override pickup + unit can_spawn + role CLI) 100+ passed, sq check clean.
<!-- sq:discussion:end -->
