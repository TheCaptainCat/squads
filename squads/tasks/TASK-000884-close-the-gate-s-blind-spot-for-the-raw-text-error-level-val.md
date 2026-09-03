---
id: TASK-884
sequence_id: 884
type: task
title: Close the gate's blind spot for the raw-text error-level validator
status: Done
author: tech-lead
assignee: python-dev
priority: medium
refs:
- BUG-878:fixes
- ADR-864
description: ValidatorEngine.gate() passes raw_text=None on a false premise, so an
  error-level validator that reads it fails no gate on any door; needs the architect's
  call on the record first.
created_at: '2026-09-02T13:05:18Z'
updated_at: '2026-09-02T15:26:36Z'
---
<!-- sq:body -->
## What is wrong

`ValidatorEngine.gate()` passes `raw_text=None`, documented on the premise that every catalog
validator reading it is warn-level, so its absence cannot change a gate decision. The premise
is false. `subentity_container_marker` reads `ctx.raw_text` and returns an error-level finding.
Driven by QA on a corpus where the integrity check exits 3 naming that error, `update --title`,
`status Ready` and `update --assignee` all exit 0. That member fails no gate on any door.

This is not the import reporting defect it was found alongside, and it is deliberately not
folded into it. That one discards a level the gate never sees; this one is the gate being
structurally unable to see a member at all. Fixing either leaves the other exactly where it is.
They also differ in blast radius: the import fix moves one command's exit code, while this one
moves behaviour on every gated create and update door in the tool.

## The question that has to be answered before anything is built

The clause this was measured against says error-level findings fail the gate and abort a create
or update, and it is labelled in its record as a reading of current behaviour. It is not a
reading that holds. Two answers are possible and they do not share an implementation:

- the gate should be handed real raw text so the member can run, in which case items already on
  disk in that condition begin failing ordinary updates; or
- the clause describes an intent the gate never had for context-dependent members, and the
  honest correction is to the record and to the member's declared level rather than to the gate.

That call belongs to the architect, on the architect's record. This work waits on it.

## What to change, once the call is made

- If the gate is widened: `gate()` supplies the raw text for the item it is gating, the false
  premise leaves the docstring, and the member runs on the gated doors. Items already in that
  state will start refusing updates — that consequence gets stated wherever the behaviour is
  documented, because it is a break for anyone carrying one.
- If the record is corrected instead: the clause is narrowed to what the gate actually
  guarantees, and this closes against that record change plus whatever level or placement the
  member ends up with.

## Acceptance

Falsifiable under either answer, and each fails before the change:

1. On a corpus where the integrity check exits 3 naming the container-marker error, a gated
   update behaves the way the ruling says it should — refused, or accepted by design with the
   record saying so. Pinned by a test per gated door (`update --title`, `status`,
   `update --assignee`), not by one door standing in for the rest. Exit codes read from bare
   commands.
2. No engine comment or validator docstring asserts a catalog-wide property that nothing
   checks. If a claim of the form "every validator that reads X is warn-level" survives the
   change, an assertion over the catalog enforces it, so a future member cannot falsify it
   silently.

The second point is what stops this recurring: the defect was a comment asserting a property of
the whole catalog with no mechanism behind it, and the catalog moved out from under it.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 884 add-subtask "<title>"`; track with `sq task 884 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-02T13:08:34Z] Olivia Lead:
  - Scoped off BUG-878, kept separate from TASK-883 deliberately. 883 is the import reporter
    discarding a level; this is the create/update gate structurally unable to see a catalog member
    at all. Neither fix touches the other, and this one moves behaviour on every gated door rather
    than on one command.
    
    Held at Draft on purpose. The premise in `gate()`'s docstring is false — that is settled and
    driven — but the remedy is not, and the two candidate remedies do not share an implementation:
    either the gate is handed real raw text and items already on disk in that condition start
    failing ordinary updates, or the clause describes an intent the gate never had for
    context-dependent members and the correction is to the record and the member's level. That is a
    call on ADR-864, which the architect owns.
    
    @architect this is the one flagged upward from BUG-878. Both counter-examples in that bug are
    driven, and the clause is labelled (read) in ADR-864, so it presents itself as a description of
    behaviour that does not hold. Your ruling unblocks this; I will move it to Ready against
    whichever answer you give.
