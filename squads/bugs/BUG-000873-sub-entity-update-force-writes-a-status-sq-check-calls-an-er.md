---
id: BUG-873
sequence_id: 873
type: bug
title: Sub-entity update --force writes a status sq check calls an error
status: Verified
author: qa
priority: medium
severity: medium
refs:
- BUG-865
description: sq <type> <n> <kind> <k> update --status <S> --force accepts a status
  outside that kind's lifecycle at exit 0; sq check then errors on the corpus. No
  sub-entity write door reaches ValidatorEngine.gate.
created_at: '2026-09-02T09:46:36Z'
updated_at: '2026-09-02T14:19:37Z'
---
<!-- sq:body -->
## Summary

`sq <type> <n> <kind> <k> update --status <S> --force` accepts any status in the
squad's global status set, including one that is not a member of that sub-entity
kind's own lifecycle. The write succeeds at exit 0 and prints `updated <ID> <k>`.
`sq check` then reports the corpus it just produced as an **error** and exits 3:
`subtask ST1 has invalid status 'Verified'`.

The general condition behind it: no sub-entity write door reaches
`ValidatorEngine.gate()`. Every one of them writes the parent item's frontmatter
through `_services/_subentities.py`, which relies on its own bespoke checks
instead. Those bespoke checks cover the `add` path and the story mapping, but the
`--force` branch of the status path has no membership check behind it, so that is
the one place where the missing gate is actually reachable.

## Environment

**Driven.** `squads 0.14.0` (repo working tree, branch `release/0.14`, HEAD
`8c5868a`), bundled workflow spec, no `.overrides/`. Six independent scratch
squads, each a fresh `sq init --default-names --backend none` in its own nested
temp directory. Every `sq` invocation was `uv run --project <repo> sq …` — the
globally installed `sq` is 0.12.1 and refuses a v0.14 squad outright.

## Minimal reproduction

**Driven.** Exit codes as observed, each captured from a bare invocation
(`cmd >/dev/null 2>&1; echo $?`), never through a pipe.

```
sq init --default-names --backend none
sq create task "Alpha task" --author tech-lead      # -> TASK-9
sq task 9 add-subtask "First subtask"               # -> ST1, status Todo
sq check                                            # exit=0

sq task 9 subtask 1 update --status Verified        # exit=1
# error: subtask ST1 cannot move Todo -> Verified (use --force to override)

sq task 9 subtask 1 update --status Verified --force  # exit=0, "updated TASK-9 ST1"

sq task 9 subtasks                                  # ST1 renders with status Verified
sq check                                            # exit=3
# error TASK-9: subtask ST1 has invalid status 'Verified'
```

`Verified` is a member of the squad's global status set (it belongs to the
*finding* machine) but not of the *subtask* machine, whose states are
Todo/InProgress/Done/Blocked/Cancelled. A status outside the global set is caught
earlier by the CLI parser, so the reachable shapes are exactly the cross-kind ones.

All three bundled kinds behave identically — driven, one scratch squad each:

```
sq feature 9 story 1 update  --status Fixed    --force   # exit=0
sq review 10 finding 1 update --status Done    --force   # exit=0
sq check   # exit=3, one error per kind:
#   error FEAT-9: story US1 has invalid status 'Fixed'
#   error REV-10: finding F1 has invalid status 'Done'
```

## The asymmetry with the item layer

**Driven.** At item level `--force` overrides the lifecycle *edge* and nothing
else — the vocabulary is still enforced, because `update` calls
`ValidatorEngine.gate()` after applying the delta:

```
sq task 11 update --status Done --force        # exit=0  (illegal edge, valid status)
sq task 11 update --status Verified --force    # exit=1
# error: 'Verified' is not a valid status for task (allowed: Blocked, Cancelled,
#        Done, Draft, InProgress, InReview, Ready)
```

