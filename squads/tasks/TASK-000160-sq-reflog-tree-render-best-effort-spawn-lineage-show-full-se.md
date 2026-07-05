---
id: TASK-160
sequence_id: 160
type: task
title: 'sq reflog --tree: render best-effort spawn lineage + show --full session surface'
status: Done
parent: FEAT-125
author: tech-lead
assignee: python-dev
refs:
- TASK-159:depends-on
subentities:
- local_id: ST1
  title: Spawn-tree view + show --full session surfacing (best-effort, untrusted)
  status: Done
  story: US2
created_at: '2026-06-22T09:11:24Z'
updated_at: '2026-06-22T11:59:26Z'
---
<!-- sq:body -->
Implements **US2** of FEAT-125 per **ADR-158** (Accepted). **Depends on TASK-159** (the structured-actor data model + reflog session fields must land first — this task consumes the recorded `session_id`/`parent_session_id` edges). Read the ADR and TASK-159 before starting.

## Guarantee framing (non-negotiable wording)
This is **forensic observability, not verification**. The tree reflects **declared, untrusted** lineage: a deliberately copied session id appears as a legitimate edge; a missing intermediate session degrades to a forest, never an error. The view (and its docs) must **label itself best-effort/untrusted** and make **no** tamper-evidence or enforcement claim.

## Scope (squads-side only, rendering on top of TASK-159's data)

### 1. `sq reflog --tree`
- Add a `--tree` flag to the existing `reflog` command (`src/squads/_cli/_main.py` ~line 592). It renders a parent→children tree built from each entry's recorded `session_id` + `parent_session_id` edges, over the **existing time-window/filter** plumbing (`--since`, `--item`, `--actor`, `--op`, `--tail`).
- Build a `parent_session_id → [children]` map from the filtered `ReflogEntry` list (already carries the session fields after TASK-159). Entries with **no or unknown** `parent_session_id` (parent not present among the rendered sessions) are **root nodes**.
- A **missing intermediate session** (truncated log) must **degrade gracefully to a forest** of roots — never raise.
- Group operations under their session node; render a nested tree (reuse existing tree rendering style if one exists, else a simple indented render). Each node should read so a self-review subtree is **visibly non-independent** to a human reader (the 2026-06-15 architect-self-review case is the worked example — verify it produces a visibly non-independent subtree in a test).
- The header/label or `--help` text must state the lineage is **best-effort/untrusted observability**, not verified.
- Keep `--json` working alongside `--tree` (decide the shape: a nested tree or the flat list — document it; flat list + a client-buildable edge set is acceptable and simplest).

### 2. `sq <type> <n> show --full` session surfacing
- `show` / `show --full` (the `show_any` command in `_cli/_main.py` and the per-type show path) surfaces the **creating** and **last-modifying** actor's session identity **where recorded** — from the optional `created_session`/`modified_session` frontmatter fields landed in TASK-159 (and/or by joining the item id against the reflog).
- Render `slug @ session_id (parent <parent_session_id>)` so a self-authored item reads differently from an independently-authored one. **Gracefully show just the slug** when no session is recorded (the common/legacy case) — no layout breakage, no error.
- Wrap any dynamic id/slug output with `_cli._common.e()` (Rich markup-escape convention).

