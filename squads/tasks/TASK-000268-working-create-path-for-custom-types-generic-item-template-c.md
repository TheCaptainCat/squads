---
id: TASK-000268
sequence_id: 268
type: task
title: 'Working create path for custom types: generic item template + custom-aware
  sq create'
status: Draft
parent: FEAT-000210
author: tech-lead
refs:
- ADR-000266:implements
- REV-000265:addresses
- TASK-000267:depends-on
created_at: '2026-07-01T08:28:54Z'
updated_at: '2026-07-01T08:30:39Z'
---
<!-- sq:body -->
**Closes REV-000265 F2 (High). Owns AC#1/US1 end-to-end.** This is the create path that fell *between* the original tasks — no prior task owned `sq <type> create` end-to-end. This task owns it.

## Problem — two independent breaks on the create path
1. **CLI surface:** `sq create <type>` (`_cli/_create.py`, `create_app`) is a plain `typer.Typer` built from a hardcoded `ItemType` tuple, never made custom-aware and not a lazy-dispatch group. `sq create incident` returns "No such command". (`sq create --help` lists only the 7 built-ins.)
2. **Service/renderer:** even `svc.create('incident', ...)` fails — `_template_for` (`_services/_base.py:213-217`) returns `items/{item_type}.md.j2` with no fallback, and custom types ship no per-type template → `jinja2.exceptions.TemplateNotFound: items/incident.md.j2`.

Result: AC#1 ("`sq incident create "…"` succeeds and `sq list -t incident` returns the item") and US1 acceptance are UNMET. The only current way to materialise a custom item is `retype` (file-move, sidesteps the template) — not a sanctioned create flow.

## Scope
1. **Generic item template.** Add a generic `items/_default.md.j2` and fall back to it in `_template_for` when the per-type template is absent (built-ins keep their specific templates → byte-identical). The default template renders the standard item skeleton (title/body markers) with no per-type assumptions.
2. **Custom-type-aware create entry.** Make the create surface resolve custom types the same way the resource groups do. **Reconcile the surface with TASK-000257's `_CustomTypeGroup`:** either make `create_app` a lazy-dispatch group, or register spec work types at startup — match the mechanism ADR-000263 / TASK-257 established for `sq <type>`. Pick one and document the decision on the task. Whichever verb form ships (`sq create <type>` vs a `create` verb on the resource group), it must be the one the thin skill advertises (coordinate with TASK-000269, which closes F4).

## Depends on TASK-000267
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
<!-- sq:discussion:end -->
