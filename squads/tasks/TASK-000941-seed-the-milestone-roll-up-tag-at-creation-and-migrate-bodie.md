---
id: TASK-941
sequence_id: 941
type: task
title: Seed the milestone roll-up tag at creation and migrate bodies once
status: Done
parent: FEAT-907
author: tech-lead
assignee: python-dev
priority: medium
refs:
- ADR-880:implements
description: The creation template seeds the tag; a schema-gated one-time runner places
  it on existing milestones through FEAT-905's placement verb
subentities:
- local_id: ST1
  title: Seed the roll-up tag in the milestone creation template
  status: Done
  story: US1
- local_id: ST2
  title: Derive a type's template-seeded view names, override-aware
  status: Done
  story: US2
- local_id: ST3
  title: One-time runner places the tag through the placement operation
  status: Done
  story: US2
- local_id: ST4
  title: Register the schema step and bump the schema version
  status: Done
  story: US2
- local_id: ST5
  title: Report the count of bodies the run changed
  status: Done
  story: US3
- local_id: ST6
  title: Shape coverage, override fixture, and test falsification
  status: Done
  story: US2
created_at: '2026-09-14T12:15:23Z'
updated_at: '2026-09-15T09:36:08Z'
---
<!-- sq:body -->
## Scope

Two halves of one write surface: the milestone creation template gains the roll-up tag, and a
one-time schema-gated migration puts that same tag on every milestone already on disk.

Type attachment applied retroactively; a tag does not. Every milestone written before this
change carries no tag, so without the migration the roll-up quietly stops appearing for the
whole existing corpus. ADR-880 rules the migration permitted **once**, under a closed set of
conditions, and its second amendment changes how: the migration does not write the tag itself.
It calls the placement operation FEAT-905 shipped, once per milestone — the tool's own
operation applied at scale, not a bespoke writer into authored prose.

**The licence is inherited, not reimplemented.** Insert-only, one deterministic anchor (the end
of the `sq:body` region), idempotent skip, a clear refusal on a name that cannot resolve —
all of that already lives in `ViewsMixin.insert_view` (`_services/_views.py`) over
`sections.insert_unpaired_marker`. This task adds no second spelling of any of it. A reviewer
finding the anchor, the idempotence rule, or the tag's text composed anywhere in the new code
should read that as the defect it is.

## What lands

**1. The creation template seeds the tag.** `_rendering/templates/items/milestone.md.j2` gains
the `sq:view:milestone_rollup` placement tag inside its `sq:body` region. This is a different,
already-sanctioned path from the placement verb — the template writes the initial file rather
than mutating one, so `reject_markers` is not on this path at all and gets no hole. The
precedent is `_rendering/templates/agents/role.md.j2`, which already seeds
`sq:view:role_definition` exactly this way.

**2. One shared derivation: which view tags a type's creation template seeds.** A helper
answering, for an item type, the set of view names that type's creation template currently
places in its `sq:body` region. Constraints on it:

