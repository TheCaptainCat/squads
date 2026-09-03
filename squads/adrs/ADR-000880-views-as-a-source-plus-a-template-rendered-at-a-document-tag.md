---
id: ADR-880
sequence_id: 880
type: decision
title: Views as a source plus a template rendered at a document tag
status: Proposed
author: architect
description: Retire the projection layer; keep and widen sources; a content-free tag
  marks where a view renders on read
created_at: '2026-09-02T12:23:01Z'
updated_at: '2026-09-02T12:23:27Z'
---
<!-- sq:body -->
## The operator's model, restated

> "the projection over refs is dumb and useless. A view is just a template and a place to go,
> that's it. the main doc contains a tag that renders the view. voila"
>
> "yeah, the source mechanism is good, that needs to be scoped to all render time logic"

Read together: **a view is a source plus a template; a tag in a document is the place it
renders.** The source mechanism stays. The projection between source and template goes. And
the scope widens from item relations to every piece of render-time logic squads has.

This record scopes that model and prices it. It does not defend the shipped one.

## What the shipped shape actually costs

`_views.py` is 428 lines in three layers. Roughly 160 of them are source resolution
(`_resolve_ref_source`, `_resolve_subentity_source`, `_resolve_subtree_source`,
`_children_by_parent`, `resolve_records`) and template dispatch (`render_view`). The other
~270 are the middle layer: `_RawRecord`, `Cell`, `ViewFieldMeta`, `ViewRecord`, `ViewGroup`,
`Projection`, `project`, `_cell`, `_badge_cell`, `_sort_key`, `_BASE_RESOLVERS`,
`projection_json`.

Two things found while pricing it are evidence the middle layer is not carrying its weight,
and both are checkable rather than argued:

**It reimplements the template language, worse.** `group_by` and `order_by` are declared in
TOML and executed by `project` and `_sort_key`. Jinja 3.1 has `groupby`, `sort` and
`selectattr` natively. A field list declared in TOML needs a validator to prove its codes
resolve — that is `_check_view_fields`, `_check_view_source`'s field-set half,
`_check_item_views` and `VIEW_BASE_FIELDS_BY_SOURCE`. A template under `StrictUndefined`
validates the same thing for free, at render, against the actual record, and catches the case
a code check cannot: a field that resolves but renders nothing usable.

**Flattening heterogeneous records forces a lie.** `_check_view_source`'s own docstring
records it: a `ref` source's records can be items of any type, so its declared field set is
"the union across every declared item type's fields", and a code only some types carry
"renders `null` for the rest". That null is not data. It is the artifact of pressing
differently-shaped items into one row. A template handed the items themselves asks each one
what it has.

**Nothing consumes the projection's machine-readable half.** Searched `clients/vscode/src`
for `workflow view`, `milestone_rollup`, `projection`, and a view `groups` payload: no hits.
The client reads `sq tree --json` and `sq show --raw`. The projection has been the "contract"
for one release with zero clients on the other end of it.

## The mechanism

### A view declaration

```toml
[views.milestone_rollup]
source = { kind = "ref", name = "targets" }
```

`fields`, `group_by` and `order_by` are gone. What remains is where the data comes from. The
template is found by the view's own name at `templates/views/milestone_rollup.md.j2`, which is
already how presentation resolves today — no new convention.

### The tag

A single, content-free marker placed in a document body — the tag `sq:view:milestone_rollup`,
written in the usual HTML-comment marker form (spelled bare here, since a body may not carry a
well-formed marker).

Note the shape deliberately. Every marker in `_models/_markers.py` today is a **pair** —
`open_marker` / `close_marker` — and a pair defines a span. This one has no `close_marker`
counterpart and therefore no span. That is not cosmetic; see the next section.

### What the template receives

**The source's own shape, unflattened, plus the host item and the active spec.** For the three
relation sources that is a list of real `Item` / `SubEntity` objects — not `Cell`s, not
`_RawRecord`s. The template writes `{{ r.id }}`, `{{ r.status | badge }}`,
`{% for g in records | groupby('status') %}`.

