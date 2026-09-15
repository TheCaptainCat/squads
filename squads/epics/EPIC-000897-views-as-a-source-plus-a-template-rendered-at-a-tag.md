---
id: EPIC-897
sequence_id: 897
type: epic
title: Views as a source plus a template, rendered at a tag
status: InProgress
author: product-owner
refs:
- ADR-880
description: 'Rebuild the view mechanism per ADR-880: source + template, a tag marks
  where it renders; the projection layer and its grammar are deleted'
created_at: '2026-09-03T09:00:54Z'
updated_at: '2026-09-03T09:59:56Z'
---
<!-- sq:body -->
## Outcome

A view is a **source plus a template**; a **tag** placed in a document body marks where it
renders, expanded at read time. The projection layer FEAT-693 built — a declared field list,
`group_by`/`order_by`, type-attached views, and a flattened record shape — is deleted outright.
The source mechanism survives and widens past item relations (`ref`/`subtree`/`subentity`) to
`role`, `playbook`, and `self`, which is what lets the three bespoke read-time render paths
squads already reinvented by hand (role definition text, system skill text, per-item-type skill
text) collapse onto one declared mechanism instead of three hardcoded ones.

Full technical shape, the four ruled problems, and the binding invariant on the tag's unpaired
form are in ADR-880 — this epic groups the features that build what it rules. ADR-880 carries a
ruled amendment (2026-09-03): the tag lives inside the `sq:body` region, placed only through a
dedicated marker-safe verb — never by typing it into a body edit, which stays refused.

## Why this epic, not a reopened one

FEAT-693 (derived views, shipped 0.14) was parentless — it never had an epic. The two epics
whose subtree it might seem to belong under are both closed against a different, already-fully-
delivered outcome (see the comment trail for the parentage reasoning). This epic exists because
the outcome it targets — a working, adopter-declarable view mechanism — has never had one.

## Scope

- Source layer: widen `resolve_records` (→ `resolve_source`) to `role`/`playbook`/`self`.
- Delete the projection middle layer, its declaration grammar, its validators, and
  `ItemSpec.views` type-attachment.
- The view tag: an unpaired marker inside `sq:body`, placed/removed by its own dedicated verb,
  expanded at the single body-read boundary; `sq check`'s balance arithmetic learns the shape.
- Collapse `role_definition_text`, system skill text, and per-item-type skill text onto the
  declared mechanism.
- Retrofit: seed the tag on new milestones, migrate existing milestone bodies once, through
  that same placement verb, in bulk.
- The adopter-facing side of retiring a grammar that shipped one release ago.

## Does not belong here

- Any new `source.kind` beyond `role`/`playbook`/`self` not named in ADR-880.
- Adopter-supplied validator/view logic in Python (a different, separately-ruled boundary).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-03T09:01:22Z] Nina Product:
  - Epic-parentage call: new epic, not a reopened one. EPIC-538 (spec-driven customization) and EPIC-540 (pluggable validators) are both Done. FEAT-693 (derived views, 0.14) was never a child of either -- it targeted MILE-836 directly with no parent epic at all.
  - EPIC-538's outcome (type vocab drop/rename/re-prefix + playbook override, only 3 roster types reserved) is fully delivered and closed against exactly that outcome. ADR-880's view rebuild is a different outcome -- a render-time mechanism, not vocabulary customization -- so reopening EPIC-538 would conflate two outcomes under one epic and misrepresent what its 0.14 closure meant.
  - Reopened EPIC-540 instead for the validator-catalog work (see that epic's comment) -- same test does not favor reopening here because there is no existing epic whose outcome statement matches the view mechanism; inventing one now is honest, not scope creep.
  - This also fixes a standing gap: derived views have needed an epic since 0.14 and never had one.
- [2026-09-03T09:01:36Z] Nina Product:
  - HOLD per op-pierre: Robert is ruling a live amendment to ADR-880 -- whether the view tag lives inside the authored sq:body region (as currently ruled) or outside it. This changes whether the retroactivity migration writes into authored prose at all, and whether the 'body write drops the tag' advisory needs to exist.
  - No features are created under this epic yet. Holding views feature authoring until the amendment is ruled; this epic's Scope section (seed/migrate the tag into :body) reflects the pre-amendment ruling and may need a rewrite once Robert rules.
<!-- sq:discussion:end -->
