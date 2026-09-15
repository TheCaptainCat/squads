---
id: TASK-942
sequence_id: 942
type: task
title: 'Required views: the declared flag, the write refusal, the check'
status: Draft
parent: FEAT-948
author: tech-lead
priority: medium
refs:
- ADR-880:implements
- TASK-941:depends-on
- BUG-951:fixes
description: A required key on the view declaration, a derived host set, an unforceable
  replace refusal, a tier-1 check finding, and the convergence licence that narrows
  with them
subentities:
- local_id: ST1
  title: The required key on the view declaration, and its grammar docs
  status: Todo
  story: US1
- local_id: ST2
  title: 'The derived host-set helper: one predicate over type and slug'
  status: Todo
  story: US1
- local_id: ST3
  title: This project's spec selection — no selection exists to take
  status: Cancelled
  story: US4
- local_id: ST4
  title: Replace refused on a required host, in the shared body closure
  status: Todo
  story: US2
- local_id: ST5
  title: The append refusal survives as its own sweep-keyed rule
  status: Todo
  story: US3
- local_id: ST6
  title: view rm refuses on a declared, required host
  status: Todo
  story: US3
- local_id: ST7
  title: 'Tier-1 check finding: a host missing its required view tag'
  status: Todo
  story: US4
- local_id: ST8
  title: All six bundled views declare required
  status: Todo
  story: US5
- local_id: ST9
  title: Retire set_body's per-type branches; move the role remedy
  status: Todo
  story: US5
- local_id: ST10
  title: Regression shapes, falsification, and the gate
  status: Todo
- local_id: ST11
  title: Role and system-skill convergence narrows to strict_empty
  status: Todo
  story: US6
- local_id: ST12
  title: The pre-0.14 roster-body reclaim moves into a migration step
  status: Todo
  story: US6
created_at: '2026-09-14T12:15:27Z'
updated_at: '2026-09-15T08:26:32Z'
---
<!-- sq:body -->
## Scope

A view declaration gains a `required` boolean. A document that the tool's own placement
authority seeds a required view's tag onto **must** hold that tag: a body **replace** on such a
document is refused outright, `sq view rm` will not take the tag off it, and `sq check` reports
a host that has lost it anyway. The hardcoded role and system-skill body refusals in `set_body`
retire into that general rule, and all six bundled views declare themselves required.

The retirement is a **narrowing**, not a like-for-like substitution, and the repair sweep's wide
convergence licence retires with the refusal that justified it — otherwise the narrowing opens a
path that replaces an author's prose with a tag line.

## The two guards are distinct, and only one is forceable

- **Overwriting an existing authored body is *protected*.** `reject_body_overwrite` is the
  protection and `--force` is exactly the consent that lifts it. Unchanged here.
- **Producing a body that omits a required view tag is *forbidden*.** It is a document
  invariant, not prose an author is consenting to lose. No flag lifts it, `--force` says
  nothing about it, and no flag may be added that does.

A write must clear both. The required check runs **first** and never consults `force`; there is
no compliant replace to fall back to, because a body text carrying the tag cannot enter through
the prose door at all (`reject_markers` refuses a well-formed marker typed into a body), so both
"omit it" and "include it" are unavailable and a refusal is the honest answer.

## The host set, exactly

A required view's hosts are **exactly the documents the tool's own placement authority seeds the
tag onto** — derived, never declared, and decidable from the host's **type and slug alone**:

- for an ordinary item type, the type's creation template, read through
  `views.template_seeded_view_names(item_type, spec)` — override-aware, already shipped;
- for a role, a permanently-system skill, and a per-item-type `sq-<type>` skill, the roster
  writer's classification, which `MaintenanceMixin._repair_body_tag` already computes
  (`role_definition` for a role, the `SYSTEM_SKILL_VIEW_NAMES` entry for the three fixed slugs,
  `ITEM_SKILL_VIEW_NAME` for a slug that currently documents a declared type, and nothing for a
  custom author-defined skill).

**One helper, composing those two — never re-deriving either, and the write path keeps no
membership test of its own.** Two answers to "which view does this document carry" is the drift
the single-derivation rule exists to prevent, and a requirement raises the cost of a disagreement
from a missing advisory to a wrongly refused write. The classification half has to be askable
**before** frontmatter parses (the check tier below needs it), so it becomes a pure
`(item_type, slug, spec)` function and the repair sweep's `Item`-shaped entry point consumes that
same function rather than keeping a second copy.

One consequence of deriving rather than declaring, intended and to be **asserted rather than
discovered**: **a requirement nothing seeds is unsatisfiable**, so deriving from the seeder makes
creation satisfy the invariant by construction — which is why creation gets no gate of its own.
The other consequence, the narrowing, has a section of its own below.

A **hand-placed** tag on a non-host document is not bound. `sq view add` will place a required
view's tag on any document whose type the view's source applies to; that document is not a host,
nothing requires it to keep the tag, and `sq view rm` takes it off. The requirement is keyed on
the host relation **as the spec and its templates currently stand** — never on how a tag
arrived, which nothing records and nothing may start recording.

## The narrowing: three shapes, intended, and its consequence one module over

Deriving hosts from the classification is **stricter** than the two tests the write path uses
today, which are bundled-blind: `is_system_skill`'s built-in half takes no spec and no playbook,
and `item.type == ROSTER_ROLE` asks nothing about the spec at all. Three documents are refused a
body today and admitted afterwards:

1. a permanently-system skill whose view is dropped from `[selected]` (`squads`, `greeting`,
   `sq-memory` stay in `bundled_skill_slugs()` forever);
