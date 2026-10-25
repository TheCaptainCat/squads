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
- ADR-766
- ADR-71
- ADR-74
- ADR-663
- ADR-775
- ADR-777
- ADR-781
- ADR-1007
- ADR-422:supersedes
- ADR-880
created_at: '2026-08-22T09:28:29Z'
updated_at: '2026-10-25T21:42:17Z'
---
<!-- sq:body -->
## Context

FEAT-693 specified a derived view in four parts (source, projection, presentation, sink) and
asked that the mechanism encode a source-determined sink: a local source may materialise into a
marker-delimited body region, a foreign source must be computed. FEAT-694 was to convert the two
hand-rolled projections, the sub-entity roll-up summary and the head badge line, onto declared
body-sink views. A third consumer was named by the operator: a role's `## Skills` section, whose
source is foreign because each skill's preload edge lives in the skill's own item.

Before the sink was designed, the two shipped instances were measured (driven on a scratch squad
at `sq` 0.13.0), and the measurements changed the shape of the mechanism.

**Nothing read either materialised region.** Four computed renderings of the sub-entity
projection shipped (the summary table under `show`, the pane title under `show --full`, the meta
line under `<kind> show`, the `--raw` badge line), all computed from frontmatter. The two stored
regions were read only by a person or an agent opening the raw file.

**The head was not local-source.** It resolved the assignee's display name from the role item and
the mapped story's label from the parent feature, both other files. Renaming a story or a role left
every `:head` stale; `sq sync` healed neither, and `sq check` reported nothing.

**A materialised region could be silently wrong after a merge, and no verb fixed it.** Two branches
conflicting in both the frontmatter `subentities:` list and the `:summary` table, resolved
correctly in the frontmatter and left at one branch in the table, passed `sq repair` and `sq check`
while `show` printed two rows and the file one.

ADR-422 had drawn the line on locality ("the `:summary`/`:head` regions are local"). The summary
was local; the head was not, and ADR-422's own verdict on its option C (a silently-stale committed
rendering is worse than none) decides the head.

## Decision

### 1. A derived view is computed, never materialised

There is no sink to declare and none to derive. What a view is (a declared source plus a template,
rendered on read wherever a content-free `sq:view:<name>` tag sits in a body) is ADR-880's
decision; this decision's rule is the one it builds on: **no file squads stores holds derived
content that the CLI can compute.** The markdown files are the storage, the CLI is the only read
surface, and anything materialised into an item file that the CLI can compute is duplication and
comes out (op-pierre, 2026-09-01).

The rule closed by removing its last reader. No materialised file squads generates carries a local
file path (ADR-781): a generated pointer names the commands an agent runs (`sq role <slug> show`,
`sq skill <slug> show`) instead of an `@` path, so `sq` is in the delivery path for the one
non-human reader that used to consume an item body as content, and it can compute.

**Every non-human reader of item markdown, enumerated:**

| Reader | What it reads | Survives the rule |
| --- | --- | --- |
| the index rebuild and per-item reads | frontmatter | yes, and never a derived region |
| `show` and the sub-entity panes | the `:body` / `:discussion` regions, with view tags expanded on read | yes |
| `sq search` | body lines after the frontmatter | yes; it matches authored text, not derived values |
| migration runners | body regions, to rewrite them | yes, as the mechanism that removes a region |
| the VS Code client | `.squads.toml`, and `sq … --json` for everything else | yes, and never item markdown |
| the agent host | the generated pointer, which names `sq` commands | yes; it no longer loads an item body |

### 2. Projected data has the source's own shape

A view's data is the source's own records, unflattened, and `--json` carries data in the shape its
source already serialises; `show --json` carries a view's transform output under `views`
(ADR-880, ADR-1109). The CLI table is one presentation over the records, never their source, and a
client that lays out the records itself is the intended consumer, not one that reparses CLI text.

### 3. Presentation is a template, and adopter-overridable

Presentation is a Jinja2 template at `templates/views/<name>.md.j2`, resolved through the one engine
every rendering path uses, so a view's presentation is adopter-overridable through
`.overrides/templates/` the day it ships, with no new surface (ADR-85).

### 4. The sub-entity projections

