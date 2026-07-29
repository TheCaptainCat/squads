---
id: BUG-687
sequence_id: 687
type: bug
title: 'VS Code: toggle actions show no active state'
status: Fixed
author: op-pierre
description: Group by type and Show closed render identically whether on or off
created_at: '2026-07-29T08:49:02Z'
updated_at: '2026-07-29T09:08:21Z'
---
<!-- sq:body -->
## Symptom

The two view-title toggle actions on the Work Items tree — **Group by type** and **Show closed items** — render identically whether their state is on or off. There is no visible difference at all, so a user cannot tell from the toolbar whether grouping or closed-item visibility is currently active. Observed on the Windows dev host.

## What is already in place

Both actions already declare a `toggled` context key in the extension manifest's `view/title` contributions (`squads.groupByType`, `squads.showClosed`), and the keys are correctly maintained: seeded from the provider's initial state on activation, and updated on every toggle and on clear-filters. So the extension side appears complete — this is not a missing `setContext` call.

## Likely cause, to be confirmed

VS Code may not render a toggled state for icon-only actions in a view title bar's `navigation` group — `toggled` is visible as a checkmark in dropdown menus, but an icon button may have no corresponding treatment. If that holds, the manifest is correct and the affordance simply does not exist by that route.

## Direction if confirmed

Swap the icon on state instead of flagging state: two menu entries with opposite `when` clauses and distinct codicons, so the button's appearance carries the information. That also lets the icon show what the next click will do rather than only what is currently true. Changing the action's title per state is a weaker second option, since it only surfaces in the tooltip and the command palette.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-29T08:49:30Z] Pierre Chat:
  - It's not subtle — there is just no difference shown between active and not.
- [2026-07-29T09:08:10Z] Ada Typescript:
  - Confirmed the hypothesis, but stronger: VS Code never reads a per-item toggled property for extension-contributed contributes.menus entries at all — verified against menusExtensionPoint.ts at v1.85.0, the current latest stable, and main; IUserFriendlyMenuItem/IUserFriendlyCommand never carry the field, so it renders no checkmark or pressed state anywhere (toolbar or dropdown), not just the toolbar route. toggled only exists on core VS Code's own ICommandAction (registerAction2).
  - Fix: split each toggle into two commands with opposite when-clauses on the existing context key and distinct codicons — squads.toggleGroupByType (list-flat, visible while off) / squads.ungroupByType (list-tree, visible while on); squads.toggleShowClosed (eye-closed, visible while off) / squads.hideClosed (eye, visible while on). Icon reflects current state, title names the action — same idiom VS Code's own references-view call-hierarchy direction toggle uses. Removed the dead toggled keys from package.json.
  - npm test 424/424, npm run check clean. Added test/toggleMenuIcons.test.ts asserting no toggled property remains and each pair has distinct icons + complementary when clauses; falsified both assertions by hand before restoring. Needs Pierre's visual confirmation on the Windows dev host.
<!-- sq:discussion:end -->
