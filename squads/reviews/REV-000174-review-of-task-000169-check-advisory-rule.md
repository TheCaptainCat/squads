---
id: REV-174
sequence_id: 174
type: review
title: Review of TASK-000169 check advisory rule
status: Approved
author: reviewer
refs:
- TASK-169:addresses
created_at: '2026-06-23T09:53:13Z'
updated_at: '2026-06-23T09:53:37Z'
---
<!-- sq:body -->
Independent review of TASK-169 (sq check advisory rule for over-long sub-entity titles) against ADR-167. VERDICT: APPROVED — no findings.

Verified (all 7 checkpoints pass):
1. Reuses TITLE_ADVISORY_MAX imported from _interactions.py. The only '120' occurrences in _maintenance.py are in the docstring prose; the logic uses the constant. No duplicated literal.
2. Walks every sub-entity title on every item: iterates index.items.values(), maps item.type -> kind via SUBENTITY_KIND ({FEATURE:story, TASK:subtask, REVIEW:finding}), then iterates item.subentities. Each item type holds exactly one sub-entity kind, so all three kinds are covered. Comparison is strict 'len(sub.title) > TITLE_ADVISORY_MAX' — silent at 120, fires at 121.
3. EXIT CODE (load-bearing): rule emits only level='warn' CheckIssue. _cli/_main.py gates Exit(3) solely on count of level=='error' (both json and human paths). Confirmed live: sq check on the live corpus prints 107 advisories and exits 0.
4. Read-only: the rule only constructs CheckIssue objects from existing model state; mutates nothing.
5. Honesty: no enforce/guarantee/secur/forbid/prevent/block language in the rule or its message; copy is advisory ('a sub-entity title is a one-line handle; put the detail in the body').
6. The 107 count is REAL, not an artifact. Independently counted straight from .md frontmatter (source of truth, bypassing the rule) = 107 over-long sub-entity titles. The rule's 107 are all unique (item+kind+local_id) — no double-counting; zero non-title warns; only sub.title measured (not summary/head/top-level item titles). REV-97 F5 = 781 chars by hand, matching the rule and the ADR's worst-case.
7. Tests (TestCheckSubentityTitleLengths, 54 total in file pass): over-long per kind -> warn issue; all-short -> none; boundary at 120 silent / 121 fires; warn-never-error; CLI exits 0 with advisory present; multiple/mixed; message carries id/length/threshold.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 174 add-finding "…" --severity high`; track with `sq review 174 finding <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:findings -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
