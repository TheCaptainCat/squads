---
id: REV-000186
sequence_id: 186
type: review
title: 'Review: sq tree filters (FEAT-000039)'
status: Approved
author: reviewer
refs:
- FEAT-000039:addresses
- TASK-000185:addresses
subentities:
- local_id: F1
  title: dim-render CLI test asserts nothing about dimming
  status: Verified
  severity: medium
- local_id: F2
  title: stale docstring references removed CLI helper _build_children
  status: Verified
  severity: medium
created_at: '2026-06-24T14:09:38Z'
updated_at: '2026-06-24T14:14:10Z'
---
<!-- sq:body -->
## Scope

_TODO: what is under review?_
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 186 add-finding "…" --severity high`; track with `sq review 186 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Verified |  | dim-render CLI test asserts nothing about dimming |
| F2 | 🟡 medium | Verified |  | stale docstring references removed CLI helper _build_children |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — dim-render CLI test asserts nothing about dimming

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
File: tests/test_tree.py:593 test_cli_tree_path_only_ancestors_dimmed. The test's own docstring admits it cannot verify dimming under CliRunner (Rich [dim] markup is stripped), so it only re-asserts that ancestors and the match appear — already covered by test_cli_tree_filter_type. Net: there is no automated guard that path_only ancestors are actually wrapped in [dim]. The behaviour IS correct (verified by live CLI smoke: EPIC/FEAT emit dim ANSI, TASK does not). Suggested fix: render with a console that has force_terminal/color enabled (or call svc.tree_view directly and assert TreeNode.path_only) so a future regression that drops the [dim] wrap would be caught. Non-blocking: the path_only flag itself is well-tested at the service layer.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — stale docstring references removed CLI helper _build_children

<!-- sq:finding:F2:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
File: src/squads/_services/_base.py:160 (docstring of _build_tree_children). It says 'This is the service-layer equivalent of the CLI helper _build_children' but _build_children was deleted from _cli/_main.py in this same change (it was moved here verbatim). The cross-reference now points at a symbol that no longer exists, which will mislead the next reader. Suggested fix: reword to 'replaces the former CLI helper _build_children (FEAT-000027 / TASK-000103)' or drop the back-reference. Trivial, non-blocking.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-24T14:10:24Z] Paul Reviewer:
  - VERDICT: APPROVE. Independent review of sq tree filters (FEAT-000039 / TASK-000185) against all four acceptance criteria + the manager's two behaviour decisions — all met. I read the diff, the tests, and ran the live CLI; I did not trust the dev's summary.
  - Criterion 1 (each filter alone + combined AND, with/without root, --depth truncates): MET. ItemFilter.matches ANDs every non-None dimension; tree_view wires type/status/assignee/priority; depth measured from each root (root=0), verified depth=0 (root-only), depth=1, and explicit-root depth. No off-by-one.
  - Criterion 2 (no orphaned match; ancestors kept; path-only visually distinct, not counted as match): MET. _compute_keep_set = match_set UNION ancestor-chain (width-tolerant via seq numbers); _walk_tree flags path_only = (id not in match_set) and drops empty path-only anchors. Live smoke confirms ancestors emit dim ANSI and the match does not.
  - Criterion 3 (--json same shape, pruned not reshaped, no path_only leak): MET. node() emits exactly id/type/status/priority/assignee/blocked/children and ignores .path_only. Golden + key-set test + ANSI-free test all green; verified no path_only/match key in JSON.
  - Criterion 4 (filters/parsing shared with list, one implementation): MET. list_items reimplemented on ItemFilter.matches (pure refactor, existing list tests green + a no-drift regression test); tree CLI reuses the same parse_type/parse_status/parse_priority/resolve_slug_or_raise edge parsers. One predicate, no parallel matching logic.
  - Behaviour decision A (closed gate mirrors list exactly): MET. include_closed = bool(all_ or status); --priority/--assignee/--type alone do NOT widen to closed (test_cli_tree_non_status_filter_does_not_widen_to_closed), --status/--all reveal matching closed items.
  - Behaviour decision B (--depth wins over a deeper match): MET. _walk_tree stops recursing when current_depth would exceed depth before checking match; a match below the cut is dropped (test_tree_view_depth_wins_over_deep_match).
  - Invariants: no hand-parsing of ID:kind; SquadsError used for the not-found root (message + --all hint preserved); no datetime.now; no new # type: ignore in src; pyright/ruff/format clean; _build_tree_children is a verbatim move of the old _build_children (FEAT-000027 repad tolerance intact, no regression); old helper and unused number_for_id import removed (no dead code).
  - Two NON-BLOCKING LOW findings filed: F1 — the dim-render CLI test asserts nothing about dimming (the flag is well-tested at the service layer, behaviour confirmed live); F2 — a docstring still cross-references the now-deleted _build_children. Neither gates approval. @python-dev nice work, optionally tidy F1/F2 in a follow-up. @manager approving; over to you for the task/feature transitions.
<!-- sq:discussion:end -->