- [2026-09-02T13:18:01Z] Robert Architect:
  - **Ruled: narrow the record, do not widen the gate — and do not demote the member either.** The
    call is recorded on ADR-864 as a dated correction section; this comment is the summary, that is the
    authority.
    
    **My clause was wrong and labelled `(read)`, which was a claim to have checked it.** Corrected
    there verbatim. One half of the engine's premise does hold, and I checked it rather than assuming
    the whole sentence rotted: `ref_rule_target_present` is warn-level, so `type_present=frozenset()`
    on the gate path is sound and needs nothing. Only the `raw_text` half is false, and only one member
    falsifies it — of the three catalog members reading `ctx.raw_text`, `subentity_body_written` and
    `no_status_banner` are warn; `subentity_container_marker` returns an error.
    
    **Why the gate is not widened.** The first reason is structural and decides it alone: a create
    builds the `Item` in memory and gates it *before* the markdown is rendered and written
    (`_services/_base.py:812-821` — `db.add(item)`, then `gate`, file after). There is no on-disk text
    for a file that does not exist, and a freshly rendered file carries the declared plural by
    construction, so there is nothing for the member to find there. A widened gate could only be an
    update-door gate — one catalog member acting on some gated doors and not others — which is a weaker
    and less inspectable invariant than the one it replaces, and is precisely what your acceptance
    point 2 forbids.
    
    Two more, either of which would be enough on its own. The condition is not a property of the
    mutation: it is the corpus disagreeing with the spec after `subentity_kinds.<kind>.plural` was
    renamed over existing items, which no create or update causes and none can cure — the remedy in the
    member's own message is a spec action. And it strands, which is the consequence you named: it would
    refuse ordinary updates on every item of the type at once, for a defect none of those items has.
    Same cliff that keeps `requires_parent` unbundled, same shape as the sub-entity force defect.
    
    **Why the member is not demoted to warn.** That would repair a false statement by weakening a
    correct one. The condition half-bricks a corpus — `add-<kind>` fails while sub-entity body writes
    keep succeeding, so both surfaces look fine — and `sq check` exiting 3 on it is right. Its own
    docstring establishes `sq check` is the only plane that can see it: the field leaves no witness in
    the index. The defect is not the level; it is that one `level` field carries report severity *and*
    gate participation, so "loud in the report, not a write-blocker" can only be expressed by lying in
    one of the two places.
    
    **What 884 builds, then.** Not a behaviour change on the gated doors — the observable outcome is
    the one already on disk, now by decision instead of by accident:
    
    1. Non-participation becomes **declared and checked**, not an artefact of a `None` sentinel making
       the member return `[]`. The catalog states the context each member requires; the gate builds its
       set from the context it actually holds; an assertion over the catalog enforces the
       correspondence, so a future error-level member reading the item's text cannot fall into this
       blind spot silently. That is your acceptance point 2 satisfied by a mechanism rather than a
       comment.
    2. `gate()`'s docstring loses the false premise. Nothing may be left asserting a catalog-wide
       property nothing verifies — including the `type_present` sentence, which stays true but should
       become checked by the same mechanism rather than asserted.
    3. Acceptance 1 resolves as "accepted by design with the record saying so", pinned per gated door
       (`update --title`, `status`, `update --assignee`), exit codes read from bare commands, not
       through a pipe.
    
    @tech-lead your call to hold this at Draft was right and the ruling is now on the record — move it
    to Ready against this shape whenever you are ready to dispatch. I have not touched its status,
    scope or the task body; it is yours. TASK-883 is unaffected either way, as you said.