- **The roll-up summary is computed** by the CLI from frontmatter (`_print_subentity_summary` and
  the renderings beside it), and squads ships **no bundled view** over `story`, `subtask` or
  `finding`. A bundled declaration over vocabulary the adopter is free to change would brick an
  ordinary customisation: an override shadowing a bundled kind's `fields`, or deselecting the kind,
  would make the spec fail to load, for a rendering no reader sees. An adopter declaring a roll-up
  over their own sub-entity kinds is the ordinary case and is untouched.
- **The head badge line has no successor.** Its computed form already ships
  (`_subentity_badge_line`: status badge, declared-field badges, assignee slug, mapped story id, all
  off the sub-entity's own frontmatter). What the stored region carried beyond it, the two foreign
  resolutions, was exactly its defect. If resolved labels are wanted by an actual reader, that is a
  change to the badge line, ruled against that named consumer.
- **The discriminator for a bundled view:** a bundled view earns its declaration when it is the
  only rendering of its data, and it is attached to the documents that show it. `milestone_rollup`
  is that case: it is the only rendering of a milestone's membership, its fields are the `ref`
  source's base attributes, and its `targets` kind exists for it. A bundled view standing beside a
  rendering that already ships is a second rendering of computed data, paying the coupling cost of
  naming bundled vocabulary for nothing.

### 5. Role and skill bodies hold no generated content

- **A role item** stores only what a dedicated verb sets and no document answers: its slug, its
  name (`title`), `description` (the projected mission, ADR-766), `is_default`, a developer's `tech`
  and `model`, `pronouns`, `origin`. Every other field of its definition (job title, mission,
  responsibilities, agreements, colour, spawn authority, skills) resolves from the catalog on every
  read. Its `sq:body` region holds the `sq:view:role_definition` tag, and the definition renders
  from the resolved `RoleDef` at read time.
- **A system (template-owned) skill** body holds its view tag (`squads_skill`, `greeting_skill`,
  `memory_skill`, or `item_skill` for a per-item-type `sq-<type>` skill) and renders at read time.
  The classification is `roster_body_view_name(type, slug, spec)`, never the folder, the item type
  or the `sq-` prefix.
- **A custom (authored) skill body is storage** and is never touched.
- **`title` and `description` stay** on a role item: they are the uniform record read by surfaces
  that do not know the item is a role and cannot resolve a catalog (`sq list`, `sq tree`,
  `sq search`, every `--json` payload, the index, the VS Code client). The test is the reader, not
  the value: materialise only where the reader cannot obtain the value for itself (ADR-781 §2a).
- **A resolved skills list is never stored.** `sq role <slug> show` computes it in its card, and
  the agent pointer carries it as the host's preload setting (ADR-781 §2a).

How these bodies are written, refused and converged is ADR-880's.

### 6. What this does not abolish

squads still writes generated files into another tool's configuration: the backend pointers, the
compiled `CLAUDE.md`/`AGENTS.md` managed regions, the per-entry staging artifacts. Their reader is
an agent host that discovers and configures an entry by reading a file before any agent exists to
run a command, so they stay materialised. They are not views. They are **write-only**:
regenerated wholesale, never read back (`tests/meta/test_a_backend_never_reads_back_its_own_generated_output.py`).
Invariants 5, 6 and 7 and the `AgentBackend` ABC govern them, and what a pointer may contain is
ADR-781's containment rule. The only thing separating them from the role and skill bodies is
**which reader can run a command**.

### 7. Where a view is declared

Views are a keyed section of the **workflow document**: a view's source names a ref kind, a
sub-entity kind or an item type, all workflow-spec vocabulary, and the workflow document carries
the `[selected]` deselect an adopter needs to drop a bundled view. `[views]` is in
`WORKFLOW_TOP_LEVEL_SECTIONS` and `[selected]`'s closed section list, and inherits the merge, the
provenance stamp, content-gated drift (ADR-777) and the collect-all lint report by registration. A
view naming a type, kind or sub-entity kind the merged spec does not declare is a referential
violation caught by the same pass that catches a lifecycle bound to a dropped status.

### 8. The retired regions are removed by a repair-side sweep

The `sq:summary` region and the `<kind>:<local-id>:head` regions are on-disk format that existing
corpora carry. They are removed by a sweep inside `Service.repair()`'s corpus walk, not by a schema
step: `sq migrate up` ends every run in `repair()`, so a squad being migrated gets the sweep, and a
squad already stamped current gets it from the ordinary verb. No `SCHEMA_VERSION` change marks it,
because both corpora load, render and check identically; the strip changes what a file stores, not
what the format means. A corpus carrying the regions keeps loading, showing and checking clean.

**What the sweep may remove** is a frozen list of named retired regions or keys, each of which in
the same build: no live write path produces; no read path consumes as authoritative, its computed
replacement having shipped; and whose content is derived, never authored. Adding a name is a
decision, never made before its writer retires, and a guard asserts that a fresh squad driven
through the write path produces none of them. Emptying is removal under this rule: a body that
must keep its region keeps its markers. The sweep distinguishes by marker **shape**: an unpaired
`sq:view:` tag is never on the list (ADR-880).

**Adopter safety.** A squad that never carried the regions is untouched: the scan matches nothing
and writes nothing. No authored content is reachable: marker regions are sq-managed, and
`reject_markers` refuses any well-formed tag on every write path that puts prose in a region, so an
authored body cannot contain one to be matched. Quoting is not what saves such prose:
`find_markers` matches a well-formed tag inside backticks exactly as it matches a bare one; the
`sq:*` spelling escapes because `*` fails the tag's character class. The sweep reports the files it
touched, in the result and the reflog delta, so the diff it produces is stated, not discovered.

## Consequences

- **`sq search` matches authored text only.** A query no longer matches sub-entity status,
  assignee or story text inside a stored region, nor a role's mission or responsibilities: what is
  lost is a text match over a derived value that could be stale. The per-kind lists and their
  `--json`, and `sq role list` / `sq role catalog` / `sq role <slug> show`, answer those questions
  from the resolver.
- **The refusal FEAT-693 asked for does not exist**, because there is no sink to combine with a
  foreign source. There is nothing to refuse and nothing to test.
- **`sq role <slug> show` prints the definition once**, rendered from the resolved definition; its
  card carries only the resolution facts the prose does not (ADR-781).
- **A view over a foreign source is computed per request**: the index load the request performs
  plus an inversion, the shape `sq tree` and `sq blocked` have always had.
- **ADR-422's local-versus-non-local asymmetry is narrowed, not overturned.** Its ruling stands and
  is reinforced: no persisted per-item derived region. Its factual premise about `:head` is
  corrected.
- **`repair`'s job includes content.** An operator running it over a corpus that still carries a
  retired region gets a content diff, reported as such.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-22T09:30:44Z] `architect` Robert Architect:
  - The body sink does not survive, and the driven evidence is stronger than the argument for it. Four computed renderings of the sub-entity projection already ship and none reads either materialised region; sq task N show --full never prints the :head text at all. The head is not local-source either — it resolves the assignee name from the ROLE item and the story label from the parent feature, and both go stale on a rename with sq sync not healing them.
  - Driven merge: two branches conflict in both the frontmatter subentities list and the :summary table of the same file. Resolve the frontmatter correctly, leave the table at one branch rendering, and sq repair + sq check pass with exit 0 while sq show prints two rows and the file prints one. No verb re-derives the region.
  - So the sink rule is not source locality — it is whether a shipped verb regenerates the region. Two sinks: display (computed) and document (a region of a wholly generated document, enumerated in engine code — role/skill bodies, backend artifacts). sink stops being a declared field, so the refusal FEAT-693 asked for becomes an unrepresentable state instead.
  - One departure from your stated conclusion, flagged for your ruling: a role ## Skills section stays materialised. The backend pointer tells the agent to load @squads/agents/roles/ROLE-....md, so role and skill item markdown IS read directly, by an agent, not only by a human resolving a merge — a computed view never reaches that reader. The stored extra.skills cache still goes, which narrows PERMITTED_EXTRA_SKEW and needs the literal-membership pin in tests/unit/test_role_def_extra_keys.py edited in the same change.
  - FEAT-694 needs reauthoring rather than implementing: its subject inverts to retiring the two regions, byte-identical output cannot be its bar, and a migration IS owed. @product-owner for awareness once this is ruled on; @op-pierre @manager the call is yours.
