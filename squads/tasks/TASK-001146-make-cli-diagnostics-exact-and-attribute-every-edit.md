---
id: TASK-1146
sequence_id: 1146
type: task
title: Make CLI diagnostics exact and attribute every edit
status: Draft
author: tech-lead
priority: low
refs:
- MILE-1051:targets
- REV-724:addresses
- REV-97:addresses
- REV-706:addresses
- REV-191:addresses
- REV-466:addresses
- REV-94:addresses
description: Lint per-entry errors, broken overrides in diff, message wording, --json
  path, --as on edits, Noted->Deferred, reflog v docs
subentities:
- local_id: ST1
  title: Collect every per-entry shape error in workflow lint
  status: Todo
- local_id: ST2
  title: Name broken overrides in a bare override diff
  status: Todo
- local_id: ST3
  title: Stop the roster gate refusal stating the status twice
  status: Todo
- local_id: ST4
  title: Name skills in the unregistered author and assignee messages
  status: Todo
- local_id: ST5
  title: Print whole type orders as integers in the types table
  status: Todo
- local_id: ST6
  title: Key the add-<kind> --json item file as path
  status: Todo
- local_id: ST7
  title: Take an optional --as on every item-mutating verb
  status: Todo
- local_id: ST8
  title: Let a noted finding move to Deferred without --force
  status: Todo
- local_id: ST9
  title: Redefine reflog v and complete the op table in stability.md
  status: Todo
- local_id: ST10
  title: State the type_implied mechanism without advising a type drop
  status: Todo
created_at: '2026-10-25T19:56:56Z'
updated_at: '2026-10-25T22:06:41Z'
---
<!-- sq:body -->
## Goal

Every diagnostic sq prints is complete and says only what is true, and every reflog line names who made the edit: `sq workflow lint` and a bare `sq override diff` name every problem in the document, a handful of messages and one JSON key stop contradicting the surface beside them, mutating verbs take an optional `--as`, a noted finding can be deferred without `--force`, a type-implied skill refusal states its mechanism without advising a type drop, and the reflog contract in `docs/stability.md` defines `v` and every `op` as written. Ten corrections: nine python-dev, one tech-writer (ST9). ST10 runs after ST3; the rest are independent.

## Read on release/0.17 HEAD (2026-10-25)

- `_workflow/_loader.py`: the lint phase that runs `_build_spec` sits in one `try`, and the per-entry parsers raise on the first malformed entry, so a second malformed `[items.*]` entry is never reported. `_split_spec_errors` returns a non-bulleted failure whole, so the raw pydantic text (`1 validation error for ItemSpec ... https://errors.pydantic.dev/...`) becomes the finding, and the referential-integrity fix hint is attached to it.
- `_cli/_override.py` `diff`: with no name, only `STATE_DRIFTED` entries are diffed. An entry in `STATE_BROKEN` with no `cause` (a readable template override missing a required marker region) prints `no drifted overrides found` and nothing else.
- `_services/_config_integrity.py`: the `preloaded_skill` messages read `not live (status 'Archived') but ...`. The retirement gate prefixes `cannot move SKILL-19 to 'Archived': ...`, so the gate states the target status twice. ADR-697 rules that gate and reporter render identical condition text and that an awkward shared text is fixed in the shared text, never forked per caller.
- `_services/_validators.py` (rule `agent_registered`) and `_services/_base.py` (create-time author/assignee checks) say `is not a registered agent or operator`, while the registered set also holds skills.
- `_cli/_workflow_cmd.py`: the human types table prints `str(row["order"])`, so a whole order shows as `10.0`.
- `_cli/_common.py` `print_block` (the `add-<kind> --json` write surface) keys the item file as `file`; every read surface keys it as `path`. The write surface is outside the frozen `--json` list in `docs/stability.md`.
- `_cli/_items.py` `_cmd_status` and `_cli/_common.py` `register_status_verb` take no `--as`, so every status transition, an `--unlink` severance included, reflogs `actor=system`; so do `update`, `body`, `ref`, `retype`, `remove` and the sub-entity verbs. ADR-117 §3 (amended 2026-10-25) rules an optional `--as`, validated like a comment's.
- `src/squads/_specs/workflow.toml` `[lifecycles.finding.transitions]` gives `Noted` no outgoing edge, so routing a noted finding to its carrier takes `--force` (op-pierre ruling on this task).
- `docs/stability.md` "Reflog on-disk format" calls the `v` coupling open (op-pierre ruled it kept, on ADR-117), its op table omits the `subentity` `delta.op` actions, and its `migrate` row omits `sq migrate repad`.

## Ordering

