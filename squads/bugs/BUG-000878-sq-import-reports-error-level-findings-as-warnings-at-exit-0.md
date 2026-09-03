---
id: BUG-878
sequence_id: 878
type: bug
title: sq import reports error-level findings as warnings at exit 0
status: Open
author: qa
priority: medium
severity: medium
refs:
- BUG-873
description: 'sq import flattens error- and warn-level validator findings into one
  warning: list, exits 0 and keeps the write; driven on two unrelated error-level
  members.'
created_at: '2026-09-02T10:21:15Z'
updated_at: '2026-09-02T10:23:55Z'
---
<!-- sq:body -->
## Summary

`sq import` runs the validator catalog over the items it touched, then prints every
finding — **error**-level and warn-level alike — as one undifferentiated `warning:`
line, exits **0**, and keeps the write. The level exists in the data and is discarded
at the reporting boundary, so the operator, the shell that ran the command and the
`--json` consumer all get "succeeded, with advisories" for a corpus that `sq check`
immediately calls an error and exits 3 on.

This is not specific to the sub-entity status route it was first noticed on. It is
general to the importer's result handling, and it is the reason the same underlying
write is loud on one door and quiet on another.

## Environment

**Driven.** `squads 0.14.0` (repo working tree, branch `release/0.14`, HEAD `be7f797`),
bundled workflow spec unless a scratch squad is noted as carrying an override. Seven
independent scratch squads, each a fresh `sq init --default-names --backend none` in
its own nested temp directory. Every invocation was `uv run --project <repo> sq …` —
the globally installed `sq` is 0.12.1 and refuses a v0.14 squad outright. Every exit
code was read from a bare command (`cmd >/dev/null 2>&1; echo $?`), never through a
pipe.

The tree was not clean during this run — another agent was mid-edit elsewhere in it.
Checked rather than assumed: none of the twenty-one modified or untracked paths is one
this evidence rests on. `_services/_import.py`, `_services/_validators.py`,
`_cli/_import.py` and the bundled workflow spec were all at their committed state
throughout.

## The mechanism

**Read.** `_services/_import.py::_board_debt_warnings` loads the post-commit index,
runs `ValidatorEngine.report()` over the touched items, and returns

```
[f"{i.item}: {i.message}" for i in issues if i.item in touched_ids]
```

`CheckIssue.level` is never read. There is no level filter, no partition, and no
second list — the strings land in `ImportApplyResult.warnings`, a `list[str]`, and
`_cli/_import.py:97` prints each as `warning: …`. The level is gone one layer below
the CLI, so no output mode can recover it.

For contrast, the same engine's `gate()` filters `if i.level == "error"` and raises on
the first one, and `sq check` prints the level as a per-line prefix. Only the import
path flattens.

## Is it narrow or general? — general in the handling, currently two members wide

The flattening itself is **general by construction**: it applies to whatever
`report()` returns, so any error-level catalog member that reaches it comes out as
`warning:`. What is narrow is *which* error-level members can reach it at all, because
the import pre-pass duplicates most of the same rules as its own bespoke checks and
refuses those events outright.

**Driven**, one route per error-level catalog member, each in its own scratch squad:

| error-level validator | import route driven | result |
| --- | --- | --- |
| `subentity_status_valid` | `sub-status` + `"force": true` | **written and kept**, printed `warning:`, exit 0 |
| `subentity_container_marker` | any event touching an item whose kind plural was renamed in an override | **written and kept**, printed `warning:`, exit 0 |
| `item_status_valid` | `status` + `"force": true` | refused in the pre-pass, exit 1, nothing written |
| `parent_in` | `create` with a wrong-type parent | refused in the pre-pass, exit 1 |
| `no_parent` | `create` of a no-parent type with a parent | refused in the pre-pass, exit 1 |
| `parent_acyclic` | `update` closing a two-item parent cycle | refused in the pre-pass, exit 1 |
| `subtask_story_mapping` | `add-subtask` naming a non-existent story | refused in the pre-pass, exit 1 |
| `parent_present` | not in any bundled type's effective set (**read**) — unreachable by construction |

So: **two independent error-level members, from two different families, are currently
degraded to `warning:` at exit 0.** The second one is the answer to the narrow-vs-general
question, because it shares nothing with the first — a different validator, a different
subsystem (corpus/spec alignment rather than sub-entity state), and a different route
(no `force` anywhere, any event touching the item will do).

### The second driver, in full

