---
id: ADR-880
sequence_id: 880
type: decision
title: Views as a source plus a template rendered at a document tag
status: Accepted
author: architect
refs:
- ADR-1109
description: Retire the projection layer; keep and widen sources; a content-free tag
  marks where a view renders on read
created_at: '2026-09-02T12:23:01Z'
updated_at: '2026-10-25T21:47:49Z'
---
<!-- sq:body -->
## The operator's model

> "the projection over refs is dumb and useless. A view is just a template and a place to go,
> that's it. the main doc contains a tag that renders the view. voila"
>
> "yeah, the source mechanism is good, that needs to be scoped to all render time logic"

Read together: **a view is a source plus a template; a tag in a document is the place it renders.**
The source mechanism stays. The projection between source and template goes. And the scope widens
from item relations to every piece of render-time logic squads has. op-pierre ruled it on
2026-09-03: build it.

## Context: what the projection layer cost

Before this decision `_views.py` had three layers: source resolution and template dispatch (about
160 lines), and a projection middle layer (about 270 lines: `_RawRecord`, `Cell`, `ViewFieldMeta`,
`ViewRecord`, `ViewGroup`, `Projection`, `project`, `_sort_key`, `projection_json`) driven by a
`fields`/`group_by`/`order_by` grammar in TOML and the validators that proved it resolved.

- **It reimplemented the template language, worse.** Jinja has `groupby`, `sort` and
  `selectattr`; a template under `StrictUndefined` validates field access at render, against the
  actual record.
- **Flattening heterogeneous records forced a lie.** A `ref` source's records can be items of any
  type, so a field only some types carry rendered `null` for the rest: an artifact of pressing
  differently-shaped items into one row.
- **Nothing consumed its machine-readable half.** The VS Code client read `sq tree --json` and
  `sq show --raw`, never a view payload.
- **Render-time logic had been reinvented bespoke three times** (role definition text, system skill
  text, per-item-type skill text) because the declared mechanism only spoke relations. The role
  item's body region was already deliberately empty, waiting for something to render into it.

## The decision

### 1. A view is a source plus a template

- A `[views.<name>]` entry declares its `source`, and optionally `position` (§6) and `transform`
  (ADR-1109). There is no `fields`, `group_by` or `order_by` key, and no per-type attachment
  (`ItemSpec.views` does not exist): a view reaches a document only through a tag.
- Presentation resolves by the view's own name at `templates/views/<name>.md.j2`, bundled or
  shadowed under `.overrides/templates/`.
- A template receives the source's own shape, unflattened, plus the host item, the active spec and
  the squad directory, and `data` when the view declares a transform. `_badges.py` is reachable as
  a registered filter, and the settled-versus-delivered distinction is a `WorkflowSpec` method a
  template calls.
- `--json` is per source, in the shape each source already serialises: `--json` answers about the
  data, `--raw` about the text. `sq workflow view <name> <id> --json` emits the resolved source;
  `show --json` carries transform output under `views` (ADR-1109).
- **Jinja is the query language, and its guard is binding.** A join may be added only as a new
  `source.kind`, declared in the spec, validated at load, named. No `fields`-shaped declaration
  layer may return to `[views.*]`, and query logic may not accrete inside a template. The sanctioned
  extension point is a filter registered in `_rendering/_engine.py`: a pure function of the spec or
  the playbook. A view that cannot be expressed as one source plus Jinja's own `groupby`/`sort`/
  `selectattr` over that source's records is a **missing source kind**, to be proposed as one.

### 2. The source grammar

`kind` means "which resolver". The same two-key grammar (`kind`, `name`):

| `source.kind` | `name` resolves against | what the template gets |
|---|---|---|
| `ref` | `[ref_kinds]` | items carrying that forward ref to the host |
| `subtree` | `[items]` | descendants of the host of that type |
| `subentity` | `[subentity_kinds]` | the host's own sub-entities of that kind |
| `role` | — | the resolved `RoleDef` (catalog + overrides + item fields) |
| `playbook` | `[items]`, or, `name` unset, the type the host *speaks for* | the type's playbook lane, the live roster, the spec |
| `self` | — | the host item, the spec, the squad dir |

**A `playbook` source's subject**, with `name` unset, is the type its host speaks for: its own type
for an ordinary item, and the item type it documents for a per-item-type skill item. The derivation
is gated on the host being the declared roster skill type (every other host keeps `item.type`), and
it resolves through the existing spec-pure slug family (`item_type_for_skill_slug` and its
siblings), never a second inversion. A skill host whose slug names no declared type renders empty
and raises nothing. That is the same resolver with a corrected default, not a seventh kind.

**One view name for every per-item-type skill:** `[views.item_skill]`, `source = { kind =
"playbook" }`, one template, one tag name, for bundled and project-declared types alike. One view
per declared type is refused: a view name that embeds a type name puts a type's name into corpus
bytes, and a rename or a `[selected]` drop would dangle the tag on every skill body carrying it.
The rich/thin split lives in the template (`lane` present or not), so a project-declared type with
no playbook lane gets the thin rendering.

**Bundled views:** `milestone_rollup` (a `ref` source over `targets`, with a transform),
`role_definition` (`role`), `squads_skill` (`playbook`, `name` unset), `greeting_skill` and
`memory_skill` (`self`), and `item_skill` (`playbook`).

### 3. Source applicability is placement state, not a defect

For each source kind, every condition under which its resolver cannot produce a well-formed result
is classified by one test: *is it decidable from the declared spec plus the host item's type alone,
before any record is read and before any template is rendered?*

- **Decidable: it is a precondition of that kind**, declared in the kind's applicability predicate
  beside its resolver. It is placement state: placement refuses it, expansion leaves the tag
  literal, the read succeeds, and the file scan reports it.
- **Not decidable: it is a defect**, discoverable only by executing the resolver or the template.
  It raises as `SquadsError` naming the item and the view.

