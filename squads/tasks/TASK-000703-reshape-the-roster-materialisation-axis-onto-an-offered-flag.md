---
id: TASK-703
sequence_id: 703
type: task
title: Reshape the roster materialisation axis onto an offered flag
status: Done
parent: FEAT-691
author: tech-lead
priority: urgent
refs:
- ADR-696:implements
- TASK-699:depends-on
- TASK-700:blocks
- TASK-701:blocks
- TASK-702:blocks
description: Replace the active-role-keyed accessors with an offered flag on the status
  role, the lifecycle's initial as create-at target, and R1/R1'/R2
subentities:
- local_id: ST1
  title: Add offered to the status role and the bundled spec
  status: Done
- local_id: ST2
  title: Reshape the two role-keyed accessors onto the flag
  status: Done
- local_id: ST3
  title: Convert the nine call sites the three ways they split
  status: Done
- local_id: ST4
  title: Restate the roster lifecycle floor as R1, R1' and R2
  status: Done
- local_id: ST5
  title: Keep the no-status-literal guard and the grammar true
  status: Done
created_at: '2026-07-30T10:06:00Z'
updated_at: '2026-07-31T12:41:27Z'
---
<!-- sq:body -->
## What this changes

ADR-696 was amended after the roster-semantics foundation landed, and the amendment retires
vocabulary that foundation introduced rather than sitting beside it. Three rulings:

- **The materialisation axis is a boolean on the status-role object, not a role name.** `offered`
  joins `settled`/`hidden`/`color` on `RoleSpec`, defaulting **false**. Keying materialisation off
  the role literally named `active` is the same name-locking the decision exists to forbid, one
  layer up. Non-settled was checked as a substitute and rejected on the evidence: four bundled
  roles are non-settled (`active`, `attention`, `blocked`, `pending`), so an adopter's `Suspended`
  on a `blocked` role or `Provisional` on `pending` would read as offered and be written into the
  agent host's config — backwards in the one direction that matters.
- **The create-at target is the lifecycle's declared `initial`,** not a role-keyed accessor. The
  spec already names one and the existing lifecycle checks already validate it.
- **The two role-name-keyed accessors are reshaped, not supplemented.** After the conversions
  below, nothing needs a `role_statuses(item_type, role_name)` or `sole_role_status(item_type,
  role_name)`. Keeping them alongside the new pair leaves two public accessors with no caller,
  which the periodic dead-code scan will flag and this project treats as signal.

The default direction is deliberate. `hidden` defaults false because wrongly hiding an item is
worse than wrongly showing it; `offered` defaults false for the mirrored reason — wrongly offering
an entry writes an agent into a host's config, which is worse than wrongly withholding one. A
custom role is not offered until its author says so.

## Why the nine converted sites split three ways

The amendment's call-site verdict is not a mechanical substitution. Each site was checked against
the code and the group it belongs to is a design answer:

| Sites | What they need | After |
| --- | --- | --- |
| `_services/_roster.py` — `activate_role`, `add_dev`, `add_skill`, `add_operator` | the lifecycle's own `initial` | **drop the `status=` argument** — `create()` already defaults it to `self.spec.initial_status(item_type)` |
| `_services/_maintenance.py` — the four system-skill seed sites (2 `Item(...)` constructions + their 2 matching reflog payloads) | created **offered**, not merely created | the offered-initial accessor |
| `_cli/_role.py` — the roster table's tick column | the offered predicate | the offered-statuses predicate, and a column header that stops saying `Active` |

The middle row is the exception and its reason must survive in the code, not only here. Those four
sites are squads scaffolding its own system skills, and **a generated role entry preloads a skill
by slug, never consulting that skill item's status.** Seeding a system skill at an unoffered
`initial` would therefore leave a freshly initialised squad with every role entry preloading three
skills that were never materialised — a config-invalid state produced by a clean `sq init`, in a
project that did nothing wrong, and precisely the state the config-integrity reporter is being
written to detect. Scaffolding must create offered; user-facing creation (a custom skill, the
roster `add`/`activate` verbs) honours whatever `initial` the project declared.

## The floor, restated