At sub-entity level the same flag overrides both, because there is no second net.
This matters because `--force` is documented with one meaning across both layers:
`docs/workflow.md` says "Transitions are validated by the sub-entity machines;
`--force` overrides" for sub-entities and "only allows a transition the machine
permits; `--force` overrides" for items. Neither states that `--force` also lets a
value leave the declared vocabulary, and at item level it does not. **Read**, from
`docs/workflow.md` lines 189 and 285.

The sub-entity `add` path already performs the membership check the `update` path
skips, which is further evidence the gap is an oversight rather than a policy:

```
sq task 9 add-subtask "X" --status Verified    # exit=1
# error: 'Verified' is not a valid subtask status (one of: Blocked, Cancelled,
#        Done, InProgress, Todo)
```

## Which verbs write parent frontmatter without reaching the gate

**Driven at the CLI**, not read off the source. Method: corrupt one sub-entity as
above so the parent item now fails an error-level catalog member, then run each
door against that same parent. A door that reaches `gate()` must refuse; a door
that does not will succeed.

Control — gated doors on the corrupted parent, all exit 1:

```
sq task 9 update --title X          sq feature 9 update --title X
sq task 9 update --assignee qa      sq review 10 update --title X
sq task 9 status InProgress
```

Ungated — every one of these exit 0 against the same corpus:

| verb | driven on |
| --- | --- |
| `add-subtask` / `add-story` / `add-finding` | task / feature / review |
| `<kind> <k> update --title` | subtask, story, finding |
| `<kind> <k> update --assignee` | subtask |
| `<kind> <k> update --status … --force` | subtask, story, finding |
| `<kind> <k> update --story` / `--no-story` | subtask |
| `<kind> <k> update --severity` | finding |
| `<kind> <k> body` | subtask, story, finding |
| `<kind> <k> comment` | subtask, story, finding |
| `<kind> <k> remove --yes` | subtask, story, finding |

Supporting mechanism, **read**: `_services/_subentities.py` contains no
`ValidatorEngine` reference and no `.gate(` call at all. The same two patterns hit
`_services/_items.py` (4 and 3 times respectively), so the search itself is sound —
the zero is a real absence, not a bad pattern.

## What is *not* reachable — a correction to the original framing

**Driven.** The second error-level sub-entity validator, `subtask_story_mapping`,
is bypassed by the same doors but **cannot** be violated through the shipped CLI,
because `_subentities.py` duplicates it as a bespoke guard on every door that
could break the mapping. Every attempt refuses:

```
sq task 10 subtask 1 update --story US9      # exit=1  user story US9 not found in FEAT-9
sq task 10 add-subtask "X" --story US9       # exit=1  user story US9 not found in FEAT-9
sq feature 9 story 2 remove --yes            # exit=1  cannot remove US2: subtasks still
                                             #         map to it: TASK-10 ST1
sq task 10 update --parent FEAT-11           # exit=1  subtask ST1 -> US2 missing from FEAT-11
sq task 10 update --no-parent                # exit=1  subtask maps to a story but the task
                                             #         has no feature parent
```

Removing an *unmapped* sibling story does not renumber the survivors either, so
that indirect route is closed too (driven: removed US1 while ST1 mapped US2; ST1
still reads US2, `sq check` exit 0).

So the missing gate is a real structural gap across every sub-entity door, but
only one error-level member is currently exposed by it. The other is held shut by
duplicated logic — which is itself the fragility: the guard and the validator are
two independent implementations of one rule.

## The bulk-import surface makes it quieter

**Driven.** `sq import` reaches the same ungated core via a `sub-status` event
carrying `"force": true`. It does run the validator engine afterwards, but through
`report()` rather than `gate()`, and flattens error-level and warn-level issues
into one list printed as `warning:` — then exits 0 and keeps the write:

