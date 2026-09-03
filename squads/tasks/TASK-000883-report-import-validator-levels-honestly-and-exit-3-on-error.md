---
id: TASK-883
sequence_id: 883
type: task
title: Report import validator levels honestly and exit 3 on error findings
status: Done
author: tech-lead
assignee: python-dev
priority: high
refs:
- BUG-878:fixes
description: sq import flattens error- and warn-level findings into one warning list
  at exit 0; carry the level through and exit 3 when an error-level finding is present,
  keeping the write.
created_at: '2026-09-02T13:05:09Z'
updated_at: '2026-09-02T14:01:37Z'
---
<!-- sq:body -->
## What is wrong

`sq import` runs the validator reporter over the items an import touched, then renders every
finding — error-level and warn-level alike — as one `warning:` line, exits 0, and keeps the
write. `_services/_import.py::_board_debt_warnings` builds its list without ever reading
`CheckIssue.level`: no filter, no partition, no second list. The level is discarded one layer
below the CLI, so no output mode can recover it. `--json` answers `"ok": true`, `"issues": []`
and a level-free `warnings` array for a corpus the integrity check calls an error and exits 3
on.

QA drove this on two unrelated error-level members, from different families and reached by
different routes, so the flattening is general to the importer's result handling rather than a
quirk of one validator. The current exposure is two members wide only because the import
pre-pass duplicates five of the other rules and refuses those events outright at exit 1 with
nothing written. Any error-level member the catalog gains later falls into the same hole.

## The ruling on the exit-code contract

Correcting this moves the door's exit-code contract, and that was flagged as an operator call.
The instruction is that it ships fixed, so the call is on *how*. It is:

**The write is kept, the level is reported honestly, and an error-level finding earns exit 3.**

*Why not refuse the write.* This door already has a designed refusal surface — the pre-pass
validates every event before anything is written and refuses the whole file at exit 1, and the
documented promise is that only a fully clean file is applied, in one transaction. The findings
at issue are not event-level defects. They come from running the reporter over touched items
after the transaction committed, and at least one of them is pre-existing corpus state the
import did not cause: in the container-marker case the item was already in that condition
before an unrelated comment event touched it. Rolling back a clean import because an item it
touched was already carrying a standing error would make the importer unusable on exactly the
corpora that most need bulk work. Promoting these rules into the pre-pass is a different and
larger change, and one that re-duplicates what the pre-pass already does.

*Why not surface the level and leave the exit at 0.* This is the door most likely to be driven
by a script rather than read by a person. A prefix a human can see and a wrapper cannot is not
a contract, and `--json` would go on asserting success.

*Why 3, rather than a new code or 1.* Code 3 is already documented as "error-level issues were
reported", with warn-level-only staying 0. Adopting it here makes two doors say the same thing
about the same findings and invents nothing. Code 1 is wrong: it means squads could not
complete what was asked and, on this door, that nothing was written. Here the import completed
and the write stands. Keeping 1 for a pre-pass refusal and 3 for "applied, and the touched
corpus carries an error-level finding" is the distinction a caller actually needs.

## What to change

- Carry the level out of `_board_debt_warnings` instead of discarding it. Findings reach the
  result with their level intact — partitioned or tagged, the shape is the implementer's call;
  the requirement is that the human output and the JSON payload can both tell the two apart.
- Human output distinguishes the levels by prefix, the way the integrity check does, rather
  than printing both as `warning:`.
- `--json`: `issues` carries every finding with its level; `warnings` keeps the warn-level
  subset it holds today, so no existing consumer silently loses a line. `ok` is false when any
  error-level finding is present. `applied` stays true — it is the field that says the write
  happened, and it must go on saying so at exit 3.
- The command exits 3 when the reporter returned at least one error-level finding on a touched
  item, and 0 when it returned only warn-level findings or none. Exit 1 (pre-pass refusal,
  nothing written) and exit 2 (usage) do not move.
- `--dry-run` writes nothing and so has no touched-item corpus to report on. It does not gain a
  new non-zero path.
- The exit-code table in the FAQ documents 3 as the integrity check's code alone. It needs
  widening to name this door and to state the part specific to it: a 3 from an import means the
  events were applied. Another agent is working in `docs/` and the changelog — coordinate on
  that edit rather than collide with it.

## What an adopter's automation sees change

- An import that today exits 0 with `warning:` lines can begin exiting 3. `sq import f.jsonl &&
  next-step` stops where it used to continue, and a `set -e` script aborts. That is the
  intended break and the whole point of the change.
- The break is bounded: it fires only when the reporter returns an error-level finding on an
  item the import touched. A corpus that is clean at those rules is unaffected.
- A retry loop keyed on "non-zero means nothing happened" becomes wrong for this door. A 3
  means applied-and-flagged, so re-running the same file replays the events. This is the one
  real migration hazard, and the documentation has to say it in those terms.
- A consumer reading `warnings` keeps every line it reads today. One branching on `ok` or on
  the exit code starts seeing failures it was previously blind to.

## Acceptance

Each of these fails before the change:

1. An import whose touched items carry an error-level finding exits 3, and the write is present
   afterwards. Exit codes read from a bare command, never through a pipe.
