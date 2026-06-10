---
id: BUG-000030
sequence_id: 30
type: bug
title: 'tree: priority and title separated by a bare space'
status: Draft
author: op-pierre
priority: low
description: In sq tree, '🟠 high Stability contract documentation' runs together —
  put a middle dot between priority and title
created_at: '2026-06-10T15:19:16Z'
updated_at: '2026-06-10T15:19:16Z'
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
  FEAT-000015's domain).
- Worth a quick sweep for the same pattern in other composed lines (e.g. `sq blocked`, `sq mine`
  output) so the separator is consistent everywhere — `sq list` is columnar and unaffected.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