Binding clauses: a resolver may not raise for a condition its kind's predicate could have decided; a
kind with no host constraint declares its predicate constantly true, explicitly. A predicate may
not read the host item's content (refs, sub-entities, status), only its type, which keeps it
answerable by all three consumers. **Emptiness is never a failure**: a milestone with no members
renders an empty roll-up; a predicate that grew into a reachability analysis would be a second query
layer.

The predicates: `subentity` requires the host's type to host that kind; `role` requires the host to
be of the declared role type (an orphaned role item whose identity resolves to nothing degrades,
not raises); `ref`, `subtree`, `playbook` and `self` are constantly true. A `playbook` source's
`name`, when set, must be a declared type, which spec load enforces. One helper beside
`view_target_exists` answers all three questions (declared, template resolves, source applies to
this type) with the reason it refused, so placement and the file scan name the same cause.

**What stays loud.** A render-time failure with the precondition satisfied raises: a template
raising under `StrictUndefined` or any other `TemplateError`, bundled or an adopter's override; a
resolver failing for anything its predicate could not decide; a transform failure (ADR-1109). A
fault in the spec or override tree fails loud everywhere, as a malformed override already stops
every command; degrading it would hide a broken template behind a tag its author placed. The
explicit `sq workflow view <name> <id>` always raises on an inapplicable pair: a direct question
gets an error, not a broken read.

### 4. The tag

**The binding invariant.** The view tag is declared **unpaired**: a marker with no `close_marker`
counterpart, and therefore no span. A tag's bytes carry the view's name plus an optional state suffix
set by the author (`:disabled`), and nothing else: no computed content, nothing that can go stale.
Materialisation needs a span to write into; there is none, so the stale-content failure of the
stored regions this corpus was stripped of (ADR-776) is unreachable by construction. `_models/_markers.py`
must not gain a closing counterpart for a view tag, and no verb writes content on a tag's behalf;
prose written beside a re-placed tag is the author's. Any proposal to give the view tag a body, a
paired form or a cached rendering *is* the proposal to rebuild the stored region, and is answered as
exactly that.

- **The tag lives inside the `sq:body` region**, as unpaired content of that region. Text outside
  every region is invisible to every read surface (`read_body` is the region's content); a tag in
  its own region would be the `sq:summary` shape again, a tool-owned slot where a cache gets argued
  for; a frontmatter `views:` list carries no position and is `ItemSpec.views` relocated onto every
  instance.
- **The tag never enters through the prose door.** `reject_markers` stays fully closed: a body
  write whose text carries a view tag the region has not placed in that state is refused, naming
  the view verbs. A body write that carries back an already-placed tag unchanged is accepted, so a
  `show --json` body round-trips (ADR-1109). Placement is its own marker-safe verbs (§7) or a
  type's creation template.
- **Spelling.** A disabled tag is `sq:view:<name>:disabled`; `MARKER_RE` is `sq:\w[\w:-]*`, so the
  suffix stays in-class, `find_markers` sees it and `reject_markers` refuses it in prose like the
  enabled form. `view_tag_parts` parses a tag into its name and its state; the suffix literal lives
  in `_models/_markers.py` only.
- **View-name alphabet**, enforced at load: a bare TOML key (`[A-Za-z0-9_-]+`) other than `end`. A
  colon would make the state suffix ambiguous, a character outside `MARKER_RE`'s class would hide
  the tag from `find_markers` and `reject_markers`, and `sq:view:end` spells a close marker.

### 5. Expansion

Tags expand at the single body-read boundary below the CLI (`read_body`), so `--raw`, the TUI and
the CLI inherit it from one place. An enabled tag whose precondition holds renders its view; an
enabled tag whose name is undeclared, whose template is missing or whose source does not apply stays
literal, byte for byte; a disabled tag expands to nothing and its bytes stay on disk. Each rendered
view is padded with one blank line against the prose beside it at read time; the stored bytes are
not changed.

**Recursion is refused at the mechanism.** Tags expand in item bodies only. View output is not
scanned for tags, so a tag appearing in a view's rendered text stays literal. There is no depth limit
and no cycle detection because there is no second expansion site to recurse through; any change that
adds one has to bring them.

### 6. Seeded views, `position`, and re-placement on every body write

**A document's seeded views** are the views the tool's own placement authority puts on it, as that
authority stands now, never derived from provenance:

| Document | Seeded views |
|---|---|
| ordinary item | `template_seeded_view_names(type)`: its creation template as it stands now, override-aware |
| role | `role_definition` |
| permanently-system skill | its `SYSTEM_SKILL_VIEW_NAMES` view |
| skill documenting a declared type | `item_skill` |
| custom skill; stale `sq-<type>` for an undeclared type | none |

Each roster row applies only while its view is declared: a view dropped from `[selected]` seeds
nothing anywhere (`roster_body_view_name`). Every seeded view is kept for good: its tag is disabled,
never deleted. The spec-level escapes are dropping the view from `[selected]` or overriding the
creation template; a creation-template override may drop a view tag, because a view tag is unpaired
and carries no region, so the override check's required-marker set excludes the view-tag family.

**`position`.** `[views.<name>]` takes an optional `position`, default `"bottom"`:

- `"top"` puts the tag on the first line of the `sq:body` region; `"bottom"` on the last.
- `"after(<regex>)"` searches the region's prose (after the edit is applied, with every view tag
  stripped) as a Python `re` pattern with `MULTILINE` set, and puts the tag on its own line after the
  line holding the **first** match's last character; with no match the view falls back to `bottom`.
  A pattern that does not compile is a spec-load error.
- An unrecognised value is a spec-load error. Several views at one place go in declaration order.
  `position` belongs to a view, not to a document: no per-document location survives a body write.

