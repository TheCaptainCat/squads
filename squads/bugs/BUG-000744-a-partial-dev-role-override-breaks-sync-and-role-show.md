---
id: BUG-744
sequence_id: 744
type: bug
title: A partial dev-role override breaks sync and role show
status: Open
author: qa
description: resolve_dev_role merges a partial tech-dev override, but sync and role
  show go through resolve_role which has no dev base
created_at: '2026-08-15T15:14:29Z'
updated_at: '2026-08-15T15:14:50Z'
---
<!-- sq:body -->
Found by the python-dev while fixing REV-736 F49, reported rather than fixed because the naive repair renames live roles. Driven.

A partial dev-role override is a documented shape: `resolve_dev_role` merges `.overrides/roles/<tech>-dev.toml` over the generated base, and `sq dev add` honours it. But `sq sync` and `sq role <slug> show` both resolve through `resolve_role`, which has no dev base to merge onto.

Reproduction: `sq dev add --tech python`, then write `.overrides/roles/python-dev.toml` containing only `title = "Senior Python developer"`. Both commands exit 1 with `missing required fields: full_name, description, mission` -- for an override the tool documents as partial.

Why it is not a one-liner: `_refresh_catalog_extra` documents that it skips dev roles, and implements that by catching `RoleNotFoundError`, which only fires when NO override file exists -- so a partial file takes a different path entirely. And `resolve_role` cannot simply be widened, because sync merges the resolved definition to_extra() onto the item while `dev_role(tech)` regenerates a name from the pool, so a naive widening renames live dev roles.

Same family as the sweep findings this release closed: a declared, documented capability that one consumer honours and another does not.

Full analysis is on REV-736 F49 body.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-15T15:14:50Z] Catherine Manager:
  - Not scoped to 0.13 unless op-pierre says otherwise. The three remaining 0.13 bugs are fixed, this one was found after that line was drawn, and the fix needs a design call about the dev-role resolution seam rather than a patch. Filed so it is not lost.
<!-- sq:discussion:end -->
