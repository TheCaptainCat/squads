---
id: ADR-775
sequence_id: 775
type: decision
title: Ref kinds are declared spec vocabulary bound by semantic role
status: Accepted
author: architect
refs:
- FEAT-693:addresses
- ADR-49:supersedes
- ADR-696
- ADR-85
- ADR-492
- ADR-738
- ADR-776
- ADR-777
- ADR-781
created_at: '2026-08-22T09:28:22Z'
updated_at: '2026-08-25T18:20:43Z'
---
<!-- sq:body -->
## Context

FEAT-693 needs a `targets` kind for milestone membership, and the operator asked whether ADR-49's
closed vocabulary should hold against adopter-declared kinds. ADR-49 closed it on four arguments.
Three of them are now false and the fourth is discharged, which makes this a supersession rather
than a third amendment to that decision.

- **"A custom kind, by definition, has no consumer."** FEAT-693 builds the consumer. A derived
  view's source names a ref kind and projects its inversion, so an adopter-declared kind acquires
  exactly the sort of consumer ADR-49 set as the bar — the same inversion the roster resolver
  already performs for `scopes` (read: `_services/_base.py:1172-1180`).
- **"Validation must distinguish rejected-as-typo from locally-declared-and-valid."** That
  distinction is now the ordinary case on every other vocabulary axis, and it is shipped. Types,
  statuses, lifecycles, collections, sub-entity kinds and status roles are all declared in the
  merged spec and validated against it; a value the merged spec does not declare is refused by name
  (read: `_specmerge.merge_override`, `_workflow/_loader.py:152-170`). ADR-696 §1 states the general
  form: validation replaces trust, and validation replaces prohibition.
- **"FEAT-14 is itself pre-design and contract-bearing, so wedging a registry into it couples two
  undesigned surfaces."** ADR-85 shipped and ADR-696 §4/4a/4b settled the merge engine. The
  `.overrides/` home ADR-49 reserved for this facility exists, with a closed top-level key space,
  a `[selected]` deselect, splat-refs, a provenance stamp and a lint verb (driven:
  `sq override scaffold --help` accepts `workflow` and `playbook` alongside templates and roles).
- **"Shared semantics are the point."** This one survives, and it is the only one. It is answered
  below by binding engine behaviour to a declared semantic instead of freezing spellings — the same
  trade ADR-696 §1 made for statuses, where the alternative was three status names no project could
  rename.

Two facts about the vocabulary bound what follows. A kind is **durable on-disk data**, stored inline
in frontmatter as `"ID:kind"` (read: `_models/_item.py:104-112`), which places it in the same class
as a status name or a type prefix and therefore under the same live-corpus refusal (ADR-696 §5a)
rather than under a freeze. And an undeclared kind on an existing edge is a `sq check` finding
(read: `_services/_validators.py:243`), not a load failure — so the cost of getting the vocabulary
wrong is bounded, unlike a re-prefixed type, whose whole corpus drops out of the on-disk scan.

## Decision

### 1. Ref kinds become a declared section of the workflow spec

`[ref_kinds]` joins the workflow document as a keyed section on the same terms as `[statuses]`,
`[collections]` and `[subentity_kinds]`: it enters `WORKFLOW_TOP_LEVEL_SECTIONS`, the closed section
list of `[selected]`, and the shared merge engine, with no special case anywhere. `VALID_REF_KINDS`
(read: `_models/_item.py:89-101`) retires as the vocabulary authority; the accepted set is
`spec.ref_kinds`, and the eight call sites that consult the frozenset (read: `_services/_refs.py:370`,
`:546-550`; `_services/_import.py:128`; `_services/_validators.py:243`; `_services/_base.py:595`;
`_workflow/_loader.py:313-324`) resolve against the active spec instead.

