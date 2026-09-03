---
id: TASK-875
sequence_id: 875
type: task
title: Make sub-entity --force override the transition, not the vocabulary
status: Done
author: tech-lead
assignee: python-dev
priority: medium
refs:
- BUG-873:fixes
description: A sub-entity status update under --force writes a value outside that
  kind's lifecycle at exit 0 and the integrity gate then errors; add the membership
  check the add path already performs.
subentities:
- local_id: ST1
  title: Membership check on the sub-entity status path
  status: Done
- local_id: ST2
  title: Recovery from an already-invalid stored status
  status: Done
- local_id: ST3
  title: Close the same write on the import route
  status: Done
created_at: '2026-09-02T09:58:51Z'
updated_at: '2026-09-02T14:01:30Z'
---
<!-- sq:body -->
## What is wrong

`sq <type> <n> <kind> <k> update --status <S> --force` accepts any status in the squad's
global status set, including one that is not a member of that sub-entity kind's own
lifecycle. The write succeeds at exit 0. `sq check` then reports the corpus it just
produced as an **error** and exits 3. Three commands from a fresh init reach it, and all
three bundled kinds behave the same way.

A supported, documented verb produces a corpus the integrity gate rejects.

## The rule to implement

`--force` overrides an illegal **transition**. It never overrides the **vocabulary**.

That is already what it means at item level, because `update` runs the validator engine
after applying the delta: an illegal edge with a valid status passes under `--force`, a
status outside the type's declared set is refused even under `--force`. It is also
already what the documentation says for both layers — `docs/workflow.md` gives `--force`
the transition meaning for items and for sub-entities, and states the vocabulary meaning
for neither.

The sub-entity `add` path already performs the membership check the `update` path skips
(`add-subtask --status Verified` correctly exits 1). Two doors onto the same kind
disagree about the same value. That asymmetry is the defect.

## The constraint any fix must clear

Do not reach for an unconditional gate on the sub-entity status door. It is wrong, and
it is wrong in a way that is worse than the bug.

`<kind> <k> update --status … --force` is the **only** way out of the state this defect
creates. While an invalid sub-entity status stands, every gated door on the parent item
refuses and quotes the sub-entity's problem — the parent cannot be transitioned or
edited at all. Gating the one remaining door against the parent's full validator set
would make an already-corrupt corpus unrecoverable through the CLI: a bricking
regression, strictly worse than a red gate.

So the fix is narrow by construction: a **membership** check on the target status
against that kind's own declared lifecycle, at the same point and with the same message
shape the `add` path already uses. Not a general gate, and not the parent's whole
validator set.

## Recovery from a corpus that is already wrong

This is the half most likely to be got wrong, and it is why the fix needs to be driven
against a pre-corrupted squad and not only against a clean one.

After the fix, recovering a subtask whose stored status is `Verified` means running
`update --status Todo --force`. The **target** (`Todo`) is a member, so the new
membership check passes. But the **current** stored value (`Verified`) is not on the
machine at all, and the transition lookup has to read it. Whatever the transition layer
does with an origin state that is not a node — raise, return no edges, or fall through —
determines whether recovery still works. Establish that empirically; do not assume it.

## Scope decisions, so they are not re-litigated

**In scope — the import route's write.** `sq import` reaches this same core through a
`sub-status` event carrying `"force": true`. Fixing the core closes that write too, but
"closes it for free" is a claim, not a result: prove it at the import door as well as at
the CLI door.

**Out of scope — the importer's severity flattening.** `sq import` runs the validator
engine through `report()` rather than the gate, flattens error-level and warn-level
findings into one list, prints an error-level finding as `warning:`, and exits 0 keeping
the write. That is a genuinely separate defect: it is in the importer's result handling
rather than in the sub-entity write path, it applies to **every** error-level validator
and not just this one, and correcting it changes `sq import`'s exit-code contract for
adopters, which is an operator call and not a rider on a fix task. It is being raised as
its own item. Do not change `sq import`'s exit code or its report handling here.

