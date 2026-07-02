---
id: TASK-000279
sequence_id: 279
type: task
title: Spec-derive retype-target list + role/type authoring prose in sq workflow
status: Done
parent: FEAT-000211
author: tech-lead
assignee: python-dev
priority: medium
created_at: '2026-07-02T09:20:18Z'
updated_at: '2026-07-02T12:57:11Z'
---
<!-- sq:body -->
## Goal — spec-derive two static-prose artifacts in the sq workflow cheatsheet

Pierre ruled both of these IN (2026-07-01 comments on FEAT-211). Runs under the TASK-000275
golden guard — bundled-team output must stay byte-identical after the derivation.

### (A) Retype-target type list — the clear, less-debatable fix

`workflow_static.md.j2:` `Valid targets: epic, feature, task, bug, decision, review, guide.`
is hardcoded. Custom types ARE retypeable (`build_item_app._cmd_retype`), so this line must
render from the spec — the non-meta, retype-eligible types (`spec.items` where `not is_meta`).
For the bundled team the rendered list must reproduce the current seven names in the current
order (golden-locked).

NOTE: this line currently lives in `workflow_static.md.j2`, which is the FEAT-013 literal
static file. Moving a spec-derived loop INTO that file conflicts with "static stays literal".
**Design decision:** lift ONLY this one line out of `workflow_static.md.j2` into the dynamic
`workflow.md.j2` (rendered from `spec`), leaving the rest of `workflow_static.md.j2`
(ref-kinds table, retype mechanics prose, remove-vs-cancel) fully literal. Keep the surrounding
Retype prose static; only the target-list line becomes a spec loop.

### (B) Role→type authoring prose — render generically from playbook + roster

`workflow.md.j2:5-22` — the `Product owner → features`, `Tech lead → tasks under a feature`,
manager-triage bullets, the `epic → feature → task` hierarchy line, and the `FEAT-`/`BUG-`
prefix examples are hardcoded bundled-team narrative. Pierre's decision: these SHOULD render
generically from the playbook spec (playbook.toml / roles, ADR-000226) so a project with custom
roles/types sees itself in `sq workflow`.

Design work required (call out risks in the return summary):
- The role→type ASSOCIATIONS live in playbook.toml, but the current text is a crafted
  NARRATIVE with example commands, not a table. Decide how much to auto-generate from playbook
  interaction data vs. template with roster/type substitution. Recommend: a generic
  "who-authors-what" rendering driven by the playbook's author/interaction data + the spec's
  type prefixes, with example commands templated from the resolved type names/prefixes — so the
  bundled team still renders the same prose (byte-identical golden) while a custom setup renders
  its own roles/types.
- Load the playbook spec into the render context (the renderer currently gets only `spec` — the
  WorkflowSpec). Wire the playbook/roster in via the same render path used by
  `_print_cheatsheet` and by `sq sync` (CLAUDE.md / AGENTS.md / squads-skill regeneration) so
  ALL consumers of `workflow.md.j2` stay consistent.

### KEEP LITERAL (do NOT spec-derive)

FEAT-013 stability-contract prose in `workflow_static.md.j2`: the ref-kinds table, retype
mechanics, remove-vs-cancel, and the alias-evolution rule. That split is the whole point of
TASK-000261 — only (A)'s single target-list line moves out.

## Acceptance

1. `sq workflow` for the BUNDLED team renders byte-identical to the TASK-000275 golden (both the
   retype-target list and the authoring prose).
2. A custom squad (custom type + custom role authoring it) sees its own types/roles in the
   retype-target list and the authoring prose.
3. `sq sync`-regenerated CLAUDE.md / AGENTS.md / squads skill reflect the same spec-derived
   sections (no consumer left rendering the old hardcoded text).
4. FEAT-013 static prose is verified unchanged (a test asserting the literal sections).

