---
id: SKILL-9
sequence_id: 9
type: skill
title: sq-contract
status: Active
author: sq-contract
description: 'Working with contract items in this squad: lifecycle, commands, and
  role-specific guidance.'
created_at: '2025-05-20T11:00:00Z'
updated_at: '2025-05-20T11:00:00Z'
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

---
The `.md` files are sq-managed — never edit them by hand, and read them through
`sq contract <n> show`, never by opening the file. Items are addressed as
`sq contract <n> <verb>`. Set this item's body with `sq contract <n> body
-m "…"` (or `--file`); `--desc` sets only the short summary. Read anything back with `sq contract <n> show --full --comments` (full dossier, including discussion).

<!-- sq:body:end -->
