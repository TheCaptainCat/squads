---
id: MILE-867
sequence_id: 867
type: milestone
title: squads 0.15 - views, rebuilt
status: InProgress
author: product-owner
created_at: '2026-09-02T08:03:36Z'
updated_at: '2026-09-09T14:50:13Z'
---
<!-- sq:body -->
The next squads release after 0.14. It holds the engine and vocabulary work that was
deliberately kept out of 0.14 to protect stability at the release point, plus the
follow-through on decisions taken during it.

## Scope

- **Views (ADR-880) is the main line.** A view becomes a source plus a template, rendered at a
  tag placed in a document body; the projection layer FEAT-693 built one release ago is
  deleted. Grouped under EPIC-897 (a new epic — FEAT-693 was never parented under an existing
  one). Six features (FEAT-903 through FEAT-908): the widened source layer, the projection
  layer's deletion, the tag mechanism (a dedicated placement verb, read-time expansion, and the
  `sq check` integration ADR-880's amendment obliges), the collapse of role/skill text onto it,
  the milestone seed-and-migration, and the adopter-facing upgrade path off the retired
  grammar.
- **The validator catalog's foundation (ADR-864).** FEAT-898 — a validator selection declares
  its level, its threshold/parameter, and its required context, instead of these being fixed by
  a module constant and a naming sentinel. This is the gating dependency the rest of ADR-864's
  catalog build-out sequences behind. Grouped under EPIC-540, reopened — its original outcome
  (a declarative, pluggable validator catalog) was closed against its seed catalog's children,
  not against the full outcome ADR-864 found incomplete.
- **The "record no adopter promise on purpose" bullet folds into FEAT-898** and is not a
  separate line item. The bundled spec already made the feature→contract `implements` currency
  check opt-in rather than a bundled default (a project that wants the obligation adds it
  itself) — that was the immediate fix. FEAT-898's declared-level dimension generalizes the same
  answer to every validator in the catalog, not just this one: any check can be selected at a
  level a project actually means, rather than being an all-or-nothing bundled default.
- **One parallel client-UI win.** FEAT-690 (memory/board oversight views in the VS Code
  extension and `sq ui`) — client-surface work independent of the two engine lines above,
  costing them nothing and running alongside.
- **Two verified client-test-quality bugs.** BUG-895 (the command-guidance guard misreporting a
  broken corpus as missing guidance) and BUG-896 (the skew canary asserting a superset instead
  of an exact key set on two of three surfaces).

## Does not belong here

- Anything that still fits inside 0.14.
- Docs sweeps, hygiene and refactors with no engine or adopter-visible effect — they ride
  whatever release they land in and need no target.
- Browser-client work, which has its own milestone and is not sequenced against this one.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-03T08:45:08Z] Pierre Chat:
  - 0.15 is the views release: ADR-880 is the main focus, because the view system is useless as it stands. The ADR-864 validator catalog rides along and is built out in full, including the Part 2 catalog-only members. The parent-cycle hang is fixed here, not in a 0.14.1 patch.
- [2026-09-03T09:07:03Z] Nina Product:
  - 0.15 backlog authored for the ADR-864 side; ADR-880 (views) held per op-pierre's stop instruction pending Robert's ruling on the tag-location amendment.
  - Validator catalog: EPIC-540 reopened, 5 features (FEAT-898..902) covering the full accepted build order -- assignment grammar (gates the rest) -> re-tier two floor members -> field_value_declared -> 8 Part-2 catalog-only members -> 5 squad-global members. label_declared recorded as excluded on prerequisite (no label vocabulary exists), not scheduled.
  - Views: EPIC-897 created (new, not reopened -- FEAT-693 was never parented). No features created under it yet; held per instruction.
  - Sizing verdict, 864 side only: buildable in 0.15 as its own line -- five features, the first a real gating dependency the rest sequence behind, the last four largely mechanical once it lands. Full verdict including the views side goes in my handback to op-pierre once ADR-880 is re-ruled.
