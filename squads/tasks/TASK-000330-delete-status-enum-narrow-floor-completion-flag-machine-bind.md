---
id: TASK-330
sequence_id: 330
type: task
title: Delete Status enum; narrow floor + completion-flag machine binding
status: Done
prefix: TASK
parent: FEAT-326
author: tech-lead
subentities:
- local_id: ST1
  title: Delete Status enum; narrow _RESERVED_FLOOR to Draft/Active/Archived + STATUS_*
    constants
  status: Done
  story: US2
- local_id: ST2
  title: Add completion flag + one-completion-per-machine validation; flag default_workflow.toml
  status: Done
  story: US2
- local_id: ST3
  title: Sub-entity create=start state, done-toggle=completion status (no Status literals)
  status: Done
  story: US2
- local_id: ST4
  title: Freeze Status refs in _v0_4_to_v0_5.py + _meta_compat.py to inline frozen
    local status-name constants
  status: Done
  story: US2
created_at: '2026-07-07T14:50:24Z'
updated_at: '2026-07-08T15:41:23Z'
---
<!-- sq:body -->
## Scope

Remove the `Status` `StrEnum` so the spec's `[statuses.*]` is the sole status
vocabulary; narrow the reserved floor to the **agent lifecycle** only; and bind
sub-entity/finding lifecycle **by role in the state machine** via a new
`completion` flag layered on FEAT-211's `terminal` flag. Implements the
status-axis half of ADR-322 (US2). This is the primary bisectable unit for the
status axis.

Because deleting the enum is only green once **no code still references it**,
this task also freezes the `Status` references in the migration runners that use
them — `_v0_4_to_v0_5.py` and `_meta_compat.py` — to inline frozen local
status-name constants (the status-axis migration-vocabulary freeze was moved
here from TASK-331). A grep-clean / pyright-clean delete is impossible while the
runners still import the enum being removed.

## Areas / files

- `_models/_enums.py` — delete the `Status` `StrEnum`.
- `_workflow/_loader.py` — drop the `Status(value)` coercion (keys stay `str`).
- `_workflow/_models.py` — `StatusSpec` keyed by `str`; narrow `_RESERVED_FLOOR`
  to exactly `Draft`/`Active`/`Archived` (the agent lifecycle); add a
  `completion` (done-role) flag on `StatusSpec` layered atop the existing
  `terminal` flag; add spec-load validation that each sub-entity/finding machine
  names **exactly one** completion status (a machine with >1 terminal must
  designate one completion, distinct from cancel-style terminals).
- `_workflow/default_workflow.toml` — flag each sub-entity/finding machine's
  completion status (`Done`/`Fixed`) so the done-toggle resolves the same
  end-state it does today with no override (byte-identical behavior).
- `_services/_subentities.py` — `create` sets the machine's **start state** (no
  `Status.TODO` literal); the done-toggle resolves the machine's **completion**
  status (no `Status.DONE` literal); terminal-but-not-done states
  (`Cancelled`/`WontFix`) must not satisfy the toggle.
- `_services/_maintenance.py`, `_roster.py` — `Status.ACTIVE` (role/skill/operator
  creation) → validated `STATUS_ACTIVE` constant; add `STATUS_DRAFT`/`STATUS_ARCHIVED`
  constants as needed. These stay reserved (agent lifecycle).
- `_models/_item.py`, `_subentity.py`, `_services/_results.py`, `_retype.py`,
  `_cli/_items.py`, `_cli/_main.py`, `_discussion.py` — drop the `Status`
  re-export; flip `Status` annotations to `str`. Status badge/filter rendering is
  already spec-resolved via `status_badge()`.
- **Migration runners — `Status` freeze.** `_migrations/_v0_4_to_v0_5.py` and
  `_migrations/_meta_compat.py` — replace `Status.X` references with **inline
  frozen local status-name constants** equal to the status names exactly as they
  existed at that schema version. These constants are a **point-in-time snapshot
  frozen into the runner — never the live spec and never the (now-removed)
  enum**; a migration transforms files as they were at the version it targets,
  so its status vocabulary must be pinned, not re-derived. (`_v0_4_to_v0_5.py`'s
  `ItemType` references are frozen under TASK-328; this task owns only its
  `Status` references.)

