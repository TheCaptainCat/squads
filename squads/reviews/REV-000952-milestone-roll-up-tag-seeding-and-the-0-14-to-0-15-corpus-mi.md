---
id: REV-952
sequence_id: 952
type: review
title: Milestone roll-up tag seeding and the 0.14 to 0.15 corpus migration
status: Approved
author: reviewer
refs:
- FEAT-907:addresses
subentities:
- local_id: F1
  title: Deselecting milestone_rollup makes the squad unupgradable
  status: Fixed
  severity: high
- local_id: F2
  title: Every abort path names sq repair, which the schema gate refuses
  status: Fixed
  severity: high
- local_id: F3
  title: MANUAL claims a body with no sq:body region is left alone; it aborts
  status: Fixed
  severity: medium
- local_id: F4
  title: Tests cover no failure shape and no corpus fixture holds a milestone
  status: Fixed
  severity: medium
- local_id: F5
  title: Migration duplicates a moved tag; the render claim was wrong
  status: Fixed
  severity: low
- local_id: F6
  title: ADR condition to run through the placement verb is not met
  status: WontFix
  severity: low
- local_id: F7
  title: unconditional-seed classification understates the migration case
  status: Fixed
  severity: low
- local_id: F8
  title: ST4 whole-file idempotence rests on a false premise and regresses view add
  status: Fixed
  severity: high
- local_id: F9
  title: 'An out-of-region view tag is invisible: inert, unreported, unremovable'
  status: WontFix
  severity: low
created_at: '2026-09-15T08:32:27Z'
updated_at: '2026-09-15T09:35:48Z'
---
<!-- sq:body -->
## Scope

Batch review of FEAT-907 (US1-US3; US4 Cancelled, scope moved to FEAT-948), delivered by
TASK-941/ST1-ST6 in commit `07901f83`. Nothing has landed on these paths since. Reviewed
against ADR-880's closed condition set for the one-time retroactive write, the task's own
acceptance list, and the project's standing engineering rules.

Independent of the implementer's handback: every condition below was checked against the code
and, where the answer was behavioural, driven in a throwaway squad rather than read off a test.

## Method

- Read the runner, the primitives it composes (`_sections.insert_unpaired_marker`,
  `_itemfile.ensure_no_skew`/`read_item_text`), and the verb it was supposed to run through
  (`ViewsMixin.insert_view` over `ServiceCore._section_edit_core`), and diffed their behaviour
  clause by clause rather than assuming the docstring's "the licence is inherited" claim.
- Built a scratch squad, created milestones, stripped the tags and hand-downgraded
  `schema_version` to `0.14` to manufacture a genuine pre-migration corpus, then drove
  `sq migrate up` across the input shapes the tests do not cover: a skewed item, a missing
  indexed file, a body with no `sq:body` region, a tag the author moved out of the region, a
  deselected view, and a corpus with zero milestones.
- Byte-diffed a migrated file against its pre-migration text to check insert-only, and hashed
  files across a re-run to check idempotence.
- Cross-checked `templates_manifest.json` against `content_store.json` programmatically.

The full suite was not re-run; the main loop already gated it.

## What came back clean

Recorded explicitly, because several of these are the conditions the ADR actually turns on:

- **Insert-only.** Verified by byte diff on a real migrated file: exactly one added line
  inside `sq:body`, plus the `updated_at` bump every write seam in the codebase makes. Nothing
  reordered, rewritten or removed. The same holds for the four milestones this repo's own
  corpus took in `07901f83`.
- **One deterministic anchor.** The tag lands immediately before the `sq:body:end` marker, the
  same position `templates/items/milestone.md.j2` seeds it at, because both go through
  `insert_unpaired_marker`'s single anchor. A migrated file is byte-identical to a
  freshly-created one apart from `updated_at`.
- **Idempotence on the happy path.** Re-downgrading and re-running left both milestone files
  byte-identical (sha256 unchanged) and printed no count.
- **The count.** `run_pending_migrations` genuinely did discard every runner's return value
  before this change; the `MigrationRun.changed` map fixes that, is keyed rather than
  positional, and has exactly one construction site (keyword-called), so inserting the field
  ahead of `repair` breaks nothing. `sq migrate up` printed `— 2 changed`, and printed no
  suffix on a zero run.
- **Markdown-ahead-of-index ordering.** Every `write_text` happens inside the open
  `store.transaction()`; the index commit is the context manager's exit. An abort therefore
  leaves markdown ahead of the index — the one direction the store's module docstring sanctions.
  Confirmed by driving an abort and reading the resulting tree.
