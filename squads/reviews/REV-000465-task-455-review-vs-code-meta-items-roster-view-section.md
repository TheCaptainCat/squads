---
id: REV-465
sequence_id: 465
type: review
title: 'TASK-455 review: VS Code meta-items (Roster) view section'
status: Approved
author: reviewer
refs:
- TASK-455
subentities:
- local_id: F1
  title: Roster leaf-builder duplicates listView's itemToLeaf/sortedLeaves
  status: Open
  severity: low
created_at: '2026-07-17T15:41:30Z'
updated_at: '2026-07-17T15:43:25Z'
---
<!-- sq:body -->
Independent review of TASK-455 (US3/F12, meta-items 'Roster' view section; Ada implemented). Scope: clients/vscode/** diff.

Recommended verdict: APPROVE. All acceptance met; strict gate + unit + canary green; preview reuse verified end-to-end. One low, non-blocking cleanup finding (leaf-builder duplication).
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 465 add-finding "…" --severity medium`; track with `sq review 465 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Open |  | Roster leaf-builder duplicates listView's itemToLeaf/sortedLeaves |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Roster leaf-builder duplicates listView's itemToLeaf/sortedLeaves

<!-- sq:finding:F1:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
domain/metaView.ts's private itemToLeaf and sortedLeaves are near-verbatim copies of the same-named private helpers in domain/listView.ts (identical DisplayNode shape: label `${id}  ${title}`, description `${status} · ${assignee}`, buildTooltip, iconForType, closed=!is_open, sortedLeaves via compareIds). Correct and behaviorally identical today — but this is exactly the leaf-level drift the task's own META_BUCKETS single-source design guards against at the type-set level. Suggest extracting a shared listItemToLeaf (+ sorted variant) into domain/displayNode.ts so the two views' leaf rendering can't diverge. Low severity, non-blocking: small, correct, no runtime impact.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-17T15:41:59Z] Paul Reviewer:
  - Recommended verdict: APPROVE (leaving status for the approver). F1 is low/non-blocking cleanup.
  - Verified: (1) squadsMeta 'Roster' registered as 2nd entry in contributes.views.squads, own provider + squads.refreshMeta wired (when: view==squadsMeta); (2) buildMetaView -> exactly 3 fixed buckets (Roles/Skills/Operators), always present even empty, leaves numeric-sorted, no work-item leakage (unit-tested); (3) RESERVED_TYPES derived from META_BUCKETS single source = drift-proof both directions; (4) toTreeItem extracted to treeItemRendering.ts, byte-identical to the removed inline impl (only comment expanded), work tree uses it, no regression; (5) preview reuse: meta leaves fire squads.openItemPreview[itemId] into the same ItemPreviewManager, and sq show/tree/graph all exit 0 for ROLE-1/OP-10/SKILL-192.
  - Gate: npm run check exit 0 (tsc strict + eslint --max-warnings 0 + prettier); npm test 131/131; npm run test:canary 8/8. Leaf label/description format matches listView.ts exactly.
<!-- sq:discussion:end -->
