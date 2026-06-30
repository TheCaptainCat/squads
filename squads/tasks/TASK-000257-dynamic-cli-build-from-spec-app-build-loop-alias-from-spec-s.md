---
id: TASK-000257
sequence_id: 257
type: task
title: 'Dynamic CLI build from spec: app-build loop + alias-from-spec + startup ordering'
status: Draft
parent: FEAT-000210
author: tech-lead
refs:
- TASK-000256:depends-on
- TASK-000258:depends-on
created_at: '2026-06-30T12:01:04Z'
updated_at: '2026-06-30T12:03:19Z'
---
<!-- sq:body -->
**Slice 1 — dynamic CLI build from spec (app-build loop + alias-from-spec).**
Maps to: US1, AC#1. The startup-ordering crux of the feature.

### Scope
Replace the two import-time enum→spec dependencies in `_cli/__init__.py`:
1. The app-build loop `for _type in _ORDERED_WORK_TYPES` (currently
   `[t for t in ItemType if t in _work_types()]`) must iterate the loaded
   spec's managed work types so a custom type gets its `sq <type>` Typer app
   (`create`/`show`/`list`/`update`/`status`/`ref`/`comment`/`body`/`remove`/`retype`).
   NB: `WorkflowSpec.managed_types` is a **property**, not a method.
2. Alias sub-app registration must read each `ItemSpec.aliases` (per-type list on
   the spec) instead of the hardcoded `TYPE_ALIASES` dict in `_enums.py`. After
   this lands, `TYPE_ALIASES` retires — its values already live in
   default_workflow.toml as `ItemSpec.aliases` (FEAT-208 encoded them, nothing
   consumes them yet). Confirm `_cli/_workflow_cmd.py::_print_cheatsheet` and
   `agents/squads_skill.md.j2` (which still pass `TYPE_ALIASES`) are migrated to
   the spec alias source as part of, or coordinated with, task 261.

### The startup-ordering problem — THIS TASK IS BLOCKED ON THE ADR
The Typer app tree is built at **import time** (lines 157-165). The custom types
live in a squad-dir-dependent spec that `_bind_active_spec` resolves only inside
the **root callback**, which Click runs AFTER it has already parsed argv and
resolved which subcommand to dispatch. So an unregistered `sq incident …` is
rejected by Click before the callback (and the spec) ever exist. FEAT-250 solved
per-invocation *value parsing* (parse_type/parse_status read the bound spec at
parse time, on already-routed commands) — it does NOT solve registering a new
top-level command NAME ahead of Click's command resolution.

This is a genuine design decision (resolve-spec-at-import vs pre-scan argv for
--dir in main() vs a lazy `TyperGroup.get_command` that registers an
unknown-prefix sub-app on demand, à la AddressDispatchGroup) with a behaviour
question attached (how `sq <unknown>` behaves and how `--help` enumerates types
before --dir resolves). **Implement per the accepted ADR (see breakdown comment
on FEAT-210); do not pick an approach unilaterally.**

### Acceptance
- AC#1: on a squad with `[workflow.types.incident]` declared, `sq incident
  create "…" --author tech-lead` and `sq list -t incident` work with no code
  change; `sq check` green.
- Built-in aliases (e/f/t/b/d/r/g, feat/dec/rev) still resolve identically.
- HARD CONSTRAINT — AC#7/#8: a non-custom squad sees byte-identical CLI surface;
  the task 256 characterization golden stays green.
- `TYPE_ALIASES` removed (or reduced to a non-authoritative shim) once all
  consumers read the spec.

### Files
- src/squads/_cli/__init__.py (app-build loop + alias registration; possibly
  main()/a custom TyperGroup per the ADR), src/squads/_models/_enums.py
  (retire TYPE_ALIASES), src/squads/_cli/_common.py (get_active_spec is the
  bound-spec handle).

### Dependencies
- BLOCKED ON: the startup-ordering ADR (architect).
- Depends on task 256 (golden gates AC#7/#8) and task 258 (folder/prefix mapping,
  so a created custom item lands on disk and parses back).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 257 add-subtask "<title>"`; track with `sq task 257 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