2. a role, when `role_definition` is dropped;
3. a stale `sq-<type>` skill whose type is no longer declared — and **only for a
   historically-bundled type**. A project-declared `widget`'s stale `sq-widget` is already
   writable today, since `custom_skill_slugs` iterates the live spec. Do not scope this shape
   wider than it is.

**That is the correction, not the cost.** A body region is tool-owned because something the tool
maintains renders into it; drop the view and nothing does, and the region reverts to authored
prose. The old refusal told the author "an authored body here would never be shown", which in
these three shapes is untrue: `read_body` returns the region verbatim and expands only when a tag
is present, so the prose displays like any other item's.

**It fixes one real defect.** `set_body` asks `is_system_skill` while the sweep asks
`item_type_for_skill_slug`: two membership tests for one question, disagreeing on exactly the
stale bundled slug. `sq-bug` with `bug` dropped is refused by the write path and never reached by
the sweep — a region no command can write and no sweep can converge. Routing both through one
classification removes that state.

**And it falsifies the premise of the repair sweep's wide convergence licence.**
`_converge_body_tag` keeps `strict_empty=False` for a role and a permanently-system skill on the
stated ground that "no code path today can have authored either region". After the narrowing,
drop → author → re-add produces exactly such a region, and a version-drift backfill then takes the
marker-free branch and **replaces the author's text with the tag line**. The sweep cannot tell
that prose from a pre-0.14 rendering and may not learn to — both are marker-free plain text, and
nothing records provenance. So both families move to `strict_empty=True`, and the one-time
pre-0.14 reclaim the wide branch existed for moves to a migration, where a closed, release-scoped
licence belongs. That also closes the trap a legacy-rendered role body would otherwise sit in:
not writable, not convergeable, and with no remedy at all.

The escape for a required host whose region holds content the author wants gone stays the
spec-level one, not a new flag: clear the requirement (drop the view from `[selected]`, or
override the seeding template), write the body, restore it.

## What lands

**1. The declaration.** `required: bool = False` on `ViewSpec` (`_workflow/_models.py`), beside
`source`. A key of the **view declaration**, never of a type's selection or placement of a view.
Default false: an upgrading corpus predates the flag and there is no per-write escape from the
restriction, so it is opted into, never inherited. Documented in the adopter-facing view
declaration grammar (`docs/workflow.md`, `docs/overrides.md`) as part of shipping the key.

**2. Spec load stays unbound.** A `required = true` view that no template and no roster writer
seeds has an empty host set and binds nothing. Vacuous, not broken — it is the ordinary
intermediate state of an adopter who declares a view before overriding a creation template to
place it. Do not refuse it at load.

**3. The host-set helper.** One function, as described above. Type and slug only; it may not
read the host's content.

**4. The replace refusal.** In `_body_mutate`'s `mutate` closure, so `set_body` and the bulk
importer's `body` op are covered by the one shared closure rather than two implementations.
Refuses a replace on a required host unconditionally, before `reject_body_overwrite` is reached
and without consulting `force`. The message names the item, the required view, and the placement
verb by the command the operator actually types — not a bare "required view missing".

**5. The append rule, separate.** The general required rule does **not** refuse `--append`:
append keeps the whole existing region and writes after it, so it cannot produce a body missing
a tag the body already had. But today's role and system-skill branches refuse append too, and
that refusal must survive the retirement rather than being widened away by accident: those
regions are converged by the repair sweep (`_repair_body_tag`/`_converge_body_tag`), so prose
appended beside the tag is erased by the next `sq repair` with no warning. Ruled: the append
refusal survives as its **own** rule, keyed on the sweep's own classification — the same
predicate, asked once — and never on a type literal re-spelled in the write path.

**6. `sq view rm`, narrowed.** `remove_view` refuses only when the named view is declared, is
`required`, and *this* document is one of its hosts. Every other removal stays free, which
preserves the existing recovery path verbatim: a tag naming an undeclared view, a view whose
source cannot apply to this host, and a non-required view all come off exactly as they do today.
Without this clause the invariant is a one-command bypass and "no flag lifts it" means nothing.
`sq view add` stays unbound — adding a tag is never the violation, and it is the remedy the
refusal and the finding both name. Its existing refusals are unchanged. The narrowing does not
reach this verb and cannot: `remove_view` refuses nothing today beyond a missing `sq:body`
region, so a declared-and-required-and-host rule can only add refusals.

**7. The check finding — tier 1, unconditional, error level.** It belongs in
`MaintenanceMixin._scan_for_check`'s raw-text file-level pass, beside `_marker_issues` and
`_view_target_issues`. Both of that tier's stated properties hold, and the second decides it:

- *It needs no resolved item.* The scan binds the host type from the type folder and the
  `PREFIX-NNNNNN-<slug>.md` filename before `read_frontmatter` runs, and that filename's slug
  segment is what `Item.slug` is defined as (`_models/_item.py::_slug_from_path`) — so both
  inputs the predicate is allowed to read are in hand. A file too broken to parse still gets the
  finding.
- *It must not be selectable.* A project that does not want the requirement clears `required`,
  drops the view, or overrides the creation template. A project that declares the requirement
  and then selects its enforcement separately has stated the same intention twice and can leave
  the two disagreeing. An invariant whose enforcement is opt-in is not an invariant.

The message names the document, the required view, and the remedy (`sq view add`). **Nothing is
reported for a non-required view** — "this document used to carry it" is a provenance question.

**8. The six bundled views become `required = true`.** `role_definition`, `squads_skill`,
`greeting_skill`, `memory_skill` and `item_skill`: each of those bodies *is* the slot its view
renders into, and without the tag the document reads as nothing — this is the behaviour already
hardcoded, now declared. `milestone_rollup` joins them, and it is the only bundled view a body
write can reach at all (the other five sit on bodies already refused), so leaving it optional
would ship a flag with no bundled consumer.