```
{"op":"create","type":"task","title":"Imported task","as":"tech-lead","handle":"t1"}
{"op":"add-sub","target":"t1","kind":"subtask","title":"Imported subtask","as":"tech-lead"}
{"op":"sub-status","target":"t1","kind":"subtask","local":"ST1","status":"Verified","force":true,"as":"tech-lead"}

sq import events.jsonl        # exit=0
#   warning: TASK-9: subtask ST1 has invalid status 'Verified'
#   imported 3 event(s)
```

The importer therefore *detects* the exact error it just wrote and reports it at
the same visual weight as an unwritten-body stub. An `add-sub` event carrying a
cross-kind status is refused in the pre-pass at exit 1 with nothing written, so
`force` on `sub-status` is the only import route in.

## Consequence

**Driven.**

- `sq check` exits 3 on a corpus produced entirely through supported CLI verbs at
  exit 0. This repo treats `sq check` as a must-pass gate, so a single `--force`
  typo turns the gate red with no other symptom.
- The corrupted value is in frontmatter, so it is the source of truth: `sq repair`
  rebuilds cleanly (exit 0, "rebuilt index: 11 items") and `sq check` still exits 3
  afterwards.
- **The parent item is stranded.** While the invalid sub-entity status stands,
  every gated door on the parent refuses — `update` on any axis and the `status`
  shortcut — quoting the sub-entity's problem. The ticket cannot be transitioned
  or edited until the sub-entity is fixed.
- No read surface degrades: `show`, `show --full`, `show --json`, `list -a`,
  `subtasks`, `tree -a` and `board list` all exit 0 and render the invalid status
  verbatim. Nothing hangs and nothing is lost.

## Recovery

**Driven.** One command, and it is itself an ungated sub-entity write:

```
sq task 9 subtask 1 update --status Todo           # exit=1 (Verified -> Todo is not
                                                   #         an edge on the machine)
sq task 9 subtask 1 update --status Todo --force   # exit=0
sq check                                           # exit=0
sq task 9 update --title Recovered                 # exit=0, parent unstuck again
```

## A reason the bypass may be partly deliberate

Not a fix proposal — a constraint any fix has to clear.

An unconditional `gate()` on these doors would be wrong in at least two places,
and one of them is already settled precedent:

- **`body` and `comment`.** `gate()` runs the parent item's *whole* per-item
  validator set, so a sub-entity comment would be refused for reasons unrelated to
  the write. TASK-866's discussion already ruled on exactly this shape for the item
  layer: blocking the discussion in which recovery is coordinated makes a
  fail-closed design worse, not safer.
- **`<kind> <k> update --status`.** This is the *only* way out of the state this
  bug creates (see Recovery, driven). Gating it against the parent's full set
  would make the corrupt corpus unrecoverable through the CLI — a bricking
  regression strictly worse than the current defect.

The narrow reading the evidence supports is that the sub-entity status path is
missing the same *membership* check its own `add` path performs, and that
`--force` should mean at sub-entity level what it demonstrably means at item level
— override the edge, not the vocabulary.

## Severity

Judged **medium**, on what was driven rather than on the surface's breadth.

Not low: it defeats the project's must-pass integrity gate through a supported,
documented verb at exit 0; the bad value is durable through `repair`; it strands
the parent ticket against every gated door; and the bulk-import path emits the
resulting error as a mere `warning:` line, which is how it would reach a corpus
unnoticed.

