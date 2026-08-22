---
id: ADR-775
sequence_id: 775
type: decision
title: Ref kinds are declared spec vocabulary bound by semantic role
status: Proposed
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
updated_at: '2026-08-22T09:47:39Z'
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
<!-- sq:discussion:end -->