**Every body write re-places the tags.** Replace and append take the same four steps: read every
view tag in the region, enabled and disabled, with its state; strip them, without changing a prose
character; apply the prose edit to what remains (the input passes `reject_markers`); re-insert one
tag per view read, at that view's position, in declaration order, each keeping its state, and insert
**enabled** the tag of any seeded view that was absent.

- **Stripping never changes a prose character.** A tag alone on its line takes its line, leaving
  what deleting a line would: where a single newline flanks it on each side no blank line remains;
  where a blank line flanks it, exactly one remains; at the region's edge nothing remains. A tag
  sharing its line with prose (a shape no writer produces, but a hand edit or an adopted file can)
  loses only itself and the one run of spaces or tabs directly touching it, trailing side preferred,
  never a newline.
- **Spacing keeps the author's own.** A re-inserted tag sits on its own line and mirrors the
  separator already at its landing spot. Against a `top` or `bottom` edge, and between two tags, the
  separator is one blank line, and no blank line pads the region's own edges.
- **Invertible and byte-stable.** Stripping a placed tag gives back the prose it was placed into,
  and running the routine over its own output changes nothing.
- **Duplicates.** Copies of one view in the same state collapse into one tag. Copies in conflicting
  states refuse the write, naming `view add` and `view disable` as the two ways to settle it.
- **Undeclared views.** A tag naming an undeclared view has no `position`; it goes to the bottom,
  after every declared view, keeping the undeclared tags' relative order, and a newly placed one
  comes after every existing one.
- **Creation** runs the same routine over the creation template's rendered `sq:body`, with the
  caller's explicit body as the edit, so a created document's tags sit at their positions from the
  first write.
- **One routine.** The body write (the single-item `body` verb and the bulk importer's body op,
  through one closure), item creation, the placement verbs, the managed-skill seed, the standing
  convergence sweep and the migration all run `place_view_tags`; no writer composes a view tag
  outside it. A bulk writer that places tags composes the tool's own placement primitives, re-spells
  none of the conditions, and applies each at the granularity the placement verb applies it: a
  predicate the verb asks per item, asked by a bulk writer per corpus, is the same defect class as a
  re-spelled anchor.
- **The authored-content guard** (`reject_body_overwrite`) compares prose with view tags stripped
  from both sides and leading and trailing blank lines ignored, so neither a tag's state or location
  nor the blank line beside it makes a body count as authored. `--force` keeps its single meaning,
  consent to overwrite prose, and lifts neither the conflicting-state refusal nor the roster refusal.
- **A template-seeded document takes the `body` verb like any other item.** A milestone accepts
  replace and append; its first replace over the unwritten scaffold needs no `--force`; an append
  lands above a `bottom` tag.
- **"Hand-placed tags survive"** means the tag and its state survive; its location is its view's
  position.

`sq retype` preserves the body, so a tag rides along to the new type. A tag that was valid when
placed and is no longer (a retype, a spec or override edit, a template change) is never stripped,
relocated or repaired; the next body write re-places it at its view's position with its state, and
the file scan reports it while it cannot render.

### 7. The placement verbs: `view add` and `view disable`

- `view add <name>` places the tag at its view's position, or re-enables a disabled one. It is the
  only way back from disabled; there is no `view enable`. It is gated by `resolve_view_target`
  (declared, template resolves, source applies).
- `view disable <name>` turns an enabled tag disabled, or places the tag disabled when it is absent.
  It is ungated by name resolution, because it is the recovery path for a dangling or inapplicable
  enabled tag: disabling it clears its error.
- Both run the §6 routine with their own view's state set explicitly. On a conflicting pair each
  collapses every copy into one tag in the state it names, never raising the conflicting-state
  refusal, since they are its remedy. A verb that finds its view already in the state it names writes
  nothing. `view add` accepts only a declared view, so a new undeclared tag can come only from
  `view disable`, placed disabled.
- Both refuse when the document carries a tag for that view **outside** the `sq:body` region,
  naming where it is: they manage in-region tags only and would otherwise place a second copy.
- There is no `view rm`: a tag is never removed, only disabled.
- **On a roster host** (§8) the view verbs pass through the roster write gate: `view add` is
  admitted for the host's own classified view only (every check remedy for a roster body ends in it),
  and `view disable` is refused, since it would hide the generated definition. The escape is the
  spec-level one: drop the view from `[selected]`, and the document leaves the classification.

### 8. Roster bodies hold no prose

A body write, replace and append alike, is refused on any document whose roster classification
(`roster_body_view_name`) names a declared view: a role, a permanently-system skill, and a
per-item-type skill. `--force` does not lift it, and the rule is keyed on that one predicate, asked
once (`_refuse_classified_roster_write`), never on a type literal; the body write, the metadata
update, the view verbs and the bulk importer's simulation ask the same question.

- **Why:** the content already has one declared, validated authoring surface; body prose would be a
  second, unvalidated source of what agents read. A template-seeded view such as `milestone_rollup`
  has no second surface, so those documents stay writable.
- **The refusal names the authoring surface**, resolved from the view's declared source and the
  active playbook, never from the slug:

  | Document | Authoring surface |
  |---|---|
  | role | `.overrides/roles.toml`, or `.overrides/roles/<slug>.toml` for a project-defined role |
  | skill whose view has a `self` source (`greeting_skill`, `memory_skill`) | its own view template override, `views/<name>.md.j2` |
  | skill whose view has a `playbook` source and whose resolved subject has a lane | that type's lane in the playbook override |
  | skill whose view has a `playbook` source and no lane (`squads_skill`, or `item_skill` for a type with no lane) | the playbook override |

- **A body region is tool-owned because something the tool maintains renders into it.** Drop the
  view from `[selected]` and the document leaves the classification: its body is authored prose,
  written with `body`, displayed by every read surface, and left alone by `sq sync` and `sq repair`.
  Re-adding the view makes it a host again; the file scan reports a missing tag, and `view add`
  places it keeping the prose.