## Done criteria

- `grep -rn '\bStatus\b' src/squads` returns no vocabulary-enum hits (verify
  identically-named locals by hand) — including `_v0_4_to_v0_5.py` and
  `_meta_compat.py`.
- `_RESERVED_FLOOR == {Draft, Active, Archived}`; the sub-entity statuses
  (`Todo`/`InProgress`/`Blocked`/`Done`/`Cancelled`) and finding statuses
  (`Open`/`Fixed`/`Verified`/`WontFix`) are ordinary spec vocabulary
  (renamable/reorderable, referenced nowhere by literal name).
- Sub-entity/finding `create` and done-toggle resolve via machine role /
  `completion` flag; byte-identical to today on the bundled default spec.
- Spec load rejects a sub-entity/finding machine that lacks exactly one
  completion status.
- The two migration runners pin their status vocabulary as frozen local
  constants (not the live spec, not a removed enum); historical migration tests
  still reproduce.
- `pyright` + `ruff check` + `ruff format --check` clean (this absorbs the
  status-axis half of the enum→`str` annotation inversion).

## Sequencing note

The floor narrowing, the `completion` flag, and the machine-role binding are
behavior-preserving and can precede the `Status` deletion; deleting the enum
last flips the remaining annotations to `str` and requires the migration-runner
`Status` freeze (folded in here) to already be in place — the delete is only
grep/pyright-clean once every reference is gone. Runs after TASK-328 so the two
tasks don't both edit `_v0_4_to_v0_5.py` concurrently.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 330 add-subtask "<title>"`; track with `sq task 330 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Delete Status enum; narrow _RESERVED_FLOOR to Draft/Active/Archived + STATUS_* constants | US2 |
| ST2 | Done |  | Add completion flag + one-completion-per-machine validation; flag default_workflow.toml | US2 |
| ST3 | Done |  | Sub-entity create=start state, done-toggle=completion status (no Status literals) | US2 |
| ST4 | Done |  | Freeze Status refs in _v0_4_to_v0_5.py + _meta_compat.py to inline frozen local status-name constants | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Delete Status enum; narrow _RESERVED_FLOOR to Draft/Active/Archived + STATUS_* constants

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US2 — Statuses become ordinary spec vocabulary
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Delete the Status StrEnum from _enums.py; drop the Status(value) coercion in _workflow/_loader.py (keys stay str). Narrow _RESERVED_FLOOR to exactly Draft/Active/Archived and add validated STATUS_ACTIVE/STATUS_DRAFT/STATUS_ARCHIVED constants for the agent-lifecycle bindings in _maintenance.py/_roster.py. Flip remaining Status annotations to str.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Add completion flag + one-completion-per-machine validation; flag default_workflow.toml

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — Statuses become ordinary spec vocabulary
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Add a completion (done-role) flag on StatusSpec layered atop FEAT-211's terminal flag, plus spec-load validation that each sub-entity/finding machine names exactly one completion status. Flag Done/Fixed as the completion status on each sub-entity/finding machine in default_workflow.toml so behavior stays byte-identical with no override.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Sub-entity create=start state, done-toggle=completion status (no Status literals)

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US2 — Statuses become ordinary spec vocabulary
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
In _services/_subentities.py, create sets the machine's start state (no Status.TODO literal) and the done-toggle resolves the machine's completion status (no Status.DONE literal); terminal-but-not-done states like Cancelled/WontFix must not satisfy the toggle.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Freeze Status refs in _v0_4_to_v0_5.py + _meta_compat.py to inline frozen local status-name constants

