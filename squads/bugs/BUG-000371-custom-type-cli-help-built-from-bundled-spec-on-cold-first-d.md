---
id: BUG-371
sequence_id: 371
type: bug
title: Custom-type CLI help built from bundled spec on cold first dispatch
status: Open
author: reviewer
priority: medium
refs:
- FEAT-336
- REV-360
created_at: '2026-07-10T03:48:50Z'
updated_at: '2026-07-10T03:48:50Z'
---
<!-- sq:body -->
`build_item_app` reads the module-global active spec via `common.get_active_spec()`, which returns the **bundled** spec before the root callback's `_bind_active_spec` runs. Click resolves a subcommand group's `get_command` before the root callback fires, so a **cold, first-in-process** `--help` / introspection of a project-declared **custom** type builds its command tree from the bundled spec — missing that type's `add-<kind>` surface and showing wrong retype-target / priority help.

**Impact:** help/introspection only. It does NOT affect enforcement or data — command handlers re-read the live spec after the callback binds it, and normal dispatch binds the spec before the handler runs. So the bug is a wrong *first-hit --help/capability view* for a custom type, not a correctness/data issue. Pre-existing; surfaced (not caused) by TASK-365's spec-derived help.

**Fix sketch:** thread the ctx-resolved spec (`_resolve_spec_for_ctx(ctx)`) into `build_item_app`, or bind the active spec before the subcommand tree is built, in `src/squads/_cli/__init__.py`. Out of scope for the FEAT-336 docs pass (disjoint files); filed for scheduling.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
