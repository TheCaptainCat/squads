---
id: TASK-968
sequence_id: 968
type: task
title: 'Harden the VS Code skew canary: sq resolution and type-catalog keys'
status: Draft
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
  status: Todo
  assignee: typescript-dev
- local_id: ST2
  title: Assert the exact type-catalog key set
  status: Todo
  assignee: typescript-dev
created_at: '2026-09-29T13:29:18Z'
updated_at: '2026-09-29T13:32:20Z'
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
<!-- sq:discussion:end -->
