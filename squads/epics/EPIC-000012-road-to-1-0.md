---
id: EPIC-000012
sequence_id: 12
type: epic
title: Road to 1.0
status: Ready
author: product-owner
priority: high
refs:
- BUG-000022:depends-on
- BUG-000021:depends-on
description: Define and prove the 1.0 stability promise across our public surfaces
created_at: '2026-06-10T12:40:41Z'
updated_at: '2026-06-11T07:54:52Z'
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

- **BUG-000022** (counter regression / sequence-number reuse): the durability promise is hollow
  if a squad can quietly recycle identities.
- **BUG-000021** (slug arguments unvalidated): the CLI grammar we freeze must not silently accept
  garbage actors.

Sequencing note: **FEAT-000013** (the contract doc) is late-binding — it records the decisions the
other features make; it starts early as a living draft and closes last.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-11T07:52:26Z] Nina Product:
  - PO readiness review (2026-06-11): definition is complete — 13 features, every one with problem/value/scope/acceptance, 32 stories with acceptance criteria where decomposition is natural (hardening deliberately story-less), priorities set, dependencies machine-readable (depends-on/blocks). Verdict: ready for Ready, with three pre-transition nits for op-pierre:
  - 1) FEAT-000019 is priced medium but is the keystone — 20, 26, 27, 37 and both UI epics depend on it; suggest high.
  - 2) FEAT-000013 (contract doc) is late-binding: it records decisions made by 19/27/35/23/24/16/32 — recommend starting it early as a living draft but defining done as 'reflects final decisions', i.e. it closes last.
  - 3) The epic's real exit criteria include BUG-000021 and BUG-000022 (slug validation, counter regression) which live outside the tree — the durability promise is hollow while 22 is open. Suggest the epic body or a checklist note make the two bugs explicit gates.
  - Also: epic itself carries no priority — fine for an umbrella, flagging for consistency. No transitions performed; operator reviews next.
- [2026-06-11T07:54:51Z] Pierre Chat:
  - Readiness review accepted — definition approved, transitioning the epic, its thirteen features and the two gating bugs (BUG-000021, BUG-000022) to Ready.
<!-- sq:discussion:end -->
