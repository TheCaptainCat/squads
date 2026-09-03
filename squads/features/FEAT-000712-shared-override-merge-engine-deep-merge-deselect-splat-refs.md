---
id: FEAT-712
sequence_id: 712
type: feature
title: 'Shared override merge engine: deep-merge, deselect, splat-refs'
status: Done
parent: EPIC-538
author: product-owner
refs:
- EPIC-538
- ADR-541
- ADR-696
- PRD-859:implements
subentities:
- local_id: US1
  title: As a spec author, I want overrides to deep-merge onto the bundled base so
    I only declare what changes
  status: Done
- local_id: US2
  title: As a spec author, I want a selected list to drop built-ins I don't want,
    refused cleanly if the result is unsafe
  status: Done
- local_id: US3
  title: As a spec author, I want a splat-ref to append to a bundled list without
    restating it
  status: Done
created_at: '2026-07-31T13:00:32Z'
updated_at: '2026-09-01T13:51:27Z'
---
<!-- sq:body -->
## Capability

One shared override-merge engine, reused by the workflow, playbook, and roles loaders, replacing the additive-only "may not redefine a built-in" policy. This is the foundation the workflow-overridability and playbook-override-kind features build on — cut separately because each is its own shipping increment, but neither is buildable without this landing first.

## Scope

The engine, given a bundled base document and an override document, produces the effective merged document:

- **Deep recursive merge at leaf granularity.** An override supplies only the fields it changes; everything else inherits from the bundled base. Tables recurse per key; a leaf value replaces its counterpart. Plain arrays are leaves — replaced wholesale, never element-merged — unless a splat-ref is used.
- **Deselect via a top-level `[selected]` table**, keyed by section name (`items`, `statuses`, `lifecycles`, `collections`, `subentity_kinds`, `roles` for the workflow spec; the equivalent keyed sections for whichever document a given loader owns). Each key's list is the *surviving* set, not the removed one — replace-wholesale semantics, because the point is to shrink. `selected` is consumed and stripped by the loader before model validation (the models keep `extra="forbid"`). `selected` carries no validation of its own: it is an ordering step (resolve splats against the bundled base → deep-merge → apply `selected` → build the resulting spec → run its own validation → run the live-index cross-check), and every unsafe drop is caught by a check that already runs on the *resulting* spec. The one thing `selected` owes on its own: when a violation traces back to a `selected` line, the message says so, so an adopter can see their own deselect caused it.
- **Splat-refs**: a safe, eval-free path-reference splice for appending to a bundled list without restating it. `$(path)` splices the bundled value at *path* as one element; `$(*path)` spreads a bundled list's elements into the surrounding list — the idiom that makes `["$(*self)", <new>]` mean "append". `$(self)` / `$(*self)` addresses the key currently being written (the only usable idiom where the surrounding structure has no stable dotted name, e.g. a role-guide array inside a keyed block); dotted paths address keyed tables elsewhere. Resolution is against the **bundled base only** — no override value is ever a splat target, so there are no cycles and the merge is order-independent. Compose-only: a splat adds, never removes (removal is `selected`'s job). Fail-closed on a dangling path, a type mismatch, or any unparsed `$(` token surviving resolution; `$$(` escapes a literal.
- Two implementation details fixed by ADR-696 and binding here: a splatted array of tables must use TOML's inline-array form (`roles = ["$(*self)", { … }]`) — the `[[…]]` header form has no slot for a token; and splat resolution completes **before** model validation, since the strictly-typed models would otherwise reject the unresolved token as a type error.
- The engine itself is loader-agnostic: it takes a bundled base and an override and knows nothing about which document produced them. It does not itself decide *which* keys are reserved/locked (that is each loader's own floor, e.g. the workflow loader's roster-locked check) — the engine's job is the merge, the deselect, and the splat resolution, nothing more.

## Out of scope (owned by dependent features)

- Wiring this engine into the workflow loader so `.overrides/workflow.toml` can shadow a built-in, and the accompanying floor checks (roster-locked, the R1/R1′/R2 lifecycle floor, drift stamping) — the workflow-overridability feature.
- Wiring this engine into a new playbook loader as the fourth override kind, and the per-request active-playbook seam — the playbook-override feature.
- Relocating/renaming the bundled TOML files — the spec-consolidation feature.
- The clean `SquadsError` refusal naming what still references a dropped/shadowed key — that is a loader-level referential-integrity check (a status/lifecycle still referenced, or a type with live items), not an engine-level guarantee. It lands with FEAT-713 (workflow loader) and FEAT-714 (playbook loader), each running its own checks over the merged mapping this engine produces.

## Acceptance

Restated at the engine boundary — each criterion is a property of the merge function over a bundled base document and an override document, not of a loaded spec (this feature ships no loader change, so nothing here can be phrased as a spec "loading"):

- Given a bundled base and an override that shadows a built-in key (deep-merge) or drops it via `selected`'s surviving-set semantics, the engine's merged mapping reflects that change precisely — the shadowed key carries the override's value, the dropped key is absent — with every other key in the merged mapping unchanged from the bundled base.
- A built-in can be re-pointed by overriding a single field: the merged mapping matches the bundled base with only that field replaced, never the whole entry.
- Appending one entry to a bundled list via `$(*self)` yields a merged list equal to the bundled list plus that one entry; a later change to the bundled list changes the merged result on the next merge without the override being touched.
- Given an empty or absent override, the merged mapping is equal to the bundled base — the no-op case that is the engine-level statement of "byte-identical to today".
- Two overrides of unrelated keys, merged in either order, produce the same merged mapping (order-independence from bundled-base-only splat resolution).
- A dangling splat path, a splat type mismatch, or a surviving unparsed `$(` token each fail closed — collected rather than stopping at the first hit when the calling mode is collect-all; `$$(` always resolves to a literal `$(` in the merged mapping, never left as a token.