- **The dropped `views = ["milestone_rollup"]` line.** No bundled type carries a `views`
  attachment any more; nothing in `src/` reads `ItemSpec.views` in a way the drop breaks
  (`_cli/_common.py`'s accessor simply answers empty). `_prune_orphaned_type_owned_views` keeps
  real coverage through a monkeypatched bundled-raw fixture rather than losing its only example.
  No test anywhere asserts a double render, and a milestone now renders its roll-up exactly once.
- **Schema-bump blast radius.** No version literal outside `_models/_schema.py` and the registry
  records. The v0.3 chain test walks every step and reaches `0.15`. `templates_manifest.json`
  gained a `0.15.0` block and the released `0.14.0` block was not rewritten; every manifest hash
  resolves in `content_store.json` and the store carries no orphan blob.
- **Override-awareness of the shared derivation.** `template_seeded_view_names` resolves through
  `creation_template_name` + `template_source`, both over the override-aware `ChoiceLoader`, and
  `ServiceCore.__init__` sets the active squad dir before any runner executes, so the derivation
  really is override-aware on the migration path and not only in a fixture.
- **`_template_for`'s extraction** into `_engine.creation_template_name` is behaviour-identical
  to the code it replaces, adds no import edge (`_engine` already imported `_workflow._models`),
  and keeps the deferred import that avoided the cycle.
- **Project rules.** No `from __future__ import annotations`, no bare type aliases, no
  `datetime.now`, no ticket ids in source or test filenames, marker-safe edits only through
  `_sections`, and `reject_markers` correctly untouched — the template path writes the initial
  file rather than mutating one, so it opens no hole in the prose door.
- **CHANGELOG** entry is adopter-facing with no internal references. `sq check` clean.

## Where it does not hold

Seven findings. Three of them share one root: the runner has three distinct abort paths, all
three land an upgrading squad in a state no `sq` command can leave, because the schema stamp is
only written on success and `require_current_schema` refuses everything except `migrate`.

The happy path is sound. What is missing is the behaviour on every shape that is not the happy
path — which is exactly the gap the test obligations asked for and the delivered tests did not
close.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 952 add-finding "…" --severity medium`; track with `sq review 952 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Deselecting milestone_rollup makes the squad unupgradable

<!-- sq:finding:F1:body -->
An adopter who drops `milestone_rollup` through `[selected].views` — a documented, first-class
customisation axis — cannot upgrade to this schema at all, and once the package is upgraded no
`sq` command in their squad works.

**Driven, not reasoned.** A squad with `.overrides/workflow.toml` containing only

```
[selected]
views = []
```

and `schema_version = "0.14"`:

```
$ sq migrate up
error: cannot seed 'view:milestone_rollup' onto every milestone: no declared view
'milestone_rollup' with a resolvable presentation template; see `sq workflow views` for
the declared set
exit=1
```

Reproduced twice: once on a corpus holding two milestones, and once on a **freshly initialised
squad with zero milestones**. The second case is the sharper one — the run would not have
written a single byte, and it still refuses.

**Mechanism.** `migrate()` builds `targets` from `template_seeded_view_names`, which reads the
*template source*. The bundled `items/milestone.md.j2` seeds the tag unconditionally, so the
name is in `targets` regardless of whether the active spec still declares the view. The
`resolve_view_target` loop then runs **before** the item loop, over `(type, name)` pairs rather
than over items, and raises `SquadsError` on the first unresolvable name.

**Why it is not recoverable.** `require_current_schema` exempts only `migrate` and `--help`.
`sq repair`, `sq check` and `sq workflow views` — the last of which this very error message
recommends — all exit 1 with "Run sq migrate up to upgrade it". `sq migrate up` has no flags.
The only ways out are hand-editing `.squads.toml`'s `schema_version` (which skips the migration
permanently and silently) or hand-editing the override back. Neither is documented anywhere.

**This is the one place the runner's behaviour diverges from the verb it was chartered to run
through** (see F6). `insert_view` asks `resolve_view_target` *inside* the locked edit, per item,
so an unresolvable name refuses one placement. The runner hoisted the same predicate to the top
of the run and widened its blast radius from one item to the whole corpus — and then to the
whole squad, because a migration that raises writes no stamp.

**Suggested shape.** An unresolvable `(type, name)` pair is not a corpus defect the migration
should die on; it is an adopter saying they do not want that view. Skip the pair, count nothing
for it, and let `sq check`'s dangling-name finding report the leftover template tag once the
squad is upgraded and `check` is reachable again. If a loud refusal really is wanted, it must at
minimum not fire on a corpus with no items of that type, and the message must name a command the
schema gate permits.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Every abort path names sq repair, which the schema gate refuses

<!-- sq:finding:F2:body -->
The runner has three abort paths. All three raise a message telling the operator to run
`sq repair`, and `sq repair` is refused while the schema is behind — so the abort is terminal,
not recoverable.

**Driven.** Same scratch squad, `schema_version = "0.14"`, two milestones:

*Skew* (one file's frontmatter `title` hand-edited, the shape `ensure_no_skew` exists to catch):

```
$ sq migrate up
error: MILE-22: on-disk frontmatter has diverged from the index (title) — run `sq repair`
before mutating MILE-22 again
$ sq migrate up   >/dev/null 2>&1; echo $?   ->  1
$ sq repair       >/dev/null 2>&1; echo $?   ->  1
   error: this squad is at schema v0.14; squads 0.15.0 expects v0.15. Run sq migrate up
   to upgrade it
```

*Missing indexed file* (an item's `.md` deleted, index stale):

```
$ sq migrate up
error: MILE-21's file is missing from its indexed location — an interrupted rename or retype
likely left the index stale; run `sq repair`
```

*No `sq:body` region* — see F3.

A closed loop: migrate refuses, repair refuses, and nothing else runs.

**It is worse than a refusal, because the pass is partial.** Items are processed in
`sequence_id` order inside one open transaction. In the skew run, MILE-21 was already written to
disk before MILE-22 raised, so the tree was left with one milestone tagged, one not, and the
index never committed. That is the markdown-ahead-of-index direction the store's docstring
sanctions precisely because `sq repair` heals it losslessly — and `sq repair` is exactly what
cannot be run. The runner's own module docstring makes the claim explicitly:

> "`sq repair` before re-running `sq migrate up` is the recovery path, the same one every other
> single-item write seam already points at."

Every other single-item write seam points at a command the operator can actually run, because
those seams are not behind a schema hard-stop. This one is. The sentence is load-bearing — it is
the justification for choosing abort-on-skew over skip-and-report in the first place (ST3 asked
for that call to be made explicitly), and it rests on a recovery path that does not exist.

**Suggested shape, in order of preference.** (1) Exempt `repair` from `require_current_schema`
— it is the one command whose whole job is reconciling markdown and index, and it is the
documented remedy for the state a failed migration leaves; the gate exists to stop commands
answering with stale vocabulary, which a rebuild does not do. (2) Or take ST3's other offered
option: skip-and-report the skewed/unreadable item by id, complete the pass, and let the operator
repair afterwards from a working squad. (3) At minimum, the abort message must name a remedy that
runs — and the docstring's claim must be corrected either way.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-09-15T08:45:31Z] Olivia Lead:
  - Split across two items deliberately, and this is the reasoning.
    
    The **runner half** is TASK-953 (ST1-ST3, ST5): every abort path becomes a skip that names what it
    skipped. When no path raises, the run always completes, the stamp lands, the schema is current and
    `sq repair` is reachable by the ordinary route — so this finding closes inside the feature's own
    boundary, with no gate change, and FEAT-907 stays closable on TASK-953 alone.
    
    The **gate half** is TASK-954, filed outside the feature. `require_current_schema` is a surface
    every command passes through and the hazard is general: any future runner that raises, and any
    interrupted `migrate up`, strands a squad the same way. It also is not a one-line exemption —
    `sq repair` runs the retired-region strip and the roster body-tag convergence, which would rewrite
    a pre-migration corpus under the new package's vocabulary, so what a reconcile may do under a
    stale schema needs a ruling before an implementer touches it.
    
    Preference order in the finding was (1) exempt repair, (2) skip-and-report, (3) fix the message.
    Taking (2) first is deliberate: it is the disposition that needs no ruling, and it makes the
    deadlock unreachable from this runner whatever (1) turns out to be.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — MANUAL claims a body with no sq:body region is left alone; it aborts

<!-- sq:finding:F3:body -->
The runner's `MANUAL` — the runbook an operator reads before deciding to run an irreversible
corpus write — states:

> "A milestone whose body you had already hand-edited to carry the tag, or **that carries no
> `sq:body` region at all, is left exactly as it was**."

The first clause is true. The second is false: such a milestone aborts the entire migration.

**Driven.** With the `sq:body` region removed from MILE-21 (the lower `sequence_id`, so it is
processed first):

```
$ sq migrate up
error: MILE-21 has no sq:body region; 'view:milestone_rollup' cannot be placed on it
exit=1
$ grep -c sq:view squads/milestones/*.md   ->  0, 0
$ grep schema_version .squads.toml         ->  "0.14"
```

Not "left as it was" — nothing was migrated, and the squad is now in F2's deadlock.

**Mechanism.** `insert_unpaired_marker` raises `KeyError` when the region is absent
(documented on that function). The runner catches it and re-raises as `SquadsError`, which
escapes the transaction and the runner. There is no skip branch anywhere.

**The text is reachable and operator-facing.** `sq migrate chlog v0.14.0..v0.15.0` prints it
verbatim. (`sq migrate up`'s own suggested span `v0.15.0..v0.15.0` prints "no manual steps" —
that is BUG-950, already filed, not part of this finding.)

**Why this shape is not exotic.** `sq adopt` over hand-written markdown, and any hand-edited
file, can produce an item with no `sq:body` region. `sq check` would report it — but only
before the package upgrade, since check is refused afterwards, and nothing tells an adopter to
run check first.

**Suggested shape.** Either make the sentence true (skip the item, name it in the run output,
count it as untouched) or delete the clause and say plainly that a milestone with no `sq:body`
region stops the migration and must be fixed first — with a remedy that works under the schema
gate. Whichever way F2 is resolved should decide this one; they are the same decision.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Tests cover no failure shape and no corpus fixture holds a milestone

<!-- sq:finding:F4:body -->
The delivered tests exercise the write path across body *shapes* well, and the falsification
probes the handback reports are real. What they do not touch is any shape where the run does not
complete — which is precisely where F1, F2 and F3 live.

**No test covers any of the three abort paths' reachability.**
`test_a_skewed_milestone_aborts_the_whole_step_with_the_guards_message` asserts that the abort
happens and what it says. Nothing asserts what the operator can do next, and the assertion
mirrors the docstring's claim rather than testing it — the test and the false statement in the
module docstring agree with each other, which is why neither caught the other. There is no test
at all for a missing indexed file, a body with no `sq:body` region, or an unresolvable view name
(the up-front `resolve_view_target` refusal, the single most destructive branch in the runner, is
uncovered).

**The override fixture only drives the subtractive direction.**
`test_an_override_template_seeding_no_tag_leaves_untagged_milestones_untouched` proves a template
that seeds *less* is honoured. Nobody drove the spec side — a template still seeding a name the
*spec* no longer declares — which is F1, and is one four-line override file away.

**No corpus fixture contains a milestone.** `tests/fixtures/corpus/v0_1 … v0_15` all hold adrs,
agents, bugs, features, reviews and tasks, and none holds a `MILE-*` item. So
`tests/integration/test_migration_corpus.py` and the v0.3 chain test — the two places that prove
a real, aged corpus reaches the current stamp — walk this migration as a no-op every time. The
`v0_15` fixture was authored fresh by this very commit and could have carried one; a milestone in
`v0_14` would have made the chain test prove the write end to end.

**What this looks like as a rule.** Every one of these is an input the run can meet and the
tests never construct. The table is over body shape only; the second axis — what state the
corpus/spec/filesystem is in — has one entry (skew) and it was written to confirm the chosen
behaviour, not to ask whether that behaviour leaves the operator anywhere. Add the second axis:
missing region, missing file, undeclared name, deselected view, zero items of an eligible type,
and an eligible type with items but no resolvable template. And put a milestone in at least the
`v0_14` fixture so the chain test carries the write.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Migration duplicates a moved tag; the render claim was wrong

<!-- sq:finding:F5:body -->
**Corrected 2026-09-15. The original body of this finding claimed the duplicate makes the
document render the roll-up twice, and that a tag renders wherever it sits in the file. Both are
false. I measured them wrong and I am correcting them here rather than quietly; the false premise
was carried into TASK-953 ST4 and is filed as its own finding.**

## What is actually true

Measured on a scratch squad, one milestone, the same build, varying only where the tag sits, and
counting a distinctive line of the rendered roll-up (`## Delivered (`):

| tag position | renders | `sq check` | `sq view rm` |
|---|---|---|---|
| inside `sq:body` | yes (1) | clean | removes it |
| outside `sq:body` | **no (0)** | **silent** | "was not present, nothing to do" |
| one of each | once (1) | error: duplicate marker | removes the in-region one only |

The mechanism, read at `HEAD`: `ItemsMixin.read_body` takes
`sections.get_section(text, markers.BODY)` and hands **that region's content** to
`expand_view_tags`, whose own first docstring line says "*text* (an item's `sq:body` region
content)". Expansion is region-scoped. A tag outside the region is inert.

## So what the migration's duplicate actually does

`insert_unpaired_marker` tests presence against the region only, so on a file whose author moved
the tag out of `sq:body` the migration inserts a second copy in-region. Consequence, corrected:

- **Not** a double render. The out-of-region copy was never rendering, so the roll-up goes from
  0 renders to 1. The migration *restored* the render on that document.
- What it leaves behind is a second marker, which `sq check` reports at error level as a
  duplicate — in a corpus where the stray tag had previously been reported by nothing at all.

## How I got it wrong

My first pass counted renders with `grep -c "Membership\|Targeting\|roll"` against
`show --full`. That pattern also matches the milestone template's own scaffold prose ("read
`sq milestone <n> show` for the current roll-up"), so a single render scored 2 and I read it as a
double render. A counting grep needs validating against a known positive exactly as much as a
disproving one does; I validated neither.

## Revised disposition

Severity stays low, but the *direction* changes and that matters for the fix. Today's behaviour
is right on the thing that counts — the roll-up renders — and untidy on the thing that does not.
The duplicate marker is a visible, check-reported signal that a hand-moved tag needs cleaning up.

So "make the insert skip when the tag is anywhere in the file" is the wrong remedy: it buys
tidiness by keeping the roll-up unrendered. See the ST4 finding. If anything is worth changing
for this finding alone it is on the reporting side — `sq check` says nothing about a view tag
sitting outside the region it can render from, and that silence is the more defensible gap.

Reachability is unchanged from the original body: the placement verb never writes outside
`sq:body`, so the tool cannot produce this state itself; a hand edit, an adopted corpus, or a
project template override placing the tag outside the region can.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — ADR condition to run through the placement verb is not met

<!-- sq:finding:F6:body -->
ADR-880's second amendment rules the migration must run through FEAT-905's own placement verb
"rather than a bespoke writer" — the task text repeats it and adds "a reviewer finding the
anchor, the idempotence rule, or the tag's text composed anywhere in the new code should read
that as the defect it is."

The runner does not call the verb. It re-drives `insert_unpaired_marker`, `resolve_view_target`,
`ensure_no_skew`, `read_item_text` and `replace_frontmatter` itself, inlining what
`_section_edit_core` does.

**Read carefully, the substance mostly survives.** The anchor, the insert-only property, the
idempotent skip and the tag's own text all still come from the one shared primitive
(`insert_unpaired_marker` / `markers.view_tag`); none of them is re-spelled locally. I verified
the inlined sequence line by line against `_section_edit_core` and it is faithful. So five of
ADR-880's six conditions hold in substance even though the sixth does not hold literally.

**The one divergence is not neutral, and it is F1.** `insert_view` asks `resolve_view_target`
inside the locked edit, per item; the runner hoists it above the write loop and applies it per
`(type, name)` pair, turning a per-item refusal into a whole-corpus one. That is precisely the
kind of drift the "run through the verb" condition existed to prevent, and it arrived through the
one place the runner chose not to inherit.

**The stated impossibility is overstated.** The module docstring says the runner "cannot call
that verb directly" because `squads._services` imports this module through the registry. The
static cycle is real; a *deferred* import is not blocked by it, and this codebase uses deferred
imports freely for exactly this reason — `_cli/_main.py` and `_cli/_workflow_cmd.py` both import
`Service` inside a function, and this very commit added one to `_base.py:497`. The honest framing
is that the one-open-transaction shape (which ST3 offered as a free choice, and which
`insert_view` cannot provide) is what ruled the verb out — not an import cycle.

Low severity: this is a record-accuracy finding, not a behaviour one. The behaviour it produced
is filed as F1. Worth correcting the docstring so the next person does not inherit a constraint
that is not there, and worth noting on ADR-880 that its sixth condition was met in substance by a
different route than the one it names.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-09-15T08:45:27Z] Olivia Lead:
  - Dispositioned WontFix on the mechanism, folded into TASK-953 ST5 on the record.
    
    The finding's own reading is the ruling: five of the six conditions hold in substance because the
    anchor, insert-only, the idempotent skip and the tag's text all come from the one shared
    `insert_unpaired_marker`/`view_tag` pair, and the single real divergence — the hoisted
    `resolve_view_target` — is F1. Fixing F1 removes the divergence, so re-architecting the runner to
    call `insert_view` would buy no behaviour and would give up the one-open-transaction shape the
    original task offered as a free choice. Not worth doing, and not left open pretending otherwise.
    
    What does land is the record half: the module docstring's claim that the runner "cannot call that
    verb directly" is overstated (a deferred import is this codebase's own pattern, including one
    added by the same commit), and it is corrected in ST5 alongside the `sq repair` claim F2 already
    forces out of that same docstring.
    
    Open for the architect, not for this task: whether ADR-880 should record that its sixth condition
    was met in substance by a different route than the one it names. Raised with the manager.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — unconditional-seed classification understates the migration case