- **Rejected:** treating roster bodies as ordinary documents (agents would read an override-declared
  definition and unvalidated prose side by side), and refusing append while admitting replace
  (incoherent, since a replace can produce every body an append can).

### 9. Convergence, and the one migration licence

- **The standing convergence sweep is strict.** `_converge_body_tag` converges only an empty or
  already-tagged region; any other region is left untouched, silently. It never re-enables or
  rewrites a disabled tag. A standing sweep runs forever and cannot tell authored prose from a
  legacy rendering, so it may not guess.
- **The one write squads made into authored regions is the 0.14 to 0.15 migration**, under a closed,
  release-scoped licence, and it is **not a precedent**: a later bundled view lights up on existing
  documents only where an author or an operator places its tag. That migration placed the
  `milestone_rollup` tag in every milestone body of a seeding type through the §6 routine (a body
  whose tags already sat at their positions was left byte-unchanged and not counted; the count was
  reported), and reclaimed every roster body the classification names: a marker-free, non-empty
  `sq:body` of a role, a permanently-system skill or a per-item-type skill was overwritten with its
  tag alone, with no provenance check (pre-1.0 squads carried rendered text there), skipping only an
  unreadable file, a body with no `sq:body` region, and marker-shaped content. Skew was judged
  against each file on disk, and a document whose tag already sat outside the region was skipped
  rather than given a second copy. ADR-955 governs that step: it fails the reconcile licence's
  clauses 1 and 2, so it is a migration step.

### 10. What `sq check` reports

The view-tag findings run in the always-on file-level scan (`_scan_for_check`), which binds the
host type from the type folder and the filename before `read_frontmatter` runs, so they need no
resolved `Item` and keep firing on a file too broken to parse. None is a selectable catalog member.

- **`view_target_resolves`, error:** an enabled tag naming a view the active spec does not declare,
  whose template is missing, or whose source does not apply to this host's type. One helper, the
  reason named. A disabled tag is not asked to render and is not reported.
- **`seeded_view_resolves`, error:** a seeded view absent from its document, or any view present
  twice, counted by view name across both states and across the whole file. Within the region every
  write holds the exactly-once condition by construction, so these arise from hand edits, adopted
  files and spec changes. The remedy names `view add` (and `view disable` on an ordinary
  document). A role body that holds prose in place of its tag is a supported state and is not
  reported; a skill body with prose beside a missing tag is reported with a remedy that preserves
  the prose, since it may be an author's own runbook.
- **`view_tag_in_region`, warn:** a view tag outside the `sq:body` region, in an item file or in a
  creation-template override. It never renders, the view verbs refuse to act on it, and the remedy
  is to move it inside the region. A copy in and a copy out are a duplicate whose remedy says the
  outside copy goes first.
- The repair sweep that strips retired regions distinguishes by marker **shape**: an unpaired
  `sq:view:` tag inside `:body` is never on its list (ADR-776).

## Consequences

- **The source layer grows and the projection layer is gone.** Ref inversion, the subtree walk and
  the sub-entity read survive; `role`, `playbook` and `self` collapse the three bespoke render paths
  onto the declared mechanism.
- **An adopter declares a view without Python**: one `[views.<name>]` entry with its `source`, a
  template under `.overrides/templates/views/<name>.md.j2`, and the tag placed with `view add` or
  seeded by overriding the type's creation template. The adopter chooses the document; the view
  chooses the position.
- **A tag is a property of the document**: `retype` carries it, and a tag left by a dropped view is
  reported until disabled.
- **The `playbook` predicate is constantly true**, so placement does not refuse an `item_skill` tag
  on a non-skill host; it renders that host's own lane. That is an odd but correct choice an author
  made; buying the refusal would need a per-view predicate axis.
- **What is lost**: a client can no longer read a view's columns off a payload, because the columns
  exist only in the template. A client wanting the view as presented asks for the rendered text
  (`show --raw`).
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-02T12:23:27Z] `architect` Robert Architect:
  - Scoped @op-pierre's model: view = source + template, tag marks the place, projection deleted. Left un-ruled deliberately — this prices the change, it does not rule it.
  - Two empirical checks that decide it: nothing in clients/vscode/src touches view JSON (no hits for workflow view / milestone_rollup / projection / groups — it reads sq tree --json and show --raw), so the projection has had zero clients for a release; and role_definition_text already IS source+template with one context var, with the role item's sq:body deliberately emptied at create — the codebase drifted to this model three times bespoke because the declared mechanism only spoke relations.
  - Sharpest cost to weigh before ruling: type-attachment is retroactive, a tag is not, so existing milestone files need a migration that inserts into the authored :body region — the first write of its kind. Second: a body -m replaces the region and silently drops the tag.
  - Not the region we just stripped: the tag is unpaired by design (no close_marker counterpart), so there is no span to materialize into. @product-owner @tech-lead for the shape before any breakdown.
- [2026-09-03T08:45:10Z] `op-pierre` Pierre Chat:
  - Ruled: build it. The view system is useless right now, so this is the main focus of 0.15 -- source plus template, tag marks the place, projection deleted.
