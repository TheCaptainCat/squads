---
id: TASK-767
sequence_id: 767
type: task
title: Project a role's resolved name and mission onto its own item fields
status: Done
author: tech-lead
assignee: python-dev
priority: medium
refs:
- BUG-756:fixes
- ADR-766:implements
description: A declared projection table on RoleDef, looped by the reconciler, plus
  the override description that reaches nothing today
created_at: '2026-08-21T19:50:11Z'
updated_at: '2026-08-22T09:26:30Z'
---
<!-- sq:body -->
A role override that declares `full_name` renames the role everywhere except the item's own record.
The one path that carries an override onto a live role item merges only the resolved definition's
`to_extra()` output, so a declared name reaches `extra.full_name` while the item's `title:` keeps
what `create` stamped at activation. The record disagrees with itself, and the stale string is not
merely displayed — it is what `sq search` indexes.

Driven, both role kinds, `sq sync` exit 0 in each:

- **Developer role** — `sq dev add --tech python`, then a `python-dev.toml` declaring
  `full_name = "Grace Hopper"`: `sq list -t role` shows `Elias Python`, `sq role python-dev show`
  shows `Grace Hopper`, and the frontmatter holds `title: Elias Python` beside
  `extra.full_name: Grace Hopper` in one file.
- **Bundled role** — `sq override scaffold --role architect`, `full_name = "Ada Lovelace"`:
  identical split. `title: Robert Architect` beside `extra.full_name: Ada Lovelace`;
  `sq list -t role` stale, `sq role architect show` and the compiled `CLAUDE.md` roster correct.
- `sq search Robert` matches and reports the hit as `title: Robert Architect`.

**The same split exists on a second pair.** `create` also stamps `description=role.mission`, and
`to_extra()` carries `mission` into extra, so a declared `mission` updates `extra.mission` and
leaves the item's `description:` on the bundled text. The visible result is one command
contradicting itself: `sq role <slug> show` prints the declared mission in its card and the bundled
mission under `## Mission` in the body beneath it.

ADR-766 settles the design and is Accepted. Read it in full — the constraints below are its rulings
restated as acceptance, not prose to reinterpret.

## The shape of the fix

**The resolved value is written to the item's own field; rendering learns nothing.** `Item.title`
stays the authoritative display name for every item type, roster types included. The resolved
`full_name` is projected into `Item.title` and `mission` into `Item.description` by the one writer
that already resolves the override.

**The pairing is declared as data, beside the pairing it mirrors — this is the load-bearing half.**
`RoleDef` gains a projection table next to `_EXTRA_FIELD_KEYS` (`src/squads/_roles/_catalog.py`)
carrying the item-field column — `title` from `full_name`, `description` from `mission` — and the
reconciler loops over it exactly as it loops over `to_extra()`.

Two hand-written assignments would fix the two instances and leave the trap. The defect class is
**one fact, two stored homes, and a writer that knows one of them**, and it has already produced
three variants: the two pairs above plus the dropped field below. A declared table makes a `RoleDef`
field that also lands on a top-level item field impossible to half-wire, because the pairing is
stated once, in the same class, in the same shape as the pairing that already works. **A pair of
inline assignments does not satisfy this task**, however green the tests are.

## Fold in: the declared `description` that reaches nothing

A `description` declared in a role override reaches nothing at all. `create` stamps
`extra.description` once at activation, but the key is absent from `_EXTRA_FIELD_KEYS`, so the
reconciler never refreshes it and the generated `.claude/agents/<slug>.md` keeps the bundled
one-liner. Same seam, same table, one dev.

### Hard constraint: land it without widening the skew exemption

`PERMITTED_EXTRA_SKEW` is literally `frozenset({X.SKILLS, *RoleDef.extra_keys()})`
(`src/squads/_itemfile.py`), and `extra_keys()` reads the key column of `_EXTRA_FIELD_KEYS`. So
**naively adding the key to that table silently widens the guard's exemption** — the unsafe
direction, because an exempt key is one the skew guard stops comparing. The field must land without
`extra_keys()` gaining a member.

Two shapes are defensible — a separate table for reconciled-but-not-exempt keys whose members
`extra_keys()` deliberately excludes, or an explicit exemption column on the existing table so
`extra_keys()` reads a narrower projection of it. Pick one, and **state in the handoff which you did
and why**. Acceptance below pins the outcome by asserting the frozenset's exact membership, so a
silent widening fails rather than passing quietly.

## Hard constraints on where and how this writes

- **The projection lands in the pure half of `_refresh_catalog_extra`**
  (`src/squads/_services/_maintenance.py`), ahead of the transaction, and **must reach the
  `if not previous` gate** so a name-only change is not skipped as a no-op.
- **The rollback needs a top-level counterpart.** The existing rollback is `extra`-shaped; without a
  counterpart a skipped write leaves the in-memory item claiming a value disk does not have, which
  is the exact property that rollback exists to hold.
- **No new write and no new position in the order.** The projection adds fields to the frontmatter
  block the existing single `update_frontmatter` call already writes, inside the existing
  transaction, with `db.add` after it and the index commit last. Invariant 8 is satisfied by the
  write it rides. Do not add a second write, and do not reorder.
