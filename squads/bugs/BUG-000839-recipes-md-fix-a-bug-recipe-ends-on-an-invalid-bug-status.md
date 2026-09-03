---
id: BUG-839
sequence_id: 839
type: bug
title: recipes.md 'Fix a bug' recipe ends on an invalid bug status
status: Verified
author: qa
priority: low
refs:
- TASK-833
- MILE-836:targets
created_at: '2026-08-26T16:35:42Z'
updated_at: '2026-09-02T08:23:07Z'
---
<!-- sq:body -->
## What happens

`docs/recipes.md`'s "Fix a bug" recipe ends with `sq bug 10 status Done`. `Done` is not a
status in the bug lifecycle, so the recipe's own last command fails.

## Repro (driven in a scratch squad, following the recipe as written)

```
$ sq create bug "Lockout counter resets on refresh" --author qa   # → BUG-10
$ sq bug 10 status Done
error: 'Done' is not a valid status for bug (allowed: Blocked, Cancelled, Fixed, InProgress,
Open, Verified, WontFix)
$ echo $?
1
```

## Expected vs actual

- Expected: every command printed in an adopter-facing recipe resolves and succeeds against the
  live CLI — this project's own meta test
  (`tests/meta/test_documented_commands_resolve_against_cli.py`) checks that documented commands
  resolve against the CLI's command/option surface, but does not appear to catch an invalid
  *status value* passed to a command that does resolve.
- Actual: the recipe's final step exits 1. The bug lifecycle is
  `Open → InProgress → Fixed → Verified` (plus `Blocked`/`Cancelled`/`WontFix`); the recipe's
  intended terminal step is presumably `Verified` (or `Fixed`), not `Done`.

## Which surface should have caught it

The command surface: the CLI correctly refuses the invalid status and reports a clean `error:`
line at exit 1 — that part is working as designed. The gap is upstream, in the documentation
verification the tech-writer's task cited for this page: a command that names a real command and
option shape but an invalid *value* for one of its arguments passes the documented-commands
resolution check.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-26T16:36:14Z] Mara Tester:
  - Driven exactly as written in docs/recipes.md's 'Fix a bug' recipe: sq bug 10 status Done exits 1, error: 'Done' is not a valid status for bug (allowed: Blocked, Cancelled, Fixed, InProgress, Open, Verified, WontFix). Flagged by the writer on TASK-833 as pre-existing/out of scope; filing per QA brief.
  - @tech-writer for the recipe fix; @tech-lead if the documented-commands meta test should also cover invalid argument values.
- [2026-09-01T07:42:43Z] Theo Writer:
  - Fixed in `docs/recipes.md`. The "Fix a bug" recipe now runs the bug's own lifecycle to its terminal — `Open → InProgress → Fixed → Verified` — instead of borrowing the task's `Done`, with a following paragraph saying why the two do not close together and pointing at `sq workflow lifecycles` for any type's states and legal moves.
    
    Same class, found by driving every command in the file against a scratch squad: seven `sq create …` lines omitted the required `--author`, so they exit 2 on `Missing option '--author'`. That is every create in the page except the contract, milestone and priority ones. Fixed all seven (the last, `sq --at 2024-02-10 create task …`, does not contain the substring "sq create" and survives a naive grep). The whole file now drives clean end to end; the one remaining non-runner is `sq task 4 ref add TASK-3 --kind blocks`, where TASK-4 is an illustrative id the page never creates.
    
    On the open question for @tech-lead — whether the documented-commands meta test should also cover invalid argument values: my view is that the value half and the shape half are different problems and only one of them belongs in that test. A missing required option is a pure CLI-shape fact the existing resolution check already has in hand, and extending it there would have caught seven live defects on this page. An invalid *status* is not: `Done` is valid for a task and invalid for a bug, so checking it means resolving each command's addressed type and consulting that type's lifecycle — and a project that overrides the workflow spec makes the bundled answer the wrong one to check against. Cheaper and stronger: drive the fenced sequences against a scratch squad, which needs no vocabulary knowledge, catches transition errors as well as name errors, and is what actually found the `--author` class here.
- [2026-09-02T08:23:05Z] Mara Tester:
  - Verified — the recipe was driven, not read. Every command in `docs/recipes.md` § "Fix a bug" (lines 29-37) run in order against a fresh scratch squad at 0.14.0 (e9dde77), with the illustrative ids substituted for the ones actually allocated (BUG-21 / TASK-22):
    
    ```
    sq create bug "Lockout counter resets on refresh" --author qa   exit 0
    sq create task "Persist lockout counter" --author tech-lead     exit 0
    sq task 22 ref add BUG-21 --kind fixes                          exit 0  TASK-22 → BUG-21 (fixes)
    sq bug 21 status InProgress                                     exit 0
    sq task 22 status InProgress                                    exit 0
    sq task 22 status Done                                          exit 0
    sq bug 21 status Fixed                                          exit 0
    sq bug 21 status Verified                                       exit 0
    ```
    
    The reported symptom is gone: the recipe no longer ends on `sq bug <n> status Done`, and its terminal step now lands on a state the bug lifecycle actually declares. Confirmed against the shipped lifecycle rather than the prose — `sq workflow lifecycles` gives bug as `Open, InProgress, WontFix, Cancelled, Fixed, Blocked, Verified`, with no `Done`, and the whole `Open → InProgress → Fixed → Verified` path is legal as driven. The added closing paragraph's claim (a bug closes on `Verified`, not on the task's `Done`) matches what the CLI did.
    
    Underlying cause left open — flagging, not reopening. The defect class that produced this can still reach the docs unnoticed. Probed the shipped gate directly by calling `tests/meta/test_documented_commands_resolve_against_cli.py::_resolve` on candidate doc lines:
    
    ```
    RESOLVES   sq bug 10 status Done          # the exact BUG-839 defect
    RESOLVES   sq bug 10 status Nonsense      # a wholly invented status value
    RESOLVES   sq create bug "Lockout counter"  # missing the required --author
    REJECTED   sq create feature X --status Draft   # known-positive control: the gate does bite
    ```
    
    The control rejects, so the probe is sensitive; the first three resolving is a real blind spot, not a broken query. That matches the test's own docstring, which states a positional's shape (a status name) is never inspected — and no required-option check was added either, so the seven `--author` omissions fixed alongside this bug are equally un-gated for the next page. The writer's own recommendation on this thread was to drive the fenced sequences against a scratch squad instead of extending the resolution check; no such gate exists in `tests/` today. @tech-lead — the open question this bug raised is still open, and the answer landed as prose rather than as a gate.
<!-- sq:discussion:end -->
