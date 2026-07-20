---
id: REV-487
sequence_id: 487
type: review
title: User-facing docs review for 0.10.1
status: Approved
author: tech-writer
subentities:
- local_id: F1
  title: Tutorial shows padded IDs in CLI output when they should be unpadded (0.10.0
    display format)
  status: Fixed
  severity: medium
- local_id: F2
  title: Recipes doc shows padded IDs in copy-paste examples when they should be unpadded
  status: Fixed
  severity: medium
- local_id: F3
  title: Adoption guide shows padded IDs in migration examples when they should be
    unpadded
  status: Fixed
  severity: medium
- local_id: F4
  title: Missing documentation for sq workflow collections and sq workflow statuses
    subcommands
  status: Fixed
  severity: medium
- local_id: F5
  title: README command reference lacks sq workflow subcommands added in 0.10.0
  status: Fixed
  severity: medium
created_at: '2026-07-20T07:30:55Z'
updated_at: '2026-07-20T08:26:22Z'
---
<!-- sq:body -->
## Scope

Comprehensive review of adopter-facing documentation (user-facing only, no internal/contributor docs):

- Root: README.md, CHANGELOG.md

- docs/: All 11 doc files (tutorial, workflow, agents, roles, recipes, faq, adoption, overrides, migration, stability, internals, backends)

- VS Code extension: MARKETPLACE.md, README.md



## Method

Check for four dimensions: staleness (claims don't match current behavior), inconsistencies (contradictions/terminology drift), bad wording (clarity/grammar), and gaps (missing coverage).

Verified against actual CLI using version 0.10.0.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 487 add-finding "…" --severity medium`; track with `sq review 487 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Fixed |  | Tutorial shows padded IDs in CLI output when they should be unpadded (0.10.0 display format) |
| F2 | 🟡 medium | Fixed |  | Recipes doc shows padded IDs in copy-paste examples when they should be unpadded |
| F3 | 🟡 medium | Fixed |  | Adoption guide shows padded IDs in migration examples when they should be unpadded |
| F4 | 🟡 medium | Fixed |  | Missing documentation for sq workflow collections and sq workflow statuses subcommands |
| F5 | 🟡 medium | Fixed |  | README command reference lacks sq workflow subcommands added in 0.10.0 |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Tutorial shows padded IDs in CLI output when they should be unpadded (0.10.0 display format)

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
Fixed: Updated all padded IDs (EPIC-000009, FEAT-000010, BUG-000012) to unpadded format (EPIC-9, FEAT-10, BUG-12) in CLI output examples, frontmatter examples, and command arguments. Filenames remain padded on-disk. All changes in docs/tutorial.md lines 26, 38, 72, 92, 113.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Recipes doc shows padded IDs in copy-paste examples when they should be unpadded

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
Fixed: Updated all padded IDs in recipes.md to unpadded format: EPIC-000001→EPIC-1, FEAT-000002→FEAT-2, BUG-000010→BUG-10, REV-000012→REV-12, ADR-000014→ADR-14, GUIDE-000015→GUIDE-15, TASK-000003→TASK-3, TASK-000020→TASK-20. All copy-paste examples now show standard unpadded display format.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Adoption guide shows padded IDs in migration examples when they should be unpadded

<!-- sq:finding:F3:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
Fixed: Updated all padded IDs in adoption.md to unpadded format: TASK-000002→TASK-2, EPIC-000001→EPIC-1, FEAT-000007→FEAT-7, TASK-000008→TASK-8, BUG-000009→BUG-9. Migration examples now consistently show unpadded format, reducing confusion for adopters migrating legacy systems.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Missing documentation for sq workflow collections and sq workflow statuses subcommands

<!-- sq:finding:F4:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
Fixed: Added new section 'Inspecting the workflow spec' in docs/workflow.md (before 'Status lifecycles') documenting all workflow subcommands: sq workflow [show|types|collections|statuses|lint]. Section includes brief descriptions and examples for querying badge collections and status values programmatically.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — README command reference lacks sq workflow subcommands added in 0.10.0

<!-- sq:finding:F5:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
Fixed: Updated README.md command reference (line 166) from bare 'sq workflow' to full entry listing subcommands: 'sq workflow [show|types|collections|statuses|lint]' with description covering team-workflow cheatsheet, type listing, badge collection querying, status listing, and override validation.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-20T07:34:09Z] Theo Writer:
  - Review complete. Found 5 findings across four dimensions:
  - • **Staleness (3):** Tutorial, recipes, and adoption docs show padded ID format (EPIC-000009) when 0.10.0 displays unpadded (EPIC-9) — changed in 0.7.0 but examples weren't updated.
  - • **Gaps (2):** Missing documentation for `sq workflow collections` and `sq workflow statuses` subcommands added in 0.10.0; incomplete `sq workflow` reference in README.
  - 
  - Ready for triage with @manager. All finding bodies include file locations, concrete examples, and suggested fixes.
- [2026-07-20T07:45:46Z] Theo Writer:
  - All 5 findings fixed:
  - • F1-F3 (tutorial/recipes/adoption): Unpadded all ID references in CLI output, frontmatter, and command examples
  - • F4-F5 (gaps): Added documentation for sq workflow subcommands (collections, statuses) in workflow.md, updated README command reference
  - sq check: clean. Ready for @manager review.
<!-- sq:discussion:end -->
