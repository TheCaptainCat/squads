---
id: TASK-432
sequence_id: 432
type: task
title: Dev-time TS CI lane for clients/vscode (strict, non-gating for core)
status: Draft
parent: FEAT-100
author: tech-lead
assignee: devops
refs:
- ADR-427:addresses
created_at: '2026-07-16T13:51:30Z'
updated_at: '2026-07-16T13:55:58Z'
---
<!-- sq:body -->
## Owner

Devops-flavored — intended for **Hugo Ops** (devops). Authored here for scope/traceability; the tech lead is not implementing it.

## Goal

A dev-time CI lane that runs the TypeScript gate for `clients/vscode/`, keyed on `clients/vscode/**` paths, independent of and **non-gating for** the Python core.

## Scope

- A **separate workflow/job keyed on `clients/vscode/**`** that runs the TS gate: `npm run check` (= `tsc --noEmit` strict + `typescript-eslint` strict-type-checked/stylistic-type-checked at zero warnings + Prettier `--check`) plus the package's test layers.
- Runs the three test layers from ADR-427 #3: **unit** (fixtures, no `sq`), **thin integration** skew canary (real `sq` against a scratch squad; skippable when `sq` absent), and the **extension-host** smoke test (`@vscode/test-electron`).
- The lane is **independent of the Python gate**: a red TS job never blocks a Python-only change and a red Python job never blocks a TS-only change. Cross-language coupling is caught only by the integration skew canary, by design.

## Enforcement nuance (state this explicitly)

Within TypeScript the bar is **strict and blocking, not advisory**: the TS gate is a **hard must-pass for any change touching `clients/vscode/`** — same standing as the Python gate has for Python changes. Parity target (must match the foundation task's toolchain):
- `tsc --noEmit` strict + `noUncheckedIndexedAccess`/`noImplicitReturns`/`noImplicitOverride`/`noFallthroughCasesInSwitch`/`noUnusedLocals`/`noUnusedParameters`/`exactOptionalPropertyTypes`/`isolatedModules`.
- ESLint `typescript-eslint` strict-type-checked + stylistic-type-checked, `complexity` ≤ 12, `max-params` ≤ 8, import ordering, bugbear/simplify rules, `--max-warnings 0`.
- Prettier `--check`.

The cross-language **isolation** (ADR #1/#3) and the within-language **strictness** are two separate things: isolation = a TS failure doesn't block Python and vice versa; strictness = within TS the gate is hard/blocking.

## Acceptance criteria

- A CI workflow/job triggers on `clients/vscode/**` changes and runs `npm run check` + all three test layers.
- The TS lane blocks merges of changes touching `clients/vscode/`; it does not run/block on Python-only changes, and the Python gate does not run/block on TS-only changes.
- The integration skew canary is skippable/gated on `sq` presence so the unit path is green with no binary.
- Zero-warnings enforcement is active (`--max-warnings 0`); a lint warning fails the job.

## ADR-427 constraints this task must honor

- #1/#3 Dev-time gate isolation: separate lane keyed on `clients/vscode/**`, non-gating for the Python core (and vice versa).
- #3 The exact three test layers; skew canary is the only cross-language coupling check.
- This is the **dev-time** lane only — distinct from the unified release pipeline (see the release-bundle task).

## Implementer note

sq/ticket IDs must not appear in source or CI file names — name by behavior.

Implements FEAT-100 (dev-time CI enablement, spans US1–US3). Addresses ADR-427.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 432 add-subtask "<title>"`; track with `sq task 432 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
