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
updated_at: '2026-09-15T08:59:42Z'
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

## Fourth amendment — 2026-09-14: a view declaration carries `required`, and the third refusal falls

op-pierre ruled that a view declaration carries a **`required`** boolean; that a document of a
type carrying a required view MUST hold its tag; and that **skipping a required view is
forbidden, and `--force` does not override it**. That overturns the third of the three
mitigations this record's first amendment refused. The ruling, the pricing and all three earlier
amendments are otherwise untouched.

The ruling is not re-argued here. What follows is the part it leaves open: where `required`
lives, what its default is, which surfaces bind it, what an upgrading corpus sees, which `sq
check` tier reports it, and which bundled views take it.

Every claim below is labelled **read** (traced in source) or **inferred**. Nothing was driven:
the ruling turns on classification and on what the source already says.

### 0. The refusal that falls, and the two that stand

The first amendment refused three mitigations in one clause, on one stated reason:

> Refused: preserving a tag across a `body` replace, re-inserting it silently, or refusing the
> write. Each of those makes the tag tool-maintained bytes inside an authored region.

That reason is true of the first two and **false of the third**, and grouping them was the
error. Preserving and silent re-insertion both have the tool write bytes the author's own input
did not contain — and preservation cannot even preserve *position*, since a replace supplies the
whole region, so it converts a visible loss into a silent relocation. Both stand refused, and
the ruling does not touch either.

Refusing the write puts **no bytes anywhere**. A refusal is a precondition on the author's
input, not authorship of the file. Calling it "tool-maintained bytes in an authored region" was
a category error about a code path that writes nothing.

The codebase settles it, and this record cited the very fact without weighing it (**read**):
`_services/_items.py::set_body`'s `mutate` closure refuses a **role** body write outright on
`item.type == ROSTER_ROLE`, and a **system skill** body write outright on `is_system_skill` —
no `--force`, no escape — precisely because those bodies are the slot `sq:view:role_definition`
and the system-skill views render into (tag names spelled bare here, as elsewhere in this
record, since a body may not carry a well-formed marker), the region `_services/_base.py` seeds
the tag into at creation. That refusal has shipped for releases. Nobody has ever described it as the tool owning
content in a file it does not own, because it is not: it owns the *rule*, and the author owns
every byte that survives it.

So the operator's distinction is the correct one and it is the one this record was missing:

- **Overwriting an existing authored body is *protected*.** `--force` is exactly the consent
  that lifts that protection (`reject_body_overwrite`), and lifting it is what the flag is for.
- **Producing a body that omits a required view tag is *forbidden*.** It is a document
  invariant, not prose the author is consenting to lose. No flag lifts it, and `--force` says
  nothing about it — the two guards are independent and a write must clear both.

`required` is the declared, per-view generalisation of behaviour that already ships hardcoded
per type. My original reasoning survives only for the two mitigations that write; for the one
that refuses, it does not survive the codebase's own precedent.

### 1. Ruled: `required` is a key of the view declaration; the host set is derived, never declared

`required: bool` is a field of `ViewSpec` — one `[views.<name>]` key, beside `source`. It is
**not** a key of a type's selection or placement of a view, and no per-type view attachment
returns to carry it.

Refused, for the reason this record already spent a section on: a per-type requirement axis is
`ItemSpec.views` coming back. That surface was deleted by the ruling above, together with
`_prune_orphaned_type_owned_views`, because it put a view's name into a type's declaration and
coupled every project that later dropped or renamed the type to keeping the view. A `required`
flag hung off that axis would reintroduce exactly that coupling for a strictly smaller payload.
The third amendment refused the mirror shape for the same class of reason.

**The half the ruling leaves open is not "where does the flag live" but "which documents does a
required view bind".** The ruling's phrase is "a document of a type that carries it". Ruled:
**a required view's hosts are exactly the documents the tool's own placement authority seeds the
tag onto**, and that authority is already implemented, in one place per family:

- for an ordinary item type, the type's **creation template**, read through
  `views.template_seeded_view_names(item_type, spec)` — override-aware, resolved through the
  same `creation_template_name`/`template_source` pair the create path uses (**read**);
- for a role, a permanently-system skill, and a per-item-type `sq-<type>` skill, the **roster
  writer's classification**, which `MaintenanceMixin._repair_body_tag(item)` already computes —
  `role_definition` for a role, the `SYSTEM_SKILL_VIEW_NAMES` entry for the three fixed slugs,
  `ITEM_SKILL_VIEW_NAME` for a slug that currently documents a declared type, `None` for a
  custom author-defined skill (**read**).

Three properties make this the right derivation rather than a convenience:

- **A requirement nothing seeds is unsatisfiable.** If the host set were declared independently
  of the seeding authority, a type could require a view its creation path never places, and
  every freshly created item would be born in violation with no write able to fix it (a tag
  cannot enter through the prose door — `reject_markers`, first amendment). Deriving the host
  set from the seeder makes creation satisfy the invariant **by construction**, which is why §3
  gives item creation no gate of its own.
- **It declares nothing derivable**, the standing rule the first amendment already applied to a
  per-item `views:` list and the third applied to a per-type view name.
- **It is decidable from the host's type and slug alone** — never from the host's content. That
  is the same clause the second amendment put on source applicability, restated here as binding
  for this predicate, and it is what makes §5's tier placement available.

**Accepted, named: one flag per view, not per (view, type) pair.** A view seeded on two types is
required on both; there is no way to say "required on milestones, optional on epics". That is a
matrix declaration whose cells would be the same value in every case anyone has raised, and it
is declaration growth out of proportion to a distinction nobody needs yet. If the case arrives
it arrives as a new key on the declaration, never by moving `required` onto a type.

**Accepted, named: a hand-placed tag on a non-host document is not bound.** `sq view add` will
place a required view's tag on any document whose type the view's source applies to; that
document is not a host, so nothing requires it to keep the tag and `sq view rm` takes it off.
The requirement is keyed on the host relation **as the spec and its templates currently stand** —
never on how a tag arrived, which nothing records and nothing may start recording. That is the
first amendment's provenance rule, unchanged.

### 2. Ruled: the default is `required = false`

A view that says nothing about `required` is not required.

- **An upgrading corpus predates the flag.** Defaulting true would make every adopter view
  instantly binding on every host, retroactively, and the ruling gives the author no per-write
  escape from it. A restriction with no flag to lift it must be opted into, never inherited.
- **It is the honest default for the surface it governs.** A view an author places by hand, on
  documents of their own choosing, with `sq view add`/`rm`, is the ordinary adopter case. Its
  posture is exactly `required = false`: place it where you want it, take it off when you don't.
- **It keeps the bundled postures readable in one place.** Each bundled declaration states its
  own answer explicitly (§6), so `[views]` is the whole story and no reader has to know a
  default to read it.

**`required` is only ever asked of a *declared* view.** A view dropped from `[selected]` is not
declared, therefore has no hosts, therefore requires nothing — the same gate `_repair_body_tag`
already applies to every branch of its own classification (**read**), inherited rather than
restated.

### 3. Ruled: what binds it

**The body write path — bound, and it is the enforcement point that matters.** The guard sits in
`_body_mutate`'s `mutate` closure, so it covers `set_body` and the bulk importer's `body` op
through the one shared closure, not two implementations.

- **Replace refuses, unconditionally, on a required host.** It refuses without consulting
  `force`, and it refuses *before* `reject_body_overwrite` is reached, because the two guards
  are independent and this one is not forceable. There is no compliant replace to fall back to:
  a body text carrying the tag cannot enter through the prose door at all (`reject_markers`,
  first amendment, ruled with no hole in it), so "omit it" and "include it" are both unavailable
  and the honest answer is a refusal. **This is exactly today's observable behaviour for a role
  and a system skill** (**read**) — which is the point: the hardcoded refusals retire into the
  general rule with no behaviour change on the surface they already covered (§6).
- **Append is not refused by this rule.** `--append` keeps the whole existing region and writes
  after it, so it cannot produce a body missing a tag the body already had. A required host
  whose tag is genuinely absent is a different state, handled by §4.

**`sq view rm` — bound, narrowly.** `remove_view` refuses only when the named view is declared,
`required`, and *this* document is one of its hosts. Every other removal stays free, which
preserves the recovery path the second amendment wrote into it verbatim: a tag naming an
undeclared view, a view whose source cannot apply to this host, or a non-required view all come
off exactly as they do today. Without this clause the invariant would be a one-command bypass,
and `--force` not lifting it would mean nothing.

**`sq view add` — unbound.** Adding a tag is never the violation, and it is the remedy §4 names.
Its existing refusals (undeclared name, unresolvable template, inapplicable source) are
unchanged.

**`sq retype` — unbound, and it writes nothing.** A retype carries the body verbatim, so it can
move a document *into* a type that requires a view the document lacks, or *out of* one, leaving
an ex-required tag behind as an ordinary optional one. Neither is refused, stripped, relocated
or repaired. That is the second amendment's disposition applied unchanged: a tag valid when
placed and no longer valid is made **visible, never undone**, and retype's behaviour stays
unchanged while its outcome becomes a reported finding. The consequence to state plainly:
**a violating document is reachable without any write path producing it**, which is why the
invariant is "no write may produce it" plus a report — not "no corpus may contain it".