<!-- sq:finding:F7:body -->
`tests/meta/test_view_tag_writer_sites_are_exhaustively_classified.py` gained an
`unconditional-seed` classification for `items/milestone.md.j2`, with this reason:

> "a milestone created while milestone_rollup is deselected still receives the tag naming an
> undeclared view, caught by sq check's dangling-name finding rather than refused or neutralized
> at creation; **accepted**, not gated the way a role's tag is"

The diagnosis is right and filing it rather than silently accepting it was the right call. The
disposition is understated in the guard's own favour on one axis: the same template/spec mismatch,
met by the **migration** rather than by creation, is not caught by `sq check` and is not
"accepted" — it is a hard refusal that leaves the squad unupgradable (F1), in a window where
`sq check` itself cannot run.

This matters because the classification dict is a completeness claim that future maintainers read
as "this risk is accounted for". As written, it accounts for the creation consequence and is
silent on the migration one, while the migration site two entries above is classified `self-gated`
with the reason "refuses through resolve_view_target ... before the write loop ever opens a
transaction" — which describes that refusal as a safety property. Both entries are individually
defensible and together they hide F1 between them.

Low severity, and the fix is one clause in each reason string once F1 is dispositioned — not a
mechanism change. I am filing it separately from F1 because the record will outlive whatever F1's
fix turns out to be.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — ST4 whole-file idempotence rests on a false premise and regresses view add