- [2026-09-03T08:50:43Z] `architect` Robert Architect:
  - Ruled per op-pierre (2026-09-03): build it, main line for 0.15. Added "The ruling" section; the pricing and evidence sections are untouched.
  - Decision: view = source + template, tag marks the place; the projection middle layer plus the fields/group_by/order_by grammar, its validators and ItemSpec.views all delete; source grammar widens past relations to role/playbook/self, which is what collapses the three bespoke read-time render paths.
  - The four problems are ruled, not restated. The retroactivity migration into the authored :body region is permitted once under a closed condition set (insert-only, one deterministic anchor at the region end, idempotent, skip a body already carrying the tag, report the count) and is explicitly not a precedent for a later view. A body write dropping the tag is accepted as an unfixed cost — refused: preserving, silently re-inserting, or refusing the write, since each makes the tag tool-maintained bytes in an authored region; the loss is made visible by a warn-level advisory that is catalog-only under ADR-864 tiering, selected by our own spec. Jinja-as-query is accepted with its guard binding: a join arrives only as a new source.kind. Recursion is refused at the mechanism — one expansion site, so no depth counter.
  - Binding constraint on any future change: the tag is unpaired, no close_marker counterpart, so no span exists to materialise into. A dangling tag name is an error-level floor finding; the repair sweep distinguishes by marker shape, never by a name list. Any proposal to give the tag a body or a paired form is the proposal to rebuild the stored region and is to be answered as that.
- [2026-09-03T09:08:20Z] `architect` Robert Architect:
  - Amendment appended, ruled against the placement change: the tag stays inside the sq:body region. @op-pierre @manager — the ruling and pricing sections are untouched.
  - Decisive fact, driven with controls in a throwaway squad (removed): text outside every region is invisible to every read surface. show --raw prints region contents only — a file carrying both an outside-region tag and the on-disk "## Discussion" heading showed neither. So the ## Discussion precedent is precedent for text that is never read. Unmarked-outside is unreachable by any read path, which pushes the tag into its own marked region — a tool-owned slot between body and discussion, byte-for-byte the sq:summary shape we just stripped, and exactly where a cache gets argued for. So yes to the sharper question: outside the body is WORSE, despite genuinely dissolving problem 2. Frontmatter refused separately: a views: list carries no position, so it is ItemSpec.views relocated onto every instance — more storage, less expressiveness, derivable from the type template.
  - Per-document placement is load-bearing only for the roll-up, but inside-the-region placement is load-bearing for every source kind: a role body is emptied at create (_services/_base.py:931) precisely to be the slot the definition renders into, so outside placement would need two homes for one grammar.
  - Two corrections the question earned, both driven. (a) reject_markers refuses a tag typed into a body (control: same text unwrapped is accepted), so the adopter step "place the tag by hand via sq body" does not work — ruled no hole in that guard; placement gets its own marker-safe verb, and the migration inserts through that same path rather than as a bespoke authored-prose write. (b) _services/_maintenance.py:455 already reports any unpaired tag as an error-level unclosed marker, in BOTH positions — so the balance arithmetic must learn the unpaired sq:view family by shape, with name resolution replacing pairing for it. The repair sweep needs no change (_maintenance.py:231 admits only sq:summary and *:head, and skips unbalanced tags).
  - Advisory gap closed: its condition is keyed on the type\s creation template as it currently stands, not on how the tag arrived — which covers migrated items (the migration touches exactly those types) and is the only implementable condition. Also named: sq retype carries the tag to the new type, accepted rather than fixed. @product-owner unblocked for the breakdown.
- [2026-09-03T11:54:44Z] `architect` Robert Architect:
  - Second amendment appended, ruling REV-912 F1 as a classification rather than a resolver patch. Ruling, pricing and first amendment untouched; @op-pierre @tech-lead @reviewer.
  - A source that cannot resolve against its host is placement state, not an engine defect: tag stays literal, read succeeds, sq check reports it. Test a future resolver is judged by — is the condition decidable from the spec plus the host item TYPE alone, before any record is read or template rendered? Decidable = precondition (quiet, reported); not decidable = defect (raises). Binding corollaries: a resolver may not raise for what its predicate could decide; a predicate may not read item content; emptiness is never a failure.
  - view add refuses an incompatible host through the same widened predicate, but the door is not the guarantee (retype, and any spec edit, reach the state without it). A tag valid when placed and no longer valid is not stripped, relocated or repaired — visible, never undone, keyed on current state and never on provenance. retype behaviour unchanged; its outcome becomes readable-and-reported.
  - Finding stays error-level and unconditional in the file-level scan beside the dangling name, and needs no resolved Item: the scan already binds the host type from the type folder before read_frontmatter, so it keeps firing on a file too broken to parse. The loud half survives relabelled as render-time failure with the precondition satisfied — template errors (bundled or adopter override), resolver bugs, the gate/render race — and the explicit sq workflow view path keeps raising.
  - F1 confirmed read at every link; two citation line numbers corrected in the section, neither affecting the finding, and I read its "check reports nothing" as narrower than stated. FEAT-903 obliged to declare each new kind predicate as part of landing.
- [2026-09-04T12:59:28Z] `architect` Robert Architect:
  - - Third amendment appended, ruling FEAT-906/TASK-923's open question. Ruling, pricing and both earlier amendments untouched; @op-pierre @tech-lead @manager.
    - It collapses — three for three survives. A `playbook` source's subject is the type its host **speaks for**: `name` unset resolves the host's own type for an ordinary item, and the item type it *documents* for a per-item-type skill item. No seventh `source.kind`: the case needs the same resolver (same `PlaybookSource`, same predicate, same `--json` payload, same template contract) with a corrected default, and `kind` means "which resolver" by this record's own words. Same shape `role` already ships — subject from the host's identity, `item.type` only as the precondition.
    - Refused: a synthesized view per declared type. Decisive reason beyond "don't declare what you can derive" — a view name embedding a type name puts that type's name in corpus bytes, so a rename or a `[selected]` drop dangles the tag on every skill body and turns ordinary customisation into corpus-wide error findings.
    - Adopter case ruled explicitly: one declaration `[views.item_skill]`, one template, one tag name; a project-declared `widget` gets `sq-widget` from the same writer, seeded with the same tag, resolving `widget` off the live `[items]`, thin because it has no lane. No per-type TOML for a bundled type either, so nothing a custom type is missing.
    - Accepted cost, named: `playbook`'s predicate is constantly true, so placement won't refuse the tag on a non-skill host. `role`'s precondition prevents a wrong answer; this one would prevent only an odd choice, and buying it costs a per-view predicate axis.
    - Corrected in place, quoted: the grammar table's `playbook` row was short by one clause; and the second amendment §6's "its precondition is that the resolved type is declared and carries a lane" is withdrawn on the "carries a lane" half — it contradicted the emptiness clause three paragraphs above it, REV-920 F1 settled it, and the "declared" half is enforced at spec load, not by a predicate.
