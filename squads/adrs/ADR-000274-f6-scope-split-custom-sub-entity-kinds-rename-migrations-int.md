---
id: ADR-000274
sequence_id: 274
type: decision
title: 'F6 scope: split custom sub-entity kinds + rename migrations into EPIC-213'
status: Accepted
author: architect
refs:
- FEAT-000212
- EPIC-000206
created_at: '2026-07-02T09:20:16Z'
updated_at: '2026-07-02T09:28:25Z'
---
<!-- sq:body -->
## Context

EPIC-000206 makes the workflow engine config-driven. Its committed workflow axis (F1–F5) delivers a coherent, shippable unit: a project can declare a custom **type** (prefix/folder/machine/parents/aliases/badges), custom **statuses/badges** with auto-linearized lifecycles, an additive-only override with load-time validation, and thin auto-generated `sq-<type>` skills — while the bundled default spec stays byte-identical to today (golden-locked). F4 is Done and F5 is InProgress; after F5 the epic satisfies its stated success criteria for the custom-vocabulary axis.

FEAT-000212 (F6) bundles two features that EPIC-206 itself already flags as second deep coupling surfaces, each comparable in blast radius to F1+F2:

1. **Custom sub-entity kinds.** Today a type's `subentity_kind` is a single string selecting one of three built-in kinds (story/subtask/finding). Letting a custom type declare a *new* kind with its own machine + summary columns + CLI verb is structurally a second de-typing, mirroring F2 on a different axis. The coupling is real and un-retired: the three `add-<kind>` verbs in `_cli/_items.py` are hand-written closures with kind-specific fields (story: none; subtask: `--story`; finding: `--severity`), each dispatching to a distinct `svc.add_story/add_subtask/add_finding` method; `_SUBENTITY_PLURAL` is still a static map (the last per-type vocabulary artifact); and there is no `SubentityKind` schema on `WorkflowSpec` carrying a machine + column definitions. Making this spec-driven touches the CLI app-build, `_common._print_subentity_summary`, `_discussion.py` column rendering, the service `add_*` methods, and the spec schema — a fresh, wide surface.

2. **Vocabulary rename migrations.** `sq migrate rename-type` / `rename-status` are *data-rewrite* events built on the existing `_services/_retype.py` primitive (atomic ID/ref/parent/prose rewrite), requiring a schema bump, a `sq migrate` runbook + `manual` string, and fail-closed validation. This is migration/tooling engineering, not vocabulary-schema engineering.

These two halves share almost no code. (1) is a spec-schema + CLI-dispatch feature that extends the L3 vocabulary story; (2) is an audited migration built on `retype` that operates *over* the vocabulary rather than extending it. They were bundled into one F6 for roadmap convenience, not because they cohere technically. F6 depends on both FEAT-000210 (Done) and FEAT-000211 (InProgress); neither dependency binds it to EPIC-206's ship boundary.

## Decision

**Split F6 out of EPIC-000206 into a new epic (recommended: EPIC-000213), and further separate its two halves into distinct features within that epic.**

EPIC-206 closes as a clean, coherent shippable unit at F1–F5 + the config axis (FR/FP): "config-driven workflow with custom types, statuses, and playbook, default==today." The two F6 surfaces are each net-new deep coupling of blast radius ≈ F1+F2, and belong in their own epic where they can be sequenced, spiked, and reviewed independently rather than as a "stretch" tail that would inflate EPIC-206's scope and delay its close.

Within the new epic, the custom-sub-entity-kinds feature owns retiring `_SUBENTITY_PLURAL` (per Catherine's ownership note) by adding a `subentity_plural` accessor to the reserved-vocab resolver established in ADR-000266. The rename-migrations feature is independent of it and could ship first or in parallel.

This ADR does not create EPIC-000213 or re-parent FEAT-000212 — that is a product-owner/manager action. It records the scope line required by EPIC-206 success criterion #8 and FEAT-212 acceptance criterion #5.

## Consequences

- EPIC-000206 becomes closable at F1–F5 + FR/FP without a dangling High-risk stretch feature; its "done" is honest and self-contained.
- The two F6 surfaces get independent sequencing and their own spike/review scrutiny proportional to their blast radius, instead of inheriting EPIC-206's momentum as an afterthought.
- Splitting the sub-entity-kinds and rename-migration halves into separate features prevents a schema bump (rename migrations) from blocking the vocabulary-schema work, and lets either land first.
- Cost: one more epic to track, and FEAT-212 must be re-parented (product-owner/manager). The dependency edges (depends-on FEAT-210/211) are preserved regardless of parent.
- If the team instead kept F6 in EPIC-206, the epic's ship date would couple to two High-risk features that deliver value orthogonal to "custom vocabulary works end-to-end" — the opposite of the minimum-viable scope-control lever EPIC-206 deliberately chose.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-02T09:23:34Z] Catherine Manager:
  - Accepted per op-pierre: proceed with the FULL split — FEAT-212 moves to a new EPIC-213 and its two halves become separate features (custom sub-entity kinds; vocabulary rename migrations). depends-on FEAT-210/211 edges preserved. product-owner to action the re-parent.
- [2026-07-02T09:28:25Z] Catherine Manager:
  - Executed: the new epic is EPIC-000280 (the ADR's 'EPIC-213' was illustrative; 213 was already claimed by BUG-000213 via the global counter). Split done — FEAT-000212 re-scoped to custom sub-entity kinds under EPIC-280; FEAT-000281 created for vocabulary rename migrations. depends-on FEAT-210/211 preserved.
<!-- sq:discussion:end -->
