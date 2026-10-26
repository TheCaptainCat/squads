---
id: REV-1160
sequence_id: 1160
type: review
title: 'Review TASK-1146: CLI diagnostics, --as on edits, Noted to Deferred'
status: Approved
author: reviewer
refs:
- TASK-1146
description: ST1-ST8 and ST10 of commit 0bdd5b38
subentities:
- local_id: F1
  title: Reachability lint now ignores an adopter's own entry-less states, not just
    inherited ones
  status: Verified
  severity: medium
- local_id: F2
  title: Check message names skills as registered, but the check reports a skill author
  status: Verified
  severity: medium
- local_id: F3
  title: view add and view disable take --as but write no reflog line to attribute
  status: Verified
  severity: low
- local_id: F4
  title: Roster create verbs write a reflog line with no --as, against ADR-117 section
    3
  status: Verified
  severity: low
- local_id: F5
  title: CHANGELOG and workflow.md still say an Open-redeclaring override has no Noted
    or Deferred
  status: Verified
  severity: low
- local_id: F6
  title: TASK-717 byte-unchanged guarantee is stale after ST3 and ST10
  status: Noted
  severity: info
- local_id: F7
  title: 'Two branches of the inherited-transition drop go untested: the lint-path
    call and the written guard'
  status: Verified
  severity: low
- local_id: F8
  title: docs/stability.md op table lacks the new view reflog op
  status: Deferred
  severity: info
  deferred_to: TASK-1146
created_at: '2026-10-26T07:30:08Z'
updated_at: '2026-10-26T08:07:49Z'
---
<!-- sq:body -->
Review of commit 0bdd5b38 on release/0.17: TASK-1146 ST1 to ST8 and ST10 (ST9 is not done yet and is out of scope).

Method: read every subtask spec and handoff, ADR-697 and ADR-117 §3, and the diff. Drove each change on scratch squads with the dev tree's `sq`. Ran mutations on a scratch copy of the code: each change was reverted or broken in turn, and the targeted tests turned red for ST1 (dev-falsified), ST2 (the message and exit 1), ST3 (all three condition texts), ST5, ST6, ST7 (actor no-op, a skipped call site, an actor set after the write), ST8 (edge removed, old reachability) and ST10. The 281 targeted tests pass at HEAD.

Sound as specified: ST1 (seven malformed fields across items and subentity_kinds, one sentence each, no pydantic text, a shape hint), ST2, ST3, ST5, ST6 (no reader of `file` in the client, TUI or docs), ST10, and the `--as` validation, which matches a comment's for an unknown, `system`, retired, skill-slug, `@`-prefixed and upper-case slug.

The findings cover the reachability loosening, a false check message, `--as` coverage gaps at both ends, stale docs, and a rebase note for TASK-717.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1160 add-finding "…" --severity medium`; track with `sq review 1160 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Reachability lint now ignores an adopter's own entry-less states, not just inherited ones

<!-- sq:finding:F1:body -->
`check_reachability` (`_workflow/_validity.py`) now drops every state no transition leads to, plus everything only that state leads to. That covers the bundled `Noted` key left behind when an override redeclares the finding's `Open` list, but it also covers states the adopter wrote themselves, which used to be refused at lint and at load (the check runs in `WorkflowSpec._validate`).

Driven on a scratch squad (current code against the previous `_validity.py`, same overrides):

- `[statuses.Parked]` plus `[lifecycles.work.transitions] Parked = ["Ready"]` (the edge into `Parked` forgotten): before, exit 1, unreachable; now `workflow spec OK — no errors or warnings`.
- A chain `Parked = ["Shelved"]`, `Shelved = ["Ready"]`: before, both reported; now clean.
- A brand-new `incident_lc` with `Triage = ["Resolved"]`, `Escalated = ["Resolved"]` (forgot `Triage -> Escalated`): now clean. `sq incident 9 status Escalated` is refused, `--force` lands on it, and `sq check` says nothing.

Failure scenario: an adopter forgets the edge into a state they just declared. Nothing reports it. Agents can't reach the state without `--force`, and they get no hint why.

No test covers this. Mutating the rule to drop every unreachable state outside a loop turns only the loop test red.

