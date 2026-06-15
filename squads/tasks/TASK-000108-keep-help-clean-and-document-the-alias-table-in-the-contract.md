---
id: TASK-000108
sequence_id: 108
type: task
title: Keep help clean and document the alias table in the contract
status: Done
parent: FEAT-000036
author: tech-lead
refs:
- FEAT-000013
subentities:
- local_id: ST1
  title: Hide aliases from root help; mention the table once (epilog or type help)
  status: Done
  story: US2
- local_id: ST2
  title: Render the alias table in the workflow cheatsheet with the add-only rule;
    tie into FEAT-000013 contract
  status: Done
  story: US2
created_at: '2026-06-15T07:42:48Z'
updated_at: '2026-06-15T08:10:56Z'
---
<!-- sq:body -->
Keep the type-command aliases (from TASK-000107) out of help clutter, document the full table in exactly one place, and record it as frozen grammar in the stability contract.

## Help stays clean

Root sq --help must list only the seven canonical type commands. Registering aliases with hidden=True (TASK-000107) already keeps them off the root list — this task verifies it with a help-output test and adds the one-line mention: surface the alias table once, either via the canonical type command's help text or the root app epilog (src/squads/_cli/__init__.py app=typer.Typer(epilog=...)). Pick the epilog or per-type help line; don't duplicate the table in both.

## Docs / workflow cheatsheet

Add the alias table to the shared workflow cheatsheet partial src/squads/_rendering/templates/workflow.md.j2 (rendered by both the squads skill and sq workflow), mirroring the existing 'Ref kinds' table format at the tail of that file. Render the table from the single canonical ALIASES map introduced in TASK-000107 (pass it into the Jinja context) rather than hand-typing it, so docs can't drift from the routing. Also surface it in docs/workflow.md if that doc carries the same content.

## Contract tie-in (FEAT-000013)

The alias table joins the CLI-grammar tier of the stability contract: adding aliases later is additive and allowed, removing or repurposing one is breaking and is not. FEAT-000013 owns creating docs/stability.md; that doc does not exist yet. This task records the add-only evolution rule next to the table in the workflow cheatsheet and leaves a ref/note so FEAT-000013's contract doc picks up the table. Do not author docs/stability.md here — coordinate via the ref to FEAT-000013.

## Acceptance

Root --help shows only the seven canonical names (asserted in a CLI test). The alias table appears in sq workflow output and each type's help (or the root epilog). The add-only evolution rule is recorded. uv run pyright && ruff check && ruff format --check && pytest all green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 108 add-subtask "<title>"`; track with `sq task 108 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Hide aliases from root help; mention the table once (epilog or type help) | US2 |
| ST2 | Done |  | Render the alias table in the workflow cheatsheet with the add-only rule; tie into FEAT-000013 contract | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Hide aliases from root help; mention the table once (epilog or type help)

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US2 — As a newcomer reading help and docs, I want aliases out of the command list but documented in one table, so that discoverability doesn't cost clarity
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Render the alias table in the workflow cheatsheet with the add-only rule; tie into FEAT-000013 contract

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — As a newcomer reading help and docs, I want aliases out of the command list but documented in one table, so that discoverability doesn't cost clarity
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-15T08:00:17Z] Elias Python:
  - Implemented TASK-000108 (US2 surface/docs for FEAT-000036).
  - ST1 (help clean): Aliases already hidden via hidden=True (TASK-000107). Added epilog to root app mentioning aliases and pointing to sq workflow. Existing test_aliases_not_in_root_help verified; added test_canonical_type_commands_present_in_root_help and test_root_help_epilog_mentions_alias_table.
  - ST2 (workflow cheatsheet): Added 'Type-command aliases' section to workflow.md.j2 above the Ref kinds table. Table is rendered from TYPE_ALIASES passed as Jinja2 context (never hardcoded). Added the add-only evolution rule referencing FEAT-000013 as the stability contract owner. Updated workflow() in _cli/_main.py and the squads_skill render in _backends/_claude_code/_backend.py to pass type_aliases context. Also updated templates_manifest.json. Added test_workflow_output_contains_alias_table and test_workflow_output_contains_add_only_evolution_rule.
  - Gate: 602 passed, 1 skipped; pyright 0 errors; ruff clean.
  - @reviewer ready for review.
- [2026-06-15T08:05:25Z] Paul Reviewer:
  - Reviewed under REV-000109 — **Approved.** Help stays clean (aliases hidden=True; root --help shows only the 7 canonical names; epilog mentions aliases and points to sq workflow). The alias table is rendered from TYPE_ALIASES (Jinja context, not hardcoded) in workflow.md.j2 and propagates through {% include %} into the generated squads skill body (backend passes type_aliases) — verified both sq workflow output and squads/agents/skills/squads.md carry it. templates_manifest.json hash regenerated and matches (sha256 verified). Add-only evolution rule recorded with ref to FEAT-000013; docs/stability.md correctly left to FEAT-000013. Gate green.
- [2026-06-15T08:07:36Z] Mara Tester:
  - QA verification complete — PASS with one gap noted.
  - **Acceptance criterion (TASK-000108):** Root --help lists only the 7 canonical type commands (epic/feature/task/bug/decision/review/guide). Aliases absent from the list. Root --help epilog explicitly mentions aliases and points to sq workflow. Verified in test_aliases_not_in_root_help, test_canonical_type_commands_present_in_root_help, test_root_help_epilog_mentions_alias_table — all pass.
  - **sq workflow alias table:** Alias table present in sq workflow output, rendered dynamically from TYPE_ALIASES via Jinja2 context (not hardcoded). Includes all 7 types with their aliases and example commands. Add-only evolution rule present, FEAT-000013 referenced. Verified in test_workflow_output_contains_alias_table and test_workflow_output_contains_add_only_evolution_rule — both pass.
  - **squads skill (sq sync):** workflow.md.j2 includes the alias table via Jinja2 {%include%}; squads/agents/skills/squads.md carries it after sq sync. This is the managed-file pathway — correct behavior.
  - **Gap — docs/workflow.md not updated:** sq docs workflow (which reads docs/workflow.md) does not contain the alias table. The feature acceptance says 'the alias table appears in sq docs workflow'. TASK-000108 used the conditional 'Also surface it in docs/workflow.md if that doc carries the same content' and chose not to add it. The task-level acceptance says 'sq workflow output and each type's help (or the root epilog)' — not sq docs workflow — and that requirement is met. This is an ambiguity between the feature-level AC and the task-level AC. Not flagging as a failure, but worth resolving: either update docs/workflow.md or confirm the feature acceptance meant sq workflow (the terminal command), not sq docs workflow. @tech-lead for visibility.
  - **Gate:** 602 passed 1 skipped; pyright 0 errors; ruff clean.
- [2026-06-15T08:10:21Z] Theo Writer:
  - Closed the docs gap identified in QA verification: added the 'Type-command aliases' section to docs/workflow.md.
  - Section includes the full 7-type alias table, full equivalence note, canonical output rule, and add-only evolution rule (FEAT-000013 reference) — matching the structure and content from workflow.md.j2.
  - Verified: sq docs workflow displays the new section; all tests pass.
  - @qa ready to confirm the feature-level AC 'appears in sq docs workflow' is now satisfied.
<!-- sq:discussion:end -->
