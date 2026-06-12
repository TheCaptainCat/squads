---
id: ADR-000049
sequence_id: 49
type: decision
title: Ref-kind vocabulary is closed in 1.0, with the extension point reserved for
  post-1.0
status: Accepted
author: architect
refs:
- FEAT-000035
- FEAT-000013
- FEAT-000014
- GUIDE-000079
created_at: '2026-06-11T20:19:55Z'
updated_at: '2026-06-12T14:26:22Z'
---
<!-- sq:body -->
## Context

FEAT-000035 turns ref kinds from an advertised-but-unenforced list into a validated vocabulary:
`ref add --kind` rejects unknowns, `sq check` flags junk edges in existing files, and one
canonical kinds table documents all eight kinds (`related`, `blocks`, `depends-on`, `implements`,
`fixes`, `addresses`, `supersedes`, `duplicates`). Kinds are stored inline in frontmatter as
`"ID:kind"` (`split_ref`/`make_ref`), and the vocabulary joins the 1.0 stability contract
(FEAT-000013) as durable on-disk format.

The feature leaves one question for this ADR: does 1.0 ship a **project-level escape hatch** for
custom ref kinds — FEAT-000014's override mechanism would be its natural home — or an **explicitly
closed vocabulary**? "Decide, don't drift."

The constraints that bound the choice:

- **Every kind earns its keep through a consumer.** `blocks`/`depends-on` feed `sq blocked`;
  `fixes`/`addresses` feed `sq check`'s task rules; `supersedes` feeds the decision checks; the
  rest serve navigation. A custom kind, by definition, has **no consumer** — squads' own tooling
  cannot act on it, so it degrades to a `related` edge wearing a private label.
- **Shared semantics are the point.** The vocabulary is squads' lingua franca: a `fixes` edge
  means the same thing in every squad. Per-project custom kinds fragment that — a `blocks`-alike
  spelled `gates` in one squad is invisible to everyone else's tooling and reading.
- **An escape hatch fights the rule we are shipping.** FEAT-000035's headline is "unknown kinds are
  rejected." Custom kinds reintroduce the very ambiguity it removes: validation must now distinguish
  *rejected-as-typo* from *locally-declared-and-valid*, `sq check`'s unknown-kind warning must read
  project config to know which junk is sanctioned, and a `"ID:gates"` edge stops being self-describing
  the moment it leaves its home squad.
- **FEAT-000014 is itself pre-design and contract-bearing** — its override lookup path and precedence
  are not yet settled. Wedging a custom-kinds registry into it now couples two undesigned surfaces and
  bakes both into the 1.0 contract before either is ready.
- **The closed list keeps `sq check` exhaustive** and lets FEAT-000013 freeze a small, finite,
  enumerable contract — exactly the rigor we gave statuses.

## Decision

**1.0 ships an explicitly closed ref-kind vocabulary** — the eight kinds named above and no others;
unknown `--kind` values are rejected and unknown kinds in files are flagged by `sq check`. There is
**no custom-kind escape hatch in 1.0**.

The contract **explicitly reserves the extension point** as a non-decision, not a closed door: a
future, project-declared custom-kind facility (the natural home being FEAT-000014's override
mechanism) is **deferred to post-1.0** and, when designed, must be **additive and non-breaking** —
declaring custom kinds may relax validation for an opting-in project but must never change the
meaning of the eight built-in kinds, and a squad that uses none of them stays fully portable. Adding
that facility post-1.0 widens what is accepted; it does not break any squad written against the
closed vocabulary, so it needs no major-version bump.

This is the middle road, deliberately: closed now, with the door named and hinged for later.

## Consequences

For FEAT-000035's implementation:

- **The vocabulary is finite and lives in one place in code** (no project-config lookup on the
  validation path). `ref add --kind` validates against exactly the eight kinds; the error lists them.
- **The kinds table is the contract.** It must state, per kind: meaning, direction convention (e.g.
  `A blocks B` lives on A; `depends-on` lives on the dependent, with `A depends-on B` ≡ `B blocks A`),
  and consumer. Eight rows, no "and your own here" footnote.
- **The contract doc (FEAT-000013) must carry the extension *policy* verbatim**, not just the list:
  "The ref-kind vocabulary is closed in 1.0. Unknown kinds are rejected. A project-declared
  custom-kind extension is reserved for a future release and will be additive and non-breaking — the
  eight built-in kinds' meanings are fixed." This is the load-bearing wording the docs table and
  stability doc must ship.
- **`sq check`'s unknown-kind warning stays simple** — any kind not in the built-in set is flagged,
  with no project-config exception path to consult. (A future facility would add that path; until
  then, no branch for it.)
- **No FEAT-000014 dependency.** FEAT-000035 ships independently; it does not block on, and is not
  blocked by, the override-mechanism design.

## Status note

Recorded as **Proposed**. Acceptance is the operator's call (Pierre / @manager). Per the decision
workflow, this ADR can be superseded by a future ADR if and when the post-1.0 custom-kind facility
is designed — that is the intended path for revisiting the closed-vocabulary stance, not editing
this decision.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-11T20:20:45Z] Robert Architect:
  - Recommendation: 1.0 ships a CLOSED ref-kind vocabulary (the eight kinds), no custom-kind escape hatch. Every kind must earn a consumer; custom kinds have none, fragment squads' shared semantics, and would muddy FEAT-000035's clean 'unknown kinds are rejected' rule (rejected-as-typo vs locally-declared).
  - Middle road, deliberate: the contract RESERVES the extension point rather than closing the door. A project-declared custom-kind facility (FEAT-000014's override mechanism is its natural home) is deferred post-1.0 and, when designed, must be additive and non-breaking — the eight built-ins' meanings stay fixed, so it needs no major bump. Revisit by superseding this ADR, not by editing it.
  - For FEAT-000035: the kinds table is the contract — eight rows (meaning / direction / consumer), no open-ended footnote. The stability doc (FEAT-000013) must carry the policy verbatim: 'closed in 1.0; unknown kinds rejected; custom-kind extension reserved for a future release, additive and non-breaking.' sq check's unknown-kind warning stays a flat set membership test — no project-config exception path. No FEAT-000014 dependency: FEAT-000035 ships independently.
  - @manager @op-pierre this is Proposed for your acceptance — left at Proposed deliberately, the call is yours. @tech-lead for awareness: the closed-vocabulary wording lands in the docs kinds table and the stability contract this feature ships.
- [2026-06-11T21:27:25Z] Pierre Chat:
  - Accepted: closed eight-kind vocabulary for 1.0; extension point reserved post-1.0, additive and non-breaking.
<!-- sq:discussion:end -->