**Out of scope — consolidating the duplicated story-mapping rule.** `_services/_subentities.py`
has no validator-engine call anywhere, and re-implements the story-mapping rule as
bespoke per-door guards. One rule, two independent implementations, which is a real
fragility. It is also, driven, not a reachable hole: every door that could break the
mapping refuses today. Consolidating it means deciding *which* validators run on *which*
sub-entity door, and the constraint above proves that answer is not "all of them on all
of them" — the `body` and `comment` doors have the same objection, since blocking the
discussion in which a recovery is coordinated makes a fail-closed design worse rather
than safer. That is a design question with a settled precedent to honour and a live
proposed catalog decision to fit into. It is not a rider on this fix. Leave the bespoke
guards exactly as they are.

## Acceptance

- A cross-kind status is refused at exit 1 with nothing written, **with and without**
  `--force`, on all three bundled kinds. Refusal names the offending value and lists the
  kind's own allowed statuses, matching the `add` path's message shape.
- An illegal **transition** between two statuses that *are* members still succeeds under
  `--force` at exit 0. This is the behaviour the fix must not take away, and it is the
  regression most likely to be introduced; assert it per kind.
- Without `--force`, an illegal transition between valid members still fails at exit 1
  with the existing message. Unchanged.
- Recovery from a pre-existing corrupt value is driven end to end: construct the corrupt
  state (write it however you must, since the CLI door is about to close), then
  `update --status <valid> --force`, then `sq check` exit 0, then a gated door on the
  parent exits 0. If recovery does not survive the fix, that is a blocking finding —
  stop and report it rather than shipping a bricking change.
- The import route is driven: a `sub-status` event with `"force": true` and a cross-kind
  status no longer writes it.
- `sq check` exits 0 on every corpus produced by these commands.
- Exit codes read from bare invocations, never through a pipe.
- **The tests fail before the fix.** Break the fix, watch each new test go red, restore
  it, watch it go green, and report both in the handoff comment. A test written to
  confirm a change rather than to disprove it has shipped three defects this release.
- Cover the shape families, not one instance per branch: kind x (member status /
  cross-kind status) x (with `--force` / without), table-driven, plus the two
  pipeline-level invariants — every write this path accepts leaves `sq check` clean, and
  every corpus this path can reach is recoverable through it.
- Name tests by behaviour. No ticket identifier in a test name, a file name, or a source
  comment.
- `uv run --all-extras pytest`, `ruff check .`, `ruff format --check .`, `pyright` and
  `sq check` all clean. `--all-extras` on each.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 875 add-subtask "<title>"`; track with `sq task 875 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Membership check on the sub-entity status path

<!-- sq:subtask:ST1:body -->
The core fix. On the sub-entity status update path, check the target status for
membership in that kind's own declared lifecycle before applying, and refuse a
non-member regardless of `--force`.

Mirror the `add` path, which already performs this check and already produces the right
message shape — it names the offending value and lists the kind's allowed statuses. Two
doors onto the same kind should not word the same refusal two ways.

`--force` keeps its existing effect on the transition: an illegal edge between two
statuses that are both members still succeeds under it. Do not touch that.

Resolve the allowed set from the kind's declared lifecycle in the active spec, not from a
literal list — a project can redeclare these, and a hardcoded set would be a second
source of truth for vocabulary the spec already owns.

