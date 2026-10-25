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
- BUG-827
- ADR-320
- ADR-1007
created_at: '2026-08-22T09:28:22Z'
updated_at: '2026-10-25T21:42:16Z'
---
<!-- sq:body -->
## Context

FEAT-693 needed a `targets` kind for milestone membership, and the operator asked whether ADR-49's
closed vocabulary should hold against adopter-declared kinds. ADR-49 closed it on four arguments.
Three of them no longer hold and the fourth is discharged, which makes this a supersession rather
than a third amendment to that decision.

- **"A custom kind, by definition, has no consumer."** A derived view's source names a ref kind
  and projects its inversion, so an adopter-declared kind acquires exactly the sort of consumer
  ADR-49 set as the bar, the same inversion the roster resolver performs for the preload kind.
- **"Validation must distinguish rejected-as-typo from locally-declared-and-valid."** That
  distinction is the ordinary case on every other vocabulary axis. Types, statuses, lifecycles,
  collections, sub-entity kinds and status roles are all declared in the merged spec and validated
  against it; a value the merged spec does not declare is refused by name. ADR-696 §1 states the
  general form: validation replaces trust, and validation replaces prohibition.
- **"FEAT-14 is itself pre-design and contract-bearing, so wedging a registry into it couples two
  undesigned surfaces."** ADR-85 shipped and ADR-696 §4/4a/4b settled the merge engine. The
  `.overrides/` home ADR-49 reserved for this facility exists, with a closed top-level key space,
  a `[selected]` deselect, splat-refs, a provenance stamp and a lint verb.
- **"Shared semantics are the point."** This one survives, and it is the only one. It is answered
  below by binding engine behaviour to a declared semantic instead of freezing spellings: the same
  trade ADR-696 §1 made for statuses.

Two facts about the vocabulary bound what follows. A kind is **durable on-disk data**, stored
inline in frontmatter as `"ID:kind"`, which places it in the same class as a status name or a type
prefix. And an undeclared kind on an existing edge is a `sq check` finding, not a load failure, so
the cost of getting the vocabulary wrong is bounded, unlike a re-prefixed type, whose whole corpus
drops out of the on-disk scan.

## Decision

### 1. Ref kinds are a declared section of the workflow spec

`[ref_kinds]` is a keyed section of the workflow document on the same terms as `[statuses]`,
`[collections]` and `[subentity_kinds]`: it is in `WORKFLOW_TOP_LEVEL_SECTIONS`, in the closed
section list of `[selected]`, and in the shared merge engine, with no special case anywhere. The
accepted set is `spec.ref_kinds`; there is no frozen vocabulary constant. Every site that accepts
or validates a kind (`ref add --kind`, the importer, `sq check`'s unknown-kind rule, the loader's
`ref_rules` check) resolves against the active spec.

Each entry declares a `label`, an optional `hint`, and an optional semantic `role` (§2). Identity
is the dict key, never restated on the value, the convention `ItemSpec`/`StatusSpec`/`Lifecycle`/
`Collection` follow.

`ItemSpec.ref_rules` carries a per-type `kind`, and the loader refuses a rule naming a kind that is
not a declared entry of `[ref_kinds]`, because such a rule could never fire.

### 2. Engine behaviour binds to a kind's declared semantic, never to its name

ADR-696 §1's rule applied to a second axis. The engine states what it needs from a kind; the spec
declares which kind supplies it; no engine site reads a kind's spelling. The semantics the engine
needs, as values of `role`:

| Semantic | Engine behaviour |
| --- | --- |
| `dependency`, with `direction = "blocker"` or `"dependent"` | the `sq blocked` graph and the two-way binding it prints |
| `preload` | a skill's forward edge to the role that preloads it, inverted by the resolver |
| `supersession` | `sq check`'s incoming-supersedes rule |
| `default` | the kind a bare ref encodes (§3a) |
| none | display and navigation only |

A kind that declares no semantic is navigational. That is the default, and it is what an
adopter-declared kind gets unless the adopter says otherwise. A kind carrying `default` is
navigational too: `default` names an encoding, and nothing in the graph, the roster resolver or
the validators branches on it.