- It resolves the template through the **same** resolution the create path uses
  (`ServiceCore` template-name-for-type in `_services/_base.py`, including the
  `items/_default.md.j2` fallback) and the same override-aware Jinja loader
  (`_rendering/_engine.py`'s `ChoiceLoader` over `<squad_dir>/.overrides/templates/`). An
  adopter who overrode `items/milestone.md.j2` to drop the tag must get the overridden answer,
  not the bundled one.
- It reads the template **source**, not a render — there is no item to render against, and a
  render would need a context this question does not have.
- It recognises tags through `markers.view_tag_name` over `_sections`' own marker scan. The
  `sq:view:` shape is never re-spelled as a literal here.

It has two consumers: this migration, and the check advisory on the sibling task. That is why
it lands here rather than in either consumer — one derivation, so the migration and the
advisory can never disagree about what "the template seeds this tag" means. **This task gates
the sibling.**

**3. The migration runner.** `_migrations/_v0_14_to_v0_15.py` plus its `Migration` record in
`_migrations/_registry.py`, plus the `SCHEMA_VERSION` bump in `_models/_schema.py` from
`"0.14"` to `"0.15"`. If a sibling change has already added a 0.14→0.15 runner by the time this
starts, extend that one — the registry holds one step per schema transition, not one per
feature.

What the runner does: for every item type whose creation template seeds a view tag (helper 2),
for every indexed item of that type, call the placement operation for each seeded name. Today
that resolves to exactly `milestone`/`milestone_rollup`; the runner derives it rather than
pinning it, so an adopter who seeded a tag in their own item template is migrated by the same
pass and an adopter who dropped it is not touched.

Deliberately **live-tree coupled**, and say so in the module docstring so a reviewer meets it as
a decision: this runner reaches the live service and the live spec on purpose, the way
`_v0_11_to_v0_14` reaches live backend methods, because applying the live placement operation
*is* its charter. What it still may not do is import a wire-encoding primitive from `_models`
(`tests/meta/test_migrations_never_import_a_vocabulary_folded_primitive.py`) — going through
the placement operation means it never composes an id, a ref or a tag itself, which is the
clean way to satisfy that guard rather than freezing a private copy of anything.

**4. The count.** The runner returns the number of bodies it changed, which is the
`Migration.run` contract already (`Callable[[SquadPaths], Awaitable[int]]`) and what
`sq migrate up` prints. A re-run against an already-migrated corpus returns zero, because the
placement operation reports "already present" without writing.

**5. `MANUAL`.** A short runbook entry for `sq migrate chlog`: what changed, that milestone
bodies gained one line each, and that the diff is worth reading before committing — the same
posture the 0.11→0.14 `MANUAL` takes about its own corpus rewrite.

## Two implementation questions to settle, not to leave implicit

**Transaction shape.** `insert_view` calls `_locked_section_edit`, which opens its own
transaction per item — N lock acquisitions and N index commits for N milestones. The
alternative is one open transaction driving `_section_edit_core` directly per item, which is
the existing bulk-importer precedent (`_services/_import.py`). Either is acceptable; pick one,
say which in the docstring, and do not invent a third path. Whichever is chosen, the markdown
write happens before the index commit, unchanged.

**Skew.** `_section_edit_core` runs `ensure_no_skew` before mutating, so a milestone whose
on-disk frontmatter has diverged from the index refuses. A corpus mid-migration can be in
exactly that state. Decide and implement one of: skip-and-report that item (counting it in the
run output as untouched, with its id named), or abort the whole step with the guard's own
message. Do not swallow it silently. Name the choice in the docstring with its reason.

## Acceptance

**Seeding.**
- A freshly created milestone's body carries the tag, and `sq milestone <n> show --full` renders
  the roll-up with no migration step involved.
- The template's existing prose and its marker pairs are otherwise unchanged; the file still
  passes whatever the override service's item-template marker rules require
  (`_overrides/_service.py`).

**Migration.**
- One pass over the existing corpus places the tag on every milestone lacking it, through the
  placement operation.
- Insert-only: for each migrated file, every byte of the body other than the inserted tag line
  is preserved verbatim. Assert this on a body with prose before and after the anchor, on a body
  with existing markers in it, and on an empty body.
- Idempotent: a second run writes nothing, touches no mtime, and reports zero.
- A milestone whose author already removed the tag is left alone by a re-run — the insert only
  acts where the tag is absent, and this runs once by schema gate, never on a schedule.
- Touches only types whose creation template seeds a tag. Assert the negative directly: with the
  bundled templates, no epic/feature/task/bug/decision/contract/guide/review/role/skill/operator
  file is written by the run.
- A type whose template seeds a tag but which has no items on disk is a clean no-op, not an
  error.

**Count.**
- The run reports the number of bodies changed, and that number matches the number of files
  whose content actually changed (assert against the files, not against the runner's own
  bookkeeping).
- A re-run reports zero.

## Fences

- **Not a convergence sweep.** `sq repair` / `sq sync` already converge role and skill bodies
  onto their tags (`MaintenanceMixin._backfill_roster_body_tags`, `_converge_body_tag` in
  `_services/_maintenance.py`). Do not extend that machinery to milestones and do not reuse it
  here. Those are tool-owned bodies converged on every run; a milestone body is authored, and
  the ADR licenses exactly one write into it, gated by the schema stamp.
- **The double render is expected, and transient.** `[items.milestone]` still carries
  `views = ["milestone_rollup"]`, so a milestone whose body carries the tag renders the roll-up
  twice on `sq milestone <n> show --full` — once from the type attachment, once from the tag.
  After this task that is true for the whole milestone corpus, not just a hand-tagged document.
  It is accepted, it ends when the type attachment is deleted, and the feature that deletes it is
  sequenced after this one and depends on it. **No test may assert a single render**, and the
  duplicate is not a defect to file.
- **Not a precedent.** Nothing in this task establishes that a future bundled view retrofits
  itself onto existing documents. Do not generalise the runner into a reusable "seed any view
  onto any corpus" service method.
- **The advisory is not here.** The warn-level `sq check` finding for a seeded tag missing from
  a body rides the sibling task, with the derivation this one lands.
- **Do not run `sq migrate up` against this repository's own `squads/` corpus.** Bumping
  `SCHEMA_VERSION` makes every `sq` command in this tree hard-stop until that migration runs,
  for everyone. Drive the runner in temp squads in the test suite; sequencing the real run on
  this corpus is the operator's call, not this task's.

## Engineering constraints (acceptance criteria — the dev is held to these)

- Layering is `_cli` -> `_services` -> (index store, backends, rendering); `_models` has no
  internal deps. Every implementation module is private; package `__init__` files do not
  re-export.
- Marker-safe edits only, through `_sections.py`. Never rewrite an agent-authored body.
- The view tag stays unpaired: no `close_marker` counterpart, and nothing writes content
  adjacent to it.
- Frontmatter is the source of truth and the index is rebuildable. Within a transaction every
  markdown write happens before it returns; the index commit is last.
- User-facing errors subclass `SquadsError`, never a bare exception.
- Time is injectable: `clock.now()` / `clock.iso()`, never `datetime.now()`.
- Escape dynamic console output with `_cli._common.e()`.
- No `from __future__ import annotations`. Keep the import graph acyclic; use `if TYPE_CHECKING:`
  plus a string annotation rather than a runtime import if a new edge would cycle.
- Type aliases use PEP-695 `type X = ...`, never a bare assignment.
- A multi-exception handler is parenthesized (`except (A, B):`) with `# fmt: skip`.
- A new module-level dict or list trips `tests/meta`'s mutable-state guard: allowlist it as a
  CODE constant rather than restructuring, and run `tests/meta` whenever a module constant is
  added.
- **No sq or ticket IDs anywhere in source, and especially not in test file names** — name tests
  by behaviour. The ticket pointer belongs in the handback comment.
- **No build-process narration in delivered text** — docstrings, comments, `MANUAL` and the
  CHANGELOG describe the thing, not the pass that built it. No "this round", "the reviewer's
  finding", "as discussed above".

## Test obligations

- A service-level test **and** a CLI smoke test per behaviour, asserting the generated files:
  valid YAML frontmatter, intact markers, body preserved verbatim where it should be.
- Table-driven position x shape coverage, not one test per implemented branch. Cover: an empty
  body, a body with prose only, a body already carrying the tag, a body carrying a *different*
  view tag, a body carrying other marker pairs, several milestones in one run, and a corpus with
  zero milestones.
- An override fixture that replaces `items/milestone.md.j2` with one that seeds no tag, proving
  the derivation is override-aware and that the migration then touches nothing.
- Migration runner tests run through `sq migrate up` (the sanctioned entry point), never by
  importing the private runner module directly for its own sake.
- **Falsify every new test before handback**: break the behaviour, watch the test go red, restore
  it, watch it go green. Report both halves in the handback comment.
- Gate clean: `uv run --all-extras pyright`, `uv run --all-extras ruff check .`,
  `uv run --all-extras ruff format --check .`. `--all-extras` is required on each — a bare
  `uv run` prunes the optional `tui` extra and pyright then reports hundreds of false
  unresolved-import errors.
- The full suite is the main loop's gate, not this task's: run the targeted tests plus
  `tests/meta`, report what you ran, and hand back rather than parking on a long run.
- `uv run sq check` clean for the work touched.
- A CHANGELOG entry under the unreleased section as this lands.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 941 add-subtask "<title>"`; track with `sq task 941 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Seed the roll-up tag in the milestone creation template

<!-- sq:subtask:ST1:body -->
`_rendering/templates/items/milestone.md.j2` gains the `sq:view:milestone_rollup` placement tag
inside its `sq:body` region, so a milestone created after this change needs no migration step
ever. The template path is a different, already-sanctioned writer from the placement verb — it
writes the initial file rather than mutating one, so `reject_markers` is not on this path and
gets no hole. Pattern it on `_rendering/templates/agents/role.md.j2`, which already seeds
`sq:view:role_definition` the same way. The existing prose and marker pairs in the template are
otherwise untouched, and the file must still satisfy the item-template marker rules
`_overrides/_service.py` enforces.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Derive a type's template-seeded view names, override-aware

<!-- sq:subtask:ST2:body -->
One helper answering, for an item type, the set of view names that type's creation template
currently places in its `sq:body` region — the single derivation both this migration and the
sibling check advisory read.

It resolves the template through the same resolution the create path uses (the
template-name-for-type lookup in `_services/_base.py`, including the `items/_default.md.j2`
fallback) and the same override-aware loader `_rendering/_engine.py` builds over
`<squad_dir>/.overrides/templates/`, so an adopter who overrode `items/milestone.md.j2` to drop
the tag gets the overridden answer. It reads the template source rather than rendering it —
there is no item to render against. Tags are recognised through `markers.view_tag_name` over the
`_sections` marker scan, never by re-spelling the `sq:view:` shape at the call site.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — One-time runner places the tag through the placement operation

<!-- sq:subtask:ST3:body -->
`_migrations/_v0_14_to_v0_15.py`: for every item type whose creation template seeds a view tag,
for every indexed item of that type, call FEAT-905's placement operation once per seeded name.

The licence is inherited, not reimplemented — insert-only, the end-of-`sq:body` anchor, the
idempotent skip and the refusal on a name that cannot resolve all already live in
`ViewsMixin.insert_view` over `sections.insert_unpaired_marker`. No second spelling of the
anchor, the idempotence rule, or the tag text appears in this runner.

Two calls to make explicitly in the module docstring rather than by accident. **Transaction
shape**: `insert_view` opens one transaction per item; the alternative is one open transaction
driving `_section_edit_core` per item, the existing bulk-importer precedent. Pick one, say which,
invent no third. **Skew**: `_section_edit_core` runs `ensure_no_skew` first, and a migrating
corpus can be skewed — either skip-and-report the item by id, or abort the step with the guard's
own message; never swallow it.

The runner is deliberately live-tree coupled, the way `_v0_11_to_v0_14` reaches live backend
methods, because applying the live placement operation is its charter. Going through that
operation is also what keeps it clear of the wire-encoding import guard
(`tests/meta/test_migrations_never_import_a_vocabulary_folded_primitive.py`): it composes no id,
ref or tag of its own.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Register the schema step and bump the schema version

<!-- sq:subtask:ST4:body -->
The `Migration` record in `_migrations/_registry.py` for the 0.14 to 0.15 transition, and the
`SCHEMA_VERSION` bump in `_models/_schema.py`. If a sibling change has already added a
0.14-to-0.15 runner, extend that one — the registry holds one step per schema transition, not one
per feature.

The schema stamp is what makes this run exactly once, deliberately, rather than on a schedule —
that gate is the whole reason this is a migration and not a convergence sweep. A `MANUAL`
runbook entry accompanies it for `sq migrate chlog`: what changed, that milestone bodies gained
one line each, and that the diff is worth reading before committing — the posture the 0.11-to-0.14
`MANUAL` already takes about its own corpus rewrite.

Do not run `sq migrate up` against this repository's own `squads/` corpus. The bump hard-stops
every `sq` command in this tree until that migration runs, for everyone; sequencing the real run
is the operator's call.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Report the count of bodies the run changed

<!-- sq:subtask:ST5:body -->
The runner returns the number of bodies it changed — already the `Migration.run` contract
(`Callable[[SquadPaths], Awaitable[int]]`), which `sq migrate up` prints — so the write is
visible in the run output as well as in the corpus diff, never silent.

Assert the number against the files whose content actually changed, not against the runner's own
bookkeeping. A re-run over an already-migrated corpus returns zero and writes nothing, because
the placement operation reports already-present without touching the file.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Shape coverage, override fixture, and test falsification

<!-- sq:subtask:ST6:body -->
A service-level test and a CLI smoke test per behaviour, asserting the generated files: valid
YAML frontmatter, intact markers, body preserved verbatim where it should be.

Table-driven position-by-shape coverage rather than one test per implemented branch: an empty
body, prose only, a body already carrying the tag, a body carrying a different view tag, a body
carrying other marker pairs, several milestones in one run, and a corpus with zero milestones.
Assert the negative directly — with the bundled templates no other type's file is written.
An override fixture replacing `items/milestone.md.j2` with one seeding no tag proves the
derivation is override-aware and that the migration then touches nothing. Drive the runner
through `sq migrate up`, the sanctioned entry point, not by importing the private module for its
own sake.

Falsify every new test before handback: break the behaviour, watch it go red, restore it, watch
it go green, and report both halves.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-14T14:42:18Z] Elias Python:
  - Landed: ST1 (tag seeded in milestone.md.j2), ST2 (template_seeded_view_names in _views.py, override-aware, backs both this migration and TASK-942), ST3 (_migrations/_v0_14_to_v0_15.py — one open transaction, abort-on-skew, inherits insert-only/anchor/idempotent-skip/refusal from insert_unpaired_marker + resolve_view_target directly since _services is unreachable from a migration runner, same import-cycle _v0_11_to_v0_14 already documents), ST4 (registry entry + SCHEMA_VERSION bump — see note below), ST5 (MigrationRun.changed + sq migrate up now prints "N changed" per applied step — this did NOT already happen before my change, despite the task text's phrasing; run_pending_migrations discarded every runner's returned count), ST6 (table-driven shapes + override fixture + 4 falsification probes, all red→green).
  - Operator rulings applied: dropped items.milestone.views from workflow.toml (closes the double-render window in this task, not deferred to FEAT-904); TASK-942's advisory selection untouched (no .overrides/workflow.toml created here).
  - Collateral from dropping the type attachment, fixed: milestone_rollup is now freestanding like the other 5 bundled views, so it survives any [selected] deselect of milestone — updated test_milestone_view_deselect_cascade.py (kept the prune mechanism covered via a monkeypatched bundled-raw fixture, since no bundled view attaches a type any more), test_view_declaration_referential_checks.py (2 tests + 1 stale-comment fix), test_milestone_cli.py's --json assertion (roll-up is in body now, not a views key), 3 files with an identical stale comment about the old attachment, and the corpus/chain tests' migration-count lists (added the 0.14->0.15 step). Also ran scripts/gen_template_manifest.py + scripts/seed_content_store.py --rebuild after editing workflow.toml/milestone.md.j2 (1 orphaned blob dropped).
  - One thing I did NOT fix, flagging rather than silently accepting or silently over-building: milestone's template tag has no deselection guard the way role's does (_create_core's ROSTER_ROLE branch overwrites the tag with empty when role_definition is undeclared; milestone has no equivalent, since its body also carries real prose that branch's whole-region overwrite would destroy). A milestone created while milestone_rollup is deselected gets a dangling tag, caught by sq check's dangling-name finding rather than refused at creation. Recorded as tests/meta's new 'unconditional-seed' classification (vs role's 'neutralized-by-overwrite') so it's not silently unaccounted-for. Candidate follow-up, not blocking.
  - Gates: pyright clean, ruff check clean, ruff format clean. tests/meta + tests/integration + tests/cli (the floor for _specs/_rendering/templates/_cli changes) all green except 9 pre-bump artifacts (a v0_15 corpus fixture and a few 'second run is clean' assertions that need SCHEMA_VERSION actually at 0.15 to resolve — verified green with a temporary bump+revert). tests/unit + tests/service (minus tui, not mine) also green minus the same 2 pre-bump artifacts. sq check clean on this repo now.
  - Falsified 4 mechanisms directly (broke the code, watched the new test go red, restored, watched it go green): the insert primitive itself, the non-roster scope guard (first attempt was a false negative — role's tag is already idempotently present so widening the scope silently no-opped; fixed by stripping the tag first so a scope bug shows up as a real write), the override-derivation-awareness, and the skew-abort path. Plus one for template_seeded_view_names's body-region scoping.
  - SCHEMA_VERSION bump: in the tree (_models/_schema.py, currently reverted back to 0.14 on disk right now). I have NOT run sq migrate up against this repo's own squad/ corpus and will not. Once you bump it for real, every sq command here hard-stops until sq migrate up runs — sequence that. All my own sq reads/writes for this task are done.
  - Files: src/squads/_specs/workflow.toml, src/squads/_rendering/templates/items/milestone.md.j2, src/squads/_rendering/_engine.py, src/squads/_services/_base.py, src/squads/_views.py, src/squads/_migrations/_v0_14_to_v0_15.py (new), src/squads/_migrations/_registry.py, src/squads/_services/_results.py, src/squads/_services/_maintenance.py, src/squads/_cli/_migrate.py, src/squads/_models/_schema.py, plus templates_manifest.json/content_store.json regen, tests/fixtures/corpus/v0_15/ (new), CHANGELOG.md, and the test files listed above.
  - @manager ready for you to sequence the schema bump + sq migrate up.
<!-- sq:discussion:end -->
