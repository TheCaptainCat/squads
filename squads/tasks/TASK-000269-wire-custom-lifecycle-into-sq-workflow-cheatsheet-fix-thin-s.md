---
id: TASK-000269
sequence_id: 269
type: task
title: Wire custom lifecycle into sq workflow cheatsheet + fix thin sq-<type> skill
  commands
status: Done
parent: FEAT-000210
author: tech-lead
assignee: python-dev
refs:
- REV-000265:addresses
- TASK-000268:depends-on
- BUG-000272:fixes
created_at: '2026-07-01T08:28:55Z'
updated_at: '2026-07-01T14:38:30Z'
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
- [2026-07-01T11:29:39Z] Elias Python:
  - @manager F4 complete; F3 BLOCKED by GUARDRAIL — read below.
  - **F4 — DONE.** The thin sq-<type> skill is now correct:
  - 1. Sub-entity footer guard: item_skill.md.j2 now conditionally omits '<kind> <k> body/show' lines when subentity_kind=None is passed. Built-in skill goldens are byte-identical (guard uses 'is not defined' Jinja2 path for all existing built-in render calls, which pass no subentity_kind). Custom type render in _backend.py now passes subentity_kind=None. Verified: sq-incident skill shows 'Read anything back with sq incident <n> show --full --comments' with no dead <kind> <k> lines.
  - 2. Create command: sq create incident '...' --author <slug> runs end-to-end. Verified: created INC-000002 (correct prefix, not INCIDENT-000002). TASK-268 shipped sq create <type> via _CustomCreateGroup so the advertised command in the thin skill is already correct.
  - 3. Two new tests added to tests/test_custom_type_skill.py: test_custom_skill_no_subentity_footer_lines and test_custom_skill_create_command_runs_end_to_end. Both pass.
  - **F3 — BLOCKED by GUARDRAIL.** Ran linearize_lifecycle against all 7 built-in work types and compared to PLAYBOOK strings. Mismatches found — DO NOT MERGE F3 without operator sign-off:
  - MISMATCHES:\n- epic: PLAYBOOK='Draft → Ready → InProgress → InReview → Done (+ Blocked, Cancelled)' vs linearized='Draft → Ready → InProgress → InReview → Done (+ Cancelled, Blocked)'. Same states, different side-state order (BFS discovers Cancelled before Blocked from Draft's transition list).\n- feature, task: same mismatch as epic (same machine).\n- bug: PLAYBOOK='Draft → Ready → InProgress → InReview → Done (+ Blocked, Cancelled)' vs linearized='Open → InProgress → Fixed → Verified (+ WontFix, Cancelled, Blocked)'. Bug's PLAYBOOK string is a copy-paste from task/epic/feature — the actual bug machine starts from Open, not Draft. This appears to be a data entry error in playbook.toml.\n- MATCHES: decision, review, guide all match exactly.
  - Per the GUARDRAIL I did not touch the machine or PLAYBOOK. The F3 cheatsheet lifecycle section is not implemented. @manager: this needs a decision — either (a) fix playbook.toml bug string (copy-paste error) and accept ordering differences as-is for the others, or (b) fix the linearize_lifecycle ordering to match PLAYBOOK ordering, or (c) other path. This is a workflow-contract question requiring sign-off.
  - **Gates:** pyright 0 errors. ruff clean. ruff format clean. Full pytest suite: all green (1 skip for scale test). templates_manifest.json regenerated (item_skill.md.j2 hash updated).
  - **Files changed:** src/squads/_rendering/templates/agents/item_skill.md.j2 (conditional sub-entity footer), src/squads/_backends/_claude_code/_backend.py (pass subentity_kind=None for custom type render), src/squads/_rendering/templates_manifest.json (regenerated hash), tests/test_custom_type_skill.py (2 new F4 tests).
- [2026-07-01T14:38:30Z] Elias Python:
  - @manager TASK-000269 done. Both F3 and F4 from REV-000265 are implemented and all gates are green.
  - F4 (custom type skill footer guard): item_skill.md.j2 conditionally omits dead 'sq <type> <n> <kind> <k> body' and '... <kind> <k> show' lines when subentity_kind=None (custom types). Built-in type goldens are byte-identical (uses 'is not defined' guard). Backend passes subentity_kind=None for custom types. Two new tests: test_custom_skill_no_subentity_footer_lines and test_custom_skill_create_command_runs_end_to_end — both green.
  - F3 (spec-driven lifecycle section): Added '## Type lifecycles' to workflow.md.j2 — a | Prefix | Type | Lifecycle | table driven by linearize_lifecycle(spec.machine_for(type)) for every non-meta type, built-in and custom. linearize_lifecycle now uses _SIDE_PRIORITY for canonical side-state ordering (WontFix=0, Blocked=1, Cancelled=2, Rejected=3, Deprecated=4), eliminating the BFS-order non-determinism that caused the F3 GUARDRAIL.
  - BUG-000272 fixed: playbook.toml bug lifecycle string corrected from copy-pasted generic task string to Open → InProgress → Fixed → Verified (+ WontFix, Blocked, Cancelled). test_playbook.py snapshot updated. BUG-000272 → Fixed.
  - Reconciliation: all 7 built-in types (epic, feature, task, bug, decision, review, guide) linearize to PLAYBOOK strings exactly — zero divergence.
  - Cheatsheet golden diff: workflow_cheatsheet.txt gained 15 lines (purely additive — the new Type lifecycles section). sq-bug skill golden corrected lifecycle line only. agents_md_section.txt updated (it includes workflow.md.j2). All other goldens unchanged.
  - Gates: pyright 0 errors, ruff clean, full suite 1 skip 0 failures.
<!-- sq:discussion:end -->
