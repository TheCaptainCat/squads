---
id: MILE-934
sequence_id: 934
type: milestone
title: squads 0.16 - one roster, flat files
status: InProgress
author: product-owner
refs:
- MILE-867
created_at: '2026-09-09T14:39:43Z'
updated_at: '2026-10-16T13:31:17Z'
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
- [2026-10-11T20:15:29Z] Pierre Chat:
  - 2026-10-11: rulings before the first developer starts.
    
    - The first developer starts on TASK-954. Its fix for BUG-988 ships with 0.16; there is no 0.15.1 patch.
    - The working version stays 0.15.0 until release preparation, and is bumped to 0.16.0 there.
    - This repository's own squad is migrated to the 0.16 schema once, at release preparation, after every contributor has amended the runner.
    - A developer's model stays as stored at `sq dev add` (ADR-984 as written). Only the colour half of BUG-985 is fixed by the retirement; story 8 of FEAT-986 is reworded to say so.
    - TASK-989 corrects the three out-of-date passages in CLAUDE.md that the structural review found.
    - `sq check` should report two distinct ids sharing one number; that and the misleading stale-index message are filed as bugs.
    - ADR-71, ADR-622, ADR-766, ADR-864 and ADR-783 each get the dated note ADR-663 carries about `sq repair` behind the schema gate.
- [2026-10-11T20:32:05Z] Pierre Chat:
  - 2026-10-11: the manager drives the build from here, in the approved order, without waiting for my go between steps. Still mine: pushing, the version bump, migrating this repository's squad, publishing, and the ruling on the manifest-freshness checks before TASK-990 changes bundled files.
- [2026-10-12T05:16:15Z] Pierre Chat:
  - 2026-10-12: the working version is bumped to 0.16.0 before TASK-990 changes bundled files, once TASK-989 is in. This replaces my answer of 2026-10-11 to bump at release preparation; the manifest is then regenerated normally during the build.
- [2026-10-12T06:26:45Z] Pierre Chat:
  - 2026-10-12: the build order changes, and so does the timing of the version bump.
    
    - The working version is bumped to 0.16.0 after the comment-header migration (FEAT-980) is in. This replaces my two earlier answers on the bump.
    - FEAT-980 therefore moves up: it is built right after TASK-954, before the developer-role retirement. It creates this release's migration runner and the 0.16 schema; the retirement and the origin work amend that runner afterwards.
    - Nothing that changes a bundled file is built before the bump. That covers TASK-990 and the `blocked` flag on status roles in FEAT-901.
    
    Main stream, in order: TASK-954, FEAT-980, the bump, TASK-989, TASK-990, FEAT-976, FEAT-977, then FEAT-961 and FEAT-966. The validator features continue in their own worktree, with any bundled-file change held until after the bump.
    
    On the validator rulings of this date: blocked stays a flag a role declares (I looked at it again after asking why it is not derived from ref kinds: the check compares the hand-set Blocked status with the dependency edges, so it needs to know which status that is).
- [2026-10-15T18:39:05Z] Pierre Chat:
  - 2026-10-15: frontmatter is already scoped by type, so the nested extra block has no reason to exist. Every key it holds is promoted to a top-level frontmatter field.
- [2026-10-15T18:41:35Z] Pierre Chat:
  - 2026-10-15: promoting the extra keys to top-level fields ships in 0.16, carried by this release migration runner.
- [2026-10-15T18:44:48Z] Pierre Chat:
  - 2026-10-15, on the frontmatter shape once `extra` goes away:
    
    - **Core keys**: the ones common to all items and used by the sq internals.
    - **Per-type keys**: generic, declared in the specs, not hardcoded per type.
    - The frontmatter is parsed against the core keys and the declared ones, and validated.
    - Unknown keys are kept silently.
- [2026-10-15T18:46:02Z] Pierre Chat:
  - 2026-10-15: the risk to guard against: a key removed from a custom spec must not then be removed from the frontmatter on the next save.
- [2026-10-15T19:09:10Z] Robert Architect:
  - 2026-10-15: ADR-1007 (flat frontmatter, no extra block) adds one step to the main stream of 2026-10-12, as ruled on ADR-1007 by op-pierre: after the 0.16.0 bump and before TASK-989. Main stream: TASK-954, FEAT-980, the bump, the ADR-1007 flattening (first frontmatter step of the 0.16 runner), TASK-989, TASK-990, FEAT-976, FEAT-977, then FEAT-961 and FEAT-966. @manager: it has no feature or task yet.
- [2026-10-15T19:11:19Z] Pierre Chat:
  - 2026-10-15: --dir is replaced by git-style -C (run sq as if started from that folder), decided by ADR, shipped in 0.16. The F26 fix in TASK-954 lands first so 0.16 has no gate bypass meanwhile.
