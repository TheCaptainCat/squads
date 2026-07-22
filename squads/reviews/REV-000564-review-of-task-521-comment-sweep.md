---
id: REV-564
sequence_id: 564
type: review
title: Review of TASK-521 comment sweep
status: Approved
author: reviewer
refs:
- TASK-521
subentities:
- local_id: F1
  title: Dropped division-of-responsibility note in WorkflowSpec floor comment
  status: Verified
  severity: low
- local_id: F2
  title: 'Acceptance gap: terse-comment standard not documented; hygiene-guard extension
    not addressed'
  status: Verified
  severity: low
created_at: '2026-07-22T00:13:41Z'
updated_at: '2026-07-22T00:23:44Z'
---
<!-- sq:body -->
Focused review of the TASK-521 repo-wide comment/docstring terseness sweep (I did not perform the sweep). Read-only: no source edits, no commit.

Verdict: comment/docstring-only confirmed independently — the full working diff over src/, tests/, .github/, pyproject.toml contains ZERO changed executable lines, signatures, control flow, or runtime string literals. Every non-comment hit in the diff is a trailing-comment strip on an otherwise byte-identical line (test '# FEAT-2/# US1/# TASK-3' annotations, the cron line's trailing note). No noqa/type:ignore/pyright:ignore/fmt:skip pragma was removed.

The big strips are accurate: _interactions/__init__.py (-66) keeps every non-obvious why (CREATE_LANES table-pinning rationale, the reviewer-review-in-task-playbook example, the no-custom-role-lane-override caveat). CI top-blocks keep the branch-protection required-checks caveat (test.yml) and the schedule-ignores-paths canary reasoning (vscode-client.yml); the 'canary is the one Python-touching job / uv sync needs repo-root pyproject' gotcha survives verbatim as an inline comment at the job body. Docstring ID-citation strips (_cli, _services, _backend, tests/_helpers) removed only the ID; substance kept, and none feed Typer --help (all are TyperGroup.list_commands / internal method docstrings, not command callbacks).

Two low findings; no blockers. Approvable once F1 is restored (or waived) and F2 is triaged.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 564 add-finding "…" --severity medium`; track with `sq review 564 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Verified |  | Dropped division-of-responsibility note in WorkflowSpec floor comment |
| F2 | 🟢 low | Verified |  | Acceptance gap: terse-comment standard not documented; hygiene-guard extension not addressed |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Dropped division-of-responsibility note in WorkflowSpec floor comment

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
In src/squads/_workflow/_models.py the condensed WorkflowSpec reserved-vocab comment dropped the sentence explaining that a status omitted from the spec but still referenced by a declared lifecycle's initial/transitions is caught by the transition check *above*, not by this floor check. That is a non-local 'which check owns what' clarification — it reassures a maintainer that narrowing the floor to Draft/Active/Archived leaves no validation hole for dropped-but-referenced statuses. Suggest restoring a half-line, e.g. '(a dropped status still referenced by a declared lifecycle is caught by the transition check above, not here).' Everything else in the condensation is accurate. Low severity — informational loss only, no code impact.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-07-22T00:21:36Z] Elias Python:
  - Fixed: restored the half-line ('a dropped status still referenced by a declared lifecycle's initial/transitions is caught by the transition check above, not by this floor') in src/squads/_workflow/_models.py.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Acceptance gap: terse-comment standard not documented; hygiene-guard extension not addressed

<!-- sq:finding:F2:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
Task acceptance #2 has two parts beyond the strip itself: (a) write the terse-comment standard into a conventions doc so it doesn't regress, and (b) check whether the existing hygiene guard can be extended to catch item-ref/over-comment regressions in code+config. Neither appears in the diff (no CONTRIBUTING.md/CLAUDE.md/guard change) and the dev's handoff comment doesn't mention them. Not a defect in the sweep's quality — the strip itself is clean — but flagging that the task's own acceptance is not fully met. Manager to triage: complete here or split to a follow-up. Low severity.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-07-22T00:21:37Z] Elias Python:
  - Fixed: (a) added a terse-comment-standard line to CONTRIBUTING.md's Conventions section. (b) extended tests/meta/test_source_and_new_test_tree_have_no_stray_ticket_references.py with a tokenize-based comment scan (_comment_violations) over src/+tests/, and widened the docstring/identifier scan to all of tests/ (old flat suite is gone, so the narrower root list was no longer needed). New tests prove it catches a planted inline comment and never flags assertion-data string literals. This surfaced 2 more real leaks (tests/conftest.py: REV-93/FEAT-178 docstring citations) and 1 case where our own kept F1-style gotcha comment (test_item_lifecycle_edge_operations.py:52) needed rewording to drop the literal US1 token — all fixed.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
