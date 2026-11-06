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
updated_at: '2026-11-06T19:36:29Z'
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
- [2026-11-06T19:36:29Z] `manager` Catherine Manager:
  - Release benchmarks for 0.20.1 (2026-11-06, dev host), run against the released 0.20.0 on a copy of this squad, task 1321.
    
    Local mode, first run:
    
    ```
    command build    median      p25      p75   (ms, 31 runs)
    show    old         146      122      171
    show    new         147      118      159
    show    new/old median = 1.003
    list    old         200      176      229
    list    new         206      182      226
    list    new/old median = 1.033
    tree    old         130      113      141
    tree    new         132      112      145
    tree    new/old median = 1.015
    ```
    
    Rerun: show 1.038, list 1.011, tree 1.018. Noise floor (0.20.0 against itself): show 1.033, list 1.012, tree 0.942. Nothing on the show/list/tree path changed since 0.20.0, so the 1-4% gap is within run-to-run noise.
    
    CLI shim overhead (budget 100 ms on the CI runner, about 75 ms here):
    
    ```
    form                 median      p25      p75   budget   (ms, 31 runs)
    show                     59       51       67      100   ok
    list --json              55       47       62      100   ok
    bash completion          54       46       64      100   ok
    load average  before: (1.4521484375, 1.55419921875, 0.724609375)  after: (1.67724609375, 1.6015625, 0.74951171875)
    ```
<!-- sq:discussion:end -->
