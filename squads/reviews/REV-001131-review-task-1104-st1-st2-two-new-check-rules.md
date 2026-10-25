---
id: REV-1131
sequence_id: 1131
type: review
title: 'Review TASK-1104 ST1-ST2: two new check rules'
status: Approved
author: reviewer
refs:
- TASK-1104
description: 'Review of commit 7d538630: subentities_settled_with_parent and type_has_live_author.'
subentities:
- local_id: F1
  title: type_has_live_author cannot be silenced, so the core and minimal init presets
    never check clean
  status: Verified
  assignee: python-dev
  severity: medium
- local_id: F2
  title: Reactivate remedy names a transition the roster lifecycle may refuse
  status: Verified
  severity: low
- local_id: F3
  title: Capability-lane remedies ignore the catalog and roster roles that hold the
    capability
  status: Verified
  severity: low
created_at: '2026-10-25T00:32:32Z'
updated_at: '2026-10-25T00:54:23Z'
---
<!-- sq:body -->
## Scope

Commit 7d538630: TASK-1104 ST1 (`subentities_settled_with_parent`, selected on `[items.review] validators`) and ST2 (`type_has_live_author`, always-on squad-global). Read against REV-1099 F3/F10, the op-pierre rulings on FEAT-1101 and ADR-1102.

## Method

Read the diff, then drove the dev build in scratch squads (default, `core` and `minimal` init presets; archived, terminal-retired and capability-addressed authors; an operator-authored playbook guide; a broken roles override; a 0.16-stamped override replacing the review validators). Ran the two new tables and the touched meta/unit/service files: 144 passed, 1 xfailed.

## Verdict on the deviations

- Leaving `subentities_settled_with_parent` out of `SUBENTITY_VALIDATOR_NAMES` is right: membership would let a review moved to `records` satisfy `_clause_subentity_checked` with a policy rule while every validity check on its findings stops.
- Not adding the splat to this repo's override is right: the released 0.16 tool refuses a dangling splat, and naming the rule explicitly would fail as an unknown validator. The strict xfail reddens when the splat lands, so it cannot be forgotten.
- F10 is sound across the shapes tried: keyed on roles both sides, generic over kind, Rejected reported as the task specifies. An adopter override that replaces the review validators without the splat loses the rule silently, but the override drift warning and `sq override diff` surface the bundled change.

## Tests

One table per behaviour, boundary and failure rows only, no cross products. The eight activation edits are needed (the `project` fixture is a `minimal` roster) and minimal (one call before each clean-check assertion). They are also the first evidence for F1.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1131 add-finding "…" --severity medium`; track with `sq review 1131 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — type_has_live_author cannot be silenced, so the core and minimal init presets never check clean

<!-- sq:finding:F1:body -->
**Driven.** `sq init --roles minimal`, then one item of each bundled type: `sq check` gives nine warnings, one per type. `--roles core` gives five (bug, contract, epic, feature, milestone). The `project` test fixture is `minimal`, which is why eight test files had to activate roles before asserting a clean check.

The rule is always-on: `[squad] validators` refuses it ("always runs and cannot be selected"), and there is no level that turns it off. A squad that picked one of the presets `sq init` offers, and lets the default role or a human write those types, can never get a clean `sq check` except by activating roles it chose to leave out. A human author cannot be declared: a playbook guide naming `op-alice` is refused ("role slug 'op-alice' not in role catalog").

US5 says both rules stay silent when the squad is sound, and a shipped preset is sound by construction. Counting the default role as an author would silence F3's own reproduction (the manager is always live), so that is not the fix. Recommend giving the squad a way to declare the gap deliberate, for example a selectable rule that `sq init` turns on, or an off level for this rule. This is a design call for the tech lead, possibly op-pierre.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-25T00:36:12Z, edited 2026-10-25T00:36:24Z] `tech-lead` Olivia Lead:
  - Ruling: `type_has_live_author` becomes a selectable squad-wide check, selected in the bundled `[squad] validators`. A squad turns it off by leaving it out of its own `[squad] validators`, and raises it with `@error`, like every other selectable check. No op-pierre ruling covers this: his 2026-10-24 rulings on FEAT-1101 settle only that F3 counts open items. Making it always-on was my call in the task plan, and the reason I gave (the bundled list is empty) goes away once the bundled spec selects it.
  - A lower level does not silence it: the only levels are warn and error. Deselecting is the off switch. A `minimal` or `core` squad still gets the warning until it opts out. That is correct: no live role writes those types, and the fix is one line.
  - Not done: operator authors in playbook guides, a per-type opt-out, or treating the default role as an author. Add them only if a squad hits a concrete failure that deselecting does not solve.
  - Change for @python-dev: TASK-1104 ST5. Move the name from `ALWAYS_ON_SQUAD_GLOBAL_NAMES` to `SELECTABLE_SQUAD_GLOBAL_NAMES`, set the bundled `[squad] validators = ["type_has_live_author"]`, and add three test rows: deselected, `@error`, and kept through `"$(*squad.validators)"`. @tech-writer rewords the CHANGELOG and docs in ST6.
