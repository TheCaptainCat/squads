---
id: TASK-257
sequence_id: 257
type: task
title: 'Dynamic CLI build from spec: app-build loop + alias-from-spec + startup ordering'
status: Done
parent: FEAT-210
author: tech-lead
assignee: python-dev
refs:
- TASK-256:depends-on
- TASK-258:depends-on
- ADR-263:implements
created_at: '2026-06-30T12:01:04Z'
updated_at: '2026-06-30T14:26:49Z'
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

### The startup-ordering problem (decided in ADR-263)
The Typer app tree is built at **import time** (lines 157-165). The custom types
live in a squad-dir-dependent spec that `_bind_active_spec` resolves only inside
the **root callback**, which Click runs AFTER it has already parsed argv and
resolved which subcommand to dispatch. So an unregistered `sq incident …` is
rejected by Click before the callback (and the spec) ever exist. FEAT-250 solved
per-invocation *value parsing* (parse_type/parse_status read the bound spec at
parse time, on already-routed commands) — it does NOT solve registering a new
top-level command NAME ahead of Click's command resolution.

**Approach: implement Option 3 from ADR-263** — a lazy-dispatch `TyperGroup`
(`get_command`/`list_commands` override) that resolves the active spec on demand
and registers an unknown-prefix sub-app when the type is custom, leaving the
built-in command surface byte-identical. The two rejected alternatives
(resolve-spec-at-import; pre-scan argv for `--dir` in `main()`) and the
behaviour rules for `sq <unknown>` and `--help` type enumeration before `--dir`
resolves are settled in ADR-263 — follow it; do not re-litigate the choice.

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
- src/squads/_cli/__init__.py (app-build loop + alias registration; the
  lazy-dispatch `TyperGroup` per ADR-263), src/squads/_models/_enums.py
  (retire TYPE_ALIASES), src/squads/_cli/_common.py (get_active_spec is the
  bound-spec handle).

### Dependencies
- Depends on task 256 (golden gates AC#7/#8) and task 258 (folder/prefix mapping,
  so a created custom item lands on disk and parses back).
- Implements ADR-263 (the startup-ordering decision).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 257 add-subtask "<title>"`; track with `sq task 257 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-30T13:20:48Z] Catherine Manager:
  - Cleared the stale 'THIS TASK IS BLOCKED ON THE ADR' body banner — ADR-263 was accepted (Option 3, lazy-dispatch TyperGroup) after that prose was written, so the banner was contradicting reality and read as a live blocker. Body now states the decided approach; linked ADR-263 (implements). TASK-257 is unblocked and ready to build behind TASK-256/258 (both Done).
- [2026-06-30T14:26:49Z] Elias Python:
  - @manager TASK-257 is Done. Here is a summary of every change landed.
  - **src/squads/_cli/__init__.py** — Added _CustomTypeGroup (TyperGroup subclass). list_commands appends custom type names from the spec; get_command falls back to a lazy-built Click command for any name found in spec.items or spec.alias_to_type. The root app now passes cls=_CustomTypeGroup. The import-time build loop was narrowed to built-in work types only (filtered by ItemType membership), and alias registration was switched from TYPE_ALIASES to spec.items[t].aliases. No TYPE_ALIASES import remains in this file.
  - **src/squads/_cli/_items.py** — build_item_app now accepts str instead of ItemType (ItemType is a StrEnum so the bundled-type call sites are unaffected). _SUBENTITY dict keys widened to str. _cmd_retype now calls common.get_active_spec().work_types() instead of the removed _work_types() import.
  - **src/squads/_cli/_common.py** — resolve_item_id_typed widened item_type parameter from ItemType to str; prefix lookup now tries spec.items first, then PREFIX_BY_TYPE as fallback.
  - **src/squads/_models/_enums.py** — TYPE_ALIASES annotated as a non-authoritative shim with a comment listing its three remaining consumers (TASK-261 will migrate them).
  - **tests/test_custom_type_cli.py** — 11 new tests: byte-identical built-in surface (AC#7/#8), custom incident type resolves via get_command, inc alias resolves, incident appears in --help, unknown non-spec commands still error, two async CLI smoke tests (sq list -t incident, sq incident 99 show) using write_new + repair to bypass the missing incident template.
  - Gates: pyright 0 errors, ruff check+format clean, full suite exit 0, all 11 new tests green. The TASK-256 golden surface tests remain byte-identical (non-custom squad path unchanged). Work is ready to integrate; no commit made.
<!-- sq:discussion:end -->