Not high: it needs an explicit `--force`, which is an "I mean it" flag; nothing
hangs, nothing is lost, and no read surface degrades; `sq check` names the exact
item and sub-entity; and recovery is a single command that is always available.
Contrast the parent-cycle defect, which was silent to every lint surface and left
no working way to see the damage.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-02T09:47:47Z] Mara Tester:
  - Filed off the gate gap Elias flagged while closing TASK-866's reopened clause. Verified independently at the CLI in six scratch squads rather than transcribed; two corrections to the original framing are in the body.
    
    - His structural claim holds: no sub-entity door reaches `ValidatorEngine.gate()` — `_services/_subentities.py` has zero `.gate(` calls, against three in `_services/_items.py` (pattern validated against that positive before letting the zero count).
    - **Reachable:** `<kind> <k> update --status <S> --force` writes a status outside the kind's own lifecycle at exit 0; `sq check` then exits 3 on it. Driven on all three bundled kinds. `sq import` reaches the same core via a `sub-status` event with `force: true`, and reports the resulting error as a `warning:` at exit 0.
    - **Not reachable:** `subtask_story_mapping` is bypassed by the same doors but cannot be violated through the shipped CLI — `_subentities.py` duplicates it as a bespoke guard on every door that could break it (remap, add, dependent-story removal, both parent doors). Driven, all refuse. The fragility there is the duplication, not an open hole.
    - The item layer keeps `--force` honest because `update` gates after applying: `task update --status Verified --force` exits 1 on the vocabulary while `--status Done --force` exits 0 on the edge. Sub-entities have no second net, and the docs give `--force` one meaning across both layers.
    - One constraint on any fix, driven: `<kind> <k> update --status … --force` is the only way out of the state this bug creates. An unconditional gate on that door would make the corrupt corpus unrecoverable through the CLI.
    
    Severity medium — needs an explicit `--force`, nothing hangs or is lost, recovery is one command; but it turns a must-pass gate red through a supported verb at exit 0, survives `sq repair`, and strands the parent item against every gated door until fixed.
    
    @tech-lead for triage.
- [2026-09-02T10:02:00Z] Olivia Lead:
  - Fix scoped as TASK-875 (fixes ref), three subtasks, assigned to the python dev.
    
    Building on the analysis rather than redoing it — the narrow reading is adopted as the
    rule: `--force` overrides an illegal transition, never the declared vocabulary. That is
    what it already means at item level, it is what the workflow doc says for both layers,
    and the sub-entity add door already enforces it. The fix is the membership check the
    update door is missing, not a general gate.
    
    The unrecoverability constraint is written into the task body as a constraint the
    implementer must clear, and ST2 exists solely to drive it. The trap it isolates: after
    the fix, recovery runs `update --status <valid> --force`, whose *target* is a member and
    passes the new check — but whose stored *current* value is not a node on the machine at
    all, and the transition lookup still has to read it. Whether that raises, returns no
    edges, or falls through decides whether recovery survives. Told them to establish it
    empirically against a pre-corrupted squad and to stop and report rather than ship if it
    does not.
    
    Scope calls, both recorded in the body so they are not re-litigated:
    
    - **The import route's write is in scope** (ST3), but as a driven proof rather than an
      assumption — "the core fix closes it too" is a claim until someone runs the events file.
    - **The importer's severity flattening is out of scope and needs its own item.** It is a
      different defect in a different place: the importer's result handling, not the
      sub-entity write path; it affects every error-level validator rather than this one; and
      correcting it changes `sq import`'s exit-code contract, which is an operator call.
      @qa please file it separately — you drove it and the evidence is yours.
    - **Consolidating the duplicated story-mapping rule is out of scope.** It is a real
      fragility and, as driven, not a reachable hole. Consolidating means deciding which
      validators run on which sub-entity door, and the recovery constraint already proves the
      answer is not "all of them on all of them" — the body and comment doors carry the same
      objection under the settled precedent about not blocking the discussion in which a
      recovery is coordinated. That is a design question, and there is an open proposed
      catalog decision it would have to fit into. Left as a separate concern for the
      architect; the bespoke guards stay untouched.
    
    One thing worth flagging upward, @architect: the open catalog decision states as read
    that "error-level findings fail the gate and abort a create or update". That is not true
    on the import door, which was driven here to report an error-level finding as a warning
    and exit 0 keeping the write. The characterisation of current behaviour is incomplete for
    that door and may want a correction.
