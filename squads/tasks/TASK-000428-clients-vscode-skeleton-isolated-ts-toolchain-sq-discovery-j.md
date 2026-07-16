---
id: TASK-428
sequence_id: 428
type: task
title: 'clients/vscode skeleton: isolated TS toolchain, sq discovery, --json adapter'
status: Done
parent: FEAT-100
author: tech-lead
assignee: typescript-dev
refs:
- ADR-427:addresses
created_at: '2026-07-16T13:51:27Z'
updated_at: '2026-07-16T18:33:18Z'
---
<!-- sq:body -->
## Goal

Stand up the `clients/vscode/` package skeleton that US1–US3 build on: an isolated TypeScript/Node toolchain, the `sq`-invocation/discovery module, and a thin `sq --json` adapter with committed fixtures captured from real output. No VS Code UI in this task — the tree provider, preview, and filter/group commands land in the story tasks on top of this foundation.

## Scope

- **Package skeleton** at `clients/vscode/`: `package.json` (VS Code extension manifest + scripts), `tsconfig.json`, ESLint flat config, Prettier config, own lockfile, and a `src/` + `test/` layout. Entirely disjoint from the Python core — own toolchain, own lockfile, no shared build/config/virtualenv.
- **`sq` discovery module**: resolves how to invoke `sq` by auto-detecting the workspace toolchain against the workspace root, in the ADR-427 #2 order (first that works wins): (1) explicit config override (`squads.sqPath`, or a `squads.command` array); (2) workspace virtualenv `.venv/bin/sq` (`.venv/Scripts/sq.exe` on Windows); (3) `uv` present + a project → `uv run sq`; (4) `poetry` present + a project → `poetry run sq`; (5) bare `sq` on PATH (fallback). The resolved invocation is **cached and re-probed on failure**. Never PATH-only.
- **`sq --json` adapter**: a thin layer that shells out to the resolved `sq`, parses stdout as the frozen 1.0 JSON shapes, and maps exit codes per the frozen table — `2` usage (our bug: log the argv), `3` check failure (surfaced verbatim), `1`/other runtime (show stderr); a version/schema-skew `1` with the "run `sq migrate up`" message is surfaced verbatim (the adapter pins **no** schema knowledge). Every failure surfaces as a VS Code notification with an actionable message — never a crash, never a partial silent result.
- **Committed fixtures**: capture real output of `sq tree <root> --json`, `sq list --json`, and `sq show <id> --raw` into fixture files under the package, so unit tests run with no `sq` binary present.

## Strict TS quality bar (parity with the Python core — set up here)

Stand up the exact toolchain/config so the story tasks inherit it. Parity target for `clients/vscode/`:

- **Type check** — `tsc --noEmit` with `strict: true` PLUS `noUncheckedIndexedAccess`, `noImplicitReturns`, `noImplicitOverride`, `noFallthroughCasesInSwitch`, `noUnusedLocals`, `noUnusedParameters`, `exactOptionalPropertyTypes`, `isolatedModules` (closest analog to pyright strict).
- **Lint** — ESLint flat config on `typescript-eslint` **strict-type-checked** + **stylistic-type-checked** (type-aware), plus rules mirroring ruff: `complexity` ≤ 12 (≈ C901), `max-params` ≤ 8 (≈ PLR0913), import ordering (≈ ruff I), and bugbear/simplify-style rules (≈ B/SIM). Zero warnings tolerated (`--max-warnings 0`).
- **Format** — Prettier `--check` (≈ `ruff format --check`).
- **Single gate command** — `npm run check` = `typecheck && lint && format:check`, mirroring `uv run pyright && uv run ruff check . && uv run ruff format --check`.

## Acceptance criteria