- **It must not route through `_update_model`.** That path recomputes `slug = slugify(title)` and
  moves the file. A roster item's path slug is its **role slug**, not a slug of its title —
  `agents/roles/ROLE-000002-architect.md` carries `title: Robert Architect`. Routing the projection
  through the rename path would relocate that file, which no override asked to change. **This is the
  one mistake that turns this from a display fix into a data-loss bug.** Title and slug are already
  decoupled for roster items and stay so.
- **The skew guard needs zero change.** `title` and `description` are top-level frontmatter keys;
  `_without_permitted_extra_skew` trims only the nested `extra` mapping and structurally cannot
  reach either of them, and `frontmatter_skew` compares them as ordinary fields. That is the correct
  treatment, not an oversight: the reconciler writes markdown then index in one transaction, so a
  completed projection leaves both sides equal and an interrupted one leaves markdown ahead — the
  one sanctioned direction, which `sq repair` heals by adopting the file's value. **A dev
  "helpfully" extending the guard to cover the new fields is a regression, not a hardening.**
- **The `extra` copies stay.** Dropping `full_name`/`mission` from `to_extra()` to make the
  top-level fields the single home was considered and rejected: a key that leaves the table leaves
  the exemption, so it would trade a duplicated string for a hand-maintained exception inside the
  integrity core, move a documented storage location, and owe a corpus migration — for no
  behavioural difference once one writer owns both fields. The roster views'
  `extra.get(FULL_NAME, it.title)` / `extra.get(MISSION, it.description)` fallbacks also stay, as
  the fallback for an item predating those keys.
- **No `sq check` rule.** The disagreement is transient by construction and heals on the next sync;
  a gate firing on every pre-fix corpus is noise in a repo where `sq check` must stay clean. Do not
  add one, and do not treat its absence as an oversight to fix.

## Out of scope

The role body template renders `description or extra.get('mission')`, and the decision notes the
line would read better preferring `extra.get('mission')` so a squad that has not yet synced renders
the declared mission. **Not in this task.** Editing a bundled template fails the manifest-freshness
guard until the generator script is re-run, and that script keys the new hash on the current package
version — which is still the last released one, so a dev-time regen would rewrite a shipped
release's recorded hash. It is also moot once one writer owns both fields. Raise it in your handoff;
it belongs with a version bump, not here.

## Sequencing

Two devs are working in `src/squads/_cli/` and `src/squads/_roles/` right now. **Do not start the
`_roles/_catalog.py` or `_services/_maintenance.py` edits until those land** — concurrent edits to
`_roles/` in particular would collide, and a review in a shared tree produces false findings.

## Acceptance criteria

- **Both pairs, both role kinds, driven.** For a bundled-slug override and for a `<tech>-dev.toml`,
  an override declaring `full_name` and one declaring `mission`: after `sq sync`, the item's
  frontmatter, the index, `sq list -t role`, `sq role <slug> show` (card **and** the `## Mission`
  body beneath it) and the compiled `CLAUDE.md` and `AGENTS.md` roster lines **all agree on the
  declared value**.
- **Assert the declared string, never agreement between the two copies.** A test asserting only
  that `title` agrees with `extra.full_name` passes on a projection that writes the stale value into
  both, so it proves nothing.
- **Drop either row from the projection table and the matching test must go red naming the bundled
  value.** Drive that falsification for both rows and report red-then-green.
- **The declared `description` reaches the generated pointer**: `.claude/agents/<slug>.md` carries
  the override's one-liner after `sq sync`, for both role kinds.
- **`PERMITTED_EXTRA_SKEW`'s membership is unchanged**, asserted as an exact frozenset in a test, and
  `RoleDef.extra_keys()` gains no member. State in the handoff which shape you used to land the
  `description` field without widening it.
- **The item's path is unchanged across a `full_name` rename**, asserted directly. Route the
  projection through the title-rename path instead and that test must go red on a moved file.
- **An override declaring neither field leaves `title` and `description` byte-identical** — the test
  that catches a projection writing unconditionally and keeps the `if not previous` gate honest.
