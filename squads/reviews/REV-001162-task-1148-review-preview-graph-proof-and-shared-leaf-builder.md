---
id: REV-1162
sequence_id: 1162
type: review
title: 'TASK-1148 review: preview graph proof and shared leaf builder'
status: Approved
author: reviewer
refs:
- TASK-1148
description: 'VS Code client: CSP render report in the e2e smoke; one item-leaf builder
  for list, roster and records'
subentities:
- local_id: F1
  title: Smoke excludes style-src-attr and calls it expected; measured zero, so inline-style
    loss is unguarded
  status: Verified
  severity: low
- local_id: F2
  title: 'List and records leaf descriptions are unpinned: changing either keeps the
    suite green'
  status: Verified
  severity: low
created_at: '2026-10-26T09:31:35Z'
updated_at: '2026-10-26T09:34:41Z'
---
<!-- sq:body -->
Review of commit c6ce2870 (TASK-1148, `clients/vscode/`): ST1 proves the item preview renders mermaid graphs under the strict CSP in the extension-host smoke; ST2 moves the flat item-leaf builder into `domain/displayNode.ts` (`itemLeaf`/`sortedItemLeaves`) for the list, roster and records views.

## What was checked

- Gates in `clients/vscode`: `npm run lint` clean, `npm run typecheck` clean, `npm test` 758 passed. `npm run test:e2e` run once (VS Code under DISPLAY :0), exit 0, report `rendered 2, failed 0, styleElements 2/2 nonced/2 applied, inlineStyleAttributes 58/58 applied, violations []`. This matches the handoff.
- ST1 production surface. The extension host has no API that reads a webview's DOM, so a message from the page is the only way the smoke can observe the render. Normal-use cost: per render pass, one `querySelectorAll('[style]')` over the SVGs, one `postMessage`, a document-level `securitypolicyviolation` listener, and on the host one parse plus an event fired with no listener. That is negligible. `parseRenderReportMessage` rebuilds the object from known keys, requires integer counts and a string array, and the host only fires an event with it. It does not reject negative counts or cap the array, which does nothing here. The `activate()` return makes `onDidReportPreviewRender` part of the extension's exports. That is acceptable and documented on `SquadsExtensionApi`.
- ST1 assertion: 2 graphs, 0 failed, `<style>` count > 0 and all nonced and applied (`.sheet` non-null), no violation other than `style-src-attr`. A preview from an earlier step cannot satisfy it: only SMOKE-2 has graphs, and a graph-less page posts no report. The `style-src-attr` exclusion hides nothing today, because the measured list is empty. It does leave inline-style loss unasserted, and the comment above it is false (F1).
- ST2: diffed the three old private builders against `itemLeaf`. Label, tooltip (plus the roster memory line), icon, closed/hidden/colour, blocked/anchor false, children and numeric id order are identical per view. Roster children are still `memoryChildren(slug, pool, now)` when `pool` is undefined, as before. Descriptions are unchanged: list `status · assignee ?? unassigned`, roster pronouns and status, records status alone. No behaviour change.
- Mutations on a scratch copy. These went red: dropping the label suffix (4 tests), forcing closed false (4), dropping the sort (7), dropping the tooltip suffix (2), swapping the records icon (1), dropping roster children (1), allowing fractional counts (1), skipping the violations check (2). Two survived: changing the list description and changing the records description (F2).

## Recommended verdict

Approve once F1 and F2 are settled. Both are low.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1162 add-finding "…" --severity medium`; track with `sq review 1162 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Smoke excludes style-src-attr and calls it expected; measured zero, so inline-style loss is unguarded

<!-- sq:finding:F1:body -->
`test/extensionHost/suite/index.ts` says "a violation of `style-src-attr` is expected and only logged". The measured run, the handoff and my own e2e run all show `violations: []` and `inlineStyleAttributesApplied 58/58`. So the comment states the opposite of what was observed, and the assertion filters out the one directive the task asked us to watch.

I infer, but did not verify against Chromium source, that the attributes survive because the SVG is put in place with `document.importNode`, a clone, and Chromium does not run the `style-src-attr` check on attributes copied by cloning.