**Item creation — bound by construction, with no gate.** Creation renders the type's template,
which is the placement authority the host set is derived from (§1), so the tag is present the
moment the file exists. A gate here would be a check that the create path had done what the
create path is defined as doing.

**Spec load — unbound.** A `required = true` view that no template and no roster writer seeds
has an empty host set and binds nothing. That is vacuous, not broken, and it is the ordinary
intermediate state of an adopter who declares a view before overriding a creation template to
place it. Refusing it at load would fail a squad hard for a state that harms nothing — the
emptiness clause of the second amendment, applied to the declaration axis.

### 4. Ruled: what an upgrading adopter sees — a finding, not a migration and not a wall

**No new migration, and no hard stop.** The one-time retroactive write into authored bodies was
licensed once, under a closed condition set, and this record already states it is not a
precedent. `required` does not reopen it: `sq repair` gains **no** new backfill for an ordinary
item type, and no command rewrites an authored body to satisfy the flag.

What an adopter with a host document missing its required tag sees:

- **every read keeps working.** The rule binds writes, not reads. A body without the tag renders
  without that view's output, exactly as it does today.
- **`sq check` reports it**, at error level, naming the document, the required view, and the
  remedy — `sq view add` (§5).
- **the first body replace on that document is refused**, and the refusal names the same remedy
  rather than a bare "required view missing", so the author is never left blocked without the
  unblock in hand.

Two escapes exist, both spec-level and both deliberate, which is what makes "no flag lifts it"
livable: an adopter may **drop the view from `[selected]`** (undeclared, so no hosts), or
**override the creation template** that seeds it (the type stops being a host). Neither is a
per-write flag, both are visible in the spec tree, and both are the existing customisation
surface rather than a new one.

For the two roster families the corpus-level remedy also already exists and needs no change:
`_repair_body_tag` plus `_backfill_roster_body_tags` converge a role's and a system skill's
region onto the tag under their existing licence (**read**).

**This repository is already compliant** (**read**): all four milestone files carry
`sq:view:milestone_rollup` after this release's migration, all ten role files carry
`sq:view:role_definition`, and every skill file carries its own view tag except
`releasing-squads` — a custom, author-defined skill, which correctly has no required view and
whose body is authored content.

### 5. Ruled: tier 1 — the always-on per-file scan, not the selectable catalog

A required view's tag missing from one of its hosts is an **error-level finding produced
unconditionally by `MaintenanceMixin._scan_for_check`'s raw-text file-level pass**, beside
`_marker_issues` and `_view_target_issues`. It is **not** a `CATALOG`/`VALIDATOR_NAMES` member,
and it never will be. Both of `_validators.py`'s stated tier-1 properties hold, and the second
one decides it:

- **It needs no resolved `Item`.** The scan binds the host type from the type folder and the
  `PREFIX-*.md` filename before `read_frontmatter` runs, and the filename's own slug segment is
  what `Item.slug` is defined as (`_models/_item.py::_slug_from_path`) — so both inputs §1's
  predicate is allowed to read are in hand at that point (**read**). A file too broken to parse
  still gets the finding, which is where a finding about a document that cannot render earns its
  keep.
- **It must not be selectable.** This is the tiering test's easy case. `required` is a *declared*
  statement that a document of this shape must hold this tag; a project that does not want the
  requirement clears `required`, drops the view, or overrides the template (§4). A project that
  declares the requirement and then selects the check that enforces it separately has expressed
  the same intention twice and can leave the two disagreeing. A binding invariant whose
  enforcement is opt-in is not a binding invariant.

**Said plainly, because earlier decisions assumed otherwise: this removes the catalog-only
advisory entirely.** TASK-942's warn-level member, its `VALIDATOR_NAMES` /
`DEFAULT_VALIDATOR_LEVEL` / `UNGUARDED_VALIDATOR_NAMES` entries, its category placement, this
project's own selection of it, and the `squads/.overrides/workflow.toml` that selection would
have required all fall away. This repository keeps having no overrides, and the enforcement it
now gets is stronger than the advisory it is not building. The one derivation TASK-942 was
correctly held to — "which view names does this type's creation template currently seed", read
once, never reimplemented — survives intact and is what §1 consumes.

**Nothing is reported for a non-required view.** A view with `required = false` has no host set,
so "this document used to carry it" is a question about provenance, which nothing records and
nothing may start recording. A tag taken off such a document is an ordinary body edit.

### 6. Ruled: the five roster views and `milestone_rollup` are all `required = true`

- `role_definition`, `squads_skill`, `greeting_skill`, `memory_skill`, `item_skill` —
  **required**. Each of these bodies *is* the slot its view renders into; without the tag the
  document reads as nothing. This is the behaviour already hardcoded in `set_body`, now
  declared.
