---
id: REV-1067
sequence_id: 1067
type: review
title: Five 0.16 bug fixes on the agent worktree branch
status: Approved
author: reviewer
assignee: reviewer
refs:
- BUG-1000
- BUG-994
- BUG-1057
- BUG-1060
- BUG-1058
description: BUG-1000, BUG-994, BUG-1057, BUG-1060, BUG-1058 fixes
subentities:
- local_id: F1
  title: Removal gate skipped for a live entry with no direct retiring edge
  status: Verified
  severity: medium
- local_id: F2
  title: 'Suite regression: catalog-lift test purges the last live role'
  status: Verified
  severity: medium
- local_id: F3
  title: Removal refusal describes an Archived status and a reactivate remedy
  status: Verified
  severity: low
- local_id: F4
  title: Gate meta guard keeps gated apps parallel to GATED_GROUPS
  status: Verified
  severity: low
- local_id: F5
  title: Pre-repair check adds a false subtasks-container error
  status: Verified
  severity: low
created_at: '2026-10-16T18:41:28Z'
updated_at: '2026-10-25T19:37:48Z'
---
<!-- sq:body -->
Review of five bug fixes on branch `worktree-agent-a2f892de06784925e`, one commit each on top of release/0.16 at 2630bf5f:

| Bug | Commit | Subject |
|---|---|---|
| BUG-1000 | f47c926a | add-block body hint names the parent-addressed command |
| BUG-994 | 05f2328f | check reports one number carried under different ids |
| BUG-1057 | 501e42d7 | wrong-typed playbook/workflow override shapes refused cleanly |
| BUG-1060 | fa227fdf | override list/diff/update allowed past the schema gate on a behind squad |
| BUG-1058 | a3f3090b | roster removal held to the retirement gate, its warnings and the reflog |

## How it was driven

The worktree build (`uv run --all-extras sq -C <scratch>`) ran in git-inited scratch squads. The behind squad was built with the released 0.15.0 tool. Targeted pytest ran in the worktree: the changed test files (77 passed, `-n0`), then a grep-derived selection of 188 test modules plus tests/meta. Ruff, ruff format and pyright are clean on the 23 changed Python files.

## Per bug

- **BUG-1000.** All three printed hints (story, subtask, finding) run as printed and exit 0. No other site prints the old `sq <kind> body` form. Clean.
- **BUG-994.** Check reports the shared number before and after a plain `repair`, naming both files. The printed remedy, `sq repair --renumber`, clears it. The referrer's ref and body mention follow the renumbered item. A task colliding with a role number (ROLE-5 and TASK-5) renumbers the task and leaves the role alone. One adjacent pre-existing defect, F5.
- **BUG-1057.** No traceback across 22 playbook shapes, 40 workflow shapes and 8 role and catalog override shapes. Every shape fails cleanly through `check --json` (exit 3) and `list` (exit 1). Clean.
- **BUG-1060.** On a behind squad, list, diff and update run. Update rewrites only the stamp lines in `.overrides/*`, and nothing outside `.overrides/` changes. Scaffold and every corpus command stay refused. On an ahead squad (schema 0.99), all three stay refused and nothing is written. A 0.16 stamp read back by the 0.15 tool shows `current`, with no crash. One low guard gap, F4.
- **BUG-1058.** On the bundled lifecycle, the removal is refused for the last live role, the `squads` skill and `sq-task`. It warns for the default role and for open work held by a role or an operator. It writes a `remove` reflog entry, and none when it refuses. An already-archived entry is removed unchecked. Two medium findings: a gate bypass under a customised lifecycle (F1) and a suite regression (F2). F3 covers the wording.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1067 add-finding "…" --severity medium`; track with `sq review 1067 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Removal gate skipped for a live entry with no direct retiring edge

<!-- sq:finding:F1:body -->
`remove_item` gates a live entry only when `_retiring_targets(item)` is non-empty, which means the entry's *current* status has a direct edge to a non-live status. A live entry with no such direct edge skips `_enforce_retirement` entirely. In that case the removal is not checked at all: no refusal and no warnings.

Driven with the worktree build, in a fresh `init --default-names` squad with this `.overrides/workflow.toml`:

```toml
[lifecycles.agent.transitions]
Active = ["Standby"]
Standby = ["Archived", "Active"]
Archived = ["Active"]

[statuses.Standby]
role = "active"
```

ROLE-2..8 were moved to Standby and then Archived, leaving ROLE-1 (Active) as the only live role.

