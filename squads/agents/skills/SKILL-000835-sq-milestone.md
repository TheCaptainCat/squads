---
id: SKILL-835
sequence_id: 835
type: skill
title: sq-milestone
status: Active
author: sq-milestone
description: 'Working with milestone items in this squad: lifecycle, commands, and
  role-specific guidance.'
created_at: '2026-08-26T15:33:00Z'
updated_at: '2026-08-26T15:33:00Z'
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

## For Nina Product (`product-owner`)

**Enter** — before you act:
- Read the full item dossier: `sq milestone <n> show --full --comments` (decisions and
  refinements often live in discussion comments, not the body — skipping this is how context
  gets missed).
- identify the target worth naming — a release, a cycle, a cutoff

**Do:**
- author it (`sq create milestone "…" --author product-owner`)
- set the target date (`sq milestone <n> update --set target_date=YYYY-MM-DD`)
- `sq milestone <n> status InProgress` once work is being aimed at it

**Hand off:**
- `@tech-lead` once the milestone exists, so incoming work can join it

**Watch for:**
- membership is never edited here — `sq milestone <n> show` reads the live roll-up, it isn't set

## For Olivia Lead (`tech-lead`)

**Enter** — before you act:
- Read the full item dossier: `sq milestone <n> show --full --comments` (decisions and
  refinements often live in discussion comments, not the body — skipping this is how context
  gets missed).
- read the roll-up (`sq milestone <n> show`) for what's still outstanding

**Do:**
- join a task to it as it's scoped (`sq task <n> ref add MILE-… --kind targets`)

**Hand off:**
- `@product-owner` if the roll-up shows the target slipping

---
The `.md` files are sq-managed — never edit them by hand, and read them through
`sq milestone <n> show`, never by opening the file. Items are addressed as
`sq milestone <n> <verb>`. Set this item's body with `sq milestone <n> body
-m "…"` (or `--file`); `--desc` sets only the short summary. Read anything back with `sq milestone <n> show --full --comments` (full dossier, including discussion).

<!-- sq:body:end -->
