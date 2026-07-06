---
id: EPIC-12
sequence_id: 12
type: epic
title: Road to 1.0
status: Done
author: product-owner
priority: high
refs:
- BUG-22:depends-on
- BUG-21:depends-on
description: Define and prove the 1.0 stability promise across our public surfaces
created_at: '2026-06-10T12:40:41Z'
updated_at: '2026-07-06T11:33:35Z'
---
<!-- sq:body -->
## Why

Version 1.0 is not a feature milestone — it is a **stability promise**. The day we tag it, people
can build on squads without fearing the ground will move under them.

Our public surfaces are:

- the **durable `.md` format** — the items on disk are the user's data, and they outlive us;
- the **CLI grammar** — scripts and muscle memory built on `sq` keep working;
- the **`--json` output shapes** — tooling layered on top can rely on what it parses.

Everything else (Python import paths, generated `.claude/` files) is explicitly *not* part of the
promise.

## What this epic groups

The work splits in two: **deciding what we promise** (writing the contract down, closing the gaps
that would lock us into accidental promises — overrides, the second backend) and **proving it
holds** (machine-readable surface audit, migration corpus, hardening). When every feature here is
done, tagging 1.0 is a formality.

## Exit gates beyond the feature list

Two open bugs live outside this tree but gate the promise — 1.0 does not tag while they're open:

- **BUG-22** (counter regression / sequence-number reuse): the durability promise is hollow
  if a squad can quietly recycle identities.
- **BUG-21** (slug arguments unvalidated): the CLI grammar we freeze must not silently accept
  garbage actors.

Sequencing note: **FEAT-13** (the contract doc) is late-binding — it records the decisions the
other features make; it starts early as a living draft and closes last.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-11T07:52:26Z] Nina Product:
  - PO readiness review (2026-06-11): definition is complete — 13 features, every one with problem/value/scope/acceptance, 32 stories with acceptance criteria where decomposition is natural (hardening deliberately story-less), priorities set, dependencies machine-readable (depends-on/blocks). Verdict: ready for Ready, with three pre-transition nits for op-pierre:
  - 1) FEAT-19 is priced medium but is the keystone — 20, 26, 27, 37 and both UI epics depend on it; suggest high.
  - 2) FEAT-13 (contract doc) is late-binding: it records decisions made by 19/27/35/23/24/16/32 — recommend starting it early as a living draft but defining done as 'reflects final decisions', i.e. it closes last.
  - 3) The epic's real exit criteria include BUG-21 and BUG-22 (slug validation, counter regression) which live outside the tree — the durability promise is hollow while 22 is open. Suggest the epic body or a checklist note make the two bugs explicit gates.
  - Also: epic itself carries no priority — fine for an umbrella, flagging for consistency. No transitions performed; operator reviews next.
- [2026-06-11T07:54:51Z] Pierre Chat:
  - Readiness review accepted — definition approved, transitioning the epic, its thirteen features and the two gating bugs (BUG-21, BUG-22) to Ready.
- [2026-06-17T08:31:32Z] Catherine Manager:
  - Capstone FEAT-13 (stability contract) is Done and gated — it was the last open feature under this epic; all planned grammar/format-settling features have landed.
  - Deliberately keeping this epic OPEN, not closing it. 'Road to 1.0' completes when 1.0 is declared, and op-pierre is shipping 0.3.0 first to exercise the contract before committing to 1.0. Remaining gate to 1.0: settle the two pre-freeze reflog questions (REV-119 F3/F5) and complete real-world testing. Close this epic at the 1.0 cut.
- [2026-07-06T11:33:18Z] Catherine Manager:
  - All planned children Done (FEAT-13 capstone, FEAT-14/15/16/17/18/19/20/23/24/27/35/36/40/41/62/64/138/283/287/288). Road to 1.0 scope complete. Remaining hygiene-guard work (FEAT-237/264/289) tracked separately.
<!-- sq:discussion:end -->