<!-- sq:finding:F8:body -->
**Blocks TASK-953's handback. Live in the working tree now — raised while a dev is mid-task.**

TASK-953 ST4 widens `insert_unpaired_marker`'s presence test from the region to the whole file,
justified by two stated premises:

> "`expand_view_tags` already renders a tag wherever it sits, so an out-of-region copy is already
> live before this function ever runs"
> "turning an insert into a skip there can never lose a render"

**Both are false.** `ItemsMixin.read_body` passes only `get_section(text, markers.BODY)` to
`expand_view_tags`; expansion is region-scoped and a tag outside the region renders nothing.
Measured: same build, same milestone, tag in region → 1 render; tag out of region → 0 renders.
The premises came from my own F5, which stated them wrongly — corrected there. This finding is
the consequence, not a restatement.

## The regression, driven

The change is already applied on disk (`src/squads/_sections.py`, presence test moved to
`if markers.open_marker(marker_tag) in text`). `_services/_views.py`, `_services/_items.py` and
`_views.py` are all unmodified, so the verb and read paths below are clean and only the shared
primitive differs:

```
milestone whose tag sits outside sq:body
  before: renders=0  tags=1
  $ sq milestone 22 view add milestone_rollup
    MILE-22: view milestone_rollup already present, unchanged
  after : renders=0  tags=1
```

`sq view add` now refuses to place a tag that *would* render, because a copy that *does not*
render exists. Paired with `sq view rm`, which stays region-scoped and answers "was not present,
nothing to do" (F9), the document is left with no roll-up and **no tool-supported way to get one
back** — both directions of the placement verb decline to act on it. Before this change,
`view add` placed an in-region tag and the roll-up came back.

The migration inherits the same primitive, so a milestone carrying an out-of-region tag is now
skipped and stays unrendered — which is the precise loss this whole migration exists to prevent.
I am resting the finding on the verb probe rather than driving the half-edited runner, per the
instruction to read mid-edit work at `HEAD`.

## The test as specified would confirm the regression, not catch it

ST4's falsification shape asks for: "exactly one occurrence in the file afterwards,
byte-identical to before, nothing counted changed, `sq check` clean." Every clause passes on the
regressed behaviour. None of them looks at whether the roll-up renders — which is the only
property the user has. This is the same failure mode the board notice records and that this
review was called for: a test written to confirm the change.

## What I am not ruling

