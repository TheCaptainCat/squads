---
id: ADR-776
sequence_id: 776
type: decision
title: 'Derived views: one computed projection, and no body sink'
status: Accepted
author: architect
refs:
- FEAT-693:addresses
- FEAT-694:addresses
- ADR-422
- ADR-766
- ADR-71
- ADR-74
- ADR-663
- ADR-775
- ADR-777
- ADR-781
created_at: '2026-08-22T09:28:29Z'
updated_at: '2026-09-02T13:13:25Z'
---
<!-- sq:body -->
## Context

FEAT-693 specifies a derived view in four parts — source, projection, presentation, sink — and asks
that the mechanism encode a source-determined sink: a local source may materialise into a
marker-delimited body region, a foreign source must be computed, and the mechanism refuses the
foreign-source body sink rather than trusting the author. FEAT-694 is scheduled against the body
sink: it converts the two hand-rolled projections, the sub-entity roll-up summary and the head badge
line, onto declared body-sink views with byte-identical output.

Three consumers are in view, and the operator named the third: a role's `## Skills` section, whose
source is foreign because each skill's `scopes` edge lives in the skill's own item.

Before designing the sink, the two shipped instances were measured. What follows is driven on a
scratch squad at `sq` 0.13.0, and it changes the shape of the mechanism rather than confirming it.

**Nothing reads either materialised region.** Four computed renderings of the sub-entity projection
ship, and none of them reads the body:

- the summary table under `sq <type> <n> show`, computed from frontmatter through the shared
  column derivation (read: `_cli/_common.py:790-813`, calling `discussion.summary_columns`/`summary_row`);
- the block pane title under `show --full`, computed from `_subentity_pane_title_raw` while the pane
  body prints only the block's `:body` region (read: `_cli/_common.py:582-614`);
- the meta line under `sq <kind> show`, a third layout of the same fields (read: `_cli/_common.py:815-830`);
- `_subentity_badge_line` for the `--raw` dossier, a fourth (read: `_cli/_common.py:725-731`).

Driven: `sq task 20 show --full` prints the computed table and the computed pane title and never
prints the `:head` region's text at all. The two materialised regions are read by exactly one kind of
reader — a person or an agent opening the raw file.

**The head is not local-source, and never was.** `_refresh_head` resolves the assignee's display name
through `self.author(sub.assignee)` — the ROLE item, another file — and the mapped story's label
through `db.get(task.parent)` — the parent feature, another file (read:
`_services/_subentities.py:753-776`). Driven: renaming a story's title updates the parent's own
`:summary` region and leaves the subtask's `:head` reading `US1 — Original story title`; declaring a
`full_name` override for `architect` renames the role item and leaves the same `:head` reading
`**Assignee:** Robert Architect`. A full `sq sync` heals neither, and `sq check` reports nothing.

ADR-422 decided a sibling question on exactly this axis and drew the line in the same place FEAT-693
does — "the `:summary` / `:head` regions are local. A parent's summary is a pure function of that
same file's own frontmatter … that locality is why the precedent is cheap and always-correct." Half
of that is true. The summary is local: its row carries the assignee's slug and the story's id, not
their resolved labels (driven: `| ST1 | Todo | architect | Do the thing | US1 |`). The head is not,
and the precedent it was cited as is the one already broken. ADR-422's own verdict on its option C —
that a silently-stale committed rendering is worse than none — is the argument that decides the head,
turned back on the region the decision took as its baseline.

**A materialised region can be silently wrong after a merge, and no verb fixes it.** Driven: two
branches, one adding a subtask and one changing a subtask's status, conflict in *both* the
frontmatter `subentities:` list and the `:summary` table of the same file. Resolving the frontmatter
correctly and leaving the table at one branch's rendering passes `sq repair` and `sq check` with exit
0 — while `sq task 19 show` prints two rows and the file's own table prints one. Two answers to one
question in one file, and no command re-derives the region from the resolved frontmatter.

## Decision

### 1. A view has three parts, and a sink is not one of them

A derived view declares **source**, **projection** and **presentation**. There is no fourth part.

- **source** — the relation to project: refs of a declared kind pointing at this item, a sub-entity
  collection, or a subtree. A ref-kind source names a declared entry of the workflow spec's ref-kind
  section, adopter-declared kinds included.
- **projection** — which fields to carry, how to group, how to order. Produces records and makes no
  presentation decision.
- **presentation** — a template over those records.
FEAT-693's fourth part is dropped rather than constrained (§4). That satisfies the constraint the
feature asked for more completely than the refusal it asked for: a state nobody can express needs
no author to be trusted and no refusal to be tested.

### 2. Projected data keeps one uniform shape, and that is the contract

Records with typed fields, optionally grouped, identically shaped across every source and every
presentation. Field metadata and grouping travel with the payload, so a client can consume a view it
has never seen without special-casing it. `--json` emits the projection and skips presentation
entirely.

This is already how the sub-entity projection behaves and it is worth naming as the precedent rather
than as an aspiration: `summary_columns`/`summary_row` derive columns and cells once, from the
declared fields of the kind, and four renderers consume that one derivation (read:
`_cli/_common.py:794-813`, `_cli/_items.py:665-677`, `_discussion.py:289-330`). The uniform shape is
what let a fourth renderer be added without touching the other three.

The CLI table is one presentation over the records, never their source. A client that lays out the
records itself is the intended consumer, not a client that reparses what the CLI printed.

### 3. Presentation is a template, and the deferral it was scoped around has lapsed

Presentation is a Jinja2 template over the records, resolved through the one engine every rendering
path already uses. A table, a single-line badge string, a sentence, a bulleted list and a nested
outline are five templates, not one renderer with four flags. The two shipped surfaces are already
exactly this — `subentities/summary.md.j2` is a table template over rows, `subentities/head.md.j2` is
a text template over the same fields — so no rendering technology is introduced.

FEAT-693 puts adopter-authored presentation templates out of scope on the ground that they "need
project-level template overrides, which this codebase has deliberately deferred." That premise has
lapsed: `.overrides/templates/` ships, resolves per file ahead of the bundled tree, carries a
provenance stamp and is covered by `sq override scaffold`/`diff`/`update`/`list` (ADR-85; read:
`_overrides/_service.py:139-141`, `285-317`). A view's presentation template lives under
`templates/views/<name>.md.j2` and is therefore adopter-overridable the day it ships, with no new
surface — the override key is the template name, as it is everywhere else. The bundled set is still
what ships; what is retired is the reason for forbidding the override.

### 4. The sink rule: every derived view is computed

**A derived view is never materialised. There is no sink to declare and none to derive.**

The rule arrived here through two narrowings. Source locality was the first proxy, and it answers
the question incorrectly in both directions (see Context). "Whether a shipped verb regenerates the
region" was the second, and it left exactly one exception standing: a region of a document that a
non-human reads *as its content*, with no `sq` in the delivery path. That described the role and
skill item bodies an agent reaches through the generated pointer's `@` reference, and nothing else.

That exception closes by removing its reader. No materialised file squads generates may carry a
local file path, because a path resolves to nothing when the CLI is a client to a server and there
is no local squad directory; a pointer names the commands an agent runs instead. Once a pointer
names `sq role <slug> show` rather than `@squads/agents/roles/ROLE-N.md`, `sq` is in the delivery
path for the one reader that previously could not receive a computed value — so it can compute one.

**Every non-human reader of item markdown, enumerated, because the collapse is only as sound as the
enumeration:**

| Reader | What it reads | Survives the direction |
| --- | --- | --- |
| the index rebuild and per-item reads | frontmatter | yes — and never a derived region |
| `show` and the sub-entity panes | the `:body` / `:discussion` regions | yes — authored prose, not a projection |
| `sq search` | every body line after the frontmatter (read: `_services/_collab.py:436-441`) | yes — the one survivor, and its dependence is a defect rather than a requirement (see Consequences) |
| migration runners | body regions, to rewrite them (read: `_migrations/_meta_compat.py`) | yes — as the mechanism that *removes* a region, never a consumer of one |
| `_regen_role_body`, the skill-body writer | the file, to preserve `:discussion` | yes — writers |
| the VS Code client | `.squads.toml` only; every other read is `sq … --json` (driven: `clients/vscode/src/squadDir.ts:141`, `processRunner.ts`) | yes — and never item markdown |
| the agent host's `@` resolver | a role or skill body **as its content** | **no** — removed by the direction above |

The `@` resolver was the only non-human reader that consumed a derived region as content. With it
gone, no materialised region in any item file has a reader, so this mechanism ships one behaviour and
no enumeration of exceptions to keep current.

**What this does not abolish, stated so the rule is not over-read.** squads still writes generated
files into another tool's configuration — the backend pointers, the compiled `CLAUDE.md` /
`AGENTS.md` managed regions, the per-entry staging artifacts. Those are materialised projections read
by a non-human with no `sq` in the loop, and they must stay materialised, because an agent host reads
files and cannot run a command. They are categorically not views. They are **write-only**:
regenerated wholesale, never read back — a rule with its own guard
(`tests/meta/test_a_backend_never_reads_back_its_own_generated_output.py`) and its own recorded
failure from when it was broken, where a role's mission was recovered by matching the
`**Mission:**` prefix of a line the backend had just rendered itself (read:
`_backends/_agents_md/_backend.py:66-79`). Invariants 5, 6 and 7 and the `AgentBackend` ABC govern
them; a view's sink never did.

That is a statement about which decision governs them, **not** a licence for their contents. "The
host reads files" establishes that a generated file must exist; it establishes nothing about how much
squad state the file may copy, and a committed pointer carrying a role's model, description and
resolved skill set is stale-capable in exactly the way this decision refuses everywhere else. What a
generated pointer may contain is ruled by the pointer decision, under its own containment rule, and
this section defers to it rather than settling it by omission.

### 5. The three consumers, ruled

- **The sub-entity roll-up summary → computed.** A genuinely local projection, and still not worth
  materialising: four computed renderings already ship, none reads it, and it is the region the
  driven merge left silently wrong.