- **R1 relaxes from `exactly one` offered status to `at least one`,** and the uniqueness rationale
  is withdrawn rather than qualified — it was buying an unambiguous create target the lifecycle's
  `initial` already supplied.
- **R1′ is new and narrow: if the lifecycle's `initial` is not offered, exactly one status is
  offered.** This is the only sliver `initial` cannot cover, and it is what keeps the offered-initial
  accessor total for the scaffolding path.
- **R2 is restated against the flag:** at least one settled, *unoffered* status reachable from an
  offered one. Retirement must be reachable — an entry must be able to stop being offered. A
  merely-paused state (unoffered but live) satisfies the spirit but not R2; a lifecycle needs a real
  end as well as a pause, and may have both.

What the relaxation buys: a project may declare an unoffered `initial` and get a
parked-then-activated roster entry with no special casing anywhere in the engine — the create path
reads `initial`, the projection reads the flag, and the two simply disagree for a while.

## Scope boundaries

- **Spec-format change only — no schema bump, no migration runner.** Neither a role name nor its
  flags ever appear in item frontmatter or the index; they are workflow-spec vocabulary. This is
  the same reasoning used for dropping the stored `terminal`/`is_open` per-status fields.
  `sq workflow roles --json` gains the field **additively**.
- **The `[selected]` deselect-table rename is not in scope.** It is override-engine work under the
  reopened customisation epic. This task changes nothing about how overrides merge.
- **The wider adopter-facing stability rewrite is not in scope.** Two statements there go wrong
  when the override engine lands (additive-only overrides, the reserved status names); this task
  touches only the one grammar line the renamed column makes stale.
- The bundled roster lifecycle keeps its two states. With the flag on the live role, `initial` is
  itself offered, so R1 holds and R1′ vacates; the retired status is settled, unoffered, and
  reachable, so R2 holds. No squad on disk breaks.

## Constraints

- The repo-hygiene scan added by the foundation task (`tests/meta`, no bundled roster status name
  as a bare literal in `src/squads/` outside `_bundled/` and `_migrations/`) **must keep passing.**
  Two things inside it go stale and are part of this work, not optional tidying: its allowlisted
  hit for the roster table's `Active` **column header** points at a line that no longer says
  `Active`, and its docstring and one of its own self-tests cite the retired accessors and the
  sanctioned role literal `"active"` — after this, no engine site names that role literal at all.
- Migration runners keep their frozen `_STATUS_ACTIVE` module constants. A migration transforms a
  corpus written at a pinned schema version and must read the vocabulary that version used, never
  the live spec. Those are already private constants, not imports of a shared name, so nothing
  here touches them.
- Gate: `uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras
  ruff format --check .` clean, plus the full suite. `--all-extras` on each is required.
- Falsification is expected. For every behavioural assertion added, break the implementation,
  watch the test go red, restore it, watch it go green, and report both.

## Done when

- `offered` is a declared field on the status role, defaulting false, present in the bundled spec
  on the offered role and in the role-catalog JSON.
- No role-*name*-keyed status accessor exists on the spec, and no engine site names a bundled
  roster status literal or the role literal `"active"`.
- A clean `sq init` still produces a squad whose every role entry preloads system skills that are
  themselves offered.
- The four roster create verbs pass no `status=` at all.
- A spec with zero offered statuses on a roster lifecycle, and one with an unoffered `initial` plus
  two offered statuses, are each refused at load with the offending type named; `sq workflow lint`
  reports every violation at once.
- Behaviour is unchanged for a bundled squad, end to end.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 703 add-subtask "<title>"`; track with `sq task 703 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add offered to the status role and the bundled spec

<!-- sq:subtask:ST1:body -->
A fourth boolean on the status-role object, alongside `settled`, `hidden`, and `color`:

```toml
[roles.active]
settled = false
hidden  = false
color   = "positive"
offered = true
```

`RoleSpec` is frozen with `extra="forbid"`, so the field is declared there with a `False` default —
that default is the fail-safe-withheld direction and must not be flipped to make a test pass. The
role docstring should say what the flag *means* (this entry is on offer, and therefore available to
be spawned, loaded, cited, and assigned) rather than what a backend does with it; materialisation is
the downstream consequence, and the flag lives in vocabulary every item type shares, so it has to
read sensibly on a work status too.