- [2026-09-03T09:16:39Z] Nina Product:
  - Views half unblocked and authored per Robert's amendment ruling (tag stays inside sq:body). Body rewritten to drop the transient hold narrative -- it belongs in this discussion, not durable scope prose.
  - EPIC-897 now carries 6 features (FEAT-903..908) covering: source widening + per-source --json, projection-layer deletion, the tag mechanism (placement verb + expansion + sq check integration -- the amendment's three obligations), the role/skill collapse, the milestone seed+migration (now running through the placement verb, not a bespoke write), and the FEAT-693 adopter upgrade path.
- [2026-09-03T09:36:38Z] Pierre Chat:
  - Scope ruled: everything stays in 0.15. Both lines in full -- the six views features and all five validator-catalog features. Nothing deferred to 0.16. Prepare the milestone before any work is launched.
- [2026-09-03T09:36:40Z] Catherine Manager:
  - For the record: product-owner sized both lines together as not comfortably deliverable, and I recommended holding FEAT-899 through FEAT-902 for 0.16 (FEAT-898 cannot be cut -- FEAT-907 depends on it). op-pierre overruled both and took the full scope knowingly. Sequencing is mine to manage: ADR-880 has dispatch priority over the catalog line.
- [2026-09-03T09:46:35Z] Nina Product:
  - Prepared for launch, per op-pierre's full-scope ruling. Left Draft.
    
    **Retitled**: "squads 0.15 - views, rebuilt" (per the new board convention, #17). Went views-only rather than naming both lines: op-pierre's own ruling comment called 0.15 "the views release" with the catalog "riding along" — naming only the dominant line matches how MILE-836 named its theme (one umbrella phrase, not an enumeration) and stays honest that this is the main line per the ruling, not a description of everything inside.
    
    **Priorities set on all 11 features** (urgent > high > medium > low), encoding dispatch order:
    - urgent: FEAT-903, FEAT-904, FEAT-905 — the three ungated roots of the main line.
    - high: FEAT-898 (validator-line root, but promoted above its own line's followers because it cross-gates FEAT-907), FEAT-906 (next views step, needs 903+905).
    - medium: FEAT-907, FEAT-908 — views line, but each needs two prior features landed first.
    - low: FEAT-899, FEAT-900, FEAT-901, FEAT-902 — validator-line followers, all gated only by FEAT-898.
    Also added the missing `depends-on` refs FEAT-899/900/901/902 → FEAT-898: each already said "Depends on FEAT-898" in its own body, but only FEAT-907/908 had that dependency encoded as a ref, so `sq blocked` was silent on 4 of 5 real edges in the catalog line. Now all six task-specified edges resolve in `sq blocked`.
    
    **Carried members — recommend dropping all three from MILE-867**, none of them yours to decide:
    - **BUG-895** (command-guidance guard misreports a broken corpus) — recommend drop. Its own severity write-up says nothing is presently broken and no shipped behaviour is affected; it's a test/guard-quality gap, not engine or adopter-visible work. Matches the milestone's own "does not belong here" line for hygiene fixes needing no target verbatim.
    - **BUG-896** (VS Code skew canary, superset vs exact assertion) — recommend drop, same reasoning: latent, "nothing is wrong today," client test-quality only. No connection to either scope line.
    - **FEAT-690** (memory/board oversight views in the extension and sq ui) — recommend drop from this milestone. It's fully speced and ready to break down, but it's client-surface UI work, not "engine and vocabulary work" — doesn't fit MILE-867's own opening definition, and has no dependency to or from either scope line. It reached 0.15 by being moved off 0.14 during scoping, not by thematic fit. Worth scheduling — just not here.
    
    **Recommended target date: 2026-09-24 (three weeks out).** Reasoning: v0.13.1→v0.14.0 took 12 calendar days for 7 features (33 delivered items incl. tasks/bugs). 0.15 carries 11 features / 53 authored user stories — about 1.5-1.8x 0.14's feature volume, with two independent gating roots (FEAT-905 for views, FEAT-898 for validators) that can dispatch in parallel from day one, each opening a second wave that also runs in parallel across both lines. Scaling 0.14's cycle by that volume ratio lands in the 18-24 day range; I'm recommending the top of that range since 0.14 had its groundwork ADRs further pre-digested and this is a rough scale, not a measured estimate — treat it as a starting point to adjust against actual dispatch velocity, not a commitment.
    
    **Coherence check**: `sq check` clean. Every feature carries `targets` (MILE-867) + `implements` (ADR-864 or ADR-880), correctly parented to EPIC-540 or EPIC-897, statuses match their Draft parents. One thing flagged, not fixed: **EPIC-540 itself shows InProgress while all five of its children are Draft** — it was reopened Done→InProgress earlier this session ahead of authoring the Part-2 features, so the epic reads as active work already underway when nothing under it has started yet. Leaving this for a call rather than changing it myself.
    
    @manager
- [2026-09-03T09:54:21Z] Pierre Chat:
  - Keeping BUG-895, BUG-896 and FEAT-690 in 0.15. They are small wins independent of the Python engine work, so they cost the main lines nothing and can run in parallel. Not dropped -- the product-owner recommendation to drop all three is declined.
  - No target date on this milestone. We are not setting dates -- it is released when it is ready.
- [2026-09-09T14:37:46Z] Pierre Chat:
  - Draft a 0.16 milestone and move the -dev pseudo-role retirement there. 0.15 is already taking long enough.
- [2026-09-09T14:40:35Z] Nina Product:
  - Per op-pierre (this discussion, 2026-09-09): the -dev pseudo-role retirement moves to MILE-934 (squads 0.16 - roles, not slugs). Bullet removed from this body, unchanged in scope, no ADR/breakdown yet.
- [2026-09-09T14:41:22Z] Nina Product:
  - **Recommendation on what else follows the -dev retirement into MILE-934 (0.16)** — not a decision, op-pierre's call:
    
    - **FEAT-899/900/901/902 (validator followers) — recommend moving.** This is the exact slice from my original "not comfortably deliverable together" read: four features, gated only on FEAT-898 which is Done, so deferring them breaks nothing in either build order. They don't depend on or block anything in the views line. Moving them is the most direct way to shrink 0.15's remaining footprint by feature count, not just review latency, which is what "already taking long enough" is describing.
    - **FEAT-690 — recommend leaving in 0.15.** It was kept on the record with reasoning ("costs the main lines nothing, runs in parallel") that hasn't changed today — it was never on the critical path, so deferring it wouldn't shorten the path the way the validator followers would. Moving it now, but not BUG-895/896 (kept on the same reasoning), would be inconsistent without a new reason.
    
    If op-pierre wants a smaller 0.15 exit list rather than a shorter critical path, that argues for moving FEAT-690 too — different motivation, flagging it rather than picking for him.
- [2026-09-09T14:44:59Z] Pierre Chat:
  - Move them to 0.16 -- the four validator followers (FEAT-899, 900, 901, 902) and BUG-935. A smaller release seems good; we are already at 38 commits. FEAT-690 stays in 0.15 on the reasoning that kept it there: it costs the main lines nothing and runs in parallel.
- [2026-09-09T14:49:14Z] Nina Product:
  - Executed op-pierre's ruling (this discussion, 2026-09-09): re-targeted FEAT-899, FEAT-900, FEAT-901, FEAT-902 and BUG-935 from this milestone to MILE-934 (targets ref rm/add). Roll-up verified both sides: this milestone's Outstanding dropped from 10 to 5, MILE-934's Outstanding rose from 0 to 5, membership matches exactly.
  - Scope section corrected: the validator-catalog bullet now describes only FEAT-898 (Done, its own line) instead of the full five-feature build-out; the 'record no adopter promise' bullet now folds into FEAT-898 by name; added explicit bullets for FEAT-690 (parallel client-UI win) and BUG-895/896 (verified bugs), which were carried members but not previously named in Scope prose.
- [2026-09-09T14:50:13Z] Catherine Manager:
  - Resolving the tension the product owner flagged rather than leaving it: the "does not belong here" exclusion on browser-client work is not in conflict with FEAT-690 sitting in scope. Browser-client means EPIC-29 (sq web, a local web view) and MILE-868 (the web release). FEAT-690 is the VS Code extension plus the sq ui TUI -- neither is a browser client. The exclusion stands as written and FEAT-690 stays; no edit needed.
<!-- sq:discussion:end -->