ST3 changes message text in `_config_integrity.py`, which TASK-717 also edits under a byte-unchanged message guarantee. Run ST3 after TASK-717 is Done. ST6 and ST7 both edit `_cli/_common.py`, and ST8 and ST9 both edit `docs/workflow.md`: run each pair one after the other, not concurrently. The other subtasks have no ordering.

## Tests

Each subtask adds or changes the assertion named in it, and the new assertion fails against today's code (falsify it before the fix). Goldens and pinned strings that change are refreshed in the same subtask and named in the handoff comment. Every user-visible change gets a CHANGELOG entry in the unreleased section.

## Gates

`uv run --all-extras pyright`, `ruff check .`, `ruff format --check .`, `pytest tests/meta tests/cli tests/integration -n 4`; `~/.local/bin/sq check` clean. No ticket ids in source, tests or docs.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1146 add-subtask "<title>"`; track with `sq task 1146 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Collect every per-entry shape error in workflow lint

<!-- sq:subtask:ST1:body -->
Owner: python-dev. Carries REV-724 F8.

`sq workflow lint` on an override with two malformed `[items.*]` entries (for example an unknown key `bogus = 1` on `alpha` and `alsobogus = 2` on `beta`) lists both, one finding per bad field, each as a written sentence naming the entry and the key. No pydantic text (`validation error for`, `errors.pydantic.dev`) reaches the output, and a shape error carries a shape-specific hint instead of the referential-integrity one ("Fix the referenced key ... or add it back").

Where: the `_build_spec` phase of lint in `_workflow/_loader.py` and `_split_spec_errors`. Translate a per-entry `ValidationError` into per-field findings and keep parsing the remaining entries; the load path (not lint) may still refuse on the first error.

Test: a table in the lint tests with two and three malformed entries across `items` and `subentity_kinds`, asserting the count, that each entry is named, the absence of pydantic text, and the hint. The `[selected]` collect-all rows from BUG-1084 stay as they are.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Name broken overrides in a bare override diff

<!-- sq:subtask:ST2:body -->
Owner: python-dev. Carries REV-97 F4.

A bare `sq override diff` on a squad whose only override is broken (a readable template override missing a required `sq:*` region, `STATE_BROKEN` with no `cause`) no longer prints `no drifted overrides found` as if all were well. It names each broken override and points at `sq override list` for the detail. Decide in the subtask whether a broken-but-readable override also exits 1, matching the unreadable case `_fail_on_unreadable` already handles, and state the choice in the handoff.

Where: `diff` in `_cli/_override.py`, the no-name branch.

Test: CLI tests for a squad with only a broken template override, with a broken and a drifted one, and with none, asserting stdout and exit code in each.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Stop the roster gate refusal stating the status twice

<!-- sq:subtask:ST3:body -->
Owner: python-dev. Carries REV-706 F13 part I3. Run after TASK-717.

A retirement refusal on a skill no longer states the target status twice. Change the shared `preloaded_skill` condition text in `_services/_config_integrity.py` (all three kinds: `scoped_edge`, `type_implied`, `always_on_floor`) so it does not restate the status the gate header already names, for example `not live but still scoped to live role(s): manager`. The gate and the `sq check` reporter keep rendering the same text, per ADR-697: no per-caller fork.

Test: the gate refusal and the reporter output for the same squad state carry the same condition text, and the refusal mentions the status once. Update the pinned strings in the predicate unit tests, the retirement service tests and the transcript in `docs/roles.md`, and name each in the handoff.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Name skills in the unregistered author and assignee messages

<!-- sq:subtask:ST4:body -->
Owner: python-dev. Carries REV-191 F2.

The unregistered author/assignee messages name what a registered participant can be: a role, a skill or an operator (the set the check uses). Where: the `agent_registered` rule in `_services/_validators.py` and the author/assignee checks in `_services/_base.py`. One wording for both, so check and create agree.

Test: assert the new text in the check and create paths; refresh the check golden if it carries the message.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Print whole type orders as integers in the types table

<!-- sq:subtask:ST5:body -->
Owner: python-dev. Carries REV-466 F1.

The human `sq workflow types` table prints a whole order as an integer (`10`, not `10.0`) and a fractional one as is (`25.5`). The `--json` value stays a float. Where: the row rendering in `_cli/_workflow_cmd.py`.

Test: a CLI test with a whole and a fractional order in an override, asserting both cells, plus a check that the `--json` golden is unchanged.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Key the add-<kind> --json item file as path

<!-- sq:subtask:ST6:body -->
Owner: python-dev. Carries REV-94 F1.

`add-<kind> --json` (story, subtask, finding and any custom kind) keys the item file as `path`, the key every read surface uses, instead of `file`. Where: `print_block` in `_cli/_common.py` and its module docstring, which records the asymmetry. Check the VS Code client and the docs for a reader of `file` before renaming, and say what you found.