**Driven**, scratch squad with a workflow override renaming one sub-entity kind's
container plural — a supported customisation, `sq workflow lint` reports the spec OK:

```
sq init --default-names --backend none
sq create task "Alpha task" --author tech-lead        # -> TASK-9
sq task 9 add-subtask "First subtask"                 # -> ST1, writes a 'subtasks' container
sq task 9 subtask 1 body -m "Real body text."
sq check                                              # exit=0

# .overrides/workflow.toml gains:  [subentity_kinds.subtask]  plural = "worksteps"
sq workflow lint                                      # "workflow spec OK"
sq check                                              # exit=3
# error TASK-9: no 'worksteps' container section; the file carries 'subtasks' — …
```

Now one import event that merely touches the item:

```
events.jsonl:
{"op":"comment","target":"TASK-9","message":"Imported comment.","as":"tech-lead"}

sq import events.jsonl                                # exit=0
#   comment: 1
#   warning: TASK-9: no 'worksteps' container section; the file carries 'subtasks' — …
#   imported 1 event(s)
```

An error-level finding, on a corpus `sq check` exits 3 on, reported at the same visual
weight as an unwritten-body stub and followed by a success line.

### Error and warn are indistinguishable in the same output

**Driven**, one run, one squad — an error-level and a warn-level finding side by side:

```
events.jsonl:
{"op":"create","type":"task","title":"Imported task","as":"tech-lead","handle":"t1"}
{"op":"add-sub","target":"t1","kind":"subtask","title":"Imported subtask","as":"tech-lead"}
{"op":"sub-status","target":"t1","kind":"subtask","local":"ST1","status":"Verified","force":true,"as":"tech-lead"}

sq import events.jsonl                                # exit=0
#   warning: TASK-9: subtask ST1 has invalid status 'Verified'      <- error level
#   warning: TASK-9: ST1 body is unwritten (still the placeholder stub)   <- warn level
#   imported 3 event(s)

sq check                                              # exit=3
#   error TASK-9: subtask ST1 has invalid status 'Verified'
#   warn  TASK-9: ST1 body is unwritten (still the placeholder stub)
```

The same two findings, from the same catalog, seconds apart: `sq check` distinguishes
them and `sq import` does not. Nothing in the import output tells a reader that one of
those two lines means the gate would have refused this write on any other door and the
other means "tidy this up when you get to it".

## The machine-readable surface asserts success

**Driven**, same events with `--json`:

```json
{
  "op_counts": { "create": 1, "add-sub": 1, "sub-status": 1 },
  "issues": [],
  "ok": true,
  "applied": true,
  "warnings": [
    "TASK-9: subtask ST1 has invalid status 'Verified'",
    "TASK-9: ST1 body is unwritten (still the placeholder stub)"
  ]
}
```

`"ok": true`, `"issues": []`, and a level-free `warnings` array. A consumer branching on
`ok`, or on the exit code, has no way to tell an error-level finding from an advisory
one — the information is not withheld, it does not exist in the payload.

This is what makes the flattening more than cosmetic: `sq import` is the door most
likely to be driven by a script rather than read by a person, and it is the only door
that answers "the write you just made violates an error-level rule" with a zero exit
and a success flag.

## The stated behaviour and the driven behaviour

The tech lead asked this be checked against the record, and it should be read as a
report of what the door does, not as a ruling on which side is wrong — that is the
architect's call.

**Read**, the open validator-catalog decision: *"Error-level findings fail the gate and
abort a create or update; warn-level ones are advisory everywhere (read)."*

**Driven**, the import door: an error-level finding neither failed anything nor aborted
anything. The write stands, the exit is 0, and the finding is rendered in the vocabulary
the same sentence reserves for warn-level.

A second, independent way the same sentence does not hold — noticed while driving the
container-marker case, and volunteered because it bears on the same clause:

**Read**, `ValidatorEngine.gate()` passes `raw_text=None` and documents the reason:
*"every catalog validator that reads it is warn-level, so its absence cannot change a
gate decision."* That premise is false — `subentity_container_marker` reads
`ctx.raw_text` and returns `CheckIssue("error", …)`. **Driven**, on the override squad
above, with `sq check` at exit 3 naming that error:

```
sq task 9 update --title "Renamed2"     # exit=0
sq task 9 status Ready                  # exit=0
sq task 9 update --assignee qa          # exit=0
```

Three gated doors, all accepting writes, on an item carrying an error-level finding.
So that member fails no gate on **any** door, not only the import one.

