---
id: REV-1076
sequence_id: 1076
type: review
title: 'Review TASK-1074: squad-global validator selection'
status: Approved
author: reviewer
refs:
- TASK-1074
description: Review of the [squad] table, the tiers and the five selectable squad-global
  members
subentities:
- local_id: F1
  title: No-selection invariant test compares against the same build, not a recorded
    baseline
  status: Verified
  severity: medium
- local_id: F2
  title: SquadGlobalContext.now is optional and stale_active silently skips without
    it
  status: Verified
  severity: low
- local_id: F3
  title: '[selected] squad is refused by two mechanisms; SELECTABLE_SECTIONS never
    decides'
  status: Verified
  severity: low
- local_id: F4
  title: dependency_acyclic reports cycles among settled items as blocking
  status: Verified
  severity: low
- local_id: F5
  title: Handoff lacks the US1-US6 bullet-to-test map; ST10's 26 issues are copy artifacts
  status: Verified
  severity: low
- local_id: F6
  title: Plural and table-shape wording in squad-global messages
  status: Verified
  severity: info
created_at: '2026-10-16T20:43:08Z'
updated_at: '2026-10-16T20:53:41Z'
---
<!-- sq:body -->
## Scope

Commit c4c413d8 on `worktree-agent-a4a6de4545a741fbd` against 4d29cecb: the `[squad]` table, the
always-on and selectable tiers, the default-level table, the load-time refusals and the five
selectable members, read against FEAT-902 US1 to US6 and ADR-982.

## What was checked, and how

- **Driven on a scratch squad (dev build):** a custom lifecycle where a task rests at `Doing`
  (a live role named `running`) and `InProgress` resolves to a non-live role. With all five
  selected, `wip_limit:1`, `unassigned_active:0`, `children_settled_with_parent` and
  `dependency_acyclic@error` each reported exactly the expected items; the `InProgress` task was
  not counted. `sq check` exited 3 on the `@error` cycle, and the `ref add` that closed the cycle
  was not refused.
- **Refusals, driven through `sq workflow lint` and `sq check`:** unknown name, a per-item name,
  an always-on name, bare, empty, `0`, `-1`, `x`, `1.5`, `3.0`, padded and `3:4` parameters, a
  parameter on `dependency_acyclic`, `@info`, an empty level, `@ERROR`, a doubled level, the same
  member twice under different parameters or levels, an uppercase name, `[selected] squad`, an
  unknown key, a non-list `validators`, and the cannot-fire case with no live role. Each was refused.
- **Members, read:** orientation through `dependency_ref_kind` per direction, self-loops through
  the SCC close, iterative Tarjan with no recursion, sub-entities never read as children, the
  `stale_active` boundary at strictly more than the given days, the clock read once in `report`.
- **New tests:** 270 passed, 2 skipped (the four new files, the gate test and the mutable-state
  guard), run with a scratch basetemp.

## The 26-issue dry run

These come from the copy, not from this branch. Copying only `squads/` and `.squads.toml` leaves
no `.claude/` and no `CLAUDE.md`, so `backend_reconciled` reports 2 errors (`CLAUDE.md`,
`.claude/settings.json`) and 24 missing-pointer warnings. After `migrate up`, `sync` brings
`sq check` on the copy to "no issues". The released tool on the live board also reports no
issues. Selecting `children_settled_with_parent` and `dependency_acyclic` on the migrated and
synced copy reports nothing. An independent scan of the index found no settled parent with an
open child, and no cycle among the 245 dependency edges.

## Recommended verdict

ChangesRequested, for the medium finding only (the no-selection invariant test). The rest are
low or nit and can be fixed in the same pass. The engine itself behaved correctly on every shape
probed.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1076 add-finding "…" --severity medium`; track with `sq review 1076 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — No-selection invariant test compares against the same build, not a recorded baseline

<!-- sq:finding:F1:body -->
The task asks for "a squad that selects nothing gets exactly the issues it got before (golden over a corpus fixture)". `test_a_squad_that_selects_nothing_gets_the_issues_it_got_before` in `tests/service/test_squad_selection_in_sq_check.py` does not test that, for three reasons:

- **The comparison is not with before.** It builds "before" from the same build's always-on members, with the levels this commit rewired. A level regression in an always-on member shows up on both sides.
- **It only checks a subset.** It asserts that every issue in the reference appears in `check()`. A new issue that `check()` adds is caught only when it carries one of the selectable members' marker texts.
- **It filters the reference.** It drops every reference issue whose message contains "index". That is a substring filter, not a member filter.

Fix: pin a recorded issue list (level, item, message) for a corpus fixture that triggers each always-on member, and assert equality with nothing selected. The dry run on this repository's squad shows no regression in practice, so this is about the proof, not the code.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-16T20:50:04Z] `python-dev` Elias Python:
  - Fixed: the no-selection test now asserts exact equality with a baseline recorded from the preceding build (4d29cecb) over a corpus triggering index_reconciled, backend_reconciled and default_designation_duplicated, with no filter. Falsification: changing an always-on default level turns 3 new tests red.
- [2026-10-16T20:53:16Z] `reviewer` Paul Reviewer:
  - Verified on dd15be98: the recorded baseline passes unchanged against the 4d29cecb build. Leaving out roster_config_integrity, roster_slug_valid and playbook_guide_role_live is acceptable. The diff only threads their level through the resolver, and that path is pinned by the default-level table test and the no-level-literal AST guard.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — SquadGlobalContext.now is optional and stale_active silently skips without it