- [2026-09-14T19:20:18Z] `op-pierre` Pierre Chat:
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
- [2026-09-14T19:28:26Z] `architect` Robert Architect:
  - - Fourth amendment appended, recording @op-pierre's ruling on `required`. The ruling, the pricing and all three earlier amendments are untouched; @manager @tech-lead.
    - My original refusal falls on one of its three limbs, and the codebase says so: preserving a tag and silently re-inserting it both have the tool write bytes the author never supplied (still refused, untouched); *refusing the write* writes nothing anywhere, and `set_body` has shipped exactly that refusal for role and system-skill bodies for releases. Calling a code path that writes nothing "tool-maintained bytes in an authored region" was a category error, and I cited that very refusal in the same amendment without weighing it. `required` is the declared, per-view generalisation of behaviour already hardcoded per type.
    - Settled: `required` is a key of the view declaration, never of a type's selection — a per-type axis is `ItemSpec.views` returning. The half the ruling leaves open is the host set, and it is **derived, never declared**: a required view's hosts are the documents the tool's own placement authority seeds it onto — `template_seeded_view_names` for an item type, `_repair_body_tag`'s classification for role/system/per-item-type skills. That makes creation satisfy the invariant by construction and keeps the predicate type-and-slug decidable.
    - Default `required = false` (an upgrading corpus predates the flag and there is no per-write escape from a restriction, so it must be opted into). Bound: the body write path (replace refused unconditionally, before and independent of `--force`; append untouched) and `sq view rm` on a host. Unbound: `view add`, `retype` (writes nothing, outcome becomes a reported finding), item creation, spec load.
    - Tier 1, plainly: the missing-required-tag finding is an unconditional error in the per-file scan beside the dangling-tag one — it needs no resolved Item and a declared requirement whose enforcement is opt-in is not a requirement. So TASK-942's catalog member, its tables, this project's selection of it and the `.overrides/workflow.toml` that selection needed all fall away. Nothing is reported for a non-required view: that would be a provenance question.
    - All six bundled views are `required = true`, `milestone_rollup` included — a stated change of position, and the only bundled view a body write can even reach. `set_body`'s hardcoded role/system-skill branches retire into the general rule for **replace**; the append refusal stays as a separate rule keyed on the repair sweep's own classification, because that region is converged and appended prose would be erased silently. This repo is already compliant (4/4 milestones, 10/10 roles, every skill but the one custom `releasing-squads`).
