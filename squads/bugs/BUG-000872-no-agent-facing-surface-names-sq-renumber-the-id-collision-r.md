---
id: BUG-872
sequence_id: 872
type: bug
title: No agent-facing surface names sq renumber, the id-collision remedy
status: Open
author: qa
priority: high
refs:
- BUG-865
description: renumber is one of only two shipped commands absent from all 1744 lines
  of agent-facing guidance, and no surface detects a duplicate id either.
created_at: '2026-09-02T08:49:51Z'
updated_at: '2026-09-02T10:02:23Z'
---
<!-- sq:body -->
## Symptom

**Driven.** Two of the shipped `sq` commands are named nowhere in any surface an agent reads: `renumber` and `ui`. `ui` is defensibly absent — an agent should not be launching an interactive TUI. `renumber` is not, because it is the remedy for a condition agents actually cause: two trees allocating the same number.

The `.squads.json` counter is per-tree, so a worktree, a branch, or an isolated scratch index allocates from its own sequence. When those trees meet, two items carry the same number. `sq` ships a remedy for exactly this — `sq repair --renumber` post-merge, `sq renumber` pre-merge — and no agent-facing carrier mentions either.

## The measurement

**Driven**, and re-measured independently rather than taken from the report that raised it.

Command inventory: 38 top-level commands, enumerated from `sq --help`.

Agent-facing surface: the union of 13 rendered surfaces — the `squads` skill, the nine `sq-<type>` skills (`sq-bug`, `sq-contract`, `sq-decision`, `sq-epic`, `sq-feature`, `sq-guide`, `sq-milestone`, `sq-review`, `sq-task`), `sq-memory`, `greeting`, and `CLAUDE.md`. Rendered with `sq skill <slug> show` from the project root with `--dir` set. **1744 lines, 78,094 characters.** Every render was checked before use: all twelve exited 0 and returned a panel header plus body, none returned error text.

Each of the 38 command names was then searched against that union, word-boundary and case-insensitive, with a second pass over a whitespace-stripped copy to catch a name broken across a line wrap.

Result: **36 of 38 commands appear; two do not.**

```
renumber   0 word-boundary hits   0 whitespace-stripped hits
ui         0 word-boundary hits   (60 whitespace-stripped hits, all substring
                                   noise inside "build", "guide", "require")
```

For contrast, the neighbouring maintenance verbs are all present: `repair` 4, `migrate` 4, `sync` 4, `adopt` 3, `check` 22, `tree` 7, `create` 51.

**Method note, because a zero is the one result that never proves a search worked.** The grep was validated against known positives before any zero was trusted, and that check earned its keep: the first corpus build used `tr -d` to strip box-drawing characters, which operates on bytes and mangled the multi-byte UTF-8, after which grep returned 0 for *every* term including `tree` and `create`. Had the known-positive check not been run first, this bug would have been filed claiming all 38 commands were missing. The corpus was rebuilt character-wise in Python and the sanity pass then returned `tree` 7, `create` 51, `check` 22, `list` 21, `comment` 42, and a control term 0.

## The guidance exists — in the wrong carrier

**Driven.** `renumber` is named in 8 human-facing files: `docs/adoption.md`, `docs/faq.md`, `docs/internals.md`, `docs/recipes.md`, `docs/stability.md`, `docs/workflow.md`, `README.md`, `CHANGELOG.md`. Zero agent-facing carriers.

`sq renumber --help` is thorough and even distinguishes the two verbs — "A distinct verb from `sq repair --renumber` (the post-merge collision fixer): this one is operator-parameterized and run deliberately, once, before a merge". That text is reachable only by an agent who already suspects the command exists.

**Driven**, one asymmetry worth noting: `sq repair --help` lists `--renumber` as a bare flag with **no help text at all**, so even an agent who reads `repair --help` learns nothing about what it does.

## Nothing detects the condition either

**Driven / read.** `sq check` has no uniqueness or collision rule: `VALIDATOR_NAMES` holds 16 members and none concerns ids, sequence numbers, or duplication. `sq repair` reports only `rebuilt index: N items, counter=N` and says nothing about numbers arriving twice. So a collision is neither prevented, nor reported, nor remediable by any route an agent is told about.

## What actually happened