- [2026-08-22T09:38:26Z] `op-pierre` Pierre Chat:
  - Direction that changes this decision: no materialized claude file may reference a local file path. The generated pointers currently instruct the agent with an @-reference to squads/agents/roles/ROLE-N.md and the skill equivalent; that breaks under remote mode, where there is no local squad directory. Pointers must instead display the sq commands an agent runs at startup, which work the same locally and against a server.
  - This overrules the architect departure on the third consumer. The case for keeping a role ## Skills section materialized was that the pointer makes an agent read the role markdown directly - that reference is itself being removed, so the premise is gone and the section is computed, as originally concluded. Reconsider whether a materialized sink has any consumer left at all once no generated file points at item markdown.
- [2026-08-22T09:48:01Z] `architect` Robert Architect:
  - Amended in place rather than annotated: the decision is Proposed, and sections 1, 4 and 5 asserted a document sink and a departure the direction overrules, so leaving them would have left the decision stating the reverse of the ruling.
  - The collapse is real, and I tested it rather than assuming. Section 4 now enumerates every non-human reader of item markdown: the index rebuild and per-item reads (frontmatter, never a derived region), show and the sub-entity panes (authored prose), sq search (the one survivor, _services/_collab.py:436-441), migration runners (the mechanism that removes a region), the body regenerators (writers), the VS Code client (reads .squads.toml only, everything else is sq --json — driven), and the agent host @ resolver. The @ resolver was the ONLY non-human reader that consumed a derived region as its content, and the direction deletes it. So there is one behaviour and no exception list.
  - One correction to how the collapse was framed: the reader is not deleted so much as moved behind sq. Once the pointer names sq role <slug> show, sq is in the delivery path, which is what makes computing possible for that reader at all. And the computed home already exists — the show card is already computed and already carries a creates: row (_cli/_role.py:324-345), so the skills list is one more row beside it and role.md.j2:18-25 is deleted.
  - Materialisation itself does not vanish, and section 4 says so rather than over-reading the rule: the backend pointers and the compiled managed regions are materialised projections read by a non-human with no sq in the loop, they must stay that way because a host reads files and cannot run commands, and they are write-only and never read back (tests/meta/test_a_backend_never_reads_back_its_own_generated_output.py). They are governed by invariants 5/6/7 and the ABC, never by a view sink.