Failure scenario: a future Chromium/VS Code stops exempting cloned attributes, or the render path moves to an `innerHTML` assignment. The inline `style=""` attributes (root `max-width`, edge/marker styling) are then dropped, a `style-src-attr` violation fires, and the smoke stays green because that directive is filtered out and `inlineStyleAttributesApplied` is only logged. The task asked to record whether those attributes are dropped. The test now records that they are not, but it does not hold that.

Fix: assert `violations` is empty and `inlineStyleAttributesApplied === inlineStyleAttributes`, with a message that names the cloning path. If keeping the exclusion is a deliberate tolerance, correct the comment to say so and why. Two prose fixes go with it:
- `RenderReportMessage.inlineStyleAttributes` says "reflected in their computed style", but the code reads `el.style` (the inline declaration), not `getComputedStyle`.
- The suite's header still sends the reader to `../runTest.ts`'s doc comment "for why this only actually executes in CI". That doc comment now says the smoke runs wherever a display is available.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-26T09:33:28Z] `typescript-dev` Ada Typescript:
  - Fixed: the smoke now asserts violations is empty (style-src-attr included) and every inline style attribute is applied (58/58 measured); stale comment, report docstring (el.style) and suite header corrected. test:e2e exit 0.
- [2026-10-26T09:34:38Z] `reviewer` Paul Reviewer:
  - Verified at 16b6355d: the smoke asserts violations deep-equal [] and inlineStyleAttributesApplied equal to a non-zero inlineStyleAttributes; the report docstring now names el.style and the suite header no longer claims CI-only. The e2e was not re-run: the measured report from my earlier run satisfies the new assertions.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — List and records leaf descriptions are unpinned: changing either keeps the suite green

<!-- sq:finding:F2:body -->
After ST2, each view's description is a one-line argument in that view's `sortedLeaves` wrapper. `displayNode.test.ts` checks that `itemLeaf` copies whatever description it is given. Only the roster's wording is pinned by a view test (`metaView.test.ts`, "shows status alone in the description").

Mutations on a scratch copy, both with 758/758 still green:
- In `listView.ts`, replacing `${item.status} · ${item.assignee ?? 'unassigned'}` with `item.status`.
- In `recordsView.ts`, replacing `item.status` with a status-plus-assignee string.

This gap was there before this commit. It matters now because ST2's evidence for "no behaviour change" is "existing list, roster and records tests pass unchanged", and that evidence cannot detect a description change in two of the three views. I confirmed by reading the diff that both descriptions are unchanged.

Failure scenario: a later edit swaps or drops one view's description argument, for example by copying the records wrapper into a new view or tidying the list wrapper. The work tree loses its assignee, or records gain one, and no test fails.

Fix: one assertion each in `listView.test.ts` and `recordsView.test.ts` on a leaf's `description`: list `Ready · ada` and `Ready · unassigned`, records the status alone.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-26T09:33:31Z] `typescript-dev` Ada Typescript:
  - Fixed: listView.test.ts pins "Ready · unassigned" and "Ready · ada"; recordsView.test.ts pins status-only with an assignee set. Verified red: dropping the assignee part fails 1 list test, appending to the records description fails 1 records test; sources restored.
- [2026-10-26T09:34:39Z] `reviewer` Paul Reviewer:
  - Verified at 16b6355d on a scratch copy: list description changed to status alone fails 1 listView test; records description with assignee appended fails 1 recordsView test; 760 passed unmutated.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-26T09:31:50Z] `reviewer` Paul Reviewer:
  - Two low findings, no blocker. F1: the e2e excludes style-src-attr as expected while every run measured zero violations and 58/58 inline styles applied, so pin the measured state (plus two doc fixes). F2: the list and records leaf descriptions are unpinned (mutations survive). ST1's report surface is justified (no other window onto the webview), cheap in normal use, and parsed strictly enough. ST2 is behaviour-preserving in all three views. Gates green; e2e rerun exit 0. Recommend Approved once F1 and F2 are fixed. @typescript-dev @tech-lead
- [2026-10-26T09:34:40Z] `reviewer` Paul Reviewer:
  - Verdict: Approved. F1 and F2 verified fixed at 16b6355d; no open findings.
<!-- sq:discussion:end -->
