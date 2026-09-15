---
id: ADR-880
sequence_id: 880
type: decision
title: Views as a source plus a template rendered at a document tag
status: Accepted
author: architect
description: Retire the projection layer; keep and widen sources; a content-free tag
  marks where a view renders on read
created_at: '2026-09-02T12:23:01Z'
updated_at: '2026-09-04T12:59:28Z'
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

## The ruling — 2026-09-03

op-pierre ruled the model this record prices: **build it**, and it is the main line of work for
0.15. The sections above stand as written — the pricing and the evidence are the reasoning
behind this ruling, not a menu of options. What follows is the decision.

### The decision

A view is a **source plus a template**, and a **tag in a document is the place it renders**.

- The source layer stays, grows the non-relation kinds, and is the only place a join may live.
  `resolve_records` becomes `resolve_source`: a dispatch on `source.kind` over resolvers, with
  ref inversion, the subtree walk and the sub-entity collection read surviving verbatim.
- The projection middle layer is **deleted** — `_RawRecord`, `Cell`, `ViewFieldMeta`,
  `ViewRecord`, `ViewGroup`, `Projection`, `project`, `_cell`, `_badge_cell`, `_sort_key`,
  `_BASE_RESOLVERS`, `projection_json` — together with the declaration grammar (`fields`,
  `group_by`, `order_by`), the validators that existed only to prove that grammar resolved
  (`_check_view_fields`, `_check_item_views`, `VIEW_BASE_FIELDS_BY_SOURCE`), and the type
  attachment (`ItemSpec.views`, and `_prune_orphaned_type_owned_views` with it).
- A `[views.<name>]` entry declares its `source` and nothing else. Presentation resolves by the
  view's own name at `templates/views/<name>.md.j2`, which is already how it resolves today.
- A template receives the source's own shape, unflattened, plus the host item and the active
  spec. `_badges.py` survives whole and must be reachable as a registered filter; the
  settled-versus-delivered distinction is real logic and moves onto `WorkflowSpec` beside
  `first_settled_status` rather than dying with the column it was expressed as.
- The source grammar **widens past relations**: `role`, `playbook` and `self` join `ref`,
  `subtree` and `subentity`. The three read-time render paths that were reinvented bespoke —
  role definition text, system skill text, per-item-type skill text — collapse onto the
  declared mechanism. That collapse is the widening's first payment, not a later possibility
  it leaves open.
- `--json` is per-source, in the shape each source already serialises. `--json` answers about
  the data, `--raw` about the text; there is no third envelope, and no client is on the other
  end of the one being removed.

### The four problems, ruled

**1. The retroactivity migration writes into the authored `:body` region — permitted, once,
under a closed set of conditions.** Type attachment applied retroactively and a tag does not,
so existing milestone bodies carry nothing and the roll-up would quietly stop working for every
milestone already on disk. Doing nothing is therefore not available; neither is keeping a
type-attachment fallback, since that coupling is what is being removed. Ruled: the migration
runs, and its licence is exhausted by these conditions —

- it **inserts** only, and never rewrites, reorders or removes authored text;
- it inserts at one deterministic anchor, the end of the `:body` region;
- it is idempotent, and skips any body already carrying the tag;
- it touches only items of a type whose creation template seeds that tag;
- it reports how many bodies it changed, so the write is visible in the run and in the diff;
- an author who later moves the tag keeps their placement, and an author who removes it keeps
  it removed (problem 2).

`templates/items/<type>.md.j2` seeds the tag at creation, so no future item needs a migration
at all. This is the only write squads makes into an authored region and it is **not a
precedent**: a later bundled view does not light up on existing documents by migrating their
prose. It lights up where an author or an operator places its tag.

**2. A body write dropping the tag is accepted as an unfixed cost — the tag is authored content
and stays that way.** Refused: preserving a tag across a `body` replace, re-inserting it
silently, or refusing the write. Each of those makes the tag tool-maintained bytes inside an
authored region, which is the stored-region failure returning through a side door — the tool
would own content in a file it does not otherwise own, and an author's deliberate deletion
would be undone by the next write. Ruled instead that the loss is *visible* rather than silent:
`sq check` carries a warn-level advisory when an item whose creation template seeds a tag no
longer carries it, storing nothing. Under ADR-864's tiering that advisory is catalog-only, not
floor — an author who does not want a view on one document is in a state a competent squad can
sit in indefinitely and on purpose. This project selects it in its own spec.

**3. Jinja as the query language is accepted, and its guard is binding rather than advisory.** A
join may be added only as a new `source.kind` — declared in the spec, validated at load, named.
No `fields`-shaped declaration layer may return to `[views.*]`, and query logic may not accrete
inside a template. The sanctioned extension point is a filter registered in
`_rendering/_engine.py`: a pure function of the spec or the playbook, exposed to templates, not
reimplemented in Jinja. A view that cannot be expressed as one source plus Jinja's own
`groupby` / `sort` / `selectattr` over that source's records is a **missing source kind**, and
is to be proposed as one.

**4. Recursion is refused at the mechanism, not by a depth counter.** Tags expand in item bodies
only, at the single body-read boundary below the CLI. View output is not scanned for tags, so a
tag appearing in a view's rendered text stays literal text. There is no depth limit and no cycle
detection because there is no second expansion site to recurse through — and any change that
adds one is the change that has to bring them.

### The binding invariant

The view tag is declared **unpaired**: a marker with no `close_marker` counterpart, and
therefore no span. This is the property that separates a tag from the stored regions this
corpus was stripped of, and it constrains future change, not merely this build.

- `_models/_markers.py` must not gain a closing counterpart for a view tag, and no verb may
  write content adjacent to one. Materialisation needs a span to write into; there is none, so
  the stale-content failure is unreachable by construction rather than avoided by discipline.