A `tests/meta` scan keeps this true (`test_no_bundled_ref_kind_literal_outside_the_spec_layer`):
no bundled ref-kind name appears as a literal in `src/squads/` outside `_specs/` and
`_migrations/`. Migration runners keep their frozen literals, because a migration reads the
vocabulary of the schema version it transforms, never the live spec.

### 3. The floor: what the declared set must supply

Per capability, checked on the merged spec, fail-closed, every violation collected (ADR-696 §3's
shape):

- **Exactly one kind carries `preload`.** Zero leaves every custom skill unreachable from the role
  that scopes it; two make the resolver's inversion ambiguous. The resolved list is materialised
  into the agent hosts' own configuration, so a spec the engine cannot drive would corrupt
  generated config.
- **Exactly one kind carries `default`**, and it is mandatory (§3a).
- **At most one kind per `dependency` direction.** Two kinds spelling `blocker` would make the
  normalisation ambiguous, and the graph has one edge kind, not two.
- **Zero is legal for `dependency` and `supersession`.** A squad that declares no dependency kind
  gets an empty `sq blocked`, a stated choice rather than a stranded item. The floor is per
  capability because a lifecycle with no settled status strands items that can never close, while
  a missing navigational capability simply answers nothing.
- **A kind name may not contain the ref separator** `:`, because `split_ref` partitions on it, and
  must be a TOML bare key so it stays splat-ref addressable (ADR-696 §4a).

### 3a. The bare ref encodes the declared `default` kind

A bare `"ID"` on disk is an edge of the kind carrying `role = "default"`, bundled on `related`.
Most stored edges carry no kind at all, so the wire form must be total: a spec declaring no
default kind would turn existing on-disk data into a load failure.

- **Renaming the kind that carries `default` is permitted and safe**, with no reserved name and no
  exemption. The bare form binds to the declared semantic, never to a spelling, so a rename
  relabels the same edges instead of re-pointing them. A reserved `related` was rejected: it would
  reinstate the frozen literal §2 removes.
- **The dangerous reassignment is unrepresentable.** Because `default` is a value of the one `role`
  field, the kind carrying it can never also carry `dependency`, `preload` or `supersession`, so
  the bare form can never come to denote a blocking, preload or supersession edge. What remains
  possible is moving `default` between two navigational kinds, a relabel of edges that drive no
  engine behaviour.
- **One on-disk encoding per edge.** An edge whose kind is the declared default is always written
  bare; squads never emits the spelled form of the default kind.
- **`_models/` resolves no vocabulary.** `make_ref`/`split_ref` are structural: a bare ref decodes
  to an unspelled kind, and resolution to the declared default happens where the active spec is in
  hand (`WorkflowSpec.default_ref_kind()`). `Item.from_frontmatter` takes the resolved default kind
  as a **required** keyword and folds a spelled default to the bare form at its input, so all three
  of its call sites, `sq repair` included, produce the canonical encoding, and omitting the
  argument is a type error. `frontmatter_skew`/`ensure_no_skew` take the same required argument,
  and each caller resolves it once per pass, so a spec declaring the wrong number of default kinds
  fails as one clean refusal. A `tests/meta` guard enumerates `Item.from_frontmatter`'s call sites,
  so adding one is a deliberate change.

### 3b. Encodings: repair canonicalises, and the guard reports a stale encoding as one

- **`sq repair` canonicalises the file, not only the index.** It writes back every file whose
  folded refs differ from the raw frontmatter (markdown before the index, as always), and it
  converges: a second repair is byte-identical. It is the standing remedy for a spelled default
  arriving by hand edit, merge resolution, import or a third-party writer, at any version.
- **The legacy `extra.ref_kinds` map is read only by the migration runners.** Since the 0.16
  flattening (ADR-1007), the model reads no `extra`; the fold of that map, with the rule that a
  default kind is written bare, lives in the migration compat reader and runs inside the runner
  that flattens a file. A migration runner never borrows a live model primitive: each carries its
  own frozen fold, beside the frozen type table it already carries.