**9. The `set_body` retirement, with its two constraints.** The `ROSTER_ROLE` branch and the
`is_system_skill` branch are replaced by the general required-host rule, for **replace only**
(constraint 1 — the append refusal of item 5 is what keeps the other half). The general rule
refuses *fewer* documents than those branches did, in the three shapes above; that is the point,
and it is to be scoped and tested as a behaviour change rather than as a substitution nobody
needs to look for. The unrelated third branch — a project-declared roster type whose body is
generated — is not a view question and stays exactly as it is. The custom-skill admission stays
too and falls out of the derivation rather than being special-cased: a custom skill has no seeded
view, so nothing requires anything of it.

**10. The remedy sentence that must not be lost** (constraint 2). Today's role refusal names the
real remedy — declare the definition in `.overrides/roles.toml`, or `.overrides/roles/<slug>.toml`
for a project-defined role. A generalised refusal composed from a view's name cannot carry that
sentence without a per-view message key, which is declaration growth for one string. The
role-authoring pointer moves to the role surface, reachable from `sq role <slug> show`'s
empty-body hint (`views.empty_body_hint_state`'s consumers), and moving it is **part of this
work, not a follow-up**. Check the skill-side consumer for parity while you are there.

**11. The convergence licence narrows with it.** A role and a permanently-system skill move to
`strict_empty=True` in `_converge_body_tag`, the licence a per-item-type skill already carries for
this exact shape one level up. Only an empty or already-tagged region converges; anything else is
left untouched, silently. Both call sites in `_services/_maintenance.py` agree, and the module
prose stating the wide licence's premise is rewritten rather than left contradicting the code.

**12. The pre-0.14 reclaim becomes a migration step.** A migration knows which release the corpus
is arriving from, so it can know that a marker-free role body is a superseded rendering; the
standing sweep runs forever and cannot. The step converges a marker-free, non-empty `sq:body` on a
role and on a permanently-system skill to that document's own view tag, reports the count of
bodies changed, is idempotent, and touches nothing else. Which runner carries it is settled in
ST12 and stated in the handback.

## What an upgrading adopter sees

A finding, not a wall. No new `sq repair` backfill for an ordinary item type, no command rewrites
an authored body to satisfy the flag, and no hard stop. Every read keeps working — the rule binds
writes, not reads; a body without the tag renders without that view's output exactly as it does
today. `sq check` reports it, and the first body replace on that document is refused with the
remedy in hand. The two escapes are spec-level and deliberate: drop the view from `[selected]`, or
override the creation template that seeds it.

The one write an upgrade performs is item 12's reclaim, and it is confined to the region the
retiring wide licence was already converging on every `sq repair`: a marker-free role or
permanently-system skill body, reported by count.

For the two roster families the corpus-level remedy already exists and needs no change
(`_repair_body_tag` plus `_backfill_roster_body_tags` converge those regions under their
remaining licence). **This repository is already compliant**: every milestone carries the roll-up
tag, every role carries its definition tag, and every skill carries its own view tag except the
one custom author-defined skill, which correctly has no required view.

## Fences

- **No validator catalog member.** This finding is not selectable and takes no level. Nothing is
  added to `VALIDATOR_NAMES`, `DEFAULT_VALIDATOR_LEVEL`, `VALIDATOR_LEVEL_FLOOR`,
  `UNGUARDED_VALIDATOR_NAMES`, `VALIDATOR_CONTEXT` or any category bundle, and no
  `squads/.overrides/workflow.toml` is created — this repository keeps having no overrides at
  all.
- **No provenance, ever.** No stored marker, frontmatter key, index field or cache recording that
  a tag was once present.
- **Not a repair.** The finding reports; it never re-inserts a tag and must not grow a `--fix`.
- **Type and slug only.** The host-set predicate may not read the host's content. A future
  required view that cannot be decided that way is a proposal to move this finding out of tier 1,
  to be raised and answered as exactly that — never worked around by widening the predicate.
- **One flag per view, not per (view, type) pair.** A view seeded on two types is required on
  both. Do not add a matrix axis, and do not reintroduce `ItemSpec.views` or any other per-type
  requirement axis.
- **Do not restore the wide convergence licence.** Restoring it is proposing to let a standing
  sweep guess at authored prose, and is to be answered as that. A compatibility branch that keeps
  the old refusal width is the same proposal wearing the write path's clothes.
- **Leave the unbound surfaces unbound.** `sq view add`, `sq retype` (it writes nothing; a
  violating document stays reachable without any write path producing it, which is why the
  invariant is "no write may produce it" plus a report, not "no corpus may contain it"), item
  creation, and spec load all stay as they are.
- **Do not touch the existing tier-1 findings.** The dangling-view-name and marker-balance
  findings keep their current conditions; this is a third finding beside them, not a widening of
  either.

## Engineering constraints (acceptance criteria — the dev is held to these)

- Layering is `_cli` -> `_services` -> (index store, backends, rendering); `_models` has no
  internal deps. Every implementation module is private; package `__init__` files do not
  re-export. `required` is a value-object field in `_workflow/_models.py`; the host-set helper
  belongs with the other view mechanics in the top-level `_views` module, which has no service
  dependency — do not put it somewhere that forces `_workflow` or `_models` to import upward.
- Recognise tags through `markers.view_tag_name` / `markers.view_tag`; the `sq:view:` shape is
  never re-spelled as a literal at a call site.
- Read the body region through `_sections.get_section`, as the existing consumers do.
- A migration runner is private and reached only through `sq migrate`; never `python -m`.
- User-facing errors subclass `SquadsError`, never a bare exception.
- Escape dynamic console output with `_cli._common.e()`.
- No `from __future__ import annotations`. Keep the import graph acyclic.
- Type aliases use PEP-695 `type X = ...`, never a bare assignment.
- A multi-exception handler is parenthesized (`except (A, B):`) with `# fmt: skip`.
- A new module-level dict or list trips `tests/meta`'s mutable-state guard: allowlist it as a
  CODE constant rather than restructuring, and run `tests/meta` whenever a module constant is
  added.
- **No sq or ticket IDs anywhere in source, and especially not in test file names** — name tests
  by behaviour. The ticket pointer belongs in the handback comment.
- **No build-process narration in delivered text** — docstrings, comments, docs and the CHANGELOG
  describe the thing, not the pass that built it.

## Test obligations

Service-level tests **and** CLI smoke tests. The full list of owed shapes lives on ST10 and is
summarised here: the required rule's own shapes (a milestone replace refused, `--force` not
lifting it, a pristine body refused, append succeeding, append still refused on a role and a
system skill, the importer sharing one closure, `view rm` refused on a host and free on every
recovery removal, a retype reported rather than refused, a dropped view binding nothing, an
unseeded required view loading cleanly, the finding firing on an unparseable file, the role
remedy still reachable); the narrowing's own shapes, table-driven over the three documents it
widens writability on plus the project-declared one it does **not**; and the whole
drop → author → re-add round trip, asserting the author's prose survives and not only that the
tag is placed.