- A view tag's bytes carry the view's *name* and nothing else. There is no state in which the
  file's content disagrees with the computed truth, because the file holds no computed content:
  a name has no freshness dimension to lose.
- Because of that, a dangling tag is detectable where stale rendered content never was. A
  `sq:view:<name>` tag naming a view the active spec does not declare, or whose template is
  missing, is an **error**-level finding — floor, unlike problem 2's advisory, because no squad
  can sit in that state on purpose.
- The repair sweep that strips retired regions distinguishes by marker **shape** — an unpaired
  `sq:view:` tag inside `:body` is authored content — never by a name list that a later view
  would fall off.

Any proposal to give the view tag a body, a paired form, or a cached rendering *is* the proposal
to rebuild the stored region, and is to be read and answered as exactly that.

## Amendment — 2026-09-03: the tag stays inside the `sq:body` region

op-pierre asked what happens if the view tag lives *outside* the `sq:body` region, where a body
replace cannot reach it. The question is a good one and it is answered against the mechanism
rather than against the ruling above: two of its premises hold, the placement change it proposes
does not, and it surfaced two defects in the ruling that are fixed here.

Everything driven below was driven in a throwaway squad outside this repository, removed
afterwards, each probe with a control.

### What the question gets right

- **Every edit verb is section-scoped.** `get_section`, `replace_section`, `append_to_section`,
  `remove_section` and `region_lines` all address a marker pair, and `replace_frontmatter`
  preserves the body verbatim. Nothing writes outside a region. Driven, further: an
  outside-region tag survives `sq repair` and survives `sq retype` across types.
- **There is precedent for tool-written text outside every region** — the `## Discussion`
  heading at `templates/items/milestone.md.j2:13`, written once at creation and never revisited.
- **Problem 2 really would dissolve there**, and problem 1 really would stop being a write into
  authored prose.

### Why the tag does not move (question 1, question 3)

**Text outside every region is invisible to every read surface.** Driven: `sq <type> <n> show
--raw` on a file whose bytes carry both an outside-region tag and the on-disk `## Discussion`
heading printed neither — the panes are composed from region *contents* (`read_body` is
`get_section(text, sq:body)`, the single body-read boundary), not from the file's document order.
So the `## Discussion` precedent is precedent for text that is **never read**, which is the
opposite of what a tag needs; it exists for someone opening the raw file, which this project's
own rule tells agents not to do.

That is what decides the placement, and it decides question 3 with it. Of the three homes:

- **Unmarked text outside the regions** — the shape the question proposes — is not reachable by
  any read path. To render it, the expansion seam stops being "a region's content" and becomes
  "the file's raw text", and the tag's position in unmarked territory becomes load-bearing while
  no verb can see or maintain it.
- **Its own marked region** is where that pressure actually lands, because a region is the only
  thing the read path reads. And a tool-owned region sitting between the body and the discussion
  is byte-for-byte the shape of `sq:summary` — the region this corpus was stripped of. So the
  answer to the sharper half of question 1 is **yes**: outside the body there is a *new*
  materialisation pressure, a tool-owned slot is exactly where a cache gets argued for, and the
  option's own gravity pulls it into the failure the invariant exists to make unreachable. The
  unpaired invariant would survive out there only for as long as the tag stayed unread. That
  makes outside-the-body **worse**, despite the two problems it genuinely solves.
- **Frontmatter** is refused for a different reason: a `views:` list carries no position, so it
  is `ItemSpec.views` relocated from the type onto every instance — strictly more storage than
  type attachment, with strictly less expressiveness, and for every item created from its type's
  template it is derivable from that template. That is the standing rule against storing what
  can be derived, applied to the exact shape being removed.

**Ruled: the tag lives inside the `sq:body` region, as unpaired content of that region.** Not in
its own region, not in frontmatter, not in unmarked territory.

### Is per-document placement load-bearing (question 2)

Only for the roll-up, and for any future view someone wants mid-prose. The role and system-skill
cases have deliberately-empty bodies (`_services/_base.py:931` empties a role's region at
creation, for the reason written out in place), so *where* in the region the tag sits carries
nothing there.

But that is not the question the amendment turns on. **Inside-the-region placement is
load-bearing for every source kind**, including `role`, `playbook` and `self`, because the region
is the only thing any read surface reads: a role's emptied body region is precisely the slot the
resolved definition renders into, and a tag outside it would leave that region empty and the
definition rendered from a place nothing reads. The amendment would therefore need two homes for
one grammar — the tag outside the body for the roll-up, inside it for the definitions — which is
a worse outcome than either home alone.

### What `sq check` and the repair sweep actually do (question 4)

The dangling-name finding is unaffected by position, and it is not free today.

**Driven, in both positions: an unpaired tag is already reported as an error.**
`_services/_maintenance.py:455` counts every well-formed tag in a file and reports an
`unclosed marker` error naming the tag `sq:view:milestone_rollup` (spelled bare here, as
elsewhere in this record, since a body may not carry a well-formed marker), whether it sits
inside `sq:body`
or outside every region; the same file with the tag removed checks clean. So the unpaired shape
collides head-on with the existing balance arithmetic, and the ruling above did not say so.

Ruled: the balance check learns the declared **unpaired family by shape** — a `sq:view:<name>`
tag is exempt from the pairing arithmetic — and name resolution is what replaces pairing for that
family: a tag naming a view the active spec does not declare, or whose template is missing, is
the error instead. One family, one rule each, no name lists.

The repair sweep needs no change and its shape-not-name discrimination holds as stated:
`_retired_region_tags` (`_services/_maintenance.py:231`) admits only the fixed `sq:summary` tag
and tags ending in `:head`, and additionally skips any tag whose region is not balanced in the
file — so a view tag is excluded twice over, by name shape and by having no region at all.

