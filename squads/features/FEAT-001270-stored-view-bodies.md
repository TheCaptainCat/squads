---
id: FEAT-1270
sequence_id: 1270
type: feature
title: Stored view bodies
status: Done
parent: EPIC-1268
author: product-owner
refs:
- MILE-1269:targets
description: A view tag can store a body its projection reads at render time
subentities:
- local_id: US1
  title: Paired view tags carry a stored body
  status: Done
- local_id: US2
  title: Body writes keep stored view bodies intact
  status: Done
- local_id: US3
  title: One operation writes a view body, escaping markers
  status: Done
- local_id: US4
  title: Projections read the stored body at render time
  status: Done
created_at: '2026-11-03T15:57:07Z'
updated_at: '2026-11-03T23:59:26Z'
---
<!-- sq:body -->
A view tag can carry a stored body: text kept in the item file between the view's open and end tags, handed to the view's projection when the item is read. A view whose source cannot be derived locally, such as an issue description fetched from a tracker, uses it as a cache; a view whose source is local keeps an empty tag and renders on read, as every bundled view does today.

The engine treats the body as opaque text. It never interprets it, keeps it intact through body writes, and lets only a dedicated operation write it. Reads never write it.

Out of scope: storing a rendered copy of a view whose source is derivable locally.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1270 add-story "As a <role>, I want … so that …"`; track with `sq feature 1270 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Paired view tags carry a stored body

<!-- sq:story:US1:body -->
As a view author, I can place a paired view tag whose stored body lives between its open and end tags, next to the empty tags that exist today.

Done when:
- `<!-- sq:view:<name> -->` … `<!-- sq:view:<name>:end -->` inside `sq:body` is recognised as one view with a stored body; the empty form keeps working unchanged.
- `view add`, `view disable` and the placement rules handle both forms; disabling a paired tag keeps its stored body.
- `sq check` reports a paired tag without its end tag, an end tag without its opening tag, and a paired tag outside `sq:body`.
- `sq repair` and the index never read the stored body.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Body writes keep stored view bodies intact

<!-- sq:story:US2:body -->
As an agent setting an item's body, I cannot lose or alter a stored view body.

Done when:
- `sq <type> <n> body -m/--file` keeps every stored view body byte for byte, whatever the new text contains.
- A new body that omits a paired tag gets it re-placed with its stored body, the way a seeded empty tag is re-placed today.
- A new body that changes the text inside a paired tag is refused, naming the view and the operation that writes it.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — One operation writes a view body, escaping markers

<!-- sq:story:US3:body -->
As a squads component holding content for a view, I write its stored body through one operation, safely, whatever the text contains.

Done when:
- One operation, available to services and not exposed as a general CLI verb, sets the stored body of a named view on an item, inside an index transaction.
- Marker-shaped text in the body (`<!-- sq:… -->`) is escaped on write and restored on read, so a stored body can never open, close or forge a marker; covered by a test with a forged `sq:body` end tag.
- No read path, including `show`, the TUI and the daemon's GET routes, writes a stored body.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Projections read the stored body at render time

<!-- sq:story:US4:body -->
As a view author, my projection reads the stored body at render time.

Done when:
- The view's transform and its template receive the stored body as `body`, unescaped; a view with an empty tag receives an empty string.
- The bundled views render exactly as before (golden output unchanged).
- `--json` output of a view includes its stored body.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-03T15:57:36Z] `op-pierre` Pierre Chat:
  - Rulings (2026-11-03): the description of a sourced item lives in a view whose stored body is a cache, not a locked item body. The stored body is a generic views capability that projection functions read at render time; `source_description` is a regular projection. The cache is refreshed by an operation (pull, `show --refresh`), never by a read.
- [2026-11-03T16:17:48Z] `architect` Robert Architect:
  - @product-owner board check against the accepted ADRs; the ADR for this epic must amend these explicitly:
    - US1, conflicts with ADR-880 §4 (binding invariant: the view tag is unpaired, and any proposal for a paired form or a cached rendering "is the proposal to rebuild the stored region") and ADR-776 (no body sink). Reconcilable: ADR-776's rule bans content the CLI can compute, and tracker text cannot be computed locally, so the amendment narrows the rule to "derivable locally" rather than reversing it.
    - US1, the marker-balance check (`_services/_maintenance.py`) reports any unpaired `sq:view` tag by shape, and the repair sweep distinguishes retired regions by marker shape (ADR-776 §8); both must learn the paired form without the sweep ever matching it.
    - US3, the escaping is new grammar: `reject_markers` and `MARKER_RE` assume no tool-owned bytes sit inside `sq:body`, so the escape form and its round trip need defining.
<!-- sq:discussion:end -->
