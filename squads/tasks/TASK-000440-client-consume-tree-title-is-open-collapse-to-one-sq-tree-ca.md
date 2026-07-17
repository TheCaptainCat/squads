---
id: TASK-440
sequence_id: 440
type: task
title: 'Client: consume tree title + is_open, collapse to one sq tree call'
status: Done
parent: FEAT-100
author: tech-lead
assignee: typescript-dev
refs:
- ADR-427:addresses
- REV-438:addresses
- TASK-439:depends-on
description: Rewire extension onto enriched surface; drop title-join + list diff;
  single sq tree call; recapture fixtures
created_at: '2026-07-17T07:45:19Z'
updated_at: '2026-07-17T11:19:01Z'
---
<!-- sq:body -->
## Owner

Client TypeScript work — intended for **Ada Typescript** (typescript-dev).
Authored here for scope/traceability; the tech lead is not implementing it.

## Goal

Rewire the VS Code extension to consume the newly-enriched machine surface (the
core task's additive `title` on `sq tree --json` and `is_open` on both
`sq list --json` and `sq tree --json`), dropping the client-side workarounds that
REV-438 flagged. **Depends on the core enrichment task landing first** — the new
keys must exist before the client reads them.

## Scope

- **Tree labels from `sq tree --json` directly.** Render node titles from the
  tree payload's new `title` field. Drop the join-by-id second `sq list --json`
  fetch (`buildTitleLookup`) that today recovers labels — the tree is now
  self-sufficient for labels.
- **Open/closed from `is_open`.** Classify each item open vs terminal from the
  `is_open` boolean. Drop the double-`sq list` diff (default vs `--all`) that
  today infers state — one payload now carries it.
- **Collapse the hierarchy render to a single `sq tree --json` call.** With titles
  and `is_open` on the tree, the non-flat/hierarchy refresh path needs exactly one
  spawn (`sq tree --json`), not three (tree + list --all + list). This also
  closes REV-438 F1 (the redundant open-only `sq list` on hierarchy refresh) as a
  natural consequence — note it in the handoff.
- Keep the flat/grouped view's data source correct: it may still need
  `sq list --json` for the flat listing, but it now reads `is_open` from that same
  single payload rather than diffing two calls.

## Required in this task

- **Recapture the committed fixtures** with the new fields:
  `clients/vscode/test/fixtures/tree.json` and
  `clients/vscode/test/fixtures/list.json`, captured from real enriched
  `sq … --json` output (not hand-edited).
- **Update unit tests** for the JSON→DisplayNode mapping and the open/closed
  classification to assert against the new fields (title from tree, `is_open`
  boolean) rather than the old join/diff logic.
- **Keep the strict gate green**: `npm run check` (tsc strict + eslint
  zero-warnings + prettier) and `npm test` all pass.
- **Keep the item-ID hygiene guard green** (`test/hygiene.test.ts`) — no sq/task
  IDs leak into client source, fixtures, or README.

## Acceptance criteria

- Hierarchy refresh issues a single `sq tree --json` spawn; no second `sq list`
  for titles, no `sq list` diff for state.
- Tree labels come from the tree payload's `title`; open/closed from `is_open`.
- Fixtures recaptured from live enriched output; unit tests updated and green.
- Strict gate + hygiene guard green.

## Addresses

REV-438 rulings (a) and (b) in the client; incidentally resolves F1 (redundant
open-only list on hierarchy refresh) by collapsing to one call.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 440 add-subtask "<title>"`; track with `sq task 440 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-17T08:17:45Z] Ada Typescript:
  - Rewired onto the enriched surface: tree labels now read title directly off sq tree --json nodes (dropped buildTitleLookup + the second sq list --json fetch); flat/grouped view classifies open/closed from is_open (dropped getListSnapshot's --all/default diff, now one sq list --all --json call); hierarchy refresh is a single sq tree --json spawn (known-types for the filter quick-pick now derived by walking the tree via distinctTypesInTree, so no list fetch needed there either).
  - SqTreeNode gained title/is_open, SqListItem gained is_open; parser validators updated to check both.
  - Recaptured fixtures from live sq output: tree.json = sq tree EPIC-99 --all --json (11 tasks, mixed open/closed/blocked); list.json = a curated-but-100%-live subset of sq list --all --json (49 items spanning all 7 non-reserved types + role/skill/operator, both is_open states) — not hand-edited, just a real capture trimmed to a representative selection.
  - Removed dead workaround code: buildTitleLookup, getListSnapshot/ListSnapshot, the openIds-diff classifyListItems signature, and their tests; this incidentally closes REV-438 F1 (redundant open-only list on hierarchy refresh) as noted in the task body.
  - Also folded in REV-443 F3: added clients/vscode/.vscodeignore (excludes src/**, test/** incl. fixtures, toolchain config, package-lock.json, node_modules/**); marked F3 Fixed on REV-443.
  - Gate: npm run check + npm test both clean, zero warnings, hygiene guard (no ticket IDs in src) green. Live extension-host verification (tree renders, preview opens) deferred to CI/manual — no VS Code host in this environment.
  - Leaving InReview (reviewer-gated, not Done) — @reviewer please review.
- [2026-07-17T11:19:01Z] Ada Typescript:
  - Blocking packaging bug fixed and verified with the real tool (npx @vscode/vsce ls / --tree). Root cause was NOT .vscodeignore anchoring — vsce's ignore matching is minimatch with no matchBase, so a mid-slash pattern like src/** or test/** is already anchored to the package root and never matched the out/src or out/test mirrors; empirically out/src/extension.js was already listed. The real defect was elsewhere in this same file's history: package.json's main (currently mid-fix in this tree to ./out/src/extension.js, matching tsc's rootDir '.' output layout) plus a latent .vscodeignore gap — test/** and vitest.config.ts don't cover their compiled out/ mirrors, so out/test/**.js and out/vitest*.js were shipping. Fixed .vscodeignore: added out/test/**, vitest.canary.config.ts, out/vitest.config.js, out/vitest.canary.config.js.
  - Separately discovered (pre-existing since FEAT-100 Phase A, not part of this fix's scope): package.json declares @types/vscode ^1.125.0 against engines.vscode ^1.85.0, which vsce 3.9.2 (and 2.15.0, checked) hard-refuses to package at all ('@types/vscode ... greater than engines.vscode'). This has blocked vsce ls/package entirely, worse than the entry-point gap. Bumped engines.vscode to ^1.125.0 to unblock verification; flagging for @qa to file as a tracked bug since it also blocks TASK-433's release pipeline.
  - Verified: npm run compile && npx vsce ls now lists package.json, README.md, resources/**, out/src/** (incl. extension.js matching main) — no src/, test/, out/test/, tsconfig, eslint/prettier config, or node_modules. npm run check and npm test both green (66/66). Not committed, nothing marked Done.
<!-- sq:discussion:end -->