Each entry declares a `label`, an optional `hint`, and an optional semantic `role` (§2). Identity is
the dict key, never restated on the value — the convention `ItemSpec`/`StatusSpec`/`Lifecycle`/
`Collection` already follow (read: `_workflow/_models.py`, `Collection`'s own docstring).

`ItemSpec.ref_rules` already carries a per-type `kind`, and the loader already refuses a rule naming
a kind no ref surface would accept, on the stated ground that such a rule could never fire (read:
`_workflow/_models.py:342-345`, `_workflow/_loader.py:307-324`). That check keeps its shape and
changes only its authority: a rule's `kind` must name a declared entry of `[ref_kinds]`.

### 2. Engine behaviour binds to a kind's declared semantic, never to its name

ADR-696 §1's rule applied to a second axis. The engine states what it needs from a kind; the spec
declares which kind supplies it; no engine site reads a kind's spelling.

The semantics the engine actually needs, each with the literal binding it replaces (all read):

| Semantic | Engine behaviour | Bound today as |
| --- | --- | --- |
| `dependency`, with `direction = "blocker"` or `"dependent"` | the `sq blocked` graph and the two-way binding it prints | `"blocks"` / `"depends-on"` at `_services/_refs.py:36`, `:79-80`, `:111-116`, `:250`, `:608-611`; `_services/_results.py:36-42`; `_cli/_main.py:922-928` |
| `preload` | a skill's forward edge to the role that preloads it, inverted by the resolver | `"scopes"` at `_services/_base.py:1178`, `_services/_config_integrity.py:160`, `_services/_items.py:73`, `_services/_retirement.py:54` |
| `supersession` | `sq check`'s incoming-supersedes rule | `"supersedes"` at `_services/_validators.py:432`, `:667`; `_workflow/_models.py:1111-1115` |
| none | display and navigation only | nothing |

A kind that declares no semantic is navigational. That is the default, and it is what an
adopter-declared kind gets unless the adopter says otherwise.

The `supersession` row is the one worth naming separately, because it is already half-converted and
reads as done. The rule is declared per type in `ref_rules`, and ADR-696-era work made a project
that drops the `decision` type take the check with it — but the validator still finds the rule by
comparing `rr.kind` against the literal `"supersedes"` (read: `_services/_validators.py:432`), so a
project that renames the kind keeps the declaration and silently loses the check. Declared-but-found-
by-literal is the exact defect ADR-696 §1 named on the status axis.

A `tests/meta` scan keeps this true, in the shape ADR-696 §2 established for roster status literals
(read: `tests/meta/test_no_bundled_roster_status_literal_outside_the_spec_layer.py`): no bundled
ref-kind name appears as a literal in `src/squads/` outside `_specs/` and `_migrations/`. Migration
runners keep their frozen literals for the reason that decision already gives — a migration reads
the vocabulary of the schema version it transforms, never the live spec.

### 3. The floor: what the declared set must supply

Per-capability, checked on the merged spec, fail-closed, every violation collected — ADR-696 §3's
shape, not a second rulebook.

- **Exactly one kind carries `preload`.** Zero leaves every custom skill unreachable from the role
  that scopes it; two make the resolver's inversion ambiguous. This is the roster-strictness case
  (ADR-696 §3): the resolved list is materialised into the agent hosts' own config, so a spec the
  engine cannot drive corrupts generated config rather than merely making a view odd.
- **At most one kind per `dependency` direction.** Two kinds spelling `blocker` would make the
  normalisation at `_services/_refs.py:79-80` ambiguous, and the graph has one edge kind, not two.
- **Zero is legal for `dependency` and `supersession`.** A squad that declares no dependency kind
  gets an empty `sq blocked`, which is a stated choice rather than a stranded item. The asymmetry
  with the lifecycle floor is deliberate and is the reason the floor is per-capability: a lifecycle
  with no settled status strands items that can never close, while a missing navigational capability
  simply answers nothing.
- **A kind name may not contain the ref separator** `:`, because `split_ref` partitions on it (read:
  `_models/_item.py:104-107`), and must be a TOML bare key so it stays splat-ref addressable
  (ADR-696 §4a).

### 4. `targets` ships bundled, and navigational

`targets` declares no semantic. Its consumer is a declared view over the inversion of its edges, and
the view names the kind in its own source declaration — so it needs no engine binding, and it is the
worked example of how a kind with no engine consumer earns its keep. Nothing about it is special:
an adopter declaring `escalates` and a view over it walks the identical path.

### 5. A kind carried by live refs may not be dropped or renamed

The live-corpus cross-check gains ref kinds, on exactly ADR-696 §5a's terms and for the reason it
gained `prefix` and `folder`: the value is durable on-disk data that no scan re-derives. For every
kind the merged spec drops or renames, the check lists the items whose `refs` still carry it and
refuses, with the offending IDs, in the wording the cross-check already uses.

Two properties, both following §5a:

- **It stores nothing new.** The expected set is recoverable from the corpus itself — every edge
  carries its own kind inline.
- **An empty corpus is unaffected.** A kind no edge uses may be dropped or renamed freely, which is
  the case the capability was actually asked for: choosing your vocabulary when you adopt squads.

The two performable remedies are to restore the entry, or to remove the edges first. The refusal
names those and nothing else, because no verb rewrites a corpus's kinds — the standing rule that a
refusal may never assert a remedy no command performs.

### 6. What replaces ADR-49's extension policy

ADR-49 required the contract doc to carry its extension policy verbatim, and two carriers ship it
today: `docs/stability.md:322-328` ("The nine built-in kinds are frozen … A project-declared
custom-kind extension is reserved for a future release") and the generated cheatsheet
`_rendering/templates/workflow_static.md.j2:88` ("The vocabulary is closed — exactly nine kinds, no
custom extensions in 1.0"), which is also the text of the `squads` skill. Both retire together. The
replacement policy, in the same load-bearing register:

> Ref kinds are declared vocabulary. The bundled set is the default; a project may declare its own,
> and may rename or drop a built-in it does not use, subject to the same live-corpus refusal that
> protects a type or a status. A kind the merged spec does not declare is still rejected. Engine
> behaviour binds to a kind's declared semantic role, never to its name — so a renamed dependency
> kind keeps driving `sq blocked`, and a kind with no semantic is navigational.

The cheatsheet's kinds table stays generated from the merged spec, so a project's own kinds appear in
its own `sq workflow` output and in the skill text its agents read. The literal count leaves both
carriers: ADR-49's own amendment note already ruled that the count was never the contract.

**Who reissues the contract prose, and in what order.** The replacement is contract wording, not a
code comment, so the **tech-writer** reissues it rather than a developer landing it beside the
engine change — leaving the stability document promising a closed list the engine no longer enforces
is the worse of the two states, so the docs follow the engine rather than lagging it.

The cheatsheet carrier is a **bundled template** (`_rendering/templates/workflow_static.md.j2`), so
retiring that text is a bundled-template edit and forces a template-manifest regeneration. It
therefore sits behind the version bump, on the sequencing stated once in the pointer decision rather
than restated here. `docs/stability.md` is not package data and carries no such constraint.

**The rule for the next request, which is what the operator asked for.** There is no queue to
administer. A kind squads' own tooling consumes ships bundled with its semantic declared, and is
therefore a normal spec-vocabulary addition. A kind only an adopter consumes needs no bundled
addition at all — they declare it, and a view or their own convention is its consumer. The reviewed-
addition process ADR-49's amendment invented existed only because the alternative was a frozen
literal; with the section declared, the question "may we add a kind" stops being asked of us.

### 7. Interaction with the derived-view mechanism and the override model

A view's source names a ref kind, so this decision bounds what a view can project — and the bound
dissolves rather than being widened. A view may name any kind the merged spec declares, and an
adopter-declared view over an adopter-declared kind is not a combined case at all: both are keys in
one document, resolved by one merge and validated by one pass, against each other. The referential
check is the one `ref_rules` already gets (read: `_workflow/_loader.py:307-324`), which is why the
combination needs no rule of its own.

Because ref kinds are a section of the workflow document, they inherit that document's whole override
treatment by registration — the merge, the closed top level, `[selected]`, the provenance stamp and
`sq workflow lint`'s collect-all report. The uniformity decision's manifest widening is what makes a
kinds override drift honestly rather than warning on every release; without it, an adopter who
declares one kind gets a stale-override warning for the rest of the project's life.


## Consequences

- **Schema-version call.** No item's stored bytes change shape: an edge is still `"ID:kind"` and
  `targets` is a new value in an existing field. `[ref_kinds]` is a workflow-spec-format change, the
  same class as ADR-696 §2a's `live` flag, which took no schema bump and no migration runner. A
  migration is still owed for the FEAT-693 item type, and this rides that release without adding a
  reason of its own.
- **`sq workflow` gains a catalog row.** Under ADR-738's one-catalog-per-spec-map rule, a new keyed
  section owes `sq workflow ref-kinds --json`, and the row lands complete on first ship rather than
  growing keys across releases — the split-by-row rule that section already settled.
- **The unknown-kind refusal keeps its shape and changes its message.** `ref add --kind` still lists
  the accepted set; the set is now the project's.
- **`sq check`'s unknown-kind rule keeps its single membership test.** ADR-49 defended that
  simplicity against a project-config exception path; the test is still one membership test, against
  the merged spec instead of a frozenset, and there is still no exception path to consult.
- **What is genuinely lost.** A `"ID:kind"` edge stops being self-describing outside its home squad
  for a project-declared kind. That is the one ADR-49 argument this decision pays rather than
  refutes, and the price is now identical to the one already paid for a renamed type or status.

## Amendment note

**2026-08-25 — the bare-ref wire format is a declared semantic (§3), and `sq graph --json`'s
`edge_kind` is bound by the same rule as the engine (§2).** §3's floor enumerates what the
declared set must supply and does not reach the one kind the on-disk format encodes by omission;
§2 converts every engine binding and does not say what the agent-facing graph contract emits once
a project renames its dependency kind. Both are settled here rather than in code, because one is
durable on-disk data and the other is a read surface agents branch on.

### A1. The bare-ref shorthand is a declared `default` role, and the kind carrying it is renameable

`make_ref`/`split_ref` omit the kind when it equals `DEFAULT_KIND = "related"`, so a bare `"ID"`
on disk decodes as `related` (read: `_models/_item.py:22`, `:104-112`). That constant is wire
format, not a display default: 598 of this squad's 1068 stored edges carry no kind at all
(driven). Renaming that kind would silently re-point every one of them, and §5 cannot see it — a
bare ref stores no kind, so the corpus carries no evidence of which entry it was written under.
That is exactly the property ADR-696 §5a relies on for `prefix` and `folder`, and it does not hold
here. §5 is therefore not extended; the gap is closed at the vocabulary end instead.

**`default` becomes a fourth value of the `role` field §2 declares** — not a second field. Exactly
one declared kind carries it, and the bundled spec declares it on `related`.

- **Exactly one, and mandatory** — unlike `dependency` and `supersession`, where §3 makes zero
  legal. The wire form must be total: a bare ref written by any earlier squads has to keep
  decoding, and a spec declaring no default kind would turn existing on-disk data into a load
  failure rather than the bounded `sq check` finding this decision's Context relies on to keep the
  cost of a wrong vocabulary small.
- **Renaming the kind that carries `default` is permitted and safe**, with no reserved name and no
  exemption. The bare form binds to the declared semantic and never to a spelling — §2's rule
  applied to the encoding — so a rename relabels the same edges instead of re-pointing them. A
  reserved `related`, exempt from rename, was the alternative and is rejected: it reinstates the
  frozen literal §2 exists to remove, and the `tests/meta` scan would have to carve it out by
  name.
- **The dangerous reassignment is made unrepresentable rather than detectable.** Because `default`
  is a value of the one `role` field, the kind carrying it can never also carry `dependency`,
  `preload` or `supersession` — so the bare form can never come to denote a blocking, preload or
  supersession edge. What remains possible is moving `default` between two navigational kinds,
  whose whole effect is relabelling edges that drive no engine behaviour. That residue is stated
  rather than guarded, and it is the reason no corpus check is owed.
- **`default` names an encoding, not an engine binding.** Nothing in the graph, the roster
  resolver or the validators branches on it. §2's "a kind that declares no semantic is
  navigational" stands with this one companion: a kind carrying `default` is navigational too.
- **One on-disk encoding per edge.** An edge whose kind is the declared default is always written
  bare, and the spelled form of the default kind is never emitted, so the corpus stays canonical
  and a spelled default arriving by hand or through import normalises on the next write.

`DEFAULT_KIND` retires as a vocabulary literal rather than moving somewhere else. `_models/`
resolves no vocabulary — the acyclic invariant is why `effective_prefix` exists — so the ref
primitives become structural: a bare ref decodes to an **unspelled** kind, and resolution to the
declared default happens where the active spec is already in hand. Two consequences worth naming,
because both make the surrounding code smaller rather than larger: the sites that only want the
target ID (`_models/_index.py`, `_services/_items.py`, `_services/_retype.py`) stop touching the
vocabulary at all, and the display sites (`_cli/_common.py:527`, `:706`; `_cli/_items.py:630`;
`_cli/_skill.py:213`) test whether a kind was spelled instead of comparing it against a name.

### A2. `sq graph --json` emits a declared kind key, and gains a semantic field beside it

`edge_kind` normalises both dependency spellings to the literal `"depends-on"` (read:
`_services/_refs.py:36`, `:79-80`, `:111-116`), documented as the output contract at
`_cli/_main.py:995-998` and on `GraphNode` itself. §2 converts the engine binding and leaves the
emitted value unstated. It is a read surface agents branch on, so it is ruled here.

- **The normalisation stays.** Collapsing the pair is what lets an item authored with both
  `A blocks B` and `B depends-on A` dedupe to a single edge; emitting the raw spelling would
  un-collapse it into two.
- **`edge_kind` emits a declared kind key — never a semantic, never a fixed sentinel.** Every
  value of the field stays the same kind of thing, and a project's own spelling is what its agents
  read. For a dependency edge it is the key of the kind carrying `dependency` in the **dependent**
  direction, which is `depends-on` under the bundled spec. §3 permits a project to declare only
  the blocker direction; in that case the blocker key is the canonical, and `direction` keeps the
  meaning it has today either way — `"out"` means the expanded item depends on the child.
- **The node gains `edge_semantic`**: the edge kind's declared semantic role, or `null` for a
  navigational kind. This is the field a consumer branches on. Emitting only the spelling would
  leave every agent testing `edge_kind == "depends-on"` — the same declared-but-found-by-literal
  defect §2 removes from the engine, since an agent reading this JSON is one of its consumers.
  Emitting only the semantic would lose the spelling the display needs and would collide with a
  project free to name a kind `dependency`.
- The field lands complete on first ship rather than growing across releases, and the `--json`
  docstring states both fields and which one to branch on.

### A3. The declared default kind is never spelled on disk, and the fold owes that

A1 states the encoding invariant in passing — an edge whose kind is the declared default is always
written bare, and the spelled form of the default kind is never emitted — and leaves it to fall out
of the write path. It does not. `Item.from_frontmatter` folds a pre-0.2 `extra.ref_kinds` map
through `fold_legacy_kinds`, and `make_ref`, structural per A1 and correctly so, spells out whatever
kind it is handed. A legacy-map edge naming the default kind therefore loads spelled, and the next
ordinary mutation of that item commits the spelled form to disk. Driven under the bundled spec with
no rename anywhere, and the sequence is worse than one bad write. A status update on such an item is
**refused** — `on-disk frontmatter has diverged from the index (refs)` — because the disk side of the
skew guard folds the map to `ID:related` while the index still holds the bare form. The refusal's own
advertised remedy then completes the damage: `sq repair` re-derives the index from disk and stores
`refs: [ID:related]`, after which the next mutation commits the spelled form to the file, strips the
map that recorded where it came from, and `sq check` reports clean.

A1's safety claim is **restored, not narrowed**. It is a claim about the design, and the design
holds: a bare ref carries no spelling, so a rename relabels it rather than re-pointing it. What
failed is an implementation emitting an encoding A1 itself forbids. Narrowing the claim to
natively-written edges would record an implementation defect as a design limit, and would leave a
corpus holding two encodings of one edge — the worse standing state, and the one that makes a
renamed default diverge across surfaces.

**Where the duty sits — the seam, named.** "The service load boundary" is not one seam, and the
seam that phrase most reads like is the wrong one. Three paths build or hold an item whose `refs`
must be canonical, and only two of them ever run the fold:

- `_index/_store.py::_read_from_disk` — behind `IndexStore.load` and `transaction`, and where
  `_validate_item_vocab` runs — builds its items with `SquadsDB.model_validate_json`. It **never
  calls `Item.from_frontmatter`**: `_read_refs` is reached only from `_frontmatter_payload`, which
  has exactly one caller. No fold runs here, and the refs this side holds are already canonical.
  **Normalisation must not go here.** Placing it beside `_validate_item_vocab` normalises the index
  side of the skew guard while the disk side still spells, which is what manufactures a false skew
  on every legacy-map item.
- `_itemfile.py::frontmatter_skew:222` builds the **disk side** of that guard through
  `Item.from_frontmatter`. This is the side that spells.
- `_services/_maintenance.py::_rebuild_index_from_disk:1324` — `sq repair` — is the third, and the
  only one that **stores** the folded item, which is how a spelled default reaches the index and
  then the corpus.

A fourth call site, `_scan_for_check:2209`, parses and discards; it carries nothing anywhere and
needs nothing.

Reconciling the two sides after the fold does not work, and the guard's own docstring is what
misleads here: it claims both sides go through the identical round trip, and they do not. Driven,
putting the base side through `Item.from_frontmatter(base.to_frontmatter_dict())` too still reports
`refs` skew, because the legacy map is real data the index does not hold. The fold is
information-adding on the disk side, so the encoding must be canonical **when the fold produces
it**.

**So: one site, at the fold's input — which reverses this note's own exclusion below.**
`Item.from_frontmatter` takes the resolved default kind as a **required** keyword argument and hands
it to `_read_refs`/`fold_legacy_kinds`, which emit a bare ref when the legacy map names that kind.
All three call sites inherit it, `sq repair` included, and no wrongly-encoded item ever exists to be
corrected afterwards.

The objection this note first recorded — many call sites, and a defaulted parameter regressing
silently at any one that omits it — does not survive being driven. `Item.from_frontmatter` has
**three** call sites in `src/squads/`, all named above, and a **required** keyword makes an omission
a type error rather than a silent regression: ADR-777's B2 applies exactly that rule to
`top_level_keys`, for exactly this reason.

`frontmatter_skew`/`ensure_no_skew` take the same required argument. Their nine call sites are all
`Service` mixin methods with `self.spec` already in hand — `_base.py:1009`, `_items.py:360`,
`_subentities.py:686` and `:746`, `_retype.py:161`, `_rename.py:124`, `_import.py:301`,
`_maintenance.py:254` and `:2033` — so nothing new is threaded through the CLI. Each caller resolves
`WorkflowSpec.default_ref_kind()` **once per pass** rather than per item, so a spec declaring the
wrong number of default kinds fails as one clean refusal naming the spec instead of raising partway
through a rebuild.

**What keeps the sites from drifting is structural, not convention.** The fold has one
implementation and one entry point, and a `tests/meta` guard enumerates `Item.from_frontmatter`'s
three call sites so that adding a fourth fails the suite — the shape
`tests/unit/test_agent_backend_abc_stays_at_seven_documented_methods.py` already uses. Drift is
reachable only by adding a site, and adding a site is the thing that fails.

**The agreement test asserts convergence, not the absence of a warning.** Table-driven over the
encodings of one edge, each written as an on-disk file against an index holding the canonical form:
bare `refs: [ID]`; spelled `refs: [ID:related]`, the form a repair at an unfixed version could
already have committed; bare plus `extra.ref_kinds: {ID: related}`; and the non-default controls
`refs: [ID:blocks]` and bare plus `{ID: blocks}`. For each row: `frontmatter_skew` returns empty,
`sq repair` stores the canonical encoding, the next ordinary mutation writes it, and `sq check` is
clean throughout. The three default-kind rows must converge on **bare**, the two controls on
`ID:blocks`. The load-bearing assertion is that the legacy-map row and the bare row produce
byte-identical `to_frontmatter_dict()` output — the property that the two sides re-derive to the
same thing, asserted rather than relied on as a coincidence. One corpus-level row runs the whole set
through `sq check`, `sq repair`, `sq check`, a mutation of every item, and `sq check` again, with the
index's `refs` byte-identical across the repair; that row catches an asymmetry introduced at any of
the three sites rather than only at the one under test.

**`_models/` still resolves nothing.** It cannot know which kind is the default without an import
cycle or a re-frozen literal — the literal A1 retired, and nothing here reopens it. Receiving a
resolved kind as an argument is not resolving one, which is exactly the split A1 already draws for
`make_ref`/`split_ref`, and it is what lets the fold be canonical at its input while `_models/`
gains no vocabulary.

**No corrective sweep, and the remedy is a command that already exists.** That conclusion holds; the
premise recorded for it does not, and is withdrawn. Disk is not already canonical everywhere. A
pre-0.14 squad can hold a spelled default kind on disk **and** in its index at once, byte-identical
on both sides, written by the create door that stayed open until the fold landed and read back
verbatim because `Item.from_frontmatter` folded only when an `extra.ref_kinds` map was present. At
that version the state is legal, `sq check`-clean and freely mutable; at this one the item is refused
on its next mutation. So the reach is wider than "an index repaired at an interim build", and the
reason no sweep is owed has to be a mechanism rather than an assumption about the corpus's shape.

**The mechanism is already in the upgrade path, and is what discharges this.**
`run_pending_migrations` ends every non-empty batch with `repair()` before it stamps the new schema,
and the root callback refuses every command on a squad whose schema is behind — so a pre-0.14 squad
cannot reach a mutating command without first running `sq migrate up`, and that run re-derives the
index from the folded disk. The 0.14 migration this release already owes for the new item types
therefore **is** the sweep, and owes no ref-canonicalisation step beyond bumping the schema (driven:
a squad holding a spelled default consistently on both sides, stepped through `sq migrate up`, comes
out with a bare index, a mutation that succeeds, and `sq check` clean). Stated here because it is now
load-bearing rather than incidental: a release that ships no runner ships no repair, and this
coverage would leave with it unnoticed.

**A step of its own is refused on its own terms, not only as redundant.** A frozen runner cannot know
which kind carries `default` without reading the live spec — the coupling the clause below forbids —
and the state is not keyed to a schema version at all: it arrives by hand edit, merge resolution,
import, or a third-party writer, at any version, including after the migration has run. A one-shot
step cannot cover an arrival path that stays open; `sq repair` covers every one of them, which is
what makes it the standing remedy rather than a fallback. So no new verb is owed, which is what the
standing rule against asserting an unperformable remedy requires.

**What the repair does not do is rewrite the file.** Disk keeps the spelled form until that item's
next ordinary mutation, which writes it bare. That is tolerated rather than corrected, and A1's
encoding invariant is read accordingly: it binds what squads **emits**, and never claimed that no
file predating the fold can hold a spelled default. Such a file is check-clean, mutable and
self-correcting on its next write, and nothing downstream distinguishes the two encodings, because
the fold resolves them to one kind before any consumer sees either.

**A migration runner may not borrow a live model primitive.** The 0.1-to-0.2 runner calls
`fold_legacy_kinds` from `_models`, so making `make_ref` structural changed that runner's on-disk
output retroactively: the same input yields a bare ref under one release and a spelled one under the
next. §2 grants `_migrations/` its frozen literals on the ground that a migration reads the
vocabulary of the schema version it transforms; the same ground forbids it reading a live
*primitive* into which that vocabulary is folded. Each runner carries its own frozen fold, beside
the frozen type table it already carries.

**The graph's silent skip is a distinct defect, settled by none of the above.**
`_out_neighbours`/`_in_neighbours` drop every edge whose kind the merged spec does not declare, with
no signal, while `refs --in`/`--all` list that same edge under its stale name and `sq check` warns
on it: three surfaces, three answers to one question. It needs no legacy fold to reach — any
undeclared-kind edge does, arriving from an import, a merge, or an edge authored after a `[selected]`
deselect. The rule: `sq graph` answers what is connected to an item, so it may not omit an edge it
can see. An undeclared-kind edge traverses, and its node reports no declared semantic in the
`edge_semantic` key A2 adds. Absence of a declaration is a value to emit, never grounds to delete
the node.

**2026-08-25 — the skew guard's report is ruled where A3 ruled the fold.** A3 settles where the
normalisation sits and what it owes the corpus; it does not say what the guard tells an adopter when
the fold, and not a divergence, is the whole of the difference. That message is the only surface a
squad reaching this state after its migration ever meets, so it is settled here rather than in code.

### A4. A stale index encoding is reported as one, and never as a divergence

Driven: a squad holding `refs: [TASK-20:related]` in the file and `["TASK-20:related"]` in the index
— the same bytes on both sides — is refused on its next mutation with `on-disk frontmatter has
diverged from the index (refs)`, and `sq check` reports `refs drift between frontmatter and index`.
Nothing diverged. `frontmatter_skew` compares the disk side **after** the fold against the index side
as stored, and its own docstring records that asymmetry as deliberate and load-bearing; what the
guard sees is the fold it applied to one side, not a change to the file.

- **The refusal stands.** It is not a false positive: the index genuinely holds a non-canonical
  encoding, and rewriting the file from an index-derived item would commit the spelled form —
  exactly the write the guard exists to stop. What is wrong is the diagnosis, not the decision, and
  only the diagnosis changes.
- **A refusal may not assert a cause the reader can disprove.** The standing rule that a refusal may
  never name a remedy no command performs gains its companion. An adopter sent to `sq repair` for a
  divergence they can open the file and see is not there learns to distrust the guard, which is the
  one thing a guard on the integrity core cannot afford.
- **The two cases are separable at the site, from data already in hand — but raw equality alone is
  not the test.** `frontmatter_skew` holds both the raw parsed frontmatter and its round-tripped
  form, and that is the right place and the right data. The discriminator this note first recorded
  was that a diverging key whose **raw** on-disk value equals the index's is a normalisation
  difference by construction, since the round trip only adds corrections. It is short by one row,
  driven in-process over three states:

  | State | Diverging | Raw == index | Correct verdict |
  | --- | --- | --- | --- |
  | index `["BUG-20:related"]`, file `refs: [BUG-20:related]` | `refs` | yes | stale encoding |
  | file `refs: [BUG-20]` + `extra.ref_kinds: {BUG-20: blocks}`, index `["BUG-20"]` | `refs` | yes | needs repair |
  | file's `title` hand-edited | `title` | no | needs repair |

  The middle row is the miss, and the reasoning that missed it is withdrawn: this note said the
  legacy map "differs raw", and the `extra` key does — but `_read_extra` pops `ref_kinds` out of
  `extra` before the comparison, so `extra` never reaches the diverging list at all. Only `refs`
  does, and its raw value equals the index's, because the kind lived in a *different* key.

  **The rule, corrected.** A diverging key is a normalisation difference only when its raw on-disk
  value equals the index's **and** the round trip produced its value from that raw key alone. When
  the fold drew on a second raw key, the difference is information-adding and needs repair — and
  raw equality on the folded key is precisely what makes that case look innocent, since the round
  trip consumes the key carrying the information and discards it. `_invented_timestamps`
  (`_itemfile.py:240-248`) already reads the raw frontmatter for the same reason, in its own words:
  once the round trip has spoken, the two cases are indistinguishable from its output. The
  correction is that the raw side must be consulted for every input the round trip drew on, not
  only for the key that ends up diverging.

  Nothing new is stored, `_models/` gains no vocabulary, and the discrimination stays at the one
  site that already computes both sides.
- **What each says.** A real divergence keeps today's wording. A stale encoding says what it is: the
  index holds a non-canonical encoding of this item's refs, `sq repair` re-derives it, and the next
  ordinary write canonicalises the file. `sq check`'s finding for the same state carries the same
  distinction in the same words — one state, one explanation, on both surfaces.

**Nothing further is owed to the adopter, and that is a finding rather than an omission.** A
migration `manual` clause would instruct them to run the repair `sq migrate up` had just run on their
behalf, and a release note would describe a state the upgrade path does not let them reach. The
message is the notification, which is precisely why it has to be true.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-22T09:30:30Z] Robert Architect:
  - Supersedes ADR-49 rather than amending it a third time: three of its four arguments are now false (a view is the consumer a custom kind lacked; declared-and-validated is the norm on every other vocabulary axis; the .overrides home it reserved is built), and the surviving one — shared semantics — is answered by binding engine behaviour to a declared semantic instead of freezing spellings.
  - Ref kinds become a [ref_kinds] section of the workflow document; VALID_REF_KINDS retires as the authority. ~12 literal bindings (blocks/depends-on in the sq blocked graph, scopes in the roster resolver, supersedes in the check validator) convert to declared semantics, guarded by a tests/meta scan in the shape ADR-696 section 2 used for roster status literals.
  - A kind is durable on-disk data, so the live-corpus cross-check gains it on ADR-696 section 5a terms: a kind live refs still carry cannot be dropped or renamed. targets ships bundled and navigational — its consumer is the view that names it.
  - Left Proposed. @op-pierre @manager the call is yours; the one thing I would flag for a ruling is retiring the verbatim closed-vocabulary policy from docs/stability.md and the generated cheatsheet, since that text is quoted in the 1.0 contract.
- [2026-08-22T09:44:34Z] Pierre Chat:
  - Retire ADR-49 closed-vocabulary policy from its carriers, and have the tech-writer reissue the contract prose rather than a developer. Leaving the stability document promising a closed list the engine no longer enforces is worse than editing the contract; the docs must follow the engine.
- [2026-08-22T09:47:39Z] Robert Architect:
  - Folded the ruling on ADR-49 policy retirement into section 6: both carriers go, and the tech-writer reissues the contract prose rather than a developer landing it beside the engine change. Recorded your reasoning — the docs follow the engine, because a stability document promising a closed list the engine no longer enforces is the worse state.
  - Noted the trap that inherits: workflow_static.md.j2 is a bundled template, so retiring that text forces a manifest regen and queues behind the version bump. Stated once in ADR-781 section 6 and cited here; docs/stability.md is not package data and carries no such constraint.
- [2026-08-25T15:02:56Z] Robert Architect:
  - Amended in place at its own end (A1-A2). A1: the bare-ref shorthand becomes a declared "default" role - a fourth value of the same role field, exactly one kind carries it, mandatory, bundled on "related". Renaming the kind carrying it is permitted and safe because the bare form binds to the semantic and never to a spelling; a reserved "related" is rejected as reinstating the frozen literal section 2 removes. Section 5 is deliberately NOT extended: a bare ref stores no kind, so the corpus carries no evidence of the entry it was written under - the ADR-696 5a property does not hold here, and the gap is closed at the vocabulary end instead.
  - Because "default" is a value of the one role field, the kind carrying it can never also carry dependency/preload/supersession - the dangerous reassignment is unrepresentable rather than detectable. What remains is moving "default" between two navigational kinds, a relabel of edges that drive no engine behaviour; recorded as residue, not guarded. DEFAULT_KIND retires as a literal rather than moving: _models/ resolves no vocabulary, so the ref primitives become structural (a bare ref decodes to an unspelled kind) and resolution happens where the active spec is in hand.
  - A2: sq graph --json keeps the dependency normalisation (it is what dedupes a doubly-authored pair) and emits a declared kind key - the dependent-direction kind, or the blocker key where a project declares only that direction. GraphNode gains edge_semantic, which is what a consumer branches on; emitting only the spelling would leave every agent testing edge_kind == "depends-on", the same declared-but-found-by-literal defect section 2 removes from the engine. Ruled on TASK-796 and TASK-797. @tech-lead
- [2026-08-25T15:53:41Z] Robert Architect:
  - Amended in place at its own end (A3). A1s safety claim is RESTORED, not narrowed: the design holds and an implementation emitted an encoding A1 itself forbids. fold_legacy_kinds spells the default kind out because make_ref became structural, so a legacy extra.ref_kinds edge naming the default loads spelled and the next ordinary mutation commits it -- driven at the BUNDLED spec with no rename, and a regression against the retired make_ref, which collapsed the default to bare.
  - A3 rules three things. The normalisation duty sits at the service load boundary, where the active spec is already in hand, and must sit on the load path both sides of the frontmatter skew guard traverse; _models/ stays vocabulary-free and A1s split is unchanged. No corrective corpus sweep: every corpus migrated to 0.2 before the structural change already holds the canonical bare form, so the damage is prospective. And a migration runner may not borrow a live model primitive -- the 0.1-to-0.2 runner imports fold_legacy_kinds and so changed its on-disk output retroactively; each runner carries its own frozen fold.
  - A3 also states the shape for the graph silent-skip, which is a distinct defect reachable with no legacy fold: sq graph may not omit an edge it can see, so an undeclared-kind edge traverses and its node reports no declared semantic in A2s edge_semantic key. Ruled on BUG-804; the fix is its own task, not TASK-797. @tech-lead
- [2026-08-25T16:10:13Z] Robert Architect:
  - A3 corrected in place after driving all three load paths. The service load boundary is not one seam, and the seam that phrase reads like - _index/_store.py::_validate_item_vocab - is the wrong side: that path builds items with SquadsDB.model_validate_json and never calls Item.from_frontmatter, so no fold runs there and normalising there manufactures the false skew. A3 now names the three paths, rules the normalisation at the fold INPUT (Item.from_frontmatter takes the resolved default kind as a required keyword), and reverses its own rejection of that threading - the "many call sites" premise is false, there are three.
  - Three factual corrections to A3, each driven rather than reasoned. The damage is NOT prospective: at HEAD a legacy-map item is already refused on its next mutation with a false refs skew, and the refusal advertised remedy (sq repair) then stores the spelled default in the index and commits it to disk with sq check clean - so sq repair was an unnamed third owed path. The two sides do NOT re-derive through an identical fold; the index side never folds at all. And symmetrising frontmatter_skew does not fix it - drove that, refs still skews, because the legacy map is data the index does not hold.
  - One-site-one-test survives, under the threading shape only. Anti-drift is a tests/meta guard enumerating Item.from_frontmatter three call sites, and the agreement test asserts convergence across five encodings of one edge rather than the absence of a warning. No corrective sweep still holds with a corrected reason: disk is canonical, an already-repaired squad index is not, and re-running sq repair after the fix re-derives it. Ruled on TASK-806. @tech-lead
- [2026-08-25T18:00:49Z] Robert Architect:
  - Amended in place at its own end (A4), and corrected A3 no-sweep clause. REV-808 F3 falsified its premise: disk is not already canonical everywhere, because the create door wrote a spelled default until the fold landed and from_frontmatter folded only when a legacy ref_kinds map was present. The conclusion survives on a mechanism instead - run_pending_migrations ends every non-empty batch with repair() before stamping, and the root callback refuses every command on a squad whose schema is behind, so the 0.14 migration this release already owes IS the sweep and owes no step of its own. Driven end to end.
  - A step of its own is refused on its own terms as well as being redundant: a frozen runner cannot resolve which kind carries default without reading the live spec, and the state is not schema-keyed at all - a hand edit, merge, import or third-party writer reach it at any version, including after migrating. Also recorded what the repair does NOT do: disk keeps the spelled form until the next ordinary mutation, and A1 encoding invariant is read as binding what squads emits rather than claiming no pre-fold file can hold a spelled default.
  - A4 rules the guard report. The refusal stands - the index genuinely holds a non-canonical encoding - but the diagnosis does not, since frontmatter_skew compares disk-after-fold against index-as-stored and the difference is the fold, not a divergence. New standing rule beside the unperformable-remedy one: a refusal may not assert a cause the reader can disprove. Separable at the site from data already in hand, with sq check carrying the same distinction. Ruled on REV-808 F3. @tech-lead
- [2026-08-25T18:20:43Z] Robert Architect:
  - A4 corrected in place: its separability test was short by one row and the reasoning behind that row is withdrawn. The tech lead drove three states against the skew site and the legacy extra.ref_kinds row falsifies the raw-equality test - I reproduced it in-process. A4 had reasoned that the map differs raw; the extra key does, but _read_extra pops ref_kinds before the comparison, so extra never reaches the diverging list and only refs does, with its raw value equal to the index because the kind lived in a different key.
  - Corrected rule now in A4: a diverging key is a normalisation difference only when its raw on-disk value equals the index AND the round trip produced that value from that raw key alone. A fold that drew on a second raw key is information-adding and needs repair, and raw equality on the folded key is exactly what makes that case look innocent. _invented_timestamps is the precedent, sharpened - the raw side must be consulted for every input the round trip drew on, not only for the key that ends up diverging. The three-row table is recorded in the decision so the withdrawn reasoning is visibly replaced. Ruled on TASK-811 ST1. @tech-lead
<!-- sq:discussion:end -->