- `milestone_rollup` — **required**. This one is a change of position and it is stated as such.
  The first amendment's problem-2 disposition rested on "an author who does not want a view on
  one document is in a state a competent squad can sit in on purpose"; the ruling replaces that
  per-document opt-out with a spec-level one (§4), which is what "a document invariant, not
  prose the author is consenting to lose" means. It is also the only bundled view a body write
  can reach at all — the other five sit on bodies already refused — so leaving it optional would
  ship a flag with no bundled consumer and change nothing the ruling was made about. The corpus
  satisfies it today (§4).

**The hardcoded per-type refusals in `set_body` retire**, with two constraints on the retirement:

1. **Replace only.** The `ROSTER_ROLE` and `is_system_skill` branches are replaced by the general
   required-host rule, which refuses a replace on exactly those documents for exactly the same
   reason. The unrelated third branch — a project-declared roster type whose body is generated —
   is not a view question and stays as it is. The custom-skill admission stays too, and falls out
   of the derivation rather than being special-cased: a custom skill has no seeded view, so
   nothing requires anything of it.
2. **The append refusal on tool-converged roster bodies stays, and it is a separate rule.**
   Today's role/system-skill branches refuse `--append` as well, and the general rule does not
   (§3). That widening must not happen by accident here, because those regions are converged by
   the repair sweep: prose appended beside the tag is erased by the next `sq repair` with no
   warning (`_repair_body_tag`/`_converge_body_tag`, **read**). Ruled: the append refusal
   survives, keyed on the sweep's own classification — the same predicate, asked once — and
   never on a type literal re-spelled in `set_body`. Whether a converged roster body should ever
   admit authored prose beside its tag is a separate question this amendment does not open.

