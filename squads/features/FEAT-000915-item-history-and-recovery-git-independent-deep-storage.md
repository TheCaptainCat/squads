---
id: FEAT-915
sequence_id: 915
type: feature
title: 'Item history and recovery: git-independent deep storage'
status: Draft
parent: EPIC-31
author: product-owner
refs:
- FEAT-33:depends-on
description: Deep, queryable history of item state over time so a bad write can be
  inspected and restored when the corpus is not a local git checkout
created_at: '2026-09-03T12:52:40Z'
updated_at: '2026-09-03T12:52:44Z'
---
<!-- sq:body -->
## Problem

Today the only recovery path for a bad write to this project — an agent that clobbered an
item's body, a destructive command run out of scope, a botched migration — is git: `git
reflog` finds the mutating commit, `git checkout` restores the file, `sq repair` rebuilds
the index from the recovered markdown. This works only because the corpus is local markdown
living inside a git working tree the operator directly controls.

Remote mode (FEAT-33) removes that precondition. The CLI becomes a client to a squads
server; the item corpus lives on a host the operator has no git checkout of. `sq reflog`
(the operation log) still records *that* a mutation happened and by whom, but it does not
hold the body as it stood before or after — it is a log of operations, not a store of
content. Once git is out of the loop, there is no path back to a prior version of an item
at all.

## Capability required

A first-class history mechanism inside squads itself, independent of git:

- Every item's body — and by implication the frontmatter state that travels with it — must
  be retrievable **as it stood at any earlier step**, not merely described by a log entry
  of what changed.
- A way to interact with that history: inspect a prior version, diff two versions, and
  restore from one.
- This must hold in both offline and remote mode — the recovery path cannot depend on the
  operator having their own git checkout of server-side storage.

## Why the existing reflog is not enough

`sq reflog` is an audit trail of *operations* (who ran what, when). The requirement is
explicit that this is insufficient: a complete history with a way to interact with it, not
just the reflog — deep storage of the bodies at each step, not just a log of what changed.
A record of what happened is not a store of the content itself.

## Open design questions (for the ADR — not answered here)

- Retention: how long is history kept, and is it configurable per squad?
- Storage cost: bodies captured at every step, for every item, compounds over the life of a
  squad — what's the growth model, and is there compaction or pruning?
- Granularity: is history kept per-item, or corpus-wide as a single append-only log?
- Interaction with the rebuildable-index invariant: `.squads.json` is rebuildable from
  frontmatter alone (`sq repair` proves this) — does a history store sit alongside that
  invariant unchanged, or does it change what "rebuildable" means?
- Interaction with `sq repair`: does repair ever consult history, or does history stay a
  recovery/audit facility entirely outside the repair path?
- Restore granularity: an item-level verb (roll one item back), a corpus-level verb (roll
  the whole squad back to a point in time), or both?

## Value

Without this, remote mode would ship with a strictly worse recovery story than offline mode
has today — a regression the team would discover only the first time a remote squad needs
recovering. This closes that gap ahead of remote mode shipping.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 915 add-story "As a <role>, I want … so that …"`; track with `sq feature 915 story <n> update --status <Status>`._

<!-- sq:stories -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