- `sq role ROLE-1 rm --purge` printed `removed ROLE-1` and exited 0. `sq check` then errors with `config integrity: no role entry is live, but backend(s) claude_code are active`.
- `sq skill squads rm --purge` printed `removed SKILL-20` and exited 0.

On the bundled lifecycle, both of these are refused. This is the same class of hole as the bug itself, reachable through an adopter's own lifecycle. The project rule is that customisation must not be able to break squads, and the engine keys off declared status roles, not the edges of a particular lifecycle.

Fix direction: when the entry is live, probe with a non-live status of the type's machine even when no direct edge reaches it, for example the first status whose role is not live. Alternatively, evaluate the config-integrity clauses on a trial db with the entry deleted. Either way, add the edge-less lifecycle to the table test.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-16T18:58:42Z] `reviewer` Paul Reviewer:
  - Verified fb3e2251: on an Active-Warm-Standby-Archived lifecycle and on one with two non-live statuses (pending and retired), the last live role is refused for plain rm and --purge, also from an intermediate live status, with no reflog write; non-last and already-retired roles and a custom skill are removed; squads refused.
- [2026-10-25T19:37:48Z] `reviewer` Paul Reviewer:
  - Holds: _services/_items.py::remove_item probes `_non_live_status` (no lifecycle edge needed) before `_enforce_retirement`.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Suite regression: catalog-lift test purges the last live role

<!-- sq:finding:F2:body -->
`tests/service/test_validator_catalog_lift.py::test_agent_registered_flags_a_deregistered_author` fails at a3f3090b and passes at 2630bf5f. Both runs were driven with `-n0`.

```
E   squads._errors.ConfigIntegrityError: cannot remove ROLE-1: the resulting projection would be structurally invalid:
E   - ROLE-1: no role entry is live, but backend(s) claude_code are active ...
```

The `svc` fixture has a single live role, and the test purges it. The commit fixed the identical setup in `tests/service/test_check_flags_unregistered_participant.py` with `await svc.activate_role("architect")`, but not this sibling. Apply the same one-line fix. Before handing back, run the suite, or at least a selection grepped for `remove_item(` and `purge=True` across tests/.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-16T18:58:43Z] `reviewer` Paul Reviewer:
  - Verified fb3e2251: test_validator_catalog_lift passes; targeted selection 642 passed, 0 failed.
- [2026-10-25T19:37:48Z] `reviewer` Paul Reviewer:
  - Holds: tests/service/test_validator_catalog_lift.py activates a spare role before purging ROLE-1.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Removal refusal describes an Archived status and a reactivate remedy

<!-- sq:finding:F3:body -->
A refused removal reuses the archive gate's rendering, which describes a status the entry would never reach:

```
error: cannot remove SKILL-20: the resulting projection would be structurally invalid:
- SKILL-20: not live (status 'Archived') but every role preloads it unconditionally — a permanent floor of the roster contract; no remedy exists
error: cannot remove SKILL-19: ...
- SKILL-19: not live (status 'Archived') but implied by declared type(s): task — remedy: make the skill live again, or drop the implicating type via `[selected]` in .overrides/workflow.toml
error: cannot remove SKILL-26: ...
- SKILL-26: not live (status 'Archived') but still scoped to live role(s): reviewer — remedy: sever the edge with `sq skill <addr> unlink-role <role>`, or reactivate the skill
```

The skill is live and stays live, so "not live (status 'Archived')", "make the skill live again" and "reactivate the skill" are all false for this reader. The last-live-role line ("activate another role first") reads correctly as it is.

Simplest accurate wording: the header already says what is refused, so for a removal drop the status lead-in and any reactivate clause. State only the dependency, and the step that clears it:

```
error: cannot remove SKILL-20: other entries depend on it:
- SKILL-20: every role preloads it unconditionally; it is part of the roster's permanent floor and cannot be removed
- SKILL-19: implied by declared type(s): task — remedy: drop the type via `[selected]` in .overrides/workflow.toml first
- SKILL-26: scoped to live role(s): reviewer — remedy: run `sq skill <addr> unlink-role <role>` first
```

Mechanically, store the dependency phrase on `ConfigIntegrityFinding` separately from the `not live (status X) but` lead-in. Then give `render_finding` a removal mode that omits the lead-in and the reactivate half of the remedy. This is the same pattern as the existing `unlink_available` switch, so the condition text still has one source.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-16T18:58:44Z] `reviewer` Paul Reviewer:
  - Verified fb3e2251: removal reads "cannot remove X: other entries depend on it" with dependency-only lines for floor, type-implied and scoped skills; archive wording unchanged.