One thing the retirement must not lose: today's role refusal names the real remedy — declare the
definition in `.overrides/roles.toml`, or `.overrides/roles/<slug>.toml` for a project-defined
role. A generalised refusal composed from the view's name cannot carry that sentence without a
per-view message key, which is declaration growth for one string. Ruled: the generalised refusal
names the item, the required view, and the placement verb; the role-authoring pointer belongs to
the role surface and stays reachable from `sq role <slug> show`'s empty-body hint
(`empty_body_hint_state`'s consumers), and putting it there is part of the retirement, not a
follow-up.

### 7. What this obliges

- TASK-942 is rescoped and renamed by the tech lead around the required flag: the `ViewSpec`
  key, its default, the one host-set helper composing the two existing derivations of §1, the
  write-path and `view rm` guards, the tier-1 finding, and the `set_body` retirement with its
  two constraints. The catalog member, its tables and the overrides file it needed are dropped.
- The host-set helper is **one** function, consuming `template_seeded_view_names` and the
  `_repair_body_tag` classification rather than re-deriving either. Two answers to "which view
  does this document carry" is the drift TASK-942's single-condition rule already existed to
  prevent, and adding a requirement on top of it raises the cost of disagreement from a missing
  advisory to a wrongly refused write.
- The predicate may not read the host's content — type and slug only — and a future required
  view that cannot be decided that way is a proposal to move this finding out of tier 1, to be
  read and answered as exactly that.
- The regression shapes owed on landing: a replace refused on a milestone (the case that has
  never been refused before), `--force` failing to lift it, an append succeeding on the same
  document, `view rm` refused on a host and permitted on a hand-placed non-host, a retype into a
  required host producing a readable document and a reported finding, and a dropped-from-
  `[selected]` view requiring nothing.

## Fifth amendment — 2026-09-15: the retirement narrows the roster refusal, intentionally, and the repair sweep's wide licence goes with it

FEAT-907's breakdown found that the fourth amendment's `set_body` retirement is **not** the
behaviour-preserving substitution that amendment claimed. It is a narrowing, it is intended, and
it has a consequence in `_services/_maintenance.py` that the fourth amendment did not reach. The
ruling, the pricing and the first three amendments are untouched; the fourth is corrected in
place below.

Every claim is labelled **read** (traced in source) or **inferred**. Nothing was driven.

### 1. The two sentences that are wrong

From the fourth amendment §3:

> **This is exactly today's observable behaviour for a role and a system skill** (**read**) —
> which is the point: the hardcoded refusals retire into the general rule with no behaviour
> change on the surface they already covered (§6).

And from its §6:

> The `ROSTER_ROLE` and `is_system_skill` branches are replaced by the general required-host
> rule, which refuses a replace on exactly those documents for exactly the same reason.

"Exactly those documents" is false. The required-host derivation gates on the view still being
declared; `is_system_skill` does not gate on anything — it is **unconditionally bundled-blind**
on its built-in half (`bundled_skill_slugs()` takes no spec and no playbook, and composes
`managed_item_types()` against the *bundled* playbook singleton, **read**). So the derived set is
strictly smaller than the hardcoded one, in three shapes rather than the two the breakdown found:

- **a permanently-system skill whose view is dropped from `[selected]`** — `squads`/`greeting`/
  `sq-memory` stay in `bundled_skill_slugs()` forever, so `set_body` refuses today; the
  derivation yields no host and admits the write;
- **a role, when `role_definition` is dropped** — the third shape, not named in the breakdown
  and following identically: today's refusal is `item.type == ROSTER_ROLE`, which asks nothing
  about the spec at all;
- **a stale `sq-<type>` skill whose type is no longer declared** — and this one only narrows for
  a **historically-bundled** type. `sq-bug` after `bug` is dropped stays in the bundled-blind
  list and is refused today, while `item_type_for_skill_slug("sq-bug", spec)` returns `None`
  (**read**). A *project-declared* `widget`'s stale `sq-widget` is already writable today, since
  `custom_skill_slugs` iterates the live `spec.items` — no change there. The breakdown's second
  shape is real but half as wide as stated.

### 2. Ruled: the narrowing is intended, and it is the correction rather than the cost

A body region is tool-owned **because something the tool maintains renders into it**. That is
exactly "this document is a host of a declared view". Drop the view and nothing the tool
maintains renders there; the region reverts to what every other body already is — authored prose
the author owns. The narrowing is that sentence applied, and refusing it would mean keeping a
refusal whose own stated reason has gone false.

Because it has. Today's refusal tells the author that "an authored body here would never be
shown". In all three shapes that is **untrue** (**read**): `read_body` returns the `sq:body`
region's content verbatim and only calls `expand_view_tags` when the body carries a tag, so a
body with no tag — which is what a dropped view's host has, since every seeding writer and
`_repair_body_tag` alike gate on the view being declared — displays its prose exactly like any
other item's. The old refusal was, in these shapes, refusing a write whose output would have
rendered fine and telling the author the opposite.

**What the adopter in either shape now experiences.** An adopter who drops `role_definition`
(or a system-skill view) is an adopter who has said they do not want the generated definition;
authoring those bodies by hand is a coherent reason to have dropped it, and until now it was the
one thing the drop did not let them do. After this they write those bodies like any other. The
prose survives `sq sync` and `sq repair` — `_repair_body_tag` returns `None` for an undeclared
view, so the sweep never reaches the region (**read**) — and it is displayed by every read
surface. A later re-add of the view makes the document a host again: the tier-1 finding fires
for the missing tag, and `sq view add` inserts the tag at the region's end **keeping the prose**,
so the round trip loses nothing.

**One thing the narrowing incidentally fixes, and it is a real defect today (read).** `set_body`
and the repair sweep currently ask *different* membership questions about the same region:
`set_body` asks `is_system_skill` (bundled-blind ∪ live custom), the sweep asks
`SYSTEM_SKILL_VIEW_NAMES` / `item_type_for_skill_slug` (live only). They disagree on exactly the
stale historically-bundled slug above: `sq-bug` with `bug` dropped is **refused by the write path
and never reached by the sweep** — a region no command can write and no sweep can converge.
Routing the refusal through the one derivation the sweep already computes is what removes that
dead state, and keeping two membership tests for one question is the drift this record has
refused twice already.

### 3. Ruled: `_converge_body_tag`'s wide licence retires with the refusal that justified it

This is the consequence the fourth amendment did not reach, and it is the real answer to "is
anything lost that the old refusal was protecting". Not read-visibility — that reason was already
false (§2). What the unconditional refusal was actually protecting sits one module over, and says
so in its own words (`_converge_body_tag`, **read**):

> `set_body` refuses a role's and a permanently-system skill's body unconditionally *in current
> code* … so **no code path today can have authored either region**. … *strict_empty* stays
> `False` for these two.

That premise is the whole safety argument for the **wide** licence: a non-empty, marker-free
`sq:body` on a role or permanently-system skill can only be a pre-0.14 plain-prose rendering, so
converging over it discards a derived rendering and never authored work. The narrowing falsifies
it. Drop a view, author the body, re-add the view, and a version-drift backfill runs
`_converge_body_tag` non-strict over prose with no markers — which takes the
`if not sections.find_markers(current)` branch and **replaces the author's text with the tag
line** (**read**). The sweep cannot tell that prose from a legacy rendering, and it may not learn
to: both are marker-free plain text, and nothing records a tag's or a body's provenance — the
refusal this record has now made three times.

**Ruled: a role and a permanently-system skill move to `strict_empty=True`, the same licence a
per-item-type skill already carries.** Only an empty or already-tagged region converges;
anything else is left untouched, silently. The reason is not new — it is the reason already
written beside `strict_empty`, which exists because a `sq-<type>` slug "can be genuinely custom
at one point and become template-owned later, the moment a project declares a matching item
type." **The drop/re-add cycle is that exact shape one level up.** The narrowing does not create
a new hazard; it moves two more families into the one the narrower licence was built for.

**And the pre-0.14 legacy reclaim moves to where a one-time licence already belongs: a
migration.** A migration knows which release the corpus is arriving from, so it can know that a
marker-free role body is a superseded rendering; the standing sweep runs forever and cannot. That
is this record's own problem-1 distinction — a closed, release-scoped licence into a region the
standing tool does not get — applied to the one shape that still needs it. It also closes the
trap the narrower licence would otherwise leave: a legacy-rendered role body is not writable
(required host), not convergeable (strict), and would have had no remedy at all; converged once
by the migration that brings the corpus to this release, it never needs one.

**The escape for a required host whose region holds content the author wants gone** is the
spec-level one this record already names, not a new flag: clear the requirement (drop the view
from `[selected]`, or override the seeding template), write the body, restore it. To change what
a required document must hold, you change the requirement — which is the same answer `--force`
already gets.

### 4. Confirmed: the narrowing does not reach `view rm`, and cannot

`remove_view` refuses **nothing** today beyond a missing `sq:body` region (**read**), so the
fourth amendment's declared-and-required-and-host rule can only *add* refusals there. There is no
existing behaviour for a narrowing to remove.

In all three shapes of §1 the view is undeclared, therefore not required, therefore not a host —
so removal stays free, which is precisely the second amendment's ruling that `view rm` must keep
taking a tag off a document for a view the spec no longer declares, because that is the recovery
path for exactly this state. The two rules agree without either being weakened, and a stale tag
left on a body by a dropped view remains removable by the one verb built for it.

### 5. What this obliges

- The fourth amendment's two sentences quoted in §1 are corrected here rather than tidied away:
  the retirement is a narrowing, it is intended, and the tech lead's breakdown must scope it as a
  behaviour change with its own regression shapes rather than as a substitution nobody needs to
  look for.
- `set_body`'s roster refusal and the repair sweep's convergence read **one** classification, and
  the write path may not keep a second membership test of its own. That is what removes the dead
  region of §2, and it is the same single-derivation obligation the fourth amendment §7 already
  placed on the host-set helper.
- `_converge_body_tag` loses its non-strict branch for a role and a permanently-system skill; the
  pre-0.14 reclaim it existed for lands as a migration step under the closed, one-time licence
  this record already defines. A future reader proposing to restore the wide licence is
  proposing to let a standing sweep guess at authored prose, and is to be answered as that.
- Regression shapes owed, beyond the fourth amendment's list: a role body written and read back
  with `role_definition` dropped from `[selected]`; the same for a permanently-system skill; a
  stale historically-bundled `sq-<type>` body written after its type is dropped (the region that
  is dead today); that prose surviving a `sync`, a `repair`, and a version-drift backfill; and
  the drop → author → re-add round trip ending with the tag placed and the prose intact.

## Sixth amendment — 2026-09-15: the placement-verb clause is restated as a property, and it was not met

REV-952's F6 found that the 0.14 to 0.15 corpus migration does not call FEAT-905's placement
verb. The finding is dispositioned WontFix on the mechanism, with the record half raised here.
This section settles the record half. The ruling, the pricing and the five earlier amendments
are untouched.

Every claim below is labelled **read** (traced in source) or **cited** (taken from REV-952's own
driven evidence, which I did not re-drive).

### 1. The clause, and what it was doing

From the first amendment's second correction:

> That verb also settles problem 1's remaining discomfort: the migration inserts through the same
> path an operator uses, so it is the tool's own placement applied in bulk rather than a bespoke
> one-off write into authored prose. The licence and the fence on it stand exactly as ruled.

Two things sit in that sentence and only one of them is a ruling.

The **ruling** is the one before it: `reject_markers` stays fully closed for prose, and placement
is its own marker-safe verb. That is untouched and is not what this amendment is about.

The **clause** is the sentence quoted — a mechanism named in order to guarantee an outcome. Its
operative content is that the six conditions of the retroactivity licence (insert-only, one
deterministic anchor, idempotent skip, scoped to types whose creation template seeds the tag, a
reported count, an author's later placement preserved) are satisfied by the tool's own placement
code rather than re-spelled by the migration. "Run through the verb" was how I proposed to
guarantee that, not a seventh condition of its own.

### 2. What was delivered

The runner does not call `insert_view`. It inlines `_section_edit_core`'s read → skew-check →
mutate → write sequence, under one open transaction for the whole run rather than
`insert_view`'s one transaction per item (**read**, the runner's own module docstring).

**Cited**, from REV-952's line-by-line comparison: the anchor, the insert-only property, the
idempotent skip and the tag's own text all come from the one shared
`insert_unpaired_marker` / `markers.view_tag` pair; none of them is re-spelled locally, and the
inlined sequence is faithful to `_section_edit_core`.

The runner's stated reason for not calling the verb is overstated and is corrected here rather
than carried: its docstring says it "cannot call that verb directly" because `squads._services`
imports the module through the migration registry. The static cycle is real; a deferred import is
not blocked by it, and this codebase uses deferred imports for exactly this purpose. The honest
driver is the one-open-transaction shape, which the delivering task offered as a free choice and
which `insert_view` cannot provide. That is a legitimate reason, and it is the one the record
should carry.

### 3. Ruled: the clause is restated as a property, and the property is what binds

**A migration is not obliged to call the placement verb.** The one-transaction-per-run shape is a
sufficient reason to compose the primitives directly, and this record does not require a bulk
writer to accept N lock acquisitions and N index commits to satisfy a sentence about routing.

What it is obliged to do instead, and what replaces the clause:

> A bulk writer that places view tags composes the tool's own placement primitives — it re-spells
> none of the licence's conditions — **and applies each of them at the granularity the placement
> verb applies it.**

The second half is the part the original clause carried implicitly and the restatement makes
binding, because it is the half that failed.

### 4. Ruled: the condition was not met, and the clause earned its keep

I decline the reading that the condition was satisfied in substance by a different route. It is
true of five of the six conditions and it is false of the one that matters, and stating the
comfortable four-fifths as the finding would leave the next reader believing a constraint had
been costlessly substituted when its one uninherited clause is the defect under review.

What is true, stated at the right width: the runner satisfies the restated property on every
clause but one. The exception is the applicability predicate. `insert_view` asks
`resolve_view_target` **inside the locked edit, per item**, so an unresolvable name refuses one
placement; the runner hoists the same predicate above the write loop and applies it per
`(type, name)` pair, which widens a per-item refusal to the whole corpus — and, because a raising
migration writes no schema stamp, to the whole squad (**cited**, driven in REV-952 on a corpus of
two milestones and again on a freshly initialised squad holding zero milestones).

So the divergence is not a residue of the substitution; it is the substitution's only real
content, and it produced the release-blocking finding. The clause did the work it was written to
do, which is why it is being restated rather than dropped.

The remaining clause is met when per-item granularity is restored, and the record should be read
that way: the substitution is complete at that point and not before. Nothing about the delivered
runner is being re-architected to get there — the fix is to the predicate's position, which the
same task already owns.

### 5. What the next reader takes from this

- **The ruling's reviewer test is widened by one item.** It reads today: "a reviewer finding the
  anchor, the idempotence rule, or the tag's text composed anywhere in the new code should read
  that as the defect it is." Add: **a predicate the placement verb asks per item, asked by a bulk
  writer per corpus, is the same defect class** — even though nothing has been re-spelled and
  every shared primitive is in use. Re-spelling is the visible form of the failure; changing a
  check's granularity is the invisible one, and it is the one that shipped.
- **The licence and its fence are unchanged.** The one-time retroactive write into authored bodies
  stands as ruled, with its six conditions and its "not a precedent" clause, and this amendment
  neither widens it nor licenses a second one.
- **A record correction is owed in the runner itself**, not only here: the "cannot call that verb
  directly" claim is withdrawn in favour of the transaction-shape reason, in the same pass that
  corrects the other false claim in that docstring.
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
- [2026-09-14T19:20:18Z] Pierre Chat:
  - Ruling on view tag placement and erasure, overturning this ADR's refusal of "refusing the write":
    
    - **A view declaration carries a `required` boolean.** When a view is required, a document of a
      type that carries it MUST hold its tag.
    - **Skipping a required view is forbidden, and `--force` does not override it.** The two
      protections are distinct and only one is forceable:
      - overwriting an existing authored body is *protected*, and `--force` is exactly the consent
        that lifts that protection — it forces a whole rewrite, which is what it is for;
      - producing a body that omits a required view tag is *forbidden*, not protected. It is a
        document invariant, not prose the author is consenting to lose, so no flag lifts it.
    - The precedent this follows is already in the codebase: `set_body` refuses a role or
      system-skill body write outright, because that body is the slot its definition renders into.
      `required` makes that declared and per-view instead of hardcoded per-type.
    
    TASK-942 is to be rescoped and renamed around the required flag rather than built as the
    template-derived advisory it currently describes.
- [2026-09-14T19:28:26Z] Robert Architect:
  - - Fourth amendment appended, recording @op-pierre's ruling on `required`. The ruling, the pricing and all three earlier amendments are untouched; @manager @tech-lead.
    - My original refusal falls on one of its three limbs, and the codebase says so: preserving a tag and silently re-inserting it both have the tool write bytes the author never supplied (still refused, untouched); *refusing the write* writes nothing anywhere, and `set_body` has shipped exactly that refusal for role and system-skill bodies for releases. Calling a code path that writes nothing "tool-maintained bytes in an authored region" was a category error, and I cited that very refusal in the same amendment without weighing it. `required` is the declared, per-view generalisation of behaviour already hardcoded per type.
    - Settled: `required` is a key of the view declaration, never of a type's selection — a per-type axis is `ItemSpec.views` returning. The half the ruling leaves open is the host set, and it is **derived, never declared**: a required view's hosts are the documents the tool's own placement authority seeds it onto — `template_seeded_view_names` for an item type, `_repair_body_tag`'s classification for role/system/per-item-type skills. That makes creation satisfy the invariant by construction and keeps the predicate type-and-slug decidable.
    - Default `required = false` (an upgrading corpus predates the flag and there is no per-write escape from a restriction, so it must be opted into). Bound: the body write path (replace refused unconditionally, before and independent of `--force`; append untouched) and `sq view rm` on a host. Unbound: `view add`, `retype` (writes nothing, outcome becomes a reported finding), item creation, spec load.
    - Tier 1, plainly: the missing-required-tag finding is an unconditional error in the per-file scan beside the dangling-tag one — it needs no resolved Item and a declared requirement whose enforcement is opt-in is not a requirement. So TASK-942's catalog member, its tables, this project's selection of it and the `.overrides/workflow.toml` that selection needed all fall away. Nothing is reported for a non-required view: that would be a provenance question.
    - All six bundled views are `required = true`, `milestone_rollup` included — a stated change of position, and the only bundled view a body write can even reach. `set_body`'s hardcoded role/system-skill branches retire into the general rule for **replace**; the append refusal stays as a separate rule keyed on the repair sweep's own classification, because that region is converged and appended prose would be erased silently. This repo is already compliant (4/4 milestones, 10/10 roles, every skill but the one custom `releasing-squads`).
- [2026-09-15T07:20:35Z] Robert Architect:
  - - Fifth amendment appended, ruling @tech-lead's finding. The fourth amendment's "no behaviour change" claim is quoted and corrected; the ruling, the pricing and the first three amendments are untouched. @manager @tech-lead.
    - **The narrowing is intended.** A body region is tool-owned because something the tool maintains renders into it — drop the view and nothing does, so the region reverts to authored prose. Today's refusal tells the author "an authored body here would never be shown", and in these shapes that is simply untrue: `read_body` returns the region verbatim and only expands when a tag is present, so the prose would display fine.
    - **Three shapes, not two, and one is half as wide as reported.** The role with `role_definition` dropped is the third (today's `item.type == ROSTER_ROLE` asks nothing about the spec). And the stale `sq-<type>` shape narrows only for a *historically-bundled* type — `sq-bug` is bundled-blind and refused today, while a project-declared `widget`'s stale `sq-widget` is already writable, since `custom_skill_slugs` iterates the live spec.
    - **What the old refusal was actually protecting is one module over, and it has to go with it.** `_converge_body_tag`'s wide licence rests in writing on "no code path today can have authored either region" — which the narrowing falsifies across drop → author → re-add: a version-drift backfill then hits marker-free prose and replaces it with the tag line. Ruled: role and permanently-system skill move to `strict_empty=True`, the licence a per-item-type skill already has for exactly this shape one level up; the pre-0.14 legacy reclaim moves to a migration, under the closed one-time licence this record already defines. That also closes the trap where a legacy-rendered role body would be neither writable nor convergeable.
    - **One real defect the narrowing fixes.** `set_body` asks `is_system_skill` while the sweep asks `item_type_for_skill_slug` — two membership tests for one question, disagreeing on exactly the stale bundled slug: `sq-bug` with `bug` dropped is refused by the write path and never reached by the sweep. A region no command can write and no sweep can converge.
    - **`view rm`: confirmed unaffected.** It refuses nothing today, so my declared+required+host rule can only add refusals — there is no behaviour for a narrowing to remove. In all three shapes the view is undeclared, so removal stays free, which is the second amendment's recovery path preserved exactly.
<!-- sq:discussion:end -->
