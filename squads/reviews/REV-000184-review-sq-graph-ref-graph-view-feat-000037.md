---
id: REV-184
sequence_id: 184
type: review
title: 'Review: sq graph ref-graph view (FEAT-000037)'
status: Approved
author: reviewer
refs:
- FEAT-37:addresses
- TASK-182:addresses
subentities:
- local_id: F1
  title: Rich tree crashes on any node with a priority
  status: Verified
  severity: high
- local_id: F2
  title: Dangling-ref stub branch in _build_graph_node is dead code
  status: Verified
  severity: low
- local_id: F3
  title: graph_to_dot _q does not escape backslashes
  status: Verified
  severity: low
- local_id: F4
  title: dot/mermaid arrows follow traversal direction, not dependency semantics
  status: WontFix
  severity: low
created_at: '2026-06-24T11:56:36Z'
updated_at: '2026-06-24T12:25:46Z'
---
<!-- sq:body -->
## Scope

_TODO: what is under review?_
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 184 add-finding "…" --severity high`; track with `sq review 184 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟠 high | Verified |  | Rich tree crashes on any node with a priority |
| F2 | 🟢 low | Verified |  | Dangling-ref stub branch in _build_graph_node is dead code |
| F3 | 🟢 low | Verified |  | graph_to_dot _q does not escape backslashes |
| F4 | 🟢 low | WontFix |  | dot/mermaid arrows follow traversal direction, not dependency semantics |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Rich tree crashes on any node with a priority

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟠 High
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
BLOCKING. `sq graph` aborts with a traceback whenever the rendered tree contains any node carrying a priority. Root cause: GraphNode.priority is a value-string (e.g. "high"), but _cli/_main.py passes it straight to priority_badge(), which is typed priority_badge(priority: Priority) and does PRIORITY_EMOJI[priority] (dict keyed by the Priority enum) + priority.value. With a str it raises AttributeError: 'str' object has no attribute 'value' (after a KeyError-prone lookup).

Two call sites are affected: _main.py:606 (root node) and _main.py:522 (children). Both carry a '# type: ignore[arg-type]' that suppressed exactly the pyright error that would have caught this — the ignore masked the bug rather than fixing it.

Reproduce: create a feature, a task with --priority high, ref them, then 'sq graph FEAT --depth 1' -> traceback, exit 1. The test suite never caught it because every fixture item has priority=None, so the 'if child.priority' guard skips the call in all tests.

Fix: convert at the call site — priority_badge(Priority(child.priority)) / Priority(root_node.priority) — and DELETE the '# type: ignore' so the type checker stays honest. Add a graph test with a priority'd node to lock it.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Dangling-ref stub branch in _build_graph_node is dead code

<!-- sq:finding:F2:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
In _build_graph_node, the 'item is None' branch builds and returns a stub GraphNode for a dangling ref. But every caller (the loop in _build_graph_node over _neighbours) already pre-checks 'nb_item is None: continue' before recursing, and the root goes through require_item (raises if missing). So the stub branch is unreachable in practice — dead code. Harmless, but either wire it in (don't pre-skip, let the stub carry the dangling id) or drop it. Minor.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — graph_to_dot _q does not escape backslashes

<!-- sq:finding:F3:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
graph_to_dot._q escapes double-quotes (" -> \") but not backslashes. A label/id containing a backslash would produce malformed DOT. In practice labels are kind names + 'depends on'/'required by' and ids are PREFIX-digits, so no backslash can occur today — not exploitable now. Worth a one-line guard (escape backslash before quote) for robustness if ids/labels ever widen. Low.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — dot/mermaid arrows follow traversal direction, not dependency semantics

<!-- sq:finding:F4:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
Observation, not a defect. In dot/mermaid export the edge arrow points parent->child following TREE TRAVERSAL order, and the label is the display string ('depends on'/'required by'). So a dependency rooted at the blocker emits 'BLOCKER -> DEPENDENT [label=required by]', i.e. the arrow is traversal-oriented, not dependency-oriented (a real dependency arrow would point dependent->blocker). Acceptance only requires 'renders in graphviz untouched', which it does, and it faithfully mirrors the tree. Flagging so it's a conscious choice; if the export is meant to be a canonical dependency graph, normalize arrow direction. Low/info.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-24T11:57:37Z] Paul Reviewer:
  - VERDICT: ChangesRequested. The traversal logic is genuinely solid — the depends-on/blocks normalization (the critical requirement) is correct and symmetric, verified by hand with mixed-authorship fixtures rooted at BOTH ends: a 'blocks' edge and a 'depends-on' edge between the same two items render the identical label pair ('depends on' / 'required by'), cycles terminate with (seen), closed items hide without --all, filters behave, the service holds the single reusable implementation and the CLI is a thin edge, and --json is now ANSI-free via print_json_clean. Pyright/ruff/format clean; graph tests green.
  - But there is ONE blocking defect (F1, high): the default Rich tree — the primary human output — crashes with a traceback on ANY node that carries a priority, because GraphNode.priority is a value-string and the CLI passes it straight to priority_badge(priority: Priority). The '# type: ignore[arg-type]' at _main.py:522 and :606 suppressed the very pyright error that would have flagged it. The tests all use priority=None so they never exercised it. Acceptance criterion 1 explicitly requires priority badges, so this fails acceptance, not just an edge case. Fix is small: priority_badge(Priority(child.priority)) and remove the ignore; add a priority'd-node graph test.
  - F2/F3/F4 are low/info (dead dangling-ref stub, dot backslash escaping, export arrow direction is traversal-oriented) — not blocking. @python-dev please fix F1 and add the regression test; @manager holding at ChangesRequested until then.
<!-- sq:discussion:end -->
