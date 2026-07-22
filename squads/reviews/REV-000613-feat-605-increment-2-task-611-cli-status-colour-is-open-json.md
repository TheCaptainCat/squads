---
id: REV-613
sequence_id: 613
type: review
title: 'FEAT-605 increment 2 (TASK-611): CLI status colour + is_open --json drop'
status: Approved
author: reviewer
refs:
- TASK-611:addresses
created_at: '2026-07-22T16:55:32Z'
updated_at: '2026-07-22T16:56:09Z'
---
<!-- sq:body -->
Scope: the uncommitted diff for TASK-611 (FEAT-605 US3) — status-colour rendering across sq list/tree/mine + the workflow statuses catalog table, and the is_open field dropped from the list/tree/mine --json payloads. Increment 1 (role model, REV-612) and the cheatsheet template change (landed on HEAD) are out of scope.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 613 add-finding "…" --severity medium`; track with `sq review 613 finding <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:findings -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T16:55:48Z] Paul Reviewer:
  - APPROVED — clean. Independent review, scoped to the uncommitted diff.
  - is_open drop: complete + safe. No Python --json payload still emits is_open (list/tree x2/mine all dropped); the sq mine open-filter reads spec.is_open(i.status) off the spec, not the removed payload field. No remaining src consumer reads is_open off a node/item payload (the surviving refs are all spec.is_open(status) calls + the __all__ export). Goldens (list/list_feature/tree/tree_feat) differ ONLY by removed is_open lines — no other field silently changed. test_json_output_shape green.
  - Colour: INTENT_COLORS is total over COLOR_INTENTS (6 intents match exactly: positive/danger/warning/info/muted/neutral) with a neutral empty-style entry doubling as the .get fallback for an unknown intent — never raises. Injection-safe: status_text applies colour via Text(status, style=...), not [colour]..[/] markup interpolation; the tree _label builds the id/prio/title span with Text.from_markup (id is system-safe, prio+title routed through e()) then append_text()s the status Text (no re-parse). workflow statuses cell uses status_text. Confirmed sq workload has no per-status cell (Assignee/Open/Closed/Total aggregate counts) — the dev's skip is correct, not a miss.
  - Allowlist: the INTENT_COLORS entry is the sanctioned mechanism for an immutable CODE lookup-table constant, consistent with the neighbouring _create/_init entries — not masking real mutable state.
  - Gate: pyright 0/0/0, ruff check clean, ruff format clean; targeted cli/golden/meta tests green. Conventions OK (no ticket IDs, no 'meta', SquadsError-family, no schema bump).
- [2026-07-22T16:56:00Z] Paul Reviewer:
  - Release-sequencing note (not a finding — out of scope, tracked): the VS Code adapter has hard runtime guards on this field (clients/vscode/src/sqAdapter.ts:102 and :174, typeof node.is_open === 'boolean'), plus types.ts:23/168 and treeMapping/metaView consumers. Dropping is_open from sq list/tree/mine --json is a breaking contract change for the extension — its type guards will reject the payload once this ships. The TS migration (FEAT-570 US3) MUST land in the same release as this task, else the extension's tree/list consumption breaks. Flagging so release sequencing is explicit.
<!-- sq:discussion:end -->
