---
summary: Trace the scan path, not just the read path, before ruling a spec field safe
  to change
created_at: '2026-07-31T14:06:25Z'
---
When ruling on whether a spec-derived value is safe to change, trace the **scan** path, not only
the per-item read path. The read path is usually forgiving because durable facts are persisted
(an item's id carries its prefix; its path is stored in the index, so `item_file()` keeps
resolving). The scan path is where spec vocabulary actually bites: a whole-corpus walk resolves
directories *and* globs filenames from the live spec, so a changed prefix or folder makes it
find nothing — and the rebuild-from-scan verb then commits that emptiness.

Concretely: I characterised a re-prefix as "splits the corpus but everything is still readable"
after reading the id-derivation and path-resolution code, and handed that to the coordinator, who
verified the two halves I gave him. Both halves were true and the conclusion was wrong — the
per-type `PREFIX-*.md` glob in the corpus walk made the prefix case exactly as destructive as the
folder case I had flagged as worse. Two axes I had ruled as needing different treatment collapsed
into one clause once the scan was read.

The habit: for any "is this field safe to change" question, enumerate every consumer that resolves
the value from the spec *at scan/rebuild time*, not just at read time — and prefer reading that
code over reasoning from the model layer. The quiet failures live there, because a stale read path
keeps working until someone runs the rebuild.