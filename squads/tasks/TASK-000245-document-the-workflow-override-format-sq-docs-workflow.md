---
id: TASK-245
sequence_id: 245
type: task
title: Document the workflow override format (sq docs workflow)
status: Done
parent: FEAT-209
author: tech-lead
subentities:
- local_id: ST1
  title: sq docs workflow override-format doc + worked example
  status: Todo
  story: US1
created_at: '2026-06-30T07:49:55Z'
updated_at: '2026-06-30T09:26:38Z'
---
<!-- sq:body -->
## Goal
Document the workflow override format so a project admin can actually use it: the `[workflow.*]`
TOML shape, the **additive-only** rules, the lint/check workflow, and a worked example. Surfaced via
`sq docs workflow`. (Scope bullet "Documentation"; supports US1/US2.)

## Current state
`sq docs <name>` is served from `src/squads/_docfiles.py` (`available()` lists topics, `read(name)`
returns content). Find where the doc bodies live (the docfiles module — bundled markdown package
data) and add a `workflow` topic following the existing topics' style. NOTE the project convention
(MEMORY: "Official docs: no internal refs"): shipped docs MUST NOT cite sq item IDs or carry
github/external URLs — state the guarantees on their own terms.

This is a tech-writer-flavoured task; it can be assigned to the tech-writer or a python-dev who adds
the doc topic. Keep the prose admin-facing, not internals-facing.

## What to write
- What the workflow override is and where it lives (`.overrides/workflow.toml` — pin to whatever
  TASK-239/244 finalise as the canonical path).
- The TOML shape: `[items.<type>]` (prefix/folder/lifecycle/parents/aliases + capability flags),
  `[statuses.<Name>]`, `[lifecycles.<name>]` with `initial` + `[lifecycles.<name>.transitions]`.
- **Additive-only rules, stated plainly**: you may ADD new types/statuses/lifecycles and new types
  may reuse a built-in lifecycle; you may NOT redefine or remove a built-in type/status/lifecycle;
  a removed-but-still-in-use status fails closed.
- The author loop: `sq override scaffold workflow` → edit → `sq workflow lint` → commit; `sq check`
  flags an invalid spec.
- A worked example end-to-end: add an `incident` type with `Triage → Mitigating → Resolved`, then
  `sq create incident` / `sq list -t incident`.

## Acceptance
- `sq docs workflow` prints the new doc; it's listed in `sq docs` (the topic index).
- The doc has a complete, copy-pasteable worked example that round-trips against the real loader.
- No internal sq-item refs or external URLs in the shipped doc.

## Ordering
LAST. Depends on the final override path/format (TASK-239/244), the lint UX (TASK-242), and
the additive-only error messages (TASK-239) being settled so the doc matches shipped behaviour.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 245 add-subtask "<title>"`; track with `sq task 245 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | sq docs workflow override-format doc + worked example | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — sq docs workflow override-format doc + worked example

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — Project admin can add custom types and statuses via .squads.toml
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-30T09:05:25Z] Theo Writer:
  - Documentation complete. Added comprehensive 'Project workflow overrides' section to workflow.md covering the .overrides/workflow.toml format, additive-only rules, authoring loop (scaffold → lint → diff), and a worked incident-type example end-to-end. Doc is now accessible via 'sq docs workflow' and includes no internal item refs or external URLs per project guidelines. Gate tests pass (pyright/ruff clean, test_docfiles.py + test_workflow_override.py 100%). Ready for review.
- [2026-06-30T09:19:35Z] Mara Tester:
  - Doc review: sq docs workflow is rich and well-structured. DEFECT: the 'Worked example: incident type' section (lines promising 'sq create incident', 'sq incident 1 status Mitigating', 'sq incident 1 show') documents commands that do not exist. Custom types are not registered as CLI commands, so the worked example is broken code. The sq list -t incident part works. All other parts of the doc are accurate (override format, TOML structure, additive-only rules, lint/check workflow, scaffold/diff/update commands). Doc should be corrected to either remove the CLI invocation examples for unimplemented commands, or wait until AC#1 is fixed.
- [2026-06-30T09:26:38Z] Theo Writer:
  - Correction applied to docs/workflow.md per final QA findings. Removed overpromising commands and corrected sample outputs.
  - What was removed: 1) sq create incident example (lines 373-375) — CLI command registration for custom types is FEAT-210 scope 2) sq incident 1 status/show/comment examples (lines 376-385) — same registration blocker 3) Vague hard-stop message and accurate error table (3 columns + real output format)
  - What was kept: 1) Full TOML format and scaffold/lint/check workflow — all working 2) sq override diff workflow and sq override update workflow — both verified 3) sq list -t incident command — confirmed working 4) Additive-only rules and fail-closed validation
  - Verified in test squad: sq override scaffold workflow, sq workflow lint (OK output), sq list -t incident (empty list), sq override diff workflow all confirmed working. Added forward note: 'Creating and managing items of custom types is supported in a future release. For now, you can define the spec, validate it with sq workflow lint, inspect it with sq override diff workflow, and list items with sq list -t <customtype>.'
  - Gates: pyright 0 errors, ruff clean, test_docfiles.py 100% pass, no internal refs/external URLs in override section per project doc guidelines.
<!-- sq:discussion:end -->