- [2026-10-25T19:37:48Z] `reviewer` Paul Reviewer:
  - Holds: `sq skill squads remove --purge` on 0.17 reads "other entries depend on it" with a dependency-only line (driven).
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Gate meta guard keeps gated apps parallel to GATED_GROUPS

<!-- sq:finding:F4:body -->
`tests/meta/test_the_commands_past_the_gate_are_the_commands_that_declare_a_grant.py` walks gated verbs through a hand-written `_GATED_APPS = {"migrate": ..., "override": ...}`. It filters the top-level groups by `GATED_GROUPS`. If a group is added to `GATED_GROUPS` without an entry in `_GATED_APPS`, the walk drops it from both lists: it is excluded as a group, and its verbs are never enumerated. The guard then stays green while that group's verbs are untested. Likewise, a `past_the_gate` grant on a command in a group outside `GATED_GROUPS` is never read, and nothing reports it.

Fix: assert `set(_GATED_APPS) == GATED_GROUPS` in `test_the_walk_sees_the_whole_command_tree`. Or derive the gated apps from `app.registered_groups` by name, so there is one list.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-16T18:58:45Z] `reviewer` Paul Reviewer:
  - Verified 550cc116: gated apps derived from app.registered_groups filtered by GATED_GROUPS, with an equality assert.
- [2026-10-25T19:37:48Z] `reviewer` Paul Reviewer:
  - Holds: the gate meta guard derives gated apps from app.registered_groups filtered by GATED_GROUPS.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Pre-repair check adds a false subtasks-container error

<!-- sq:finding:F5:body -->
This defect predates the fix (reproduced at 2630bf5f), but it sits next to the new error. On the merged-tree state from the bug, before any `repair`, `sq check` prints the new shared-number error and also this:

```
error TASK-21: no 'subtasks' container section — 'subtask' declares plural 'subtasks', so `sq task 21 add-subtask` cannot write here. Revert subentity_kinds.subtask.plural in the workflow override, or change it only while no task items exist
```

The index's TASK-21 entry is read through the bug file that shares the number, so a per-item check runs against the wrong file. Its remedy tells the operator to edit a workflow override they never touched. After `repair` it disappears, and the shared-number error remains.

Suggested disposition: suppress per-item file checks for numbers in a shared-number group, since the new error already names those files. Or give it a named home as a separate bug.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-16T18:58:45Z] `reviewer` Paul Reviewer:
  - Verified 312b018b: FEAT/TASK, BUG/FEAT, ADR/ROLE, TASK/SKILL pairs report only the shared-number error, before and after repair; the same-id duplicate error still fires alone and alongside a shared number.
- [2026-10-25T19:37:48Z] `reviewer` Paul Reviewer:
  - Holds: _services/_check.py reports a shared number once via shared_number_groups and skips per-item checks under it.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T18:41:55Z] `reviewer` Paul Reviewer:
  - Verdict: ChangesRequested. Two medium findings on BUG-1058: F1, a live roster entry whose lifecycle has no direct retiring edge is removed unchecked (last live role and the squads skill, driven); F2, the commit breaks tests/service/test_validator_catalog_lift.py::test_agent_registered_flags_a_deregistered_author.
  - F3 proposes the removal wording; F4 (gate meta guard) and F5 (pre-existing false error next to the BUG-994 report) are low.
  - BUG-1000, BUG-1057 and BUG-1060 drove clean; BUG-994 remedy works as printed.
  - @python-dev F1-F3 on a3f3090b, F4 on fa227fdf; F5 needs a disposition (fix or named home).
- [2026-10-16T18:53:51Z] `python-dev` Elias Python:
  - F1-F3 fixed in fb3e2251: removal probes a directly-set non-live status so no lifecycle edge is needed; the refusal is worded as a dependency through a removal mode on render_finding; F2 test given a spare role. Falsification: F1 6 of 6 gated rows fail with the edge-based check; F3 2 of 3 wording rows fail without the removal mode.
  - F4 fixed in 550cc116: gated apps derived from GATED_GROUPS plus an equality assert; adding a ghost group fails 1 of 3 tests. F5 fixed in 312b018b: per-item checks skip a shared number, which the shared-number error already names; 1 of 3 rows reproduced the false error and fails without the fix.
  - Full suite on the branch: 11256 passed, 17 skipped, 0 failed, run with a private --basetemp because the default /tmp/pytest-of-pchat was being pruned by concurrent runs.
- [2026-10-16T18:58:52Z] `reviewer` Paul Reviewer:
  - Fixes verified (fb3e2251, 550cc116, 312b018b); all five findings Fixed. Recommend Approved.
<!-- sq:discussion:end -->
