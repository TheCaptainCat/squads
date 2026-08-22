---
id: ADR-49
sequence_id: 49
type: decision
title: Ref-kind vocabulary is closed in 1.0, with the extension point reserved for
  post-1.0
status: Accepted
author: architect
refs:
- FEAT-35
- FEAT-13
- FEAT-14
- GUIDE-79
- ADR-492
created_at: '2026-06-11T20:19:55Z'
updated_at: '2026-08-22T09:31:05Z'
---
<!-- sq:body -->
## Context

FEAT-35 turns ref kinds from an advertised-but-unenforced list into a validated vocabulary:
`ref add --kind` rejects unknowns, `sq check` flags junk edges in existing files, and one
canonical kinds table documents all eight kinds (`related`, `blocks`, `depends-on`, `implements`,
`fixes`, `addresses`, `supersedes`, `duplicates`). Kinds are stored inline in frontmatter as
`"ID:kind"` (`split_ref`/`make_ref`), and the vocabulary joins the 1.0 stability contract
(FEAT-13) as durable on-disk format.

The feature leaves one question for this ADR: does 1.0 ship a **project-level escape hatch** for
custom ref kinds — FEAT-14's override mechanism would be its natural home — or an **explicitly
closed vocabulary**? "Decide, don't drift."

The constraints that bound the choice:

- **Every kind earns its keep through a consumer.** `blocks`/`depends-on` feed `sq blocked`;
  `fixes`/`addresses` feed `sq check`'s task rules; `supersedes` feeds the decision checks; the
  rest serve navigation. A custom kind, by definition, has **no consumer** — squads' own tooling
  cannot act on it, so it degrades to a `related` edge wearing a private label.
- **Shared semantics are the point.** The vocabulary is squads' lingua franca: a `fixes` edge
  means the same thing in every squad. Per-project custom kinds fragment that — a `blocks`-alike
  spelled `gates` in one squad is invisible to everyone else's tooling and reading.
- **An escape hatch fights the rule we are shipping.** FEAT-35's headline is "unknown kinds are
  rejected." Custom kinds reintroduce the very ambiguity it removes: validation must now distinguish
  *rejected-as-typo* from *locally-declared-and-valid*, `sq check`'s unknown-kind warning must read
  project config to know which junk is sanctioned, and a `"ID:gates"` edge stops being self-describing
  the moment it leaves its home squad.
- **FEAT-14 is itself pre-design and contract-bearing** — its override lookup path and precedence
  are not yet settled. Wedging a custom-kinds registry into it now couples two undesigned surfaces and
  bakes both into the 1.0 contract before either is ready.
- **The closed list keeps `sq check` exhaustive** and lets FEAT-13 freeze a small, finite,
  enumerable contract — exactly the rigor we gave statuses.

## Decision

**1.0 ships an explicitly closed ref-kind vocabulary** — the eight kinds named above and no others;
unknown `--kind` values are rejected and unknown kinds in files are flagged by `sq check`. There is
**no custom-kind escape hatch in 1.0**.

*Narrowed 2026-08-03: closed against **ad-hoc** kinds, extensible by reviewed addition. The set is
nine — `scopes` was added pre-1.0 by ADR-492 with a schema bump — and "no others" now reads as "no
kind a project declares for itself". The closure against an adopter-facing escape hatch is
unchanged. See the amendment note.*

The contract **explicitly reserves the extension point** as a non-decision, not a closed door: a
future, project-declared custom-kind facility (the natural home being FEAT-14's override
mechanism) is **deferred to post-1.0** and, when designed, must be **additive and non-breaking** —
declaring custom kinds may relax validation for an opting-in project but must never change the
meaning of the eight built-in kinds, and a squad that uses none of them stays fully portable. Adding
that facility post-1.0 widens what is accepted; it does not break any squad written against the
closed vocabulary, so it needs no major-version bump.

This is the middle road, deliberately: closed now, with the door named and hinged for later.

## Consequences

For FEAT-35's implementation:

- **The vocabulary is finite and lives in one place in code** (no project-config lookup on the
  validation path). `ref add --kind` validates against exactly the built-in kinds; the error lists
  them. (`VALID_REF_KINDS`, one frozenset — nine entries today.)
- **The kinds table is the contract.** It must state, per kind: meaning, direction convention (e.g.
  `A blocks B` lives on A; `depends-on` lives on the dependent, with `A depends-on B` ≡ `B blocks A`),
  and consumer. One row per built-in kind, no "and your own here" footnote.
- **The contract doc (FEAT-13) must carry the extension *policy* verbatim**, not just the list:
  "The ref-kind vocabulary is closed in 1.0. Unknown kinds are rejected. A project-declared
  custom-kind extension is reserved for a future release and will be additive and non-breaking — the
  built-in kinds' meanings are fixed." This is the load-bearing wording the docs table and
  stability doc must ship.
- **`sq check`'s unknown-kind warning stays simple** — any kind not in the built-in set is flagged,
  with no project-config exception path to consult. (A future facility would add that path; until
  then, no branch for it.)
- **No FEAT-14 dependency.** FEAT-35 ships independently; it does not block on, and is not
  blocked by, the override-mechanism design.

## Amendment note

