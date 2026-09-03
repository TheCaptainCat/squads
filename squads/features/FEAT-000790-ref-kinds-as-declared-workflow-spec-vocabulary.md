---
id: FEAT-790
sequence_id: 790
type: feature
title: Ref kinds as declared workflow-spec vocabulary
status: Draft
author: product-owner
refs:
- ADR-775:implements
subentities:
- local_id: US1
  title: Declare [ref_kinds] as a workflow-spec section
  status: Todo
- local_id: US2
  title: Bind engine behaviour to declared semantics, not literals
  status: Todo
- local_id: US3
  title: Per-capability floor and the live-corpus refusal
  status: Todo
- local_id: US4
  title: sq workflow ref-kinds --json catalog command
  status: Todo
- local_id: US5
  title: Reissue the ref-kind contract prose (tech-writer)
  status: Todo
  assignee: tech-writer
created_at: '2026-08-24T18:24:12Z'
updated_at: '2026-08-24T18:25:20Z'
---
<!-- sq:body -->
## The problem

Ref kinds are a nine-entry frozenset (`VALID_REF_KINDS`) baked into code, not a declared piece of
the workflow spec. Every other vocabulary axis — types, statuses, lifecycles, collections,
sub-entity kinds — went through this conversion already: declared in the merged spec, validated
against it by name, overridable and extensible by a project. Ref kinds are the one axis still
closed, and the engine binds several behaviours (the `sq blocked` graph, the roster skill
resolver, the supersedes check) to literal kind spellings rather than to what those kinds mean —
so a project cannot rename `depends-on` without silently losing `sq blocked`, and cannot add its
own kind at all.