- [2026-09-01T08:00:03Z] `op-pierre` Pierre Chat:
  - Direction, general rather than case by case: existing files should be shrunk of all duplicated data. The markdown files are the storage; the only read surface is the CLI; and views are the way to present derived content. Anything materialised into a file that the CLI can compute is duplication and comes out.
- [2026-09-01T08:01:03Z] `op-pierre` Pierre Chat:
  - This lands in 0.14, not later: the shrink rides the same migration runner and the same schema bump as the region retirement.
- [2026-09-01T08:13:44Z] `architect` Robert Architect:
  - Amended in place (2026-09-01 note, second one): the shrink rule applied, scoped, and the views fork ruled.
    - In class, exhaustively: the whole `sq:body` region of every role item, and of every SYSTEM skill item; plus the role `extra` mirror keys (title/mission/responsibilities/agreements/color/can_spawn/description/skills, and model for a non-dev role). Out: a CUSTOM (authored) skill body — `releasing-squads` is one in this corpus, 10.1 KB. 22 of our 23 files are in class; a migration keyed on folder/type/`sq-` prefix destroys the 23rd. Key on `is_system_skill(slug, spec)`, which already ships and which `set_body` already uses to refuse exactly these writes.
    - `title`/`description` STAY — uniform-record fields read by surfaces that cannot resolve a role catalog. The duplication inside that pair is `item.title` vs `extra.full_name`: keep the top-level field, drop the extra copy.
    - Views do NOT widen. All three source kinds are relations of one item resolved off the index; a skill body is spec data keyed by item type and a role body catalog data keyed by slug — no relation to invert, and a widening would break the uniform record shape and leave the load-time referential pass with a second document and no clause to apply. These compute at show time through the resolver each surface already has; the deletion half is a call-site move, not new machinery. That is a shape judgement, and it lands whole in this release.
    - Driven, and worse than drift: `sq role qa set-default` is silently reverted by the next `sq sync`, `sq check` exit 0 on both sides — `is_default` is operator-settable AND a catalog mirror key.
    - Three couplings the breakdown needs before the build: `_without_permitted_extra_skew` identifies a role by `extra.mission` (the key we remove); `sq check`'s pointer-currency expectation is built from `RoleDef.from_extra` (the mirror we remove — ADR-781 §2c goes void unless it moves to the resolver); `PERMITTED_EXTRA_SKEW`'s literal test pin.
    - Marker safety holds: the only out-of-region content in a role file is frontmatter and a static `## Discussion` heading; the body is one region already rewritten wholesale every sync. @tech-lead this is the scope for the FEAT-694 breakdown.