- **The head badge line → computed.** Foreign-sourced in fact, stale in fact, and read by nothing.
- **A role's `## Skills` section → computed, and the section leaves the body template.** The
  materialised case for it rested on the agent reading the role body directly through the pointer's
  `@` reference, and that reference is what the direction removes. The computed home already exists
  and needs no new surface: `sq role <slug> show` prints a **computed** catalog card ahead of the
  stored body — resolved through `resolve_role_with_base`, and already carrying a computed
  `creates:` row (read: `_cli/_role.py:324-345`; driven: the card renders name, title, model, can
  spawn, creates, mission and responsibilities). The skills list becomes one more row beside
  `creates:`, resolved through `resolved_skills_for_role` (read: `_services/_base.py:1183-1203`),
  and `role.md.j2:18-25`'s `{% if extra.get('skills') %}` block is deleted rather than re-pointed.

  The **stored cache** goes with it, and would have anyway. `extra.skills` is a frontmatter copy of a
  value `_resolve_role_skills` computes with no I/O beyond the index the caller already loaded, from
  `db.backrefs` plus the playbook-derived system list (read: `_services/_base.py:1156-1181`). Driven:
  11 skill items against 747 items in this repo's own corpus.

  ADR-766 §6 declined the mirror-image change on `full_name`/`mission` because removing a key from
  `RoleDef.extra_keys()` would leave `PERMITTED_EXTRA_SKEW` and have to be re-added by hand as a
  legacy exemption. The shapes are opposite. `X.SKILLS` is not a member of `RoleDef.extra_keys()`; it
  is the separate first term of `frozenset({X.SKILLS, *RoleDef.extra_keys()})` (read:
  `_itemfile.py:70`), and its exemption exists only for this cache — the sole writer that persists it
  outside `store.transaction()` (read: `_services/_base.py:1279-1330`). It dies with the cache
  instead of outliving it.

### 6. What this means for FEAT-694's premise

FEAT-694 is a conversion onto a sink that does not survive, with byte-identical output as its
acceptance bar. Both halves change:

- Its subject inverts. The work is to **retire** the two materialised regions and reissue both
  projections as computed views, not to re-implement them on a general body-sink mechanism.
- Its acceptance bar cannot be byte-identical output, because the output that disappears is the two
  regions themselves. It is instead: every computed rendering of the projection is byte-identical
  before and after, the four that ship today included; the regions are removed from existing item
  files; and no authored content moves.
- A migration **is** owed, which FEAT-694 asked to have settled explicitly rather than assumed. The
  regions are on-disk format, present across the corpus, and removing them is a corpus-wide edit —
  the runner strips the `sq:summary` and `sq:<kind>:<id>:head` regions and leaves every other byte,
  including the authored `:body` and `:discussion` regions inside each block, untouched.

That is a reauthoring of the feature, not an implementation note against it.

### 7. Where a view is declared, and what that inherits

Views are a keyed section of the **workflow document**, not the playbook. A view's source names a ref
kind, a sub-entity kind or an item type — all workflow-spec vocabulary — and the workflow document is
the only one carrying the `[selected]` deselect an adopter needs to drop a bundled view. So `[views]`
enters `WORKFLOW_TOP_LEVEL_SECTIONS` and `[selected]`'s closed section list, and inherits the merge
semantics, the provenance stamp and the collect-all lint report by registration rather than by new
wiring.

Two consequences of that placement, both of which are the point of settling these together:

- A view naming a type, kind or sub-entity kind the merged spec does not declare is a referential
  violation on the merged spec, caught by the same pass that catches a lifecycle bound to a dropped
  status — so a `[selected]` line that drops a ref kind a view projects fails without any
  view-specific guard.
- The uniformity decision's manifest widening is a prerequisite for shipping an adopter-editable view
  set, not an adjacent nicety: without a content hash for `workflow.toml`, every adopter who declares
  a view is told their override may be stale on every release thereafter.

An adopter-declared view over an adopter-declared ref kind is therefore the ordinary case, and the
sink question cannot reopen for it: there is no sink, so there is no field an adopter could set and
no combination for the mechanism to refuse.


## Consequences

- **`sq search` narrows, deliberately.** Search scans every body line after the frontmatter (read:
  `_services/_collab.py:402-442`), so today a query matches sub-entity status, assignee and story
  text inside the two regions. After removal it matches the block heading's title but not the
  derived fields. What is lost is a text match over a derived value — a filter's job — and the text
  it matched could be stale (driven). The remedy is the existing per-kind list and its `--json`.
- **The refusal FEAT-693 asked for disappears rather than being implemented.** There is no
  foreign-source-body-sink combination to reject, because there is no sink. A test asserting the
  refusal would have nothing to assert.
- **`sq role <slug> show` already prints a role's mission and responsibilities twice** — once in the
  computed card and once in the stored body beneath it (driven). That is a pre-existing duplication,
  and it stops being cosmetic once a pointer names that command as an agent's startup read: the two
  renderings can disagree, because the card resolves a project override and the body carries
  whatever the last `sq sync` wrote. Settling it belongs with the pointer's own decision, not here,
  but it is a consequence of routing the agent through `show`.
- **`role.md.j2` loses its `## Skills` block, and three item templates lose their summary region**
  (`items/task.md.j2`, `items/feature.md.j2`, `items/review.md.j2` — read). That makes this a
  bundled-template edit, so it inherits the release ordering stated once in the pointer decision's
  sequencing section — the version bump before the manifest regeneration — rather than restating it.
- **`PERMITTED_EXTRA_SKEW` changes membership, and one test pins it as a literal.**
  `tests/unit/test_role_def_extra_keys.py:43-64` asserts the exact frozenset including `X.SKILLS`,
  precisely to catch an unreviewed widening. Dropping the cache narrows it — the safe direction — and
  that test must be edited in the same change, with its docstring stating why the narrowing is
  intended. The per-item exemption at `_itemfile.py:130-136` returns `frozenset({X.SKILLS})` for a
  dev role and collapses to empty; the `save-and-restore` rollback in `_refresh_role_skills_extra`
  goes with the method.
- **`ensure_summary`, `set_head` and `_refresh_head` retire**, and with them the refresh-on-mutation
  obligation on every sub-entity write. The column derivation, the badge resolution and the two
  templates stay — they become the bundled presentations of two declared views.
- **A view over a foreign source is computed per request**, so its cost is the index load the request
  already performs plus an inversion — the same shape `sq tree` and `sq blocked` have always had.
- **ADR-422's local-versus-non-local asymmetry is narrowed, not overturned.** Its ruling stands and
  is reinforced: no persisted per-item derived region. What is corrected is its factual premise about
  `:head`, and the conclusion it drew for option C now applies to the region it used as its baseline.

## Amendment note — 2026-08-26: what field codes a `ref` source may project

§1 settled the three source kinds and §2 settled the one uniform record shape. Neither said
which **field codes** a source may name. The loader answered it by construction — an empty
declared-field set for a `ref` source, so base attributes only — and that answer is stricter
than either section requires. Ruled here; §1 and §2 stand as written except where §4 below
narrows the message that carries the remaining refusal.

Driven on scratch squads at 0.14.0: a bundled squad with a milestone holding a feature, a task,
a decision and two bugs on `targets` edges, and a second squad whose override declares an
`impact` collection and field on `feature` alone.

### 1. A `ref` source may name a field code at least one declared item type carries

A code **no** declared item type carries stays refused. A code **some** declared item type
carries is accepted, and renders `null` for a record whose type does not carry it.

The governing clause is the one `_check_views` already states for the source axis: a source
that can never resolve is refused rather than carried as an inert declaration. On the field
axis that reads the same way. A code no type declares can never resolve for any record, on any
corpus — inert by construction, refuse. A code some type declares resolves for every record of
that type — not inert, permit. The current refusal is not that clause but a proxy for it, and
the proxy mistakes *no single type the records all share* for *no type at all*.

That the resolver tolerates the declaration is **not** the reason. Driven: a `ref`-source
projection of `wibble`, a code no type declares anywhere, also produces a clean uniform payload
with a `null` cell on every record. The resolver tolerates the typo exactly as gracefully as it
tolerates the useful case, because `resolve_collection`'s same-name fallback is documented as
rendering-only robustness. "The mechanism copes" therefore licenses nothing; it would license
everything, the typo included. What decides the question is whether the declaration can ever
mean anything, and that is a property of the spec.

**Scope of the criterion, stated because each edge was checked rather than assumed.**

- **Item types only, never sub-entity kinds.** A `ref` source's records are always items
  (`_record_from_item`); only a `subentity` source yields sub-entities. A code declared solely
  by a sub-entity kind can never resolve for a `ref` record and stays refused.
- **Every declared item type, roster types included.** `field_badge_codes` answers a
  neighbouring cross-type question over `non_roster_types()` only, and that precedent does not
  transfer: it backs a filter door over work items, whereas a `ref` source's records may
  legitimately be roster items — a skill carries a forward edge to the role that preloads it,
  so a view over that kind projects `skill` records. Excluding roster types would refuse an
  adopter's field on `role` while it resolves perfectly.
- **The catalog, not the reachable set.** A ref kind types only its *target* end
  (`RefRule.target`), and only for kinds that declare one, so which types can appear as records
  of a given ref-kind source is not derivable at load. The narrowing therefore buys "this code
  means something in this spec", not "this code means something for these records". The
  stronger guarantee would require typing the source end of every ref kind — a vocabulary
  change nothing here is asking for, and disproportionate to the failure it would catch.
- **A property of the spec, never of the corpus.** The same declaration is accepted or refused
  identically in an empty squad and a full one. A ref-kind source whose members happen to carry
  none of the projected code renders an all-null column; nothing refuses that and nothing
  should, because one member of a carrying type joining tomorrow makes it interesting.

### 2. The payload contract does not change: there is one absence, not two

A field that is `null` because the record's type cannot carry one and a field that is `null`
because it is unset mean the **same thing to a consumer**, and the payload does not distinguish
them.

That identity is by construction and predates views. `Item.badge_value` reads the stored value
with no spec in hand — the stored code is the authoritative value — while the write gate refuses
a value for a field the type does not declare (driven: setting `severity` on a feature is
refused, "not a settable field on a feature"). There is therefore no state in which "cannot
carry one" and "carries none" differ as facts about a record. Driven, in a single projection
over one milestone's members: a feature that cannot carry `severity` and a bug that declares
`severity` and has none set are byte-identical `null`.