- **A refusal may not assert a cause the reader can disprove.** When the only difference between
  the file and the index is a non-canonical encoding of the item's refs, the skew guard still
  refuses (the index holds a non-canonical encoding, and rewriting the file from it would commit
  it), but it says so: `the index holds a non-canonical encoding of refs, not a divergence`, with
  `sq repair` as the remedy. A diverging key counts as a normalisation difference only when its raw
  on-disk value equals the index's **and** the round trip produced its value from that raw key
  alone. `sq check` carries the same distinction in the same words.

### 4. `targets` ships bundled, and navigational

`targets` declares no semantic. Its consumer is a declared view over the inversion of its edges
(`milestone_rollup`), which names the kind in its own source declaration, so it needs no engine
binding. Nothing about it is special: an adopter declaring `escalates` and a view over it walks the
identical path.

### 5. A kind carried by live refs may not be dropped or renamed, at the write and lint boundary

For every kind the merged spec drops or renames, the live-corpus cross-check lists the items whose
`refs` still carry it, on ADR-696 §5a's terms: the value is durable on-disk data that no scan
re-derives.

- **It stores nothing new.** The expected set is recoverable from the corpus: every edge carries
  its own kind inline.
- **An empty corpus is unaffected.** A kind no edge uses may be dropped or renamed freely, which is
  the case the capability was asked for: choosing your vocabulary when you adopt squads.
- **The refusal is bounded to the write and lint boundary and is never a load failure.** What
  refuses: `sq workflow lint`, and any command that would *write* a ref of an undeclared kind. What
  keeps running: every read command; `sq check`, which reports the stale kind as a bounded finding;
  `sq repair`; and the ref-removal verb. Nothing vanishes from the scan the way a re-prefixed type
  does, and a load-time lock would make the second remedy unperformable.
- **The remedies are performable end to end with shipped verbs.** Restore the entry, or remove the
  edges (`sq <type> <n> ref remove`), then re-apply the change. The message states that sequence,
  and names `sq repair` as what canonicalises a non-canonical encoding.
- **`sq graph` may not omit an edge it can see.** An undeclared-kind edge traverses, and its node
  reports `edge_semantic: null`. `refs --in`/`--all`, `sq graph` and `sq check` give one answer.

### 6. The extension policy

The contract prose:

> Ref kinds are declared vocabulary. The bundled set is the default; a project may declare its own,
> and may rename or drop a built-in it does not use, subject to the same live-corpus refusal that
> protects a type or a status. A kind the merged spec does not declare is still rejected. Engine
> behaviour binds to a kind's declared semantic role, never to its name — so a renamed dependency
> kind keeps driving `sq blocked`, and a kind with no semantic is navigational.

`docs/stability.md` and the generated cheatsheet carry that policy, and the cheatsheet's kinds
table is generated from the merged spec, so a project's own kinds appear in its own `sq workflow`
output and in the skill text its agents read. Neither carries a literal count. The contract prose
is the tech-writer's to maintain, and the docs follow the engine.

**The rule for the next request.** A kind squads' own tooling consumes ships bundled with its
semantic declared, as a normal spec-vocabulary addition. A kind only an adopter consumes needs no
bundled addition: they declare it, and a view or their own convention is its consumer.

### 7. Interaction with derived views and the override model

A view's source may name any kind the merged spec declares, and an adopter-declared view over an
adopter-declared kind is not a combined case: both are keys in one document, resolved by one merge
and validated by one pass, against each other. The referential check is the one `ref_rules`
already gets.

Because ref kinds are a section of the workflow document, they inherit that document's whole
override treatment by registration: the merge, the closed top level, `[selected]`, the provenance
stamp, content-gated drift (ADR-777) and `sq workflow lint`'s collect-all report.

### 8. `sq graph --json` emits a declared kind key, and a semantic beside it

- **The dependency normalisation stays.** Collapsing `A blocks B` and `B depends-on A` dedupes to
  a single edge.