The bundled spec gains `offered = true` on the one offered role and takes the default everywhere
else. Check every declared role before assuming which one: an adopter reading the bundled file
learns the convention from it.

The role catalog surface gains the field **additively** — the frozen field tuple, the row builder,
the human table column, and the command's own help text describing what a client joins. Widen the
tuple's annotation rather than leaving it stale.

Two downstream surfaces are load-bearing and are part of this subtask, not follow-up:

- The spec golden-lock test asserts the bundled role table byte-for-byte and will fail until it
  carries the new field.
- The VS Code client's role-catalog contract: its entry type, its runtime type guard, its committed
  fixture, and its skew canary. The canary's shape assertion is a subset match and survives, but it
  also asserts **exact object equality** on the offered role's row — that one breaks and must be
  updated deliberately, because it is the assertion that would otherwise hide a field the client
  silently ignores.

No `SCHEMA_VERSION` bump and no migration-registry entry. Neither the role name nor its flags ever
appear in item frontmatter or the index, so a migration would be the wrong instrument — the same
conclusion reached when the stored per-status `terminal`/`is_open` fields were dropped. If that turns
out to be false, stop and say so rather than adding a runner quietly.

Done when the flag is declared with a false default, the bundled spec carries it on the offered
role, the catalog JSON emits it, and every golden/fixture/canary that pins the role shape agrees.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Reshape the two role-keyed accessors onto the flag

<!-- sq:subtask:ST2:body -->
Two derived accessors on the workflow spec, computed from the type's lifecycle states and the
existing resolved-role lookup — no new stored field, nothing an adopter declares twice:

- **An offered-statuses predicate** — the states of that type's lifecycle whose resolved role carries
  the flag, returned as a frozenset. This is the **read** axis: "is this entry on offer" is a
  membership test against it.
- **An offered-initial accessor** — the status an entry squads *itself* scaffolds is created at: the
  lifecycle's `initial` when that status is offered, otherwise the sole offered status. R1′ (ST4) is
  what makes it total; the accessor must still fail closed with a clean `SquadsError` naming the type
  when the spec it is handed does not satisfy the floor, never an `IndexError` or a bare
  `StopIteration`, so a non-roster caller cannot get a silent wrong answer.

Fallback resolution applies to both — an absent `StatusSpec.role` resolves to the declared fallback
role, which carries the default and is therefore not offered.

**Reshape the existing pair; do not add alongside it.** The role-name-keyed read predicate and the
sole-status write-target accessor both lose their last caller in ST3. Two public accessors with no
caller is what the periodic dead-code scan exists to catch, and this project treats that report as
signal rather than noise. Delete them and their tests; do not deprecate.

Settled-ness and default-hiding are already read off the role object and stay that way — this
subtask adds no third way to ask those questions.

Check whether the private resolved-role-name helper still has a caller once the floor (ST4) reads
the role object's flag instead of comparing a role name. If it does not, it goes too. The
`status_role` accessor is a different thing with live callers and stays.

Rename the accessors' test module for the behaviour it now covers. No ticket ID in any source or
test name.

Done when the two new accessors exist with the semantics above, the old pair is gone from the spec's
surface, and the offered-initial accessor is proven total on the bundled roster types and
fail-closed on a spec that violates the floor.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Convert the nine call sites the three ways they split

<!-- sq:subtask:ST3:body -->
The nine sites the foundation task converted to the role-name-keyed accessors are reconverted, and
they split three ways. The group a site belongs to is a design question — do not substitute
mechanically.

**Four roster create verbs — `activate_role`, `add_dev`, `add_skill`, `add_operator` — drop the
`status=` argument entirely.** Not converted to another accessor: deleted. `create()` already
defaults the status to the spec's `initial_status` for the item type, which was verified in the code
rather than assumed. Passing anything explicitly here is what made the roster create path unable to
honour a project's declared `initial`, and dropping the argument is what gives an adopter the
parked-then-activated entry for free.

