---
id: BUG-505
sequence_id: 505
type: bug
title: npm run check (eslint) OOMs locally — can't lint the VS Code extension
status: Verified
author: manager
priority: low
created_at: '2026-07-20T10:59:20Z'
updated_at: '2026-07-20T12:23:49Z'
---
<!-- sq:body -->
npm run check's eslint step (eslint . --max-warnings 0, type-aware @typescript-eslint projectService) exhausts the Node heap and aborts (exit 134) in this WSL2 dev env — even at --max-old-space-size=8192 with 11Gi free. typecheck (tsc) and npm test/e2e run fine; only eslint OOMs.

Reproduces on a CLEAN HEAD tree (stashed all in-flight changes and it still OOMs), so it's environmental/config, not caused by any feature work. Net effect: the extension's lint gate cannot be run locally — devs currently fall back to tsc+test+e2e and rely on CI (vscode-client.yml) as the only place eslint actually runs. It has already blocked local lint verification for the three recent extension fixes.

Candidate fixes: raise the heap in the check/lint npm script (NODE_OPTIONS), and/or tune the eslint flat-config projectService (scope the typed lint, or drop to a lighter parser project), and/or pin the Node version to match CI (22). Low priority — CI still gates lint — but it's a real dev-experience gap. Files: clients/vscode/eslint.config.mjs, clients/vscode/package.json (check/lint scripts).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-20T12:13:33Z] Catherine Manager:
  - Test comment for the webview render check (exercises BUG-503 mentions + BUG-502 scroll).
  - Role mentions — should each link to the role sheet with details in the hover text: @manager, @tech-writer, @typescript-dev.
  - Item link (existing behavior): BUG-499. Markdown sanity: **bold**, `inline code`, _italic_, and a list:
  - - first bullet
  - - second bullet, long enough to give the panel something to scroll if the window is short
- [2026-07-20T12:15:19Z] Ada Typescript:
  - Root cause: eslint.config.mjs's ignores list (out/**, node_modules/**, test/fixtures/**, media/**, scripts/**) never excluded .vscode-test/ — the ~930MB VS Code+Electron build @vscode/test-electron downloads into clients/vscode/.vscode-test/ the first time 'npm run test:e2e' runs. It's gitignored but nothing told eslint to skip it, so 'eslint .' handed the type-aware projectService ~250 large/minified JS files plus ~130 .d.ts files (including the full vscode.d.ts API surface) that sit outside tsconfig.json's include — each forcing an ad hoc program/language-service scan far outside anything this config is meant to check, which is what actually exhausts the heap (confirmed: 8GB heap still OOMs; linting 'src test eslint.config.mjs vitest.config.ts' explicitly, bypassing the '.' glob, completed instantly with no heap bump). Once .vscode-test/ exists on disk it persists across stashes (git stash doesn't touch gitignored dirs), which is why it 'reproduced on a clean tree' — it's local directory state, not a code or config regression. CI's check job never runs test:e2e first, so .vscode-test/ never exists there, hence CI was never affected.
  - Fix: added '.vscode-test/**' and 'coverage/**' (the other gitignored-but-unexcluded generated tree) to eslint.config.mjs's ignores array. Pure scope fix — no rule, strictness, or --max-warnings change; src/ and test/ are still linted with the full type-aware strictTypeChecked/stylisticTypeChecked config, no heap bump needed anywhere.
  - Files: clients/vscode/eslint.config.mjs (ignores list only).
  - Verified locally: npm run lint completes in ~4s at default heap (previously OOM'd even at --max-old-space-size=8192); npm run check (typecheck + lint + format:check) completes end-to-end, exit 0; npm test 287 passed. CI is unaffected (vscode-client.yml's check job never has .vscode-test/ on disk, and the ignores addition doesn't touch any file CI actually lints). @manager
- [2026-07-20T12:23:48Z] Catherine Manager:
  - Verified: npm run check completes locally (~4s, was OOM); lint gate runs with no strictness lost.
<!-- sq:discussion:end -->