Done when: a cross-kind status is refused at exit 1 with nothing written, with and
without `--force`, on all three bundled kinds; an illegal transition between members
still succeeds under `--force`; and without `--force` an illegal transition between
members still fails with the message it gives today.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-09-02T12:33:07Z] Elias Python:
  - Done. The membership check now lives in one helper, `_require_declared_status(kind, status)`, resolved from the active spec's `subentity_workflow(kind).states` — no literal list. Both doors call it: the seed path (`_resolve_add_status`, which previously carried the check inline) and the transition path (`_apply_subentity_status`, which is the single point `set_block_status`, `update_block` and the importer's `sub-status` all funnel through). The refusal is now byte-identical between the two doors, because it is literally the same raise; a test asserts the two messages are equal string-for-string.
    
    Placement matters and is deliberate: the membership check runs *before* `current = sub.status` is read, and the transition guard below it is untouched, so `--force` still waives the edge and nothing else.
    
    Driven at the CLI, one scratch squad per kind, exit codes from bare invocations:
    - `task 9 subtask 1 update --status Verified` and the same with `--force`: both exit 1, `'Verified' is not a valid subtask status (one of: Blocked, Cancelled, Done, InProgress, Todo)`, stored status unchanged.
    - `feature 10 story 1 update --status Fixed --force`: exit 1. `review 11 finding 1 update --status Done --force`: exit 1.
    - Illegal edge under force still lands: subtask Todo->Done exit 0, story Todo->Done exit 0, finding Open->Verified exit 0.
    - Without force, Todo->Done still exits 1 with `cannot move Todo -> Done (use --force to override)`, unchanged.
    - `sq check` exit 0 on every corpus these produced.
    
    Test: `tests/service/test_subentity_status_force_overrides_the_edge_not_the_vocabulary.py`, table-driven over kind x (member / cross-kind) x (with force / without), plus the metadata door (`update_block`) proven to refuse the same value and to land none of the other fields it was carrying, plus the pipeline invariant that walking the kind's whole declared vocabulary through the forced door leaves zero error-level check issues. CLI spine in `tests/cli/test_subentity_status_force_is_gated_on_the_kinds_vocabulary_cli.py`.
    
    Falsified: deleting the one added line takes 17 of the 35 new tests red across all three files; the 18 that stay green are exactly the ones pinning behaviour that must not change (edge waiver, no-force refusal, recovery). Restored, all 35 green.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Recovery from an already-invalid stored status

<!-- sq:subtask:ST2:body -->
The regression risk, isolated so it is driven rather than assumed.

Recovering a sub-entity whose stored status is already outside its machine means running
`update --status <valid member> --force`. The target is a member, so the new membership
check passes. But the stored current value is not a node on the machine, and the
transition lookup has to read it. What that layer does with an origin state it does not
know — raise, return no edges, or fall through — decides whether recovery still works
after the fix.

Establish it empirically against a squad that is already in the bad state. Construct that
state directly, since the CLI door that used to produce it is being closed by ST1.

This matters because that door is the only way out: while an invalid sub-entity status
stands, every gated door on the parent item refuses and quotes the sub-entity's problem,
so the parent cannot be transitioned or edited at all.

If recovery does not survive the fix, stop and report it. A change that closes the last
exit from a corrupt corpus is worse than the defect it fixes, and this subtask is where
that gets caught.

Done when: the full recovery sequence is driven end to end on a pre-corrupted squad —
force the value back to a valid member, integrity gate clean, a gated door on the parent
succeeds — and a test pins it so a later change cannot quietly take it away.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-09-02T12:33:32Z] Elias Python:
  - Recovery survives. Driven, not assumed, on a squad already in the bad state.
    
    What the transition layer does with an unknown origin, read first and then confirmed at the CLI: `Lifecycle.can_transition` is `dst in self.transitions.get(src, [])`, so an origin that is not a node returns False rather than raising — it would refuse, not crash. But it is never consulted on the recovery path at all: the guard is `not force and current != status and not can_transition(...)`, and Python short-circuits on the first term, so `--force` skips the lookup before the unknown origin is ever read. That is why ordering the new membership check on the *target* ahead of `current = sub.status` keeps the door open.
    
    Constructing the state: the CLI door that used to produce it is now closed, so the corrupt value was written straight into frontmatter (`subentities[0].status = Verified`) with no service seam involved, then `sq repair` — which is also the shape an adopted or hand-edited corpus arrives in.
    
    Driven sequence, exit codes from bare invocations:
    - `sq repair` exit 0; `sq check` exit 3, `error TASK-9: subtask ST1 has invalid status 'Verified'`.
    - `sq task 9 update --title Stranded` exit 1, `subtask ST1 has invalid status 'Verified'` — the parent is stranded, as described.
    - `sq task 9 subtask 1 update --status Todo` exit 1 (no force, still refused on the edge).
    - `sq task 9 subtask 1 update --status Todo --force` exit 0.
    - `sq check` exit 0. `sq task 9 update --title Recovered` exit 0 — the parent's gated doors open again.
    
    Pinned per kind by `test_a_stored_status_outside_the_machine_is_still_recoverable_through_this_door`, which drives that whole sequence including the stranding assertion.
    
    Falsified against the specific bricking regression rather than only against the absent fix: making the check read the stored value too (`current = self._require_declared_status(kind, sub.status)`) takes exactly those three tests red with `'Done' is not a valid finding status`, i.e. the corpus is unrecoverable. Restored, green. A later change that quietly widens this gate to the origin state cannot pass.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Close the same write on the import route

