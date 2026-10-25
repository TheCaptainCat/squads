---
id: ADR-274
sequence_id: 274
type: decision
title: 'F6 scope: split custom sub-entity kinds + rename migrations into EPIC-213'
status: Accepted
author: architect
refs:
- FEAT-212
- EPIC-206
created_at: '2026-07-02T09:20:16Z'
updated_at: '2026-10-25T21:17:17Z'
---
<!-- sq:body -->
## Context

EPIC-206 makes the workflow engine config-driven. Its workflow axis (F1–F5) is a coherent,
shippable unit: a project can declare a custom type (prefix, folder, lifecycle, parents, aliases,
badges), custom statuses and badges, an additive override validated at load, and thin
auto-generated `sq-<type>` skills, while the bundled default spec stays golden-locked.

FEAT-212 (F6) bundled two further features, each a deep coupling surface comparable in blast
radius to F1+F2:

1. **Custom sub-entity kinds.** Letting a type declare a new kind with its own lifecycle, summary
   columns and CLI verb is a second de-typing on a different axis. It touches the CLI app build,
   the sub-entity summary rendering, `_discussion.py`, the service `add_*` surface and the spec
   schema.
2. **Vocabulary rename migrations.** `sq migrate rename-type` / `rename-status` are data-rewrite
   events built on the retype primitive (atomic id, ref, parent and prose rewrite), with a
   `sq migrate` runbook and fail-closed validation. That is migration engineering over the
   vocabulary, not an extension of it.

The two halves share almost no code; they were bundled for roadmap convenience.

## Decision

**F6 leaves EPIC-206 for its own epic, and its two halves become separate features within it.**

EPIC-206 closes at F1–F5 plus its config axis. The split landed as **EPIC-280**: FEAT-212 is the
custom sub-entity kinds feature, and FEAT-281 is the vocabulary rename migrations feature, each
keeping its depends-on edges to FEAT-210 and FEAT-211. The sub-entity kinds feature owns
retiring the last static per-kind vocabulary table: a kind's plural is answered by the spec
(`WorkflowSpec.subentity_plural(kind)`), and the kind schema itself is specified by ADR-348.

## Consequences

- EPIC-206's "done" is self-contained, without a high-risk stretch feature attached to it.
- The two surfaces get independent sequencing and their own review scrutiny, proportional to
  their blast radius.
- Separating the features keeps a migration surface from blocking the vocabulary-schema work and
  lets either land first.
- Cost: one more epic to track.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-02T09:23:34Z] `manager` Catherine Manager:
  - Accepted per op-pierre: proceed with the FULL split — FEAT-212 moves to a new EPIC-213 and its two halves become separate features (custom sub-entity kinds; vocabulary rename migrations). depends-on FEAT-210/211 edges preserved. product-owner to action the re-parent.
- [2026-07-02T09:28:25Z] `manager` Catherine Manager:
  - Executed: the new epic is EPIC-280 (the ADR's 'EPIC-213' was illustrative; 213 was already claimed by BUG-213 via the global counter). Split done — FEAT-212 re-scoped to custom sub-entity kinds under EPIC-280; FEAT-281 created for vocabulary rename migrations. depends-on FEAT-210/211 preserved.
- [2026-08-03T08:51:21Z] `architect` Robert Architect:
  - One scoping detail corrected: the `subentity_plural` accessor landed as `WorkflowSpec.subentity_plural(kind)`, not on the ADR-266 resolver this decision pointed at — `_models/_vocab.py` explicitly declined to host it, and rightly, since a kinds plural is spec data the spec object can answer directly. `_SUBENTITY_PLURAL` is gone as required, and the kind schema itself was specified by ADR-348, which this decision only scoped.
  - Worth recording that the scoping executed exactly as the DISCUSSION records rather than the body: EPIC-280 with FEAT-212 re-parented under it and FEAT-281 beside it, and the bodys "recommended EPIC-000213" was corrected in a comment because 213 was already claimed via the global counter. A live demonstration of why the discussion has to be read alongside the body.
- [2026-10-25T21:17:17Z] `architect` Robert Architect:
  - 2026-10-25 audit: partly stale, body rewritten in the present tense; the scope split is unchanged. Named the epic as executed (EPIC-280 with FEAT-212 and FEAT-281, not the recommended EPIC-213 number, which is a bug), folded the italic subentity_plural note into the Decision, and removed the then-current status of F4/F5 and the re-parenting to-do.
<!-- sq:discussion:end -->
