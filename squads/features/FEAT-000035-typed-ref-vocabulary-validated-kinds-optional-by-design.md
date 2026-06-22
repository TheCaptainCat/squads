---
id: FEAT-000035
sequence_id: 35
type: feature
title: 'Typed ref vocabulary: validated kinds, optional by design'
status: Done
parent: EPIC-000012
author: product-owner
priority: high
refs:
- BUG-000021
- FEAT-000013
description: ref add validates --kind against the documented vocabulary (typos rejected,
  check flags unknowns); untyped refs stay first-class for plain cross-reference;
  one canonical kinds table in the docs
subentities:
- local_id: US1
  title: Unknown ref kind rejected immediately with the valid vocabulary
  status: Done
- local_id: US2
  title: 'Untyped refs remain first-class: context links without taxonomy'
  status: Done
- local_id: US3
  title: 'Single canonical kinds table: direction and consumers documented'
  status: Done
- local_id: US4
  title: depends-on authorable from the dependent without touching the blocker
  status: Done
created_at: '2026-06-11T07:19:35Z'
updated_at: '2026-06-23T09:58:49Z'
---
<!-- sq:body -->
## Problem

Ref kinds look like a closed vocabulary but aren't one. The CLI help advertises
`related | blocks | implements | fixes | addresses`, the docs teach them by example — and
`ref add --kind banana` succeeds with exit 0 (verified live). A typo like `--kind fixe` silently
creates an edge that nothing consumes: `sq blocked` won't see a misspelled `blocks`, `sq check`'s
task rules won't see a misspelled `fixes`, and no one is told. The semantics are also scattered:
no single doc enumerates the kinds with their meaning, direction convention, and consumers. And
the vocabulary itself has three proven gaps (see Scope) — they must be settled in the same breath
as the validation that closes the list.

## Value

Refs are part of the durable on-disk format (`"ID:kind"` in frontmatter), and the kinds carry the
semantics our own tooling acts on — the vocabulary deserves the same rigor as statuses before 1.0
freezes the contract. Tightening is a behaviour change (commands that accepted junk start
refusing), which is exactly why it must happen in 0.x.

## Scope

- **Validate the vocabulary** at `sq <type> <n> ref add --kind …`: unknown kinds are a clean
  `SquadsError` listing the valid ones. The vocabulary is defined in one place in the code (no
  scattered string literals).
- **Untyped refs stay first-class — by design, not as a leftover.** A bare `ref add <id>` (no
  `--kind`) remains the right way to say "this is relevant context"; the default `related` is the
  plain cross-reference, and nothing nudges users to over-type their links.
