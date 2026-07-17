---
id: REV-447
sequence_id: 447
type: review
title: 'Close-out batch: merged publish.yml VSIX release + VSIX packaging + e2e smoke
  + skill mermaid split'
status: Approved
author: reviewer
refs:
- TASK-433:addresses
- TASK-435:addresses
subentities:
- local_id: F1
  title: publish.yml step name still carries an ADR ref missed by the workflow-ref
    sweep
  status: Fixed
  severity: low
- local_id: F2
  title: engines.vscode floor raised to ^1.125 to fix the vsce mismatch — wrong knob
  status: Fixed
  severity: low
- local_id: F3
  title: Version guard protects only the VSIX job, not the PyPI publish
  status: Open
  severity: low
created_at: '2026-07-17T11:35:00Z'
updated_at: '2026-07-17T11:46:04Z'
---
<!-- sq:body -->
Final close-out review (TASK-433 release/packaging + TASK-435 skill mermaid split, plus the extension-host e2e smoke folded into this batch). Reviewed the full uncommitted diff (git diff HEAD + untracked). Scope held to code/CI + templates; agent-memory and sq-bookkeeping .md churn ignored.

Gates run by the reviewer (Python suite already green per main loop):
- npm run check: clean. npm test: 66/66. npm run test:canary (real sq on PATH): 6/6.
- npx @vscode/vsce ls: ships EXACTLY package.json + README.md + resources/squads-icon-mono.svg + out/src/**.js (incl. out/src/extension.js) — NO tests, sources, unused icons, configs, out/test, or .map files.
- uv run sq check: clean.

VERDICT: APPROVE (all areas). Three low findings, none blocking. This batch also resolves REV-446 F1+F2 and REV-443 F1 (see below).

=== 1. publish.yml (merged) — APPROVE ===
- Trigger "release: types: [published]" — correct for Pierre's manual-release flow (the Release UI creates the tag; the release already exists when this runs, so the vsix job uploads directly). Matches op-pierre's own TASK-433 comment.
- Per-job permissions correct + least-privilege: the publish job keeps id-token:write + contents:read (PyPI trusted publishing, environment: pypi) and its PyPI steps are byte-identical to before (the diff adds only the trigger change, a job name, and the per-job permissions block); the vsix job gets contents:write ONLY, no id-token, so it can never touch trusted publishing. The workflow-level permissions block was removed so the job-level blocks fully replace (not merge). Correct.
- Version guard (vsix job) fails unless github.event.release.tag_name == "v" + pyproject version. VSIX attached via first-party "gh release upload ... --clobber". softprops dropped, so REV-443 F2 is moot. release.yml deleted.
- No way the PyPI publish breaks: the publish job is unchanged, uses trusted publishing, builds from pyproject, and runs in parallel (no needs:) independent of the vsix job — a VSIX failure can neither block nor break it. See F3 (guard asymmetry, informational).

=== 2. VSIX packaging — APPROVE ===
- main = ./out/src/extension.js (tsconfig rootDir "." emits src under out/src) — matches where tsc emits; vsce ls confirms the entry point ships. .vscodeignore excludes src, test, out/test, toolchain + compiled-config mirrors, lockfile, node_modules, .map files, and the 5 unused icon variants; the comments are careful about vsce/minimatch root-anchoring (out/test listed separately). Verified clean via vsce ls.
- engines.vscode ^1.85 -> ^1.125: see F2 — my call is this is the wrong knob.

=== 3. Extension-host e2e smoke — APPROVE ===
- runTest.ts launches a real host with a throwaway /tmp workspace (--disable-extensions), cleans up in finally, and propagates failure via process.exitCode. suite/index.ts is a genuine smoke: getExtension(TheCaptainCat.squads-vscode) -> activate() -> assert isActive -> execute squadsTree.focus (proves the view contribution loaded) -> open squads:/SMOKE-0 and assert the scheme (exercises the provider, no sq needed). Wired to "npm run test:e2e" + the e2e CI job (xvfb-run). CI-only-runnable (no display in the sandbox), honestly documented. Resolves REV-446 F2 — the extension-host layer is now implemented + wired, not a stub.

=== 4. Mermaid split (TASK-435) — APPROVE, no findings ===
- The for_skill flag is set ONLY in squads_skill.md.j2 and read ONLY in workflow.md.j2 (guarded by "if not for_skill | default(false)"). No leak: sq workflow emits 7 stateDiagram-v2 (live-verified) and its golden workflow_cheatsheet.txt is UNCHANGED in this diff; AGENTS.md's agents_md_section.txt golden (which contains stateDiagram) is likewise UNCHANGED — byte-proof both render paths are unaffected; the CLAUDE.md section does not include workflow.md.j2 at all. The skill has 0 diagrams and keeps the hierarchy flowchart + lifecycle table. Test-covered (new skill test + the unchanged workflow/agents goldens). CHANGELOG note present.
- The nightly schedule cron added to vscode-client.yml (runs only the canary job; check/test/e2e skip via "if: github.event_name != 'schedule'") is the exact mitigation I recommended and closes REV-446 F1 — core-only surface drift is now caught within a day, with no path filter that would pull Python-only PRs into check/test.

=== 5. sq mine --json is_open — APPROVE, no findings ===
- Additive is_open via spec.is_open(i.status), spec-driven, consistent with list (line 410) and tree. Hoists spec = get_active_spec() once. Resolves REV-443 F1 (mine was the un-enriched sibling surface).

=== 6. Icon — APPROVE, no findings ===
- activity-bar -> resources/squads-icon-mono.svg (fill=currentColor, theme-tintable); the placeholder activity-bar-icon.svg is deleted. package.json + .vscodeignore reference only the mono variant.

=== 7. Workflow comment hygiene ===
- test.yml and vscode-client.yml were both swept clean of item refs this round (test.yml's sole change is dropping "(REV-438 F3)"; vscode-client.yml dropped "(ADR-427 #1/#3)"). One ref slipped through — see F1.

Overall: APPROVE. Clean, careful close-out; the three findings are all low/nit.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 447 add-finding "…" --severity medium`; track with `sq review 447 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Fixed |  | publish.yml step name still carries an ADR ref missed by the workflow-ref sweep |
| F2 | 🟢 low | Fixed |  | engines.vscode floor raised to ^1.125 to fix the vsce mismatch — wrong knob |
| F3 | 🟢 low | Open |  | Version guard protects only the VSIX job, not the PyPI publish |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — publish.yml step name still carries an ADR ref missed by the workflow-ref sweep

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
This round deliberately swept squad-item refs out of the workflow files — test.yml's ONLY change is dropping '(REV-438 F3)' from a comment, and vscode-client.yml dropped '(ADR-427 #1/#3)'. But publish.yml line 44 still reads: 'name: read core version (unified version, ADR-427 #5)'. It is in a step NAME (surfaced in the Actions UI/logs), the one ref the sweep missed. For consistency with the sweep (and workflow-comment-hygiene check), drop the ADR ref -> 'read core version (unified version)'. Low/nit; no functional impact.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — engines.vscode floor raised to ^1.125 to fix the vsce mismatch — wrong knob

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
package.json bumped engines.vscode ^1.85.0 -> ^1.125.0 to clear vsce's refusal-to-package when engines.vscode is lower than @types/vscode (^1.125). It works and vsce packages, but it is the wrong side to move: the extension uses only long-stable VS Code APIs (TreeDataProvider, TextDocumentContentProvider, window.showErrorMessage, commands, workspace config, ThemeIcon/ThemeColor, markdown.showPreview) — none newer than 1.85 — so raising the DECLARED minimum to 1.125 overstates the extension's real requirement and needlessly narrows the install floor. The principled fix is the opposite: LOWER @types/vscode to the true minimum (^1.85) so the two agree AND typing against the real floor would flag any accidental use of a newer API. In practice ~everyone is past 1.125 by now so the user impact is negligible, but the contract is dishonest. This was a real pre-existing mismatch — recommend a tracked item to reconcile engines.vscode and @types/vscode at the intended minimum. Low.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-07-17T11:44:07Z] Operator:
  - Reverted engines.vscode to ^1.85.0 and lowered @types/vscode to match (^1.85.0, resolved 1.85.0). npm run check stayed green typed against the 1.85 floor -- confirms no post-1.85 API usage. npm test 66/66, vsce ls unchanged (entry point + mono icon, no tests/sources).
- [2026-07-17T11:44:33Z] Ada Typescript:
  - (re-attributing prior note as myself) Fixed: engines.vscode reverted to ^1.85.0, @types/vscode lowered to ^1.85.0 (resolved 1.85.0); tsc check green at that floor.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Version guard protects only the VSIX job, not the PyPI publish

<!-- sq:finding:F3:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
The tag-vs-pyproject version guard lives in the vsix job only. The publish (PyPI) job has no such guard and builds from pyproject regardless of the release tag, and the two jobs run in parallel (no needs:). So on a tag/pyproject mismatch, PyPI still publishes (the pyproject version) while the vsix job fails the guard — you get a PyPI release with a mismatched tag and no matching VSIX asset, rather than a clean stop. Not a break (PyPI is unchanged and independent; this is why 'no way PyPI breaks' holds) and the scenario is operator error on a manually-created release, but the guard's protection is asymmetric. Optional hardening: hoist the tag==version check into a shared pre-flight (or a job both depend on) so a mismatch stops the whole bundle, not just the VSIX. Low/informational.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