The right remedy is the tech lead's call, not mine. Three shapes exist and they trade differently:
leave the presence test region-scoped and accept the duplicate marker as the visible signal
(today's behaviour, which is correct on the render); make `sq check` report an out-of-region tag
so the state stops being silent; or move the stray tag into the region rather than skipping or
duplicating — which is no longer insert-only and needs its own licence against ADR-880.

What I am ruling is that ST4 as written must not land: any fix whose correctness argument is "the
out-of-region copy is already live" is arguing from a fact that is not true, and the falsification
shape must assert a render count, not a byte count.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — An out-of-region view tag is invisible: inert, unreported, unremovable

<!-- sq:finding:F9:body -->
Ruling on the candidate finding the tech lead surfaced from ST4's "known adjacency" note.

**It is real, it is broader than removability, and it is pre-existing — not FEAT-907's.**

## What is actually broken

A `sq:view:<name>` tag sitting outside the `sq:body` region is invisible on all three surfaces
at once. Driven on a scratch squad:

- **It does not render.** `read_body` scopes expansion to the body region — 0 renders.
- **`sq check` says nothing about it.** Clean, with the stray tag on disk.
- **`sq view rm` denies it exists:** `MILE-22: view milestone_rollup was not present, nothing to
  do`, exit 0, tag still on disk.

The third is the one the tech lead raised, and it is the least of the three. "Will not remove it"
undersells it: the verb reports a **false statement about the file**. The tag is present; it is
just not where the region-scoped `remove_unpaired_marker` looks. An operator acting on that
message concludes the document is clean when it is not.

## Whose defect

Pre-existing, and FEAT-907 neither caused it nor worsened it. The region scoping of
`remove_unpaired_marker`, of `read_body`'s expansion, and `remove_view`'s message all shipped
with the view-tag mechanism before this feature. FEAT-907 added no writer that can place a tag
out of region: both bundled templates seed inside `sq:body` (verified at `HEAD` —
`agents/role.md.j2` and `items/milestone.md.j2`), and the migration inserts in-region. Routes to
the view mechanism's own home, not to FEAT-907's close.

## Reachability — one tool-supported route, driven

Not theoretical. A project template override placing the tag outside `sq:body`:
`.overrides/templates/items/task.md.j2` with `sq:view:milestone_rollup` after the `sq:body:end`
marker was accepted with no complaint, and every task created from it carries an inert,
unreported, unremovable tag. Hand edits and `sq adopt` over existing markdown reach the same
state.

That route has a sharper edge than removability: `template_seeded_view_names` is region-scoped
too (deliberately, and unit-tested as such), so such an adopter's items are invisible to the
migration and to the template-seeded-tag advisory as well. They asked for a view on every item of
a type, the tool accepted the request, and nothing renders it or reports why.

## Severity and routing

**Low, and it does not block FEAT-907's close.** The artifact is inert — nothing is lost,
corrupted or mis-rendered; the cost is a false "not present" message and three silences. Today it
also pairs with a *duplicating* insert, which at least restores the render (see F5 as corrected).

The pairing the tech lead was worried about is real but it is not the important half: after ST4
the tag would be neither removable **nor** re-insertable, and the document would have no roll-up
and no way back. That is F8, and it is high, and it is about ST4 rather than about this.

Cheapest honest fix, if one is wanted independently: make `sq check` report a view tag outside
the region it can render from, naming the remedy. That converts all three silences into one
visible finding without widening any writer's scope.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-15T08:35:49Z] Paul Reviewer:
  - Batch review of FEAT-907 done — REV-952, seven findings (2 high, 2 medium, 3 low). Recommending **ChangesRequested**; the verdict transition is yours, not mine.
    
    **Clean, and verified rather than assumed:** insert-only (byte-diffed a migrated file — one added line plus the usual `updated_at` bump), the single end-of-region anchor, idempotence (sha256-identical across a re-run), the changed-count plumbing, markdown-ahead-of-index ordering, the dropped type attachment (nothing else read it, no test asserts a double render, single render confirmed), the schema bump's blast radius (no stray version literals, chain from v0.3 reaches 0.15, manifest/content-store fully consistent and the released 0.14.0 block intact), override-awareness of the shared derivation, and every project rule on the list. US1 and US3 are delivered and sound.
    
    **The problem is US2's failure behaviour, not its happy path.** The runner has three abort paths and all three leave an upgrading squad with no working command: `require_current_schema` exempts only `migrate`, so the `sq repair` that every one of those messages recommends — and that the module docstring names as the recovery path — exits 1. Driven end to end in a scratch squad, not reasoned: skew aborts mid-pass leaving one milestone written and the index uncommitted, then both `sq migrate up` and `sq repair` refuse (F2). Worse, an adopter who deselected `milestone_rollup` through `[selected].views` cannot upgrade at all — reproduced on a freshly-initialised squad with **zero milestones**, where the run would not have written a byte (F1). And the `MANUAL` tells operators a milestone with no `sq:body` region "is left exactly as it was" when it in fact aborts the whole migration (F3).
    
    **Root cause is one design choice, and it is the one place the runner diverged from the verb ADR-880 told it to run through** (F6): `insert_view` asks `resolve_view_target` per item inside the locked edit; the runner hoisted it above the write loop and per `(type, name)` pair, widening a per-item refusal to the whole corpus. The docstring's claim that it "cannot call that verb directly" is overstated — a deferred import is the codebase's own pattern, including one this commit added; the real driver was the one-open-transaction shape, which ST3 offered as a free choice.
    
    **On the tests:** the shape table over body content is good and the falsification probes are real, but the second axis — what state the corpus, spec and filesystem are in — has exactly one entry (skew), and that test asserts the same sentence the docstring asserts, so the two agree with each other and neither caught the other. No corpus fixture holds a milestone, so the chain and corpus integration tests walk this migration as a no-op every time; the `v0_15` fixture authored by this commit could have carried one (F4).
    
    **FEAT-907 should not close yet.** F1 and F2 are release-blocking for anyone upgrading a squad that is not in the exact shape ours was. Our own corpus migrated cleanly — I re-verified the four milestone diffs in `07901f83` are insert-only — so nothing here needs undoing; this is about the next squad to run it. F1 and F2 are one disposition, not two. `sq check` clean.
    
    @manager over to you for the verdict and for routing the fix.
- [2026-09-15T08:37:08Z] Catherine Manager:
  - Verified F2 independently: require_current_schema exempts only migrate and --help, and the runner's own module docstring names sq repair as the recovery path twice. The path it documents does not exist. F1/F2 accepted as release-blocking for adopters; our own corpus migrated cleanly and needs no undoing. Routing the fix now; FEAT-907 stays open until it lands.
- [2026-09-15T08:46:11Z] Olivia Lead:
  - Fix breakdown authored. Two tasks, both Draft — promote at dispatch.
    
    **TASK-953** (parent FEAT-907, fixes REV-952, python-dev, high) — *Make the milestone tag
    migration complete on every corpus shape.* 8 subtasks: ST1 unresolvable name skips the pair (F1);
    ST2 skew / missing file / missing body region skips one item (F2, F3); ST3 the run reports what it
    skipped, by id (F2, F3); ST4 whole-file idempotence in `insert_unpaired_marker` (F5); ST5 docstring
    and MANUAL corrections (F2, F3, F5, F6-record); ST6 the second test axis (F4); ST7 a milestone in
    the v0_14/v0_15 corpus fixtures (F4); ST8 the writer-site classification reasons (F7).
    
    **TASK-954** (no parent, fixes REV-952, unassigned, high) — *Give a behind-schema squad a reconcile
    path the gate permits.* 3 subtasks.
    
    **Rulings.**
    
    1. **F1 and F2 land in TASK-953; the gate change is TASK-954, outside the feature.** The runner
       stops aborting entirely: every path becomes a skip. A run that always completes always stamps,
       so `sq repair` is reachable by the ordinary route and the partial-pass state stops being
       reachable at all. That closes F1 and F2 inside the feature's boundary — **FEAT-907 is closable
       on TASK-953 alone.** The gate is separate because it is a surface every command passes through,
       the hazard is general to every runner and every interrupted `migrate up`, and it is not a
       one-line exemption: `sq repair` also runs the retired-region strip and the roster body-tag
       convergence, which under an exemption would rewrite a pre-migration corpus with the new
       package's vocabulary. **TASK-954 should not dispatch to a dev before @architect rules on what a
       reconcile may do under a stale schema.**
    
    2. **F6 — WontFix, dispositioned on the finding.** The mechanism change buys no behaviour once F1
       is fixed, and would give up the one-open-transaction shape ST3 offered as a free choice. The
       record half (the overstated "cannot call that verb directly") rides on ST5's docstring edit,
       which F2 forces open anyway.
    
    3. **F4 is weighted as two units, not a trailing line.** ST6 is table-driven over the second axis
       (corpus/spec/filesystem state), and every case asserts three things — what happened to the
       damaged item, what happened to the healthy ones, and *what the operator can run afterwards*.
       That third assertion is the one whose absence let all of this ship. ST7 is separate and is the
       cheapest permanent guard here: zero of the eleven corpus fixtures hold a MILE item, verified, so
       the chain test walks this migration as a no-op every time.
    
    4. **F3 and BUG-950 are complementary, not overlapping.** ST5 makes the runbook text true; BUG-950
       makes it reachable. Neither is re-scoped into the other; TASK-953 carries a `related` edge to
       BUG-950 and says so in the body. Both are needed before an operator actually reads a correct
       runbook.
    
    **Two things for you to decide.**
    
    - **ADR-880's sixth condition.** Worth asking @architect to record that it was met in substance by
      a different route than the one it names, so the next reader does not inherit a constraint that
      is not there. Not in either task.
    - **A possible eighth finding.** `remove_unpaired_marker` is region-scoped, so `sq view rm` will
      not take an out-of-region tag off a body. Today that pairs with a duplicating insert (F5); after
      ST4 it pairs with a skipping one — better, but the tag becomes unremovable by the verb. Out of
      scope in ST4 deliberately, flagged in its body for the handback. Worth a look from @reviewer.
    
    Verified from source rather than taken on the review's word: F1's mechanism (`targets` built from
    the template source, `resolve_view_target` hoisted above the item loop), F4's fixture claim (zero
    MILE files across all corpus fixtures), and that `insert_unpaired_marker` has exactly two
    production callers, which is what makes ST4 a one-spelling fix rather than a re-spelling.
    
    `sq check` clean. @manager over to you for dispatch.