Narrower fix: exempt only the entry-less states whose transition key comes from the bundled document and that the override doesn't name. An alternative is for the merge to drop such inherited keys when the override redeclares the lifecycle's transitions. That would also bring back the earlier behaviour where `Noted` is simply not a status of that machine, not a state `--force` can still land on. Add a table test of adopter-declared entry-less states (single, chain, new lifecycle) that must still exit 1, next to the inherited cases (`Noted`, a `Blocked` the override stops entering) that must lint clean.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-26T07:44:22Z] `python-dev` Elias Python:
  - Reverted the reachability loosening. A bundled transition key the override never names is now dropped when the override redeclares that lifecycle and nothing enters the key (_drop_inherited_unreachable_transitions, load and lint paths); an adopter-written entry-less state is reported again. Rows: own state, chain, new-lifecycle orphan (exit 1), Open-redeclaring and a Blocked the override stops entering (clean); the old Open-redeclaring service test is restored. Mutation-checked.
- [2026-10-26T08:00:12Z] `reviewer` Paul Reviewer:
  - Verified on eb5df1db: strict lint is back, and the merge drops only an inherited, unwritten, unentered key. All override shapes behave (own Parked, chain, new-lifecycle orphan exit 1; Open-redeclaring, Blocked dropped or entered, new initial, splat clean). Untested branches are in F7.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Check message names skills as registered, but the check reports a skill author

<!-- sq:finding:F2:body -->
The `agent_registered` message now reads `author 'x' is not a registered role, skill or operator`. The handoff says the check's set includes skills. It doesn't: `registered_slugs` in `_services/_validators.py` keeps only `ROSTER_ROLE` and `ROSTER_OPERATOR`, and its docstring says "A skill never authors, so it is outside the set". The only skill exemption is a skill item authored by its own slug.

Driven: in a scratch squad, set a task's `author:` to an active project skill's slug (`probe-skill`), then `sq repair` and `sq check` give `warn TASK-12: author 'probe-skill' is not a registered role, skill or operator`. The message says a skill is accepted while it reports a skill.

The suite pins the contradiction: `test_agent_registered_names_roles_and_operators_only.py`, param `id="skill"` (`pairing`, reported), asserts `"author 'pairing' is not a registered role, skill or operator"`.

Failure scenario: an adopter reads the warning, thinks registering the slug as a skill fixes it, and the warning stays.

Fix: use the spec's single wording for both paths, `not a registered role or operator` (the check and create sets already agree, so the split isn't needed). Correct the `_agent_registered` docstring. Also fix the `_is_participant` docstring in `_services/_base.py`, which says the catalog validator "treats any roster type — including a skill's slug — as registered", which is false. Then update the pinned strings and the CHANGELOG sentence that gives the two wordings.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-26T07:44:25Z] `python-dev` Elias Python:
  - One wording, not a registered role or operator, in agent_registered and the create/update checks; docstrings of _agent_registered and _is_participant corrected; pinned strings and the skill param assertion updated.
- [2026-10-26T08:00:13Z] `reviewer` Paul Reviewer:
  - Verified: one wording on the check and create paths; the skill-param test now pins the true text.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — view add and view disable take --as but write no reflog line to attribute

<!-- sq:finding:F3:body -->
`view add` and `view disable` (work item, role, skill) now take `--as`, and the help says "Attribute the edit in the reflog to this role slug". Neither verb writes a reflog line, as the table test's `_UNLOGGED` set records. The flag is validated and then has no effect.

Driven: `sq task 12 view disable children --as qa` places a disabled tag in the task's `sq:body` (an edit to the file) and adds 0 reflog lines.

Failure scenario: an agent passes `--as` expecting `sq reflog --actor qa` to show the edit, and it doesn't. The flag looks like attribution but nothing is recorded.

Pick one: make these verbs log a line (they do change the body, so a `view` op attributed like the rest is consistent with ADR-117 §3), or don't take `--as` on them. The CHANGELOG entry lists both verbs as attributed.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-26T07:44:27Z] `python-dev` Elias Python:
  - view add and view disable now write a view reflog op (delta: view name and state) when the tag changes, attributed to the actor. New op in REFLOG_OPS and the docs/workflow.md op table; ST9 must add it to the docs/stability.md op table. The --as table test now requires a line for these verbs.
- [2026-10-26T08:00:14Z] `reviewer` Paul Reviewer:
  - Verified: the view op is logged only when the tag changes, with the --as actor; mutation reddens 2 tests. stability.md row in F8.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Roster create verbs write a reflog line with no --as, against ADR-117 section 3

<!-- sq:finding:F4:body -->
ADR-117 §3: "`--as` is the actor source on every verb that writes a reflog line". The roster create verbs write a `create` line with no way to attribute it.

Driven: `sq skill add "Probe skill"` and `sq operator add "Alice Op"` each write `{"actor":"system","op":"create",...}`, and neither takes `--as`. `role activate` / `role add` and `dev add` go through the same create path.

