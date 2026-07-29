---
id: BUG-679
sequence_id: 679
type: bug
title: 'VS Code: per-section refresh only refreshes its own tree'
status: Verified
author: qa
severity: low
refs:
- BUG-680
created_at: '2026-07-28T07:32:44Z'
updated_at: '2026-07-29T08:32:22Z'
---
<!-- sq:body -->
Observed (Pierre): clicking the refresh button on one of the three activity-bar sections
(Work / Roster / Records) only refreshes that section; he had to click all three separately.

Established from code inspection (`clients/vscode/src/commands.ts`, `package.json`):
`squads.refreshTree`, `squads.refreshMeta`, and `squads.refreshRecords` are three
independently registered commands, each bound to its own view's title-bar refresh icon, and
each calling only its own tree provider's `refresh()`. No command refreshes more than one
provider — there is no silent failure here, this is simply how the three are wired.

That a shared refresh is achievable is already proven elsewhere in the same file:
`extension.ts`'s `.squads.json` file-watcher handler (`onIndexChanged`) calls all three
providers' `refresh()` together on every on-disk change. No manual command does the
equivalent today.

Expected: any of the three refresh buttons refreshes Work, Roster, and Records together,
matching what the file-watcher's auto-refresh already does.

Not verified: the on-screen click behavior in a running dev host — no GUI session available
for this filing; based on source inspection of the command registrations only.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-28T07:32:54Z] Pierre Chat:
  - In the vscode ext, the refresh button of each section should refresh ALL 3 sections, I had to click to refresh each
- [2026-07-28T08:01:06Z] Pierre Chat:
  - Extend the expected behaviour: a tree refresh button should also trigger a webview refresh, so one global refresh covers all three trees plus any open previews. And add a refresh action on the webview itself, left of the nav arrows, firing that same global refresh.
- [2026-07-29T08:32:22Z] Catherine Manager:
  - Verified with a split basis, recorded so it isn't overstated: the operator confirmed the in-content refresh action on the dev host (present, correctly placed beside the nav arrows, clickable). The one-click-refreshes-all-three-trees-plus-preview half is covered by unit test rather than observation — it is not visually observable, since the watcher pre-empts a manual refresh and the action gives no feedback by design. Dropping the preview call from refreshAll turns that test red.
<!-- sq:discussion:end -->