- **Falsify every new test before handback**: break the behaviour, watch the test go red, restore
  it, watch it go green. Report both halves in the handback comment. Falsify the round-trip test
  against the wide convergence branch specifically, so it is proven to catch the loss.
- Gate clean: `uv run --all-extras pyright`, `uv run --all-extras ruff check .`,
  `uv run --all-extras ruff format --check .`. `--all-extras` is required on each — a bare
  `uv run` prunes the optional `tui` extra and pyright then reports hundreds of false
  unresolved-import errors.
- The full suite is the main loop's gate, not this task's: run the targeted tests plus
  `tests/meta`, report what you ran, and hand back rather than parking on a long run.
- `uv run sq check` clean for the work touched, on a corpus that already satisfies every new
  requirement.
- A CHANGELOG entry under the unreleased section as this lands.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 942 add-subtask "<title>"`; track with `sq task 942 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — The required key on the view declaration, and its grammar docs

<!-- sq:subtask:ST1:body -->
`required: bool = False` on `ViewSpec` (`_workflow/_models.py`), declared beside `source` — a key
of the **view declaration**, never of a type's selection or placement of a view, and no per-type
requirement axis returns to carry it.

Default false, deliberately: an upgrading corpus predates the flag and the restriction has no
per-write escape, so it must be opted into rather than inherited. Spec load stays unbound — a
`required = true` view that no creation template and no roster writer seeds has an empty host
set and binds nothing, which is vacuous rather than broken and is the ordinary intermediate state
of an adopter who declares a view before overriding a template to place it. Do not refuse it at
load.

The key is adopter-facing, so it is documented where the view declaration grammar already lives
(`docs/workflow.md`, `docs/overrides.md`): what it means, that it defaults to false, that its
host set is derived from what seeds the tag rather than declared, and that no flag lifts it.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — The derived host-set helper: one predicate over type and slug

<!-- sq:subtask:ST2:body -->
One function answering "which required view, if any, must this document carry" from the host's
**type and slug alone** — never from the host's content.

It composes the two derivations that already exist and re-derives neither:

- `views.template_seeded_view_names(item_type, spec)` for an ordinary item type — override-aware,
  resolved through the same template resolution the create path uses;
- the roster writer's classification that `MaintenanceMixin._repair_body_tag` computes —
  `role_definition` for a role, the `SYSTEM_SKILL_VIEW_NAMES` entry for the three fixed slugs,
  `ITEM_SKILL_VIEW_NAME` for a slug that currently documents a declared type, nothing for a
  custom author-defined skill.

The classification half must be askable before frontmatter parses, because the file-level check
tier needs it, so it becomes a pure function of `(item_type, slug, spec)` and the repair sweep's
item-shaped entry point consumes that same function. One implementation, two callers — and the
write path may not keep a second membership test of its own. Two answers to "which view does this
document carry" is the drift the single-derivation rule exists to prevent, and a requirement
raises the cost of that disagreement from a missing report to a wrongly refused write.

`required` is only ever asked of a **declared** view: a view dropped from `[selected]` is not
declared, therefore has no hosts, therefore requires nothing — the same gate the classification
already applies on every branch of its own answer.

## The narrowing this introduces, in three shapes

Deriving from the classification is **stricter** than the write path's current test, which is
bundled-blind: `is_system_skill`'s built-in half takes no spec and no playbook, and
`item.type == ROSTER_ROLE` asks nothing about the spec at all. Three documents are refused a
body today and admitted after this change. Each is asserted, not discovered:

1. **A permanently-system skill whose view is dropped from `[selected]`.** `squads`, `greeting`
   and `sq-memory` stay in `bundled_skill_slugs()` forever, so the write path refuses today; the
   derivation yields no host and admits the write.
2. **A role, when `role_definition` is dropped.** Follows identically, from a test that asks
   nothing about the spec.
3. **A stale `sq-<type>` skill whose type is no longer declared — and only for a
   *historically-bundled* type.** `sq-bug` after `bug` is dropped stays in the bundled-blind list
   and is refused today, while `item_type_for_skill_slug("sq-bug", spec)` returns `None`. A
   *project-declared* `widget`'s stale `sq-widget` is already writable, since `custom_skill_slugs`
   iterates the live spec — nothing changes there. Do not scope this shape wider than it is.

