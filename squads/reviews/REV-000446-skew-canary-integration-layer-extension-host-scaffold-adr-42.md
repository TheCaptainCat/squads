---
id: REV-446
sequence_id: 446
type: review
title: 'Skew-canary integration layer + extension-host scaffold (ADR-427 #3)'
status: Approved
author: reviewer
refs:
- TASK-441:addresses
subentities:
- local_id: F1
  title: Skew canary is path-filtered to clients/vscode/**, so core-only drift isn't
    caught at core-PR time
  status: Fixed
  severity: low
- local_id: F2
  title: Extension-host smoke layer follow-up is noted in README only, not tracked
    as an sq item
  status: Fixed
  severity: low
created_at: '2026-07-17T09:05:56Z'
updated_at: '2026-07-17T11:38:06Z'
---
<!-- sq:body -->
Round-5 (final) review of TASK-441 — the ADR-427 #3 integration skew-canary layer (closes REV-438 F2). Scope: clients/vscode/** + the vscode-client.yml canary job.

Gate run by the reviewer:
- npm run check: clean (tsc strict + eslint --max-warnings 0 + prettier).
- npm test: 66/66 green, HERMETIC — the canary is excluded from the unit run (vitest.config.ts now excludes test/canary/**).
- npm run test:canary WITH a real sq on PATH: 6/6 green.
- npm run test:canary with sq hidden from PATH: cleanly SKIPPED (1 file / 6 tests skipped, exit 0) — a contributor without the Python toolchain still gets a green run.

VERDICT: APPROVE. Two low, non-blocking findings (both follow-up/operational, neither a defect in the implementation).

=== ISOLATION: CONFIRMED SOUND (the leak-risk the coordinator flagged) ===
The canary inits a throwaway squad via mkdtempSync(path.join(os.tmpdir(), 'squads-vscode-skew-canary-')) — NOT the repo — and every sq write (init, create epic/feature/task, body) goes through runSq(), which passes cwd: scratchDir. Since scratchDir lives under os.tmpdir() (/tmp), sq's squad-resolution walk-up can never reach the repo's own .squads.* (a different path tree entirely). The only sq call without a cwd override is the isSqOnPath() probe (sq --version), which is read-only and touches no squad. Teardown rmSync(scratchDir, recursive, force). Verified empirically after a real run: zero 'Canary' items leaked into the repo squad, squads/ has no new items, and no scratch dirs remain in /tmp. No path writes to the repo squad.

=== DRIFT DETECTION: CONFIRMED SHAPE-BASED, NOT BRITTLE ===
Each of the three surfaces (sq tree --json / sq list --json / sq show --raw) is checked twice — once against LIVE sq output, once against the committed fixture — for SHAPE, never values: (1) the adapter's own real isSqTreeNode/isSqListItem type guards (reused, not re-implemented), plus (2) Object.keys(...) expect.arrayContaining([...required keys...]), plus (3) a clean-markdown regex for --raw (H1 first line + a bold-key bullet + NO box-drawing chrome + no Rich '=== ... ===' rule). A dropped or renamed key fails on BOTH the guard (which requires title:string / is_open:boolean etc.) AND the arrayContaining presence check → red build. arrayContaining tolerates ADDED keys, which is correct (additive changes must not break the client). Tree checks flatten the whole tree so shape is asserted at every depth, not just the root. This is a genuine drift guard, not a snapshot equality that churns on unrelated data.

=== OTHER CHECKS ===
- Hermetic unit run preserved: separate vitest.canary.config.ts (own project, fileParallelism:false, 30s timeouts); test/canary excluded from npm test; describe.skipIf(!SQ_AVAILABLE) skips cleanly when sq is absent. Confirmed both directions.
- CI wiring: new 'canary' job in vscode-client.yml — checkout, setup-python/uv, 'uv sync --frozen' with working-directory: . (the one legit Python touch, to provision a real sq), puts .venv/bin on PATH, sanity 'sq --version', then npm ci + npm run test:canary. The check/test jobs and the Python test.yml are untouched; still path-filtered to clients/vscode/**. Sound.
- Exported guards: making isSqTreeNode/isSqListItem public in sqAdapter.ts is REASONABLE, not over-exposure — they are pure stateless predicates, and reusing the exact runtime contract in the canary (vs a parallel hand-rolled check that could itself drift) is precisely the point; the export carries a docstring saying so.
- Extension-host stub: @vscode/test-electron scaffold (runTest.ts + suite/index.ts) present, honestly a no-op (not a fake pass), not wired to any script/CI, documented in README as a follow-up needing Xvfb + a compiled out/. Acceptable 0.10 deferral per the task's own scoping and my REV-438 ruling (lower priority). See F2.

Overall: APPROVE. Clean, careful implementation; the skew canary is a real cross-language drift guard and closes REV-438 F2.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 446 add-finding "…" --severity medium`; track with `sq review 446 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Fixed |  | Skew canary is path-filtered to clients/vscode/**, so core-only drift isn't caught at core-PR time |
| F2 | 🟢 low | Fixed |  | Extension-host smoke layer follow-up is noted in README only, not tracked as an sq item |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Skew canary is path-filtered to clients/vscode/**, so core-only drift isn't caught at core-PR time

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
The canary job lives in vscode-client.yml, which triggers only on clients/vscode/** changes. So a CORE-only PR that alters the sq tree/list --json or show --raw shape does NOT run the skew canary — the drift is caught only on the next PR that happens to touch clients/vscode/**. This is consistent with ADR-427 #3's accepted isolation ('cross-language coupling is caught only by the integration skew canary, by design', dev-time lanes kept non-cross-blocking), and TASK-441 wired the canary exactly where the ADR specified — so it is NOT a defect in this implementation. Recording it as an operational coverage caveat: the guard's effectiveness depends on client-side churn to fire. Optional mitigation for the team to weigh (out of scope here): add a scheduled/nightly canary run, or also trigger it on the core --json/--raw surface files, so core-introduced drift is caught promptly rather than latently. Low/informational.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-07-17T09:42:17Z] Ada Typescript:
  - Fixed: added a nightly schedule trigger (cron) to vscode-client.yml. GitHub only applies push/pull_request path filters -- schedule ignores them entirely, so the nightly tick runs the whole workflow regardless of what changed. check/test/e2e opt out on the schedule event (they gate clients/vscode's own dev-time surface, nothing to re-check nightly); canary has no such guard, so it alone runs every night against a real sq, catching core-only --json/--raw drift within at most a day. Chose this over adding src/squads/** to the workflow's own path filters because that would also re-trigger check/test on core-only PRs, contradicting the file's own documented isolation invariant ('a Python-only change never triggers this workflow at all') -- schedule achieves the coverage without touching that guarantee. YAML validated with PyYAML (parses, job/on keys as expected).
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Extension-host smoke layer follow-up is noted in README only, not tracked as an sq item

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
ADR-427 #3's third layer (a @vscode/test-electron extension-host smoke test) is correctly deferred for 0.10 — the scaffold is present and honest (a no-op run(), not a fake pass), and it's documented in README.md + the code as needing Xvfb + a compiled out/. That deferral is acceptable and matches my REV-438 ruling (lower priority than the skew canary). The gap: the follow-up is captured only as a README/handoff note, not as a tracked sq work item, so ADR-427 #3's third layer could quietly fall off the backlog. Recommend creating a tracked task for 'wire the @vscode/test-electron extension-host smoke test (headless Xvfb + out/ build)' so the remaining ADR layer stays visible. Low; tracking hygiene, not a code defect.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-07-17T09:42:07Z] Ada Typescript:
  - Fixed: real Extension Development Host smoke test wired (runTest.ts + suite/index.ts), test:e2e npm script, new e2e CI job in vscode-client.yml (xvfb-run, after npm ci + compile, skipped on the nightly schedule tick). Asserts activate()+isActive, squadsTree.focus, and opening a squads: preview doesn't throw. Also fixed an incidental bug found while wiring: package.json main pointed at out/extension.js but tsc emits out/src/extension.js (rootDir '.') -- corrected, else the extension would never load for real. Verified npm run check/test green; ran the compiled script locally and confirmed it gets past all path/module resolution into the real VS Code download step before failing on network/no-display -- actual execution is CI-only.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-17T11:38:06Z] Paul Reviewer:
  - F1 + F2 both Fixed in the close-out batch (reviewed in REV-447, APPROVE). F1: vscode-client.yml gained a nightly schedule cron that runs only the canary job (check/test/e2e gated off the schedule tick) — core-only surface drift is now caught within a day, the exact mitigation F1 proposed, with no path filter that would pull Python-only PRs into check/test. F2: the extension-host smoke layer is now fully implemented (test/extensionHost/runTest.ts + suite/index.ts: activate, squadsTree.focus, squads: preview open) and wired to npm run test:e2e + an xvfb e2e CI job — no longer a README-only stub.
<!-- sq:discussion:end -->