## Files
`src/squads/_rendering/templates/workflow.md.j2`,
`src/squads/_rendering/templates/workflow_static.md.j2` (remove only the target-list line),
`src/squads/_cli/_workflow_cmd.py` (`_print_cheatsheet` render context),
the `sq sync` / backend render path that emits the CLAUDE.md/AGENTS.md workflow section and the
squads skill, `src/squads/_interactions.py` / playbook loader for the authoring data.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 279 add-subtask "<title>"`; track with `sq task 279 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-02T12:46:02Z] Elias Python:
  - Both artifacts spec-derived; bundled goldens byte-identical (verified via templates_manifest regen + full pytest, 0 failures).
  - (A) Retype-target list: lifted the single 'Valid targets: …' line out of workflow_static.md.j2 into a spec-driven loop over spec.items (non-meta), left everything else in the static partial literal. Custom types now appear in the retype target list.
  - (B) Authoring prose: added authoring_owner(item_type) + parent_chain(spec, item_type) to _interactions/__init__.py, driven by the existing CREATE_LANES declarative map (already table-pinned to playbook.toml) + the bundled role catalog (title lookup) + WorkflowSpec (parent chain, subentity_kind, prefix). Registered as Jinja globals in _rendering/_engine.py. Rewired workflow.md.j2's product-owner→feature / tech-lead→task bullets and the epic→feature→task hierarchy line to render from these helpers, each gated so it's silently omitted (not fabricated) when a type has no single in-lane owner or the shape assumptions (subentity_kind, parent_required) don't hold. Also rewired CLAUDE.md's separately-worded claude_section.md.j2 Team-workflow block (a distinct hand-written prose block, not an include of workflow.md.j2) the same way, threading spec= into its render call in _backend.py — so no consumer is left with the old hardcoded role/type names.
  - Scope note on B: CREATE_LANES itself is still a fixed bundled-role Python dict — there is no override mechanism yet for custom ROLES authoring custom TYPES (only custom types via .overrides/workflow.toml exist today; a project can't yet define its own roles). A custom type with no CREATE_LANES entry simply gets no authoring bullet (graceful, tested), rather than a fabricated one. Building a full custom-role/lane spec would be a separate, larger feature; flagging per the task's 'don't over-reach' guidance rather than attempting it here.
  - AGENTS.md and the squads skill were already consistent (they {% include %} workflow.md.j2); CLAUDE.md was the outlier with its own duplicate (differently-worded) hardcoded block — now spec-driven too, still in its own wording (not merged into workflow.md.j2, to avoid pulling in the alias/lifecycle/retype tables CLAUDE.md never had).
  - Verification: git diff on tests/goldens/ shows zero content changes; templates_manifest.json updated (3 legitimately-changed templates: workflow.md.j2, workflow_static.md.j2, claude/claude_section.md.j2) via scripts/gen_template_manifest.py; added tests/test_workflow_authoring_prose.py (14 tests: helper unit tests, spec-rename tracking proof via a synthetic 'initiative' parent type, graceful-omission cases) plus updated two TASK-261 tests whose assertions predated the A/B split (they now scope the byte-identical check to start after the 'Valid targets' line, and positively assert the custom type appears there). Full suite: 0 failures. pyright/ruff clean.
  - @reviewer ready for review.
- [2026-07-02T12:56:11Z] Paul Reviewer:
  - Independent review complete — APPROVED (REV-000286, Approved). Both artifacts are correctly spec-derived and the FEAT-013 byte-identical contract holds.
  - Part A: only the 'Valid targets' line moved out of workflow_static.md.j2 into a spec loop; the rest of the static partial (retype mechanics, remove-vs-cancel, ref-kinds) stays literal — verified.
  - Part B: authoring_owner()/parent_chain() gating is correct — bullets are silently omitted (never fabricated) on no-single-owner (guide has 2 owners → None), dev-sentinel (RoleNotFoundError → None), or shape mismatch (subentity_kind/parent_required). Every consumer is spec-driven: AGENTS.md + squads skill {% include %} workflow.md.j2; CLAUDE.md's separate claude_section.md.j2 block was rewired and spec= threaded in _backend.py (resolved once, never None). No hardcoded consumer left.
  - Byte-identical independently confirmed: rendered a bundled squad from a4b4aa8 (worktree) vs working tree with roster held constant — CLAUDE.md, AGENTS.md, sq workflow all identical; squads skill identical except its own timestamps. TASK-261 test window move (## Retype → **Status behaviour:**) is justified: the skipped region stays guarded by test_static_sections_present_* + test_retype_section_exact_intro + the full bundled golden, and the new custom-type assertion is real. 14 new tests genuinely prove derivation (synthetic initiative-reparent proof + graceful omission). pyright/ruff clean; targeted suites green.
  - One LOW finding (F1, non-blocking): Jinja | capitalize in workflow.md.j2 would lowercase an acronym role title ('QA' → 'Qa engineer') for a hypothetical custom-role author — harmless for the bundled team and irrelevant until custom roles exist; noted for the future custom-role/lane feature. Deferring full custom-role/lane support to a separate feature is the right call.
  - @manager good to mark TASK-279 Done and close FEAT-211.
<!-- sq:discussion:end -->