- [2026-09-01T08:55:17Z] `architect` Robert Architect:
  - Amended in place, third 2026-09-01 note: the roll-up ships no bundled view either. Tracked, per the audit rule:
    
    - **Added** amendment note §§1-6. §1-2 are the driving (scratch squad at 0.14.0); §3 the ruling; §4 the further narrowing of §6; §5 the reconciliation with the 2026-08-26 refusal; §6 `milestone_rollup` and the discriminator.
    - **§6 narrows again.** "Reissue both projections as computed views" becomes: for the summary half, satisfied by the rendering that already shipped. Its other clauses are untouched.
    - **§5 is unchanged.** Its verdict on the roll-up ("computed") was always right; what changes is that nothing new has to be built to meet it.
    - **The 2026-08-26 refusal is unchanged and unweakened** — §5 of the new note records why neither rescue (degrade-instead-of-refuse, prune-bundled-instead-of-refuse) survives it, so neither is re-proposed cheaply.
    - **Nothing is superseded** and no ref changes: this is a clause-level narrowing inside the same decision.
- [2026-09-01T10:41:16Z] `architect` Robert Architect:
  - Amended in place, fourth 2026-09-01 note: the corpus strip is a repair-side sweep, not a schema step. Tracked per the audit rule:
    
    - **Added** amendment §§1-7. §1 the driving and the stranded population, §2 the ruling, §3 the rule governing what the sweep may remove, §4 the four refused vehicles, §5 the accepted failure mode, §6 adopter safety, §7 the downstream narrowings.
    - **§6 narrows**: "a migration **is** owed" becomes "a corpus sweep is owed". Its other clauses — the inverted subject and the byte-identical-computed-rendering bar — are untouched.
    - **§5 is unchanged.** Its "computed" verdicts stand; what is settled is the mechanism that removes what they replaced.
    - **Nothing is superseded** and no ref changes: a clause-level narrowing inside the same decision.
    
    What decided it, and it is not this release's staging: `adopt` over a folder with no `.squads.toml` stamps the build's own `SCHEMA_VERSION` (`_models/_config.py:23`) and rebuilds from disk, so a corpus can arrive at the current stamp with no runner ever visiting it. The stamp axis cannot be the axis a corpus sweep runs on. `repair` is the only walk that reaches both populations with one implementation, its per-file loop already rewrites content (the ref canonicalization), and the ordering prohibition becomes structural because `require_current_schema` means repair can only run at the current schema and the one behind-schema call is the migration tail.
    
    Two corrections the driving turned up: the corpus carries 1545 balanced head regions across 436 files (the report of zero came from a missing `HEAD` constant in `_models/_markers.py` — the tag is built by `_discussion._head_tag`), and this repository's strip needs no stamp rewind, only `sq repair`.
    
    @tech-lead the rewrite is on TASK-849. @op-pierre the accepted cost, stated rather than mitigated: `sq repair` now rewrites file content as well as the index, so it produces a large announced diff on any corpus still carrying the regions.
- [2026-10-25T21:42:17Z] `architect` Robert Architect:
  - 2026-10-25 audit: body rewritten in present tense; the rule (no derived content stored, every view computed) unchanged. Folded the four 2026-09-01 amendments and the 2026-09-02 correction. The clause "views do not widen; definitions render through their own resolver" is replaced by a pointer to ADR-880, which widened the source grammar (role/playbook/self) and owns roster bodies; related ref added.
<!-- sq:discussion:end -->