The narrowing is the intended correction, not a cost: a body region is tool-owned because
something the tool maintains renders into it, and in all three shapes nothing does. `read_body`
returns the region verbatim and expands only when a tag is present, so the authored prose displays
like any other item's — the refusal's own stated reason ("an authored body here would never be
shown") is false in exactly these shapes.

## The dead region it removes

`set_body` asks `is_system_skill` (bundled-blind ∪ live custom) while the sweep asks
`SYSTEM_SKILL_VIEW_NAMES` / `item_type_for_skill_slug` (live only). They disagree on precisely the
stale historically-bundled slug of shape 3: `sq-bug` with `bug` dropped is refused by the write
path and never reached by the sweep — a region no command can write and no sweep can converge.
Routing both through the one classification is what removes that state, and it is the same
single-derivation obligation this subtask already carries.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — This project's spec selection — no selection exists to take

<!-- sq:subtask:ST3:body -->
No selection exists to take: the enforcement this task builds is unconditional and not
selectable, so there is no validator name, no level, and no `[items.*]` validators list to name
it in. `squads/.overrides/workflow.toml` is not created and this repository keeps having no
overrides at all.

Recorded rather than dropped so the absence reads as a decision. Nothing here is to be built.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Replace refused on a required host, in the shared body closure

<!-- sq:subtask:ST4:body -->
The enforcement point that matters. The guard sits in `_body_mutate`'s `mutate` closure, so
`set_body` and the bulk importer's `body` op are both covered by the one shared closure rather
than two implementations.

A **replace** on a required host is refused unconditionally: before `reject_body_overwrite` is
reached, and without consulting `force`. The two guards are independent and this one is not
forceable — overwriting an authored body is *protected* and `--force` is the consent that lifts
that protection, while producing a body that omits a required view tag is *forbidden*, a
document invariant rather than prose an author is consenting to lose. Do not add a flag that
lifts it. A pristine, never-written body on a required host is refused too, where the overwrite
guard alone would have admitted it.

There is no compliant replace to fall back to: a body text carrying the tag cannot enter through
the prose door at all (`reject_markers` refuses a well-formed marker typed into a body), so both
"omit it" and "include it" are unavailable and a refusal is the honest answer.

The message names the item, the required view, and the placement verb by the command the
operator actually types — never a bare "required view missing", so an author is not left blocked
without the unblock in hand.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — The append refusal survives as its own sweep-keyed rule

<!-- sq:subtask:ST5:body -->
`--append` is **not** refused by the required-host rule: it keeps the whole existing region and
writes after it, so it cannot produce a body missing a tag the body already had.

But today's role and system-skill branches refuse append as well, and that half must survive the
retirement rather than being widened away by accident. Those regions are converged by the repair
sweep (`_repair_body_tag` / `_converge_body_tag`), so prose appended beside the tag is erased by
the next `sq repair` with no warning at all.

So the append refusal survives as a **separate rule**, keyed on the sweep's own classification —
the same predicate the host-set helper already asks, asked once — and never on a type literal
re-spelled in the write path. Whether a converged roster body should ever admit authored prose
beside its tag is a different question and is not opened here.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — view rm refuses on a declared, required host

<!-- sq:subtask:ST6:body -->
`remove_view` refuses only when all three hold: the named view is declared, it is `required`, and
*this* document is one of its hosts.

Every other removal stays free, which preserves the existing recovery path verbatim — a tag
naming an undeclared view, a view whose declared source cannot apply to this host, and any
non-required view all come off exactly as they do today. Without this clause the invariant is a
one-command bypass and "no flag lifts it" would mean nothing.

`sq view add` stays unbound: adding a tag is never the violation, and it is the remedy both the
write refusal and the check finding name. Its existing refusals — undeclared name, unresolvable
template, source inapplicable to the host's type — are unchanged.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Tier-1 check finding: a host missing its required view tag

<!-- sq:subtask:ST7:body -->
An error-level finding produced unconditionally by `MaintenanceMixin._scan_for_check`'s raw-text
file-level pass, beside `_marker_issues` and `_view_target_issues`. Not a validator catalog
member, not selectable, and carrying no level.

Both of that tier's stated properties hold, and the second decides it:

- **It needs no resolved item.** The scan binds the host type from the type folder and the
  `PREFIX-NNNNNN-<slug>.md` filename before `read_frontmatter` runs, and that filename's slug
  segment is exactly what `Item.slug` is defined as (`_models/_item.py::_slug_from_path`) — so
  both inputs the predicate is allowed to read are already in hand. A file too broken to parse
  still gets the finding, which is where a finding about a document that cannot render earns its
  keep.
- **It must not be selectable.** A project that does not want the requirement clears `required`,
  drops the view from `[selected]`, or overrides the creation template that seeds it. A project
  that declares the requirement and then selects its enforcement separately has stated the same
  intention twice and can leave the two disagreeing. An invariant whose enforcement is opt-in is
  not an invariant.

The message names the document, the required view, and the remedy (`sq view add`). Nothing is
reported for a non-required view — "this document used to carry it" is a provenance question, and
nothing records provenance.

It reports and never repairs: no re-inserting the tag, and no `--fix`.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — All six bundled views declare required

<!-- sq:subtask:ST8:body -->
`role_definition`, `squads_skill`, `greeting_skill`, `memory_skill` and `item_skill` take
`required = true`: each of those bodies *is* the slot its view renders into, and without the tag
the document reads as nothing. That is the behaviour already hardcoded in the write path, now
declared.

`milestone_rollup` takes it too. It is the only bundled view a body write can reach at all — the
other five sit on bodies that are already refused — so leaving it optional would ship a flag with
no bundled consumer and change nothing about the surface the requirement was made for.

This corpus already satisfies all six: every milestone carries the roll-up tag, every role carries
its definition tag, and every skill carries its own view tag except the one custom author-defined
skill, which correctly has no required view and whose body is authored content. No migration and
no new backfill is added for an ordinary item type.
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->

<!-- sq:subtask:ST9 -->
### ST9 — Retire set_body's per-type branches; move the role remedy

<!-- sq:subtask:ST9:body -->
The `ROSTER_ROLE` branch and the `is_system_skill` branch in the body-write closure are replaced
by the general required-host rule — for **replace only**, the append half being the separate
sweep-keyed rule.

This is a **narrowing, not a substitution**, and it must be scoped and tested as a behaviour
change. The general rule refuses a replace on *fewer* documents than the two branches do, in the
three shapes ST2 names: the derivation gates on the view still being declared and the hardcoded
tests gate on nothing. Do not write this as "the same documents for the same reason", and do not
add a compatibility branch to keep the old width — the width is the defect.

Two things the retirement must not take with it:

- **The unrelated third branch stays.** A project-declared roster type whose body is generated is
  not a view question and is left exactly as it is. The custom-skill admission stays too, and
  falls out of the derivation rather than being special-cased: a custom skill has no seeded view,
  so nothing requires anything of it.
- **The role-authoring remedy moves rather than disappearing.** Today's role refusal names the
  real remedy — declare the definition in `.overrides/roles.toml`, or in
  `.overrides/roles/<slug>.toml` for a project-defined role. A generalised refusal composed from
  a view's name cannot carry that sentence without a per-view message key, which is declaration
  growth for one string. The pointer belongs to the role surface and stays reachable from
  `sq role <slug> show`'s empty-body hint (`views.empty_body_hint_state`'s consumers). Check the
  skill-side consumer for parity while you are there.