- **A value equal to the current one takes the no-op path**, asserted rather than assumed.
- **File shapes, not just fields**: a bundled-slug override, a `<tech>-dev.toml` on the **second** of
  two developers (the other developer's `title` must be untouched), an override on a retired role,
  and one declaring a value equal to the current one.
- **A pre-split corpus heals**: an item already carrying a stale `title`/`description` from an
  earlier release converges on the next `sq sync`, with no migration and no manual step.
- **The skew guard is byte-identical** — no change to `_without_permitted_extra_skew`,
  `frontmatter_skew`, or `_exempt_extra_keys` as part of this work.
- **The rollback is covered**: a simulated write failure leaves the in-memory item truthful to disk
  on the top-level fields as well as on `extra`.
- **The reflog is untouched.** Its create/update deltas record the title as it stood at the time; a
  log line is a historical record, not a projection, and must not be refreshed.
- `sq check` is clean on a squad carrying a `full_name`-declaring override, **both before and after**
  the sync that applies it.
- `uv run --all-extras pyright`, `ruff check`, `ruff format --check` and the full `pytest` suite are
  green, `tests/meta` included.

## Handoff

**Do not edit `CHANGELOG.md`.** Several items in this batch run concurrently and a shared file would
have them racing. Put your adopter-facing changelog entry text in your handoff comment on this item
and the tech lead applies it.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 767 add-subtask "<title>"`; track with `sq task 767 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-21T19:50:34Z] Olivia Lead:
  - Authored against ADR-766 (linked, implements). Body carries the projection table as the deliverable and states explicitly that a pair of inline assignments does not satisfy the task, however green the tests are — the defect class is one fact with two stored homes and a writer that knows one of them, and it has produced three variants already.
  - Grounded from source: PERMITTED_EXTRA_SKEW is frozenset({X.SKILLS, *RoleDef.extra_keys()}) and extra_keys() reads the key column of _EXTRA_FIELD_KEYS, so the dropped description field cannot simply be appended there. Acceptance pins the frozenset membership exactly so a silent widening fails, and requires the dev to state which shape they used. The _update_model hazard is called out as the one mistake that makes this a data-loss bug: _rename recomputes slug = slugify(title), and ROLE-000002-architect.md carries title Robert Architect.
  - One deliberate scope cut: the role.md.j2 precedence tweak the ADR notes in Consequences is OUT of scope. Editing a bundled template fails the manifest-freshness meta guard until scripts/gen_template_manifest.py is re-run, and that script keys the new hash on the current package version (still 0.13.0), so a dev-time regen would rewrite a shipped release entry. It is also moot once one writer owns both fields. Flagged for a version-bump-adjacent item instead.
- [2026-08-21T20:29:03Z] Elias Python:
  - Landed the projection table (RoleDef._ITEM_FIELD_PROJECTION, beside _EXTRA_FIELD_KEYS): title from full_name, description from mission. _refresh_catalog_extra loops it exactly as it loops to_extra(), assigning directly onto item.title/item.description (never through _update_model/_rename), with a top-level previous_fields rollback alongside the existing extra rollback, both gating the same 'if not previous' check. Commit 03c0802.
  - Driven, bundled + dev role, before/after: architect full_name override -> Ada Lovelace: title/extra.full_name/index/sq-list/CLAUDE.md all Ada Lovelace (were Robert Architect on title/list). python-dev full_name -> Grace Hopper: same split closed (was Elias Python on title/list, Grace Hopper on extra/card, now Grace Hopper everywhere). architect mission -> 'Secure the whole system.': description + ## Mission body now show it (was the bundled ADR/mission text). python-dev mission -> 'Own the whole backend.': same.
  - Dropped 'description' (the pointer one-liner): landed via a second table, _RECONCILED_EXTRA_KEYS, merged into to_extra()'s output but NOT read by extra_keys() -- so PERMITTED_EXTRA_SKEW stays frozenset({X.SKILLS, X.FULL_NAME, X.SLUG, X.TITLE, X.MISSION, X.RESPONSIBILITIES, X.AGREEMENTS, X.MODEL, X.COLOR, X.IS_DEFAULT, X.CAN_SPAWN}) unchanged and extra_keys() gains no member -- pinned exactly in tests/unit/test_role_def_extra_keys.py. Declared description now reaches .claude/agents/<slug>.md for both role kinds.
  - Path-unchanged proof: test_the_items_path_is_unchanged_across_a_full_name_rename asserts item.path/item.slug ('architect') are byte-identical before/after a full_name rename and the old file still exists at that path -- passed.
  - Falsification driven both ways: removing either _ITEM_FIELD_PROJECTION row turns the matching new tests red, citing the bundled value (Robert Architect / Elias Python for the title row; the bundled ADR/python mission text for the description row); restored and green after.
  - Also covered: no-op gate (neither field declared -> byte-identical; equal value -> update_frontmatter never called), second-dev isolation, retired-role reconciliation, pre-split-corpus healing on next sync, and a simulated write-failure rollback proven downstream (the same sync pass's pointer/body regen used the rolled-back value, not the attempted one).
  - CHANGELOG entry (mine to hand off, not landed): '**A role override's declared name, mission, and one-line description now reach the role itself, not just its internal record.** Renaming a role (full_name) or rewriting its mission (mission) in a .overrides/roles/<slug>.toml file used to update sq role <slug> show and your generated CLAUDE.md/AGENTS.md roster, but leave the role's own record -- what sq list, sq show, and sq search all read -- carrying the old name and mission, so the same command could show two different names for the same role depending on which surface you asked. Both now update together, and sq search matches the name you declared rather than the one you replaced. A declared one-line description, previously ignored no matter what it said, now reaches the generated agent pointer file too.'
  - Out of scope per the task: agents/role.md.j2's field precedence (bundled template, manifest keyed on 0.13.0) -- untouched.
  - Gates: pyright 0 errors; ruff check all passed; ruff format --check clean; tests/meta 180 passed; tests/service+unit+cli filtered on role/override/sync/check/itemfile/repair 846 passed, 0 failed. sq check clean before and after; sq repair a stable no-op (identical diff across two runs).
<!-- sq:discussion:end -->
