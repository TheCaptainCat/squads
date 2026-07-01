---
id: TASK-000269
sequence_id: 269
type: task
title: Wire custom lifecycle into sq workflow cheatsheet + fix thin sq-<type> skill
  commands
status: Draft
parent: FEAT-000210
author: tech-lead
refs:
- REV-000265:addresses
- TASK-000268:depends-on
created_at: '2026-07-01T08:28:55Z'
updated_at: '2026-07-01T08:30:41Z'
---
<!-- sq:body -->
**Closes REV-000265 F3 (Medium) + F4 (Medium). Both gated on the create path (TASK-000268).**

## F3 — sq workflow renders no lifecycle string
**File:** `_rendering/templates/workflow.md.j2`. The spec-rendered cheatsheet renders ONLY the alias table (`{% for item_type, item_spec in spec.items.items() %}` → Canonical/Aliases/Example). It renders **no lifecycle string and no prefix for any type** — `linearize_lifecycle`/`machine_for` are built (TASK-262) and used in the generated skill, but never wired into the cheatsheet. So a valid `incident` override shows `incident | inc | sq inc <n> show` but its lifecycle (`Open → Done (+ WontFix)`) never appears. AC#2/US2 ("output includes the custom type's prefix, lifecycle string, and aliases") is only partially met (aliases yes, prefix + lifecycle no); AC#3 unmet.

**Fix:** add a spec-driven section to `workflow.md.j2` that, for each non-meta work type, renders `prefix` + `linearize_lifecycle(spec.machine_for(type))`. Keep it strictly in the **dynamic** region — the static FEAT-000013 contract partial (`workflow_static.md.j2`: ref-kinds table, retype, remove-vs-cancel) stays literal and untouched, never config-editable. Confirm built-in derived lifecycle strings reconcile with what the TASK-256 golden captures (a known golden-drift risk).

**Adjacent (reconcile with PO, not necessarily a code change):** AC#4 says `sq sync` regenerates *CLAUDE.md* to include the custom type, but `claude_section.md.j2` never included the cheatsheet — the vocabulary lands in the `squads` skill and AGENTS.md, not CLAUDE.md. Likely an AC-wording artifact. Flag to @product-owner; do not silently expand CLAUDE.md scope.

## F4 — thin sq-<type> skill advertises a broken command
**File:** `_interactions/__init__.py::custom_item_skill_commands` (~244-261) + the generated skill body. The thin skill emits `sq create {type} "…" --author <slug>` as its first command — broken per F2. Once TASK-000268 lands a working create path, this command string must match the actual surface: if 268 ships `sq create <type>`, the current string is already right; if it ships a `create` verb on the resource group, update this line. **Do not close F4 until 268 lands AND the advertised command is verified to run.** Secondary (lower stakes): the shared footer references `sq <type> <n> <kind> <k> body`/`show` (sub-entity verbs) — custom types declare no sub-entity kind, so guard those out of the custom-type skill (brand-new sub-entity kinds are FEAT-212 scope, out of this feature).

## Depends on TASK-000268 (and thereby 267)
Both F3 and F4 are behaviourally gated on a working, correctly-prefixed create path.

## Acceptance
- AC#3/US2: `sq workflow` output for a declared custom type includes its prefix AND auto-linearized lifecycle string alongside the alias row.
- F4: the generated `sq-<type>` skill's advertised create command runs successfully end-to-end (verify, don't assume); dead sub-entity verbs removed from custom-type skills.
- **AC#7/#8:** the static FEAT-013 sections are untouched; TASK-256 goldens (`sq workflow`, CLAUDE.md/AGENTS.md sections, bundled `sq-<type>` skill bodies) stay green — pin roster/clock/flags.
- Gates clean: `uv run pyright && uv run ruff check . && uv run ruff format --check .`.
- **Test end-to-end:** declare a custom type, assert `sq workflow` shows its lifecycle+prefix, and that the generated thin skill's create command executes and creates a correctly-prefixed item.

## Files
`_rendering/templates/workflow.md.j2`, `_interactions/__init__.py`, the shared item-skill template footer.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 269 add-subtask "<title>"`; track with `sq task 269 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
