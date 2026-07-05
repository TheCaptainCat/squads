---
id: REV-162
sequence_id: 162
type: review
title: reflog --tree + show session surfacing (TASK-000160)
status: Approved
author: reviewer
refs:
- TASK-160:addresses
subentities:
- local_id: F1
  title: Session cycle silently drops entries from the tree
  status: Verified
  severity: medium
- local_id: F2
  title: No cycle/pathological-edge test for the renderer
  status: Verified
  severity: low
created_at: '2026-06-22T11:07:55Z'
updated_at: '2026-06-22T11:50:39Z'
---
<!-- sq:body -->
Independent review of **TASK-160** (FEAT-125 US2, under ADR-158): `sq reflog --tree` spawn-lineage renderer + `show --full` session surfacing.

## Scope reviewed
- `src/squads/_cli/_main.py` — `--tree` flag, `_reflog_entry_line`, `_build_session_maps`, `_attach_session_node`, `_render_reflog_tree`.
- `src/squads/_cli/_common.py` — `_build_item_panel_rows` session surfacing.
- `tests/test_reflog_tree.py` (27 tests).
- Consumed data model (TASK-159) confirmed sound for this layer.

## Gates (re-run)
- pyright: 0 errors. ruff check: clean. ruff format: clean. pytest: full suite exit 0; new file 27/27.

## What is correct
- `--json` evaluated before `--tree`; flat `dataclasses.asdict` list preserved (back-compat); session fields additive/omitted-when-None. Golden `reflog_shape.json` bumped 0.3→0.4, required-field list unchanged.
- Tree is display-only — no stored-data mutation.
- Best-effort/untrusted/observability-only header always printed; `--help` carries the same framing; no tamper-evidence claim. Faithful to data, no overclaim.
- `show --full` surfacing degrades cleanly (slug-only when no session); legacy items unchanged; untrusted-flavored wording.
- `e()` escaping complete on every new console string (ts/op/target/actor/delta, session ids, slugs, parent ids).
- Forest/nesting/unknown-parent/missing-intermediate/no-session/empty all handled without raising.

## Findings
See review points. One MEDIUM (silent data loss on a session cycle) + one LOW (missing cycle test) — required before approval.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 162 add-finding "…" --severity high`; track with `sq review 162 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Verified |  | Session cycle silently drops entries from the tree |
| F2 | 🟢 low | Verified |  | No cycle/pathological-edge test for the renderer |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Session cycle silently drops entries from the tree

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
**Severity: medium.** A session cycle in the declared edges silently drops the cycled sessions from the rendered tree.

`_render_reflog_tree` selects roots as sessions where `parent is None or parent not in known_sessions`, then descends via `children_map` (`_attach_session_node`). If two-or-more sessions form a pure parent cycle (e.g. A.parent=B, B.parent=A — forgeable/corrupt input), every node in the cycle has a *known* parent, so NONE qualifies as a root and the cycle is never reached from `_attach_session_node`. The entries vanish — they appear in neither the session branch nor the no-session branch.

Reproduced: two entries with `session_id` SIDALPHA/SIDBETA referencing each other render only the header + empty `reflog` root; neither SIDALPHA nor SIDBETA appears in the output. (No infinite loop: reachable-from-root cycles are structurally impossible because a cycle node's parent is always inside the cycle, so it can never be a root — that part is sound. The defect is silent loss, not a hang.)

Why this matters here: input is explicitly untrusted/forged (the whole point of this view is forensic visibility of *declared* lineage). Silently discarding declared sessions undercuts "best-effort, faithful to the data, no overclaim" — a forged self-loop becomes a way to make operations disappear from the tree entirely.

Required change: any `session_id` present in `session_entries` must surface SOMEWHERE in the tree. Suggest: after attaching the legitimate roots, do a reachability pass (track a visited set while attaching) and emit any unvisited sessions as forest roots with the existing "(parent X — forest root)"-style note. Add a visited-set to `_attach_session_node` as belt-and-suspenders so the never-raise / never-loop contract holds even if the structural argument is later broken by a refactor.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-06-22T11:50:32Z] Paul Reviewer:
  - Verified resolved. Reachability pass in _render_reflog_tree (after the root walk) emits every unvisited session_id as a cycle/forest root, so no recorded session is silently dropped. Confirmed for a 2-node A<->B cycle (both surface, each exactly once) and a self-loop A->A (surfaces once). The visited-set is threaded through _attach_session_node with an in-place guard (child_sid skipped if already visited), making the never-loop contract structural rather than argued. New cycle-root label escapes e(sid)/e(p).
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — No cycle/pathological-edge test for the renderer

<!-- sq:finding:F2:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
**Severity: low.** The renderer has no test for cyclic / pathological parent edges, even though the task brief makes cycle-safety an explicit robustness requirement and the input is untrusted. The 27 tests cover empty / no-session / single-root / chain / 3-level / unknown-parent / missing-intermediate / self-review, but never a session whose parent chain loops. That gap is exactly what hid the F1 silent-drop behaviour.

Required change: add a test asserting that (a) a session cycle does not raise and does not loop, and (b) every cycled `session_id` still appears in the output (couples to the F1 fix). A 2-cycle and a 3-cycle case both at render and service level would close it.

Minor (no change required, FYI): the render-level self-review test (`test_render_tree_self_review_visibly_non_independent`) asserts only `out.count("arch-sid") >= 1` and a bare `"create" in out` — neither actually proves the two ops nest under a single root. The service-level test `test_service_self_review_same_session_single_root` carries the real assertion, so coverage is fine overall; consider tightening the render-level one.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-06-22T11:50:32Z] Paul Reviewer:
  - Verified resolved. Three renderer tests added: two_node_cycle (no-raise + both appear), self_loop (no-raise + session appears), and cycle_entries_each_appear_exactly_once (counts '[dim]session:[/dim] <id>' node-label occurrences == 1 each, via markup=False capture). Genuinely asserts both no-raise/no-loop AND surfacing, including the self-loop case.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-22T11:50:39Z] Paul Reviewer:
  - Re-review passed — both findings Verified, REV-162 Approved. F1 (silent cycle drop): reachability pass surfaces every session_id; visited-set guard in _attach_session_node makes the never-loop contract structural. F2: three cycle/self-loop renderer tests added asserting no-raise AND surfacing. No regression: --json still the flat dataclasses.asdict list (evaluated before --tree), best-effort/untrusted header still printed, e() escaping complete on the new cycle-root label. Gates: pyright 0 errors, ruff check + format clean, full pytest 920 passed / 1 skipped, complexity within limits.
<!-- sq:discussion:end -->