Test: the add-* `--json` tests assert `path` and the absence of `file`; CHANGELOG notes the rename under the unreleased section as a change for JSON consumers.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Take an optional --as on every item-mutating verb

<!-- sq:subtask:ST7:body -->
Owner: python-dev. Carries REV-706 F13 part I5, under the ADR-117 §3 ruling (amended 2026-10-25).

Every verb that mutates one addressed item, sub-entity or roster entry takes an optional `--as SLUG`, and the reflog line it writes records that slug as `actor`. Without `--as` the line still records `system`, so no scripted call changes. The flag is validated exactly like a comment's: `resolve_actor_or_raise` in `_cli/_common.py` (an unknown or retired slug is refused naming the valid ones, and `system` itself is refused), then `actor.set_actor(slug)` before the service call. A refused `--as` writes nothing.

Verbs in scope:

- `status`: the work-item verb (`_cmd_status` in `_cli/_items.py`) and the roster verb (`register_status_verb` in `_cli/_common.py`), including `--unlink`. Every line one `--unlink` run writes, the severed `ref` lines and the `status` line, carries the actor.
- `update`, `body`, `ref add` / `ref rm`, `retype` and `remove` on a work item.
- A sub-entity's `add-<kind>`, `update` (its `--status` is a status transition), `body` and `remove`.
- The roster `update`, `body` and `remove` verbs, and `sq skill <addr> link-role` / `unlink-role`, `sq role <addr> set-default`.

Enumerate the mutating verbs from the CLI before starting, and name any you leave out in the handoff with the reason. Corpus-wide maintenance (`repair`, `renumber`, `migrate`, `sync`) stays `system`: no one participant acts there.

Why one subtask and not a status-only one plus a follow-up: the remedy is one shared option-and-resolve helper applied to each callback, so the extra verbs are more call sites of the same change, with one owner and one release. A status-only cut would split the sub-entity `update` verb (its `--status` is in scope, its other fields would not be) and leave `sq reflog --actor` meaning different things depending on which verb ran.

Where: one helper beside `as_option` in `_cli/_common.py` that resolves an optional `--as` and sets the actor, called from each verb above in `_cli/_items.py`, `_cli/_common.py`, `_cli/_skill.py`, `_cli/_role.py` and `_cli/_operator.py`. No service signature changes: the actor is ambient (ADR-117 §3, ADR-534).

Test: one CLI table over every verb in scope, asserting the reflog line's `actor` is the `--as` slug when given and `system` when not; an unknown slug and `system` are refused with exit 1 and no reflog line; an `--unlink` retirement with `--as` attributes every line it wrote. Falsify against today's code first (the `--as` rows fail as an unknown option).

Docs and CHANGELOG: the unreleased section notes the new flag; the reflog `actor` row in `docs/workflow.md` and the `--unlink` lines in `docs/roles.md` say `--as` attributes the edit.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — Let a noted finding move to Deferred without --force

<!-- sq:subtask:ST8:body -->
Owner: python-dev. Ruled by op-pierre on this task (2026-10-25).

The bundled finding lifecycle gains `Noted -> Deferred`, so a finding first closed as noted can be routed to the item that carries its work without `--force`. Every other rule of the move stays: `--deferred-to <ID>` is required and `--force` does not waive it, and `sq check`'s `subentity_deferral_resolved` judges the pointer as for any deferred finding. `Deferred` keeps no outgoing edge.

Where: `[lifecycles.finding.transitions]` in `src/squads/_specs/workflow.toml` gains `Noted = ["Deferred"]`. Its comment says Noted and Deferred have no table key so that an override redeclaring `Open` keeps its own machine; with a `Noted` key that no longer holds by construction, so check how the merge treats an override whose `Open` list omits `Noted`, make that override still load and lint clean, and correct the comment to say what is true.

Test: a service test that moves a finding `Open -> Noted -> Deferred --deferred-to <ID>` with no `--force`, and that the same move without `--deferred-to` is still refused; a CLI smoke of the same; a loader/lint test for an override that redeclares `Open` without `Noted`. Refresh any golden or rendered skill that prints the finding lifecycle (`sq workflow` output, the `sq-review` skill, the template manifest) and name each in the handoff.

Docs and CHANGELOG: the unreleased section notes the new transition. In `docs/workflow.md`, "Closing a finding as Noted or Deferred": add `Noted -> { Deferred }` to the transition block, and replace "Neither has an outgoing edge, so reopening one takes `--force`" with the true rule (a noted finding can still be deferred; reopening either takes `--force`). The override snippet in that section gains the `Noted` key if adopting the move needs it.
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->

