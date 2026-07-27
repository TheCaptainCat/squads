---
id: BUG-655
sequence_id: 655
type: bug
title: 'sq check TOCTOU: phantom status-drift under concurrent mutation'
status: Open
author: qa
created_at: '2026-07-24T14:38:21Z'
updated_at: '2026-07-24T14:40:08Z'
---
<!-- sq:body -->
## Symptom

`sq check` reports `status drift between frontmatter and index (run \`sq repair\`)` for one
or more items while another process is concurrently mutating the board — even though the
persisted `.squads.json` is never actually wrong.

## Root cause

`Service.check()` (`src/squads/_services/_maintenance.py:855-856`) performs two **separate,
unlocked** reads that are not atomic with each other or with any in-flight transaction:

```
index = await self.store.load()          # line 855
issues, on_disk, bodies = await self._scan_for_check()   # line 856 — walks every .md file
```

`_scan_for_check()` reads every item file on disk one at a time; on a squad of a few hundred
items this scan alone takes 0.5-2s (measured). If another process commits a status transition
while the scan is in progress, the scan observes that item's already-updated `.md` while
`_check_items()` (`_maintenance.py:906-922`) compares it against the `index` snapshot loaded
*before* the commit — a stale comparison, not a stale file.

## Repro

Seeded a throwaway squad (~430 items) and ran 4 concurrent OS processes, each driving
`Service.set_status()` in a tight loop on a disjoint set of items, while a 5th process
polled `Service.check()` in a loop for ~20s. 11 of 19 `check()` calls flagged a "status
drift" warning naming whichever item a transaction committed mid-scan. Immediately after
the 4 mutating processes stopped, `check()` (and `sq check`) were clean again — the drift
did not reappear once reads and writes stopped racing, confirming the persisted index was
never actually wrong.

## Severity

Low. Cosmetic — self-heals as soon as concurrent mutation settles, and `sq repair` (or a
subsequent clean `sq check`) always clears it. But it erodes trust in `sq check` as a gate:
an agent seeing "drift" mid-session with no way to tell it apart from real corruption may
run unnecessary `sq repair`s or escalate a non-issue.

## Proposed fix

Make the two reads atomic with respect to in-flight transactions — options:
- Take a shared/reader lock (or the same Layer-3 file lock, briefly) around `load()` +
  the file scan so no transaction can commit mid-check.
- Snapshot-then-recheck: only report a drift that still holds after a second, cheap
  re-read of just the affected item's frontmatter + index entry (filters out anything
  that was mid-flight).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-24T14:40:08Z] Pierre Chat:
  - Investigated + fix proposed; parked — not scheduled for 0.12.1.
<!-- sq:discussion:end -->
