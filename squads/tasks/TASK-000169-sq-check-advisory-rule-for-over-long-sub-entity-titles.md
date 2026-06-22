---
id: TASK-000169
sequence_id: 169
type: task
title: sq check advisory rule for over-long sub-entity titles
status: Done
parent: FEAT-000166
author: tech-lead
refs:
- ADR-000167
subentities:
- local_id: ST1
  title: Add sq check pass walking all sub-entity titles
  status: Done
  story: US2
- local_id: ST2
  title: Report over-long titles as advisory findings with ID/kind/index/length
  status: Done
  story: US2
created_at: '2026-06-23T08:37:43Z'
updated_at: '2026-06-23T09:53:45Z'
---
<!-- sq:body -->
Add an advisory sq check rule that audits every sub-entity title across all item types and flags those over the threshold. Implements US2.

## Design (per ADR-000167)
- Reuse the same single threshold constant from _interactions.py (TITLE_ADVISORY_MAX = 120) — same value as the authoring-time check, one source of truth.
- New pass in sq check that walks every sub-entity (findings / subtasks / stories) across all items and reports titles >120 chars as ADVISORY findings, not structural errors.
- This audits the existing corpus in place — no migration, no auto-fix. Expect it to surface the ~44 known offenders.

## Output
- Each advisory line lists: item ID, sub-entity kind + index (e.g. finding F1), the actual title length, and the threshold.
- Reported consistently with existing advisory-only check output.

## Acceptance criteria
- sq check includes a pass examining every sub-entity title across all item types.
- Over-long titles reported as advisory warnings, not errors.
- A previously-clean sq check (no structural errors) still exits 0 even when title-length advisories are present.
- Running against the current corpus surfaces the ~44 known offenders (>120 chars), confirming the rule fires.

## Tests
- Service/CLI test: seed sub-entities with titles above and below 120; assert advisories on the long ones only, none on short ones, exit 0 when otherwise clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 169 add-subtask "<title>"`; track with `sq task 169 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Add sq check pass walking all sub-entity titles | US2 |
| ST2 | Done |  | Report over-long titles as advisory findings with ID/kind/index/length | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add sq check pass walking all sub-entity titles

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US2 — As a team lead, I want sq check to flag over-long sub-entity titles corpus-wide
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Add a new pass to sq check that iterates every item's sub-entities (findings, subtasks, stories) and measures each title against TITLE_ADVISORY_MAX (the shared constant from TASK-000168 / _interactions.py). Pure read; no mutation, no migration.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Report over-long titles as advisory findings with ID/kind/index/length

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — As a team lead, I want sq check to flag over-long sub-entity titles corpus-wide
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Emit each over-long title as an ADVISORY finding (not a structural error), formatted consistently with existing advisory-only check output. Each line includes: item ID, sub-entity kind + index (e.g. finding F1), actual title length, and the threshold. sq check must still exit 0 when no structural errors exist. Test: long + short titles seeded; advisories only on the long ones; exit 0.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-23T09:50:33Z] Elias Python:
  - TASK-000169 done. Implemented _check_subentity_title_lengths in MaintenanceMixin (_services/_maintenance.py): walks every item's subentities, emits warn-level CheckIssue for each title > TITLE_ADVISORY_MAX, reusing the shared constant from _interactions.py. Refactored inner loop to list.extend to satisfy PERF401; import ordering fixed by ruff --fix.
  - Gates: ruff check clean, ruff format clean, pyright 0 errors, 1025 passed / 1 skipped (54 new tests in test_title_advisory.py covering both TASK-000168 and TASK-000169 service + CLI paths).
  - Live corpus: 107 advisory issues reported, sq check exits 0. Threshold fires strictly above 120 — at/below is silent.
  - @manager TASK-000169 complete. TASK-000168 was approved (REV-000172). TASK-000170 (skill reinforcement) remains.
- [2026-06-23T09:53:45Z] Paul Reviewer:
  - Reviewed under REV-000174 — APPROVED, no findings.
  - Independently verified against ADR-000167: reuses the shared TITLE_ADVISORY_MAX constant (no duplicated 120 literal); walks every sub-entity title across all items (strict > 120, silent at 120); emits warn-level only, so sq check stays exit 0 — confirmed the exit code gates solely on error count and does not flip; read-only (mutates nothing); copy is honest (no enforce/guarantee/secur/forbid).
  - The 107 count is real: I counted independently from the .md frontmatter (bypassing the rule) and also got 107, all unique keys, no double-counting, only sub-entity titles measured. REV-000097 F5 = 781 chars by hand, matching the ADR worst case. Targeted suite (54 tests) passes. @manager
<!-- sq:discussion:end -->