**Read**, from the coordinating agent's report, not driven by me: a verification worktree allocated BUG-867 while the main tree independently created MILE-867. The recovery was done by hand — the item was recreated — because the agent did not know `sq repair --renumber` existed.

**Driven**, the corpus is consistent with that account: `MILE-867` is present, there is no `BUG-867`, and a full scan of `sq list -a --json` finds no duplicate sequence numbers anywhere in the live corpus.

The defect is not the hand recovery. It is that no surface the agent reads named the tool that existed for the job.

## Precedent

BUG-789 is the same shape and was accepted: guidance that lives in one carrier and not the one the agent actually reads. There the "`.md` files are sq-managed" rule was stated for writes in all four agent-facing carriers and never for reads. Here the remedy for a duplicate id is stated in eight human-facing files and in none of the thirteen agent-facing ones.

## Environment

**Driven.** `squads 0.14.0`, branch `release/0.14` at `ad9c5d6`, bundled workflow spec, no `.overrides/`. Renders taken with `FORCE_COLOR=0 NO_COLOR=1`; ANSI stripped before matching.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-02T10:02:23Z] Olivia Lead:
  - Fix scoped as TASK-876 (fixes ref), three subtasks, assigned to the python dev — the
    centre of gravity is the guard and a help string, not prose, so one owner in one pass
    rather than a writer and a dev colliding in the same tree on a change that has to land
    together.
    
    **Ruling on guidance-edit versus guard: both, and the guard is the durable fix.**
    
    Adding the verb to a skill fixes this instance and leaves the class exactly where it is.
    The guard closes the class, and the objection to it — that it forces a judgement about
    commands that should legitimately be absent — does not survive contact with this
    repository. We have already solved that same problem three times: the lockstep guard over
    the live command table, the illustrative-types allowlist in the documented-commands
    guard, and vulture's ignore list. In each, the exception is one entry with a one-line
    reason and the assertion runs in both directions so a stale exemption fails too. `ui` is
    one such entry; it is the guard working, not an obstacle.
    
    This is deliberately not the same ruling as the earlier read-side guidance bug, which I
    ruled documentation-only, and the distinction should be on the record so this does not
    read as a reversal. There the condition was an agent *choosing* to open a file instead of
    running a command — a property of tool use, outside any tracked artifact, unobservable in
    principle. Here the condition is that a name present in one artifact squads generates is
    absent from another artifact squads generates. Static, in-process, fully enumerable. An
    existing guard already sits on that line from the other side, walking every command cited
    in the bundled docs and resolving it against the live command tree; this is the missing
    inverse direction of it.
    
    Carrier list and regeneration path reused from the earlier fix rather than reinvented,
    including the settled decision that the two pointer templates are not carriers of a rule
    like this. Placement is scoped as a judgement, not a broadcast — this is a merge-time
    maintenance remedy and belongs next to the neighbouring maintenance verbs, not on every
    surface.
    
    One measured correction to the report, and it is a real implementation trap rather than
    a nitpick. The 38 is the *rendered help* count. The live Typer table holds **52**, because
    fourteen item-type aliases are registered as commands. A guard built naively from the
    command table flags all fourteen aliases as missing and is useless. It must de-alias
    against the bundled spec, which is exactly the derivation the existing lockstep guard
    already performs — 52 minus 14 is 38, verified. That is written into the subtask.
    
    Also written in: pin the roster (the generated per-type skill text is roster-dependent
    through the has-dev gate, so an unpinned corpus shifts under the guard), and validate the
    matcher against known positives before trusting a zero — the byte-wise-strip trap you
    documented is the reason, and I re-ran the check on the main skill before relying on it.
    
    **Deferred, explicitly, with the reason on the task:** the third gap you named — nothing
    detects a collision either. A duplicate number cannot exist inside one index, so the
    condition is only observable when two trees' markdown lands in one folder, which makes
    the corpus-walking rebuild rather than the per-item validator catalog its natural home.
    Deciding what the rebuild should then do — refuse, report, or shift the collision itself
    — is a design call on the integrity core, and the open proposed catalog decision would
    need to accommodate it (it currently lists no uniqueness member at all). @architect that
    one is yours; making the remedy discoverable does not depend on it and should not wait
    for it.
    
    Noted for the coordinator on the task: the manifest regeneration is not the implementer's
    step and is explicitly withheld from them.
<!-- sq:discussion:end -->
