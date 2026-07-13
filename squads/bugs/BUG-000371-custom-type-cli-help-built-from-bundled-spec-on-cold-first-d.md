---
id: BUG-371
sequence_id: 371
type: bug
title: Custom-type CLI help built from bundled spec on cold first dispatch
status: Verified
author: reviewer
assignee: python-dev
priority: medium
refs:
- FEAT-336
- REV-360
created_at: '2026-07-10T03:48:50Z'
updated_at: '2026-07-13T07:15:54Z'
---
<!-- sq:body -->
`build_item_app` reads the module-global active spec via `common.get_active_spec()`, which returns the **bundled** spec before the root callback's `_bind_active_spec` runs. Click resolves a subcommand group's `get_command` before the root callback fires, so a **cold, first-in-process** `--help` / introspection of a project-declared **custom** type builds its command tree from the bundled spec — missing that type's `add-<kind>` surface and showing wrong retype-target / priority help.

**Impact:** help/introspection only. It does NOT affect enforcement or data — command handlers re-read the live spec after the callback binds it, and normal dispatch binds the spec before the handler runs. So the bug is a wrong *first-hit --help/capability view* for a custom type, not a correctness/data issue. Pre-existing; surfaced (not caused) by TASK-365's spec-derived help.

**Fix sketch:** thread the ctx-resolved spec (`_resolve_spec_for_ctx(ctx)`) into `build_item_app`, or bind the active spec before the subcommand tree is built, in `src/squads/_cli/__init__.py`. Out of scope for the FEAT-336 docs pass (disjoint files); filed for scheduling.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-13T07:05:44Z] Catherine Manager:
  - Dispatching @python-dev to fix. Scope: help/introspection only — thread the ctx-resolved spec into build_item_app (or bind the active spec before the subcommand tree is built) in src/squads/_cli/__init__.py, per the fix sketch. Move to InProgress on pickup, Fixed on completion. Add a regression test proving a cold first --help on a custom type shows that type's add-<kind> surface.
- [2026-07-13T07:10:41Z] Elias Python:
  - Fixed: threaded the ctx-resolved spec into build_item_app instead of it re-reading common.get_active_spec() internally.
  - src/squads/_cli/_items.py: build_item_app(item_type, spec=None) now accepts an optional resolved WorkflowSpec, defaulting to get_active_spec() when not passed (preserves the static import-time registration path).
  - src/squads/_cli/__init__.py: _CustomTypeGroup.get_command now passes spec=spec (the already ctx-resolved spec used to confirm canonical is a declared custom type) into build_item_app, instead of letting it silently re-resolve a possibly-stale bundled spec before the root callback binds the real one.
  - Regression test: tests/cli/test_custom_type_end_to_end.py::test_cold_first_help_on_a_custom_type_shows_its_declared_subentity_and_retype_surface — declares a custom type with a subentity_kind and asserts a cold, first-in-process 'sq incident --help' lists add-action, and 'sq incident retype --help' lists incident as a valid target. Verified it fails pre-fix (missing add-action) and passes post-fix.
  - Gates: pyright + ruff check + ruff format --check all clean. Targeted tests green (tests/cli/test_custom_type_end_to_end.py + test_custom_subentity_kind_cli.py + test_custom_status_vocab_flow.py + test_workflow_cheatsheet_reflects_custom_type_cli.py + test_spec_context_binding_order.py, 36 passed). Did NOT run the full suite — that's the main loop's gate.
- [2026-07-13T07:15:16Z] Paul Reviewer:
  - Reviewed the working-tree fix (read-only) — approve, no findings. Root cause correctly addressed: build_item_app no longer re-reads get_active_spec() internally; get_command threads the ctx-resolved spec (from ctx.params['dir'] on cold dispatch, bound active spec when warm), so the built command tree matches the spec used to decide the type exists. Cache is now sound — the wrong bundled tree that was cached under the canonical name for the whole process is now the correct override-merged tree. Regression test is non-vacuous: cold 'incident --help' (subentity_kind=action) asserts add-action + retype target — both derive from the passed spec, so pre-fix (bundled spec, no incident) they're absent and the test fails; autouse _reset_active_spec guarantees the cold premise. No regression on non-custom/warm paths (static import-time registration + warm dispatch keep the default get_active_spec() behavior byte-identically). ruff check/format clean; type annotation valid.
- [2026-07-13T07:15:54Z] Catherine Manager:
  - Verified & closed. Fix: build_item_app now takes the ctx-resolved spec from _CustomTypeGroup.get_command (2-file minimal change, __init__.py + _items.py). Gates: full default suite green (exit 0, no failures); reviewer (Paul) approved with no findings; behavior-named regression test proves cold first --help on a custom type shows its add-<kind> + retype surface (fails pre-fix). Ready to fold into the next commit.
<!-- sq:discussion:end -->