2. The same import shape with only warn-level findings exits 0.
3. An import producing no findings at all exits 0.
4. A pre-pass refusal still exits 1 with nothing written; that contract does not move.
5. `--json` on the error-level case: `ok` false, `applied` true, the error-level finding present
   in `issues` carrying its level, and the warn-level finding still present in `warnings`.
6. A single run producing one finding of each level renders them distinguishably in human
   output.
7. `--dry-run` over the same events exits 0 and writes nothing.

Drive at least one case through a validator that reaches the reporter without `force`, so the
coverage is not pinned to a single route.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 883 add-subtask "<title>"`; track with `sq task 883 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-02T13:08:23Z] Olivia Lead:
  - Scoped off BUG-878. The exit-code call is made and is in the body — do not re-open it, and do
    not narrow the fix to the two error-level members that reach the reporter today. The defect is
    that `_board_debt_warnings` discards `CheckIssue.level`; fixing it for the members currently
    exposed and not for the reporter's result handling leaves the same hole open for the next
    catalog member.
    
    Two things to hold on to while implementing. `applied` must stay true at exit 3 — it is the
    field that tells a caller the write happened, and a caller that reads exit 3 as "nothing
    happened" and replays the file is the failure this change must not create. And `--dry-run` gets
    no new non-zero path; it writes nothing, so it has no touched-item corpus to report on.
    
    The FAQ exit-code table needs the row for 3 widened. Another agent is live in `docs/` and the
    changelog — coordinate before editing rather than collide.
    
    @python-dev yours, Ready. @qa for verification once it lands; the acceptance list is written to
    fail before the fix, including the negative cases.
- [2026-09-02T13:23:21Z] Elias Python:
  - Implemented. The level now leaves the reporter intact and reaches every surface.
    
    - `_board_debt_warnings` is now `_board_debt_findings` and returns `list[CheckIssue]` whole — no
      level filter and no flattening to strings, so the fix is in the reporter's result handling
      rather than in the members that reach it today.
    - `ImportApplyResult` gains `findings` (levelled) alongside `warnings`. `warnings` is now the
      warn-level stream: the apply pass's own advisories plus the warn half of `findings`, in the
      exact wording it has always used.
    - Human output prints error-level findings as `error: <item>: <msg>` before the `warning:` lines,
      the way the integrity check prefixes its own.
    - `--json`: `issues` carries every finding with `level`/`item`/`message`; `ok` is false when any
      is error-level; `applied` stays true.
    - Exit 3 when an applied run's touched items carry an error-level finding. `--dry-run` and the
      pre-pass refusal (exit 1, nothing written) are untouched.
    
    Documented the hazard in the `sq import` command help, in those words — "**Exit 3 from this
    command means applied-and-flagged.** The events are on disk. A retry loop keyed on 'non-zero means
    nothing happened' will replay them; branch on `--json`'s `applied` instead."
    
    Two things for whoever takes the docs half. The exit-code contract is documented in **two**
    places, not one: `docs/faq.md`'s stable table and `docs/stability.md`'s frozen-contract table.
    Both currently attribute code 3 to `sq check` alone and both need the row widened plus the
    applied-and-flagged sentence. I did not edit either — another agent is live in `docs/`, and
    adopter prose is the writer's artifact.
    
    Tests: `tests/cli/test_import_exit_code_and_finding_levels.py` (exit 3 + both prefixes + the write
    present, the JSON shape, warn-only at 0, `--dry-run` at 0, the pre-pass refusal still at 1) and
    `tests/service/test_import_findings_carry_their_level.py` (the engine returns the level; the warn
    stream does not smuggle the error line in). The error-level case is driven through the container-
    marker route, which needs no `force` — any event touching the item reaches it.
    
    @qa for verification; @tech-lead the two-table point is the only correction to the brief.
- [2026-09-02T13:39:06Z] Elias Python:
  - Gates, both suite runs read from their summary line.
    
    - Baseline, HEAD 4e126fc2 in an isolated worktree (no stash — three other agents have uncommitted
      work in this tree, including in one file I edit): **4552 passed, 12 skipped, 0 failed**.
    - With the fix, full tree: **4603 passed, 12 skipped, 7 failed**. None of the seven is mine, and
      none is in the import path: two are the tree `--json` goldens, four belong to a new
      validator-context meta scan that is not yet committed, and one is the module-level mutable-state
      allowlist reporting `CONTEXT_REQUIRED`/`GATE_WITHHELD` in `_services/_validators.py`. All seven
      sit in the two lanes running concurrently, and the baseline is green on the committed code.
    - `pyright` reports 0 errors on the five files I touched (the two it reports tree-side are the
      other lane's). `ruff check` and `ruff format --check` clean on mine. `sq check` clean.
    
    Falsified before trusting: with the service and CLI halves reverted, the new CLI tests fail on the
    real defect — `assert 0 == 3` under a run printing both findings as `warning:`, and `issues == []`
    where the levels should be. One pre-existing assertion moved and it moved by strengthening:
    `test_json_shape_on_success` asserted `issues == []` for a run that does produce a warn-level
    finding; it now asserts the level, the item, and that `warnings` mirrors it.
<!-- sq:discussion:end -->
