---
id: TASK-000270
sequence_id: 270
type: task
title: 'Custom-type CLI clean-ups: scope get_command except, alias-guard defence test'
status: Done
parent: FEAT-000210
author: tech-lead
assignee: python-dev
refs:
- REV-000265:addresses
- TASK-000269:depends-on
created_at: '2026-07-01T08:28:56Z'
updated_at: '2026-07-01T15:40:17Z'
---
<!-- sq:body -->
**Closes REV-000265 F5 (Low) + F6 (Low) — reviewer's discretion, non-blocking clean-ups.** Independent of the F1/F2 fixes; can run in parallel. Do only if cheap.

## F5 — broad except masks genuine build errors
**File:** `_cli/__init__.py:171` — the `except Exception: return None` at the bottom of `_CustomTypeGroup.get_command`. The fail-soft is defensible at the TOP of the method (an invalid/unresolvable spec should degrade to the built-in surface, never crash `sq --help`). But by line 171 the code has already passed the built-in guard and resolved `canonical` as a declared custom type/alias — a failure there is a genuine build error for a type the user just declared and `--help` lists, yet it surfaces the misleading "No such command 'incident'".

**Fix:** scope the broad `except` to the spec-RESOLUTION region only (~lines 140-152). Once `canonical` is confirmed a declared custom type, let `build_item_app`/`get_command` errors propagate (or wrap in a `SquadsError` naming the type) rather than mapping to `None`. The only thing that should yield `None` is "genuinely not a custom type", already handled explicitly.

## F6 — alias-guard could silently drop an alias-less built-in
**File:** `_rendering/templates/workflow.md.j2:40` — `{% if item_spec.aliases and not item_spec.is_meta %}`. Byte-identical today (every built-in work type declares an alias, golden proves it), but it silently couples "appears in the alias cheatsheet" to "has an alias". No code change required (a type with no alias arguably doesn't belong in an alias table). **Defence-in-depth:** add a test asserting every non-meta `spec.work_types()` type expected in the cheatsheet declares an alias, so a future alias-less type fails loudly rather than vanishing.
- NB: if TASK-000269 restructures `workflow.md.j2` to add the lifecycle section, keep this guard in sync there. Coordinate line references with 269.

## Acceptance
- F5: a forced build error on a declared custom type surfaces a diagnosable error (not "No such command"); `sq --help` still degrades gracefully on an invalid spec.
- F6: a test fails loudly if a non-meta cheatsheet work type declares no alias.
- **AC#7/#8:** TASK-256 goldens stay green; no built-in surface change.
- Gates clean: `uv run pyright && uv run ruff check . && uv run ruff format --check .`.

## Files
`_cli/__init__.py`, `_rendering/templates/workflow.md.j2` (test only, or in coordination with 269), a new test.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 270 add-subtask "<title>"`; track with `sq task 270 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-01T15:40:17Z] Elias Python:
  - TASK-270 done. Both Low findings from REV-265 closed.
  - **F5 — except narrowing (both group classes):** Scoped the broad `except Exception: return None` to the spec-resolution region only in both `_CustomTypeGroup.get_command` (_cli/__init__.py) and `_CustomCreateGroup.get_command` (_cli/_create.py). Once `canonical`/`cmd_name` is confirmed as a declared custom work type, build errors propagate rather than becoming a silent 'No such command'. Spec-resolution failures (before the type is confirmed) still degrade gracefully. Three tests added: resource-group build error propagates, create-group build error propagates, corrupt-spec still degrades.
  - **F6 — alias-guard defence test:** Added `test_f6_all_builtin_work_types_have_aliases` to tests/test_custom_type_cli.py. It iterates all non-meta `spec.work_types()` in the bundled spec and asserts each declares at least one alias, so a future alias-less built-in type fails loudly rather than silently vanishing from the workflow cheatsheet. No change to workflow.md.j2 or rendered output — goldens stay green.
  - **Gates:** pyright 0 errors · ruff check all passed · ruff format all formatted · pytest full suite exit 0 (1 skip, 0 failures, all dots).
  - @manager ready for re-review.
<!-- sq:discussion:end -->