**Four system-skill seed sites — two `Item(...)` constructions plus their two matching reflog
payloads — take the offered-initial accessor.** These are the exception, and the reason belongs in
the code next to them, phrased about the mechanism and not about this change: a generated role entry
preloads a skill **by slug** and never consults that skill item's status, so seeding a system skill
at an unoffered `initial` would leave a freshly initialised squad with every role entry preloading
three skills that were never materialised — a config-invalid state manufactured by a clean `sq init`
in a project that did nothing wrong. Scaffolding creates offered; user-facing creation honours the
project's declared `initial`. The two reflog payloads must agree with the two items they record, or
the reflog stops being a reconstructable account of what was written.

**The roster table's tick column takes the offered predicate, and its header stops saying `Active`.**
The header is a display label that has been naming a bundled status; what the column actually shows
is offered-ness, and the label should say that. Renaming it is what retires the last allowlisted
status literal in the source tree (see ST5).

Two stale comments fall out and are part of this subtask:

- The bundled roster lifecycle's own comment explains that entries are created directly at the live
  status "via the role-keyed write-target accessor". That stops being true the moment the four create
  verbs drop their argument — they now create at `initial`, which for the bundled spec happens to be
  the same status. Restate the mechanism, and keep the note about why the third state is not part of
  this machine.
- The workflow models module docstring names both retired accessors as the read/write pair.

Behaviour for a bundled squad must be unchanged end to end: `sq init`, `sq role activate`, `sq dev
add`, `sq skill add`, `sq operator add`, and `sq role list` all produce what they produced before.
Assert that as tests, not as an inspection.

Done when no engine site names a bundled roster status literal or the role literal `"active"`, the
four create verbs pass no status, the four seed sites create offered, and the tick reads the
predicate under a header that describes it.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Restate the roster lifecycle floor as R1, R1' and R2

<!-- sq:subtask:ST4:body -->
The additional floor a lifecycle bound to a `category = "roster"` type must satisfy, restated
against the flag. It replaces what the foundation task implemented; the universal clauses are
already enforced and need no change.

- **R1 — at least one status whose role is offered.** Zero means no entry of this type could ever be
  materialised, so the squad's generated config could never present an agent. This *relaxes* the
  landed `exactly one`, and the uniqueness rationale is withdrawn rather than qualified: it was
  justified solely by giving the create path an unambiguous write target, which the lifecycle's
  `initial` already supplies and the existing lifecycle checks already validate.
- **R1′ — if the lifecycle's `initial` status is not offered, exactly one status is offered.** The
  narrow uniqueness the engine genuinely needs, and nothing more: it keeps the offered-initial
  accessor total for the scaffolding path that must create an entry already on offer. When `initial`
  *is* offered there is no ambiguity to resolve and any number of further offered statuses is fine.
- **R2 — at least one settled status, reachable from an offered status, that is not offered.**
  Retirement must be reachable: an entry must be able to stop being offered. The universal floor only
  requires *some* settled status reachable from `initial`, which a machine could satisfy while never
  letting an offered entry retire. Note R2 asks for a *settled* unoffered status — a merely-paused
  state (unoffered but live) satisfies the spirit of "stop being offered" but not R2, because a
  lifecycle needs a real end as well as a pause and may have both. With more than one offered status
  admissible under R1, reachability is computed from the offered *set*, not from a single live status.

All three derive from the role assignment and the `initial` the spec already carries; none adds a
field beyond the flag. The floor must not require any role *name* — retirement is consumed through
`settled`, default-hiding through `hidden`, being-on-offer through the flag, and the create-at target
through `initial`. Requiring names would trade reserved status names for reserved role names at the
same cost to a project whose vocabulary differs.

Keep the loader's two existing calling modes: raise for the service-open path, one finding per
violation with its override path and a fix hint for the lint command. Every violation reported at
once, never a traceback.

Error messages are the deliverable here as much as the predicates. An adopter who declares a custom
roster role and forgets the flag gets a load failure, and the message is the only thing that tells
them why — name the offending type, the lifecycle, and which clause failed. R1′ in particular needs a
message that distinguishes itself from R1, because "too many offered statuses" is only a violation
when `initial` is unoffered.

The landed tests for the old shape need reworking, not deleting wholesale: the zero-offered case is
still a violation, and the two-offered case flips from a violation to *legal* unless `initial` is
unoffered — which is the exact behaviour change worth a test of its own. The reserved-vocab test
asserting a renamed roster status through the old accessors moves onto the new pair.