<!-- sq:subtask:ST9 -->
### ST9 — Redefine reflog v and complete the op table in stability.md

<!-- sq:subtask:ST9:body -->
Owner: tech-writer. Ruled by op-pierre on ADR-117 (2026-10-25): `v` stays coupled to the schema version, and no new constant is added. The op-table corrections are from the architect's comment there.

Where: "Reflog on-disk format" in `docs/stability.md`.

What:

- Redefine `v` as the schema version of the squad that wrote the line. Drop "currently coupled" and "whether to decouple is open": both are settled.
- The closing paragraph says "readers key off `v`". As defined, `v` names the writing squad's schema, not the line format, which changes only by field addition. Say that instead: forward-compatible by field addition, readers ignore unknown fields.
- The op table: the `subentity` row names its `delta.op` actions (`add`, `status`, `assignee`, `update`, `body`, `remove`), and states that `delta` is namespaced by `op`; the `migrate` row covers `sq migrate up` and the `sq migrate repad` padding rewrite (`delta.op` = `repad`).
- Align the `v` row of the field table in `docs/workflow.md` with the new definition, and check its op table still agrees with the one in `docs/stability.md`.

Test: read each changed table against the writers it describes (`_index/_reflog.py` for `v`, `_services/_subentities.py` for the sub-entity actions, `_services/_maintenance.py` for `repad`) and quote one real line of each shape from this repo's `.reflog.jsonl` in the handoff. No CHANGELOG line: the line format does not change.
<!-- sq:subtask:ST9:body:end -->

#### Discussion

<!-- sq:subtask:ST9:discussion -->
<!-- sq:subtask:ST9:discussion:end -->
<!-- sq:subtask:ST9:end -->

<!-- sq:subtask:ST10 -->
### ST10 — State the type_implied mechanism without advising a type drop

<!-- sq:subtask:ST10:body -->
Owner: python-dev. Run after ST3, which edits the same `preloaded_skill` texts. Carries the code/ADR mismatch the architect raised on ADR-697 (2026-10-25 audit).

**The ADR is right; the code is fixed.** ADR-697 §8 rules that a `type_implied` refusal "states the mechanism, not a recommendation": `sq-task` is implied by declared type `task` is a fact, while "drop `task` to retire this skill" is advice that is usually wrong, because a live work type with items under it is not something to drop so that one skill can retire. The condition text already states the mechanism (`implied by declared type(s): …`). The two remedy texts in `_services/_config_integrity.py` push the drop:

- `remedy`: "make the skill live again, or drop the implicating type via `[selected]` in .overrides/workflow.toml"
- `removal_remedy`: "drop the type via `[selected]` in .overrides/workflow.toml first"

Reword both to the mechanism: the skill stays implied for as long as the named type(s) are declared, and the retirement succeeds once no declared type implies it; `remedy` keeps "make the skill live again" as its actionable step. Neither names `[selected]` or tells the operator to drop a type. Remove the code comment above `remedy` that defends naming the drop. Gate and reporter keep one shared text (ADR-697).

**Tests.** Update the pinned strings in `tests/unit/test_roster_config_integrity_predicates.py` and `tests/service/test_retirement_refuses_a_config_breaking_transition.py`, and grep the old wording across `tests/` and `docs/`. One table over the three surfaces (retirement refusal, `sq check` reporter, removal refusal) for a squad where a declared type implies the skill: each states the implicating type, and none contains `[selected]` or "drop".
<!-- sq:subtask:ST10:body:end -->

#### Discussion

<!-- sq:subtask:ST10:discussion -->
<!-- sq:subtask:ST10:discussion:end -->
<!-- sq:subtask:ST10:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T20:10:57Z] `op-pierre` Pierre Chat:
  - Add a Noted -> Deferred transition to the bundled finding lifecycle, so routing a noted finding to a carrier needs no --force.
- [2026-10-25T20:14:48Z, edited 2026-10-25T20:15:08Z] `tech-lead` Olivia Lead:
  - Added ST7 (`--as` on mutating verbs, REV-706 F13 I5), ST8 (Noted -> Deferred, op-pierre ruling above) and ST9 (reflog `v` and op table, tech-writer). Retitled to cover the attribution and lifecycle work.
    ST7 takes all the verbs Robert listed, not status only: one shared resolve-and-set helper, and a status-only cut would split the sub-entity `update` verb. The reasoning is in ST7's body.
- [2026-10-25T22:06:41Z] `tech-lead` Olivia Lead:
  - Added ST10 from the ADR-697 audit note: the type_implied remedy texts advise dropping the type via [selected], which ADR-697 section 8 rules out. The ADR is right; the code changes. Runs after ST3.
<!-- sq:discussion:end -->
