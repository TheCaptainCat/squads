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
updated_at: '2026-08-24T18:10:35Z'
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
<!-- sq:discussion:end -->