The convergence consequence of this narrowing is ST11 and ST12; neither is optional, and landing
the retirement without them opens a data-loss path.
<!-- sq:subtask:ST9:body:end -->

#### Discussion

<!-- sq:subtask:ST9:discussion -->
<!-- sq:subtask:ST9:discussion:end -->
<!-- sq:subtask:ST9:end -->

<!-- sq:subtask:ST10 -->
### ST10 — Regression shapes, falsification, and the gate

<!-- sq:subtask:ST10:body -->
Service-level tests and CLI smoke tests, covering the owed shapes — each asserted, not assumed.

## The required rule

- a replace refused on a milestone (the case that has never been refused before);
- `--force` failing to lift it, and the refusal landing before the overwrite guard — a pristine
  body on a required host is refused too;
- an append succeeding on that same milestone;
- an append still refused on a role and on a permanently-system skill, through the sweep's
  classification rather than a type literal;
- the bulk importer's `body` op refused by the same closure as the single-item path, proving one
  closure and not two;
- `view rm` refused on a host and permitted on a hand-placed non-host, with the three recovery
  removals (undeclared name, inapplicable source, non-required view) still free;
- a retype into a required host producing a readable document and a reported finding, with no
  refusal and no rewrite;
- a view dropped from `[selected]` requiring nothing — no refusal, no finding;
- a `required = true` view that nothing seeds loading cleanly and binding nothing;
- the file-level finding firing on a file too broken to parse, keyed on type folder and filename
  slug alone;
- the role-authoring remedy reachable from `sq role <slug> show`'s empty-body hint once the
  refusal message no longer carries it.

## The narrowing, as a behaviour change

These are the shapes a substitution would not have owed, and they are table-driven over the three
documents rather than one example of one:

- a role body written and read back with `role_definition` dropped from `[selected]`;
- the same for a permanently-system skill (`squads`, `greeting`, `sq-memory`);
- a stale historically-bundled `sq-<type>` body written after its type is dropped — the region
  that is dead today, refused by the write path and unreachable by the sweep;
- a *project-declared* type's stale `sq-<type>`, asserted **unchanged**: it is already writable,
  so the narrowing must not be reported as reaching it;
- that authored prose surviving a `sync`, a `repair`, and a version-drift backfill untouched.

## The round trip, whole

One test drives **drop → author → re-add** end to end, because that is the sequence the wide
convergence licence loses text on: the view dropped, the body authored, the view re-added, a
version-drift backfill run, and the author's prose still there afterwards with the tag placed
beside it. Assert the prose, not just the tag — a test that only checks the tag passes on the
data-loss path.

## Everything else

- Falsify every new test before handback: break the behaviour, watch the test go red, restore it,
  watch it go green, and report both halves. Falsify the round-trip test against the *wide*
  convergence branch specifically — restore it and watch the prose be replaced — so the assertion
  is proven to catch the loss rather than assumed to.
- Run `tests/meta` whenever a module constant is added.
- Gates: `uv run --all-extras pyright`, `uv run --all-extras ruff check .`, and
  `uv run --all-extras ruff format --check .` — `--all-extras` on each.
- Targeted tests plus `tests/meta` here; the full suite is the main loop's gate.
- A CHANGELOG entry under the unreleased section as this lands.
<!-- sq:subtask:ST10:body:end -->

#### Discussion

<!-- sq:subtask:ST10:discussion -->
<!-- sq:subtask:ST10:discussion:end -->
<!-- sq:subtask:ST10:end -->

<!-- sq:subtask:ST11 -->
### ST11 — Role and system-skill convergence narrows to strict_empty