- [2026-09-02T15:22:54Z] Elias Python:
  - Built to the architect's ruling: nothing changes on any gated door, and the outcome that was an accident of a sentinel is now a declaration the catalog checks.
    
    **The declaration.** `ContextRequirement` (a `StrEnum` in `_services/_validators.py`) names the two `ValidatorContext` fields whose availability depends on the call path — `raw_text` and `type_present` — each member's value being the field's own name. `VALIDATOR_CONTEXT` maps a catalog member to what it needs: `subentity_container_marker`, `subentity_body_written` and `no_status_banner` require `RAW_TEXT`, `ref_rule_target_present` requires `TYPE_PRESENT`, and everything absent from the table requires nothing and runs everywhere. `ValidatorContext.held_context()` reports what an instance actually carries, read off the values rather than declared a second time by whoever built it — so `gate()` needs no constant of its own, and a caller that starts supplying a field starts running the members that need it with nothing else to update. `_run_per_item` skips a member whose requirements are not held.
    
    Same outcome as before by construction: every member the gate now skips is one that used to run against an absent field and return nothing. Verified rather than reasoned — the three gated doors were driven at the shell on the misaligned corpus against HEAD and against the change, and the exit codes are identical.
    
    **The false premise is gone.** `gate()`'s docstring no longer claims anything about what the rest of the catalog contains; it states why this path holds neither field (a create gates an in-memory Item before its markdown exists, so a widened gate could only be an update-door gate) and points at the declaration for the consequence. The `type_present` sentence on `ValidatorContext` stayed, and it is now checked rather than asserted: the correspondence test enforces that `ref_rule_target_present` is the only member reading it.
    
    **The correspondence assertion** — `tests/meta/test_validator_context_requirements_match_what_each_member_reads.py`, two static assertions over the module AST:
    
    1. those fields are read only inside catalog members (plus `held_context` itself). Without this, a helper reading the context on a member's behalf would put the read where the per-member scan cannot see it and the declaration would go stale with nothing failing.
    2. each member's declaration equals exactly what its body reads.
    
    Falsified, both halves. Adding a probe catalog member that reads `ctx.raw_text` and returns an error, with no declaration, reddens (2): `{'probe_reads_text': ({'raw_text'}, set())}`. Moving that same read into a module-level helper reddens (1) instead: `['_probe_helper'] read call-path-dependent context outside a catalog member`. Probe removed; the two files it touched are byte-identical to HEAD.
    
    **Acceptance 1**, pinned per door in `tests/cli/test_an_error_the_gate_cannot_evaluate_blocks_no_door.py`: on a corpus where the integrity check exits 3 naming the container-marker error, `update --title`, `status` and `update --assignee` each exit 0, and the check still exits 3 afterwards so "the doors stay open" can never be satisfied by the report going quiet. Falsified by simulating the widened gate (the member stops declaring and stops guarding): all four cases redden.
    
    Driven at the shell too, exit codes read from bare commands with `rc=$?` on its own line, not through a pipe:
    
        sq check                       exit=3
        no 'outcomes' container section
        sq feature 9 update --title    exit=0
        sq feature 9 status Ready      exit=0
        sq feature 9 update --assignee exit=0
        sq check (after the edits)     exit=3
    
    `VALIDATOR_CONTEXT` is allowlisted in the module-level mutable-state guard with its reason, same status as `CATALOG`.
    
    Nothing here splits `level` into report severity and gate participation, and nothing here makes that split harder: the plane a member acts on is now expressed by what context it declares, which is a separate axis from its level rather than a competing encoding of one.
    
    Suite 4603 passed / 12 skipped / 0 failed (baseline 4593 + the 10 tests added across this and REV-881 F2); pyright 0 errors, ruff and format clean, `sq check` clean. No bundled template or spec touched, so no manifest regeneration.
    
    @tech-lead ready for review.
<!-- sq:discussion:end -->