### Who computes it

`resolve_records` becomes `resolve_source`, and it is already the right thing: a dispatch on
`source.kind` over three private resolvers. The honest statement is that **the source layer
does not shrink and does not change shape — it grows**. Ref inversion, the subtree walk and
the sub-entity collection read survive verbatim. What changes is that `kind` stops meaning
"which relation" and starts meaning "which resolver", which is what it already meant
mechanically.

## The trap: this is not the region we just deleted

Three commits ago (`b37cdc9d`, behind `0f514114` / `1cf1d300`) this repository's corpus was
stripped of `sq:summary` and `sq:<kind>:<local-id>:head`. Those were tags in a document
holding rendered content. The surface reading of this record is that it puts them back. It
does not, and the difference has to survive a careless reader.

**The separating property, as a testable invariant:**

> A view tag's bytes on disk carry the view's *name* and nothing else. There is no state in
> which the file's content disagrees with the computed truth, because the file holds no
> computed content.

A stored region held the *output*. It went stale because the values it rendered — an
assignee's display name, a mapped story's title — lived in other files, nothing re-derived it,
and no verb could tell fresh bytes from stale ones by looking at them. A tag holds an
*instruction*. A name has no freshness dimension to lose.

**The smallest rule that makes the failure unreachable rather than merely unlikely:** the view
tag is a self-closing marker with no closing counterpart. Materialisation needs a span to
write into. There is no span, so there is no code path that could write there — closed by
construction, not by discipline. Any future proposal to give the tag a body is the proposal to
rebuild the stored region, and should be read as exactly that.

Two consequences worth stating because they invert the old failure:

- `sq check` gains a rule it could never have had for a stored region: a `sq:view:<name>` tag
  naming a view the active spec does not declare, or whose template is missing, is a clean
  error. Stale rendered content was undetectable; a dangling name is trivially detectable.
- The repair sweep that strips retired regions must not learn to strip these. It distinguishes
  by marker **shape** — an unpaired `sq:view:` tag inside `:body` is authored content — not by
  a name list that a later view would fall off.

## What it costs

### `_views.py`

**Reduced, roughly halved, not deleted.** Source resolution and template dispatch survive
(~160 lines). The middle layer deletes (~270 lines).

Two pieces do not simply delete, and pretending otherwise would be the same mistake the
projection made:

- `_delivery_target` / `_is_delivered` — the settled-versus-delivered distinction (a lifecycle
  reaching its happy-path terminal, versus stopping some other way) is real logic and it
  stays. It stops being a declared boolean column and becomes something a template calls. It
  already resolves entirely off the spec, so it belongs on `WorkflowSpec` beside
  `first_settled_status`.
- `_badges.py` survives whole and must be reachable from a template, as a filter registered
  beside `slugify` / `open_marker` / `idnum` in `_rendering/_engine.py`. Without it every
  template hand-writes emoji, which is a worse outcome than the projection.

### The spec model

`ViewSpec.fields`, `group_by`, `order_by` delete. `_check_view_fields`, `_check_item_views`
and `VIEW_BASE_FIELDS_BY_SOURCE` delete. `_check_view_source` survives — checking that a
source's `name` resolves against its `kind`'s vocabulary is real and cheap.

`ItemSpec.views` deletes, and `_prune_orphaned_type_owned_views` deletes with it. That
function exists solely to un-brick a squad whose `[selected]` deselection orphaned a view the
adopter never wrote. Removing type-attachment removes the coupling that made it necessary.

### `[views.milestone_rollup]` and the roll-up

**The declaration survives, at one line.** The roll-up still works.

The joining survives too, and it is worth being exact about where, because "the roll-up needs
its members joined from refs" is true: **the join *is* the source.** Ref inversion is
`_resolve_ref_source`, which is the layer the operator kept. What goes is the step *after* the
join that turned each joined item into eight labelled cells. Grouping by status role and
ordering by type-then-id move into `milestone_rollup.md.j2` as `groupby` and `sort`.

**One real behavioural loss, and it is the sharpest risk in the change.** A type-attached view
applies retroactively to every existing item of that type. A tag does not — existing milestone
files carry no tag. So:

- `templates/items/milestone.md.j2` seeds the tag at creation, and
- a migration inserts the tag into existing milestone bodies.

That second step inserts into `:body`, which is **authored** content. Marker-safe editing has
never written into an authored region. Smallest containment: insert at a deterministic anchor
(end of `:body`), make it idempotent, skip any body already carrying the tag, and accept that
an author who later moves it keeps their placement.

### `--json`

**Per-source, not uniform.** `sq workflow view <name> <id> --json` serialises the source's own
records in a shape that source already has a serialiser for: a `ref` or `subtree` source emits
what `sq tree --json` and `sq list --json` already emit; a `subentity` source emits what the
per-kind list already emits; a role source emits the resolved definition.

This is better for a client than the projection envelope, not merely equal: it is a shape the
client already parses, instead of a bespoke `{fields, group_by, groups}` envelope it must
learn. The client reads `sq tree --json` and `sq show --raw` today and touches no view JSON at
all, so there is no migration to perform on the consumer side.

**The honest loss:** a client can no longer read a view's *columns* off the payload, because
the columns now exist only in the template and a template is not machine-readable. The line
that makes this acceptable: `--json` answers about the *data*, `--raw` answers about the
*text*. A client wanting the view as presented asks for the rendered text — which `show --raw`
already returns. Nobody has asked for a third thing.

## What it makes possible: role and skill definitions

The test case, verified against the code rather than asserted.

**1. `role_definition_text` is already this shape.** `_services/_base.py:1165` renders
`agents/role.md.j2` with exactly one context variable, `role=role`, and extracts the `sq:body`
region. A source (`resolve_role_with_base`: the catalog, merged with `.overrides/roles.toml`,
with operator-settable fields carried off the item by `role_base_from_item`) plus a template.
Nothing else. The operator's model, implemented once, bespoke.

**2. The role item's body region is already deliberately empty.** `_services/_base.py:858-864`
blanks `sq:body` at creation, with the reasoning written out in place: a stored region would
be a second copy of a value the resolver already answers, and the only copy that can go stale.
Every role file on disk already carries an empty body region waiting for something to render
into it on read. The tag is the thing that region is missing.

**3. The trigger is a hardcoded branch, which is what makes it undeclarable.**
`_cli/_role.py:478` calls `role_definition_text` from a branch keyed on `it is not None and r
is not None`. `_cli/_skill.py:148` calls `skill_definition_text` from a branch keyed on
`system`. Those branches are `items.<type>.views` by another name — type-keyed attachment with
a fixed position — except undeclared and invisible. Under the tag model both branches delete:
a role file's body carries the tag `sq:view:role_definition`, a system skill file's carries
its own, and generic tag expansion renders them. Three render paths collapse to one.

So yes: declarable, and the verification says something sharper than that. **The codebase has
been drifting toward this model on its own.** Rendering at read time was reinvented bespoke
three times — role text, system skill text, per-type skill text — because the declared
mechanism only spoke relations and could not express any of them. That is the gap the operator
is naming.

**4. One case does not fit cleanly, and it is where his model costs more than it saves.**
`_item_skill_definition_text` (`_base.py:1233`) passes **eight** kwargs: `title`, `type`,
`overview`, `lifecycle`, `commands`, `sections`, `subentity_kind`, `subentity_plural`. Under
"the template reads the source's own shape", the source hands over the playbook lane, the live
roster and the spec, and the template derives the rest — which means `linearize_lifecycle`,
`_item_skill_role_sections`, `custom_item_skill_commands` and `label_for` must become
reachable from Jinja. Smallest option that keeps the shape: register them as filters. They are
pure functions of the spec and the playbook; none needs rewriting in Jinja, only exposing.

## The source grammar, widened

The same two-key grammar, more values for `kind`. The three relation kinds survive unchanged:

| `source.kind` | `name` resolves against | what the template gets |
|---|---|---|
| `ref` | `[ref_kinds]` | items carrying that forward ref to the host |
| `subtree` | `[items]` | descendants of the host of that type |
| `subentity` | `[subentity_kinds]` | the host's own sub-entities of that kind |
| `role` | — | the resolved `RoleDef` (catalog + overrides + item fields) |
| `playbook` | `[items]`, or the host's own type | the type's playbook lane, the live roster, the spec |
| `self` | — | the host item, the spec, the squad dir |

`role`, `playbook` and `self` are sources that are not relations. That is the widening: "where
this render's data comes from" was only ever answerable as "which other items relate to this
one", which is why everything that was not a relation went bespoke.

## Adopter surface

Declaring a view without touching Python, three steps:

1. `.overrides/workflow.toml` — `[views.my_view]` with one line, its `source`.
2. `<squad>/.overrides/templates/views/my_view.md.j2`. Verified: `_rendering/_engine.py:66`
   puts a `FileSystemLoader` over `<squad_dir>/.overrides/templates` ahead of the
   `PackageLoader` in a `ChoiceLoader`, so any path shadows by name — including a name with no
   bundled counterpart.
3. Place the tag `sq:view:my_view` in a body, by hand via `sq <type> <n> body`, or seeded into
   every new item of a type by overriding `templates/items/<type>.md.j2` in the same tree.

Step 3 is a capability the shipped design does not have. Today an adopter attaches a view to a
*type* and the CLI chooses the position. Here the adopter chooses the document and the
position. It also costs one fewer concept: no `fields` / `group_by` / `order_by` grammar, no
`items.<type>.views` attachment, and no `[selected]` pruning interaction to understand.

## Problems in this model, named

Four, in descending order of how much they cost.

**1. Retroactivity, and a migration that writes into authored prose.** Covered above. A new
bundled view can no longer light up on existing documents without inserting a tag into
`:body`. This is the one place the change touches agent-authored content, and it deserves the
tightest possible containment.

**2. A tag is deletable.** `sq <type> <n> body -m "…"` replaces the whole body region and
silently drops any tag in it. A type-attached view cannot be lost that way. This is the real
cost of "a place in the document" and it has no free fix. Smallest change that keeps the
shape: `sq check` warns when an item whose creation template seeds a tag no longer carries it.
Advisory, cheap, stores nothing.

**3. Jinja becomes the query language.** `groupby` / `sort` / `selectattr` under
`StrictUndefined` is adequate for the roll-up — grouping on one attribute, ordering on two.
It is not adequate for an arbitrary join, and the first time someone wants one the pressure
will be to reintroduce a `fields`-shaped layer. The guard is to keep the source dispatch the
only place a join can be added, so a new join arrives as a new `source.kind` — declared,
validated, and named — rather than as logic accreting inside templates.

**4. Recursion.** A view template rendering a document that contains a tag. Refuse it: tags
expand in item bodies only, never in view output. Depth one.

## Integration seam

Tag expansion belongs at the body-read boundary, below the CLI, so `--raw`, the TUI and the
CLI all inherit it from one place rather than each growing its own expander. That placement
constraint is the requirement; which module holds it is an implementation choice.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-02T12:23:27Z] Robert Architect:
  - Scoped @op-pierre's model: view = source + template, tag marks the place, projection deleted. Left un-ruled deliberately — this prices the change, it does not rule it.
  - Two empirical checks that decide it: nothing in clients/vscode/src touches view JSON (no hits for workflow view / milestone_rollup / projection / groups — it reads sq tree --json and show --raw), so the projection has had zero clients for a release; and role_definition_text already IS source+template with one context var, with the role item's sq:body deliberately emptied at create — the codebase drifted to this model three times bespoke because the declared mechanism only spoke relations.
  - Sharpest cost to weigh before ruling: type-attachment is retroactive, a tag is not, so existing milestone files need a migration that inserts into the authored :body region — the first write of its kind. Second: a body -m replaces the region and silently drops the tag.
  - Not the region we just stripped: the tag is unpaired by design (no close_marker counterpart), so there is no span to materialize into. @product-owner @tech-lead for the shape before any breakdown.
<!-- sq:discussion:end -->