<!-- sq:subtask:ST11:body -->
`_converge_body_tag`'s **wide** licence for a role and a permanently-system skill rests, in
writing, on "`set_body` refuses a role's and a permanently-system skill's body unconditionally in
current code … so no code path today can have authored either region". ST9 falsifies that premise,
so the licence goes with the refusal that justified it.

**The data-loss path this closes.** Drop the view, author the body, re-add the view. A
version-drift backfill then runs `_converge_body_tag` non-strict over prose carrying no markers,
takes the `if not sections.find_markers(current)` branch, and **replaces the author's text with
the tag line**. The sweep cannot distinguish that prose from a pre-0.14 plain-prose rendering, and
it may not learn to: both are marker-free plain text, and nothing records a body's or a tag's
provenance.

**A role and a permanently-system skill move to `strict_empty=True`** — the licence a per-item-type
skill already carries for exactly this shape one level up, where a `sq-<type>` slug can be
genuinely custom at one point and become template-owned later. Only an empty or already-tagged
region converges; anything else is left untouched, silently. This adds no new hazard, it moves two
more families into the one the narrower licence was built for.

Done when:

- `_repair_body_tag`'s call site passes `strict_empty=True` for `role_definition` and for every
  `SYSTEM_SKILL_VIEW_NAMES` entry, not only for `ITEM_SKILL_VIEW_NAME`, and both call sites in
  `_services/_maintenance.py` agree — do not fix one and leave the other.
- The module prose that states the wide licence's premise is rewritten to the narrow one; a future
  reader proposing to restore the wide licence is proposing to let a standing sweep guess at
  authored prose, and the docstring should answer that in place.
- The one-time pre-0.14 reclaim the wide branch existed for is not deleted: it moves, and ST12 is
  where it lands. Land these two together.
<!-- sq:subtask:ST11:body:end -->

#### Discussion

<!-- sq:subtask:ST11:discussion -->
<!-- sq:subtask:ST11:discussion:end -->
<!-- sq:subtask:ST11:end -->

<!-- sq:subtask:ST12 -->
### ST12 — The pre-0.14 roster-body reclaim moves into a migration step

<!-- sq:subtask:ST12:body -->
The wide convergence branch ST11 retires exists for one real case: a non-empty, marker-free
`sq:body` on a role or permanently-system skill that is a superseded pre-0.14 plain-prose
rendering. That reclaim is not dropped — it moves to where a one-time licence belongs.

**A migration knows which release the corpus is arriving from, so it can know that a marker-free
role body is a superseded rendering; the standing sweep runs forever and cannot.** That is the
closed, release-scoped licence into a region the standing tool does not get, applied to the one
shape that still needs it.

It also closes the trap the narrower licence would otherwise leave: a legacy-rendered role body is
neither writable (it is a required host) nor convergeable (the sweep is now strict), and would have
had no remedy at all. Converged once by the migration that brings the corpus to this release, it
never needs one.

Done when:

- A migration step converges a marker-free, non-empty `sq:body` on a role and on a
  permanently-system skill to that document's own view tag, reporting the count of bodies it
  changed, in the style the existing runners already use.
- It is idempotent and touches nothing else: an empty region, an already-tagged region, a
  per-item-type skill, and a custom author-defined skill are all left alone.
- The step is the deterministic `run` half, not a manual runbook entry.

Two things to settle before writing code, and to state in the handback:

- **Which migration carries it.** The 0.14→0.15 runner is unreleased, so appending the step there
  costs no second schema bump and no second hard-stop for the team. The consequence is that a
  corpus already stamped 0.15 — this repository's, and only this repository's — will not re-run it.
  Verify first that this corpus needs nothing: every role and permanently-system skill body here
  should already carry its tag, converged by the wide branch before it retires. If any does not,
  say so rather than choosing a migration to fit.
- **What `sq repair` does afterwards.** Nothing, for these two families, beyond the strict rule —
  that is the point. The corpus-level remedy for a genuinely missing tag is `sq view add`, which
  is what the write refusal and the check finding both name.
<!-- sq:subtask:ST12:body:end -->

#### Discussion

<!-- sq:subtask:ST12:discussion -->
<!-- sq:subtask:ST12:discussion:end -->
<!-- sq:subtask:ST12:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-14T13:59:16Z] Olivia Lead:
  - Amended for op-pierre's ruling on FEAT-907: catalog member only. This repository does not select the advisory in its own spec and no `squads/.overrides/workflow.toml` is created, so the advisory will not fire here on any type — accepted, and now stated in the body rather than left as an open question. ST3 is cancelled with the reason on it (not removed, so the decision stays legible); the summary, the "what lands" item and the `sq check` acceptance line are reworded to match. Everything else on the task is unchanged and still lands as written. `sq check` clean.
