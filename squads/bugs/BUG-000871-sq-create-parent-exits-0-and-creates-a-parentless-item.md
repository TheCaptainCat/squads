---
id: BUG-871
sequence_id: 871
type: bug
title: sq create --parent "" exits 0 and creates a parentless item
status: Verified
author: qa
priority: low
refs:
- BUG-865
description: The truthiness shape fixed in the update path is still live at three
  sites in the create path; the empty value is discarded and success reported.
created_at: '2026-09-02T08:49:48Z'
updated_at: '2026-09-02T14:18:42Z'
---
<!-- sq:body -->
## Symptom

**Driven.** `sq create <type> "…" --parent ""` exits 0 and creates the item with no parent. The empty value is neither honoured nor refused — it is silently discarded, and the command reports a plain success.

Fresh `sq init --default-names --backend none`:

```
sq create bug "Empty parent probe" --author qa --parent ""
  -> created BUG-16, exit 0
sq list -a --json  ->  BUG-16 parent = None
```

Contrast, on the same squad, the update path that was fixed:

```
sq bug 17 update --parent ""
  -> error: --parent needs an item ID; use --no-parent to clear the parent
  -> exit 1
```

## Mechanism

**Read.** `_cli/_create.py` tests the option for truthiness before resolving it, so an empty string takes the no-parent branch instead of reaching the id parser. Three sites carry the identical expression:

```
src/squads/_cli/_create.py:127   resolved_parent = await resolve_item_id_any(parent, svc) if parent else None
src/squads/_cli/_create.py:381   resolved_parent = await resolve_item_id_any(parent, svc) if parent else None
src/squads/_cli/_create.py:467   resolved_parent = await resolve_item_id_any(parent, svc) if parent else None
```

(Line numbers as of `ad9c5d6`; the expression is the stable identifier, not the line.)

This is the same truthiness shape that was fixed in `_cli/_items.py`'s `update`, where both the mutual-exclusion guard and the resolution below it now test `parent is not None`. The create path was left as it was.

## Why it matters

**Inferred.** The consequence is milder than the update case — the item that gets created is a legitimate corpus state, so nothing is corrupted and no success line describes a write that did not happen. What is wrong is that a caller who supplied a parent gets an item without one and is told the command succeeded. A script or an agent interpolating an id into `--parent` that resolves to empty silently loses the hierarchy edge, and the only way to notice is to read the item back.

It also means the two write doors now disagree on the same argument: `update --parent ""` is refused, `create --parent ""` is accepted.

## Provenance

**Read.** Found and reported by the implementer during the BUG-865 fix (subtask ST4) and deliberately left out of scope, since that subtask was scoped to `_cli/_items.py`. Re-driven here on the committed fix.

## Environment

**Driven.** `squads 0.14.0`, branch `release/0.14` at `ad9c5d6`, bundled workflow spec, no `.overrides/`. Exit codes read from bare commands, never through a pipe.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-02T10:01:40Z] Olivia Lead:
  - Fix scoped as TASK-874 (fixes ref), assigned to the python dev.
    
    Standalone, not folded. It shares no file, no layer and no test with the other two 0.14
    bugs — this is CLI option parsing in the create module, one is service-layer sub-entity
    validation, the other is templates and a meta guard. Folding it in would merge unrelated
    surfaces to reduce a count.
    
    Two things confirmed while scoping, both in the task body. The three sites are still
    live and the expression is unchanged. And the fix is not a one-token flip of the ternary:
    the update door that was fixed is three cooperating pieces — the mutual-exclusion guard,
    an explicit empty/whitespace refusal with its own message, and only then the resolution.
    Flipping the ternary alone sends the empty string into the id parser and produces a
    different message than the update door gives.
    
    Asked for a shared resolution helper rather than three parallel edits, so the class
    narrows instead of waiting for the next create-shaped command to copy the nearest site.
    
    One wording detail flagged for the implementer: create has no `--no-parent`, so the
    update door's sentence points at a flag that does not exist on this door.
- [2026-09-02T14:18:40Z] Mara Tester:
  - Verified. Two fresh scratch squads (`sq init --default-names --backend none`); exit codes read from bare commands.
    
    All three create doors refuse an empty parent at exit 1 with nothing written:
    - statically-registered built-ins — swept every one: epic, feature, task, bug, decision, contract, milestone, review, guide. `--parent ""` -> exit 1 on all nine
    - `create guide` specifically -> exit 1
    - override-declared custom type — second squad carrying `.overrides/workflow.toml` declaring an `incident` type (prefix INC, own lifecycle; `sq workflow lint` "workflow spec OK"). `sq create incident "…" --parent ""` -> exit 1
    - whitespace-only `--parent "   "` -> exit 1 on every door driven (task, guide, incident)
    
    Corpus after the sweep: empty in the first squad, and only the one control item in the second. Nothing was created by any refused call — the previously-driven "exit 0 and a parentless item" is gone.
    
    Controls, to prove the refusal is the new behaviour and not a broken door:
    - `sq create task "Control no parent"` (option omitted) -> exit 0, TASK-9 created
    - `sq create incident "…" --parent TASK-999` -> exit 1, "no item with number 999 (use a full ID like TYPE-999 or bare 999)" — the id parser is still reached for a non-empty value
    
    On the wording flagged during scoping. The two doors deliberately differ after the semicolon and each names something real on its own door:
    - create: "--parent needs an item ID; omit --parent to create without a parent" — and omitting it is exactly what the control above does
    - update: "--parent needs an item ID; use --no-parent to clear the parent" — and `--no-parent` is on `update --help`, absent from `create --help`
    
    Confirmed by reading both help screens: create has `--parent` only, update has `--parent` and `--no-parent`. No door points at a flag it does not have.
    
    Nothing to flag.
<!-- sq:discussion:end -->