The handoff explains the exclusion as "create or own-slug verbs". That doesn't hold for these: `sq create` attributes its `create` line through `--author`, so creating a work item is attributed and creating a roster entry isn't. Memory and board have their own stores (no reflog line), so leaving them out is fine.

Failure scenario: `sq reflog --actor manager` doesn't show the roles and skills the manager added, which is exactly the audit question the reflog exists to answer.

Fix: add the optional `--as` (via `apply_edit_actor`) to `role activate`/`add`, `skill add`, `operator add` and `dev add`. Or have the architect narrow ADR-117 §3 with a stated reason, but not leave a silent gap between the ADR and the code.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-26T07:44:29Z] `python-dev` Elias Python:
  - Optional --as on skill add, operator add, role add, role activate and dev add, validated like the rest; rows added to the table test (the create line carries the actor). sq create keeps --author.
- [2026-10-26T08:00:15Z] `reviewer` Paul Reviewer:
  - Verified: the five create rows (skill add, operator add, role activate, role add, dev add) record the --as slug and system without it; mutating skill add or dev add reddens the table.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — CHANGELOG and workflow.md still say an Open-redeclaring override has no Noted or Deferred

<!-- sq:finding:F5:body -->
Three adopter-facing statements no longer match the shipped behaviour:

- CHANGELOG `[0.17.0]`, the "A finding can be closed as Noted or Deferred" entry (same unreleased section) still says "neither has an outgoing edge, so reopening one takes `--force`" and "An override that redeclares the finding's `Open` list keeps its own lifecycle, without either state". The new entry beside it contradicts both. In an unreleased section the earlier entry should be amended, not answered by a second one.
- `docs/workflow.md` (the override paragraph after "Closing a finding as Noted or Deferred") says "your lifecycle stays as you wrote it, without `Noted` or `Deferred`". With that override, `sq workflow lifecycles` lists `Deferred, Noted` among the finding states and the edge `Noted → Deferred`, and `--force` can move a finding there.
- The new CHANGELOG entry "A lifecycle state with no way in is no longer reported as unreachable when it only leads onward from a dropped edge" describes a narrower rule than the code. The code exempts every entry-less state, not only one left by a dropped bundled edge (see the reachability finding).

Failure scenario: an adopter reads the docs, assumes `Noted`/`Deferred` don't exist in their machine, and then finds findings `--force`d into them.

Fix: decide the reachability finding first, then make the CHANGELOG and docs describe what remains (the tech writer's pen).
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-26T07:44:32Z] `python-dev` Elias Python:
  - CHANGELOG and docs/workflow.md now say an Open-redeclaring override has neither state; the reachability and two-wording CHANGELOG sentences are gone or corrected, and the --as entry lists the create verbs and the view op.
- [2026-10-26T08:00:18Z] `reviewer` Paul Reviewer:
  - Reopened: CHANGELOG.md line 23 (the Noted/Deferred entry) still says both states have no outgoing edge, so reopening one takes --force. Noted now has Noted -> Deferred. The other two bullets are fixed.
- [2026-10-26T08:06:34Z] `python-dev` Elias Python:
  - CHANGELOG line 23 no longer says neither state has an outgoing edge; it now says reopening either takes --force.
- [2026-10-26T08:07:43Z] `reviewer` Paul Reviewer:
  - Verified on ef2d9f83: CHANGELOG line 23 now says reopening either takes --force, with no outgoing-edge claim.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — TASK-717 byte-unchanged guarantee is stale after ST3 and ST10

<!-- sq:finding:F6:body -->
ST3 ran before TASK-717 (Draft), as the handoff says. Driven: the refusal now names the status once (`cannot move SKILL-19 to 'Archived': ... not live but implied by declared type(s): task`), and the reporter shares the text. Mutating any of the three condition texts back reddens 2 to 5 pinned tests, so the guarantee is held.

The conflict for TASK-717: its ST1 says the no-unlink rendering assertion in `tests/unit/test_roster_config_integrity_predicates.py` and the reactivation refusal in `tests/service/test_retirement_refuses_a_config_breaking_transition.py` "must pass byte-unchanged", and that "only these three" assertions change. Both files were edited here (ST3 condition text, ST10 `type_implied` remedy and `removal_remedy`). TASK-717 as written would be measured against strings that no longer exist.

Fix: before TASK-717 is dispatched, the tech lead rebases its "may change / may not" list onto the current strings. No code change here.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-26T07:44:33Z] `python-dev` Elias Python:
  - Noted, no action.
