---
summary: Sweep the declaration site's own writer list, and re-derive a command's message
  and exit code
created_at: '2026-09-08T15:02:32Z'
---
When a fix gates **one** writer of a shared value, sweep the declaration site's own enumerated
writer list before calling the class closed — and when a fix changes what a command *does*,
re-derive that command's own message and exit code in the same pass.

Two families accounted for every fix-induced finding across three rounds of REV-926:

**(A) A writer enumerated in the code but not swept.** `_interactions/__init__.py` declares
`SYSTEM_SKILL_VIEW_NAMES` with the sentence "seeded at creation (`_write_managed_skill`) and
backfilled by `sq repair` (`_repair_body_tag`) — **the two writers this table is shared
between**". One fix gated `_repair_body_tag`; the follow-up fix was scoped to the *role*
constant and nobody re-ran the same condition against the sibling table two lines up. The
enumeration was right there. So: when a finding is "writer X does not check C", grep the
declaration of the value X writes, read its own writer list, and check every one of them —
`grep -rn 'markers.view_tag('` was six lines.

**(B) A message or exit code left stating the old behaviour.** Withholding a version stamp
without touching the CLI's green "synced to this version" line; adding `unreadable` to an exit
condition without adding it to the output loop; giving a hint two new branches and leaving the
third branch's truth condition alone. Each is one command whose behaviour moved and whose own
self-description did not.

Both families are mechanically enumerable, which is the useful part: the right recommendation
after a second layer of fix-induced findings is not another instance sweep but one test that
enumerates the family (every writer of the tag; every CLI consumer of the result object,
table-driven against the reference command's message + exit per channel). Say that plainly
instead of grinding another cycle.