- [2026-09-14T20:13:25Z] Olivia Lead:
  - - Rescoped and renamed for ADR-880's fourth amendment and the op-pierre ruling it records. The
      task now builds the `required` view flag: the `ViewSpec` key and its false default, the one
      derived host-set helper, the unconditional replace refusal in `_body_mutate`, the separate
      sweep-keyed append rule, the `view rm` narrowing, the tier-1 `sq check` finding, all six
      bundled views taking `required = true`, and the `set_body` branch retirement with the role
      remedy moving onto `sq role <slug> show`'s empty-body hint. Ten subtasks, ST3 left Cancelled.
      Left **Draft** — promotion at dispatch is still mine.
    - Dropped: the warn-level catalog member and everything it needed (`VALIDATOR_NAMES` /
      `DEFAULT_VALIDATOR_LEVEL` / `UNGUARDED_VALIDATOR_NAMES`, category placement, this project's
      selection, and the `squads/.overrides/workflow.toml` that selection required). Fenced in the
      body so a dev does not rebuild it on noticing the gap. The `implements ADR-864` ref came off
      with it — nothing here implements the declared-level catalog grammar any more, and the tiering
      decision this lands on is ADR-880's own. `implements ADR-880` and `depends-on TASK-941` stand:
      the host-set helper consumes `template_seeded_view_names`, and `milestone_rollup` is only
      satisfiable because the seeding and the corpus migration landed there.
    - **Parenting — my recommendation is a new feature under EPIC-897, which is the product owner's
      to author, so I have not created it.** FEAT-907's outcome is "the milestone roll-up is seeded
      and the corpus migrated", and its US1-3 are delivered. The new scope binds 4 milestones, 10
      roles and every system skill, changes the shared body-write closure, retires two per-type
      refusals, and adds a third unconditional file-level finding — none of which FEAT-907 states,
      and none of which its acceptance would ever test. Its natural sibling is the tag placement and
      check-integration feature, not the milestone one: this is the view mechanism's integrity half.
      Leaving it where it is means either closing FEAT-907 against an outcome one of its stories does
      not describe, or holding a delivered feature open on unrelated work. If it moves, US4 moves
      with it and the ten subtask story mappings are remapped at the same time.
    - Two things for the manager before dispatch. First, the projection-layer deletion feature edits
      the same `ViewSpec` model and the same view-grammar doc sections this task adds a key to —
      textual collision, not a semantic dependency, so sequence them rather than running them in one
      tree. Second, FEAT-907's own Scope section still carries the deleted advisory as a bullet
      ("a warn-level, catalog-only `sq check` advisory … this project selects it in its own spec") —
      a feature body is the product owner's to edit, and it needs one either way.
    - One judgment call I want on the record rather than found in review: deriving the host set from
      the sweep's classification is **narrower** than today's bundled-blind `is_system_skill` test,
      so a system skill whose view was dropped from `[selected]`, and a stale `sq-<type>` skill whose
      type is no longer declared, stop having their bodies refused. That follows from "an undeclared
      view has no hosts" and I read it as intended, but it is a behaviour change on a surface the
      amendment describes as retiring with no behaviour change — called out in ST2 to be asserted,
      not discovered.
    - `sq check` clean. @manager for dispatch once the parenting is settled; @product-owner for the
      feature call and FEAT-907's Scope bullet.
- [2026-09-15T08:06:57Z] Olivia Lead:
  - Reparented to FEAT-948 and folded in ADR-880's fifth amendment. Still **Draft** — promotion at dispatch is not mine to take here.
    
    - **Story remapping** (FEAT-907 US4 → FEAT-948 US1–US5): ST1, ST2 → US1 (the flag + the derived host set). ST4 → US2 (the replace refusal). ST5, ST6 → US3 (append and `view rm` scoping). ST3, ST7 → US4 (the tier-1 finding; ST3 stays Cancelled and records that there is no selection to take). ST8, ST9, ST11, ST12 → US5 (the six declarations and the retirement). ST10 is left **unmapped on purpose** — it is the cross-story verification subtask and mapping it to one story would misattribute four others.
    - **Two new subtasks, both obliged by the fifth amendment.** ST11: `_converge_body_tag` moves a role and a permanently-system skill to `strict_empty=True`. ST12: the pre-0.14 legacy reclaim the wide branch existed for moves into a migration step. These are not optional — the narrowing falsifies the wide licence's stated premise ("no code path today can have authored either region"), and drop → author → re-add then has a version-drift backfill replace the author's prose with the tag line. Landing ST9 without ST11/ST12 ships that data-loss path.
    - **ST2 rewritten**: three narrowing shapes, not two (the dropped-`role_definition` role is the third), and the stale `sq-<type>` shape narrows **only for a historically-bundled type** — a project-declared type's stale skill is already writable, so it must not be claimed. ST9 rewritten to state the retirement as a narrowing rather than a substitution. ST10 rewritten with the new regression shapes, including one test driving the whole round trip and asserting the **prose** survives, not just that the tag is placed.
    - **One sequencing call I want ruled before dispatch (ST12).** `_v0_14_to_v0_15` is unreleased, so appending the reclaim step there costs no second schema bump and no second hard-stop for the team. The consequence is that a corpus already stamped 0.15 — ours, and only ours — will not re-run it. I have scoped it that way and told the dev to verify first that this corpus needs nothing (every role and permanently-system skill body here should already carry its tag, converged by the wide branch before it retires) rather than choosing a migration to fit. The alternative is a 0.15→0.16 bump.
    - **Gap in the feature's acceptance, for @product-owner**: FEAT-948 US5 names the declarations and the retirement but not the convergence licence that retires with them. ST11/ST12 map there and the acceptance line does not cover them.
    - Earlier sequencing note still stands: the projection-layer deletion feature edits the same `ViewSpec` model and the same view-grammar doc sections — textual collision, sequence rather than share a tree.
    
    `sq check` clean. @manager ready for dispatch behind TASK-941 once ST12's migration call is ruled.
- [2026-09-15T08:21:57Z] Pierre Chat:
  - Ruling on where the pre-0.14 legacy reclaim lands: append it to the unreleased 0.14 to 0.15
    migration step rather than cutting a 0.15 to 0.16 bump. 0.15 is not released, so this costs no
    second schema bump and no second hard-stop for anyone sharing the project.
    
    The consequence is accepted and must not be papered over: a corpus already stamped 0.15 -- ours,
    and only ours -- will not re-run it. The dev verifies first that this corpus needs nothing, and
    reports what it found, rather than assuming the answer that suits the choice.
<!-- sq:discussion:end -->
