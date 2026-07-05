---
id: TASK-268
sequence_id: 268
type: task
title: 'Working create path for custom types: generic item template + custom-aware
  sq create'
status: Done
parent: FEAT-210
author: tech-lead
assignee: python-dev
refs:
- ADR-266:implements
- REV-265:addresses
- TASK-267:depends-on
created_at: '2026-07-01T08:28:54Z'
updated_at: '2026-07-01T10:20:02Z'
---
<!-- sq:body -->
**Closes REV-265 F2 (High). Owns AC#1/US1 end-to-end.** This is the create path that fell *between* the original tasks — no prior task owned `sq <type> create` end-to-end. This task owns it.

## Problem — two independent breaks on the create path
1. **CLI surface:** `sq create <type>` (`_cli/_create.py`, `create_app`) is a plain `typer.Typer` built from a hardcoded `ItemType` tuple, never made custom-aware and not a lazy-dispatch group. `sq create incident` returns "No such command". (`sq create --help` lists only the 7 built-ins.)
2. **Service/renderer:** even `svc.create('incident', ...)` fails — `_template_for` (`_services/_base.py:213-217`) returns `items/{item_type}.md.j2` with no fallback, and custom types ship no per-type template → `jinja2.exceptions.TemplateNotFound: items/incident.md.j2`.

Result: AC#1 ("`sq incident create "…"` succeeds and `sq list -t incident` returns the item") and US1 acceptance are UNMET. The only current way to materialise a custom item is `retype` (file-move, sidesteps the template) — not a sanctioned create flow.

## Scope
1. **Generic item template.** Add a generic `items/_default.md.j2` and fall back to it in `_template_for` when the per-type template is absent (built-ins keep their specific templates → byte-identical). The default template renders the standard item skeleton (title/body markers) with no per-type assumptions.
2. **Custom-type-aware create entry.** Make the create surface resolve custom types the same way the resource groups do. **Reconcile the surface with TASK-257's `_CustomTypeGroup`:** either make `create_app` a lazy-dispatch group, or register spec work types at startup — match the mechanism ADR-263 / TASK-257 established for `sq <type>`. Pick one and document the decision on the task. Whichever verb form ships (`sq create <type>` vs a `create` verb on the resource group), it must be the one the thin skill advertises (coordinate with TASK-269, which closes F4).

## Depends on TASK-267
The create path calls `allocate_id`/`format_id` and stamps `Item.prefix` — those become spec/prefix-aware in TASK-267. Create is where the folder is auto-created and the correctly-prefixed id is first minted, so it must sit on top of the 267 foundation or the created item reproduces F1.

## Acceptance
- AC#1: declare `[workflow.types.incident]` in `.overrides/workflow.toml`, then `sq incident create "DB timeout" --author tech-lead` succeeds; the item lands in the auto-created folder with a correctly-prefixed id (`INC-000001`); `sq list -t incident` returns it; `sq check` green.
- Built-in create (`sq create task ...`) unchanged — **AC#7/#8:** TASK-256 goldens stay green; byte-identical built-in create output/filenames.
- Gates clean: `uv run pyright && uv run ruff check . && uv run ruff format --check .`.
- **Test the headline end-to-end (the gap that let F2 through — prior tests used `write_new`/`retype`, never `create`):** declare a custom type in `.overrides/workflow.toml`, run the actual `sq <type> create` (headline command), then `sq list -t <type>` and `sq <type> <ID> show` with the correctly-prefixed id round-tripping. Add a service-level test AND a CLI smoke test.

## Files
`_cli/_create.py`, `_cli/__init__.py` (create surface / lazy dispatch), `_services/_base.py` (`_template_for` fallback), `_rendering/templates/items/_default.md.j2` (new).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 268 add-subtask "<title>"`; track with `sq task 268 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-01T10:20:02Z] Elias Python:
  - @manager TASK-268 is done. All gates green: pyright 0 errors, ruff clean, 1493 passed / 1 skipped / 0 failed.
  - Files changed: (1) src/squads/_rendering/templates/items/_default.md.j2 — new generic item template with body+discussion markers; (2) src/squads/_rendering/_engine.py — added has_template() that checks the Jinja2 loader without raising TemplateNotFound; (3) src/squads/_services/_base.py — _template_for() now falls back to items/_default.md.j2 for custom types, with has_template() checking whether a per-type template exists; (4) src/squads/_cli/_create.py — create_app is now a _CustomCreateGroup (same lazy-dispatch pattern as _CustomTypeGroup in __init__.py), adding sq create <custom-type> as a registered command; (5) src/squads/_rendering/templates_manifest.json — regenerated via gen_template_manifest.py to include _default.md.j2; (6) tests/test_custom_type_create.py — 8 new tests.
  - How the generic template + custom-aware create hook together: _build_create_cmd(item_type_str) builds a TyperCommand for any custom type string by registering _make_fn in a single-command Typer (which yields a leaf TyperCommand, not a group). _CustomCreateGroup.get_command() lazily calls _build_create_cmd when Click dispatches a name that is not a built-in but is in the active spec's work_types(). _template_for() in ServiceCore now calls has_template(per_type_path) and falls back to items/_default.md.j2 when the per-type template is absent — built-ins all have dedicated templates so they are byte-identical.
  - Reconciliation with _CustomTypeGroup (TASK-257): _CustomCreateGroup follows the same pattern but is scoped to the create sub-app. Both call common.get_active_spec() (bound once per invocation by _bind_active_spec in the root callback), so they always see the same spec. Each has its own ClassVar _custom_cmd_cache so they are fully independent. No changes to __init__.py were needed — create_app just gets a new cls=_CustomCreateGroup.
  - End-to-end create test (test_create_incident_end_to_end): declares [workflow.types.incident] in .overrides/workflow.toml, runs sq create incident 'DB timeout' --author manager (the actual CLI verb, NOT write_new/retype), asserts INC- prefix (not INCIDENT-), folder auto-created, sq list -t incident finds it, sq incident N show round-trips, sq check green.
  - Byte-identical proof: all 7 built-in types keep their dedicated templates (unchanged). test_builtin_create_surface_unchanged confirms sq create --help still lists only built-ins for a non-custom squad. The TASK-256 goldens pass (1493 passed, 0 failed).
  - Notable: _build_create_cmd uses a single-command Typer so typer.main.get_command returns a TyperCommand (leaf) not a TyperGroup — this was the critical design decision. A TyperGroup would have broken sq create incident TITLE dispatch because Click would have tried to dispatch TITLE as a subcommand. Also: the manifest.json needed regeneration after adding _default.md.j2 (gen_template_manifest.py script).
<!-- sq:discussion:end -->
