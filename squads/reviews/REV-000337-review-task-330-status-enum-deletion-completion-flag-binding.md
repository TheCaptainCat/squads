---
id: REV-337
sequence_id: 337
type: review
title: 'Review: TASK-330 Status-enum deletion + completion-flag binding'
status: Approved
prefix: REV
author: reviewer
refs:
- TASK-330:addresses
subentities:
- local_id: F1
  title: No automated test for the completion-count spec-load validation
  status: Fixed
  severity: high
- local_id: F2
  title: completion decoupled from terminal deviates from Accepted ADR-322 §5 wording
    — needs architect sign-off
  status: Fixed
  severity: medium
- local_id: F3
  title: 'Global-per-status-name completion flag: same shared-name coupling as terminal;
    will resurface for custom sub-entity kinds'
  status: WontFix
  severity: low
created_at: '2026-07-08T15:11:40Z'
updated_at: '2026-07-08T15:24:15Z'
---
<!-- sq:body -->
Independent review of the uncommitted TASK-330 working tree (Status-enum deletion + completion-flag machine binding) on release/0.8. READ-ONLY.

Gates re-run green: pyright 0 errors, ruff check passed, ruff format 161 files clean. Targeted suites all pass (test_workflow_spec, test_collab, test_bug_workflow, test_reserved_types_invariants, test_meta_compat, test_migrations, test_squad_ref_hygiene, test_workflow_capability_flags — 154 tests).

Verified independently: Status StrEnum deleted; grep '\\bStatus\\b' src/squads has only display-string/docstring hits (no enum refs); _RESERVED_FLOOR == {Draft,Active,Archived}; sub-entity/finding statuses off the floor; STATUS_* constants are the only surviving by-name status bindings (agent lifecycle); migration runners freeze status names as inline local constants; scope disciplined (Priority/Severity + _vocab.py effective_prefix/UNRESOLVED untouched). Validator exercised by hand: rejects 0 and 2+ completion statuses for subtask/story AND finding; done-toggle byte-identical (subtask/story->Done@Todo, finding->Fixed@Open); Cancelled/WontFix never returned by subentity_completion.

Verdict: CHANGES-REQUESTED. F1 (high): the required completion-count validation ships with zero automated coverage — must add a regression test. F2 (medium): completion decoupled from terminal deviates from Accepted ADR-322 §5 — code is sound, but needs architect sign-off + ADR amendment. F3 (low): forward coupling note for FEAT-212.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 337 add-finding "…" --severity high`; track with `sq review 337 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟠 high | Fixed |  | No automated test for the completion-count spec-load validation |
| F2 | 🟡 medium | Fixed |  | completion decoupled from terminal deviates from Accepted ADR-322 §5 wording — needs architect sign-off |
| F3 | 🟢 low | WontFix |  | Global-per-status-name completion flag: same shared-name coupling as terminal; will resurface for custom sub-entity kinds |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — No automated test for the completion-count spec-load validation

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟠 High
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
Done-criteria requires: 'Spec load rejects a sub-entity/finding machine that lacks exactly one completion status.' ST2 adds _check_completion_status (wired into _validate). But NO automated test drives it — grep for 'completion'/'subentity_completion'/'must name'/'exactly one' across tests/ finds only a _helpers.py comment and unrelated shell-completion tests. test_collab::test_subtask_done_toggle exercises subentity_completion('subtask')->Done indirectly, but would still pass if the entire validation were deleted, and never touches the finding path or the zero/2+ rejection.

The dev's own comment says 'Manually confirmed spec-load rejects a machine with zero or two completion statuses' — manual, not a regression test. I re-verified it holds right now (built bad specs via _build_spec: zero->rejected, 2+->rejected, for both subtask/story and finding). But a required, load-bearing new spec invariant with zero automated coverage is exactly what silently regresses. CLAUDE.md: 'When adding a feature, add a service-level test.'

Fix: add negative tests (a spec with 0 and with 2+ completion statuses on a sub-entity/finding machine each raise SquadsError) plus a positive assertion that bundled subentity_completion resolves subtask/story->Done, finding->Fixed. test_workflow_spec.py is the natural home.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — completion decoupled from terminal deviates from Accepted ADR-322 §5 wording — needs architect sign-off

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
ADR-322 §5 (Accepted) states the done-toggle target is 'one of its TERMINAL statuses ... the success end-state, distinct from cancel-style terminals' — i.e. completion is a subset of terminal. FEAT-326 scope repeats this ('terminal-but-not-done states ... must not satisfy the toggle'). The dev instead made StatusSpec.completion INDEPENDENT of terminal: the finding machine's completion status is Fixed, which is terminal=false.

Adjudication: the code is CORRECT and the decoupling is defensible. The finding machine is two-phase (Open->Fixed->Verified); its natural done-target Fixed is intrinsically non-terminal because a verification step (Verified) follows. So completion-subset-of-terminal is simply false for any two-phase machine — this is a real modeling truth, independent of the dev's shared-Fixed argument.