<!-- sq:finding:F2:body -->
`SquadGlobalContext.now` defaults to `None`, and `_stale_active` returns `[]` when it is `None`. So a caller that builds a context without the instant turns off a selected check without saying so. `test_a_member_run_without_an_instant_reports_nothing` pins that behaviour.

`report()` is the only builder, and it always supplies `now`. Make the instant required (no default), or have the member raise when it is missing. Then drop the test that pins the silent skip.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-16T20:50:06Z] `python-dev` Elias Python:
  - Fixed: SquadGlobalContext.now is required (no default), the None guard and the test pinning the silent skip are removed; every builder passes clock.now(). Structural: enforced by construction and pyright, no test to turn red.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — [selected] squad is refused by two mechanisms; SELECTABLE_SECTIONS never decides

<!-- sq:finding:F3:body -->
Two mechanisms refuse `[selected] squad`. `_selected_squad_violations` runs before the merge, in both load and lint, and raises or returns first. `SELECTABLE_SECTIONS` (`_workflow/_loader.py`) is then handed to `merge_override`, which uses it only to validate `[selected]` section names, so it never decides anything for `squad`.

Keep one. The custom check carries the better message, so drop `SELECTABLE_SECTIONS` and pass `WORKFLOW_TOP_LEVEL_SECTIONS` as before. Or keep the set and give `merge_override` the custom message. Either way, one refusal path.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-16T20:50:08Z] `python-dev` Elias Python:
  - Fixed: SELECTABLE_SECTIONS removed; [selected] squad has one refusal path (the custom message). Falsification: dropping the custom refusal turns 1 new test red.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — dependency_acyclic reports cycles among settled items as blocking

<!-- sq:finding:F4:body -->
`_dependency_edges` takes every dependency ref, whatever the status of the two items. A cycle between two Done items is reported as "each waits on another, so none can start", which is not true: nothing waits, and `sq blocked` shows nothing.

FEAT-902 justifies the check by the permanent mutual block that `sq blocked` would render, and that block only exists among open items. Either restrict the graph to edges whose items are not settled (the `settled` flag, never a name), or keep every edge and reword the message so it does not claim a block. Add a settled-cycle row to the graph-shape table either way. Raised for a decision, since the stories do not rule on status.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-16T20:50:10Z] `python-dev` Elias Python:
  - Fixed per the manager ruling: dependency_acyclic reports every group of dependency edges, settled or not, as "dependency cycle: A -> B -> A" (each depends on the next), plus "(also involving ...)" for a larger group; no claim about what can start. Falsification: reintroducing the block claim turns 10 new tests red; skipping settled items turns 1 red.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Handoff lacks the US1-US6 bullet-to-test map; ST10's 26 issues are copy artifacts

<!-- sq:finding:F5:body -->
The task's acceptance says "the handoff maps bullet to test" for every acceptance bullet of FEAT-902 US1 to US6. The delivery comment on TASK-1074 lists the tiers, levels and splat, but there is no bullet-to-test map.

ST10 also records "26 issues with nothing selected" without saying where they come from. They come from the copy, not the branch: there is no `.claude/` or `CLAUDE.md` in the copy, and `sync` clears them (see the review body). Add the map, and correct the ST10 note so the release-preparation step does not read 26 as a baseline.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-16T20:50:12Z] `python-dev` Elias Python:
  - Fixed: bullet-to-test map and the ST10 correction are on TASK-1074.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Plural and table-shape wording in squad-global messages

<!-- sq:finding:F6:body -->
Some messages have plural and table-shape mistakes:

- `_unassigned_active` prints "1 active items have no assignee".
- `_stale_active` prints "(more than 1 days)".
- `_wip_limit` prints "holds 1 active items" when the limit is 0. That limit is refused, so only the plural rule matters there.
- `[squad]` given as a non-table gets the generic `as_table` text, "declare it as [squad] with one key per entry". The table has one key, a list.

`_children_settled_with_parent` already switches between child and children. Do the same in the other members, and pass a squad-specific hint for the non-table case.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-16T20:50:15Z] `python-dev` Elias Python:
  - Fixed: singular forms for item/day, and a squad-specific hint when [squad] is not a table. Falsification: unassigned singular 2 red, days singular 1 red, hint 1 red.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T20:43:55Z] `reviewer` Paul Reviewer:
  - Review of c4c413d8 done: 6 findings (1 medium, 4 low, 1 info). Recommended verdict: ChangesRequested, for F1 (the no-selection invariant is not pinned against a baseline). The engine behaved correctly on every shape probed. The 26 dry-run issues come from the copy, which has no .claude/ or CLAUDE.md, and sync clears them. F4 needs a decision. @python-dev @manager
- [2026-10-16T20:44:32Z] `manager` Catherine Manager:
  - F4 ruling (simplest predictable rule): dependency_acyclic reports every cycle, settled or not, worded neutrally as a cycle with its path; no claim about what can start.
- [2026-10-16T20:53:17Z] `reviewer` Paul Reviewer:
  - Fixes in dd15be98 verified; F1 to F6 Verified. 712 targeted tests pass, and the F1 baseline also passes on the base build. F4 follows the manager ruling: every cycle is reported with its path, worded neutrally. Recommended verdict: Approved. The approver makes that transition, since a reviewer approving its own review skips the two-party gate. @manager
- [2026-10-16T20:53:41Z] `manager` Catherine Manager:
  - Approved on the reviewer's verification of all six findings (dd15be98). Merge into release/0.16 follows TASK-990's commit.
<!-- sq:discussion:end -->
