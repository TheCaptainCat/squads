---
id: BUG-1284
sequence_id: 1284
type: bug
title: Pull drops links between issues of different sources
status: Open
author: qa
refs:
- FEAT-1271
created_at: '2026-11-04T09:00:26Z'
updated_at: '2026-11-04T09:19:42Z'
severity: high
---
<!-- sq:body -->
A tracker link becomes a ref only when both linked issues are held by items of the same source. With two sources on one tracker (for example one per label, epics and stories), every link between an issue of one and an issue of the other is dropped, and the pull reports nothing.

Found in the live GitLab run recorded on TASK-1278: every epic-to-story link was lost with one source per label; one source covering both kept them. The operator confirmed in the VS Code client that pulled items show no refs.

## Steps (reproduced 2026-11-04)

Recorded harness (tests/_tracker_harness.py, tests/fixtures/sources/gitlab/routes.json) served on loopback, in a scratch squad, dev build. The routes are edited so the listing of label `epics` returns issue 12 and the listing of label `stories` returns issue 13. The recorded link on issue 12 is `blocks` issue 13.

1. Declare two sources on the same `base_url` (gitlab.example.com in a real setup), `epics` with `filter = "epics"` and `stories` with `filter = "stories"`, both mapping `type.issue = "task"`; set a credential for each.
2. `sq source pull epics` then `sq source pull stories`.
3. `sq task 2 show` (the epics item).

## Actual

- Pull 1: `epics: created 1 (TASK-2)`, `stories: created 1 (TASK-3)`. No warning, no omission about the link.
- Pull 2: both sources report `unchanged 1`. Still no ref, because links are compiled only for changed issues, so the loss does not heal.
- TASK-2 has no `refs:` line.

Control, one source `all` with `filter = "squads"` over the same two issues: one pull creates TASK-2 and TASK-3 and TASK-2 shows `refs: TASK-3 (blocks)`.

## Expected

A link resolves to whichever item holds the target issue on the same tracker (same `base_url`, whatever the source). At minimum, when the target is held by another source's item, or is not held at all, the pull reports the dropped link instead of dropping it silently. The ref should also appear on a later pull once the target issue is pulled, not only when the host issue changes.

## Code pointer

`src/squads/_services/_pull.py`, `Compiler.links()`: targets are looked up as `self.by_id.get((self.source.name, link.target_id))` and, for items created in the same run, `f"{self.source.name}:{link.target_id}"` in `self.out.created`. Both keys carry `self.source.name`, so a target held under another source never matches, and an unmatched target produces no event and no warning.

## Not covered

Cross-tracker links (different `base_url`) are out of scope: no item can hold those.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-04T09:19:42Z] `architect` Robert Architect:
  - - Settled in ADR-1274 §14, **Links across sources** (amendment 2026-11-04, ruling f6cbdfc): links, references and the one-holder check resolve across every source with the same normalised base URL; a link carries its inverse type, so the second issue's own detail fetch makes the ref and the loss heals without refetching unchanged issues; a mapped link whose target no item holds is reported per host issue.
    - The scope-based selection in the same amendment also removes the one-source-per-label setup that triggered this.
<!-- sq:discussion:end -->