But the dev's headline reasoning (Fixed is shared with the non-terminal bug status, so global terminal=true would break sq list/blocked for bugs) is only HALF the story: verified true (Fixed is used by both bug and finding lifecycles; StatusSpec.terminal is one flag per name; flagging Fixed.terminal=true would flip bug Fixed to terminal and hide/close Fixed bugs) — BUT the decoupling would be needed EVEN WITHOUT bug-sharing, because Fixed is non-terminal within the finding machine itself. Also note: the dev could alternatively have designated Verified (terminal, consistent across bug+finding) as the finding completion and kept completion-subset-of-terminal; they chose Fixed because a fixing dev asserts Fixed, not Verified (QA's call). That choice is sound but is a design call, not a mechanical necessity.

This is a contract-level divergence from an Accepted ADR that is part of the 1.0 surface (project convention: grammar/format decisions land in an ADR; ADRs impose rules). It should NOT ship silently. Recommend @architect Robert bless it and amend ADR-322 §5: drop 'one of its terminal statuses', state completion is an independent machine-role flag that MAY be non-terminal (e.g. finding Fixed), distinct from both terminal-success and cancel-style states. No code change required if blessed.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Global-per-status-name completion flag: same shared-name coupling as terminal; will resurface for custom sub-entity kinds

<!-- sq:finding:F3:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
StatusSpec.completion is a global attribute keyed by status NAME (like terminal), not per-(machine,status). The bundled default is fine (Done and Fixed don't collide across subtask/story/finding). But FEAT-212 (custom sub-entity kinds) will hit the same shared-name coupling the dev navigated for Fixed: if two sub-entity machines share a status name but want different completion semantics, or a new machine reuses 'Done' for a non-completion meaning, it's unrepresentable — you'd force Done.completion=false and break subtask/story, or get 2 completions -> load rejected.

Not a defect in this task (bundled spec validates and works; verified). Forward note for @architect / FEAT-212 / FEAT-327: the completion-flag model inherits terminal's per-name coupling. Worth deciding whether custom sub-entity vocab needs per-machine completion designation rather than a global status flag.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-07-08T15:24:13Z] Catherine Manager:
  - Deferred, not fixed in TASK-330: this is a forward-note about completion inheriting terminal's per-status-NAME (not per-machine) coupling. Harmless on the bundled default; the per-machine designation decision belongs to the custom-sub-entity-kinds work. Recorded by the architect on ADR-322 and carried forward there.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-08T15:16:23Z] Robert Architect:
  - F2 resolved (Fixed) — deviation BLESSED as-is, no code change. Decoupling StatusSpec.completion from terminal is the correct model: completion ⊆ terminal is false for any two-phase machine (finding Open→Fixed→Verified makes Fixed a non-terminal done-target), and ADR-322's own backward-compat invariant already names Fixed as the finding completion target — so the terminal-preserving alternative (Verified) would break do-nothing==today and is not available. §5's 'one of its terminal statuses' was imprecise wording; corrected via a dated clarification comment on ADR-322 (refinement, NOT a supersession — the bind-by-machine-role decision stands).
  - Does NOT block TASK-330's merge on F2 grounds. F1 (missing regression test for the completion-count validation) is a separate, valid blocker and must land before the review flips to Approved / the task closes — that's the reviewer's call, not overridden here. F3 acknowledged as a forward note for FEAT-212/FEAT-327 (per-name vs per-machine completion coupling); no action in TASK-330.
- [2026-07-08T15:16:54Z] Elias Python:
  - F1 fixed: added regression coverage in tests/test_workflow_spec.py — test_subtask_and_story_machine_with_no_completion_status_fails_to_load, test_finding_machine_with_no_completion_status_fails_to_load, test_subtask_and_story_machine_with_two_completion_statuses_fails_to_load, test_finding_machine_with_two_completion_statuses_fails_to_load (all via WorkflowSpec.model_validate on a status-swapped copy of the bundled spec), plus test_bundled_spec_resolves_one_completion_status_per_subentity_kind asserting subtask/story->Done and finding->Fixed explicitly. tests/test_workflow_spec.py (34 tests) + tests/test_squad_ref_hygiene.py green; pyright/ruff check/ruff format clean.
- [2026-07-08T15:24:14Z] Catherine Manager:
  - Reconciling to Approved: F1 Fixed (5 regression tests added exercising the completion-count validator for 0 and 2+ on both subtask/story and finding kinds + a positive assertion — verified adequate), F2 Fixed (architect blessed the completion/terminal decoupling as the only ADR-consistent model and recorded a dated clarification on ADR-322), F3 WontFix (deferred forward-note for the custom-sub-entity-kinds work). Full suite green on the final diff.
<!-- sq:discussion:end -->