### Two corrections to the ruling above

**1. The tag never arrives through the prose door, and the adopter surface is wrong as written.**
Driven, with a control: a `sq milestone <n> body -m …` whose text carries the tag in its real
HTML-comment form is **refused** — `reject_markers` rejects any well-formed tag in any prose input
— while the same
text without its comment wrapper is accepted. So "place the tag in a body by hand via `sq <type>
<n> body`" does not work, and making it work means punching a per-name hole in the one guard whose
entire argument is that a corpus is clean because marker-shaped text is refused at the door.

Ruled: **no hole.** Placement is its own marker-safe verb on the item — insert and remove a view
tag within the `sq:body` region — and `reject_markers` stays fully closed for prose. A tag is an
instruction, not prose, so it does not enter through the prose door. The adopter surface's third
step is that verb, or seeding the tag in a type's creation template, and nothing else.

That verb also settles problem 1's remaining discomfort: the migration inserts through the same
path an operator uses, so it is the tool's own placement applied in bulk rather than a bespoke
one-off write into authored prose. The licence and the fence on it stand exactly as ruled.

**2. Problem 2 stands, and its advisory needs one condition it did not have.** Preserving a tag
across a body replace was refused above; the sharper reason is that preservation cannot preserve
*position* — a replace supplies the whole region — so it would convert a visible loss into a
silent relocation to the region's end. The advisory is the honest surface.

Its condition is keyed on **the item's type's creation template as that template currently
stands**, never on how the tag arrived. That closes the gap a migrated item would otherwise fall
into: the migration touches exactly the types whose template seeds the tag, so the same condition
covers migrated and freshly-created items alike — and it is the only implementable condition,
because nothing records a tag's provenance. A hand-placed tag on a type whose template does not
seed it is the author's own; it gets no advisory, and losing it is an ordinary body edit.

### One consequence to name, in either placement

Driven: `sq retype` preserves the whole body verbatim, so a tag rides along to the new type — a
milestone retyped to an epic keeps its roll-up tag, and the dangling-name check does not fire,
because a view is no longer type-scoped and the name still resolves. Accepted rather than fixed:
the tag is a property of the document, and retype preserves the document. It is recorded here so
it is met as a decision rather than found as a bug.

## Second amendment — 2026-09-03: source applicability is placement state, and the failure-mode split was incomplete

REV-912's F1 raised a third read-time failure mode that neither half of the split above accounts
for, and the split's own wording claimed to be complete. This section corrects it. The ruling, the
pricing and the first amendment are untouched.

Two sentences of that amendment are wrong as written. The first, from its question-4 ruling:

> Ruled: the balance check learns the declared **unpaired family by shape** — a `sq:view:<name>`
> tag is exempt from the pairing arithmetic — and name resolution is what replaces pairing for that
> family: a tag naming a view the active spec does not declare, or whose template is missing, is
> the error instead. One family, one rule each, no name lists.

"One family, one rule each" asserted that name resolution is the *whole* precondition for expanding
a tag. It is not. Name resolution answers whether the view exists; it does not answer whether that
view's declared source can resolve against **this** host. The second, from the consequence named at
the end of the same amendment:

> the dangling-name check does not fire, because a view is no longer type-scoped and the name still
> resolves.

A view's *name* is not type-scoped. A `subentity` source's *applicability* is. That distinction was
collapsed, and TASK-911's US8 acceptance inherited the collapsed form.

### 1. What is actually true (read)

`expand_view_tags` gates on `view_target_exists` alone (`_views.py:501` — declared in `spec.views`
and the presentation template resolves, `_views.py:417-429`) and then calls `resolve_records`
(`_views.py:214-224`), which dispatches on the declared `source.kind`. Of the three shipped
resolvers, two impose nothing on the host — `_resolve_ref_source` (`_views.py:155-176`) only inverts
forward edges, `_resolve_subtree_source` (`_views.py:195-211`) only walks descendants — and one
does: `_resolve_subentity_source` (`_views.py:141-152`) raises `SquadsError` when
`spec.item_subentity_kind(item.type)` is not the projected kind.

So a tag naming a declared, templated view whose source cannot apply to its host passes the gate,
reaches the resolver, and raises out of the single body-read boundary. Every read surface that
boundary feeds fails with it, while the placement verb accepted the tag (`_services/_views.py:21-48`
asks `view_target_exists` and nothing else) and the file scan reports nothing (the finding at
`_services/_maintenance.py:487-513` asks the same predicate expansion gates on, and it is satisfied).
Not reachable on the bundled spec: the one bundled view is `ref`-sourced
(`_specs/workflow.toml:632`). Reachable for any adopter declaring a `subentity`-source view, and
FEAT-903 widens the grammar with `role`, `playbook` and `self` — two of which carry host
constraints of their own, which is why the classification is settled here rather than per resolver
as each lands.

The decisive fact for everything below, and the reason this is cheap: **a source's applicability is
a function of the view, the active spec, and the host item's *type* — never of the host item's
content.** `item_subentity_kind` (`_workflow/_models.py:2125-2133`) takes a type string and returns
the kind or `None`. Nothing needs a resolved `Item` to answer it.

### 2. Ruled: source applicability is a precondition, not a defect

A source that cannot resolve against its host is **placement state**. It joins the quiet half: the
tag is left exactly as authored, the read succeeds, and the file scan reports it. It is not an
engine defect, and a resolver is not the place it gets discovered.

The reasoning is the reasoning the first amendment already used for the dangling name, applied one
step further. Both conditions are mismatches between a corpus artifact — a tag placed on a document
of a given type — and the declared spec. Neither is a fault in engine code or in a template. Both
are decidable before anything is read or rendered. Treating one as reportable state and the other as
a crash split an identical class down the middle, and put the louder half on the side where a
correct-looking corpus becomes unreadable with every gate clean.

**The classification test, which is what a future resolver is judged by.** For a source kind, list
every condition under which its resolver cannot produce a well-formed result, and ask of each:

> Is this condition decidable from the declared spec plus the host item's **type** alone, before any
> record is read and before any template is rendered?

- **Decidable → it is a precondition of that kind.** It belongs in the kind's declared applicability
  predicate, and it is placement state: placement refuses it, expansion leaves the tag literal, the
  read succeeds, the file scan reports it as an error.
- **Not decidable → it is a defect**, discoverable only by executing the resolver or the template.
  It raises as `SquadsError` naming the item and the view.

Three clauses make the test binding rather than a description of today's code:

- **A resolver may not raise for a condition its kind's predicate could have decided.** Every raise
  left inside a resolver is, after this ruling, a defect signal. A kind arrives with its predicate
  declared beside its resolver; a kind with no host constraint declares the predicate constantly
  true, explicitly, rather than by saying nothing.
- **A predicate may not read the host item's content** — not its refs, not its sub-entities, not its
  status. It is a question about a *type*, which is what keeps it answerable by all three consumers
  (§4) and keeps it out of the per-item catalog.
- **Emptiness is never a failure.** A precondition covers only conditions under which the resolver
  cannot produce a well-formed result at all, never conditions under which it produces an empty one.
  A milestone with no members renders an empty roll-up; a `subtree` source over a type this host
  will never in practice parent yields zero rows and that is the correct answer. Without this clause
  the predicate grows into a reachability analysis over the parent graph, which is a second query
  layer arriving through the back door — the thing problem 3's guard exists to refuse.

**One predicate, asked once, three consumers.** `view_target_exists`'s two questions become three,
in one helper beside it in `_views.py`, resolving each kind's constraint off `WorkflowSpec` methods:
declared, template resolves, source applies to this type. It answers with the reason it refused, not
a bare boolean, so the placement refusal and the scan finding name the same cause composed in one
place rather than each writing its own sentence. That preserves the property the first amendment
asked for — the placement verb and the file scan ask the same question through the same helper,
never a second implementation of it.

### 3. Ruled: placement refuses at the door, and the door is not the guarantee

`view add` refuses a source-incompatible host, through the widened predicate, exactly as it already
refuses a dangling name. `view rm` stays ungated, as it already is and for the reason already
written into it: taking a tag off a document must keep working for a view the spec no longer
declares, and it is the recovery path for precisely this state.

Refusing at the door cannot be the whole answer, because the state is reachable without passing
through the door — three ways, all of them legitimate:

- `retype` carries the tag to the new type. That is accepted above and stays accepted.
- A spec or override edit can change what a type hosts, or drop a hosting type, under a tag that was
  valid when placed.
- A creation template seeds the tag for a type, and a later override edit changes that type.

**Ruled, for a tag that was valid when placed and is not any more: nothing is rewritten.** The tag
is not stripped, not relocated, not silently repaired, and `retype` gains no refusal. The document
keeps what its author placed; the read keeps working because the tag stays literal; the file scan
reports the state with its remedy nameable. This is the same disposition problem 2 already has for
a lost tag — the loss is made *visible*, never undone — and it is the same refusal of provenance:
the finding is keyed on the state as it currently stands, never on how the tag arrived, because
nothing records a tag's provenance and a rule that varied by arrival path would be unimplementable
as well as wrong.

So `retype`'s behaviour is unchanged and its *outcome* is what changes: the same retype that today
produces a clean check and an unreadable item produces, after this, a readable item and a reported
finding. TASK-911's US8 keeps its ruling — the tag is a property of the document and retype
preserves the document — and loses the sentence quoted above.

### 4. Ruled: an error, unconditional, beside the dangling-name finding

The finding is **error-level**, produced unconditionally, in the always-on file-level marker scan at
`_services/_maintenance.py:2984-2986` — the same place, in the same helper, as the dangling name.
Not a validator-catalog member.

REV-912 ruled the dangling-name finding correctly placed there on two properties, and this finding
has both:

- **It runs before a file becomes an item.** The scan loop binds the host type at
  `_services/_maintenance.py:2963` from `_iter_item_files` (`:1478-1507`), which derives it from the
  type folder it globbed and the `PREFIX-*.md` filename it matched, and `read_frontmatter` does not
  run until `:2988`. Because §2's predicate is type-scoped and never instance-scoped, the type is
  already in hand: **this finding needs no resolved `Item`**, and it keeps firing on a file too
  broken to parse — which is exactly where a finding about an unreadable document earns its keep.
  Requiring an `Item` would have made catalog membership the natural home and lost the case.
- **It must not be selectable.** Under ADR-864's tiering test — is this a defect in *any* squad, or
  only in *some* — a document carrying a tag that cannot render is a defect in any squad: it reads
  as nothing at best, and today as an error. REV-912 also makes a precision worth carrying: "floor"
  in the catalog's own vocabulary means `COMMON_CORE` membership, which is still a selectable-shaped,
  item-scoped mechanism, so reading the invariant's word "floor" as "must be a catalog member" would
  weaken the guarantee rather than honour it. What is owed is unconditional-by-construction, which
  is what the file-level scan gives.

One helper, two reasons, one message each — not a sibling function. The predicate of §2 answers
both, so the existing finding generalises and its name stops being accurate: "dangling" describes
one of the two reasons it now reports.

### 5. What is left inside the loud half

The "engine defect propagates as `SquadsError`" clause survives, and its label was wrong. What is
left inside it, once applicability moves out, is **a render-time failure with the precondition
satisfied**: a declared view, a resolvable template, a source that applies to this host, and the
render or resolve still fails. Three things live there —

- a template raising under `StrictUndefined`, or any other `TemplateError`, whether the template is
  bundled or an adopter's own override;
- a resolver failing for anything its kind's predicate could not have decided, which after §2's
  first clause means a bug;
- the narrow race the translation helper already documents, where a template resolves at the gate
  and is gone at the render.

"Engine defect" mis-described the first of those, and the mis-description is load-bearing: an
adopter's broken override template is not our bug, and a reader who took the label literally would
be pushed toward making it quiet on the grounds that it is not an engine fault. It stays loud, for a
reason that is consistent with the rest of squads rather than special to views: **a fault in the
corpus never breaks a read; a fault in the spec or override tree already fails loud everywhere** — a
malformed overrides file stops every command, not one document's body. A template fault failing loud
on the documents that placed that view is strictly narrower than the precedent it sits under. And
degrading it to literal text would hide a broken template behind a tag its author placed
deliberately, with nothing anywhere saying why the view stopped appearing.

Two boundaries on the clause, so it is not read wider than it is:

- **The explicit resolve path keeps raising, unconditionally.** `sq workflow view <name> <id>` names
  a view and an item directly; an inapplicable pair is a bad argument pair and an error is the answer
  to a direct question, not a broken read of a document. Only *tag expansion at the body-read
  boundary* is subject to §2's quiet half. A reader who moves the quiet half into `resolve_view`
  has broken the command.
- **Quiet never means empty.** A tag whose precondition fails is left as the tag, byte for byte. It
  is not replaced with an empty rendering, a placeholder, or a comment. The bytes on disk and the
  bytes read back are the same, which is the property the unpaired invariant exists to protect.

### 6. What this obliges

- FEAT-903's three kinds each declare their applicability predicate as part of landing, not after.
  Read against §2's test as the grammar stands in the ruling above: `role` resolves the host's own
  role definition, so its precondition is that the host's type is the declared role type — type-
  decidable. `playbook` resolves a type's lane, named or the host's own, so its precondition is that
  the resolved type is declared and carries a lane — type-decidable. `self` constrains nothing and
  declares its predicate constantly true. None of the three needs the host's content, so the
  file-scan placement of §4 holds for all of them.
- The two sentences quoted at the top are corrected here rather than tidied away: this record's
  first amendment claimed a complete rule set for the unpaired family and did not have one, and
  generalised "not type-scoped" from a name to a view.
- The regression shape that was missing is a `subentity`-source view on a non-hosting host, driven
  through both doors — placement and retype — with an assertion that the body still **reads**. A
  retype test that asserts only a clean check and the tag's surviving bytes cannot see this class of
  failure at all, which is how it reached review.

### On REV-912's evidence

F1's mechanism is confirmed **read**, at every link: the gate, the dispatch, the raise, the two
resolvers that impose nothing, the placement verb's single question, the scan's satisfied predicate,
and the bundled spec's `ref` source that keeps it off this repository. I did not re-drive the two CLI
transcripts, and did not need to — the ruling turns on the classification, which the source settles.
Two small corrections to the citations, neither affecting the finding: the gate is at `_views.py:501`
inside `expand_view_tags`, whose definition is at `:462`; and the raise F1 attributes to `:146` is at
`:147-152` inside `_resolve_subentity_source`, defined at `:141`.

One claim in F1 I read as narrower than stated. It says the state is created "while `sq check`
reports nothing" — true of this finding and of the corpus, but a squad in this state is not
otherwise clean by construction: nothing about it suppresses any other finding. The gap is that the
one surface that should have reported it cannot, which is what §4 fixes; it is not a blind spot
across the check surface.

## Third amendment — 2026-09-04: the per-item-type skill collapses on a corrected `playbook` subject, not a seventh kind

FEAT-906's breakdown found that the third of the three bespoke read-time render paths does not
fit the source grammar **as this record tables it**. Ruled: it does collapse, the three-for-three
claim survives, and no new `source.kind` is added — what was under-specified is one clause of the
`playbook` row, corrected in §5. The ruling, the pricing and both earlier amendments are otherwise
untouched.

Every claim below is labelled **read** (traced in source), **driven** (executed) or **inferred**.
Nothing here was driven: this ruling turns on the classification and on what the source already
says, and no probe was needed to settle either. Where a hazard is read rather than demonstrated,
it says so.

### 1. Why the row cannot express it (read)

> | `playbook` | `[items]`, or the host's own type | the type's playbook lane, the live roster, the spec |

Both answers that row offers are the wrong type for this case:

- A per-item-type skill item is **always** of the roster `skill` type (`ROSTER_SKILL`,
  `_workflow/_models.py:41`) — never of the type it documents. `_resolve_playbook_source`
  (`_views.py:251-269`) resolves `view.source.name or item.type`, so `name` unset on a skill host
  yields `skill`, which carries no lane. That is not an accident to be repaired: it is precisely
  what `[views.squads_skill]` relies on, deliberately and in writing
  (`_specs/workflow.toml:686-692`).
- `name` set is a **static, spec-declared literal**, and a per-type skill's described type is not
  static: `_write_item_skills` (`_backends/_claude_code/_backend.py:238-281`) derives one
  `sq-<type>` skill per declared non-roster type, built-in and project-declared alike, with no
  per-type TOML anywhere in the path.

The bespoke path derives the type a **third** way, which is the one the grammar was missing:
`_item_skill_definition_text` (`_services/_base.py:1350-1386`) inverts `item_skill_name(t)` over
the active spec's declared non-roster types, and returns `""` when nothing matches.

### 2. Ruled: a `playbook` source's subject is the type its host **speaks for**

The corrected row, and the whole of the grammar change:

> | `playbook` | `[items]`, or — `name` unset — the type the host *speaks for*: its own type for an ordinary item, the item type it documents for a per-item-type skill item | the type's playbook lane, the live roster, the spec |

A seventh `source.kind` is **refused**, and the test that refuses it is this record's own definition
of `kind`: "`kind` stops meaning 'which relation' and starts meaning 'which resolver', which is what
it already meant mechanically." So the question is not *is this a new case* but **does this case need
a different resolver**. It does not. Its resolved value is `PlaybookSource`; its applicability is
`playbook`'s; its `--json` is `_playbook_json_payload` (`_cli/_workflow_cmd.py:805-843`); its
template contract is `render_source_view`'s `source`/`item`/`spec`/`squad_dir`
(`_views.py:806-834`). Every column of the row is a copy but the subject derivation. A kind that
duplicates another kind's row in order to change its default is not a source — it is the same source
with a corrected default, and shipping it as a kind buys two resolvers, two predicates and two
payload arms to hold in agreement forever, which is the class of cost this record has spent two
amendments avoiding.

**Priced against problem 3's guard, which is binding here and does not decide it.** The guard fences
*joins* into new declared kinds and forbids query logic accreting in templates. This adds no join:
it is the same single lane lookup, keyed on the host's identity instead of the host's type, and it
stays inside the source layer — where the guard wanted it. The guard is satisfied by both shapes, so
the definition of `kind` is what separates them. No `fields`-shaped declaration returns to
`[views.*]`; the declaration this needs is byte-for-byte the shape `squads_skill` already ships.

**This is a shape the grammar already contains, not a new one (read).** The `role` kind already
derives its subject from the host item's own **identity** rather than from `source.name` or
`item.type`: `_resolve_role_source` delegates to `resolve_role_for_item`, which resolves
`item.extra.get(X.SLUG, item.slug)` (`_roles/_resolver.py:496`), with `item.type` serving only as
the precondition. The per-item-type skill is the second instance of that shape, and
`_role_source_applies`'s own docstring already draws the line it needs — the host's *type* is a
precondition; whether *this host's identity* resolves against anything is not, and is degraded
rather than raised.

Four binding constraints on the derivation:

- **It is gated on the host being the declared roster skill type**; every other host keeps
  `item.type` verbatim. The gate is load-bearing, not tidiness: `Item.slug` is the filename slug
  segment for *every* item (`_models/_item.py:147`, `:602-619`), so an ordinary work item whose
  title slugifies to `sq-<some declared type>` would otherwise resolve a different type's lane.
  Read, not driven — a hazard the gate closes by construction rather than a demonstrated defect.
- **It resolves against the active spec, through the existing slug family** —
  `item_skill_name`/`active_skill_slugs`/`orphaned_skill_item_type` (`_interactions/__init__.py:301`,
  `:542`, `:588`) — rather than re-inverting the slug a second time beside them. Two implementations
  of "which type does this skill document" is exactly the agreement-pinning debt TASK-918 was held
  to on the rich/thin question. That family's answer for the three permanently-system slugs, and for
  an author's own `sq-`-prefixed skill, is *no documented type*, which is what keeps `squads_skill`
  unchanged and keeps an authored skill out of this path.
- **A skill host whose slug names no declared type is the emptiness case**, ruled by the second
  amendment §2, not a precondition: it renders nothing and raises nothing, preserving today's `""`
  (`_services/_base.py:1370-1371`). It is not decidable from the host's *type*, so it may not become
  a predicate — the same clause `_role_source_applies` already records for an orphaned role item.
- **The rich/thin split moves into the presentation template and lives nowhere else.**
  `PlaybookSource.lane is None` is the declared empty case; a declared type with no playbook coverage
  must still get the thin rendering (the standard command list plus the auto-derived lifecycle),
  because that is the *ordinary* case for a project-declared type, not an edge.

### 3. Ruled: one view name for every per-item-type skill, bundled and project-declared alike

One declaration, `[views.item_skill]` with `source = { kind = "playbook" }` and `name` unset; one
presentation template at `templates/views/item_skill.md.j2`; one tag name, `sq:view:item_skill`
(spelled bare here, as elsewhere in this record, since a body may not carry a well-formed marker),
seeded into every per-item-type skill body by the same writer that seeds the other three.

**Refused: one synthesized view per declared type**, at load time or otherwise. Three reasons, in
ascending order of weight:

- It *declares* what is derivable — N entries recoverable from `[items]` — which is the standing rule
  the first amendment already applied to a per-item `views:` list.
- Presentation resolves by the view's own name (`view_template_name`, `_views.py:718`). N names need
  either N templates or a template-name indirection, and the indirection is a new key in `[views.*]`.
- **Decisive:** a view name that embeds a type name puts a type's name into **corpus bytes**. A
  rename, or a `[selected]` drop, then dangles that tag on every skill body carrying it — and a
  dangling name is an error-level finding under this record's binding invariant. An adopter's
  ordinary customisation would produce corpus-wide errors from a declaration they never wrote, which
  is the exact coupling removing `ItemSpec.views` and `_prune_orphaned_type_owned_views` was for. One
  shared name never dangles: the type goes away, the render goes empty, the scan stays clean.

**The adopter case, ruled explicitly, because it is the axis this turns on (read at every link).** A
project that declares its own type `widget` gets `sq-widget` from the same writer as `sq-task`
(`_write_item_skills` loops the spec's declared non-roster types; there is no built-in/custom split
at the slug layer — `active_skill_slugs`' own docstring says so), seeded with the same tag name,
resolving `widget` from the live `spec.items` at read time, rendered by the same bundled template,
thin because `widget` has no playbook lane. There is no per-type TOML for a bundled type either, so
there is nothing a project-declared type is missing and no per-type entry for anyone to author. A
type that is dropped or renamed has its skill withdrawn by the mechanism that already does that
(`is_live_roster_entry`/`orphaned_skill_item_type`), and a stale skill item left on disk renders
empty rather than raising, per §2's third constraint.

### 4. What this shape does not buy, accepted

`playbook`'s applicability predicate is constantly true (`_playbook_source_applies`,
`_views.py:428-438`), so placement does not refuse an `item_skill` tag on a non-skill host: a task
carrying it renders that task's own lane through the skill template. A seventh kind would have
refused it at the door, and that refusal is the whole of what a seventh kind would have bought.

Accepted, on the line that keeps it distinct from `role`: `role`'s type precondition prevents a
**wrong answer** — a non-role item resolved as a role. This one would prevent only an **odd choice**
— a correctly resolved lane in a document nobody wants it in. Preconditions have *kind* granularity
by construction (the applicability registry is keyed on `source.kind`), so buying that refusal means
a per-*view* predicate axis, a declaration growth out of all proportion to an odd-but-correct
rendering an author placed deliberately. The same exposure already ships for all three
system-skill views, whose `playbook`/`self` predicates are constantly true too, and this record's
own adopter clause already puts the choice of document with the author.

### 5. Corrections in place

**1. The `playbook` row of the source grammar table under-specified its second answer.** Quoted and
corrected in §2. The row is not wrong about anything it says; it is short by one clause, and the
missing clause is what the third render path needs.

**2. The ruling's collapse claim survives, and its evidence needed this clause to be true.** From
the ruling:

> The three read-time render paths that were reinvented bespoke — role definition text, system skill
> text, per-item-type skill text — collapse onto the declared mechanism.

Three for three, unchanged. But it was a claim about the *mechanism*, and the same record's own
grammar table could not express one of the three. That gap is closed here rather than argued away:
had it not closed, the honest outcome was two-for-three and a bespoke third path recorded as such,
never a bundled-types-only declaration standing in for a general one.

**3. The second amendment §6 states a `playbook` precondition that no longer exists, and this ruling
depends on the opposite.** Quoted:

> `playbook` resolves a type's lane, named or the host's own, so its precondition is that the
> resolved type is declared and carries a lane — type-decidable.

The "carries a lane" half is **withdrawn**: it contradicts the emptiness clause ruled three
paragraphs above it in the same amendment, which is binding. REV-920's F1 found the implementation
had satisfied the sentence rather than the clause, and the predicate is now constantly true. The
"declared" half survives but not as a predicate: it is enforced at **spec load**, where
`_check_views` resolves every view's source unconditionally and refuses a `name` that no `[items]`
entry declares. A name-less `playbook` source whose host type is undeclared resolves empty, which is
the emptiness clause's answer and not a gap.

### 6. What this obliges

- The subject derivation is a correction to `_resolve_playbook_source`'s implicit target, gated on
  the roster skill type and composed from the existing spec-pure slug family — not a change to
  `resolve_source`'s dispatch, not a new kind, and not a new key in a view declaration. That bounds
  the change to already-reviewed code to one clause of one resolver, and this is the sign-off for it.
- The four derivations `_item_skill_definition_text` passes as kwargs today are reachable from
  `PlaybookSource` + `spec` + the four filters the collapse registers, with the rich/thin test being
  `lane` presence. Nothing else about the presentation half changes.
- The equivalence owed on landing is per **type**, not per bundled type: the rendered text for every
  declared type's skill, and for a synthetic project-declared type, is what the collapse must leave
  unchanged — a bundled-only diff would prove the half of this the ruling above refuses.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-02T12:23:27Z] Robert Architect:
  - Scoped @op-pierre's model: view = source + template, tag marks the place, projection deleted. Left un-ruled deliberately — this prices the change, it does not rule it.
  - Two empirical checks that decide it: nothing in clients/vscode/src touches view JSON (no hits for workflow view / milestone_rollup / projection / groups — it reads sq tree --json and show --raw), so the projection has had zero clients for a release; and role_definition_text already IS source+template with one context var, with the role item's sq:body deliberately emptied at create — the codebase drifted to this model three times bespoke because the declared mechanism only spoke relations.
  - Sharpest cost to weigh before ruling: type-attachment is retroactive, a tag is not, so existing milestone files need a migration that inserts into the authored :body region — the first write of its kind. Second: a body -m replaces the region and silently drops the tag.
  - Not the region we just stripped: the tag is unpaired by design (no close_marker counterpart), so there is no span to materialize into. @product-owner @tech-lead for the shape before any breakdown.
- [2026-09-03T08:45:10Z] Pierre Chat:
  - Ruled: build it. The view system is useless right now, so this is the main focus of 0.15 -- source plus template, tag marks the place, projection deleted.
- [2026-09-03T08:50:43Z] Robert Architect:
  - Ruled per op-pierre (2026-09-03): build it, main line for 0.15. Added "The ruling" section; the pricing and evidence sections are untouched.
  - Decision: view = source + template, tag marks the place; the projection middle layer plus the fields/group_by/order_by grammar, its validators and ItemSpec.views all delete; source grammar widens past relations to role/playbook/self, which is what collapses the three bespoke read-time render paths.
  - The four problems are ruled, not restated. The retroactivity migration into the authored :body region is permitted once under a closed condition set (insert-only, one deterministic anchor at the region end, idempotent, skip a body already carrying the tag, report the count) and is explicitly not a precedent for a later view. A body write dropping the tag is accepted as an unfixed cost — refused: preserving, silently re-inserting, or refusing the write, since each makes the tag tool-maintained bytes in an authored region; the loss is made visible by a warn-level advisory that is catalog-only under ADR-864 tiering, selected by our own spec. Jinja-as-query is accepted with its guard binding: a join arrives only as a new source.kind. Recursion is refused at the mechanism — one expansion site, so no depth counter.
  - Binding constraint on any future change: the tag is unpaired, no close_marker counterpart, so no span exists to materialise into. A dangling tag name is an error-level floor finding; the repair sweep distinguishes by marker shape, never by a name list. Any proposal to give the tag a body or a paired form is the proposal to rebuild the stored region and is to be answered as that.
- [2026-09-03T09:08:20Z] Robert Architect:
  - Amendment appended, ruled against the placement change: the tag stays inside the sq:body region. @op-pierre @manager — the ruling and pricing sections are untouched.
  - Decisive fact, driven with controls in a throwaway squad (removed): text outside every region is invisible to every read surface. show --raw prints region contents only — a file carrying both an outside-region tag and the on-disk "## Discussion" heading showed neither. So the ## Discussion precedent is precedent for text that is never read. Unmarked-outside is unreachable by any read path, which pushes the tag into its own marked region — a tool-owned slot between body and discussion, byte-for-byte the sq:summary shape we just stripped, and exactly where a cache gets argued for. So yes to the sharper question: outside the body is WORSE, despite genuinely dissolving problem 2. Frontmatter refused separately: a views: list carries no position, so it is ItemSpec.views relocated onto every instance — more storage, less expressiveness, derivable from the type template.
  - Per-document placement is load-bearing only for the roll-up, but inside-the-region placement is load-bearing for every source kind: a role body is emptied at create (_services/_base.py:931) precisely to be the slot the definition renders into, so outside placement would need two homes for one grammar.
  - Two corrections the question earned, both driven. (a) reject_markers refuses a tag typed into a body (control: same text unwrapped is accepted), so the adopter step "place the tag by hand via sq body" does not work — ruled no hole in that guard; placement gets its own marker-safe verb, and the migration inserts through that same path rather than as a bespoke authored-prose write. (b) _services/_maintenance.py:455 already reports any unpaired tag as an error-level unclosed marker, in BOTH positions — so the balance arithmetic must learn the unpaired sq:view family by shape, with name resolution replacing pairing for it. The repair sweep needs no change (_maintenance.py:231 admits only sq:summary and *:head, and skips unbalanced tags).
  - Advisory gap closed: its condition is keyed on the type\s creation template as it currently stands, not on how the tag arrived — which covers migrated items (the migration touches exactly those types) and is the only implementable condition. Also named: sq retype carries the tag to the new type, accepted rather than fixed. @product-owner unblocked for the breakdown.
- [2026-09-03T11:54:44Z] Robert Architect:
  - Second amendment appended, ruling REV-912 F1 as a classification rather than a resolver patch. Ruling, pricing and first amendment untouched; @op-pierre @tech-lead @reviewer.
  - A source that cannot resolve against its host is placement state, not an engine defect: tag stays literal, read succeeds, sq check reports it. Test a future resolver is judged by — is the condition decidable from the spec plus the host item TYPE alone, before any record is read or template rendered? Decidable = precondition (quiet, reported); not decidable = defect (raises). Binding corollaries: a resolver may not raise for what its predicate could decide; a predicate may not read item content; emptiness is never a failure.
  - view add refuses an incompatible host through the same widened predicate, but the door is not the guarantee (retype, and any spec edit, reach the state without it). A tag valid when placed and no longer valid is not stripped, relocated or repaired — visible, never undone, keyed on current state and never on provenance. retype behaviour unchanged; its outcome becomes readable-and-reported.
  - Finding stays error-level and unconditional in the file-level scan beside the dangling name, and needs no resolved Item: the scan already binds the host type from the type folder before read_frontmatter, so it keeps firing on a file too broken to parse. The loud half survives relabelled as render-time failure with the precondition satisfied — template errors (bundled or adopter override), resolver bugs, the gate/render race — and the explicit sq workflow view path keeps raising.
  - F1 confirmed read at every link; two citation line numbers corrected in the section, neither affecting the finding, and I read its "check reports nothing" as narrower than stated. FEAT-903 obliged to declare each new kind predicate as part of landing.
- [2026-09-04T12:59:28Z] Robert Architect:
  - - Third amendment appended, ruling FEAT-906/TASK-923's open question. Ruling, pricing and both earlier amendments untouched; @op-pierre @tech-lead @manager.
    - It collapses — three for three survives. A `playbook` source's subject is the type its host **speaks for**: `name` unset resolves the host's own type for an ordinary item, and the item type it *documents* for a per-item-type skill item. No seventh `source.kind`: the case needs the same resolver (same `PlaybookSource`, same predicate, same `--json` payload, same template contract) with a corrected default, and `kind` means "which resolver" by this record's own words. Same shape `role` already ships — subject from the host's identity, `item.type` only as the precondition.
    - Refused: a synthesized view per declared type. Decisive reason beyond "don't declare what you can derive" — a view name embedding a type name puts that type's name in corpus bytes, so a rename or a `[selected]` drop dangles the tag on every skill body and turns ordinary customisation into corpus-wide error findings.
    - Adopter case ruled explicitly: one declaration `[views.item_skill]`, one template, one tag name; a project-declared `widget` gets `sq-widget` from the same writer, seeded with the same tag, resolving `widget` off the live `[items]`, thin because it has no lane. No per-type TOML for a bundled type either, so nothing a custom type is missing.
    - Accepted cost, named: `playbook`'s predicate is constantly true, so placement won't refuse the tag on a non-skill host. `role`'s precondition prevents a wrong answer; this one would prevent only an odd choice, and buying it costs a per-view predicate axis.
    - Corrected in place, quoted: the grammar table's `playbook` row was short by one clause; and the second amendment §6's "its precondition is that the resolved type is declared and carries a lane" is withdrawn on the "carries a lane" half — it contradicted the emptiness clause three paragraphs above it, REV-920 F1 settled it, and the "declared" half is enforced at spec load, not by a predicate.
<!-- sq:discussion:end -->