- [2026-09-02T10:24:40Z] Mara Tester:
  - Importer severity flattening filed separately as BUG-878 (`related`), per the scope call.
    
    Driven a second error-level member through it — `subentity_container_marker`, via a plain
    `comment` event with no `force` — so it is general to the importer's result handling, not a
    quirk of the sub-entity route. Closing the membership hole here removes one of the two
    currently reachable routes into it; the other is untouched. @tech-lead
- [2026-09-02T14:19:34Z] Mara Tester:
  - Verified. Fresh `sq init --default-names --backend none`; exit codes from bare commands, mutations under `timeout 60`.
    
    The three-command repro, no longer reproducing:
    - `sq task 9 subtask 1 update --status Verified` -> exit 1, "'Verified' is not a valid subtask status (one of: Blocked, Cancelled, Done, InProgress, Todo)"
    - `sq task 9 subtask 1 update --status Verified --force` -> **exit 1, same message, nothing written**. Previously exit 0 + "updated TASK-9 ST1".
    - `sq check` -> exit 0 (one unwritten-body warn, no errors). Previously exit 3.
    - `sq task 9 subtasks` still renders ST1 at Todo — the write never landed.
    
    The membership message now fires ahead of the transition message, which is the right precedence: an invalid target is refused before an edge is even considered.
    
    All three bundled kinds, each driven:
    - subtask `--status Verified --force` -> exit 1
    - story `--status Fixed --force` -> exit 1 ("not a valid story status")
    - finding `--status Done --force` -> exit 1 ("not a valid finding status")
    
    **`--force` still waives an illegal transition** — the half that had to survive, driven on all three:
    - subtask Todo -> Done: without `--force` exit 1 "subtask ST1 cannot move Todo → Done (use --force to override)"; with `--force` **exit 0**, "updated TASK-9 ST1", stored Done, `sq check` exit 0
    - story Todo -> Done with `--force` -> exit 0
    - finding Open -> Verified with `--force` -> exit 0
    So `--force` now means at sub-entity level what it means at item level: it overrides the edge, not the vocabulary.
    
    **Recovery from a corpus already carrying an invalid stored status is still open** — the door that could not be closed. Wrote `status: Verified` into TASK-9's subentity frontmatter by hand, then:
    - `sq repair` -> exit 0, "rebuilt index: 11 items"
    - `sq check` -> exit 3, "error TASK-9: subtask ST1 has invalid status 'Verified'"
    - parent stranded as before: `sq task 9 update --title Renamed` -> exit 1, "subtask ST1 has invalid status 'Verified'"
    - `sq task 9 subtask 1 update --status Todo --force` -> **exit 0**, "updated TASK-9 ST1". No hang, no raise from the transition lookup reading a current value that is not a node on the machine.
    - `sq check` -> exit 0; `sq task 9 update --title Recovered` -> exit 0, parent unstuck
    Repeated with a stored `Fixed` (cross-kind, globally valid) and recovery to InProgress: exit 0, check back to 0. The recovery path does not depend on which invalid value is stored.
    
    Two boundary observations, neither a regression:
    - The new membership check applies to the recovery call too, so you cannot "recover" from one invalid status to another: stored Verified, `--status Verified --force` -> exit 1. Correct, and it does not close the exit — any legal member is reachable.
    - A status outside the squad's **global** set is a different, pre-existing condition and is not recoverable through this door because the index cannot be rebuilt around it: hand-wrote `Bogus`, `sq repair` -> exit 1, "item TASK-9 sub-entity ST1 has unknown status 'Bogus' in TASK-000009-recovered.md; fix the frontmatter before running `sq repair`", and every mutation on the parent then refuses with the frontmatter-diverged message. Consistent with the body's note that the CLI parser catches out-of-set values earlier; unchanged by this fix and out of its scope.
    
    The import route into the same core is closed too — driven under BUG-878: a `sub-status` event with `"force": true` carrying a cross-kind status is now refused in the pre-pass at exit 1, "line 3: 'Done' is not a valid finding status … 1 issue(s) found — nothing written."
    
    Nothing to flag.
<!-- sq:discussion:end -->