- [2026-10-15T19:16:11Z] Pierre Chat:
  - 2026-10-15: -C names the folder that holds .squads.toml (the project root). No walk-up: if that folder has no .squads.toml, sq refuses.
- [2026-10-15T19:16:53Z] Pierre Chat:
  - 2026-10-15: correction to my previous comment: -C keeps the walk-up (git-style, as if sq were started from that folder). It refuses if no .squads.toml is found from there.
- [2026-10-15T19:25:09Z] Pierre Chat:
  - 2026-10-15, on editing comments (new ADR and feature, in 0.16 after FEAT-980):
    
    - Comments can be edited and deleted, on every type.
    - Each comment gains an `index` attribute, computed on load and never stored. A comment is addressed by its index, and the index shifts once an earlier comment is deleted.
    - Rendered views show the index with a hash (`#3`); `--json` carries it as a key.
    - The author must still be given (`--as`). If it does not match the comment's original author, the CLI raises.
- [2026-10-15T19:31:40Z] Pierre Chat:
  - 2026-10-15, amending my comment-editing ruling of today:
    
    - A comment is addressed by a short hash, like a git commit, in place of the positional index. The hash is computed on load over what an edit cannot change (item, author slug, timestamp), and is never stored. Renders show the short form; `--json` carries the hash; any unique prefix addresses a comment.
    - Two comments by the same author at the same time share a hash. That is always a mistake: they are effectively the same comment.
      - On write: a comment that would produce an existing hash is refused.
      - On load: tolerated silently.
      - On edit: the two are merged into one comment carrying the new text.
      - On delete: both are deleted.
- [2026-10-15T19:31:53Z] Robert Architect:
  - 2026-10-15: ADR-1013 drafts the comment edit and delete ruling of 2026-10-15T19:25:09Z. It places that work in the main stream after FEAT-977 and before FEAT-961. It needs FEAT-980's slug header for the author match, it changes bundled guidance so it comes after the bump, and FEAT-977 creates the roster comment verbs it extends. It changes no schema and no migration runner. @manager: it has no feature or task yet, and it raises a concurrency option for the operator.
- [2026-10-15T19:35:28Z] Robert Architect:
  - 2026-10-15: correction to my comment above. ADR-1013 now drafts the amended ruling of 2026-10-15T19:31:40Z (short-hash addressing). The verbs still go after FEAT-977 and before FEAT-961. @manager, one point is time-sensitive: millisecond comment timestamps, and disambiguating the 15 existing same-second collisions, belong in FEAT-980's grammar and migration, so the operator should rule on them before FEAT-980 starts.
- [2026-10-15T19:56:33Z] Robert Architect:
  - 2026-10-15: withdrawn: my earlier note asking for millisecond timestamps and a collision migration in FEAT-980. The ruling of 2026-10-15T19:54:29Z on ADR-1013 puts the comment text in the hash, so FEAT-980 takes nothing from ADR-1013 beyond its existing slug header. The comment-editing verbs stay after FEAT-977 and before FEAT-961. @manager
- [2026-10-16T08:34:44Z] Pierre Chat:
  - 2026-10-16: asked for a global review pass on the adopter docs (suspects parts are outdated or wrong). Five reviewer audits launched (Paul on Fable), findings only; fixes by the writer, with overrides/workflow/stability fixes held until after FEAT-1016 where flattening touches them.
- [2026-10-16T11:16:28Z] Pierre Chat:
  - 2026-10-16: set pytest tmp_path_retention_count = 1 (the /tmp tmpfs filled during a run on 2026-10-15).
- [2026-10-16T11:52:30Z] Pierre Chat:
  - 2026-10-16: renamed to 'squads 0.16 - one roster, flat files'; the old title no longer covered the release's content.
- [2026-10-16T12:24:23Z] Pierre Chat:
  - 2026-10-16: bugs for 0.16 are BUG-994, BUG-1000 (with its duplicate BUG-1037 folded in), BUG-1049, BUG-1057 and BUG-1058. Every other open bug moves to 0.17 (MILE-1051).
- [2026-10-16T12:54:20Z] Pierre Chat:
  - 2026-10-16: authorised the manager to do the 0.16.0 version bump. Migrating this repo's squad, pushing and publishing stay mine.
- [2026-10-16T13:01:10Z] Pierre Chat:
  - 2026-10-16: 0.16 keeps its full scope as planned; no features move to 0.17.
- [2026-10-16T13:31:17Z] Pierre Chat:
  - 2026-10-16: authorised a one-line hand edit restamping squads/.overrides/workflow.toml from override-base 0.15.0 to 0.16.0 (no verb can restamp it while this squad is behind the schema; content unchanged).
<!-- sq:discussion:end -->
