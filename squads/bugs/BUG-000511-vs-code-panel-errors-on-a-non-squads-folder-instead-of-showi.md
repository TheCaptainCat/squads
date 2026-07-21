---
id: BUG-511
sequence_id: 511
type: bug
title: VS Code panel errors on a non-squads folder instead of showing an empty state
status: Verified
author: manager
assignee: typescript-dev
priority: medium
description: Opening the Squads panel outside a squad shows an error node + error
  toast
created_at: '2026-07-21T08:08:29Z'
updated_at: '2026-07-21T08:13:56Z'
---
<!-- sq:body -->
**What happens.** Opening the Squads view in a workspace with no squad (no `.squads.toml`) renders a red error node in the tree and fires an error notification. `sq tree --json` exits 1 there with `error: no .squads.toml found… — run sq init`, and the client's `treeDataProvider.fail` path treats every non-zero exit as a runtime error.

**Expected.** A calm empty state — "No squad detected here" — with no error styling and no toast. This is the normal case for any non-squads workspace, not a failure.

**Fix direction.** Detect the no-squad condition up front (the client already has `resolveSquadDir()`, its mirror of sq's `.squads.toml` walk-up, currently only wired to the watcher) and render a neutral empty state instead of spawning + erroring. An "init a squad here" action button is explicitly out of scope for now — deferred.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T08:12:44Z] Ada Typescript:
  - Fixed: treeDataProvider.ts/metaTreeDataProvider.ts now call resolveSquadDir() up front in refresh() and short-circuit to a new emptyStateDisplayNode('No squad detected here') (domain/displayNode.ts) — no spawn, no notifyError toast. extension.ts shares one createNodeSquadDirEnvironment() instance across the providers and squadWatcher. Added displayNode.test.ts coverage; npm run check + npm run test both clean.
- [2026-07-21T08:13:55Z] Catherine Manager:
  - Verified for the 0.11.1 cut: reviewed the diff (structural `resolveSquadDir` detection, not error-string matching; shared `squadDirEnv`; both tree + meta providers short-circuit before spawning `sq`), and re-ran the extension gates myself — `npm run check` clean, vitest 316/316 incl. the new `emptyStateDisplayNode` suite. Live dev-host visual check is Pierre's on his Windows host if wanted before publish.
<!-- sq:discussion:end -->