The question that *is* different — could a record of this type ever carry one — is a question
about the spec, not about the record, and it is already answerable from the payload: `type` is a
base attribute of every `ref` source, so a view needing the distinction declares one more column
and joins it against the spec. That costs the author a field and the contract nothing.

Encoding it in the payload instead is refused. §2's shape is field metadata **once per
projection** with records identically shaped; a per-record marker would make two records of one
view differently shaped, which is the precise property that lets a client consume a view it has
never seen. `ViewFieldMeta.type` stays `badge` for such a column and a null cell keeps rendering
as empty text, so no presentation template changes and `--json` gains no key.

### 3. `subtree` and `subentity` sources are unaffected — they are not heterogeneous

The heterogeneity is a `ref`-source property alone. Driven: a subtree source filters descendants
to `source.name`'s own type, so every record it yields is of exactly that one type; a subentity
source yields one declared kind. Their declared-field sets are already exactly right, neither
over- nor under-refusing, and a `subtree`-over-`task` view naming `severity` stays refused. This
amendment touches neither, and a fix that generalises across all three source kinds has
misidentified the defect.

### 4. The refusal that remains must name a remedy the author can perform

The current message names two things the code is not, and for a `ref` source the second is
unperformable: "nor a field `<ref-kind>` declares" asks the author to make a ref kind declare a
field, which no spec grammar expresses. Driven, the accompanying fix hint compounds it — an
override declaring `impact` on `feature` alone is told to add the key back directly or through
`selected`, a key it has just written.

The remaining refusal must say what is actually wrong: name the view and the code, state that no
declared item type declares it, and give the two remedies that exist — declare the field on a
type, or name a base attribute, listing the ones this source kind allows. The
"nor a field `<source-name>` declares" clause does not follow the code into the `ref` branch;
`subtree` and `subentity` keep it, where it names a type or kind that can genuinely declare one.

## Amendment note — 2026-09-01: the head badge line retires with no successor

§5 ruled the head "computed" and §6 said both projections are reissued as computed views. Driven
against the mechanism that has since shipped, one of those two reissues has no work in it. Ruled
here; §5's verdict on the head stands, and §6 narrows to one view rather than two.

Driven on a scratch squad at 0.14.0: a feature with a story, a task with two subtasks (one mapped
to the story and assigned to `architect`), a review with a `critical` finding assigned the same
way, and an override declaring a `subentity`-source view over each kind, attached through
`items.<type>.views` and presented through an override template.

### 1. The head's lines have three different answers, and only one is a gap

The materialised region beside the closest a declared view can come — driven, one finding, both
rendered from the same state:

| head line | materialised region | shipped `[views]` projection |
| --- | --- | --- |
| `**Status:** 🔴 Open` | the status badge | `Open` — the bare status name |
| `**Assignee:** Robert Architect` | the ROLE item's display name | `architect` — the stored slug |
| `**Severity:** 🔴 Critical` | the declared field's badge | `🔴 Critical` — identical |

The severity line already projects exactly, because it is a declared badge field and the mechanism
was built for those. The status line fails for a reason that is neither of the two gaps FEAT-694
names: `status` is a base attribute, its resolver returns the stored name, and `project` types every
base code `text`, so **no view — bundled or adopter-declared — can render a status badge at all**,
and one that declared a `status` field would still be answered by the base resolver. That is a
property of §2's record shape rather than an oversight: `status_role` travels beside `status`
precisely so a client styles the axis itself instead of consuming a pre-styled string. Only the
assignee and story lines fail on the two foreign hops.

Also driven: `sq workflow view <name> <ID>` resolves against an item id (`TASK-10:ST1` and `ST1`
both answer "no item … in the index"), and a `subentity` source yields the whole collection — two
subtasks, two renderings, no selector.

### 2. What the region carried beyond the computed line is exactly its defect

`_subentity_badge_line` is the head, computed, and it already ships. Driven: `sq review 11 show
--full` prints the pane title `=== F1 — Something wrong  🔴 Open  🔴 Critical  architect ===` —
the same status badge, the same declared-field badge, the same fields, in one line — and never
prints the region's text. It reads the assignee as a slug and the mapped story as a local id, both
off the sub-entity's own frontmatter.

So the delta between that line and the region is precisely the two foreign resolutions, and those
are not a capability being carried forward. They are the fact Context measured in order to condemn
the region: the display name and the story title are read out of other files, they go stale on a
rename, and no verb heals them. §5's finding for the head is "foreign-sourced in fact, stale in
fact, and read by nothing" — three clauses, and a successor that resolved them fresh would satisfy
the first two while contradicting the third. It would be a rendering built for no reader: the
migration removes the one reader the region ever had (a person opening the raw file), and Context's
enumeration of non-human readers leaves no other.

### 3. Ruled

**The head badge line has no successor.** Neither a widened `[views]` entry nor a bespoke computed
renderer beside the general mechanism. The region retires, the write path that maintained it
retires, and nothing is written in its place; the computed rendering of a sub-entity's badges is
the one that already ships, frozen byte-identical by the same acceptance clause that freezes the
other three.

This is not the bespoke option under a new name. The bespoke option builds a renderer; this builds
nothing. The shape §1 exists to remove is a second general mechanism standing beside the first, and
after this ruling there is no second mechanism — one declared view for the roll-up, one deletion
for the head.

### 4. §6 narrows, and to what

§6's "reissue both projections as computed views" over-counted. The roll-up is one projection and
becomes one declared view, which buys what a hand-rolled renderer cannot: an adopter re-presents it
through `templates/views/<name>.md.j2` and drops it through `[selected]`. The head was never a
second projection needing reissue — it was a second *materialisation* of fields whose computed
rendering already existed. §6's remaining clauses stand unchanged: the subject still inverts, the
acceptance bar is still every computed rendering byte-identical rather than the regions' own bytes,
and the migration is still owed.

### 5. Why the widening is refused, stated so it is not re-proposed cheaply

Single-record addressing alone would not breach §2 — one record is a one-record group, and a
selector on the source axis leaves the payload shape untouched. The whole cost sits in the second
half, cross-item field resolution, and it is not affordable for a consumer that does not exist:

- **A field code stops being answerable from the declaration.** Today every code resolves off the
  record or off the spec, so what a code means is a property of the merged spec, decidable at load.
  A hop resolves off a *joined* item, so its meaning depends on the record's context — which item
  hosts it, whether its parent resolves, whether the target exists.
- **It reopens the absence contract the 2026-08-26 amendment closed.** That amendment ruled there
  is one absence and not two, and refused a per-record marker distinguishing them, because
  identically shaped records are what let a client consume an unfamiliar view. A hop introduces a
  third absence — the join target missing or dangling — which under that ruling must also render
  `null`, making a dangling role reference indistinguishable from an unassigned sub-entity. That is
  the class of silent wrongness this decision exists to remove, reintroduced one layer down.
- **It reopens the refusal criterion the same amendment settled.** That criterion refuses a code no
  declared item type carries. A hop code names a traversal rather than a declared field, so there is
  nothing in the catalog to check it against and the load-time pass that refuses an inert
  declaration would have no clause to apply.
- **The adopter test fails at the narrow end.** A fixed `assignee_name` code, meaningful only
  because the bundled spec happens to declare a `role` type, is a bespoke renderer wearing a
  declaration. Passing the test needs a declared join grammar — a source-side traversal an adopter
  writes over their own types and ref kinds — a vocabulary addition on the scale of the source axis
  itself. Worth designing when a view genuinely wants it; not worth designing for a rendering being
  deleted.

### 6. What this does not settle

If resolved labels are later wanted by an actual reader — a full name in the pane title rather than
a slug — that is a change to `_subentity_badge_line`, ruled on its own merits against that named
consumer. It is out of FEAT-694's scope by that feature's own acceptance, which freezes those
bytes. Nothing here forbids it and nothing here schedules it.

### 7. Two corrections the driving turned up, owed to the breakdown

- **The head renderer cannot simply be deleted; it is pinned by a frozen migration runner.**
  `_migrations/_v0_2_to_v0_3.py` calls `discussion.set_head` to render the region it creates when
  lifting legacy `:meta` blocks, so both that function and `templates/subentities/head.md.j2` stay
  reachable while a squad can still replay from 0.2 (the later runner then strips what it wrote —
  wasteful across a full replay, and correct). What retires from the live write path is the
  refresh-on-mutation obligation; the historical renderer either stays as migration-only machinery
  next to the rest of the legacy-body handling it serves, or is inlined into its one caller. Either
  way "`set_head` is deleted" is not literally achievable as stated.
- **The roll-up half is unaffected in substance, with one non-equivalence its story asserts away.**
  The `subentity` source resolves the roll-up's data exactly, because that region was always local
  (driven: `| ST1 | Todo | architect | Do the thing | US1 |`). But routing the shipped renderings
  through the new view's projection is claimed to be no behaviour change in either direction, and
  driven it is one: a declared badge field projects through `badge_parts` and renders emoji +
  **label** (`🔴 Critical`), while the existing row derivation renders emoji + **code**
  (`🔴 critical`). Sharing the projection therefore changes the summary table's bytes, which the
  first acceptance clause forbids. Either the shipped renderings keep their own derivation, or the
  projection's badge text is reconciled with the row derivation's in the same change.

## Amendment note — 2026-09-01: no generated item body survives, and the reader test that draws the line