<!-- sq:subtask:ST3:body -->
The bulk-import surface reaches the same core through a sub-status event carrying a force
flag, and that is the only import route in — an add-sub event carrying a cross-kind
status is already refused in the pre-pass with nothing written.

Fixing the core should close this write too. That is a reasonable expectation and not a
result: drive it at the import door as well as at the CLI door, with an events file
carrying the force flag and a cross-kind status.

Strictly the write, not the reporting. The importer's habit of flattening error-level and
warn-level findings into one list, printing an error as a warning and exiting 0, is out of
scope for this task and is being raised separately — it is in the importer's result
handling, it affects every error-level validator rather than this one, and changing the
exit code is an adopter-facing contract change. Do not touch the exit code or the report
handling here.

Done when: the import route can no longer write a cross-kind sub-entity status, proven by
a test that runs the events file and asserts nothing was written; and the importer's exit
code and report formatting are unchanged by this task.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-09-02T12:33:34Z] Elias Python:
  - Closed at the import door, proven by running an events file rather than by arguing from the shared core.
    
    Driven, fresh scratch squad, the three-event file from the bug report (`create` / `add-sub` / `sub-status` with `"force": true` and `"status": "Verified"`):
    
    ```
    sq import events.jsonl        # exit=1
    #   line 3: 'Verified' is not a valid subtask status (one of: Blocked, Cancelled, Done, InProgress, Todo)
    #   1 issue(s) found - nothing written.
    sq check                      # exit=0
    sq list -a                    # zero items - the create in line 1 did not land either
    ```
    
    Where it lands matters: the importer validates the whole file against a shadow index before it writes, and its pre-pass calls `_set_block_status_model` -> `_apply_subentity_status`, so the refusal surfaces as a pre-pass issue at exit 1 with the file held back whole. It is not an applied write that the post-apply report then flattens into a `warning:`.
    
    The edge waiver still works through the same door: the identical file with `"status": "Done"` (an illegal Todo->Done edge, valid vocabulary) imports at exit 0 and `sq check` exits 0.
    
    Nothing was changed in the importer: no exit-code change, no touch to `report()` or the result handling. The separately-filed severity flattening is untouched and still reachable by its other route.
    
    Test: `tests/service/test_bulk_import_cannot_force_an_undeclared_subentity_status.py` - three cases: the forced cross-kind event is refused with the subtask still at Todo and zero error-level check issues; the forced illegal edge still applies; and one bad forced event holds back the whole file (a sibling `create` on line 1 does not land), so a refusal cannot leave a half-imported corpus. The first and third go red without the fix.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-02T10:02:46Z] Olivia Lead:
  - Scoped from BUG-873 and dispatchable. The rule is settled in the body — `--force`
    overrides the transition, never the vocabulary — so there is no design call left open for
    the implementer.
    
    Read ST2 before starting ST1. It is the reason this is three subtasks and not one: the
    door being narrowed is also the only way out of the state the defect creates, and whether
    recovery survives depends on what the transition layer does with a stored origin state
    that is not a node on the machine. Drive it, do not assume it, and stop and report rather
    than ship if it does not survive.
    
    Two things deliberately left out and recorded as such on the bug: the importer's
    severity flattening (a separate defect in the importer's result handling, with an
    adopter-facing exit-code contract change behind it) and the consolidation of the
    duplicated story-mapping guards (a design question with an open catalog decision it would
    have to fit). Do not widen into either.
    
    @python-dev ready for dispatch.