- [2026-10-26T08:00:34Z] `reviewer` Paul Reviewer:
  - Noted: nothing to fix in this commit; the rebase note sits on TASK-717 for the tech lead.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Two branches of the inherited-transition drop go untested: the lint-path call and the written guard

<!-- sq:finding:F7:body -->
`_drop_inherited_unreachable_transitions` (`_workflow/_loader.py`) behaves correctly on every shape driven: an own `Parked`, a `Parked -> Shelved` chain and a new lifecycle's orphan all exit 1. Open redeclared without `Noted`, a `Blocked` the override stops entering, a `Blocked` the override enters only from its own edge (kept), a changed `initial` and the splat form all lint clean. An own orphan that targets `Blocked` reports both. An override that writes `Noted = ["Deferred"]` itself while dropping it from `Open` reports both states. A task already sitting in a dropped `Blocked` is loud: lint and `sq check` error.

Two of its branches can be broken with every test staying green (mutations on a scratch copy, reachability, deferred-finding and lint test files: 51 passed each time):

- **The lint-path call.** `lint_workflow_spec` reuses the loaded spec when load succeeded, so the call only runs when load fails. Driven with it removed: an override that redeclares `Open` without `Noted` and also has one unrelated error (`[items.alpha] lifecycle = "nosuch"`) lints with 3 errors, adding spurious `state 'Noted' unreachable` and `state 'Deferred' unreachable`. With the call in place it reports the 1 real error.
- **The `s not in written` guard.** With the guard deleted, a bundled key the override writes itself (`Noted = ["Deferred"]` with `Open` not entering it) would be dropped silently instead of reported. No test covers it.

Failure scenario: a later refactor drops either line, and the adopter gets extra unreachable errors next to a real one, or an explicitly written but unentered state disappears with nothing said.

Fix: add two rows to `test_lifecycle_reachability_lint_cli.py`. The first is Open-redeclaring plus one unrelated error, asserting exactly one error and no `unreachable`. The second is an override that writes the inherited key itself without entering it, asserting exit 1 and the state named.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-26T08:06:36Z] `python-dev` Elias Python:
  - Added tests/unit/test_workflow_lint_inherited_unreachable_states.py: (a) Open-redeclaring plus one unrelated error lints exactly that error (red without lint call), (b) an override naming Noted itself still reports it unreachable (red without the written guard).
- [2026-10-26T08:07:47Z] `reviewer` Paul Reviewer:
  - Verified: removing the lint-path call and deleting the written guard each turn one row of test_workflow_lint_inherited_unreachable_states.py red.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — docs/stability.md op table lacks the new view reflog op

<!-- sq:finding:F8:body -->
F3's fix adds a reflog op `view` (delta: `view`, `state` = `enabled`/`disabled`). It's in `REFLOG_OPS`, so `sq reflog --op view` works, and it's in the `docs/workflow.md` op table. The op table in `docs/stability.md` "Reflog on-disk format", which describes the closed op vocabulary for adopters, doesn't list it.

Driven: `sq milestone 10 view disable milestone_rollup --as op-pierre` writes `{"view":"milestone_rollup","state":"disabled"}` with actor `op-pierre`. A no-op (already disabled, already present) writes nothing, and placing a new tag disabled writes `state: disabled`. The VS Code client doesn't read the reflog (no op names under `clients/vscode/src`), and no other reader dispatches on op names.

Failure scenario: a reflog consumer built from `docs/stability.md` treats `view` as an unknown op.

TASK-1146 ST9 already rewrites that op table, so the row belongs there.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-26T07:30:43Z] `reviewer` Paul Reviewer:
  - Six findings: 2 medium (F1 reachability loosening, F2 false agent_registered message), 3 low (F3 --as on view verbs, F4 roster create verbs, F5 stale CHANGELOG/docs), 1 info (F6 TASK-717 rebase). Everything else is sound, and the tests for each change go red under mutation. Recommended verdict: ChangesRequested once F1 and F2 are decided; left InReview. @tech-lead for routing.
- [2026-10-26T08:00:35Z] `reviewer` Paul Reviewer:
  - Re-review of eb5df1db: F1-F4 Verified. F5 reopened (CHANGELOG line 23 still says Noted has no outgoing edge). New F7 (low): two untested branches of the inherited-transition drop. New F8 (info) deferred to TASK-1146 ST9 (stability.md view op row). F6 Noted. Not approved: F5 and F7 are open. @tech-lead
- [2026-10-26T08:07:48Z] `reviewer` Paul Reviewer:
  - All findings settled: F1-F5 and F7 Verified, F6 Noted, F8 Deferred to TASK-1146 (ST9). Approved.
<!-- sq:discussion:end -->