§4 collapsed the sink by enumerating every non-human reader of item markdown. That enumeration
asked what reads a *derived region of a work item*; it never asked what a **roster item's whole
body** is. Operator direction (recorded in this decision's discussion, in his own words) settles the
general rule: the markdown files are the storage, the only read surface is the CLI, and anything
materialised into a file that the CLI can compute is duplication and comes out. Ruled here: what
falls under it, what does not, why the views mechanism is not the vehicle, and what the file holds
afterwards. §1–§7 stand; §4's enumeration gains a row and §5 gains two consumers.

### 1. Driven: the role item's `extra` is a mirror, and staleness is the milder half of its defect

Driven on a scratch squad at 0.14.0 — eight bundled roles, one custom role declared through
`.overrides/roles/security-analyst.toml`, and a catalog-document override at `.overrides/roles.toml`.

- **One command, two answers.** With `.overrides/roles.toml` declaring a new `mission` and
  `responsibilities` for `architect`, `sq role architect show` printed the override in its computed
  card and the pre-override text in the stored body immediately beneath it, in the same output.
  `sq check` exited 0. A `sq sync` heals it; nothing reports it in the meantime, and nothing marks
  which half is authoritative.
- **The mirror overwrites operator-set state.** `sq role qa set-default` reported success and moved
  `is_default` in both role files; the next `sq sync` moved it back to the bundled default, with
  `sq check` at exit 0 on both sides. `is_default` is operator-settable through a shipped verb
  (`_services/_roster.py:158-214`) *and* a member of `RoleDef._EXTRA_FIELD_KEYS`
  (`_roles/_catalog.py:78`), so the reconciler restores the catalog's answer over the operator's.
  That is the mirror's defect in its purest form: a stored copy of derivable data cannot tell a
  value it should refresh from a value it must preserve, so it refreshes both.

**And the asymmetry the mirror is usually defended by does not exist.** The expectation is that a
role's mission is *stored role data* for a custom role and a *catalog mirror* for a predefined one —
the same field with two provenances. Driven, it is not: editing `mission` in
`.overrides/roles/security-analyst.toml` changed the card for that wholly custom, activated role on
the very next command, with the stored body still reading the old text. A custom role's definition
is a document too. There is no role whose definition the item stores; the item stores the
operator-settable set and mirrors the rest.

### 2. What is in class, exhaustively — and the discriminator for each already ships

**(a) The role item body: the whole `sq:body` region, not selected sections.** `set_body` refuses a
role body outright (read: `_services/_items.py:533-548`), there is no `sq role <n> body` or
`comment` verb (driven: both are "No such command"), and `sq sync` re-renders the region wholesale
for every roster role, live or retired (read: `_services/_maintenance.py:638`). No byte of it is
authored. Every section is derived: the `# <full name>` heading and the `**Role:** / **Slug:**` line
from the resolved definition, `## Mission` and `## Responsibilities` from the catalog, `## Skills`
from the resolver (already ruled computed by §5), and `## Working agreements` — including the
spawned-as-a-subagent and live-with-the-operator blocks — from the bundled template with `full_name`
and `slug` substituted. Nothing is left over, so the ruling is the region, not a section list.

**(b) Every system (template-owned) skill body.** Same shape one document over: a `sq-<type>` body
renders the type's lifecycle from the workflow spec and its per-role Enter/Do/Hand-off/Watch-for
block from the playbook's types table, with role display names joined from the roster. The
discriminator is `is_system_skill(slug, spec)` (read: `_interactions/__init__.py:551-571`) — a pure
function of the slug and the active spec, already used by `set_body` to refuse exactly these writes,
and already surfaced as `kind: system (template-owned)` by `sq skill <slug> show`. Driven:
corrupting a heading in a `sq-<type>` body and running `sq sync` restored it byte-for-byte.

**(c) A custom (author-defined) skill body is storage and stays.** Driven: `sq skill my-custom body`
was admitted, and the text survived `sq sync` untouched. This is the two-provenance asymmetry, and
it is real for skills and false for roles. **It is also live in this repository's own corpus.** Of
the 23 generated-looking roster files here — 10 role bodies (37.5 KB) and 13 skill bodies (63.3 KB) —
exactly 22 are in class; `releasing-squads` (10.1 KB) is `kind: custom (authored)` and must not be
touched. A migration keyed on the folder, the type, or the `sq-` prefix destroys it. Key on
`is_system_skill`.

**(d) The role item's `extra`, key by key.** Retained, because each is stored data no document
answers: `slug` (the dispatch identity, frozen non-renamable by ADR-85 §4); `full_name`
(operator-settable through `sq role activate --name` / `sq dev add --name`, and the value
`role_base_from_item` swaps into the resolver's base — driven: a `full_name` declared in
`.overrides/roles.toml` for an activated role is deliberately shadowed by the item's own);
`is_default` (operator-settable through `sq role set-default`, and it must **leave**
`RoleDef._EXTRA_FIELD_KEYS` or §1's revert survives the shrink); and `is_dev` / `tech` / a dev's
`model` (the developer identity `dev_base_from_item` reads off the item).

Removed, because each is a copy of a catalog answer: `title`, `mission`, `responsibilities`,
`agreements`, `color`, `can_spawn`, `description`, and `skills` (already scoped by §5). For a
bundled role, `model` joins them; the key stays in the schema because a dev role's `model` is
operator-settable, so the reconciler stops *writing* it for a non-dev role rather than the key
being dropped from the vocabulary.

### 3. `title` and `description` stay: they are the uniform record, not the mirror

`RoleDef._ITEM_FIELD_PROJECTION` writes the resolved `full_name` onto `item.title` and the resolved
`mission` onto `item.description` (read: `_roles/_catalog.py:104-110`). Both are derivable, and both
stay — for a reason the general rule does not supply on its own, so it is stated here.

**The test is the reader, not the value.** `title` and `description` are read by surfaces that do
not know the item is a role and therefore cannot resolve a role catalog: `sq list`, `sq tree`,
`sq search`, every `--json` payload, the index, and the VS Code client all consume the uniform
record. Driven: `sq list --type role --json` returns `title` and `description` in exactly the shape
it returns them for a task. The body's sections have one reader, `sq role <slug> show`, which
resolves the catalog on that same call and can therefore compute what it needs. That is ADR-781's
clause 2 applied to a CLI reader instead of a host: materialise only where the reader cannot obtain
the effect for itself. Dropping `description` here would also reopen the absence contract the
2026-08-26 amendment closed, by inventing a third `null` meaning "resolvable elsewhere".

One duplication inside that pair is real and resolves the other way: `item.title` and
`extra.full_name` hold the same string twice in one file. Keep `item.title` — the generic field the
type-agnostic surfaces read — and let `role_base_from_item` take the operator-settable name from it.
That is the one place in this ruling where a wrong answer either leaves duplication behind or breaks
`sq list`, and the answer is: keep the top-level field, drop the `extra` copy.

### 4. The views fork: views stay for item relations; a definition renders through its resolver

The direction says views are the way to present derived content, and §1's mechanism cannot express
either body. Ruled: **the source axis does not widen, and these compute at show time.** Four reasons,
each a property of the mechanism as built rather than of the calendar.

- **Every source kind is a relation *of one item*.** `ref` inverts stored forward edges pointing at
  it, `subentity` reads its own collection, `subtree` walks its descendants (read:
  `_workflow/_models.py:644-666`), and a view resolves against an item id (driven in the 2026-09-01
  amendment above). A skill body is a projection of the playbook keyed by **item type**; a role body
  is a projection of the catalog keyed by **slug**. In neither is the item at the source end — it is
  only the addressee. There is no relation to invert.
- **The record shape would have to stop being a record.** `VIEW_BASE_FIELDS_BY_SOURCE` is
  `id/type/status/status_role/settled/delivered/assignee/title/story` — every one a work item's
  lifecycle position. A playbook guidance row is none of them. Widening to carry it means records
  that are no longer identically shaped across sources, which is the exact property §2 says lets a
  client consume a view it has never seen, and which the 2026-08-26 amendment refused to weaken for
  a far cheaper gain than this one.
- **The load-time referential check would have nothing to check against.** It works because
  `source.name` names a declared entry of `[ref_kinds]`, `[subentity_kinds]` or `[items]` and every
  field code resolves off the record or off the merged workflow spec's collections — decidable at
  load. A spec-derived source's field codes would name rows of a *second document* with its own
  loader, so the pass that refuses an inert declaration would have no clause to apply. That is the
  2026-09-01 amendment §5 objection ("a field code stops being answerable from the declaration") one
  level larger: a cross-document source rather than a cross-item join.
- **It would be a second general mechanism wearing the first's name.** New record shape, new field
  vocabulary, a second document's referential pass, and a new addressing model (resolved against a
  type or a slug, not an item). §3 of the 2026-09-01 amendment already named that shape as the thing
  §1 exists to remove.

**So what the rule means, stated so the next reader is not told one thing by the direction and
another by the code.** The rule is *nothing materialised that the CLI can compute*. The mechanism by
which the CLI computes is per surface. **Views are the way to present a derived projection over an
item relation** — a set of related records with a uniform shape and a template over them. A role's
or a skill's definition is not a projection over relations; it is one document rendered for one
addressee, and its computed home is the resolver that already renders it. Both surfaces already have
that resolver, and this is why the deletion half is a call-site move rather than new machinery:
`_regen_role_body` already renders `agents/role.md.j2` (`_services/_base.py:1347-1360`), and the
Claude backend already renders `agents/item_skill.md.j2` and its siblings
(`_backends/_claude_code/_backend.py:115-143`, `:324`, `:353`). The change is to call the same
render at show time instead of at sync time and stop storing the result. One substitution rides
with it and must not be missed: `_regen_role_body` renders from `item.extra` — the mirror — so at
show time the context becomes the resolved `RoleDef` from
`resolve_role_with_base(slug, squad_dir, base=role_base_from_item(item, squad_dir))`. Same template,
same engine, an authoritative context instead of a stored copy of one.

If a genuine consumer later wants an adopter-declarable spec-derived view, that is a source-axis
design on the scale of the axis itself, ruled on its own merits against that named consumer. Nothing
here forbids it and nothing here schedules it.

### 5. What ADR-781 §4 does not repeal, stated because it is exactly what gets collapsed under time

**The compiled managed regions (`CLAUDE.md` / `AGENTS.md`) and the backend pointers stay
materialised, unchanged by this amendment.** Their reader is an agent host that discovers and
configures an entry by reading a file, before any agent exists to run a command; a runtime fetch
cannot substitute for a configuration that has already taken hold. That is the whole of the
distinction, and it is the reader, not the directory: role and skill bodies sit next to the pointers
and go the other way precisely because `sq` is in their delivery path — the pointer names
`sq role <slug> show` / `sq skill <slug> show` rather than an `@` path. The containment rule in
ADR-781 §2a and the invariant-5 wording in ADR-781 §4 govern pointer contents; this rule never did
and does not now.

### 6. What the files contain afterwards

- **A role item file:** frontmatter (the retained `extra` of §2d plus `title`, `description`,
  `status`, ids and timestamps), the static `## Discussion` heading, and an empty `sq:discussion`
  region. The `sq:body` region is emptied by the migration and stops being written. It keeps its
  markers rather than being deleted: `role_body()`'s absent-region branch is what `sq role show`
  renders as "no active item for this slug", so a removed region would print a false and alarming
  message, and the marker pair is the shape every item file shares if a body verb is ever added.
- **A system skill item file:** frontmatter plus an emptied `sq:body` region. These carry no
  discussion region today and gain none.
- **A custom skill item file:** unchanged.
- **`sq role <slug> show` and `sq skill <slug> show`** render the definition from the resolver on
  every call, so the file's shrinking costs the agent nothing: the surface ADR-781 made an agent's
  primary definition read gets the same text, resolved rather than recalled.

The files still have a reason to exist: they carry the operator-settable state, the identity, the
status and the id, and under invariant 1 they remain the source of truth for exactly that.

### 7. Findings the breakdown needs before the build, not during it

- **Marker safety holds, and the reason is stronger than "the machinery is careful".** Driven: the
  only content outside a marker region in a role file is the frontmatter and the literal
  `## Discussion` heading — static template chrome carrying no derived data. Every derived byte is
  inside `sq:body`, one region, one `replace_section` call. And the region is already rewritten
  wholesale on every sync, so emptying it cannot destroy authored content that the shipped write
  path was not already destroying. The authored-content risk is not inside the region; it is
  **choosing the wrong files**, which §2c answers with `is_system_skill`.
- **`_without_permitted_extra_skew` identifies a role by `extra.mission`** — documented in place as
  "the one key only a role's own `RoleDef.to_extra()` merge ever writes" (read:
  `_itemfile.py:113-119`). §2d removes that key, so the discriminator disappears and every non-dev
  role silently loses its skew exemption. The predicate must move to a key the shrink retains
  (`extra.slug` on a role item, or the item's type) in the same change.
- **`sq check`'s pointer-currency comparison renders its expectation from
  `RoleDef.from_extra(item.extra)`** (read: `_services/_validators.py:761`). After the shrink that
  expectation would be built from the mirror the shrink removes, so ADR-781 §2c's currency guarantee
  is void unless the expectation is resolved through
  `resolve_role_with_base(slug, squad_dir, base=role_base_from_item(item, squad_dir))`. The same
  substitution is owed at the three other `from_extra` call sites
  (`_services/_base.py:1403`, `:1454`, `_services/_items.py:481`); `RoleDef.from_extra` is the
  mirror's reader and retires with it.
- **`PERMITTED_EXTRA_SKEW` narrows to near-empty, and one test pins it as a literal**
  (`tests/unit/test_role_def_extra_keys.py`), for the reason §5's consequences already state for the
  `X.SKILLS` case alone: it exists to catch an unreviewed widening. Narrowing is the safe direction;
  the test moves in the same change with its docstring stating why.
- **`sq search` narrows further than §5's consequences anticipated.** Driven: a query for a role's
  responsibility text matches that role item today, because search scans every body line; the
  mission matches by the same path. After the shrink neither does. The remedy is `sq role list` / `sq role catalog` / `sq role <slug> show`, all of
  which answer from the resolver rather than from a text match over a value that could be stale.
- **The release ordering is ADR-781 §6's, unchanged.** This touches `agents/role.md.j2` and the
  skill templates' rendering path, so it queues behind the same version bump before the template
  manifest is regenerated, and moves with the managed-section golden and the generated-agent-text
  guards.

## Amendment note — 2026-09-01 (second): where the read-time producer lives, and the order the substitution lands in

The note above ruled that both bodies compute at show time "through the resolver each surface
already has". That was true for the role body and imprecise for the skill body, whose producer is
inside a backend and therefore unreachable by `sq skill <slug> show` under invariant 6. Ruled here:
the producer's home, three consumer sites the note's §7 list misses, and the order the substitution
has to land in. Everything above stands; §7 gains three entries.

### 1. The home is decided by the import graph, and it refuses both scoped options

`_rendering/_engine.py:25` imports `squads._interactions`, and `_interactions/__init__.py:35`
imports `squads._roles._catalog`. The rendering engine therefore sits **above** both packages, and
neither may import it without creating a cycle — the acyclic-graph rule this project verifies.
Driven on the tree: neither package imports `_rendering` today, and the reason is structural rather
than incidental.

That refuses the placement the symmetry argument wants — each definition rendered by the package
that owns its document, a role's by `_roles/` and a skill's by `_interactions/`. It is recorded here
because it is the attractive answer and it will be re-proposed otherwise.

**Ruled: both producers live on `ServiceCore` (`_services/_base.py`), as
`role_definition_text(slug)` and `skill_definition_text(slug)`.** Three reasons, in order of force:

- **It is the only layer that can host them.** `_rendering` is below `_services`, so a service may
  call `render`; `ServiceCore` already does, in `_regen_role_body` (`_services/_base.py:1293`).
- **A core consumer needs it.** `roster()`/`roster_all()` (`:1089`, `:1110`) are themselves
  substitution sites (§2), and they live in the core. The concern mixins compose into `Service`;
  they do not import one another, so a producer any core method needs cannot sit in a sibling
  mixin. A new `_definitions.py` mixin would be a cleaner-looking name and an unreachable one.
- **The role half does not move at all — it inverts.** `_regen_role_body` already renders
  `agents/role.md.j2` in this exact place. It becomes a read-time producer taking the resolved
  `RoleDef` as its context, and its write-time caller in the sync sweep is deleted. Putting the
  skill half anywhere else would split one ruling across two layers for no gain.

**Invariant 6 is satisfied by direction, not by exemption.** The service produces the text and the
backend consumes nothing: `_write_managed_skill` loses its `body` parameter, and the five `render`
calls that feed it — three in `write_managed`, two in `_write_item_skills` — move with it. Nothing
reaches into `.claude/`, and the backend keeps its own pointer render, which needs only slug and
description. There is exactly one producer to move and, after the move, one consumer:
`sq skill <slug> show`. The `agents_md` backend writes no skill body, so it is untouched.

### 2. Three more substitution sites; two of them fail silently, and the silent pair is the worst path in this work

**`roster()` / `roster_all()` (`_services/_base.py:1089-1132`) build every `RoleView` off the
mirror, and that view is what `write_managed` compiles `CLAUDE.md`, `AGENTS.md` and the pointers
from — the files §5 above deliberately keeps materialised.** It is not a `from_extra` call, so §7's
list missed it. Its per-field fallbacks decide the failure mode, and the split is exactly the one §3
predicts:

| `RoleView` field | fallback when the key is gone | outcome |
| --- | --- | --- |
| `full_name` | `it.title` | correct — `title` carries the resolved full name (§3) |
| `mission` | `it.description` | correct — `description` carries the resolved mission (§3) |
| `is_default` | key retained (§2d) | correct |
| `title` (the role title) | `it.title` | **wrong, silently** — the role's title becomes the person's name |
| `responsibilities` | `()` | **empty, silently** |

So §3's ruling is what saves three of the five, and **the degradation set is precisely the fields
with no uniform-record home**. That is the sharpest statement of why §3 draws its line where it
does, and it is also why this site outranks the rest: it degrades without raising, into generated
agent configuration, on the one path this decision deliberately leaves materialised.

**`dev_base_from_item` (`_roles/_resolver.py:355`) reads `item.extra[X.FULL_NAME]` as a bare
subscript and raises rather than degrading.** §7 named only `role_base_from_item`. Both take the
name from `item.title` instead; this one is the loud failure and therefore the cheap one.

**The migration runner's frozen local copy (`_migrations/_v0_11_to_v0_14.py:136-176`) must not be
taught to resolve.** Its own docstring records why it is local — `_services` imports the migration
registry, so calling `Service` from a runner would be a real cycle — and the general rule stands
above that: a runner is frozen against the corpus vocabulary of the version it transforms, and that
corpus still carries the mirror. Leave it reading `extra`.

### 3. The order, stated as three stages and one prohibition

- **Stage 1 — every consumer resolves, while the mirror is still written.** `roster`/`roster_all`,
  the four `from_extra` sites, `dev_base_from_item`, `role_base_from_item`, and
  `_without_permitted_extra_skew`'s `extra.mission` discriminator. Its falsifiable property: with
  the roster held constant, regenerate every managed file before and after and diff to zero —
  except where the mirror was already wrong, which is where the fix shows rather than where a
  regression would. **This stage is separately shippable and separately valuable:** on its own it
  ends the `set-default` revert and the pre-sync card/body disagreement, with no corpus change and
  no migration.
- **Stage 2 — the producers invert.** `sq role show` / `sq skill show` render at read time;
  `_regen_role_body` and the backend's body renders are deleted; the card drops `mission` and
  `responsibilities` (ADR-781's 2026-09-01 amendment §2).
- **Stage 3 — stop writing, then strip.** The keys leave `RoleDef.to_extra()`,
  `PERMITTED_EXTRA_SKEW` and its literal test narrow, and only then does the runner empty the
  regions and delete the key set from the corpus.

**The prohibition, because it is an ordering to not break rather than one to engineer.** The strip
runner must sit **later in the registry than every runner that regenerates surfaces, and must
regenerate none itself.** The registry's ordering then gives the right result on a full replay for
free: `_v0_11_to_v0_14._regenerate_surface` runs against a corpus that still carries the mirror it
reads, and the strip runs after it. And `sq migrate up` never syncs — it returns "run `sq sync` to
refresh managed files" (read: `_cli/_migrate.py:50`) — so the live surfaces are rebuilt afterwards
by the resolver-fed code Stage 1 has already landed.

## Amendment note — 2026-09-01 (third): the roll-up ships no bundled view either

The first 2026-09-01 amendment narrowed §6 from two reissues to one and left the roll-up's reissue
standing as a declared view. Driven against the shipped mechanism, that one view has no reader and
one real cost. Ruled here: **squads ships no bundled sub-entity roll-up view.** §5's "computed"
verdict on the roll-up stands and is already satisfied; §6's "reissue as computed views" is met for
the summary half by a rendering that shipped before this work began.

### 1. Driven: the bundled declaration bricks an ordinary customisation

Three freestanding views over the bundled sub-entity kinds — one each for `story`, `subtask` and
`finding`, field-for-field matching `discussion.summary_columns` — driven against a scratch squad at
0.14.0 carrying a feature, a task and a review with one sub-entity apiece.

An override doing nothing but `[subentity_kinds.finding] fields = []` — shadowing a bundled kind's
field list, an ordinary supported customisation with its own test — makes **every** command in that
squad fail:

```
error: this squad's workflow override could not be loaded, so no command can answer
with the vocabulary it declares.
  cause: view 'finding_rollup': field 'severity' is neither a base attribute for a
  'subentity' source nor a field 'finding' declares
```

Not the view — `sq list`, `sq show` and `sq check` alike, because the spec does not load. The second
axis behaves the same: `[selected].subentity_kinds` dropping or replacing `finding` fails with
"source names sub-entity kind 'finding', not declared". Fifteen tests in the suite exercise exactly
those two customisations; all fifteen fail with the declarations present and pass with them removed.

Neither axis is reachable by the pruner. `_prune_orphaned_type_owned_views` keys off
`[selected].items` and takes only a view a *dropped type's own* `views` list named, so it reaches
neither a freestanding view nor a sub-entity-kind or field deselection. Attaching the views through
`items.<type>.views` does not change that: driven, the field drop still bricks the squad, and the
attachment additionally makes `sq <type> <n> show` print the same table twice, because
`_print_item_content` renders the built-in sub-entity table and then every attached view.

### 2. Driven: what the bundled view was said to buy, it does not buy

The first 2026-09-01 amendment justified keeping the roll-up's view on two capabilities a
hand-rolled renderer cannot give — re-presentation through `templates/views/<name>.md.j2`, and a
`[selected]` drop. Neither reaches the roll-up any reader sees.

- **Re-presentation.** An override at `.overrides/templates/views/finding_rollup.md.j2` renders
  through `sq workflow view finding_rollup <REV>` and changes nothing under `sq review <n> show`,
  which keeps printing its own table (driven, both in one session). The roll-up a reader gets is
  `_cli/_common.py::_print_subentity_summary` — a Rich table built from
  `discussion.summary_columns`/`summary_row`, called unconditionally for any item hosting
  sub-entities and rendered through no template at all. Re-presenting the view re-presents only the
  view.
- **The `[selected]` drop.** Dropping a view nothing reads removes nothing. It is not a capability
  the declaration buys; it is the un-brick step §1 forces on an adopter who edits their own
  vocabulary.

The only surface a freestanding roll-up view reaches is `sq workflow view <name> <ID>`, a generic
proof command carrying no specified consumer. The `--raw` dossier renders attached views only, and
the retired region never appeared there either: `read_body` returns the `:body` region and the
roll-up sat in its own.

### 3. Ruled

**The roll-up has no bundled declared successor.** No `[views]` entry over `story`, `subtask` or
`finding` ships — attached or freestanding — and no presentation template for one.

An adopter declaring a roll-up over their own sub-entity kinds is the ordinary case and is
untouched: §7's placement, the merge semantics and the load-time refusal all continue to serve it.
What retires is squads pre-declaring one over vocabulary the adopter is free to change.

### 4. §6 narrows again, and to what

§6's verb was "reissue", written when FEAT-694 was a conversion onto a body sink and the projection
therefore had to be rebuilt somewhere. It does not have to be. The computed rendering that satisfies
§4's sink rule existed before this work and is untouched by it, so for the summary half "reissue
both projections as computed views" is met by `_print_subentity_summary` and the renderings beside
it, and retiring the `:summary` region is a **deletion**, exactly as the head's is. The same two
clauses of §5's finding decide both: the computed rendering already ships, and the region is read by
nothing.

That the declared-view grammar *can* express the roll-up remains proven, and remains the mechanism's
adequacy bar. Expressing a shape is not a reason to ship an instance of it.

§6's remaining clauses stand unchanged: the subject still inverts, the acceptance bar is still every
computed rendering byte-identical rather than the regions' own bytes, and the corpus migration is
still owed.

### 5. The load-time refusal is not weakened, and why it did not have to be

The 2026-08-26 refusal stands entire. Two rescues were weighed against it and both fail:

- **Degrade rather than refuse** — render the view minus a field it can no longer resolve. That
  reopens the absence contract that amendment closed: a column absent because an adopter dropped the
  field becomes indistinguishable from a value absent on the record.
- **Prune the bundled view instead of refusing.** On the `[selected]` axis this is the pruner's
  existing courtesy and would be consistent. On the `fields` axis it is not a deselection at all but
  ordinary shadowing, so the trigger would have to be "a view names a code the merged spec no longer
  declares" — which is the refusal's own condition, and swallowing it silently would swallow an
  adopter's typo in their own view identically. Scoping the swallow to *bundled* views buys one
  grammar with two behaviours by provenance, which is the second-mechanism shape §1 exists to
  remove.

Both rescues spend real design to keep a rendering with no reader. The refusal is right; what was
wrong was shipping a declaration for it to fire on. That amendment's own criterion — a refusal must
name a remedy the author can perform — is what fails here in a new instance. The message names the
two remedies a view's author has (declare the field on the kind, or name a base attribute); the
adopter's actual remedy is a third one it never names, deleting a declaration they did not write.

### 6. `milestone_rollup` is unaffected, and the discriminator that separates the cases

`milestone_rollup` stays, and is not the same case on either clause.

- **It is the reader.** No built-in computed milestone roll-up exists; the declared view *is* the
  rendering, attached through `items.milestone.views` and printed by both `sq milestone <n> show`
  and the `--raw` dossier (driven: a task carrying a `targets` ref appears under Outstanding).
  Dropping it removes the only rendering of a milestone's membership.
- **Its coupling runs to its type's own mechanism, not to an orthogonal field.** Its eight fields
  are exactly the `ref` source's base attribute set, so no field or collection customisation can
  reach it. Its source names the `targets` ref kind, which exists for it — `items.milestone`'s own
  text states membership rides a `targets` ref and nothing else. Dropping the type takes the view
  with it through the pruner (driven). The one residual is dropping `targets` while keeping
  `milestone`, which the load-time refusal catches with an accurate message; that pair is an
  incoherent declaration rather than an ordinary customisation, and refusing it is what the refusal
  is for.

The discriminator, stated so it decides the next one rather than being re-derived: **a bundled view
earns its declaration when it is the only rendering of its data, and it is attached to the type that
shows it.** A bundled view standing beside a rendering that already ships is a second rendering of
computed data, paying the coupling cost of naming bundled vocabulary in exchange for nothing.

## Amendment note — 2026-09-01 (fourth): the corpus strip is a repair-side sweep, not a schema step

§6 ruled that a corpus migration is owed. The breakdown read "migration" as "a step inside the
release's runner", and driven, that vehicle reaches neither corpus the retirement stranded. Ruled
here: the corpus edit is still owed, and its mechanism is not a schema transition. §1–§7 stand;
§6's "a migration **is** owed" narrows to "a corpus sweep is owed", and nothing else moves.

### 1. Driven: who is stranded, and why it is not a one-off of this release

The write path retired ahead of the strip, so the regions sit in a corpus already stamped at the
target schema. The single record for this release declares `from_schema="0.11"`,
`to_schema="0.14"`, and this squad's index reads `0.14`: `sq migrate up` answers "already at
schema v0.14; nothing to migrate" and exits 0. There is no precondition left for the runner to
match, and none can be manufactured without asserting a format change that did not happen.

Measured on this corpus: **632 files carry a `sq:summary` region, and 436 files carry 1545
balanced `<kind>:<local-id>:head` regions.** Both halves are stranded, and both are already
wrong rather than merely vestigial — driven, one task file's `ST1` frontmatter reads `Cancelled`
and its `ST3` reads `Done`, while both stored head regions read `**Status:** ⚪ Todo`.

**A correction, recorded because a false number was about to narrow this ruling to half the
corpus.** A probe reported zero head regions on the ground that `_models/_markers.py` declares
`SUMMARY` and no `HEAD`. The premise is true and the conclusion does not follow: the head tag is
not declared there. `_discussion._head_tag` renders `<kind>:<local-id>:head` at write time, and
the regions are present, balanced and countable. Absence of a constant in one module is not
absence of a region in the corpus — the corpus is the thing to count.

**And the stranded class recurs with no release doing anything.** `adopt` over a folder carrying
no `.squads.toml` writes a fresh config whose `schema_version` defaults to the build's own
`SCHEMA_VERSION` (`_models/_config.py:23`) and then rebuilds from disk, so a pre-existing corpus
is stamped current with no runner ever visiting it. The stamp axis therefore cannot be the axis a
corpus sweep runs on. That is a property of how a squad can arrive at a stamp, not a consequence
of this release's staging, and it is what decides the vehicle.

### 2. Ruled: the sweep is a step in `repair`, and no registry entry ships

**The corpus strip is a sweep inside `Service.repair()`'s corpus walk. There is no second
`Migration` record, no `SCHEMA_VERSION` change, and no strip step inside any runner.**

Four reasons, in order of force.

- **It is the only walk that reaches both populations with one implementation.**
  `run_pending_migrations` runs the ordered runners, then calls `repair()`, then stamps
  (`_services/_maintenance.py:984-988`). So a squad at 0.11 or below gets the sweep on its way up
  with nothing declared for it, and a squad already stamped current gets it from the ordinary
  verb. One step, both ends of the gap, and no vehicle that has to be told which squad it is
  looking at.
- **The seam exists and already has this exact shape.** `_rebuild_index_from_disk` already
  rewrites file *content*, not only the index: every file whose on-disk ref encoding differs from
  what the fold produced is queued into `pending_canonicalization`, written after the
  corpus-alignment refusal check, markdown before the index commit, and reported back as
  `canonicalized` (`:1504-1520`, `:1593-1601`). The sweep is one more recorder in that same
  per-file loop, on that same deferred list, inheriting the idempotence the method already
  documents in place: a corpus needing no correction writes no file at all, and a second pass
  over a corrected corpus is byte-identical to the first.
- **The ordering prohibition stops being a rule and becomes a property.** The requirement that a
  strip never run ahead of a surface regeneration reading what it removes cannot be violated
  here. `require_current_schema` refuses every subcommand but `migrate` on a mismatched stamp
  (`_cli/_common.py:1237-1250`), so `sq repair` can only ever run against a corpus already at the
  current schema; the single call on a behind-schema corpus is the tail of
  `run_pending_migrations`, after every runner has finished. `_regenerate_surface` therefore
  always reads a mirror that is still there. What was a prohibition someone could break by
  tidying two adjacent lines inside `migrate()` is now a consequence of where the verb sits.
- **This is hygiene, and this decision already forbids calling it a format change.** A corpus
  carrying the retired regions must keep loading, showing and checking clean — that tolerance is
  what an un-migrated adopter file needs, and it is asserted against the frozen fixture. A stamp
  that separates two corpora which are both valid, read identically and check identically is not
  a schema version. The strip changes what a file *stores*; it does not change what the format
  *means*.

### 3. The rule that governs what the sweep may remove

Repair is not thereby a place to put content deletions. It may remove only a **named retired
region or key** — one for which, in this same build: no live write path produces it; no read path
consumes it as authoritative, its computed replacement having already shipped; and its content is
derived, never authored. The names are a frozen list. Adding to that list is a decision, not a
dev's choice, and a name may not be added before its writer retires.

The guard that keeps the list honest is falsifiable: for every name on it, a fresh squad driven
through the write path produces none of them — restore a writer and the assertion reddens. A name
added early does not merely leave dead bytes behind; it puts the sweep and the writer into a loop
where each undoes the other on alternate commands.

Emptying is removal under this rule: a role body and a system-skill body lose their contents and
keep their `sq:body` markers, for the reason the second 2026-09-01 note §6 already gives. The
sweep deletes no region that a live surface still reads as a shape.

### 4. The vehicles refused

- **A new registry entry behind a further schema bump.** It would stamp a difference that does
  not exist: both corpora load, render and check identically, which this decision requires. It
  also names a release that has not shipped, against the release-tracking convention
  `_models/_schema.py` documents, and it answers this instance while leaving the class — every
  future mid-release retirement would buy its own bump, and `adopt` would keep manufacturing
  corpora that no bump reaches.
- **A dedicated one-shot maintenance verb.** The population that needs it is exactly the
  population that does not know it needs it: the harm is a silent stale hit in `sq search`, and
  the announcement is a changelog line. A cleanup nobody runs is not delivered — and it would
  reimplement repair's corpus walk, its idempotence and its write ordering beside repair.
- **Relaxing the frozen-runner rule.** It reaches nobody in the gap, who are past every runner,
  and it trades a bounded cleanup for an unbounded cost: a runner whose behaviour changes after
  squads have run it makes "migrated" a claim with no fixed referent, and every replay assertion
  becomes a test of the current tree rather than of history.
- **The runner step plus a hand-rewound stamp for this repository.** Withdrawn. Editing
  `.squads.toml` and `.squads.json` back to `"0.11"` to make a runner fire is a procedure that
  inverts invariant 1's direction, cannot be handed to any adopter, and leaves the class unowned
  once this repository is clean.
- **The write path keeps the regions current while they exist.** It reinstates the
  refresh-on-mutation obligation §5 retired, for a region §5 found is read by nothing, and it
  makes the head's two foreign resolutions live again — the staleness this decision was written
  to remove, re-adopted in order to maintain what is being deleted.

### 5. The failure mode accepted

Named rather than mitigated away, because both are real.

- **`repair`'s advertised job is the index, and it now rewrites content.** An operator who runs it
  to reconcile an index gets a content diff they did not ask for; on this corpus that is over a
  thousand regions across 632 and 436 files. The answer is announcement, not prevention: the
  sweep reports the files it touched the way `canonicalized` already does, in the result and in
  the reflog delta, so the diff is stated rather than discovered. An adopter running `sq repair`
  over a dirty working tree cannot separate the sweep's changes from their own. That is the price
  of the sweep being unconditional, and the alternative — a flag — is the one-shot verb again
  under another name.
- **Nothing compels it.** A squad that neither migrates nor repairs keeps its stranded regions and
  keeps serving them to `sq search`. The read path tolerates them deliberately, so the sweep is
  available and free on the next maintenance pass rather than forced. A `sq check` rule reporting
  a region that disagrees with frontmatter is **not** ruled in here: it would fire on precisely
  the corpora the read path is required to tolerate, and its remedy already runs unconditionally
  on the next repair. If it is wanted for the window between a mutation and that repair, it is a
  separate decision against a named reader.

### 6. Adopter safety: unconditional, with no corpus precondition

- **A squad that never carried the regions is untouched.** The scan matches nothing, no file is
  written, and repair behaves byte-identically to today. This is not a new tolerance being
  claimed; it is the property `_rebuild_index_from_disk` already documents for canonicalization.
- **No authored content is reachable.** Marker regions are sq-managed, no verb writes an arbitrary
  marker, and `find_markers` is strict, so prose naming a tag inside backticks is not matched.
  The adopter-shaped case runs the other way and is a feature: a head region belonging to a
  sub-entity kind an adopter declared and later dropped is still removed, because the scan matches
  tag *shape* rather than a list of declared kinds.
- **The one real destruction risk is not a corpus condition, it is the discriminator.** A custom
  (authored) skill body must survive, and the folder, the item type and the `sq-` prefix each get
  it wrong. `is_system_skill(slug, spec)`, and nothing cheaper.
- **The cross-version hazard closes itself.** A squad swept by this build and then opened by an
  older `sq` is refused by that older build's own schema gate on the ahead-of-build branch, so no
  earlier binary ever reads a stripped file and mistakes an emptied body for a missing one.
- **The precondition that does exist is on the build, not on the squad** — §3's rule. It is
  checked once, when a name joins the list, by a guard that drives the write path; it is never a
  runtime gate on corpus state.

### 7. What this changes downstream, and what it leaves alone

- No `SCHEMA_VERSION` change, no version bump, no new `Migration` record, no new corpus fixture,
  no strip step in any runner.
- **The runner's docstring correction is withdrawn.** With the sweep in repair, "no existing item
  data is rewritten" stays true of the runner, and the registry `summary` line stays about the
  two new types. What is still owed is the adopter-facing `MANUAL` section, which must say the
  removal happens in the rebuild at the end of `sq migrate up` rather than attribute it to the
  runner — an adopter migrating from 0.11 does experience it, and the sentence has to be true
  about where.
- **The already-stamped population has no runbook path**, because `chlog` is keyed to a schema
  transition they will not perform. Their announcement is the release's changelog: `sq repair`
  removes the retired regions and the role mirror.
- **The frozen `v0_14` fixture stays frozen and its no-op assertion stands unchanged.**
  `run_pending_migrations` calls `repair()` only when a runner applied, so a corpus already at the
  current stamp still migrates to nothing and still carries its regions — which remains the right
  proof that the read path tolerates them.
- **This repository's own corpus is stripped by running `sq repair`**, reading the diff, and
  committing it. No stamp is rewound and no index is hand-edited.
- **One coupling the sweep introduces that a runner step did not.** The walk builds each index
  entry from the same frontmatter it rewrites, so a key the sweep removes from a file must also be
  removed from the `Item` before it is added to the rebuilt index — otherwise file and index
  disagree on exactly the key just deleted, and the skew guard is the only thing standing between
  that and a silent divergence.

## Amendment note — 2026-09-02 (fifth): §6's authored-content bullet cites the wrong guard

The fourth amendment's §6 second bullet reads:

> **No authored content is reachable.** Marker regions are sq-managed, no verb writes an arbitrary
> marker, and `find_markers` is strict, so prose naming a tag inside backticks is not matched.

The final clause is false, and the bullet's conclusion does not rest on it. Both halves are
corrected here rather than the conclusion being softened to fit the argument that was given.

### 1. Driven: backticks are not the discriminator, the `*` is

Tags below are written without their HTML-comment wrapper, because `reject_markers` refuses this
body otherwise — which is itself the point. Four probes on strings built at runtime, including a
control, so a null result cannot be mistaken for a working search:

- control, a bare well-formed `sq:summary` tag: `find_markers` returns `['sq:summary']`;
- the same tag wrapped in backticks: `['sq:summary']` — **identical**;
- the `sq:*` form wrapped in backticks: `[]`;
- the `sq:*` form with no backticks at all: `[]` — **also identical**.

`MARKER_RE` is `<!--\s*(sq:\w[\w:-]*)\s*-->`. Backticks sit outside the match and change nothing
in either direction. What saves the `sq:*` spelling is that `*` is not in `[\w:-]`. Prose is not a
category the regex can see; a well-formed tag in prose is matched exactly like one in a region.

### 2. The guard that actually holds the conclusion is `reject_markers`

`reject_markers` (`_services/_base.py:393`) refuses **any** well-formed marker in a body, a comment
message or a sub-entity title, and every prose input that lands inside a marker-delimited region
passes through it before any file write — ten call sites across the item body writer, the shared
section-edit core, both sub-entity body writers, the comment path and the importer's two seams. Its
own docstring and its refusal message already state the correct mechanism ("an author who does that
reaches for backticks first, which do not help").

So the conclusion stands, and on a **stronger** guarantee than the one §6 claimed: not "the scan
cannot see a quoted tag" — it can — but "no sq write path ever lets a well-formed tag into a body
in the first place". The correct bullet is:

> **No authored content is reachable.** Marker regions are sq-managed, no verb writes an arbitrary
> marker, and `reject_markers` refuses any well-formed tag on every write path that puts prose in a
> region, so an authored body cannot contain one to be matched. Quoting is not what saves such
> prose — `find_markers` matches a well-formed tag inside backticks exactly as it matches a bare
> one; the `sq:*` spelling escapes because `*` fails the tag's character class.

The rest of §6 is unaffected: the adopter-shaped case still runs the other way and is still a
feature, the discriminator is still `is_system_skill`, and the cross-version hazard still closes
itself.

### 3. Why the wrong reason mattered even with the right conclusion

The recorded argument is what the next person reasons from when they widen the frozen list of
region tags §3 governs. "A quoted tag is not matched" invites the belief that a corpus is safe
because its authors quoted; it is safe because a guard refused the tag at the door. The two differ
exactly where the guard does not run — the `adopt` population §1 names, and any hand-edited or
merge-resolved file — which is the population §6 exists to reason about.

### 4. The same conflation is repeated outside this record

Named because they are the sources a reader checks next, not as scope for this decision:
`_sections.find_markers`' docstring attributes the exclusion to references "written in prose"
rather than to the character class, and the project's contributor conventions carry the same
sentence. Both are narrowly true of their `sq:*` example and misleading about the reason.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-22T09:30:44Z] Robert Architect:
  - The body sink does not survive, and the driven evidence is stronger than the argument for it. Four computed renderings of the sub-entity projection already ship and none reads either materialised region; sq task N show --full never prints the :head text at all. The head is not local-source either — it resolves the assignee name from the ROLE item and the story label from the parent feature, and both go stale on a rename with sq sync not healing them.
  - Driven merge: two branches conflict in both the frontmatter subentities list and the :summary table of the same file. Resolve the frontmatter correctly, leave the table at one branch rendering, and sq repair + sq check pass with exit 0 while sq show prints two rows and the file prints one. No verb re-derives the region.
  - So the sink rule is not source locality — it is whether a shipped verb regenerates the region. Two sinks: display (computed) and document (a region of a wholly generated document, enumerated in engine code — role/skill bodies, backend artifacts). sink stops being a declared field, so the refusal FEAT-693 asked for becomes an unrepresentable state instead.
  - One departure from your stated conclusion, flagged for your ruling: a role ## Skills section stays materialised. The backend pointer tells the agent to load @squads/agents/roles/ROLE-....md, so role and skill item markdown IS read directly, by an agent, not only by a human resolving a merge — a computed view never reaches that reader. The stored extra.skills cache still goes, which narrows PERMITTED_EXTRA_SKEW and needs the literal-membership pin in tests/unit/test_role_def_extra_keys.py edited in the same change.
  - FEAT-694 needs reauthoring rather than implementing: its subject inverts to retiring the two regions, byte-identical output cannot be its bar, and a migration IS owed. @product-owner for awareness once this is ruled on; @op-pierre @manager the call is yours.
- [2026-08-22T09:38:26Z] Pierre Chat:
  - Direction that changes this decision: no materialized claude file may reference a local file path. The generated pointers currently instruct the agent with an @-reference to squads/agents/roles/ROLE-N.md and the skill equivalent; that breaks under remote mode, where there is no local squad directory. Pointers must instead display the sq commands an agent runs at startup, which work the same locally and against a server.
  - This overrules the architect departure on the third consumer. The case for keeping a role ## Skills section materialized was that the pointer makes an agent read the role markdown directly - that reference is itself being removed, so the premise is gone and the section is computed, as originally concluded. Reconsider whether a materialized sink has any consumer left at all once no generated file points at item markdown.
- [2026-08-22T09:48:01Z] Robert Architect:
  - Amended in place rather than annotated: the decision is Proposed, and sections 1, 4 and 5 asserted a document sink and a departure the direction overrules, so leaving them would have left the decision stating the reverse of the ruling.
  - The collapse is real, and I tested it rather than assuming. Section 4 now enumerates every non-human reader of item markdown: the index rebuild and per-item reads (frontmatter, never a derived region), show and the sub-entity panes (authored prose), sq search (the one survivor, _services/_collab.py:436-441), migration runners (the mechanism that removes a region), the body regenerators (writers), the VS Code client (reads .squads.toml only, everything else is sq --json — driven), and the agent host @ resolver. The @ resolver was the ONLY non-human reader that consumed a derived region as its content, and the direction deletes it. So there is one behaviour and no exception list.
  - One correction to how the collapse was framed: the reader is not deleted so much as moved behind sq. Once the pointer names sq role <slug> show, sq is in the delivery path, which is what makes computing possible for that reader at all. And the computed home already exists — the show card is already computed and already carries a creates: row (_cli/_role.py:324-345), so the skills list is one more row beside it and role.md.j2:18-25 is deleted.
  - Materialisation itself does not vanish, and section 4 says so rather than over-reading the rule: the backend pointers and the compiled managed regions are materialised projections read by a non-human with no sq in the loop, they must stay that way because a host reads files and cannot run commands, and they are write-only and never read back (tests/meta/test_a_backend_never_reads_back_its_own_generated_output.py). They are governed by invariants 5/6/7 and the ABC, never by a view sink.
- [2026-09-01T08:00:03Z] Pierre Chat:
  - Direction, general rather than case by case: existing files should be shrunk of all duplicated data. The markdown files are the storage; the only read surface is the CLI; and views are the way to present derived content. Anything materialised into a file that the CLI can compute is duplication and comes out.
- [2026-09-01T08:01:03Z] Pierre Chat:
  - This lands in 0.14, not later: the shrink rides the same migration runner and the same schema bump as the region retirement.
- [2026-09-01T08:13:44Z] Robert Architect:
  - Amended in place (2026-09-01 note, second one): the shrink rule applied, scoped, and the views fork ruled.
    - In class, exhaustively: the whole `sq:body` region of every role item, and of every SYSTEM skill item; plus the role `extra` mirror keys (title/mission/responsibilities/agreements/color/can_spawn/description/skills, and model for a non-dev role). Out: a CUSTOM (authored) skill body — `releasing-squads` is one in this corpus, 10.1 KB. 22 of our 23 files are in class; a migration keyed on folder/type/`sq-` prefix destroys the 23rd. Key on `is_system_skill(slug, spec)`, which already ships and which `set_body` already uses to refuse exactly these writes.
    - `title`/`description` STAY — uniform-record fields read by surfaces that cannot resolve a role catalog. The duplication inside that pair is `item.title` vs `extra.full_name`: keep the top-level field, drop the extra copy.
    - Views do NOT widen. All three source kinds are relations of one item resolved off the index; a skill body is spec data keyed by item type and a role body catalog data keyed by slug — no relation to invert, and a widening would break the uniform record shape and leave the load-time referential pass with a second document and no clause to apply. These compute at show time through the resolver each surface already has; the deletion half is a call-site move, not new machinery. That is a shape judgement, and it lands whole in this release.
    - Driven, and worse than drift: `sq role qa set-default` is silently reverted by the next `sq sync`, `sq check` exit 0 on both sides — `is_default` is operator-settable AND a catalog mirror key.
    - Three couplings the breakdown needs before the build: `_without_permitted_extra_skew` identifies a role by `extra.mission` (the key we remove); `sq check`'s pointer-currency expectation is built from `RoleDef.from_extra` (the mirror we remove — ADR-781 §2c goes void unless it moves to the resolver); `PERMITTED_EXTRA_SKEW`'s literal test pin.
    - Marker safety holds: the only out-of-region content in a role file is frontmatter and a static `## Discussion` heading; the body is one region already rewritten wholesale every sync. @tech-lead this is the scope for the FEAT-694 breakdown.
- [2026-09-01T08:55:17Z] Robert Architect:
  - Amended in place, third 2026-09-01 note: the roll-up ships no bundled view either. Tracked, per the audit rule:
    
    - **Added** amendment note §§1-6. §1-2 are the driving (scratch squad at 0.14.0); §3 the ruling; §4 the further narrowing of §6; §5 the reconciliation with the 2026-08-26 refusal; §6 `milestone_rollup` and the discriminator.
    - **§6 narrows again.** "Reissue both projections as computed views" becomes: for the summary half, satisfied by the rendering that already shipped. Its other clauses are untouched.
    - **§5 is unchanged.** Its verdict on the roll-up ("computed") was always right; what changes is that nothing new has to be built to meet it.
    - **The 2026-08-26 refusal is unchanged and unweakened** — §5 of the new note records why neither rescue (degrade-instead-of-refuse, prune-bundled-instead-of-refuse) survives it, so neither is re-proposed cheaply.
    - **Nothing is superseded** and no ref changes: this is a clause-level narrowing inside the same decision.
- [2026-09-01T10:41:16Z] Robert Architect:
  - Amended in place, fourth 2026-09-01 note: the corpus strip is a repair-side sweep, not a schema step. Tracked per the audit rule:
    
    - **Added** amendment §§1-7. §1 the driving and the stranded population, §2 the ruling, §3 the rule governing what the sweep may remove, §4 the four refused vehicles, §5 the accepted failure mode, §6 adopter safety, §7 the downstream narrowings.
    - **§6 narrows**: "a migration **is** owed" becomes "a corpus sweep is owed". Its other clauses — the inverted subject and the byte-identical-computed-rendering bar — are untouched.
    - **§5 is unchanged.** Its "computed" verdicts stand; what is settled is the mechanism that removes what they replaced.
    - **Nothing is superseded** and no ref changes: a clause-level narrowing inside the same decision.
    
    What decided it, and it is not this release's staging: `adopt` over a folder with no `.squads.toml` stamps the build's own `SCHEMA_VERSION` (`_models/_config.py:23`) and rebuilds from disk, so a corpus can arrive at the current stamp with no runner ever visiting it. The stamp axis cannot be the axis a corpus sweep runs on. `repair` is the only walk that reaches both populations with one implementation, its per-file loop already rewrites content (the ref canonicalization), and the ordering prohibition becomes structural because `require_current_schema` means repair can only run at the current schema and the one behind-schema call is the migration tail.
    
    Two corrections the driving turned up: the corpus carries 1545 balanced head regions across 436 files (the report of zero came from a missing `HEAD` constant in `_models/_markers.py` — the tag is built by `_discussion._head_tag`), and this repository's strip needs no stamp rewind, only `sq repair`.
    
    @tech-lead the rewrite is on TASK-849. @op-pierre the accepted cost, stated rather than mitigated: `sq repair` now rewrites file content as well as the index, so it produces a large announced diff on any corpus still carrying the regions.
<!-- sq:discussion:end -->