The end-to-end, load-time versions of these — a spec that loads and runs clean, and the `SquadsError` refusal naming what still references a dropped/shadowed key — are asserted by FEAT-713 and FEAT-714 against their wired loaders, so the epic-level acceptance chain stays traceable through them, not through this feature alone.

## Constraints

- No `eval`, no user-supplied code path — splat-refs are a closed-grammar path splice, per the standing no-eval line (ADR-541 Axis B, ADR-696 §4a).
- The engine does not itself enforce the roster-locked floor or any category-specific rule; those stay in each loader, per ADR-541/ADR-696. This feature must not grow a special case for the roster category.
- No dropped item may break `sq`: every consumer downstream of a loader that uses this engine must see either a fully functional result or a clean refusal — this feature supplies the ordering guarantee that makes that possible; the consumer-side absorption is the dependent features' job.

## References

Settled input, not open questions: EPIC-538 (outcome list, epic body "The design (settled)"), ADR-541 (Axis A/B, roster-locked floor), ADR-696 §4/§4a/§4b (the authoritative naming — `selected`, not the epic body's `active`; `$(self)`/`$(*self)`; the ordering rule). Do not re-derive or amend the design here.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 712 add-story "As a <role>, I want … so that …"`; track with `sq feature 712 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | As a spec author, I want overrides to deep-merge onto the bundled base so I only declare what changes |
| US2 | Done |  | As a spec author, I want a selected list to drop built-ins I don't want, refused cleanly if the result is unsafe |
| US3 | Done |  | As a spec author, I want a splat-ref to append to a bundled list without restating it |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a spec author, I want overrides to deep-merge onto the bundled base so I only declare what changes

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
Given a bundled base document and an override document, the merge recurses into tables per key and replaces leaf values; plain arrays are replaced wholesale (never element-merged) unless a splat-ref is present. Acceptance: an override touching one field of a built-in leaves every other field of that built-in unchanged in the merged result.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a spec author, I want a selected list to drop built-ins I don't want, refused cleanly if the result is unsafe

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
A top-level [selected] table, keyed by section name, names the surviving set per section. Order of operations: resolve splats against the bundled base, deep-merge, apply selected, build the resulting spec, run its own validation, then the live-index cross-check. selected adds no validation of its own; a violation on the resulting spec that traces to a selected line says so in its message. Acceptance: dropping a status/lifecycle/type still referenced by the resulting spec fails with the existing referential-integrity check, naming the selected line as the cause.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As a spec author, I want a splat-ref to append to a bundled list without restating it

<!-- sq:story:US3:head -->
**Status:** 🟢 Done
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
$(path) splices the bundled value at path as one element; $(*path) spreads a bundled list's elements (the append idiom, ["$(*self)", x]); $(self)/$(*self) addresses the key currently being written. Resolution is against the bundled base only (no cycles, order-independent); compose-only (no element removal); fails closed on a dangling path, a type mismatch, or a surviving unparsed token; $$( escapes a literal. A splatted array of tables uses TOML's inline-array form; resolution completes before model validation. Acceptance: two overrides of unrelated keys produce the same merged result in either order; each of the three failure modes is caught and reported, not silently swallowed.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-31T13:20:57Z] Olivia Lead:
  - Broken down as one task: TASK-716 (high) — the loader-agnostic engine as a new flat private module (src/squads/_specmerge.py, only internal dep squads._errors, since three loaders import it). Four subtasks: ST1 splat resolution (US3, built first — steps 2/3 consume it), ST2 deep-merge (US1), ST3 selected apply/strip/provenance (US2), ST4 ordered entry point + fail-fast/collect-all modes (US2).
  - One task, not several: same owner role and same shipping increment throughout — FEAT-713 and FEAT-714 each need the whole engine, and the three mechanisms are one ordered pipeline over one new module. No adopter-facing doc here: the grammar becomes documentable when a loader exposes it (FEAT-713), so no tech-writer surface splits off.
  - @architect @manager one reading recorded rather than resolved: this feature's acceptance is phrased at load ('loads and runs clean', 'fail closed at load') while its Out-of-scope assigns all loader wiring to FEAT-713/714. I scoped TASK-716 to the engine boundary — merged-mapping equality, no-op on empty override, order-independence, four fail-closed cases, both calling modes — per the more specific Out-of-scope clause. Correct me if the intent was for FEAT-712 to also swap _merge_override over.
- [2026-07-31T13:24:48Z] Nina Product:
  - Acceptance re-grounded on the engine boundary: each criterion is now a property of the merge over a bundled base + override (merged-mapping equality, no-op on empty override, order-independence, the four fail-closed cases, the $(*self) append), not of a loaded spec — this feature ships no loader change, so 'loads and runs clean' was never a claim it alone could make. The clean-SquadsError-naming-what-still-references-it refusal moved to Out of scope, re-homed on FEAT-713/714's referential-integrity checks. Closes the conflict flagged against TASK-716's scope.
<!-- sq:discussion:end -->
