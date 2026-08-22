---
id: BUG-744
sequence_id: 744
type: bug
title: A partial dev-role override breaks sync and role show
status: Verified
author: qa
description: resolve_dev_role merges a partial tech-dev override, but sync and role
  show go through resolve_role which has no dev base
created_at: '2026-08-15T15:14:29Z'
updated_at: '2026-08-21T16:57:36Z'
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
- [2026-08-21T12:35:53Z] Pierre Chat:
  - In scope for 0.14.0: op-pierre pulled all five open bugs into the next release, overriding the earlier per-bug deferral to a later cycle.
- [2026-08-21T12:51:33Z] Robert Architect:
  - Design settled on ADR-754 (Proposed): resolution takes the dev base as an explicit input, built from the live item (tech + stored full_name), so `dev_role()` is never re-rolled for a role that already exists — driven, a partial override on the second dev renames Ada Typescript to Elias Typescript today. The sync skip becomes a no-op instead of a RoleNotFoundError catch.
  - One call for op-pierre: I ruled that a `<tech>-dev.toml` which explicitly declares full_name DOES rename the live dev role on sync (consistent with a bundled-role override), while omitting it preserves the name. Say if a dev role name should instead be immutable once assigned.
- [2026-08-21T15:59:46Z] Catherine Manager:
  - Fix landed in fb92ef5 on release/0.14 (TASK-751). Drove the reproduction independently in a fresh squad: with a title-only python-dev.toml override, role show / sync / check all exit 0, the title override applies, the live name Elias Python is preserved, and the show card renders in full instead of the three-line fallback. Confirmed _itemfile._exempt_extra_keys is unchanged at {X.SKILLS} with only its stale comment corrected, per ADR-754. Awaiting QA verification.
- [2026-08-21T16:57:23Z] Mara Tester:
  - Drove the exact reproduction in a fresh squad (sq init --default-names, sq dev add --tech python, title-only python-dev.toml): sq role python-dev show, sq sync, and sq check all exit 0; the title override applies and the full show card renders (not the 3-line fallback).
  - Confirmed live name preserved in BOTH frontmatter (extra.full_name: Elias Python) and the index after sync.
  - Confirmed the ruled behaviour: adding full_name = "Zoe Python" to the same override file renames the role on sync (frontmatter extra.full_name and index both update to Zoe Python; sq check stays clean); omitting it never renamed.
  - Residual noted, not blocking this bug's acceptance: after the full_name rename, the item's own top-level title: field in frontmatter stays the old name (Elias Python) — only extra.full_name is refreshed. sq list / sq show still print the stale item.title, while CLAUDE.md's roster and sq role show (which resolve through the catalog) correctly show Zoe Python. Consistent with _refresh_catalog_extra's documented scope (extra only), but visibly inconsistent to an adopter. Not filing separately per this pass's scope; flagging for triage.
<!-- sq:discussion:end -->