- [2026-10-25T00:45:07Z] `python-dev` Elias Python:
  - Fixed: type_has_live_author is now a selectable squad-wide check, selected in the bundled [squad] validators; deselect by leaving it out, raise with @error. Rows: deselected, raised-to-error, kept via the squad splat. The eight activation edits stay: the fixture still selects the rule.
- [2026-10-25T00:53:59Z] `reviewer` Paul Reviewer:
  - Verified on 2a7c7ca3: minimal preset warns 9x by default, a [squad] validators = [] override gives a clean check, @error raises it (nonzero exit).
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Reactivate remedy names a transition the roster lifecycle may refuse

<!-- sq:finding:F2:body -->
**Driven.** Workflow override adding `[statuses.Retired] role = "retired"` with agent transitions `Active = ["Archived", "Retired"]`, `Archived = ["Active"]`, `Retired = []`. After `sq role reviewer status Retired` with an open review, check says: reactivate `reviewer` (`sq role reviewer status Active`). Running that command fails with "role cannot move Retired → Active (use --force to override)".

`_author_remedies` builds the command from `live_initial(ROSTER_ROLE)` for any roster entry that is not live. It never checks that the entry's current status has an edge to that live status. Recommend naming the transition only when the lifecycle allows it, and otherwise pointing at another author. The refusal text of `sq role activate` for an existing non-live role has the same blind spot, outside this commit. No test row covers a non-revivable author.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-25T00:45:08Z] `python-dev` Elias Python:
  - Fixed: the reactivate command is built only when the roster lifecycle has an edge from the role status to the live status; otherwise it names the --force form and the missing edge. Row: non-revivable author.
- [2026-10-25T00:54:00Z] `reviewer` Paul Reviewer:
  - Verified: the Retired repro now names the --force form and the missing edge; running it revives the role and check is clean. The --force choice is sound: the edge really is absent, and the message says so.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Capability-lane remedies ignore the catalog and roster roles that hold the capability

<!-- sq:finding:F3:body -->
**Driven.** Playbook override making `*plan` the author of task and `*dev` the author of bug, with roster `manager` plus an archived `python-dev`:

- task: "give a live role the 'plan' capability". No command does that, and the catalog role `tech-lead` holds `plan`, so `sq role activate tech-lead` is the remedy the spec asks for ("name the playbook's in-lane authors that exist in the catalog but are not live"). A `*review` lane with the reviewer archived gets the same generic text instead of the reactivation.
- bug: "add a developer (`sq dev add --tech <tech>`)" while `sq role python-dev status Active` brings back the developer the squad already has.

The capability branch looks only at the subject's name. Recommend expanding it to the catalog roles and roster entries that hold the capability, then reusing the activate/reactivate remedies, with "add a developer" kept for a dev lane that has none. No test row covers either shape.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-25T00:45:10Z] `python-dev` Elias Python:
  - Fixed: a capability lane expands to the catalog and roster roles holding the capability, each given its activate or reactivate remedy; add a developer remains only for a dev lane with no holder. Rows: catalog holder, archived developer.
- [2026-10-25T00:54:01Z] `reviewer` Paul Reviewer:
  - Verified: *plan names sq role activate tech-lead, *review and *dev with archived holders name the reactivation, a dev lane with no holder still says add a developer.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T00:33:07Z] `reviewer` Paul Reviewer:
  - Reviewed 7d538630 (ST1, ST2). Both deviations are sound: keeping the rule out of SUBENTITY_VALIDATOR_NAMES, and deferring the splat in the repo override until the board tool is upgraded. F10 holds on every shape tried.
  - Three findings, all on type_has_live_author: F1 medium (always-on, so the core and minimal presets never check clean; this is a design call), F2 low (the reactivate command can be refused), F3 low (capability-lane remedies). Recommended verdict: ChangesRequested on F2 and F3, and a ruling on F1.
  - @tech-lead F1 needs a design decision, possibly from op-pierre. F2 and F3 go to @python-dev on TASK-1104.
- [2026-10-25T00:54:02Z] `reviewer` Paul Reviewer:
  - F1-F3 Verified against 2a7c7ca3 (repros re-driven, 98 targeted tests pass). Verdict left to @manager.
- [2026-10-25T00:54:23Z] `manager` Catherine Manager:
  - Approved: F1-F3 Verified at 2a7c7ca3; full suite green.
<!-- sq:discussion:end -->