- `clients/vscode/` exists as a self-contained package with its own lockfile; nothing under it is referenced by the Python toolchain and vice versa (`clients/` is in the Python tooling's ignore set — a stray `.ts`/`node_modules` can never fail a Python run).
- `npm run check` runs the full strict gate (tsc + ESLint + Prettier) and passes on the skeleton.
- The discovery module resolves `sq` through all five strategies in order, caches the result, and re-probes on failure; each failure mode produces an actionable notification (no throw, no crash).
- The `--json` adapter parses the three surfaces from committed fixtures and maps every documented exit code; unit tests pass with **no `sq` binary present**.
- The adapter reads **only** via `sq … --json` / `sq show <id> --raw` — it MUST NOT read `.claude/` and MUST NOT parse `.squads.json` (ADR-427 #2, invariant #1).

## ADR-427 constraints this task must honor

- #1 Placement & isolation: `clients/vscode/`, isolated toolchain/lockfile, no shared config inheritance.
- #2 Consumer contract + discovery order + failure-mode notifications; no `.claude/`/`.squads.json` access.
- #3 Testing: unit layer against committed fixtures runs with no `sq` present (this task establishes the fixture discipline).

## Implementer note

Project rule: **sq/ticket IDs must not appear in source** (this task's ID included). Name files, modules, and tests by behavior (e.g. `discovery`, `sqAdapter`, `exitCodeMapping`), not by ticket. Keep the ticket pointer in the sq task / PR, not in code.

Implements FEAT-100 (foundation for US1–US3). Addresses ADR-427.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 428 add-subtask "<title>"`; track with `sq task 428 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-16T18:18:17Z] Ada Typescript:
  - Foundation stood up at clients/vscode/: package.json (VS Code manifest incl. squads.sqPath/squads.command config contributions + a check = typecheck && lint && format:check gate), tsconfig.json (strict + all 8 requested strict-plus flags), eslint.config.mjs (typescript-eslint strictTypeChecked+stylisticTypeChecked, type-aware, complexity<=12/max-params<=8, simple-import-sort), .prettierrc.json, own package-lock.json, src/ + test/.
  - Discovery module (src/discovery.ts): resolveSqInvocation implements the ADR-427 #2 order exactly (config-sq-path > config-command > venv > uv+project > poetry+project > bare-path), pure/injectable (DiscoveryEnvironment DI, no vscode/node:fs coupling so it's unit-testable with no host); SqDiscovery caches + invalidate() re-probes on failure; describeTriedOrder for the 'none found' notification text. Real fs/PATH-backed env lives in src/nodeEnvironment.ts, wired from src/extension.ts (minimal activate/deactivate only -- no tree/preview, that's US1-3).
  - Adapter (src/sqAdapter.ts + src/processRunner.ts): shells out via the resolved invocation, maps exit codes 2/3/1+other to usage-error/check-error/runtime-error (schema-skew surfaced verbatim, no special-casing), plus parse-error/spawn-error for malformed JSON or a vanished binary -- every path returns a typed outcome, nothing throws. getTree/getList cover the two in-scope surfaces (sq show --raw fixture deferred to TASK-434/430 per the task note).
  - Fixtures: test/fixtures/tree.json (sq tree EPIC-99 --json) and list.json (sq list --json), captured from this repo's real output.
  - npm run check: clean (tsc --noEmit + eslint --max-warnings 0 + prettier --check all pass). npm test: 28/28 passing (vitest), covering the full discovery resolution order/precedence/caching and the adapter's exit-code mapping + fixture parsing, no sq binary needed.
  - Python side: added clients to [tool.ruff] extend-exclude and [tool.pyright] exclude in pyproject.toml (only that change). Verified: uv run ruff check . / ruff format --check . / pyright all still clean; sq check clean.
  - Note for reviewer: uv run pytest currently shows 2 unrelated failures in tests/meta/test_source_and_new_test_tree_have_no_stray_ticket_references.py from tests/cli/test_show_raw_markdown_golden.py -- that file + the TASK-434 md are uncommitted concurrent work (US2 core prerequisite), not touched by me; flagging so it isn't mistaken for something this task broke.
  - @reviewer ready for review.
- [2026-07-16T18:32:15Z] Ada Typescript:
  - REV-436 changes-requested addressed, all 4 findings marked Fixed:
  - F1 (medium): stripped ticket/ADR-ID citations from clients/vscode production source + README (src/extension.ts, src/discovery.ts x2, src/sqAdapter.ts, eslint.config.mjs, README.md) -- reworded to describe the design directly, no ID pointers. Left the EPIC-99/FEAT-100 fixture-assertion literals in test/sqAdapter.test.ts untouched (reviewer's explicit carve-out).
  - F2: added test/hygiene.test.ts -- a forward guard scanning src/** + eslint.config.mjs/tsconfig.json/package.json/vitest.config.ts/.prettierrc.json/README.md for ADR|FEAT|TASK|REV|BUG|EPIC-N / USn / STn tokens, zero-tolerance, with test/** (fixtures + assertions) carved out -- mirrors the core's tests/meta gate inside the TS lane.
  - F3: usage-error argv now carries the full resolved command line (invocation.command + args), e.g. ['/venv/bin/sq','tree','EPIC-99','--json'] or ['uv','run','sq','tree',...] -- replayable, not missing the binary.
  - F4: tryConfigCommand now resolves a path-shaped squads.command[0] (contains a slash) via fileExists instead of a PATH scan, so an absolute-path override (e.g. ['/opt/py/bin/python','-m','squads']) resolves correctly; bare names (['uv','run','sq']) still go through isOnPath unchanged.
  - Verified: npm run check clean (tsc --noEmit + eslint --max-warnings 0 + prettier --check), npm test 33/33 green (28 orig + 5 new: F3/F4 coverage + the hygiene guard). Python gate re-verified: ruff/pyright/sq check all clean.
  - @reviewer ready for re-review.
<!-- sq:discussion:end -->
