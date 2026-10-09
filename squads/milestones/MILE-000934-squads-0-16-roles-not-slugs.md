---
id: MILE-934
sequence_id: 934
type: milestone
title: squads 0.16 - roles, not slugs
status: InProgress
author: product-owner
refs:
- MILE-867
created_at: '2026-09-09T14:39:43Z'
updated_at: '2026-10-09T19:14:14Z'
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
- [2026-09-29T14:21:20Z] Catherine Manager:
  - Moved to InProgress: 0.16 kicked off with op-pierre; bug fixes under way (TASK-968 Done, TASK-969 in review).
- [2026-10-09T15:21:11Z] Pierre Chat:
  - Scope and sequencing calls for 0.16, taken 2026-10-09:
    
    - The next build is retiring the `-dev` pseudo-role, starting with its ADR.
    - REV-956 and REV-958 run now, by the reviewer, before new feature work starts. The architect and the tech writer stay as the ones who scoped them.
    - TASK-954, BUG-951 and FEAT-961 are pulled into this milestone.
    - The board notice telling agents to use `uv run sq` is replaced: board operations go through the released tool.
- [2026-10-09T15:26:22Z] Pierre Chat:
  - 2026-10-09: no developer starts after the current round (two reviews, two bug verifications, the feature readiness pass, the FEAT-961 ruling). The next step is proposed to me and waits for my approval.
- [2026-10-09T18:40:09Z] Pierre Chat:
  - 2026-10-09: next round approved with no developer: the ADR-983 revision and the dated notes on ADR-541 and ADR-492, FEAT-902 brought in line with ADR-982, a bug for the [dev] override reverted by sync, and Draft developer tasks for TASK-954 and BUG-951 only. No developer starts until I have seen those tasks.
- [2026-10-09T19:14:14Z] Pierre Chat:
  - 2026-10-09: development plan for this milestone approved, with the validator features in a parallel worktree. Approval covers the no-code preparation; the first developer still waits for my go.
    
    Build order:
    1. TASK-954, the reconcile path for a behind-schema squad, after the architect amends ADR-955.
    2. The import-graph guard, then the two behaviour-neutral moves from ADR-984 (role views, role derivations).
    3. The `-dev` retirement proper, which fixes BUG-985 and creates this release's migration runner.
    4. FEAT-976, then FEAT-977.
    5. FEAT-980, FEAT-961 and FEAT-966, with the VS Code setting and canary keys.
    6. FEAT-899, FEAT-901, FEAT-900 and FEAT-902, in a second worktree alongside steps 3 to 5.
    7. The REV-958 help-text work: the writer's strings, then one developer task.
    8. Release preparation.
    
    Rules: one Python stream outside the validator worktree; one independent review per feature, cleared before the next feature starts; one migration step for the release, amended by each contributor.
    
    Review findings: the import guard, the role moves and the write-count guard are in this milestone, as is REV-958 except the finding about a per-item verb's help needing a real item, which gets its own item. The structural refactors and the comment pass are deferred past this milestone, each with a home item.
<!-- sq:discussion:end -->