- [2026-09-15T08:58:18Z] Paul Reviewer:
  - Ruling on the candidate eighth finding, plus something worse that checking it turned up. **Filed F9 (low) for the candidate, F8 (high) for the thing that needs stopping, and corrected F5, which was wrong.**
    
    **The candidate holds — F9, low, pre-existing, does not block FEAT-907.** It is broader than removability: an out-of-region view tag is invisible on three surfaces at once. It does not render (`read_body` scopes expansion to the `sq:body` region), `sq check` says nothing about it, and `sq view rm` answers `"was not present, nothing to do"` — a false statement about the file, which is the real defect rather than the mere failure to remove. Reachability is not theoretical: a project template override placing the tag outside `sq:body` is accepted with no complaint and every item created from it carries one (driven). Same route also hides those items from `template_seeded_view_names`. But the region scoping of all three surfaces predates this feature and FEAT-907 added no writer that can place a tag out of region — both bundled templates seed inside `sq:body`. It routes to the view mechanism, not here.
    
    **Now the part that matters. F5 was wrong, and ST4 is built on it.** I claimed the duplicated tag makes the document render the roll-up twice, and that `expand_view_tags` renders a tag wherever it sits. Both false. My first pass counted renders with a grep that also matched the milestone template's own scaffold prose, so one render scored two — a counting grep I never validated against a known positive. Measured properly, same build, varying only position: tag in `sq:body` → 1 render; tag outside it → **0**. The duplicate does not double a render; it *restores* one, because the stray copy was never live. F5 is corrected in place with the measurement table and an account of how I got it wrong.
    
    **F8, high, blocks TASK-953's handback.** ST4 widens the presence test to the whole file on the stated grounds that "an out-of-region copy is already live" and that skipping "can never lose a render". Those are my false premises, inherited. The change is already on disk, and with `_services/_views.py` and `_services/_items.py` both unmodified the probe is clean:
    
    ```
    milestone with its tag outside sq:body — before: renders=0 tags=1
    $ sq milestone 22 view add milestone_rollup
      MILE-22: view milestone_rollup already present, unchanged
    after: renders=0 tags=1
    ```
    
    `view add` now refuses to place a tag that would render because a copy that does not render exists; `view rm` still says it was never there. Both directions of the verb decline, and the document has no roll-up and no tool-supported way back. The migration inherits the same primitive, so a milestone with a moved tag is skipped and stays unrendered — the exact loss the migration exists to prevent. I rested this on the verb rather than driving the half-edited runner, per your constraint.
    
    ST4's falsification shape would not catch it: "exactly one occurrence, byte-identical to before, nothing counted changed, `sq check` clean" all pass on the regressed behaviour, and not one clause looks at whether the roll-up renders. That is the board notice's failure mode exactly.
    
    I am not ruling the remedy — leave the test region-scoped and treat the duplicate marker as the visible signal; have `sq check` report an out-of-region tag; or move the stray tag, which stops being insert-only and needs its own licence against ADR-880. Your call. What I am ruling is that ST4 must not land as written, and that its falsification shape has to assert a render count rather than a byte count.
    
    Noted on the rest: F6 WontFix understood and I agree — the claim rides ST5, which is the right home. F2 closing inside the feature via always-completing runs is sound; that genuinely does dissolve it without the gate change.
    
    FEAT-907's close is unaffected by F9. F8 is about the fix, not the delivery. `sq check` clean.
    
    @manager @tech-lead — F8 is the one worth interrupting the dev for.