## Acceptance
- `sq reflog --tree` renders a parent→children tree from recorded edges; no/unknown parent = root; **missing intermediate sessions degrade to a forest, never error.**
- The 2026-06-15 self-review scenario produces a **visibly non-independent subtree** (covered by a test fixture).
- The view + its docs/`--help` note the **best-effort/untrusted** nature; no tamper-evidence claim.
- `sq <type> <n> show --full` surfaces creating + last-modifying session (slug @ session, parent) where recorded; **degrades to slug-only** when absent; legacy items render unchanged.
- Back-compat: a reflog/squad with **only slug-only entries** renders `--tree` as a flat forest of roots (no crash); legacy items show slug-only.
- `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean; full `uv run pytest` green.
- New tests: service/CLI for `--tree` (forest from slug-only; nested tree from edges; missing-intermediate forest; self-review subtree) **and** a CLI smoke test for `show --full` session surfacing (present + absent cases).

Out of scope: the data-model/reflog/schema/migration work (→ TASK-159, must land first).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 160 add-subtask "<title>"`; track with `sq task 160 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Spawn-tree view + show --full session surfacing (best-effort, untrusted) | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Spawn-tree view + show --full session surfacing (best-effort, untrusted)

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US2 — Spawn-tree view in sq reflog
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
- [2026-06-22T09:13:26Z] Olivia Lead:
  - @python-dev US2 of FEAT-125 / ADR-158 — the spawn-tree view + show --full session surface. DEPENDS ON TASK-159 (depends-on ref linked): the reflog session fields + frontmatter session fields must land first; this task only renders on top of that recorded data. Start once 159 is Done.
  - Add sq reflog --tree: build a parent->children map from recorded session_id/parent_session_id edges over the existing filters; no/unknown parent = root; a missing intermediate session degrades to a FOREST, never an error. The 2026-06-15 architect-self-review case must produce a visibly non-independent subtree (cover it in a test). show --full surfaces creating + last-modifying session (slug @ session, parent) where recorded, degrading to slug-only when absent. Escape dynamic output with _common.e().
  - Framing is non-negotiable: this is forensic observability, NOT verification — the tree reflects declared, untrusted lineage; a copied session id appears as a legitimate edge. The view + its --help/docs must say best-effort/untrusted, with no tamper-evidence claim. Acceptance: back-compat (slug-only reflog renders as a flat forest; legacy items show slug-only); pyright + ruff + format clean; full pytest green; service + CLI smoke tests.
- [2026-06-22T10:59:40Z] Elias Python:
  - Implementation complete. Summary of what changed:
  - src/squads/_cli/_main.py — added --tree flag to the reflog command. Added three helper functions: _reflog_entry_line (formats one entry as Rich markup), _build_session_maps (partitions entries into session_id buckets + parent/children edge maps, extracted for testability), _attach_session_node (recursive tree attachment). _render_reflog_tree builds the Rich Tree from the maps: session-less entries become slug-only roots; sessions whose parent is absent/unknown become forest roots with a '(parent X not in view — forest root)' label; sessions with known parents are nested under their parent node. The best-effort/untrusted header is always printed first.
  - src/squads/_cli/_common.py — _build_item_panel_rows now surfaces created_session and modified_session where present. The author row shows 'author: slug @ session_id (best-effort session, untrusted)' when created_session is set, plain 'author: slug' otherwise. A separate 'last-modified session: ...' row appears when modified_session differs. Legacy items with no session fields render unchanged.
  - show --full session surfacing: TASK-159 did NOT surface session in the show panel — that was explicitly out of scope for 159. This task (160) adds it here.
  - tests/test_reflog_tree.py — 27 new tests: unit tests for _build_session_maps (empty, no-session, single-root, chain, unknown parent, first-occurrence wins, mixed); _render_reflog_tree output-capture tests (empty, no-session, single-root, manager→dev chain, 3-level, unknown-parent forest, missing-intermediate forest, self-review single-root); CLI smoke tests for sq reflog --tree (exits 0, best-effort note, session in output, flat forest for slug-only, --json still works); CLI smoke tests for show session surfacing (present + absent); service-level tests (3-level chain, unknown parent forest, legacy no-session, self-review same-session groups as one root).
  - Gates: uv run pyright: 0 errors. uv run ruff check: clean. uv run ruff format --check: clean. uv run pytest: 917 passed, 1 skipped.
  - @reviewer
- [2026-06-22T11:09:15Z] Paul Reviewer:
  - Reviewed under REV-162 (reviews FEAT-125 US2). Solid work — gates all green (pyright 0, ruff+format clean, full pytest exit 0, 27 new tests). --json back-compat preserved (flat list, evaluated before --tree), tree is display-only, best-effort/untrusted framing present and faithful on every surface, e() escaping complete, show --full degrades cleanly for legacy items. The no-infinite-loop property genuinely holds — reachable-from-root cycles are structurally impossible.
  - MEDIUM blocks approval (REV-162 F1): a pure session cycle in forged/corrupt declared edges (A.parent=B, B.parent=A) silently DROPS the cycled sessions — they render nowhere (neither session nor no-session branch). No crash/loop, but on untrusted input 'forge a self-loop to make operations vanish from the lineage view' defeats the forensic purpose. Required: every session_id in the data must surface somewhere — add a reachability pass that emits unvisited sessions as forest roots, plus a visited-set in _attach_session_node so the never-loop contract survives future refactors.
  - LOW (F2): no cyclic/pathological-edge test for the renderer — add one asserting no-raise/no-loop AND that cycled sessions still appear (couples to the F1 fix). Minor FYI: the render-level self-review test assertion is loose (count>=1 + bare 'create' substring); the service-level test carries the real check, so not blocking.
  - @python-dev please address F1 (and its test, F2); re-request review when done. Leaving InReview.
- [2026-06-22T11:35:49Z] Elias Python:
  - F1 fix (MEDIUM): added a reachability pass in `_render_reflog_tree` — after the normal root walk, any session_id in `session_entries` not yet in the `visited` set is emitted as a cycle/forest root with a '(parent X — cycle/forest root)' label. This ensures every session surfaces somewhere regardless of cyclic declared edges. The `visited` set is now threaded through `_attach_session_node` as a belt-and-suspenders guard: each child_sid is checked before recursing and skipped if already visited, so the never-loop contract holds even if a future refactor makes a cycle reachable from a root.
  - F2 fix (LOW): added three renderer tests in `tests/test_reflog_tree.py` — `test_render_tree_two_node_cycle_does_not_raise_and_both_appear` (2-node cycle, both sids in output), `test_render_tree_self_loop_does_not_raise_and_session_appears` (self-loop, sid in output), `test_render_tree_cycle_entries_each_appear_exactly_once` (each session node rendered exactly once via markup-tag count). All three assert no-raise/no-loop AND that cycled sessions surface.
  - Gates: uv run pyright — 0 errors. uv run ruff check + ruff format --check — clean. uv run pytest — 920 passed, 1 skipped (30 tests in test_reflog_tree.py, all green). No previously-approved behavior regressed.
  - @reviewer re-review ready under REV-162. Only changes are in `src/squads/_cli/_main.py` (reachability pass + visited-set guard in two functions) and `tests/test_reflog_tree.py` (3 new tests). --json flat shape, e() escaping, show --full surfacing, best-effort header all unchanged.
- [2026-06-22T11:50:44Z] Paul Reviewer:
  - Re-review passed, approved (REV-162 Approved). Both prior findings Verified: F1 cycle silent-drop fixed (reachability pass surfaces every session exactly once; visited-set guard makes never-loop structural), F2 cycle/self-loop tests added. No regression in --json, header, or e() escaping. Gates green: pyright 0, ruff + format clean, pytest 920 passed / 1 skipped. Ready for QA. @qa
- [2026-06-22T11:59:26Z] Mara Tester:
  - Verified TASK-160. All checks pass — marking Done.
  - Suite: 920 passed, 1 skipped (full suite green). test_reflog_tree.py: 30/30 green, including 3 new F1/F2 cycle tests.
  - Behavioral checks confirmed in a fresh squad at /tmp/sq_mara_test3:
  - 1. manager->tech-lead->dev chain (mgr-sess-aaa->tl-sess-bbb->dev-sess-ccc) renders as a proper 3-level nested tree.
  - 2. No-session entries appear as forest roots labelled 'actor=X (no session recorded)' — none dropped.
  - 3. Header always shows 'BEST-EFFORT / UNTRUSTED / OBSERVABILITY-ONLY' and 'no tamper-evidence or enforcement guarantee'. No overclaim anywhere.
  - 4. Empty (no entries) renders: header + 'no reflog entries'. No error.
  - 5. CYCLE ROBUSTNESS (F1 fix verified live): injected 2-node cycle (SIDCYCLE-A parent=SIDCYCLE-B, SIDCYCLE-B parent=SIDCYCLE-A) and self-loop (SIDSELF-LOOP parent=SIDSELF-LOOP) into .reflog.jsonl. sq reflog --tree did NOT hang, did NOT raise, and ALL cycled sessions appeared in output: SIDCYCLE-A labelled '(parent SIDCYCLE-B — cycle/forest root)' with SIDCYCLE-B nested under it; SIDSELF-LOOP labelled '(parent SIDSELF-LOOP — cycle/forest root)'. Exactly what the F1 fix promises.
  - 6. show --full surfaces session: TASK-000011 (created with SQUADS_SESSION_ID=mgr-sess-aaa) shows 'author: manager @ mgr-sess-aaa (best-effort session, untrusted)'. TASK-000009 (no session at create) shows 'author: manager' (slug-only, no layout breakage).
  - 7. --json --tree: json takes priority, flat list returned, back-compat preserved.
  - No issues found. This completes FEAT-125 US2 (both TASK-159 and TASK-160 Done).
<!-- sq:discussion:end -->
