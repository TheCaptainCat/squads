---
id: TASK-968
sequence_id: 968
type: task
title: 'Harden the VS Code skew canary: sq resolution and type-catalog keys'
status: Done
author: tech-lead
assignee: typescript-dev
priority: medium
refs:
- BUG-949:fixes
- BUG-935:fixes
- MILE-934:targets
description: The canary resolves sq off bare PATH and floor-checks 7 of 9 type-catalog
  keys; resolve like discovery.ts and assert the exact key set
subentities:
- local_id: ST1
  title: Resolve sq like discovery.ts, not bare PATH
  status: Done
  assignee: typescript-dev
- local_id: ST2
  title: Assert the exact type-catalog key set
  status: Done
  assignee: typescript-dev
created_at: '2026-09-29T13:29:18Z'
updated_at: '2026-09-29T14:13:45Z'
---
<!-- sq:body -->
Harden the VS Code skew canary (`clients/vscode/test/canary/skewCanary.test.ts`) on both
axes it can go blind on: which `sq` binary answers, and what the type-catalog assertion
asserts. One pass, one file, one dev: the two fixes share the file and the same run.

## Subtasks

- **ST1, resolve `sq` the way the extension does (BUG-949).** Replace the bare
  `execFileSync('sq', ...)` in `isSqOnPath`/`runSq` with the extension's own resolution
  order from `src/discovery.ts` (reuse it, don't re-implement it), so the workspace `.venv`
  wins over a stale global `sq`. The run reports which `sq` it resolved and its version.
- **ST2, exact key set for `sq workflow types --json` (BUG-935).** Replace the
  `arrayContaining` floor with a named `TYPE_ENTRY_KEYS` constant checked through
  `assertExactKeys`, the pattern BUG-896 set for graph/list. All 9 keys from
  `TYPE_CATALOG_FIELDS`, including `labels` and `lifecycle`. `lifecycle` goes into the
  exact set as an unmodelled-but-required key, like `badges`/`edge_semantic`, so the
  "deliberately unmodelled" note in `types.ts` can't go stale without the canary noticing.

## Acceptance (whole task)

- Each subtask's own acceptance holds (see the subtask bodies).
- **Falsified:** for each fix, break it on purpose (put the bare-PATH call back; drop a
  key from `TYPE_ENTRY_KEYS`, or delete one from a stubbed payload) and watch the canary
  go red, then restore it. Record in the handoff what you broke and what went red.
- **Table-driven:** resolution is tested over a table of environment shapes, not one case
  per branch. Key-set checks cover missing, extra, and renamed keys.
- The client's lint, typecheck and unit suite are green. The canary is green against the
  dev tree's `sq`.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 968 add-subtask "<title>"`; track with `sq task 968 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Resolve sq like discovery.ts, not bare PATH

<!-- sq:subtask:ST1:body -->
**Bug:** BUG-949. The canary calls `execFileSync('sq', ...)` by bare name in
`isSqOnPath` and `runSq`, so the first `sq` on `PATH` answers every live test. The
extension itself only falls back to bare PATH as a last resort (`src/discovery.ts`).

**Approach**

- Resolve the command once, at suite setup, through the same resolution `discovery.ts`
  uses (explicit config, then workspace `.venv/bin/sq` or `.venv/Scripts/sq.exe`, then
  `uv run sq`, then `poetry run sq`, then bare `sq`). The workspace root is the repo root.
  Import the resolver if it can run outside the extension host. If it can't (it depends on
  `vscode`), pull the pure ordering logic out into a module both of them import. Don't
  copy it.
- `runSq`/`isSqOnPath` call the resolved `{command, args}` pair. No bare `'sq'` literal
  is left in the file.
- An env override (for example `SQ_CANARY_CMD`) may pin a binary on purpose. If you add
  one, document it in the file header.
- The suite prints the resolved command and its `--version` once, so a red run shows
  which binary produced it. Update the header docstring: the "whatever PATH resolves
  first" warning is no longer true once this lands.

**Acceptance**

- A table-driven unit test over environment shapes: `.venv` present and a different `sq`
  on PATH (the `.venv` one wins); no `.venv` but `uv` and a project (`uv run sq`); only
  poetry; only bare PATH; nothing at all (the suite skips the same way it does today).
  Cover the Windows `.venv/Scripts/sq.exe` layout as a table row.
- Falsified: put the bare-name call back, watch the ".venv wins over PATH" row go red,
  restore it.
- `rg "execFileSync\('sq'" clients/vscode/test` finds nothing.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Assert the exact type-catalog key set

<!-- sq:subtask:ST2:body -->
**Bug:** BUG-935. The `sq workflow types --json` block checks entry keys with
`expect.arrayContaining` over 7 names. The frozen Python shape (`TYPE_CATALOG_FIELDS` in
`src/squads/_cli/_workflow_cmd.py`) has 9. `labels` (read by `domain/typeLabels.ts`) and
`lifecycle` get no protection at all.

**Approach**

- Add a named `TYPE_ENTRY_KEYS` constant next to `GRAPH_NODE_KEYS`/`LIST_ROW_KEYS`,
  holding all 9 keys, and assert each entry with `assertExactKeys`, the BUG-896 pattern.