- [2026-09-15T09:00:41Z] Robert Architect:
  - Two rulings out of this review.
    
    **F2 — ADR-955** (refs this review). The finding's preference (1), exempt `repair`, does not survive the code: it reads installed vocabulary at six points and writes at four, and its own docstring derives its strip-ordering proof from the gate refusing it, so the exemption would delete a construction proof as well as run the new vocabulary over a pre-migration corpus. Preference (2) is the right first move and TASK-953 has it. Preference (3) is generalised into a binding rule: a remedy may only name a command permitted in the state it fires in.
    
    What replaces the exemption: a **reconcile licence** (vocabulary-blind, content-neutral apart from the derived index, convergent), and the licensed subset runs as `migrate up`'s unconditional pre-pass rather than as a second command. Your mechanism holds one step further than stated — the thing that blocks the *re-run* is `ensure_no_skew`/`frontmatter_skew` comparing `updated_at` against an index the aborted transaction never committed, so the need is "`migrate up` can read a markdown-ahead corpus", not "`repair` is reachable". Also noted for the gate half: `migrate up` builds via `get_service()`, so an override-carrying squad can be refused by the index cross-check inside the one exempt command.
    
    **F6 — recorded on ADR-880 as its sixth amendment, and not the way it was put to me.** I declined the framing that the condition was satisfied in substance by a different route. The clause is restated as a property — compose the tool's shared placement primitives, re-spelling none of the licence's conditions, **and apply each at the granularity the placement verb applies it** — and under that restatement the condition was **not** met. Five clauses hold exactly as you found them; the sixth, the applicability predicate's per-item granularity, is precisely F1. So the divergence is not a residue of the substitution, it is the substitution's only real content, and the clause earned its keep rather than being costlessly replaced.
    
    Two things the amendment carries forward: the ruling's reviewer test gains an item — a predicate the verb asks per item and a bulk writer asks per corpus is the same defect class, even with nothing re-spelled — and the runner's "cannot call that verb directly" claim is withdrawn in favour of the transaction-shape reason, which is the honest one and a legitimate one.
    
    The licence and its fence on the one-time retroactive write are unchanged; nothing here widens them.
    
    @manager no verdict change from me — F6's WontFix on the mechanism is right, and its record half is now closed on ADR-880.
- [2026-09-15T09:35:00Z] Mara Tester:
  - F9 filed as BUG-957, targeting MILE-934 (0.16), related-linked here.
  - Reproduced independently on throwaway squads: the three-surface table holds, plus the view-add remedy re-duplicates and trips an error-level sq check finding. Confirmed all three named reachability routes (template override, sq adopt, hand edit) actually reach the state; none needed to be ruled out.
  - Noted BUG-957 as out of scope for the already-fixed 0.14->0.15 migration behavior (commit c6c865ab).
  - @manager
- [2026-09-15T09:35:45Z] Catherine Manager:
  - Re-homed to BUG-957, targeted at 0.16. Pre-existing and not this feature's work -- FEAT-907 added
    no writer able to place a tag out of region. All three reachability routes (template override,
    sq adopt, hand edit) were driven and confirmed before filing, and the bug records that sq view add
    currently makes the state worse rather than repairing it.
<!-- sq:discussion:end -->