- [2026-09-02T12:34:22Z] Elias Python:
  - Implemented, all three subtasks Done, task to InReview. Not committed.
    
    **The fix**, one place: `src/squads/_services/_subentities.py`. The membership check that lived inline in `_resolve_add_status` is extracted as `_require_declared_status(kind, status)` and called from `_apply_subentity_status` as well — the single point every sub-entity status write funnels through (`set_block_status`, `update_block`, `set_subtask_done`, and the importer's `sub-status` via both `_set_block_status_model` and `_set_block_status_core`). The allowed set is resolved from the active spec's `subentity_workflow(kind).states`, never a literal. Both doors now raise the identical string, asserted as an equality in a test.
    
    The check runs before `current = sub.status` is read; the transition guard below is byte-for-byte untouched. So `--force` still waives the edge, and only the edge.
    
    **Recovery from an already-invalid stored status: it survives**, driven on a squad corrupted directly in frontmatter with no service seam. `update --status Todo --force` exits 0, `sq check` goes 3 -> 0, and the parent's gated doors open again. The mechanism, since ST2 asked for it empirically: `not force` short-circuits the whole transition condition before `can_transition` ever reads the unknown origin. (Had it been reached: `transitions.get(src, [])` returns False for an unknown src, so it would have refused rather than raised — a quiet bricking, not a crash.) Falsified against exactly that regression, not only against the absent fix — widening the check to the stored value takes the three recovery tests red.
    
    **Import route: closed, and driven.** The bug's own events file now exits 1 in the pre-pass with nothing written (not even line 1's `create`) and `sq check` exits 0; the same file with a legal-vocabulary illegal edge still imports at exit 0. The importer's exit code and report handling are untouched.
    
    **Tests**, 35 new, no ticket ids anywhere:
    - `tests/service/test_subentity_status_force_overrides_the_edge_not_the_vocabulary.py` (27) - table-driven kind x (member / cross-kind) x (with force / without), both doors, plus the two pipeline invariants.
    - `tests/service/test_bulk_import_cannot_force_an_undeclared_subentity_status.py` (3).
    - `tests/cli/test_subentity_status_force_is_gated_on_the_kinds_vocabulary_cli.py` (5).
    
    Falsification, both directions, reported as asked: deleting the added line -> 17 red / 18 green, the green ones being exactly the behaviours the fix must not take away. Widening it to the stored origin -> the 3 recovery tests red. Restored -> 35 green.
    
    **Gates**: `4539 passed, 8 skipped in 75.14s` (baseline 4504+8; +35 is exactly the new tests), 0 FAILED lines. pyright 0 errors, ruff check clean, ruff format clean, `sq check` exit 0.
    
    Nothing out of scope was touched: no change to the importer's severity flattening, none to `subtask_story_mapping`'s duplicate implementation, no spec/template/doc edit. `docs/workflow.md` already states the meaning the code now has, so it needed nothing.
    
    One correction to the brief, minor: it says the CLI-level cross-kind refusal was the `add` path's only precedent, which held, but it also said every other door on the parent "refuses ... quoting the sub-entity's problem" - true for the gated doors, and I confirmed the ungated sub-entity doors (`body`, `comment`, `--title`) still work on a corrupt parent, which is what makes coordinating a recovery possible. Left exactly as they are.
    
    @reviewer ready for review. @tech-lead for the board.
<!-- sq:discussion:end -->
