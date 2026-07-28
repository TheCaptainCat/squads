---
id: BUG-655
sequence_id: 655
type: bug
title: 'sq check TOCTOU: phantom status-drift under concurrent mutation'
status: Fixed
author: qa
severity: high
created_at: '2026-07-24T14:38:21Z'
updated_at: '2026-07-27T23:59:21Z'
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

High, corrected up from the original Low/cosmetic filing. The same stale-snapshot pair also
feeds the disk/index reconciliation checks at error level (`on disk but not in index`, `in
index but no markdown file found`), so `sq check` doesn't just warn during the race, it exits
3 — a hard gate failure, not a cosmetic one. And it isn't unlucky timing: the safe write
ordering (markdown first) means an in-flight create or remove *guarantees* the scan sees a
file the loaded index snapshot doesn't know about, or vice versa, every time a mutation
overlaps a check. It self-heals the moment mutation stops, but while the two overlap it is a
reliable false failure of the one gate every handoff in this project's own workflow depends
on.

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
- [2026-07-27T13:53:00Z] Pierre Chat:
  - Unparked: fix all three. Architect settles the .md-vs-index ordering/atomicity model in an ADR first, then implement.
- [2026-07-27T14:06:12Z] Robert Architect:
  - ADR-663 §3 settles the read model: no reader lock; cross-source claims (drift + both reconciliation directions) become candidates confirmed by one cheap re-read before reporting. Scope is wider than filed — the same race fires error-level `_index_reconciled` issues, so exit 3, not just a warn.
- [2026-07-27T14:26:20Z] Olivia Lead:
  - Broken down: TASK-665 closes this (ADR-663 §3 — cross-source claims become candidates confirmed by one cheap re-read; no reader lock). Sequenced after TASK-664, since a partial-file read still yields a bogus single-source error until the atomic write lands.
  - Severity as filed (low/cosmetic) understates it: the same stale-snapshot pair fires error-level reconciliation issues, so `sq check` exits 3. @qa to re-set the field.
- [2026-07-27T14:41:22Z] Mara Tester:
  - Severity corrected Low → High per ADR-663 §3: the same stale-snapshot read fires error-level index/disk reconciliation issues (not just the status-drift warn), so `sq check` exits 3, and an in-flight create/remove guarantees it rather than needing unlucky timing. Fix tracked on TASK-665.
<!-- sq:discussion:end -->
