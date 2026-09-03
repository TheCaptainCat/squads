---
id: SKILL-10
sequence_id: 10
type: skill
title: sq-milestone
status: Active
author: sq-milestone
description: 'Working with milestone items in this squad: lifecycle, commands, and
  role-specific guidance.'
created_at: '2025-05-20T11:00:00Z'
updated_at: '2025-05-20T11:00:00Z'
extra:
  slug: sq-milestone
---
<!-- sq:body -->
# Milestone items

A named target for a set of work — a release, a cycle, anything work can be aimed at. Membership rides a `targets` ref on the work item; the milestone file never lists its own members.

**Lifecycle:** Draft → InProgress → Done (+ Cancelled)

## Commands

```bash
sq create milestone "…" --author product-owner
sq milestone <n> update --set target_date=2026-12-01
sq <type> <n> ref add MILE-… --kind targets   # from the work item joining it
sq milestone <n> show   # the delivered/outstanding roll-up, computed fresh
```

---
The `.md` files are sq-managed — never edit them by hand, and read them through
`sq milestone <n> show`, never by opening the file. Items are addressed as
`sq milestone <n> <verb>`. Set this item's body with `sq milestone <n> body
-m "…"` (or `--file`); `--desc` sets only the short summary. Read anything back with `sq milestone <n> show --full --comments` (full dossier, including discussion).

<!-- sq:body:end -->