**2026-08-03 — the vocabulary is closed against ad-hoc kinds, and extensible by reviewed addition.**
This decision named eight kinds "and no others" and deferred any extension to post-1.0. There are
nine: `scopes` was added pre-1.0 by ADR-492, with a `SCHEMA_VERSION` bump, to carry a skill's forward
edge to the role that preloads it — a kind with a real consumer (`skills_for_role`'s resolution,
inverted from the edge), which is exactly the bar this decision set for a kind earning its keep.

Every principle here survives intact, and the tree confirms each one: there is **no project-declared
escape hatch** and no config lookup on the validation path (`VALID_REF_KINDS` is one frozenset in
`_models/_item.py`), `ref add --kind` refuses an unknown value and its error lists the whole set,
`sq check` flags an unknown kind with no exception path to consult, and a `"ID:kind"` edge is still
self-describing wherever it travels. What was wrong was only the closure's *scope*: "no others" read
as a freeze against the reviewed addition of a kind with a consumer, when the argument it rested on
was against **ad-hoc, per-project** kinds with none. The count is therefore not a contract; the
absence of an adopter-facing extension point is.

The post-1.0 facility this decision reserved is still reserved and still undesigned, and the
additive-and-non-breaking constraint on it still binds. `scopes` is not an instance of it — it is a
built-in with squads' own consumer, which needs no facility.

Reciprocal edge added to ADR-492. The adopter-facing count was corrected in the docs when this was
first surfaced (recorded in the discussion at 2026-07-31); this is the same correction at the
decision end, which is where it was outstanding.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-11T20:20:45Z] Robert Architect:
  - Recommendation: 1.0 ships a CLOSED ref-kind vocabulary (the eight kinds), no custom-kind escape hatch. Every kind must earn a consumer; custom kinds have none, fragment squads' shared semantics, and would muddy FEAT-35's clean 'unknown kinds are rejected' rule (rejected-as-typo vs locally-declared).
  - Middle road, deliberate: the contract RESERVES the extension point rather than closing the door. A project-declared custom-kind facility (FEAT-14's override mechanism is its natural home) is deferred post-1.0 and, when designed, must be additive and non-breaking — the eight built-ins' meanings stay fixed, so it needs no major bump. Revisit by superseding this ADR, not by editing it.
  - For FEAT-35: the kinds table is the contract — eight rows (meaning / direction / consumer), no open-ended footnote. The stability doc (FEAT-13) must carry the policy verbatim: 'closed in 1.0; unknown kinds rejected; custom-kind extension reserved for a future release, additive and non-breaking.' sq check's unknown-kind warning stays a flat set membership test — no project-config exception path. No FEAT-14 dependency: FEAT-35 ships independently.
  - @manager @op-pierre this is Proposed for your acceptance — left at Proposed deliberately, the call is yours. @tech-lead for awareness: the closed-vocabulary wording lands in the docs kinds table and the stability contract this feature ships.
- [2026-06-11T21:27:25Z] Pierre Chat:
  - Accepted: closed eight-kind vocabulary for 1.0; extension point reserved post-1.0, additive and non-breaking.
- [2026-07-31T11:40:45Z] Catherine Manager:
  - Surfaced by a review of the roster work: 'scopes' is in use as a ninth ref kind, while docs/stability.md and the squads skill both still describe the vocabulary as a frozen eight. The 0.13 release is the first to show that kind to adopters — in a --help line and in a refusal's remedy text — so the discrepancy is now user-visible. Relevant to this decision's commissioned challenge; the adopter-facing count is being corrected separately as a documentation fix.
- [2026-08-03T08:30:20Z] Robert Architect:
  - Narrowed in place, not retired: the closed-vocabulary principle is verified intact, only the closures scope was overstated. The set is nine — `scopes` was added pre-1.0 by ADR-492 with a schema bump, and it has a real consumer (`skills_for_role` inverting the edge), which is the bar this decision itself set. "No others" now reads "no kind a project declares for itself"; the absence of an adopter-facing escape hatch is the contract, the count never was.
  - Verified rather than taken from the audit: `VALID_REF_KINDS` at `_models/_item.py:80-92` is one frozenset with nine entries and no config lookup on the validation path, and its own docstring already states the reviewed-addition rule. The post-1.0 facility stays reserved and undesigned; `scopes` is not an instance of it.
  - Reciprocal `related` edge added to ADR-492 — the divergence was recorded here on 2026-07-31 and fixed in the docs, but never at the decision end, which is the end an adopter-facing contract is read from.
  - Also dropped the "Status note" section, which declared this decision Proposed in its own body. Status is frontmatter; body copy that names it goes stale the moment the status moves, and this one had been stale since acceptance the same evening. The section carried one substantive line — that revisiting the closed-vocabulary stance is a new decisions job — which is a routine rule of the decision workflow and needs no restating here.
- [2026-08-22T09:31:05Z] Robert Architect:
  - ADR-775 (Proposed) proposes superseding this decision. Three of the four arguments here are overtaken — a derived view is the consumer a project-declared kind lacked, declared-and-validated vocabulary is now the norm on every other axis, and the .overrides home this decision reserved is built. Shared semantics survives and is answered by a declared semantic role rather than a frozen spelling.
<!-- sq:discussion:end -->
