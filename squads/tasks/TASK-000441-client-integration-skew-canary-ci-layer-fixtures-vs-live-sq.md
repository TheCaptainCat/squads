---
id: TASK-441
sequence_id: 441
type: task
title: 'Client: integration skew-canary CI layer (fixtures vs live sq)'
status: Draft
parent: FEAT-100
author: tech-lead
assignee: typescript-dev
refs:
- ADR-427:addresses
- REV-438:addresses
- TASK-440:depends-on
description: 'ADR-427 #3 skew canary: real sq --json/show --raw vs committed fixtures
  as own npm script, wired into CI lane'
created_at: '2026-07-17T07:45:20Z'
updated_at: '2026-07-17T07:45:39Z'
---
<!-- sq:body -->
## Owner

Client TypeScript work — intended for **Ada Typescript** (typescript-dev).
Authored here for scope/traceability; the tech lead is not implementing it.

## Goal

Close REV-438 F2 (medium): the CI lane today runs only the unit test layer.
Implement ADR-427 #3's **integration skew-canary** test layer — the ADR's
designated mechanism for catching cross-language contract drift — as its own npm
script, and wire it into the CI lane. **Depends on the client-adoption task**, so
the skew canary verifies the recaptured, enriched fixtures against live output.

## Why the skew canary is the priority (per REV-438 ruling)

The committed tree/list/show-raw fixtures are captured snapshots of the frozen
`sq … --json`/`sq show --raw` shapes. Nothing currently re-verifies them against
live `sq` output, so a core-side shape change (even an additive one) could drift
the fixtures silently. The skew canary is the guard: run real `sq` and assert the
committed fixtures still match the live shapes.

## Scope

- **Integration skew-canary layer.** A thin test suite that, against a scratch
  squad (init a throwaway squad in a temp dir), runs the real surfaces the client
  depends on — `sq tree --json`, `sq list --json`, `sq show <id> --raw` — and
  asserts the **committed fixtures still match the live shapes** (key set / types /
  structure; not brittle value-for-value). Skippable when `sq` is absent (mirrors
  ADR-427 #3: "skippable when `sq` is absent").
- Expose it as **its own npm script** (e.g. a `test:integration` /
  `test:skew` script distinct from the unit `test`).
- **Wire it into the CI lane** — the `clients/vscode` workflow
  (`.github/workflows/vscode-client.yml`) runs the skew-canary job/step in
  addition to the unit layer. It must have a real `sq` available in that job
  (the repo's `uv`-provisioned `sq`), since it shells out.
- **Extension-host smoke layer (lower priority — stub + note).** ADR-427 #3's
  third layer (`@vscode/test-electron` smoke: tree loads, preview opens) is a
  lower-priority stub for this task: note it in the body/handoff as a known gap
  with a placeholder script, rather than fully implementing it. The skew canary
  is the deliverable here.

## Required in this task

- New npm script for the skew canary; documented in `clients/vscode/README` (or
  the package's test docs) as how to run it locally and that it needs `sq`.
- CI lane updated to invoke it; the job provisions `sq`.
- Keep the strict gate green; no item-ID leakage (hygiene guard).

## Acceptance criteria

- `npm run <skew script>` runs real `sq … --json`/`sq show --raw` against a
  scratch squad and fails if a committed fixture's shape drifts from live output.
- Skippable/graceful when `sq` is unavailable locally.
- CI lane runs the skew canary with a real `sq` present.
- Extension-host smoke layer noted as a tracked lower-priority stub.

## Addresses

REV-438 F2 (medium); implements ADR-427 #3's integration test layer.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 441 add-subtask "<title>"`; track with `sq task 441 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
