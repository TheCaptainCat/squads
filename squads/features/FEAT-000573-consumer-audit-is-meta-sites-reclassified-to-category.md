---
id: FEAT-573
sequence_id: 573
type: feature
title: 'Consumer audit: is_meta sites reclassified to category'
status: Draft
parent: EPIC-538
author: product-owner
priority: medium
refs:
- FEAT-567
- FEAT-533
created_at: '2026-07-22T08:39:40Z'
updated_at: '2026-07-22T09:47:53Z'
---
<!-- sq:body -->
## Capability

Reclassify the ~15 sites that today overload `not is_meta` for two different
meanings ("creatable/trackable" vs "burn-down work only"), pointing each one
precisely at either "roster vs not" or "category-specific behaviour" now that
`category` (FEAT-567) disambiguates them. This is the audit FEAT-533 US1 flagged
and handed off rather than doing inline (FEAT-533 scoped it as adjacent/CLI-tree
concern, out of its own engine-statelessness scope).

## Why

Per ADR-541: the `category` axis exists precisely so this reclassification can be
done precisely instead of mechanically. Each consumer site cared about one of two
different splits that the boolean smeared together; leaving any site still keyed
on a derived `is_meta`-equivalent (or a raw type-name list) instead of `category`
re-introduces the same conflation bug this whole epic exists to fix.

## Scope — known sites to audit (non-exhaustive, confirm full list at kickoff)

- TUI tree grouping (superseded by FEAT-570's records-root work, but confirm no
  other TUI site still branches on `is_meta`)
- VS Code extension tree/provider selection
- `sq create` — type eligibility / self-author bypass for roster types
- retype / rename logic
- roster service (`_roles/`, agent lifecycle) — literal roster-name bindings
  stay (ADR-541: roster is locked, dispatched by literal name), but confirm no
  site uses `not is_meta` where it means "roster" only by coincidence
- playbook coverage checks
- backend pointer-file generation (`_backends/`)
- prefix/folder maps
- Any site still reading `ItemSpec.is_meta` after FEAT-567 removes/derives it

## Acceptance

- No source site references `is_meta` (removed by FEAT-567) or re-derives an
  equivalent boolean from `category` where the *actual* intent is one of the two
  disambiguated meanings — each site reads `category` (or the specific
  roster-literal-name binding where that's genuinely what's meant) directly.
- `sq check`, generated `sq-<type>` skills, backend pointer files, and both UI
  trees are unaffected in output for the bundled spec (behaviour-preserving
  reclassification, not a behaviour change).
- A dropped/renamed/re-prefixed custom type (once droppable, per this epic's
  wider scope) is absorbed cleanly by every audited site — no orphan, no
  traceback — per EPIC-538's "no dropped item may break sq" invariant.

## Dependencies / ordering

- **Depends on FEAT-567 (Phase A)** — needs `category` to exist as the
  replacement target for every site currently on `is_meta`.
- **Phase C, parallelizable** against the other EPIC-538 Phase C features, but
  touches the same call sites as FEAT-569 (custom records types) and FEAT-570
  (UI trees) — coordinate to avoid duplicate/conflicting edits to shared files
  (e.g. don't both rewrite the TUI tree-grouping site independently).
- Traces back to FEAT-533 US1's handoff (the consumer audit that feature scoped
  out as CLI/UI-surface concern, not engine-statelessness scope).
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 573 add-story "As a <role>, I want … so that …"`; track with `sq feature 573 story <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:stories -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T09:44:18Z] Pierre Chat:
  - Scope addition: drop the word 'meta' repo-wide — fold into this consumer audit (it already touches these sites). Rename META_OPERATOR/META_ROLE/META_SKILL → ROSTER_* and their ~15 by-name dispatch sites; purge 'meta'/'meta-types' from comments, docstrings, docs, and CLAUDE.md (use 'roster' / 'roster category'); add a one-line naming convention to CONTRIBUTING (no 'meta'; use 'roster'). The item_is_meta→item_is_roster accessor rename is handled in Phase A (FEAT-567). Historical ADR text that documents the is_meta→category transition may keep the old name in that context.
- [2026-07-22T09:47:53Z] Pierre Chat:
  - Also fold in the 'work_types()' accessor rework: it's historic framing — 'non-roster = work+records' — which lumps exactly what the category axis splits (a records type is not a work type). Out-of-scope for Phase A (FEAT-567 leaves it as-is); handle it here as part of the consumer reclassification — rename to a category-accurate name and/or replace each call site with the precise category query (roster-vs-not / is-work / is-records) rather than the lossy lump. Becomes a concrete task when this feature is cut.
<!-- sq:discussion:end -->
