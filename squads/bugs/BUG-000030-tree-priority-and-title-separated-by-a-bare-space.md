---
id: BUG-30
sequence_id: 30
type: bug
title: 'tree: priority and title separated by a bare space'
status: Verified
author: op-pierre
priority: low
description: In sq tree, '🟠 high Stability contract documentation' runs together —
  put a middle dot between priority and title
created_at: '2026-06-10T15:19:16Z'
updated_at: '2026-06-11T13:19:46Z'
---
<!-- sq:body -->
## Observed

In `sq tree`, the priority label and the title are separated by a single space, so they read as
one phrase:

```
├── FEAT-000013 🟠 high Stability contract documentation (Draft)
```

"high Stability contract documentation" — the eye has to find the boundary itself, and
priority-less nodes vs prioritized ones make the title column start at inconsistent visual
positions.

## Expected

A middle dot (`·`) between the priority and the title:

```
├── FEAT-000013 🟠 high · Stability contract documentation (Draft)
```

## Notes

- Only the human-readable tree rendering changes; `sq tree --json` is untouched (machine surface,
  FEAT-15's domain).
- Worth a quick sweep for the same pattern in other composed lines (e.g. `sq blocked`, `sq mine`
  output) so the separator is consistent everywhere — `sq list` is columnar and unaffected.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-11T12:12:32Z] Catherine Manager:
  - Triage 2026-06-11: promoted to Ready, stays low. Batched with BUG-25 as one quick-win. Include the consistency sweep: apply the same priority/title separator to other composed lines (sq blocked, sq mine); sq tree --json untouched.
- [2026-06-11T12:16:05Z] Olivia Lead:
  - Fix task created: TASK-44 (low, @python-dev) — batched with BUG-25. Adds the '·' separator in tree plus a consistency sweep of sq blocked / sq mine.
- [2026-06-11T12:51:04Z] Olivia Lead:
  - @qa Fix landed and reviewed (TASK-44, Done). 'sq tree' human rendering now puts ' · ' between the priority badge and the title (e.g. '🟠 high · beta'); 'sq tree --json' is unchanged. blocked/mine were swept and confirmed not to compose priority+title inline, so no change there. Please verify. Uncommitted in the working tree. Bug stays open until you verify.
- [2026-06-11T13:19:46Z] Mara Tester:
  - Verified fix for BUG-30 (TASK-44) against working tree.
  - sq tree --all human rendering shows '·' separator between priority and title for all prioritized nodes, e.g. 'EPIC-12 🟠 high · Road to 1.0 (Ready)'. Visual boundary is clear.
  - sq tree --all --json: priority values are clean strings ('high', 'medium', 'low') — no dot in machine surface.
  - All acceptance criteria met. Closing.
<!-- sq:discussion:end -->