Done when a spec with zero offered statuses is refused, a spec with an unoffered `initial` and two
offered statuses is refused under R1′, a spec with an offered `initial` and several offered statuses
loads cleanly, a spec whose offered entries cannot retire is refused under R2, and the lint command
reports every violation at once with the type named.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Keep the no-status-literal guard and the grammar true

<!-- sq:subtask:ST5:body -->
The repo-hygiene scan added by the foundation task — no bundled roster status name may appear as a
bare string-constant literal under `src/squads/` outside `_bundled/` and `_migrations/` — **must keep
passing.** Its behaviour is not what changes; three things inside it go stale, and leaving them is
how a guard quietly stops guarding.

- **Its allowlisted hit becomes dead.** The one entry is the roster table's `Active` **column
  header**, keyed by path, line number, and value. ST3 renames that header, so the entry points at
  nothing. Remove it. A line-numbered allowlist entry that no longer matches is worse than no
  allowlist: it survives a file being edited around it and silently starts excusing a different line.
- **Its self-test for the sanctioned role literal cites a retired accessor.** It plants a call to
  the role-name-keyed write-target accessor to prove the scan does not flag the lowercase role name.
  The claim it makes is now historical — after this task no engine site names that role literal at
  all. Either retire the test with the accessor it documents, or keep the narrower fact it actually
  establishes (the scan matches an exact status name, not a lowercase role name) with a planted
  fixture that does not reference deleted code.
- **Its same-line-masking test loses its premise if the allowlist empties.** That test plants two
  constants on one line under the roster CLI path to prove allowlisting one triple does not suppress a
  different value at the same location. With an empty allowlist it still *passes*, while no longer
  testing anything — the worst failure mode for a guard's own test. Either give it a synthetic
  allowlist to work against, or fold the property into the scan's own contract so it stays asserted.

Also true here, and stated so nobody "fixes" it: migration runners keep their frozen private status
constants, because a migration reads the vocabulary of the schema version it transforms and never the
live spec. They are already private module constants rather than imports of a shared name, and the
`_migrations/` exemption is one of the scan's two deliberate ones. Keep the docstring's explanation
of *why* each exemption exists — it is the part that stops a future reader deleting one.

One adopter-facing grammar line goes stale: the roster list command is documented as showing an
"active/inactive marker per row". What it shows is offered-ness, and the wording should follow the
column. Nothing more in the adopter docs is in scope — the larger rewrite the amended decision calls
for (additive-only overrides, the reserved status names) belongs with the override engine, not here.

Done when the scan is green on the converted tree, still fails on a planted literal, carries no dead
allowlist entry, and every one of its own self-tests asserts a property that is still true.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-30T10:09:34Z] Olivia Lead:
  - Cut against ADR-696's second amendment (2026-07-30), which retires vocabulary TASK-699 landed rather than sitting beside it. All seven scope points were verified against the code before writing: the create-default at `_base.py:460`, the four roster `status=` arguments, the four maintenance seed sites and their reflog payloads, the roster table's tick and header, and the landed `exactly one` floor.
  - Two drift items the amendment does not mention, found while verifying. (1) The hygiene scan's `_ALLOWED_HITS` allowlists the roster table's `Active` column header by (path, line, value) — renaming the header makes that entry dead, and a stale line-numbered allowlist silently starts excusing whatever moves onto that line. (2) The scan's own same-line-masking self-test loses its premise if the allowlist empties: it still passes while testing nothing. Both are carried on ST5.
  - One more, found in the client: the VS Code skew canary asserts exact object equality on the offered role's catalog row, so adding the field breaks it even though the shape assertion is a subset match. That is the assertion doing its job and it must be updated deliberately, not loosened. Carried on ST1.
  - Refs: implements ADR-696, depends-on TASK-699, blocks TASK-700/701/702 — the three unstarted tasks are commented with what changed rather than having their bodies rewritten, so the amendment history stays readable.
  - Left in Draft. @manager promote to Ready at dispatch; this wants a single dev pass, since ST2's reshape and ST3's conversions collide on the same files.
<!-- sq:discussion:end -->
