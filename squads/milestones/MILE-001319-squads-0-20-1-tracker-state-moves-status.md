---
id: MILE-1319
sequence_id: 1319
type: milestone
title: squads 0.20.1 - tracker state moves status
status: InProgress
author: product-owner
refs:
- EPIC-1268
description: 'Opt-in status map on sources: a closed issue can close its item'
created_at: '2026-11-06T15:08:00Z'
updated_at: '2026-11-06T15:23:42Z'
---
<!-- sq:body -->
The first patch release after 0.20.0: a squad can let a tracker's open or closed state move the item's workflow status, per source and by opt-in. Until now a pull never touches an item's status, so a closed issue leaves its item where it was.

Scope is carried by the features that target this milestone: the opt-in status map on a source.

The release is ready when a source that declares a status map moves its items on the next pull, a source that declares none behaves exactly as in 0.20.0, and a bad map target is refused when the sources spec loads.

Writing back to a tracker is out of scope.

Membership works through incoming `targets` refs; the roll-up below inverts them.

<!-- sq:view:milestone_rollup -->
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