- **`edge_kind` emits a declared kind key**, never a semantic and never a fixed sentinel. For a
  dependency edge it is the key of the kind carrying `dependency` in the **dependent** direction
  (`depends-on` under the bundled spec); where a project declares only the blocker direction, the
  blocker key is the canonical one. `direction` keeps its meaning: `"out"` means the expanded item
  depends on the child.
- **The node carries `edge_semantic`**: the edge kind's declared semantic role, or `null` for a
  navigational or undeclared kind. This is the field a consumer branches on; emitting only the
  spelling would leave every agent testing `edge_kind == "depends-on"`, the defect §2 removes from
  the engine.

## Consequences

- **Schema.** No item's stored bytes change shape: an edge is still `"ID"` or `"ID:kind"`.
  `[ref_kinds]` is a workflow-spec-format element, the same class as ADR-696 §2a's `live` flag.
- **`sq workflow ref-kinds --json`** is the catalog row for the section, under ADR-738's
  one-catalog-per-spec-map rule.
- **The unknown-kind refusal keeps its shape.** `ref add --kind` lists the accepted set, and the set
  is the project's.
- **`sq check`'s unknown-kind rule is one membership test**, against the merged spec, with no
  exception path to consult.
- **What is genuinely lost.** An `"ID:kind"` edge is not self-describing outside its home squad for
  a project-declared kind. That is the one ADR-49 argument this decision pays rather than refutes,
  and the price is the one already paid for a renamed type or status.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-22T09:30:30Z] `architect` Robert Architect:
  - Supersedes ADR-49 rather than amending it a third time: three of its four arguments are now false (a view is the consumer a custom kind lacked; declared-and-validated is the norm on every other vocabulary axis; the .overrides home it reserved is built), and the surviving one — shared semantics — is answered by binding engine behaviour to a declared semantic instead of freezing spellings.
  - Ref kinds become a [ref_kinds] section of the workflow document; VALID_REF_KINDS retires as the authority. ~12 literal bindings (blocks/depends-on in the sq blocked graph, scopes in the roster resolver, supersedes in the check validator) convert to declared semantics, guarded by a tests/meta scan in the shape ADR-696 section 2 used for roster status literals.
  - A kind is durable on-disk data, so the live-corpus cross-check gains it on ADR-696 section 5a terms: a kind live refs still carry cannot be dropped or renamed. targets ships bundled and navigational — its consumer is the view that names it.
  - Left Proposed. @op-pierre @manager the call is yours; the one thing I would flag for a ruling is retiring the verbatim closed-vocabulary policy from docs/stability.md and the generated cheatsheet, since that text is quoted in the 1.0 contract.
- [2026-08-22T09:44:34Z] `op-pierre` Pierre Chat:
  - Retire ADR-49 closed-vocabulary policy from its carriers, and have the tech-writer reissue the contract prose rather than a developer. Leaving the stability document promising a closed list the engine no longer enforces is worse than editing the contract; the docs must follow the engine.
- [2026-08-22T09:47:39Z] `architect` Robert Architect:
  - Folded the ruling on ADR-49 policy retirement into section 6: both carriers go, and the tech-writer reissues the contract prose rather than a developer landing it beside the engine change. Recorded your reasoning — the docs follow the engine, because a stability document promising a closed list the engine no longer enforces is the worse state.
  - Noted the trap that inherits: workflow_static.md.j2 is a bundled template, so retiring that text forces a manifest regen and queues behind the version bump. Stated once in ADR-781 section 6 and cited here; docs/stability.md is not package data and carries no such constraint.
