---
id: BUG-746
sequence_id: 746
type: bug
title: 'Sub-entity panes open inconsistently: discussion unfolded, body collapsed'
status: Verified
author: qa
description: Both folds in a sub-entity pane should default collapsed; today the discussion
  opens while the body stays shut
created_at: '2026-08-20T18:40:30Z'
updated_at: '2026-08-20T19:27:05Z'
---
<!-- sq:body -->
Reported by op-pierre from the extension dev host, on the 0.13.0 build.

On opening an item preview, a sub-entity pane renders its **body fold collapsed** and its **discussion fold open**. Both should be collapsed. The defect is the inconsistency between two folds sitting in the same pane, not the choice of default on either one.

Mechanism, read at `clients/vscode/src/domain/previewDocument.ts`:

- The body is `<details class="sq-subentity-body" data-sq-fold-id="{local_id}"{openAttr}>` — `openAttr` comes from the caller's per-panel tracker, so it is absent on first open.
- The discussion is `<details class="sq-graph" open>` at `buildSubEntityDiscussionHtml`, hardcoded. Its docstring states the `open` is deliberate: the block carries no `data-sq-fold-id` so that its state cannot collide with, or reset, the body fold's tracking, which IS keyed by `local_id`.

So the hardcoded `open` is the immediate cause, and the reason it was chosen is fold-id collision avoidance rather than a view on the default.

Note the second-order question, which the fix should answer rather than leave: if the discussion simply loses `open`, the two folds agree on first open but still disagree across a refresh — the body remembers what you left it as, the discussion always returns to collapsed. That is the same class of inconsistency one step further out. Giving the discussion its own tracked identity, distinct from the body's `local_id` key, would make both the initial state and the remembered state agree.

Earlier in this release op-pierre saw the expanded panes and accepted them as shipped ("I do not mind it -- leave it as is", TASK-730). Having examined it properly in the host he has revised that: the inconsistency is the problem. This supersedes that note.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-20T18:42:23Z] Pierre Chat:
  - On open the sub-entity body is folded but the discussions are not. Both should be.
- [2026-08-20T18:50:26Z] Ada Typescript:
  - Fixed: gave the discussion its own tracked fold id (subEntityDiscussionFoldId = `${local_id}:discussion`), not just dropped `open`.
  - Chose the tracked-identity route over the minimal drop: a minimal fix would still leave the two folds disagreeing across a same-item refresh (body remembers, discussion always re-collapses) — same defect class one step out. With its own key, distinct from the body's plain local_id, both folds now agree on first open and on refresh.
  - Files: clients/vscode/src/domain/previewDocument.ts (subEntityDiscussionFoldId, buildSubEntityDiscussionHtml, buildSubEntityHtml, buildSubEntitiesHtml), clients/vscode/src/itemPreviewManager.ts (prune set now includes each entity's discussion fold id), clients/vscode/test/previewDocument.test.ts (3 new/updated tests). Falsified: reverted the source only, watched the 3 new tests redden, restored, watched them go green (615/615).
- [2026-08-20T19:27:02Z] Pierre Chat:
  - Checked in the dev host. Sub-entity panes open fully collapsed now, body and discussion agreeing. Approved.
<!-- sq:discussion:end -->