**Inferred**, and offered only as the shape of the discrepancy: the decision's sentence
describes what `gate()` intends for the members it can see. Two things sit outside that —
a door that runs `report()` instead of `gate()`, and a member `gate()` structurally
cannot see. Whether the sentence should be narrowed or the doors widened is not mine to
rule.

## Consequence

**Driven.**

- A `sq import` run that violates an error-level rule is indistinguishable, by exit code
  and by `--json`, from one that did not. The next `sq check` is where it surfaces, and
  in this repo that check is a must-pass gate — so the failure appears attached to
  whoever runs the gate next, not to the import that caused it.
- The write is kept. **Driven**: after the import, `sq task 9 subtasks` renders `ST1`
  with status `Verified`, and `sq check` exits 3.
- The bad value is in frontmatter and therefore durable — it is the source of truth, and
  `sq repair` rebuilds around it cleanly.
- Nothing hangs, nothing is lost, and no read surface degrades.

## What is not claimed

- This is not the sub-entity write-path gap and does not overlap its fix. Closing the
  membership hole on the sub-entity status door removes *one* of the two currently
  reachable routes into this reporting bug; the container-marker route is untouched by
  it, and so is every error-level member a future catalog gains.
- No fix is proposed. Correcting this changes `sq import`'s exit-code contract — which
  exit code an error-level finding earns, and whether the write is kept, rolled back or
  reported and kept — and that is an operator decision, not a QA one.

## Severity

Judged **medium**.

Not low: it is a reporting contract that is wrong in general rather than in one place —
driven on two unrelated error-level members, and structurally applicable to every one
that can reach the reporter. It is the one door where an error-level violation returns
exit 0 with `"ok": true`, and it is the door most likely to be automated. The resulting
corpus turns a must-pass gate red with the cause already off-screen.

Not high: nothing hangs and nothing is lost; `sq check` remains a complete and reliable
backstop that names the exact item and the exact rule; the pre-pass still refuses five
of the seven reachable error-level members outright at exit 1 with nothing written; and
every read surface renders the affected corpus correctly.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-02T10:23:55Z] Mara Tester:
  - Filed off the scope call on the sub-entity force bug. Driven at the CLI in seven scratch
    squads; the evidence is in the body, labelled driven / read / inferred throughout.
    
    - **The flattening is general, not narrow.** The importer's result handling discards
      `CheckIssue.level` outright — `_board_debt_warnings` returns `f"{i.item}: {i.message}"`
      with no level filter, into a `list[str]`. So it applies to whatever the reporter returns,
      and no output mode can recover the level because it is gone below the CLI.
    - **Driven on a second, unrelated error-level member** so this is not one route's quirk:
      `subentity_container_marker` (a workflow override renaming a kind's container plural),
      reached by a plain `comment` event with no `force` anywhere. `sq check` exits 3 on that
      corpus; `sq import` prints it as `warning:` and exits 0.
    - **What is narrow is the current exposure, and only because of duplication.** I drove one
      import route per error-level catalog member: five are refused in the pre-pass at exit 1
      with nothing written (item status, both parent-eligibility rules, the parent cycle, the
      story mapping), one is unreachable by construction, and two get through. The table is in
      the body.
    - **Machine consumers are told it succeeded:** `--json` gives `"ok": true`, `"issues": []`,
      and a level-free `warnings` array. Exit 0 either way.
    - Error and warn are literally indistinguishable in one import's output — the body has a
      run where the two lines sit next to each other under the same `warning:` prefix, and the
      `sq check` on the same corpus seconds later that prints `error` and `warn`.
    
    On the catalog decision's "error-level findings fail the gate and abort a create or update":
    driven, that does not hold on this door — the write stands at exit 0. It also does not hold
    for one member on **any** door: `gate()` passes `raw_text=None` on the documented premise
    that every raw_text-reading validator is warn-level, and `subentity_container_marker` reads
    it and is error-level. Driven, on a corpus where `sq check` exits 3 naming that error,
    `update --title`, `status` and `update --assignee` all exit 0. Reporting the behaviour, not
    ruling on which side should change.
    
    No fix proposed — correcting this moves `sq import`'s exit-code contract, which is an
    operator call. Severity medium: reasoning in the body, and it turns on the reporting being
    wrong in general while `sq check` stays a complete backstop.
    
    @tech-lead for triage. @architect the catalog-decision clause above is the one that was
    flagged upward; both counter-examples are driven.
<!-- sq:discussion:end -->