- [2026-09-15T07:20:35Z] `architect` Robert Architect:
  - - Fifth amendment appended, ruling @tech-lead's finding. The fourth amendment's "no behaviour change" claim is quoted and corrected; the ruling, the pricing and the first three amendments are untouched. @manager @tech-lead.
    - **The narrowing is intended.** A body region is tool-owned because something the tool maintains renders into it — drop the view and nothing does, so the region reverts to authored prose. Today's refusal tells the author "an authored body here would never be shown", and in these shapes that is simply untrue: `read_body` returns the region verbatim and only expands when a tag is present, so the prose would display fine.
    - **Three shapes, not two, and one is half as wide as reported.** The role with `role_definition` dropped is the third (today's `item.type == ROSTER_ROLE` asks nothing about the spec). And the stale `sq-<type>` shape narrows only for a *historically-bundled* type — `sq-bug` is bundled-blind and refused today, while a project-declared `widget`'s stale `sq-widget` is already writable, since `custom_skill_slugs` iterates the live spec.
    - **What the old refusal was actually protecting is one module over, and it has to go with it.** `_converge_body_tag`'s wide licence rests in writing on "no code path today can have authored either region" — which the narrowing falsifies across drop → author → re-add: a version-drift backfill then hits marker-free prose and replaces it with the tag line. Ruled: role and permanently-system skill move to `strict_empty=True`, the licence a per-item-type skill already has for exactly this shape one level up; the pre-0.14 legacy reclaim moves to a migration, under the closed one-time licence this record already defines. That also closes the trap where a legacy-rendered role body would be neither writable nor convergeable.
    - **One real defect the narrowing fixes.** `set_body` asks `is_system_skill` while the sweep asks `item_type_for_skill_slug` — two membership tests for one question, disagreeing on exactly the stale bundled slug: `sq-bug` with `bug` dropped is refused by the write path and never reached by the sweep. A region no command can write and no sweep can converge.
    - **`view rm`: confirmed unaffected.** It refuses nothing today, so my declared+required+host rule can only add refusals — there is no behaviour for a narrowing to remove. In all three shapes the view is undeclared, so removal stays free, which is the second amendment's recovery path preserved exactly.
- [2026-09-25T12:47:43Z] `architect` Robert Architect:
  - Added the seventh amendment, which records op-pierre's 2026-09-24 rulings on REV-964 (TASK-942 discussion). @manager @tech-lead
    
    - **Ruled:** `required` is retired, and a document's seeded views are kept for good. A seeded view comes from the creation template or the roster classification, with the per-host table in §1. A view declaration gains `position` (`top`, `bottom` (the default), or `after(<regex>)`, which falls back to bottom when nothing matches and uses the first match otherwise). A view is disabled (`sq:view:<name>:disabled`, confirmed inside `MARKER_RE`) and never deleted. `view rm` is retired, and the verbs are `view add` (place or re-enable) and `view disable`, which is ungated and inherits rm's recovery role. Every body write strips the tags and re-places them at their positions, in declaration order, each keeping its state. After the write, and in `sq check`, each seeded view must appear exactly once and no view twice, with duplicates counted by name. F2: the migration also reclaims `sq-<type>` skills. F5: the dead skip channel is deleted.
    - **Consequences worked out:** "hand-placed tags survive" means the tag and its state survive, while its location is the view's position. View names are restricted to bare TOML keys other than `end`. A disabled tag renders nothing and escapes the dangling-name error. The authored-content guard compares prose with tags stripped. The migration places through the same routine, so the bytes are unchanged for `bottom`.
    - **Narrowed in place:** the ruling's problem-1 licence (anchor; author move/remove) and problem 2 (superseded), plus the binding invariant's adjacency and name-only bullets. First amendment: both corrections. Second amendment: §3 (rm recovery; "not relocated") and §5's "quiet never means empty". Fourth amendment: largely superseded, with the survivors listed at its head. Fifth amendment: §3 (reclaim widened; escape superseded), §4 (rm) and the non-strict bullet in §5. The third and sixth amendments and ADR-955 are unchanged.
    - **F7 is left open for op-pierre** (§8). The options are: A, no prose on roster bodies (refuse replace and append); B, roster bodies as ordinary documents; C, refuse append but admit replace, which is incoherent. I recommend A. There are five further open questions in §9: a missing seeded tag at write time, a duplicate at write time, the position of an undeclared view's tag, whether `view enable` is a separate verb, and disable on a roster host under A.
- [2026-09-25T12:57:20Z] `op-pierre` Pierre Chat:
  - Rulings on the seventh amendment's §8 and §9:
    
    - **F7 (§8): option A.** Roster bodies hold no prose: replace and append are both refused on any document whose roster classification names a declared view, per-item-type skills included.
    - **Q1:** a seeded view whose tag is absent is inserted enabled at its position.
    - **Q2:** the post-write check runs on the finished body before commit. Duplicate copies of one view in the same state collapse into one tag during re-placement. Copies in conflicting states (enabled and disabled) refuse the write, and the refusal names `view add` / `view disable`.
    - **Q3:** an undeclared view's tag goes to the bottom, after every declared view, keeping the undeclared tags' relative order.
    - **Q4:** no `view enable` verb; `view add` is the only way back from disabled.
    - **Q5:** `view disable` is admitted on a roster host.
- [2026-09-25T12:58:50Z] `architect` Robert Architect:
  - Folded op-pierre's 2026-09-25 rulings on the seventh amendment into the body. @manager
    
    - §8 now states option A as the rule: replace and append are refused on any document whose roster classification names a declared view, per-item-type skills included, and `--force` does not lift it. The refusal names the authoring surface. B and C remain only as one line of rejected rationale each.
    - §9 is removed, and each ruling now sits in the section it governs. §4: an absent seeded tag is inserted enabled; same-state duplicates collapse into one tag; conflicting states refuse the write and the refusal names `view add` / `view disable`; an undeclared view's tag goes to the bottom, after the declared views, in its existing relative order. §5: the check runs on the finished body before commit. §3: there is no `view enable` verb, and `view disable` is admitted on a roster host.
    - Two corrections follow from the rulings. §4's "nothing about tags is refused" is replaced, since `--force` lifts neither the conflicting-state refusal nor the roster refusal. The in-place note at the head of the fourth amendment now says that its §6 append refusal is replaced by §8.
- [2026-09-25T13:21:27Z] `op-pierre` Pierre Chat:
  - Rulings on the implementation gaps TASK-942's breakdown raised against the seventh amendment:
    
    - **Spacing.** A re-inserted tag sits on its own line with exactly one blank line between it and adjacent prose. No blank line is added at the region's edges (a `top` tag is the region's first line, a `bottom` tag its last). Adjacent tags placed together are separated by one blank line. Re-placement is byte-stable: a write that changes no prose leaves the region unchanged. An `after(<regex>)` match inserts after the line holding the match's last character.
    - **Conflicting copies and the verbs.** `view add` and `view disable` do not run the conflicting-state refusal: each collapses every copy of the view into one tag in the state the verb names. They are the remedy the refusal names.
    - **Creation** runs the same re-placement routine, so a created document's tags sit at their positions.
    - **The legacy reclaim set** is the roster classification itself (`roster_body_view_name` names a declared view); `_LEGACY_ROSTER_VIEW_NAMES` collapses into it.
