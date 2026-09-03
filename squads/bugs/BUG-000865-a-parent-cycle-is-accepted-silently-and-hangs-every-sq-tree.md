---
id: BUG-865
sequence_id: 865
type: bug
title: A parent cycle is accepted silently and hangs every sq tree call
status: Open
author: qa
priority: high
severity: high
description: update --parent accepts a self- or mutual-parent edge with exit 0; every
  sq tree call in the squad then spins forever while every other read surface stays
  fine.
created_at: '2026-09-01T15:41:07Z'
updated_at: '2026-09-01T15:41:30Z'
---
<!-- sq:body -->
## Summary

An item can be made its own parent, or two items each other's parent, through the
ordinary `update --parent` verb with no warning and exit 0. Once that edge exists,
every `sq tree` invocation in that squad spins in an unbounded loop and never
returns — including a targeted tree rooted at an item that has nothing to do with
the cycle. No other read surface is affected, and no lint surface reports the
condition, so the only symptom an operator or agent sees is a command that never
comes back.

## Environment

**Driven.** `squads 0.14.0`, repo HEAD `19acd14`, bundled workflow spec (no
`.overrides/`), fresh `sq init --default-names --backend none` in a scratch tree.
Reproduced in three independent scratch squads.

## Minimal reproduction

**Driven.** One item, one command. Exit codes are as observed; every command that
was expected to hang was run under `timeout 15`, so `exit=124` means the timeout
killed a still-running process, not a manual kill.

```
sq init --default-names --backend none
sq create bug "Repro" --author qa            # -> BUG-9
timeout 15 sq tree                           # exit=0, renders normally

sq bug 9 update --parent BUG-9               # exit=0, prints "updated BUG-9"

timeout 15 sq tree                           # exit=124  (hang)
timeout 15 sq tree BUG-9 --json              # exit=124  (hang)
sq check                                     # exit=0, "no issues"
sq repair                                    # exit=0, "rebuilt index: 9 items"
```

The two-item form behaves identically:

```
sq create bug "Alpha" --author qa            # -> BUG-9
sq create bug "Beta"  --author qa            # -> BUG-10
sq bug 9  update --parent BUG-10             # exit=0
sq bug 10 update --parent BUG-9              # exit=0
timeout 15 sq tree BUG-9                     # exit=124
```

## Blast radius, surface by surface

**Driven.** Every row below was executed against a squad holding one cycle.

Hangs (exit=124 under `timeout 15`):

- `sq tree` (bare)
- `sq tree <id>` — including `sq tree EPIC-9` where the epic is unrelated to the
  cycle and has no path to it
- `sq tree --json`
- `sq tree --depth 1` — bounding the depth does not help
- `sq tree -a`
- the terminal browser's tree pane (**read**, not driven: `_tui/_browse.py`
  awaits the same `tree_view()` call that hangs)

Unaffected — exit 0, correct output:

`sq list`, `sq list --json`, `sq list --parent <id>` (correctly lists the child on
both sides of a two-item cycle), `sq show <n>`, `sq <type> <n> show --full
--comments`, `sq check`, `sq check --json`, `sq repair`, `sq search`, `sq blocked`,
`sq graph <id>`, `sq graph <id> --json`, `sq mine <role>`, `sq workload`,
`sq board list`, `sq inbox <role>`, `sq reflog`, `sq sync`, `sq workflow lint`.

No surface was found that produces wrong-but-terminating output. The failure is
binary: a surface either renders correctly or never returns.

Candidate-set nuance, **driven**: the loop only runs over items in the tree's
candidate set. Moving the cyclic items to a terminal status makes bare `sq tree`
return to normal while `sq tree -a` still hangs — so a cycle among closed items is
latent until someone asks for closed items.

## Can the CLI alone create it

**Driven — yes, no hand-editing of frontmatter is required.** `update --parent`
accepts a self-parent in a single command and accepts a mutual pair in two. Both
report success and exit 0. `sq check` and `sq repair` both accept the resulting
corpus as clean afterwards.

## Which types are exposed

**Driven**, one probe per type on a fresh squad. Refused at the write door with a
clear error and exit 1:

- `epic` — "epic takes no parent" (own `no_parent` validator)
- `feature` — "a feature's parent must be of type epic"
- `task` — "a task's parent must be of type feature"
- `decision`, `contract`, `milestone`, `guide` — "takes no parent"

Accepted, exit 0:

- `bug` — self-parent, and bug/review mutual
- `review` — self-parent, and review/bug mutual

**Read**, explaining the split: `parents = []` in the spec means unconstrained, so
`parent_in` lets anything through; the block is `no_parent`, which `epic` declares
itself and which the `records` category hands to `decision`/`contract`/`milestone`/
`guide` through the category validator bundle. `bug` and `review` are the only
bundled types that are category `work`, declare `parents = []`, and get no
`no_parent` from either source — so they are the whole exposed set under the
bundled spec. Any project override that gives a type an empty `parents` in the
`work` category widens it.

