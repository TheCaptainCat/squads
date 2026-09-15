---
id: MILE-934
sequence_id: 934
type: milestone
title: squads 0.16 - roles, not slugs
status: Draft
author: product-owner
refs:
- MILE-867
created_at: '2026-09-09T14:39:43Z'
updated_at: '2026-09-14T14:58:07Z'
---
<!-- sq:body -->
The next squads release after 0.15.

## Scope

- **Retiring the `-dev` pseudo-role.** A developer becomes an ordinary custom role identified
  by a declared capability instead of by a slug spelling (`is_dev_slug`'s `slug.endswith("-dev")`
  check, carried across dozens of call sites), with a migration for existing dev items. This is
  the same defect class the ref-kinds work already outlawed everywhere else in the engine — bind
  to a declared semantic property, never to a literal. Needs its own ADR and breakdown before
  it is buildable.
- **Validator catalog followers (ADR-864).** The remainder of ADR-864's accepted build order
  beyond the assignment grammar: re-tiering `no_status_banner` and the sub-entity title floor to
  catalog-only (FEAT-899), `field_value_declared` against frontmatter values (FEAT-900), the
  Part 2 catalog-only per-item validators — title, body, description, blockers (FEAT-901), and
  the squad-global validators — parent outcomes, cycles, WIP, staleness (FEAT-902). All four
  depend only on FEAT-898, the assignment grammar (Done): this line begins with a completed
  dependency rather than an open one, which is what makes carrying it here safe. Grouped under
  EPIC-540 alongside FEAT-898.
- **Type-catalog skew canary gap (BUG-935).** The VS Code skew canary's floor for
  `sq workflow types --json` omits two live keys: `labels` (modelled and consumed by the
  client's `domain/typeLabels.ts`, currently unprotected) and `lifecycle` (deliberately
  unmodelled, documented in `types.ts`, but also unprotected in the floor). The same blindness
  class BUG-896 closed on the graph/list surfaces, on a surface that fix did not reach.

## Does not belong here

- Anything that still fits inside 0.15.
- Docs sweeps, hygiene and refactors with no engine or adopter-visible effect — they ride
  whatever release they land in and need no target.
- Browser-client work, which has its own milestone and is not sequenced against this one.
<!-- sq:view:milestone_rollup -->
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-09T14:49:19Z] Nina Product:
  - Received FEAT-899, FEAT-900, FEAT-901, FEAT-902 and BUG-935 from MILE-867 (targets ref rm/add), per op-pierre's ruling in MILE-867's discussion. Body scope section extended with the validator-followers bullet and the BUG-935 bullet, plus the build-order note: all four followers depend only on FEAT-898, which is Done -- this line starts with a completed dependency, not an open one.
  - Title kept as 'squads 0.16 - roles, not slugs', deliberately: the -dev retirement is still the dominant line here -- its own ADR, a cross-cutting defect fix across dozens of call sites -- while the four followers and BUG-935 are secondary overflow carried for release-size reasons (op-pierre: 'a smaller release seems good'), not because they share a theme with the roles work. Same call MILE-867 made naming only its dominant line over a full validator-catalog build-out riding along.
  - Also dropped 'moved here from 0.15 unchanged in scope' from the -dev bullet while updating the body -- lifecycle/move narration that belongs in the discussion (already on record there), not in scope prose.
<!-- sq:discussion:end -->
