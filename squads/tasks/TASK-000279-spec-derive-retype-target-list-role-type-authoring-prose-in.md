---
id: TASK-000279
sequence_id: 279
type: task
title: Spec-derive retype-target list + role/type authoring prose in sq workflow
status: Draft
parent: FEAT-000211
author: tech-lead
priority: medium
created_at: '2026-07-02T09:20:18Z'
updated_at: '2026-07-02T09:21:56Z'
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
<!-- sq:discussion:end -->
