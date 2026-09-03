---
id: SKILL-834
sequence_id: 834
type: skill
title: sq-contract
status: Active
author: sq-contract
description: 'Working with contract items in this squad: lifecycle, commands, and
  role-specific guidance.'
created_at: '2026-08-26T15:14:16Z'
updated_at: '2026-08-26T15:14:16Z'
extra:
  slug: sq-contract
---
<!-- sq:body -->
# Contract items

The living functional contract: what the product does for a user, right now — the functional twin of the ADR set.

**Lifecycle:** Draft → Active → Superseded (+ Deprecated)

## Commands

```bash
sq create contract "…" --author product-owner
sq contract <n> status Active
sq feature <n> ref add PRD-… --kind implements   # link the contract slice a feature delivers
sq contract <n> refs --in   # every feature that has shaped this contract
```

## For Nina Product (`product-owner`)

**Enter** — before you act:
- Read the full item dossier: `sq contract <n> show --full --comments` (decisions and
  refinements often live in discussion comments, not the body — skipping this is how context
  gets missed).
- identify the capability / user-facing area this contract covers

**Do:**
- author it (`sq create contract "…" --author product-owner`)
- write the current functional behaviour, from the user's point of view, in the body
- keep it current: once a feature lands, rewrite the slice it touches in place

**Hand off:**
- `sq contract <n> status Active` once it reflects the live behaviour

**Watch for:**
- a contract describes behaviour, never architecture (that's the ADR set) or its own workflow state

## For Olivia Lead (`tech-lead`)

**Enter** — before you act:
- Read the full item dossier: `sq contract <n> show --full --comments` (decisions and
  refinements often live in discussion comments, not the body — skipping this is how context
  gets missed).
- read the contract slice(s) the feature being broken down implements

**Do:**
- update the touched slice as the feature lands (`sq feature <n> ref add PRD-… --kind implements`)

## For developers

**Enter** — before you act:
- Read the full item dossier: `sq contract <n> show --full --comments` (decisions and
  refinements often live in discussion comments, not the body — skipping this is how context
  gets missed).
- read the contract slice(s) the feature you're implementing shapes

**Do:**
- update the touched slice as the feature lands

## For Robert Architect (`architect`)

**Enter** — before you act:
- Read the full item dossier: `sq contract <n> show --full --comments` (decisions and
  refinements often live in discussion comments, not the body — skipping this is how context
  gets missed).
- read the contract set for the area under change

**Do:**
- watch cross-contract consistency; flag drift between contracts

---
The `.md` files are sq-managed — never edit them by hand, and read them through
`sq contract <n> show`, never by opening the file. Items are addressed as
`sq contract <n> <verb>`. Set this item's body with `sq contract <n> body
-m "…"` (or `--file`); `--desc` sets only the short summary. Read anything back with `sq contract <n> show --full --comments` (full dossier, including discussion).

<!-- sq:body:end -->