## Mechanism

**Driven**, by interrupting a hung run with `faulthandler.dump_traceback_later`
against the service call directly. The stack sits in `_compute_keep_set`
(`_services/_base.py`), in its upward `while item is not None and item.parent is
not None` walk: with a cyclic parent chain the walk alternates between the same
items forever. It is a busy loop with no stack growth, so it pegs a core and never
raises — which is why it presents as a hang rather than a crash. The loop's own
`keep_set.add` is idempotent, so nothing about the accumulating state ever ends it.

**Driven**, second fault behind the first: neutralising `_compute_keep_set` in a
probe and re-running the same call makes the downward `_walk_tree` recursion fail
with `RecursionError`. So the traversal has two independent cycle-unsafe walks, not
one; the upward loop merely reaches its failure first. Anything that addresses only
the hang will change the symptom to a crash rather than remove it.

For contrast, **read**: the subtree resolver in `_views.py` walks the same
parent/child structure and does carry a visited set, so the views surface is not
exposed to this.

## Recovery

**Driven.** `sq <type> <n> update --no-parent` clears the edge and `sq tree`
returns to normal immediately. So a poisoned squad is recoverable through the CLI
with no data loss — the difficulty is diagnosis, not repair, because nothing points
at the cycle.

Side observation, **driven**, minor and separable: `update --parent ""` prints
"updated <ID>" and exits 0 while leaving the parent unchanged. The empty value
silently no-ops but reports success. Noted here only because it is the first thing
one reaches for when trying to undo the edge.

## Severity

Proposed **high**, not critical. The reasoning:

- Reachable by an agent or operator in one ordinary command, with no warning at
  the write door and no report from either lint surface afterwards.
- The consequence is a hang, not an error — the caller has no exit code to react
  to and no message to read, and an agent that runs the command without a timeout
  blocks indefinitely.
- The affected surface is the hierarchy view a coordinator uses to assess a
  subtree before delegating, and it is denied for the whole squad, not just for
  the items in the cycle.
- Held back from critical because there is no data loss and no corruption: the
  markdown and the index stay consistent, `sq repair` round-trips them, every
  other read surface keeps working, and one CLI command undoes it.

## Primary defect

**Inferred**, from the driven evidence above: the write door is the primary defect
and the traversal hang is its symptom. A parent cycle is not a legitimate corpus
state — the parent relation is the squad's hierarchy, and every consumer of it is
entitled to assume it is acyclic. Letting one in means every present and future
traversal has to defend itself against it separately, which the evidence already
shows is not happening: there are two cycle-unsafe walks in the tree code today
and a third walk elsewhere that happens to guard. The traversal robustness is
worth having on its own merits, but treating it as the fix would leave the corpus
holding a shape nothing else in the system expects.

A secondary gap sits between the two: neither `sq check` nor `sq repair` can see
the condition, so a squad that already carries a cycle has no way to be told.

Where the write door should refuse, and how a traversal should behave if one gets
in anyway, are the architect's and tech lead's calls — deliberately not proposed
here.

## What in the original report did not hold up

The report attributed the exposure to `parents = []` plus a missing `no_parent`
across the affected types. The `bug`/`review` half of that is correct, but
`parents = []` alone is not the condition: `decision`, `contract`, `milestone` and
`guide` also declare `parents = []` and all four are refused, because the `records`
category supplies `no_parent` to them. The exposed set is narrower than the
declaration table alone suggests.

The report also placed the hang across both `_compute_keep_set` and `_walk_tree`.
Both are cycle-unsafe, but only the first one runs: the upward loop spins before
the downward recursion is ever entered, and the downward recursion's failure mode
is a `RecursionError`, not a hang.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-01T15:41:30Z] Mara Tester:
  - Filed off the architect's lead, reproduced independently in three scratch squads on 0.14.0 / HEAD 19acd14 with the bundled spec. Every hang claim is a timeout-15 exit=124, not a manual kill.
  - @architect two corrections to the lead: parents = [] alone is not the exposure condition (decision/contract/milestone/guide all declare it and are all refused, via the records category's no_parent bundle) — bug and review are the whole exposed set; and only _compute_keep_set actually runs, _walk_tree's recursion is a second latent fault behind it that surfaces as RecursionError once the first is neutralised.
  - @tech-lead the write door is my primary-defect call: the cycle is creatable in one ordinary command with exit 0, sq check and sq repair both accept the result, and a poisoned squad denies sq tree for every item including unrelated subtrees. Recovery is update --no-parent, so no data loss. No fix design in the body — that is yours and the architect's.
<!-- sq:discussion:end -->