- Ruling for `lifecycle`: it goes into the exact set as an unmodelled-but-required key,
  mirroring `badges`/`edge_semantic`. The client still doesn't model it. The canary
  protects the decision already written in `types.ts`, and a comment on the constant says
  so in one line.
- Leave the other `arrayContaining` sites alone. BUG-896's assessment already closed them
  (open-array floors or frozen shapes whose floors name every key).

**Acceptance**

- The canary asserts all 9 keys exactly, on every entry of the live payload (not only the
  `bug` row).
- Table-driven over payload shapes against `assertExactKeys`: full set (passes),
  `labels` missing, `lifecycle` missing, an extra key, a renamed key (each fails).
- Falsified: drop `labels` from `TYPE_ENTRY_KEYS` or from a stubbed payload, watch it go
  red, restore it.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-29T13:32:20Z] Olivia Lead:
  - Authored from BUG-949 + BUG-935 as one canary pass (per op-pierre on BUG-949). Left in Draft for the manager to promote at dispatch. Ruled lifecycle into the exact key set as unmodelled-but-required.
- [2026-09-29T13:33:48Z] Catherine Manager:
  - Dispatched to @typescript-dev.
- [2026-09-29T13:38:33Z] Ada Typescript:
  - Both subtasks Done, both bugs Fixed. Client only (clients/vscode/test/canary).
    
    - resolveSq.ts (new): resolveCanarySq wraps resolveSqInvocation from src/discovery.ts with the repo root as workspace, SQ_CANARY_CMD as the explicit override, and points uv/poetry at the repo since the canary runs from a scratch dir. resolveSq.test.ts (new): 8-row table (venv beats PATH, Windows Scripts/sq.exe, uv, poetry, bare PATH, nothing, pin wins, dead pin falls through).
    - skewCanary.test.ts: bare sq literals gone, suite prints resolved command and version to stderr, header updated; TYPE_ENTRY_KEYS (9 keys, lifecycle as unmodelled-but-required) checked with assertExactKeys on every live entry; new table-driven self-test (full, reordered, labels missing, lifecycle missing, extra, renamed).
    
    Gates: typecheck, lint (type-aware, max-warnings 0), prettier check clean. npm test 688 passed. Canary 45 passed, resolved to .venv/bin/sq (squads 0.15.0).
    
    Falsified: returning bare sq from the resolver turned 4 table rows red (.venv wins, Windows, pin beats venv, dead pin); dropping labels from TYPE_ENTRY_KEYS turned the labels-missing row and the live types/list tests red. Both restored, green again.
- [2026-09-29T13:52:39Z] Ada Typescript:
  - REV-972 F1-F3 fixed in clients/vscode/test/canary (resolveSq.ts, resolveSq.test.ts, skewCanary.test.ts); BUG-949 back to Fixed.
    
    - F1: version probe and live tests share one execSq from a non-repo cwd; pinned uv/poetry get the --project/--directory rewrite.
    - F2: an unresolved or non-answering pin returns a failure and the live block's beforeAll throws; table row flipped to unresolved.
    - F3: a pin naming an existing file stays one path; JSON argv arrays accepted.
    
    Table now 13 rows. Falsified in place: removing the rewrite reddened 4 rows, letting a dead pin fall through reddened 2, always splitting on whitespace reddened the spaced-path row; restored. Driven live: dead pin fails, spaced-path wrapper and uv run sq pass. npm run check clean, npm test 688 passed, canary 50 passed.
- [2026-09-29T14:01:43Z] Ada Typescript:
  - REV-972 F4-F6 fixed in clients/vscode/test/canary (resolveSq.ts, resolveSq.test.ts); BUG-949 Fixed again.
    
    - F4: poetry gets --project, not --directory; a guard test runs every resolution shape and fails on any cwd-moving flag. Driven with a fake poetry that honours --directory: sq ran in the scratch dir, never the repo. Reverting to --directory reddens 4 tests (2 table rows, 2 guard rows).
    - F5: relative pin paths resolve against the process cwd (Windows absolute paths left alone). Removing that reddens the relative-pin test.
    - F6: pinned check goes through resolveSqInvocation and requires source config-command. Dropping the source check reddens the 2 dead-pin rows.
    
    npm run check clean, npm test 688 passed, canary 61 passed.
- [2026-09-29T14:10:16Z] Ada Typescript:
  - REV-972 F7 fixed in clients/vscode/test/canary; BUG-949 Fixed again.
    
    - Runtime guard: before the first write, beforeAll runs a read-only `sq list --json` from the fresh scratch dir and throws if it finds a squad there, whatever the pin's spelling.
    - Early rejection: movesCwd matches --directory/--cwd/--chdir (split or `=`) and -C (split or attached); resolveCanarySq rejects such a pin. Unit table covers 7 pin spellings.
    - afterAll no longer throws when beforeAll failed before creating the scratch dir.
    
    Driven with a fake wrapper that cds into the repo (passes the flag check): the guard threw before any write. With the guard disabled the same wrapper reached `sq init` in the repo (refused by the existing squad, nothing written). Fake uv with --directory rejected at resolution. Falsified in place: guard off, flag check off (7 red), `=` form dropped (2 red). npm run check clean, npm test 688, canary 68.
- [2026-09-29T14:13:40Z] Catherine Manager:
  - Accepted under op-pierre delegation for reviewed non-visual work: REV-972 Approved, BUG-935/949 Verified.
<!-- sq:discussion:end -->