- **Three new kinds** (decided with op-pierre, 2026-06-11), each with a consumer:
  - **`supersedes`** — `DEC-B supersedes DEC-A`, stored on the newer decision. Completes the
    decision lifecycle: the `Superseded` status finally gets its graph half. Consumer: `sq check`
    may warn when a Superseded decision has no incoming `supersedes` edge; navigation answers
    "what's the current decision?".
  - **`depends-on`** — stored on the *dependent* item; semantically the inverse of `blocks`, and
    consumed by `sq blocked` identically (either direction marks the dependency). Exists for
    authoring ergonomics: you record a dependency from the item you're drafting, without editing
    the blocker. The docs table must state that `A depends-on B` ≡ `B blocks A`.
  - **`duplicates`** — `BUG-B duplicates BUG-A`, stored on the later filing. Triage-standard;
    pairs with closing the duplicate as Cancelled (and with FEAT-000023's removal someday).
- **`sq check` flags unknown kinds** in existing squads (warning, not error — old files are data,
  not mistakes), so adopted/legacy squads surface their junk edges without breaking.
- **One canonical kinds table in the docs** (likely `sq docs workflow` + referenced from
  internals): all eight kinds — `related`, `blocks`, `depends-on`, `implements`, `fixes`,
  `addresses`, `supersedes`, `duplicates` — each with meaning, direction convention (e.g.
  `A blocks B` lives on A; `depends-on` lives on the dependent), and consumers (`blocks`/
  `depends-on` → `sq blocked`; `fixes`/`addresses` → `sq check` task rules; `supersedes` →
  decision checks; the rest → navigation). CLI help points at it.
- **The vocabulary joins the stability contract** (FEAT-000013): the eight kinds and the
  "unknown kinds are rejected" rule become documented format. Design question for the ADR: whether
  1.0 ships a project-level escape hatch for custom kinds (FEAT-000014's override mechanism would
  be the natural home) or an explicitly closed vocabulary — decide, don't drift.
- **Explicitly rejected for now**: `tests`, `documents`, `caused-by` — no consumer; `related`
  covers them until proven otherwise.

## Acceptance

- Unknown `--kind` values are rejected with the valid list; all eight kinds accepted; bare
  `ref add` unchanged.
- `sq blocked` treats `A depends-on B` exactly as `B blocks A` (mixed usage in one squad works).
- `sq check` warns on unknown kinds present in files (naming item and edge), and on Superseded
  decisions lacking an incoming `supersedes` edge.
- The docs contain a single kinds table (meaning, direction, consumers); help text references it.
- The contract doc states the vocabulary and its extension policy.
- Tests: rejection, each valid kind, depends-on/blocks equivalence in `blocked`, check-warning
  fixtures (junk kind; superseded-without-edge).
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 35 add-story "As a <role>, I want … so that …"`; track with `sq feature 35 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | Unknown ref kind rejected immediately with the valid vocabulary |
| US2 | Done |  | Untyped refs remain first-class: context links without taxonomy |
| US3 | Done |  | Single canonical kinds table: direction and consumers documented |
| US4 | Done |  | depends-on authorable from the dependent without touching the blocker |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Unknown ref kind rejected immediately with the valid vocabulary

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a user adding a typed ref, I want a typo'd kind rejected on the spot with the valid vocabulary, so that I can't silently create an edge nothing consumes.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Untyped refs remain first-class: context links without taxonomy

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a user linking context, I want plain untyped refs to stay first-class, so that not every link needs a taxonomy decision.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Single canonical kinds table: direction and consumers documented

<!-- sq:story:US3:head -->
**Status:** 🟢 Done
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As a team member learning the system, I want one documented table of kinds with direction and consumers, so that I pick the right kind without archaeology across five docs.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — depends-on authorable from the dependent without touching the blocker

<!-- sq:story:US4:head -->
**Status:** 🟢 Done
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
As a user drafting an item that needs another one first, I want to record depends-on from the item I'm editing, so that dependencies are authorable without touching the blocker.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-11T07:29:45Z] Pierre Chat:
  - Vocabulary decision: extend to eight kinds — add supersedes, depends-on and duplicates (each with a consumer); explicitly keep tests/documents/caused-by out until they earn a consumer.
- [2026-06-11T20:23:26Z] Olivia Lead:
  - Broken down per ADR-000049 (closed vocabulary, no config lookup, flat membership test for check). Two tasks, sequenced.
  - TASK-000050 (US1/US2/US4) — VALID_REF_KINDS constant in one place (_models/_item.py) + reject unknown --kind at ref add and create --ref; bare ref add stays first-class; the three new kinds (supersedes/depends-on/duplicates) accepted. Foundation.
  - TASK-000051 (US3/US4, blocked by 50) — consumers + docs: depends-on≡blocks in sq blocked; sq check warns on unknown kinds in files and on Superseded decisions lacking an incoming supersedes edge; the one canonical eight-row kinds table in workflow.md.j2 with help pointing at it.
  - Boundary: the stability-CONTRACT wording (closed-in-1.0 + extension policy, verbatim per ADR-000049) is FEAT-000013's to write, not this feature's — same split we used on FEAT-000019. TASK-000051 ships the docs kinds table + help only.
  - Format unchanged: kinds are additive, schema stays 0.3, no migration (verified). @python-dev — start with TASK-000050; 51 unblocks when its constant lands.
- [2026-06-11T20:50:05Z] Mara Tester:
  - QA verification complete. FEAT-000035 closes as Done. All acceptance criteria verified hands-on in a scratch squad (tmp dir, sq init, items of several types).
  - US1 PASS: ref add --kind banana exits 1 listing all 8 valid kinds; --kind fixe exits 1 listing valid kinds; create --ref id:banana exits 1. All 8 kinds (related, blocks, depends-on, implements, fixes, addresses, supersedes, duplicates) accepted via ref add and at least 3 via create --ref id:kind.
  - US2 PASS: bare ref add <id> works unchanged (exit 0), stored as plain ID in frontmatter (no :kind suffix), CLI renders as (related) at add time, shows as plain ID in sq show.
  - US4 + blocked equivalence PASS: A=TASK-000019 depends-on E=TASK-000020 reported by sq blocked as 'blocked by E'. C=TASK-000021 blocks F=TASK-000022 reported as 'blocked by C'. Mixed usage in one squad works. Item G blocked via both spellings (two separate blockers) appears once with both blockers listed — no duplication.
  - sq check warnings PASS: walked ADR-000024 to Superseded without incoming supersedes edge — sq check emitted 'warn ADR-000024: status is Superseded but no incoming supersedes edge found', exit 0 (warning, not error). Added ADR-000025 supersedes ADR-000024 — warning gone, sq check clean. Unknown-kind-in-files path: covered by test fixtures (tests/test_service.py::test_check_warns_on_unknown_ref_kind and tests/test_cli.py::test_check_warns_unknown_kind_and_superseded_cli) that inject junk kinds directly into frontmatter — both pass. Not verified by hand-editing managed files, as required.
  - US3 PASS: sq workflow renders the kinds table with all 8 rows (meaning, direction convention, consumers). Equivalence 'A depends-on B ≡ B blocks A' stated explicitly. sq <type> <n> ref add --help reads 'Run sq workflow for the canonical kinds table (meaning, direction, and which commands consume each kind)'.
  - Real repo: uv run pytest 275 passed 1 skipped; uv run sq check clean (no issues).
  - Note: contract-doc wording (ADR-000049 Consequences, FEAT-000013 stability contract) is FEAT-000013's scope — deferred by design, FEAT-000035 already links FEAT-000013 as a ref. ADR-000049 remains Proposed pending op-pierre acceptance per its status note.
<!-- sq:discussion:end -->