- [2026-09-28T16:32:22Z] `architect` Robert Architect:
  - Amended in place: op-pierre's 2026-09-25 placement-gap rulings (his second comment on this record), plus the decisions TASK-942 settled while it was built. Each claim was checked against the committed code (`_views.py`, `_sections.py`, `_services/_items.py`, `_services/_views.py`, `_services/_base.py`, `_services/_maintenance.py`, `_overrides/_service.py`, `_migrations/_v0_14_to_v0_15.py`). No supersedes edge, and the status is unchanged. @manager @tech-lead
    
    - **Seventh amendment §2, `after(<regex>)`:** the tag anchors on the line holding the first match's last character (op-pierre's ruling; the ST15 fix). A pattern ending in `\n` lands where its `$` form does, and a zero-width match anchors on its own line. The pattern searches the prose after the edit, with tags stripped. Also dropped "now" from the view-name alphabet bullet.
    - **§1:** a creation-template override may drop a view tag. That is the sanctioned escape, not a structural error: the override check's required-marker set excludes the view-tag family (`_required_markers_from_bundled`, found by the ST17 docs pass as the false `sq:sq:` error).
    - **§3:** replaced the stale `view_tag_name` bullet, which carried "Today it would…" narration, with `view_tag_parts`. Added op-pierre's ruling that on a conflicting pair `view add` and `view disable` collapse every copy to the state they name and never raise the refusal. Also: a verb that finds its view already in its state writes nothing, and a new undeclared tag can come only from `view disable`.
    - **§4:** added blank-line handling on strip (the `strip_marker_lines` fix for the stray blank line on `after()` fallback), op-pierre's spacing and byte-stability rulings, "a newly placed undeclared tag comes after every existing one" (the sort-key fix), and creation running the routine (his ruling). The one-routine bullet now names every caller. The authored-content guard also ignores edge blank lines, which is the milestone fix. A new bullet says a template-seeded document such as a milestone takes `body` replace and append.
    - **§6:** "`_LEGACY_ROSTER_VIEW_NAMES` gains `item_skill`" was stale, because op-pierre ruled the reclaim set is the classification itself and the list no longer exists. Restated it that way. The reclaim clears the legacy text (the ST12 edit-clearing fix), and skew is judged against the on-disk file (REV-964 F3, ST12).
    - **§8:** the "Why" bullet said the playbook overrides serve every skill, which was wrong for `greeting`/`sq-memory`. Replaced it with a per-document authoring-surface table matching `skill_authoring_surface`, which resolves from the view's declared source, never from the slug (the ST17 docs pass's defect #1).
    - **The ruling's problem-1 note:** the migration's idempotence is the routine's. A body already at its positions is unchanged and not counted, and an in-region tag elsewhere is moved to its position.
    - **New §9, an open question, not a ruling:** a tag outside `sq:body` (BUG-957). The body states the mechanism and the three candidate owners, and decides nothing.
    
    Code vs ruling, reported and not papered over. §5's text is unchanged.
    - §5 says a post-write check runs on the finished body and refuses a failing write. No such check exists. `place_view_tags` emits one tag per name by construction and raises only `ConflictingViewStateError`. `_reject_unwritable_body`'s docstring still refers to "its own post-write check". Within the region the guarantee holds by construction. Across the whole file it does not: the BUG-957 duplicate is exactly the write a real post-write check would refuse.
    - §4 step 2 ("strip them, each with its own line") assumes the tag has a line to itself. For a tag sharing a line with prose (`foo <tag>` then `bar`), `strip_marker_lines` joins the two lines into `foo bar`, which rewrites prose. No writer produces that shape; a hand edit or adopted file can.
    - `_write_managed_skill` composes the empty-region seed itself rather than calling the routine. A test pins it byte-equal, so it is a second spelling of placement, not a divergence in output.
- [2026-09-28T17:39:44Z] `op-pierre` Pierre Chat:
  - Code-vs-ruling gaps: (1) narrow the post-write check ruling to exactly-once by construction within the region; the whole-file case stays with the out-of-region open question (0.16). (2) Fix the stripping of a tag that shares a line with prose, so prose is never rewritten. (3) Route the managed-skill seed through the placement routine.
- [2026-09-28T17:41:48Z] `architect` Robert Architect:
  - Seventh amendment §5 narrowed in place, on op-pierre's ruling of 2026-09-28 (his comment above, point 1). @manager
    - The old text ruled a separate check on the finished body that refuses a failing write. No such check exists, and none is owed. §5 now states that within `sq:body` the exactly-once condition holds by construction: the §4 routine re-inserts one tag per view name and every absent seeded view, and its only refusal is the conflicting-state one. The heading changed from "post-write condition" to "exactly-once condition" to match.
    - Added a bullet that the guarantee is region-only. The whole-file case, a copy outside `sq:body`, points at the §9 open question.
    - Points 2 and 3 of the same ruling are code fixes still in progress, so §4 is unchanged until they land.
- [2026-09-28T18:11:46Z] `architect` Robert Architect:
  - Seventh amendment §4 amended in place to match 45c3b2a2, on op-pierre's 2026-09-28 ruling (points 2 and 3). Checked against `strip_marker_lines` and `_write_managed_skill`, with the strip shapes run through the function. @manager
    - Step 2 and the strip rules: stripping never changes a prose character. A tag alone on its line takes the line, under the existing blank-line rules. A tag sharing its line with prose loses only itself and one directly touching run of spaces or tabs, trailing preferred, never a newline.
    - The one-routine bullet now names the managed-skill seed, which runs through `place_view_tags`. No writer composes a view tag outside the routine.
    - op-pierre's `item_skill_shadowed` ruling (one remedy, no lane split, no rename) is not recorded here: this record does not speak about that finding.
- [2026-09-29T08:21:19Z] `architect` Robert Architect:
  - Seventh amendment §4 and §6 amended in place, on op-pierre's REV-967 rulings (F12, F1). The code is at 6231fe5c. @manager
    - §4 (F12): a placed tag now mirrors the author's own separator, which makes the placement invertible. The fixed blank line is now a read-time rule: `expand_view_tags` pads each rendered view and leaves the stored bytes alone. Checked with `place_view_tags`/`strip_view_tags` on single-newline and blank-line shapes.
    - §6 (F1): the reclaim overwrites every marker-free, non-empty per-type (and role or system) skill body with its tag alone. There is no provenance check. It skips only an unreadable file, a missing `sq:body` region, or marker-shaped content, per `_reclaim_legacy_roster_bodies`.
- [2026-10-25T21:42:22Z] `architect` Robert Architect:
  - 2026-10-25 audit: body rewritten in present tense; decision unchanged. Seven amendments folded; required, view rm and the catalog advisory removed as retired. Two later facts folded: the out-of-region tag handling built for BUG-957 (view_tag_in_region warn, verbs refuse), and FEAT-976 US3 (op-pierre ruling): on a classified roster host view disable is refused and view add admits only its own view, replacing the 2026-09-25 Q5 ruling. @manager please confirm that second fold with op-pierre.
- [2026-10-25T21:47:49Z] `manager` Catherine Manager:
  - Confirmed: the FEAT-976 US3 rule (view disable refused on a classified roster host) is what holds.
<!-- sq:discussion:end -->