<!-- sq:subtask:ST4:head -->
**Status:** 🟢 Done
**Implements:** US2 — Statuses become ordinary spec vocabulary
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
Replace Status.X in _v0_4_to_v0_5.py and _meta_compat.py with inline frozen local status-name constants equal to the status names as they existed at that schema version. Point-in-time snapshot pinned into the runner, never the live spec or the removed enum. _v0_4_to_v0_5.py's ItemType refs are TASK-328's.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-08T11:40:41Z] Olivia Lead:
  - Re-scoped (pre-dispatch): folded the Status migration-vocabulary freeze into this task. It was TASK-331's, but deleting the Status enum here can't be grep-clean or pyright-clean while _v0_4_to_v0_5.py and _meta_compat.py still reference it — you can't delete a symbol while references remain. So 330's own done-criteria ('no Status hits / pyright clean') REQUIRE freezing those runner refs in the same commit.
  - New scope freezes Status.X in _v0_4_to_v0_5.py and _meta_compat.py to inline frozen local status-name constants equal to the status names as they existed at that schema version. Frozen = point-in-time snapshot pinned into the runner, never the live spec and never the removed enum. This task owns only _v0_4_to_v0_5.py's Status refs; its ItemType refs are TASK-328's. Runs after 328 so the two don't both edit _v0_4_to_v0_5.py concurrently. Added ST4 to track it.