- [2026-08-25T15:02:56Z] `architect` Robert Architect:
  - Amended in place at its own end (A1-A2). A1: the bare-ref shorthand becomes a declared "default" role - a fourth value of the same role field, exactly one kind carries it, mandatory, bundled on "related". Renaming the kind carrying it is permitted and safe because the bare form binds to the semantic and never to a spelling; a reserved "related" is rejected as reinstating the frozen literal section 2 removes. Section 5 is deliberately NOT extended: a bare ref stores no kind, so the corpus carries no evidence of the entry it was written under - the ADR-696 5a property does not hold here, and the gap is closed at the vocabulary end instead.
  - Because "default" is a value of the one role field, the kind carrying it can never also carry dependency/preload/supersession - the dangerous reassignment is unrepresentable rather than detectable. What remains is moving "default" between two navigational kinds, a relabel of edges that drive no engine behaviour; recorded as residue, not guarded. DEFAULT_KIND retires as a literal rather than moving: _models/ resolves no vocabulary, so the ref primitives become structural (a bare ref decodes to an unspelled kind) and resolution happens where the active spec is in hand.
  - A2: sq graph --json keeps the dependency normalisation (it is what dedupes a doubly-authored pair) and emits a declared kind key - the dependent-direction kind, or the blocker key where a project declares only that direction. GraphNode gains edge_semantic, which is what a consumer branches on; emitting only the spelling would leave every agent testing edge_kind == "depends-on", the same declared-but-found-by-literal defect section 2 removes from the engine. Ruled on TASK-796 and TASK-797. @tech-lead
- [2026-08-25T15:53:41Z] `architect` Robert Architect:
  - Amended in place at its own end (A3). A1s safety claim is RESTORED, not narrowed: the design holds and an implementation emitted an encoding A1 itself forbids. fold_legacy_kinds spells the default kind out because make_ref became structural, so a legacy extra.ref_kinds edge naming the default loads spelled and the next ordinary mutation commits it -- driven at the BUNDLED spec with no rename, and a regression against the retired make_ref, which collapsed the default to bare.
  - A3 rules three things. The normalisation duty sits at the service load boundary, where the active spec is already in hand, and must sit on the load path both sides of the frontmatter skew guard traverse; _models/ stays vocabulary-free and A1s split is unchanged. No corrective corpus sweep: every corpus migrated to 0.2 before the structural change already holds the canonical bare form, so the damage is prospective. And a migration runner may not borrow a live model primitive -- the 0.1-to-0.2 runner imports fold_legacy_kinds and so changed its on-disk output retroactively; each runner carries its own frozen fold.
  - A3 also states the shape for the graph silent-skip, which is a distinct defect reachable with no legacy fold: sq graph may not omit an edge it can see, so an undeclared-kind edge traverses and its node reports no declared semantic in A2s edge_semantic key. Ruled on BUG-804; the fix is its own task, not TASK-797. @tech-lead
- [2026-08-25T16:10:13Z] `architect` Robert Architect:
  - A3 corrected in place after driving all three load paths. The service load boundary is not one seam, and the seam that phrase reads like - _index/_store.py::_validate_item_vocab - is the wrong side: that path builds items with SquadsDB.model_validate_json and never calls Item.from_frontmatter, so no fold runs there and normalising there manufactures the false skew. A3 now names the three paths, rules the normalisation at the fold INPUT (Item.from_frontmatter takes the resolved default kind as a required keyword), and reverses its own rejection of that threading - the "many call sites" premise is false, there are three.
  - Three factual corrections to A3, each driven rather than reasoned. The damage is NOT prospective: at HEAD a legacy-map item is already refused on its next mutation with a false refs skew, and the refusal advertised remedy (sq repair) then stores the spelled default in the index and commits it to disk with sq check clean - so sq repair was an unnamed third owed path. The two sides do NOT re-derive through an identical fold; the index side never folds at all. And symmetrising frontmatter_skew does not fix it - drove that, refs still skews, because the legacy map is data the index does not hold.
  - One-site-one-test survives, under the threading shape only. Anti-drift is a tests/meta guard enumerating Item.from_frontmatter three call sites, and the agreement test asserts convergence across five encodings of one edge rather than the absence of a warning. No corrective sweep still holds with a corrected reason: disk is canonical, an already-repaired squad index is not, and re-running sq repair after the fix re-derives it. Ruled on TASK-806. @tech-lead
