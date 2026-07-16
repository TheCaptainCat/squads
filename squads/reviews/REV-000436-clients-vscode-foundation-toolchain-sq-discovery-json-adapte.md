---
id: REV-436
sequence_id: 436
type: review
title: 'clients/vscode foundation: toolchain, sq discovery, --json adapter'
status: Approved
author: reviewer
refs:
- TASK-428:addresses
subentities:
- local_id: F1
  title: Squad item IDs embedded in production source and README
  status: Fixed
  severity: medium
- local_id: F2
  title: No hygiene enforcement covers clients/ going forward
  status: Fixed
  severity: low
- local_id: F3
  title: usage-error argv omits the resolved command, weakening the diagnostic
  status: Fixed
  severity: low
- local_id: F4
  title: squads.command with an absolute-path first element never resolves
  status: Fixed
  severity: low
created_at: '2026-07-16T18:25:10Z'
updated_at: '2026-07-16T18:33:18Z'
---
<!-- sq:body -->
Independent review of TASK-428 — the clients/vscode/ foundation (isolated TS toolchain, sq discovery module, sq --json adapter, committed fixtures). Scope: clients/vscode/** plus the one-line pyproject.toml clients/ exclusion only; concurrent src/tests work (TASK-434) explicitly excluded.

Gate run by the reviewer: `npm run check` clean (tsc --noEmit + eslint --max-warnings 0 + prettier --check all pass) and `npm test` 28/28 green.

Assessment by dimension:
- Discovery (src/discovery.ts): resolution order matches ADR-427 #2 exactly (config-sq-path > config-command > venv incl. Windows Scripts/sq.exe > uv+project > poetry+project > bare PATH), first-that-works-wins, pure/injectable, cached-on-success with invalidate() re-probe, 'none found' surfaces the tried order. Correct.
- Adapter (src/sqAdapter.ts + processRunner.ts): exit-code mapping complete (2 usage / 3 check / 1+other runtime, schema-skew surfaced verbatim) plus parse-error + spawn-error; every path returns a typed outcome, nothing throws. execFile (no shell) — no injection surface. Shells out only; no .claude/ or .squads.json access (verified). Correct.
- Strict-gate parity: tsconfig carries strict + all 8 strict-plus flags; ESLint is typescript-eslint strictTypeChecked + stylisticTypeChecked (type-aware via projectService) with complexity<=12, max-params<=8, zero-warnings; Prettier checked; single npm run check gate. Genuine parity with the Python core.
- Fixtures: tree.json / list.json match live sq output shapes (verified against this repo). show --raw fixture correctly absent (deferred to TASK-434). Coverage is thorough across discovery precedence/caching and all adapter exit-code branches.
- Isolation: ruff extend-exclude + pyright exclude both set for clients/ (belt-and-suspenders alongside include); Python gate confirmed not to walk clients/. Correct.

Verdict: changes-requested — narrowly, on item-ID hygiene (finding 1). All architecture, logic, tests, and parity are sound; the rest is a fast cleanup.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 436 add-finding "…" --severity medium`; track with `sq review 436 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Fixed |  | Squad item IDs embedded in production source and README |
| F2 | 🟢 low | Fixed |  | No hygiene enforcement covers clients/ going forward |
| F3 | 🟢 low | Fixed |  | usage-error argv omits the resolved command, weakening the diagnostic |
| F4 | 🟢 low | Fixed |  | squads.command with an absolute-path first element never resolves |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Squad item IDs embedded in production source and README

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
The task's implementer note is explicit: 'sq/ticket IDs must not appear in source (this task's ID included).' Yet src/extension.ts:4 carries 'Foundation only (TASK-428)', and ADR-427 is cited in comments in src/discovery.ts (lines 4, 106), src/sqAdapter.ts:3, eslint.config.mjs:2, and throughout README.md.

This is the same class the core's own hygiene gate (tests/meta/test_source_and_new_test_tree_have_no_stray_ticket_references.py) forbids in src/ and docs/ full-text — the pattern matches ADR-/TASK-/EPIC- alike, and the core keeps its src/docs clean of them. Parity says clients/vscode should hold the same line. It is not caught automatically here only because that scan is scoped to src/docs/tests and does not walk clients/ (see separate finding).

Not a violation: the EPIC-99 / FEAT-100 literals in test/sqAdapter.test.ts are assertion data derived from the real captured fixture — that mirrors the same gate's deliberate test-assertion-data carve-out and is fine.

Fix: remove TASK-428 and the ADR-427 citations from source comments and README prose (describe the design directly); keep the ticket/ADR pointer in the sq task / PR only.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-07-16T18:31:45Z] Ada Typescript:
  - Removed TASK-428/ADR-427 ID citations from src/extension.ts, src/discovery.ts (x2), src/sqAdapter.ts, eslint.config.mjs, and README.md; reworded to describe the design directly. EPIC-99/FEAT-100 fixture-assertion literals in test/sqAdapter.test.ts left untouched per the carve-out.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — No hygiene enforcement covers clients/ going forward

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
The no-ticket-IDs rule (and any other src-hygiene invariant) has no automated guard under clients/: the Python meta scan is scoped to src/docs/tests by design, and the TS gate has no equivalent rule. So finding 1's cleanup can silently regress in future TS work with nothing to catch it.

Recommend a TS-side guard — an ESLint no-restricted-syntax/regex rule or a small vitest that greps src for the item-ID pattern — wired into npm run check, and/or extending the scan's remit in the dev-time TS CI lane (TASK-432). Flagging for tech-lead/devops; not blocking this task.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-07-16T18:31:46Z] Ada Typescript:
  - Added test/hygiene.test.ts: scans src/** + eslint.config.mjs/tsconfig.json/package.json/vitest.config.ts/.prettierrc.json/README.md for ticket-ID tokens, zero-tolerance; test/** (fixtures + assertion data) is out of scope, mirroring the core gate's carve-out.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — usage-error argv omits the resolved command, weakening the diagnostic

<!-- sq:finding:F3:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
On exit 2 the adapter returns { kind: 'usage-error', argv } so 'our bug' can be logged. But buildArgv returns [...invocation.args, ...subcommandArgs] and drops invocation.command. For a venv invocation (args: []) the logged argv is e.g. ['tree','EPIC-99','--json'] — the sq binary itself is gone; for uv it is ['run','sq',...] — 'uv' is gone. The logged line can't be replayed to reproduce the usage bug.

Suggest including invocation.command in the argv captured for the usage-error path (e.g. [command, ...args, ...subcommandArgs]) so the diagnostic is a full, runnable command line.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-07-16T18:31:47Z] Ada Typescript:
  - usage-error argv now includes the resolved invocation.command (e.g. ['/venv/bin/sq','tree',...] or ['uv','run','sq','tree',...]) so the logged line is directly replayable.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — squads.command with an absolute-path first element never resolves

<!-- sq:finding:F4:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
tryConfigCommand (src/discovery.ts) validates command[0] via env.isOnPath(first), which only PATH-scans a bare name. If an operator sets squads.command to e.g. ['/opt/py/bin/python','-m','squads'], isOnPath('/opt/py/bin/python') scans PATH dirs for that literal and fails, so config-command is silently skipped and discovery falls through to venv/uv/... — surprising for an explicit override.

Either accept an absolute command[0] (fall back to fileExists when it looks like a path), or document that absolute binaries must go through squads.sqPath and command is for PATH-resolved prefixes only. Low-impact edge; config-command with a bare name (the documented 'uv','run','sq' shape) works correctly.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-07-16T18:31:48Z] Ada Typescript:
  - tryConfigCommand now checks env.fileExists for a path-shaped command[0] (contains a slash) and env.isOnPath for a bare name; absolute-path overrides now resolve instead of being silently skipped.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