ADR-775 rules this out: `[ref_kinds]` joins the workflow spec, engine behaviour binds to a
declared semantic role instead of a literal name, and the bundled `targets` kind (needed for
FEAT-693's milestone membership) ships as the worked example of a kind with no engine binding at
all.

## Shape

- **`[ref_kinds]` becomes a keyed section of the workflow document**, on the same terms as
  `[statuses]`/`[collections]`/`[subentity_kinds]`: it enters `WORKFLOW_TOP_LEVEL_SECTIONS`, the
  `[selected]` closed section list, and the shared merge engine, with no special case. Each entry
  declares a `label`, an optional `hint`, and an optional semantic `role`.
- **`VALID_REF_KINDS` retires as the vocabulary authority.** The eight call sites that consult the
  frozenset today resolve against the active spec's declared ref-kind set instead. The accepted
  set in every `ref add --kind` refusal becomes the project's own, not a fixed nine.
- **Engine behaviour binds to a kind's declared semantic, never to its spelling.** Three semantics,
  each with the literal binding it replaces: `dependency` (with `direction = "blocker"` or
  `"dependent"`) drives the `sq blocked` graph, replacing the literal `blocks`/`depends-on` checks;
  `preload` drives the roster resolver's skill-to-role inversion, replacing the literal `scopes`
  checks; `supersession` drives `sq check`'s incoming-supersedes rule, replacing the literal
  `supersedes` check. A kind declaring no semantic is navigational only — the default, and what an
  adopter-declared kind gets unless it says otherwise.
- **A per-capability floor, checked on the merged spec, fail-closed, every violation collected:**
  exactly one kind may carry `preload` (zero strands every custom skill, two make the resolver's
  inversion ambiguous); at most one kind per `dependency` direction; zero is legal for `dependency`
  and `supersession` (a project may choose to have no such capability at all); a kind name may not
  contain `:` and must be a bare TOML key.
- **The live-corpus cross-check gains ref kinds.** A kind that a merged spec drops or renames while
  live refs still carry it is refused, listing the offending IDs — the same shape the check
  already uses for a dropped type prefix or folder. A kind no edge uses may be dropped or renamed
  freely.
- **`targets` ships bundled and navigational** — no engine binding, consumed only by the derived
  view that names it in its own source declaration (FEAT-693).
- **A `tests/meta` scan** asserts no bundled ref-kind name appears as a literal in `src/squads/`
  outside `_specs/` and `_migrations/` (migration runners keep their frozen literals deliberately —
  they read the vocabulary of the schema version they transform, never the live spec).
- **`sq workflow ref-kinds --json`** joins the catalog family (`types`, `statuses`,
  `subentity-kinds`, `collections`), complete on first ship — declared entry, label, hint, semantic
  role, direction where applicable.
- **The contract prose that stated the closed-vocabulary policy retires**, and is reissued by the
  tech-writer rather than landed by a developer beside the engine change (ADR-775 §6): leaving the
  stability document and the generated cheatsheet promising a closed list the engine no longer
  enforces is the worse of the two states, so the docs follow the engine. The cheatsheet carrier
  (`_rendering/templates/workflow_static.md.j2`) is a bundled template, so retiring its text is a
  bundled-template edit and queues behind the version bump, on the release ordering ADR-781 states
  once for every template-touching change in this release.

## Acceptance

- `[ref_kinds]` is a declared, merge-able, deselect-able section of the workflow spec; an
  undeclared kind is refused by name in `ref add --kind`, `sq check`, and every other consultation
  site — no frozenset remains as an authority.
- Renaming `depends-on` to a project's own spelling (with `dependency`/`blocker` declared) keeps
  `sq blocked` working against the renamed kind; renaming `scopes` keeps the roster resolver
  working; renaming `supersedes` keeps `sq check`'s incoming-supersedes rule working. None of the
  three is found as a literal anywhere the `tests/meta` scan covers.
- The per-capability floor fires, with every violation collected in one pass, for: two kinds
  claiming `preload`; two kinds claiming the same `dependency` direction; a kind name containing
  `:`; a kind name that isn't a bare TOML key.
- Dropping or renaming a ref kind that live refs still carry is refused, naming the offending
  items; dropping or renaming one with no live refs succeeds.
- `targets` ships bundled, declares no semantic, and a project can add its own navigational kind
  (e.g. `escalates`) the same way.
- `sq workflow ref-kinds --json` lists every declared kind's label, hint and semantic role
  complete on first ship.
- `docs/stability.md` and the generated cheatsheet no longer state a closed, frozen ref-kind
  vocabulary; the replacement wording is authored by the tech-writer, as its own story, and lands
  behind the version bump that the manifest regeneration requires.
- This rides the same schema bump as FEAT-693/FEAT-694's on-disk format changes rather than forcing
  a second one — `[ref_kinds]` itself is a workflow-spec-format change, not a stored-item-shape
  change, so it needs no migration runner of its own.

## Out of scope

- Re-deciding the merge engine's own semantics (deep merge, splat-refs, `[selected]`) — settled by
  ADR-696 and unchanged here.
- The derived-view mechanism itself and the `MILE-`/`targets` build — that is FEAT-693's scope;
  this feature only makes `targets` (and any adopter-declared kind) a legal, declared vocabulary
  entry for a view's source to name.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 790 add-story "As a <role>, I want … so that …"`; track with `sq feature 790 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Declare [ref_kinds] as a workflow-spec section |
| US2 | Todo |  | Bind engine behaviour to declared semantics, not literals |
| US3 | Todo |  | Per-capability floor and the live-corpus refusal |
| US4 | Todo |  | sq workflow ref-kinds --json catalog command |
| US5 | Todo | tech-writer | Reissue the ref-kind contract prose (tech-writer) |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Declare [ref_kinds] as a workflow-spec section

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
`[ref_kinds]` enters the workflow document as a keyed section on the same terms as
`[statuses]`/`[collections]`/`[subentity_kinds]`: `WORKFLOW_TOP_LEVEL_SECTIONS`, the `[selected]`
closed section list, and the shared merge engine, with no special case. Each entry declares a
`label`, an optional `hint`, and an optional semantic `role`. `VALID_REF_KINDS` retires as the
vocabulary authority; the eight call sites that consult the frozenset resolve against the active
spec's `ref_kinds` instead, and `ItemSpec.ref_rules`'s existing check that a rule's `kind` names an
acceptable entry now checks it against the declared section rather than the frozenset.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Bind engine behaviour to declared semantics, not literals

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
Engine behaviour binds to a kind's declared semantic role instead of its spelling, for the three
semantics the engine actually needs: `dependency` (with `direction = "blocker"` or `"dependent"`)
drives the `sq blocked` graph and its two-way binding, replacing the literal `blocks`/`depends-on`
checks; `preload` drives the roster resolver's skill-to-role inversion, replacing the literal
`scopes` checks; `supersession` drives `sq check`'s incoming-supersedes rule, replacing the
literal `supersedes` check in the validator. A kind declaring no semantic is navigational, which
is the default. A `tests/meta` scan (in the shape already used for bundled roster status
literals) asserts none of the ~12 converted bindings' kind names survive as a literal in
`src/squads/` outside `_specs/` and `_migrations/` — migration runners keep their frozen literals
deliberately, since a runner reads the vocabulary of the schema version it transforms, never the
live spec.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Per-capability floor and the live-corpus refusal

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
The per-capability floor is checked on the merged spec, fail-closed, with every violation
collected in one pass rather than stopping at the first: exactly one declared kind may carry
`preload`; at most one kind per `dependency` direction; zero is legal for `dependency` and for
`supersession` (a project may choose to have neither capability at all); a kind name may not
contain `:` (it would break `split_ref`) and must be a bare TOML key. Separately, the live-corpus
cross-check gains ref kinds on the same terms it already covers a dropped type prefix or folder:
a kind the merged spec drops or renames while live refs still carry it is refused, naming the
offending item IDs and the two performable remedies (restore the entry, or remove the edges
first); a kind no live edge uses may be dropped or renamed freely.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — sq workflow ref-kinds --json catalog command

<!-- sq:story:US4:head -->
**Status:** ⚪ Todo
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
`sq workflow ref-kinds --json` joins the existing catalog family (`types`, `statuses`,
`subentity-kinds`, `collections`, `lifecycles`, `roles`) as a new command, listing every declared
kind's key, label, hint and semantic role (plus direction, where the semantic is `dependency`),
complete on first ship rather than growing keys across releases. `targets` ships bundled,
declaring no semantic, as the worked example of a kind whose only consumer is a declared view
naming it in FEAT-693 — and a project can add its own navigational kind (e.g. `escalates`) the
identical way, with no engine change required.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Reissue the ref-kind contract prose (tech-writer)

<!-- sq:story:US5:head -->
**Status:** ⚪ Todo
**Assignee:** Theo Writer
<!-- sq:story:US5:head:end -->

<!-- sq:story:US5:body -->
The tech-writer reissues the ref-kind contract prose, not a developer landing it beside the engine
change (ADR-775 §6's explicit ruling: leaving the stability document and cheatsheet promising a
closed list the engine no longer enforces is the worse state, so the docs must follow the engine).
Two carriers retire together: `docs/stability.md`'s "the nine built-in kinds are frozen … reserved
for a future release" passage, and the generated cheatsheet's "the vocabulary is closed — exactly
nine kinds, no custom extensions in 1.0" line (`_rendering/templates/workflow_static.md.j2`, also
the text of the `squads` skill). The replacement states: ref kinds are declared vocabulary, the
bundled set is the default, a project may declare its own or rename/drop an unused built-in
subject to the live-corpus refusal, and engine behaviour binds to a kind's declared semantic role
rather than its name. Because the cheatsheet carrier is a bundled template, this story's landing
is sequenced behind the version bump per the release ordering ADR-781 states once for the whole
set of template-touching changes in this release — it is not merged ahead of that bump.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