- [2026-08-25T18:00:49Z] `architect` Robert Architect:
  - Amended in place at its own end (A4), and corrected A3 no-sweep clause. REV-808 F3 falsified its premise: disk is not already canonical everywhere, because the create door wrote a spelled default until the fold landed and from_frontmatter folded only when a legacy ref_kinds map was present. The conclusion survives on a mechanism instead - run_pending_migrations ends every non-empty batch with repair() before stamping, and the root callback refuses every command on a squad whose schema is behind, so the 0.14 migration this release already owes IS the sweep and owes no step of its own. Driven end to end.
  - A step of its own is refused on its own terms as well as being redundant: a frozen runner cannot resolve which kind carries default without reading the live spec, and the state is not schema-keyed at all - a hand edit, merge, import or third-party writer reach it at any version, including after migrating. Also recorded what the repair does NOT do: disk keeps the spelled form until the next ordinary mutation, and A1 encoding invariant is read as binding what squads emits rather than claiming no pre-fold file can hold a spelled default.
  - A4 rules the guard report. The refusal stands - the index genuinely holds a non-canonical encoding - but the diagnosis does not, since frontmatter_skew compares disk-after-fold against index-as-stored and the difference is the fold, not a divergence. New standing rule beside the unperformable-remedy one: a refusal may not assert a cause the reader can disprove. Separable at the site from data already in hand, with sq check carrying the same distinction. Ruled on REV-808 F3. @tech-lead
- [2026-08-25T18:20:43Z] `architect` Robert Architect:
  - A4 corrected in place: its separability test was short by one row and the reasoning behind that row is withdrawn. The tech lead drove three states against the skew site and the legacy extra.ref_kinds row falsifies the raw-equality test - I reproduced it in-process. A4 had reasoned that the map differs raw; the extra key does, but _read_extra pops ref_kinds before the comparison, so extra never reaches the diverging list and only refs does, with its raw value equal to the index because the kind lived in a different key.
  - Corrected rule now in A4: a diverging key is a normalisation difference only when its raw on-disk value equals the index AND the round trip produced that value from that raw key alone. A fold that drew on a second raw key is information-adding and needs repair, and raw equality on the folded key is exactly what makes that case look innocent. _invented_timestamps is the precedent, sharpened - the raw side must be consulted for every input the round trip drew on, not only for the key that ends up diverging. The three-row table is recorded in the decision so the withdrawn reasoning is visibly replaced. Ruled on TASK-811 ST1. @tech-lead
- [2026-08-26T11:46:17Z] `architect` Robert Architect:
  - Amended in place at its own end (A5), ruling BUG-827. A1 restored rather than narrowed: driven, the rename relabels both a legacy-folded and a native edge to the new default with every surface agreeing - what fails is the corpus holding a second, spelled encoding that A1 itself forbids. A3s toleration of the un-rewritten file is withdrawn, on the disproof of its own stated ground: after a default-kind rename the fold resolves the two encodings to two different kinds. sq repair now canonicalises the file, not only the index - it is not schema-keyed, resolves the default from the live spec, and covers the arrival paths A3 named.
  - Section 5s refusal is bounded to the write and lint boundary and is never a load failure, measured against this decisions own Context (an undeclared kind is a sq check finding, not a load failure - the bound that justified opening the vocabulary at all). Section 5 borrowed ADR-696 5a terms and its blast radius with them; 5a earns that radius because a re-prefixed corpus vanishes from the scan, and nothing vanishes here. Driven: the load-time lock makes section 5s own second remedy unperformable, generally, not just for legacy data.
- [2026-10-25T21:42:16Z] `architect` Robert Architect:
  - 2026-10-25 audit: body rewritten in present tense; decision unchanged. A1-A5 folded into sections 3a, 3b, 5 and 8. The legacy extra.ref_kinds fold is now described as migration-only (ADR-1007), from_frontmatter takes a required default kind, repair canonicalises the file, section 5 refuses at the write and lint boundary only, sq graph traverses undeclared kinds. Build-order and dated sediment removed.
<!-- sq:discussion:end -->