- [2026-07-08T14:58:16Z] Elias Python:
  - ST1 done: deleted the Status StrEnum from _models/_enums.py; dropped the Status(value) coercion in _workflow/_loader.py (both item-type and status TOML keys now stay plain str, bundled and override paths unified); narrowed _RESERVED_FLOOR to exactly {Draft, Active, Archived} as a module-level frozenset in _workflow/_models.py, mirroring META_TYPES; added validated STATUS_DRAFT/STATUS_ACTIVE/STATUS_ARCHIVED string constants and re-exported them from squads._workflow; repointed _maintenance.py/_roster.py's Status.ACTIVE writes at STATUS_ACTIVE.
  - ST2 done: added StatusSpec.completion: bool = False layered on the existing terminal flag; added WorkflowSpec._check_completion_status (wired into _validate) requiring each sub-entity/finding machine — identified via ItemSpec.subentity_kind, the same lookup subentity_machine() already uses — to name exactly one status with completion=True; added WorkflowSpec.subentity_completion(kind) accessor. Flagged Done (subtask/story) and Fixed (finding) as completion=true in default_workflow.toml. Deliberately did NOT couple completion to terminal: Fixed is shared with the bug item lifecycle where it is (and must stay) non-terminal, so completion is an independent role marker, not a terminal subset.
  - ST3 done: _services/_subentities.py's set_subtask_done now resolves self.spec.subentity_completion('subtask') / self.spec.subentity_initial('subtask') instead of Status.DONE/.TODO literals; create already used subentity_initial() so no change was needed there. Cancelled/WontFix are never returned by subentity_completion (only the one flagged status is), so they can't satisfy the toggle.
  - ST4 done: froze the Status refs in _migrations/_v0_4_to_v0_5.py (_STATUS_ACTIVE local constant, alongside TASK-328's existing _SKILL_TYPE/_SKILL_PREFIX/_SKILL_FOLDER) and _migrations/_meta_compat.py (_STATUS_TODO/_STATUS_DONE local constants for the pre-2 checkbox parser; to_subentity() now passes the parsed status string straight through instead of re-validating via Status(b.status), since the removed enum's membership check is no longer available and was never this file's job to reinvent).
- [2026-07-08T14:58:32Z] Elias Python:
  - Also reworked the test suite's Status-enum usage to match (26 files): mechanical Status.MEMBER -> literal-string replacement (StrEnum members already compared equal to their string values, so this is behavior-preserving) plus targeted rewrites — test_workflow_spec.py's golden-lock set-equality/terminal/badge loops now iterate a new _helpers.BUILTIN_STATUSES tuple instead of set(Status)/for s in Status; test_reserved_vocab_omit_status_fails_closed now drops 'Active' (an actual floor member) instead of 'Done' (which left the floor); added test_former_floor_status_omission_no_longer_hits_the_reserved_floor (parametrized over the 9 former sub-entity/finding floor statuses) proving they now fail via the lifecycle-integrity check, never via the reserved-floor check; mirrored the same split in test_reserved_types_invariants.py (test_spec_missing_floor_status_raises narrowed to the 3 real floor members + a new test_spec_missing_subentity_status_no_longer_hits_the_floor). Added FLOOR_STATUSES/FORMER_FLOOR_STATUSES/BUILTIN_STATUSES to _helpers.py.
  - Verified byte-identical done-toggle behavior directly: bundled_spec().subentity_completion('subtask'/'story') == 'Done', ('finding') == 'Fixed', matching today's Status.DONE/no live finding-toggle baseline; test_collab.py::test_subtask_done_toggle (unmodified assertions, Status.DONE/.TODO replaced with literal strings) still passes. Manually confirmed spec-load rejects a machine with zero or two completion statuses (see comment).
  - Gates: uv run pyright (0 errors) + uv run ruff check . (all checks passed) + uv run ruff format --check . (161 files already formatted) all clean. Targeted tests green: test_workflow_spec/test_workflow/test_workflow_capability_flags/test_workflow_override/test_workflow_lint/test_reserved_types_invariants, test_collab/test_operators/test_skill_seeding/test_migrations/test_meta_compat/test_discussion/test_bug_workflow/test_retype/test_models/test_service/test_index/test_rendering/test_reflog_*/test_session_lineage/test_spine_characterization/test_priority_views/test_lane_derivation/test_terminal_accepted_published/test_backend_conformance/test_override_loader/test_graph/test_tree, test_custom_status_badges/test_custom_status_flow/test_status_display_characterization/test_status_banner_check/test_show_render/test_workflow_renderer_261/test_playbook. tests/test_squad_ref_hygiene.py green. Did NOT run the full ~4-min suite (main loop owns that) — everything not explicitly listed above (e.g. scale tests, other CLI smoke tests) is unverified by me.
  - Left TASK-330 InReview for the full-suite gate + review.
- [2026-07-08T15:12:58Z] Paul Reviewer:
  - CHANGES-REQUESTED (review REV-337). Independent read of the uncommitted tree. Gates re-run green (pyright 0, ruff check + format clean); 154 targeted tests pass. The mechanics are correct and I verified them directly: Status enum gone, grep clean (only display strings), _RESERVED_FLOOR=={Draft,Active,Archived}, migration status freeze in place, scope disciplined. I hand-exercised the validator (_build_spec with bad specs): it correctly rejects 0 and 2+ completion statuses for subtask/story AND finding, and the done-toggle is byte-identical (subtask/story->Done, finding->Fixed; Cancelled/WontFix never satisfy it).
  - F1 (HIGH — blocking): the completion-count validation is a required done-criterion but has ZERO automated test. grep across tests/ finds no 'completion'/'subentity_completion' coverage; test_subtask_done_toggle would pass even if the whole validation were deleted, and never touches the finding path or the negative cases. 'Manually confirmed' != a regression test. @python-dev (Elias): add negative tests (0 and 2+ completion -> SquadsError) + a positive assertion (subtask/story->Done, finding->Fixed) in test_workflow_spec.py. Small, mechanical.
  - F2 (MEDIUM — needs architect, not a code change): making completion independent of terminal deviates from ADR-322 §5's 'flag one of its TERMINAL statuses' (FEAT-326 scope repeats the same subset assumption). The decoupling is CORRECT — the finding machine is two-phase (Open->Fixed->Verified), so its natural done-target Fixed is intrinsically non-terminal regardless of the bug-sharing argument. But it's a contract-level divergence from an Accepted ADR on the 1.0 surface. @architect Robert: please bless the decoupling and amend ADR-322 §5 (completion is an independent machine-role flag that MAY be non-terminal, e.g. finding Fixed). Full reasoning in REV-337 F2.
  - F3 (LOW — forward note): the completion flag is global-per-status-name (same coupling as terminal); FEAT-212 custom sub-entity kinds may need per-machine designation. Parked for the architect/FEAT-212.
  - Disposition: approve-on-fix. Land F1's test and get Robert's F2 sign-off (+ADR amendment) and this is APPROVED — no logic change to the implementation is required.
<!-- sq:discussion:end -->
