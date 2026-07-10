---
id: SKILL-193
sequence_id: 193
type: skill
title: sq-bug
status: Active
author: sq-bug
created_at: '2026-06-24T20:14:34Z'
updated_at: '2026-06-24T20:14:34Z'
extra:
  slug: sq-bug
path: agents/skills/SKILL-000193-sq-bug.md
description: 'Working with bug items in this squad: lifecycle, commands, and role-specific
  guidance.'
---
<!-- sq:body -->
# Bug items

A defect: what's wrong, how to reproduce, expected vs actual.

**Lifecycle:** Open → InProgress → Fixed → Verified (+ WontFix, Blocked, Cancelled)

## Commands

```bash
sq create bug "…" --author <slug>
sq task <n> ref add BUG-… --kind fixes
sq bug <n> status InProgress
```

## For Mara Tester (`qa`)

**Enter** — before you act:
- Read the full item dossier: `sq bug <n> show --full --comments` (decisions and
  refinements often live in discussion comments, not the body — skipping this is how context
  gets missed).
- reproduce the defect and capture the exact steps

**Do:**
- file it (`sq create bug "…" --author qa`)
- in the body give repro steps + expected vs actual (`sq bug <n> body -m …`)
- set `--severity`/`--priority`

**Hand off:**
- once filed, `@tech-lead` to triage; once a fix task lands, verify it and confirm in a comment so the bug can close

## For developers

**Enter** — before you act:
- Read the full item dossier: `sq bug <n> show --full --comments` (decisions and
  refinements often live in discussion comments, not the body — skipping this is how context
  gets missed).
- read the repro steps; confirm you can reproduce it

**Do:**
- fix it inside a task and link it (`sq task <n> ref add BUG-… --kind fixes`)
- add a regression test

**Hand off:**
- when the fix is ready, move the task to InReview and `@reviewer`/`@qa`; the bug closes when the fix is verified

**Watch for:**
- track the fix on a task — don't implement straight off the bug

## For Olivia Lead (`tech-lead`)

**Enter** — before you act:
- Read the full item dossier: `sq bug <n> show --full --comments` (decisions and
  refinements often live in discussion comments, not the body — skipping this is how context
  gets missed).
- assess impact + severity against current work

**Do:**
- triage and prioritise; create the fix task and assign a developer

**Hand off:**
- once the fix task is created and assigned, `@<tech>-dev` to start the fix

## For Paul Reviewer (`reviewer`)

**Enter** — before you act:
- Read the full item dossier: `sq bug <n> show --full --comments` (decisions and
  refinements often live in discussion comments, not the body — skipping this is how context
  gets missed).
- read the bug + the fix task's changes

**Do:**
- review the fix for correctness and a regression test before it lands

**Watch for:**
- make sure the root cause is fixed, not just the symptom

---
The `.md` files are sq-managed — never edit them by hand. Items are addressed as
`sq bug <n> <verb>`. Set this item's body with `sq bug <n> body
-m "…"` (or `--file`); `--desc` sets only the short summary. Read anything back with `sq bug <n> show --full --comments` (full dossier, including discussion).

<!-- sq:body:end -->
