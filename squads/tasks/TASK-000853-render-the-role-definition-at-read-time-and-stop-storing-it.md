---
id: TASK-853
sequence_id: 853
type: task
title: Render the role definition at read time and stop storing it
status: Done
parent: FEAT-694
author: tech-lead
priority: high
refs:
- ADR-776:implements
- ADR-781:implements
- TASK-851:depends-on
description: The role definition producer inverts to a read-time ServiceCore method
  and the role extra mirror stops being written
subentities:
- local_id: ST1
  title: Invert _regen_role_body into a read-time ServiceCore producer
  status: Done
- local_id: ST2
  title: Drop mission and responsibilities from the role show card
  status: Done
- local_id: ST3
  title: Key the no-active-item branch on the item, not the region
  status: Done
- local_id: ST4
  title: Stop writing the role extra mirror keys
  status: Done
  assignee: python-dev
- local_id: ST5
  title: Narrow PERMITTED_EXTRA_SKEW, its pin, and the settable fields
  status: Done
  assignee: python-dev
created_at: '2026-09-01T08:43:24Z'
updated_at: '2026-09-02T14:01:18Z'
---
<!-- sq:body -->
## Scope

The role half of **stages 2 and 3** of ADR-776's second 2026-09-01 amendment §3: the role
definition producer inverts to read time, and the role `extra` mirror stops being written.

Stage 1 — every consumer resolving while the mirror is still written — is the sibling task and is
a hard precondition, not a preference. This task's substitutions are only safe once nothing reads
the mirror.

The corpus strip of what is already on disk is TASK-849. This task changes the write path and the
read path; nothing already on disk is touched here, and after it lands a role file still carries
its stored body and keys until the migration runs.

## Stage 2 — the producer inverts, in the place it already lives

`_regen_role_body` (`_services/_base.py:1293`) already renders `agents/role.md.j2` on
`ServiceCore`. It becomes **`role_definition_text(slug)`** on the same class: same template, same
engine, called at read time, with the **resolved `RoleDef`** as its context instead of
`item.extra`. Its caller in the sync sweep (`_services/_maintenance.py:638`) is deleted, and no
code path writes a role's `sq:body` region afterwards.

**The home is ruled, and the attractive alternative is structurally unavailable.**
`_rendering/_engine.py` imports `squads._interactions`, and `_interactions/__init__.py:35` imports
`squads._roles._catalog` — verified. The rendering engine therefore sits above both packages, so
neither `_roles/` nor `_interactions/` may import it without a cycle. Rendering a role's
definition from the package that owns the role catalog is the symmetric answer and it does not
exist. `ServiceCore` is the only layer that can host it, and it is also where `roster()` and
`roster_all()` live, which are themselves consumers.

`role.md.j2` changes with the context: every
`extra.get('full_name'|'title'|'slug'|'mission'|'responsibilities'|'agreements')` reference becomes
a field on the passed definition. The rendered text is otherwise unchanged.

**The card drops `mission` and `responsibilities`** (ADR-781's 2026-09-01 amendment §2). With no
stored copy left, the double print resolves by removal: the card keeps the resolution facts the
prose does not carry — role title, model, spawn authority, the create lane, the resolved skills
list — and the rendered definition prints the rest once, in the form an agent is meant to read.
`--json` is a different reader and keeps every field it returns today.

## The empty region stays, and the no-active-item branch must not key on it

`ServiceCore.role_body` (`_services/_base.py:1044`) returns `None` both when no item exists for
the slug and when the region is absent, and `sq role show` prints "(no active item for … — run
`sq role activate …`)" on that `None`. After the migration the region is present and **empty** for
every role, so a branch keyed on the region prints that false and alarming message for a role that
is active.

`show_role` already holds the item before it renders anything: key the branch on the item being
absent. Do both — keep the markers, and stop depending on them to answer a question about the
item.

`role_body` itself then has no caller in the show path. Remove it with its last caller, or give it
one with a reason to read raw stored text; do not leave it as a dead read of a region nothing
fills.

## Stage 3 — the keys stop being written

`RoleDef._EXTRA_FIELD_KEYS` (`_roles/_catalog.py`) loses `full_name`, `title`, `mission`,
`responsibilities`, `agreements`, `color` and `can_spawn`; `_RECONCILED_EXTRA_KEYS` loses
`description`. What survives is `slug`, plus `model` for a dev role only — the key stays in the
vocabulary because a dev's model is operator-settable, so the reconciler stops *writing* it for a
non-dev role rather than the key leaving `ExtraKey`.

`is_default` **leaves `_EXTRA_FIELD_KEYS`** too, and by this point that is a tidying rather than a
fix: the sibling task already ended the revert by putting the designation in the merge base, which
is where it permanently belongs. It remains a stored key written only by `sq role set-default`.

`RoleDef.from_extra` retires here — the mirror's reader, left in place through stage 1 with no
call sites precisely so that stage could keep the mirror wholly intact.

`_ITEM_FIELD_PROJECTION` is **unchanged**: `item.title` from `full_name` and `item.description`
from `mission` are the uniform-record fields other surfaces read.

`PERMITTED_EXTRA_SKEW` (`_itemfile.py:66`) is `frozenset(RoleDef.extra_keys())` and narrows to
near-empty with the key table. The test pinning its membership as a literal
(`tests/unit/test_role_def_extra_keys.py`) exists to catch an unreviewed *widening*; narrowing is
the safe direction. It moves in this change with its docstring stating what was removed and why,
so a later reader can tell a reviewed narrowing from an accident.

`_models/_metadata.py::_ROLE_FIELDS` narrows to the retained set, so `sq role <n> update --set`
stops accepting a key the next sync would delete. The refusal names where the value is declared
now — `.overrides/roles.toml`, or `.overrides/roles/<slug>.toml` for a project-defined role —
rather than reporting an unknown field with no remedy.

`activate_role`/`add_dev` (`_services/_roster.py:55`, `:86`) spread `role.to_extra()` into a
larger literal, so they follow the narrowed table with no edit. Verify that rather than assuming
it.

## Accepted consequence

`sq search` stops matching a role's mission or responsibility text — search scans body lines, and
after the migration there are none. Accepted rather than compensated for. `sq role list` /
`sq role catalog` / `sq role <slug> show` answer from the resolver instead, over a value that
cannot be stale.

## Release ordering

This edits `agents/role.md.j2`, so it sits behind ADR-781 §6's ordering: the version bump precedes
any template-manifest regeneration, only the `0.14.0` manifest entry moves,
`scripts/bump_version.py` is not run, and the managed-section golden and the generated-agent-text
guards move with it. Orphan manifest residue is the operator's.

## Acceptance

- No code path writes a role item's `sq:body` region. `sq sync` leaves the region untouched for
  every roster role, live or retired, and running it twice produces no diff on a role file.
- `sq role <slug> show` renders the full definition — identity line, mission, responsibilities,
  skills, working agreements — resolved on the call, for an activated role, a bundled-only role
  and a dev role. A project override reaches that output on the very next command.
- The card no longer prints `mission:` or `responsibilities:`, and still prints title, model,
  spawn authority, the create lane and the skills row. `--json` returns every field it returns
  today.
- An activated role whose `sq:body` region is present and empty prints its definition, not the
  "no active item" hint; a slug with no item still prints the hint.
- `RoleDef.from_extra` no longer exists, and no module reads `extra.full_name`, `extra.title`,
  `extra.mission`, `extra.responsibilities`, `extra.agreements`, `extra.color`, `extra.can_spawn`
  or `extra.description` off a role item — proven by a repository-wide assertion, not by
  inspection. The migration runner's frozen local copy is the one permitted exception and is named
  as such.
- A newly activated role's file carries only the retained keys; a dev role keeps `is_dev`, `tech`
  and `model`, a non-dev role has no `model` written.
- `sq role set-default` still holds across a sync, now with the key absent from `to_extra()` as
  well as present in the merge base.
- `PERMITTED_EXTRA_SKEW`'s pinned membership test asserts the narrowed set, with a docstring
  saying the narrowing is intended and what left.
- `sq role <n> update --set` refuses a removed key with a message naming where the value is
  declared now, and still accepts the retained ones.
- The compiled `CLAUDE.md`/`AGENTS.md` regions and every backend pointer are byte-identical across
  this change, roster held constant — the stage-1 substitutions are what make that true, and this
  is the regression guard on them.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite are clean. `sq check` is clean on this repository.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 853 add-subtask "<title>"`; track with `sq task 853 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Invert _regen_role_body into a read-time ServiceCore producer

<!-- sq:subtask:ST1:body -->
`_regen_role_body` (`_services/_base.py:1293`) becomes `role_definition_text(slug)` on
`ServiceCore` — same class, same template (`agents/role.md.j2`), same engine, called at read time.
Its caller in the sync sweep (`_services/_maintenance.py:638`) is deleted.

**The context becomes the resolved `RoleDef`, not `item.extra`.** That is the substitution that
must not be missed: `_regen_role_body` passes `item=item, description=item.description,
extra=item.extra` today, which is a stored copy of a resolvable value. It becomes
`resolve_role_with_base(slug, squad_dir, base=role_base_from_item(item, squad_dir))` — and
`show_role` already computes exactly that base and already resolves it for the card, so the
producer should take the resolved definition as an argument rather than resolving a second time on
the same call.

`role.md.j2` changes with it: every `extra.get('full_name'|'title'|'slug'|'mission'|
'responsibilities'|'agreements')` reference becomes a field on the passed definition. The rendered
text is otherwise unchanged — the point is where the values come from, not what they say.

**The home is ruled and the symmetric alternative does not exist.** Verified:
`_rendering/_engine.py` imports `squads._interactions`, and `_interactions/__init__.py:35` imports
`squads._roles._catalog`. The engine sits above both, so neither package may import it without a
cycle — rendering a role's definition from the package that owns the role catalog is unavailable,
structurally rather than by preference. `ServiceCore` is the only layer that can call `render`,
and it is where `roster()`/`roster_all()` live, which are themselves consumers of the same
resolution. A new `_definitions.py` concern mixin would read better and be unreachable: the
mixins compose into `Service` and do not import one another, so a producer a core method needs
cannot sit in a sibling.

`--raw` and the piped/non-TTY path are unaffected — the rendered string still goes through
`render_body_text`.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Drop mission and responsibilities from the role show card

<!-- sq:subtask:ST2:body -->
The card drops the `mission:` row and the `responsibilities:` block from `sq role <slug> show`
(`_cli/_role.py`). It keeps the rows the rendered definition does not carry: the display name and
slug line, `title:`, `model:`, `can spawn:`, `creates:`, and the skills row.

This is the removal half of the double print, ruled in ADR-781's 2026-09-01 amendment §2. It was
the first option named there and it was unsafe before only because dropping the card rows would
have left the *stored* copy as the sole answer. Once the body renders from the resolver, both
halves of the output come from one `resolve_role_with_base` on one call, so they cannot disagree —
and printing one resolved value twice is still noise even when it cannot be wrong.

`--json` is a different reader with a different contract: `_role_json_payload` keeps `mission` and
`responsibilities` in its payload. Only the human card loses the rows.

The `RoleNotFoundError` card fallback is untouched here — the sibling stage-1 task already moved
it off `extra.full_name`. Do not widen the `except`; its narrowness is deliberate and documented
in place.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Key the no-active-item branch on the item, not the region

<!-- sq:subtask:ST3:body -->
`ServiceCore.role_body` (`_services/_base.py:1044`) returns `None` in two different situations —
no item exists for the slug, and the item exists but its `sq:body` region is absent — and
`sq role show` renders both as "(no active item for … — run `sq role activate …`)".

After the migration every role item carries a **present and empty** region, so today's shape is
one corpus change away from telling an operator that an active role does not exist. Keep the
markers (that is the migration's rule) and stop asking them a question about the item: `show_role`
already holds `it` before it renders anything, so the branch keys on `it is None`.

Belt and braces, both cheap and both worth having: the region's markers stay, and the branch no
longer depends on them.

`role_body` then has no caller in the show path. Either remove it with its last caller, or give it
a caller with a genuine reason to read raw stored text. Do not leave it as a dead read of a region
nothing fills — that is the shape that gets re-wired to something years later on the assumption it
still means something.

Test the case the corpus does not yet contain: an activated role whose `sq:body` region is present
and empty prints its definition; a slug with no item prints the activation hint. Both, in one run.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Stop writing the role extra mirror keys

<!-- sq:subtask:ST4:body -->
`RoleDef._EXTRA_FIELD_KEYS` (`_roles/_catalog.py`) loses `full_name`, `title`, `mission`,
`responsibilities`, `agreements`, `color` and `can_spawn`. `_RECONCILED_EXTRA_KEYS` loses
`description`. What survives is `slug`, plus `model` for a dev role only.

`model` is the one conditional: the key stays in `ExtraKey` because a dev role's model is
operator-settable through `sq dev add --model`, so the reconciler stops *writing* it for a non-dev
role. Express that as a condition, not by dropping the key from the vocabulary.

`is_default` leaves `_EXTRA_FIELD_KEYS` as well, and by this point it is tidying rather than a
fix — the sibling stage-1 task already ended the revert by putting the designation in the resolver
merge base, which is where it permanently belongs. It stays a stored key, written by
`sq role set-default` and by nothing else. Do not "restore" it to the key table on the grounds
that the resolved definition should carry it; the base is what makes the resolved definition carry
it.

`RoleDef.from_extra` retires here. It was left in place through stage 1 with no call sites
deliberately, so that stage could keep the mirror wholly intact and diff against it.

`_ITEM_FIELD_PROJECTION` is **unchanged**: `item.title` from `full_name`, `item.description` from
`mission`. Those are the uniform-record fields read by surfaces that cannot resolve a role
catalog, and removing them would break `sq list`, `sq tree`, the index and the VS Code client
while reopening the absence contract.

`activate_role`/`add_dev` (`_services/_roster.py:55`, `:86`) spread `role.to_extra()` into a
larger literal, so they should follow the narrowed table with no edit of their own. Verify that
rather than assuming it — a key one of them writes explicitly outside `to_extra()` would survive
the narrowing unnoticed.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-09-02T10:53:21Z] Elias Python:
  - Built. The role `extra` mirror is no longer written by any path.
    
    **What I cut.** `_EXTRA_FIELD_KEYS` (`_roles/_catalog.py`) is now `(slug,)`; a second table `_DEV_EXTRA_FIELD_KEYS` holds `model`, and `to_extra(*, is_dev=False)` writes it only when the caller says the item is a developer. `is_dev` is a parameter, not `slug.endswith("-dev")`: the marker lives on the item, and both callers already know which shape they are writing (`add_dev`, and the reconciler reading `extra.is_dev` back off the item). `_RECONCILED_EXTRA_KEYS` is gone with `description`, its only member.
    
    **The producer the ticket did not name, and it mattered.** `activate_role` and `add_dev` do *not* just spread `to_extra()` — both wrote `X.DESCRIPTION: role.description` explicitly in the create literal. Narrowing the table alone would have left `description` on every new role item. Removed from both. That is exactly the "verify rather than assume" this subtask asked for, and the answer was no.
    
    **The role body writer retired too.** `sq dev add --tech rust` was still storing a 54-line rendered definition; `_create_core` now empties the `sq:body` region for a role after rendering (the scaffold still has to render — `agents/role.md.j2` is both the file scaffold and the read-time definition, so it needs a complete `RoleDef` regardless — but its body is discarded). Markers kept, region empty: a removed region is what `show` reads as "no item for this slug".
    
    **What I deliberately left.**
    - `_ITEM_FIELD_PROJECTION` untouched: `item.title` from `full_name`, `item.description` from `mission`.
    - `is_dev`/`tech`/`is_default` still stored, written only by their own verbs.
    - The migration runner's frozen local copy (`_v0_11_to_v0_14.py`) still reads `extra` — the permitted exception.
    - `dev_base_from_item`'s bare `item.extra[X.MODEL]` subscript. Left loud on purpose: `model` is a *retained* key for a dev role, so a missing one is a corpus defect a sweep should not be able to cause silently. Flagging it rather than softening it.
    
    **One thing this ticket's own body has wrong.** "`RoleDef.from_extra` retires here. It was left in place through stage 1 with no call sites deliberately" — it had one: `resolve_role_for_item`'s orphaned-custom-role fallback (`_roles/_resolver.py`). That call site is why retiring it naively would have been a crash: after this change `extra[X.FULL_NAME]` is a `KeyError` on every role. Folded onto `from_extra_or_item`, which already takes the item's own `title`/`slug`/`description` as fallbacks and therefore reads *both* corpus vintages — mirror present and mirror absent — with no subscript. `_fallback_full_name` went with it.
    
    **A read-boundary defect found on the way.** `from_extra_or_item` documented "absent *or* blank, treated alike" and implemented `extra.get(k) or fallback` — a stored `"   "` is truthy, so it went straight through to `RoleDef.__post_init__`'s refusal. That is the v0.13.0 blank-name corpus, and the old `from_extra` did tolerate it. Fixed in `_or_fallback`, one place for every field, and the docstring now states what the code does.
    
    Driven, not asserted — fresh scratch squad, `init --roles core` + `dev add --tech rust` + `sync`: a bundled role's whole `extra` is `{slug: architect}`, a dev's is `{slug, model, is_dev, tech}`, every `sq:body` region present and empty, `sq check` clean. `.claude/` and `CLAUDE.md` byte-identical against the same drive on the pre-change tree, roster held constant. And the named failure driven end to end: hand-strip a legacy corpus to the post-sweep shape, `sq repair`, then `sq sync` — nothing comes back, including for a bundled role reduced to `{slug}` alone, with `sq role show` still rendering the full definition.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Narrow PERMITTED_EXTRA_SKEW, its pin, and the settable fields

<!-- sq:subtask:ST5:body -->
`PERMITTED_EXTRA_SKEW` (`_itemfile.py:66`) is `frozenset(RoleDef.extra_keys())` and narrows to
near-empty as the key table shrinks. The frozenset exists so a squad synced by a release predating
the reconciler's index mirror can converge on its next sync instead of being refused by the skew
guard; with almost nothing left in the mirror, there is almost nothing left to forgive.

`tests/unit/test_role_def_extra_keys.py` pins its membership as a literal, deliberately, to catch
an unreviewed **widening**. Narrowing is the safe direction. Update the literal in this same
change and say so in the test's docstring — naming what left and why — so the next reader can tell
a reviewed narrowing from an accident. Do not delete the pin because the set got small; a small
set is exactly when an accidental re-widening is easiest to miss.

The skew discriminator itself is **not** touched here — the sibling stage-1 task already moved it
off `extra.mission`, while that key still existed and could be compared against.

`_models/_metadata.py::_ROLE_FIELDS` narrows to the retained set. It declares what
`sq role <n> update --set` will accept for a role, and it currently advertises `full_name`,
`title`, `mission`, `responsibilities`, `color` — every one of which would write a value the next
sync deletes and nothing reads. The refusal for a removed key must name where the value is
declared now (`.overrides/roles.toml` for a catalog-document override,
`.overrides/roles/<slug>.toml` for a project-defined role) rather than reporting an unknown field
with no remedy: an operator reaching for `--set mission=` has a real intent and there is a real
place to satisfy it.

`GLOBAL_FIELDS` still carries `title` and `description`, so `sq role <n> update --title` keeps
working on the item's own top-level fields. Check that the narrowed extra table does not shadow or
confuse that path — the same word means two different things on a role item and the error messages
should not.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
- [2026-09-02T10:53:44Z] Elias Python:
  - Built. `PERMITTED_EXTRA_SKEW` is `{slug, model}`, its pin says so and why, and `_ROLE_FIELDS` matches.
    
    **The pin.** `tests/unit/test_role_def_extra_keys.py` keeps its literal (a small set is exactly when an accidental re-widening is easiest to miss) and its docstring now names what left and that narrowing is the safe direction. Added a positive clause beside it — `to_extra()` stores none of the eight definition keys, for a bundled role and a dev one — so the removal is guarded rather than merely absent. The two `description`-specific tests were re-pointed to assert its *absence*; `test_can_spawn_round_trips_through_extra_both_ways` was deleted, its subject having been removed (the field's values stay pinned by the other three tests in that file, and its surfacing by `test_can_spawn_surfaces.py`).
    
    **`_ROLE_FIELDS`** is now `(model, is_default, tech)`. The refusal for a removed key names where the value lives now, via `_refusal_hint`: `full_name` → the item's own `title` (`sq role activate --name` / `sq dev add --name`), the rest → `.overrides/roles.toml` or `.overrides/roles/<slug>.toml`. The role clauses are gated on `item_type == "role"` and come *before* the `GLOBAL_FIELDS` clause, for the reason this subtask flagged: `title` means two different things on a role item, and the old ordering would have sent an operator to `--title` (which sets the person's name) for a value that is now a catalog answer. A skill's own `title`/`description`/`model` still gets its own refusal with no role-override remedy in it — pinned by a test.
    
    **Same defect one document over.** `set_body`'s roster refusal named `sq update --set …` as the remedy, which after this narrowing would be a remedy that no longer applies. Split: a role now gets the override-document remedy, any other roster type a plain "generated, not authored".
    
    **The skew discriminator** was already off `extra.mission` (stage 1), as this subtask says — verified, not assumed.
    
    **What the narrowing broke, and it was mine.** `is_default` leaving the table means the role the *catalog* designates holds the designation with nothing stored at all. Four readers asked `extra.is_default` raw, so they stopped seeing it: `set_default_role`'s clearing loop (which then cleared nobody and left two live defaults — driven, `sq role list` showed `manager ✓` and `rust-dev ✓` at once), `sq check`'s duplicate-holder report, the retirement warning, and the lane exemption. All four now go through one seam, `holds_default_designation` (`_roles/_resolver.py`), which resolves and falls back to the stored key only when a broken override document makes resolution refuse — narrower reading, never wider, so it can only under-report. Clearing writes an explicit `False`, which is the only thing that can override a declared designation.
    
    Driven for both role shapes: `set-default` on a bundled role and on a dev role, each followed by `sync` → `repair` → `sync`, exactly one holder throughout and the compiled `CLAUDE.md` default-role line naming it; `sq check` clean. Falsified both new guards — restore the raw read and four tests redden; restore either mirror writer and five redden.
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-01T10:15:54Z] Elias Python:
  - Implemented ST1–ST3 only, per the explicit scope-discipline in my brief (stage two: producer inversion; the mirror-key removal this ticket's own body calls "Stage 3" — ST4/ST5 — is left for the separate follow-up task; not started here).
    
    **ST1 — producer inverted.** `role_definition_text(role: RoleDef) -> str` on `ServiceCore` (`_services/_base.py`) replaces `_regen_role_body`: renders `agents/role.md.j2` from the *resolved* `RoleDef` the caller already computed (no second resolution), extracts the `sq:body` section, returns it. `_regen_role_body`'s two callers are gone — the sync sweep (`_maintenance.py`) no longer calls it at all, and `_resync_role_skills` (the link-role/unlink-role partial hook) drops its body-refresh line entirely, now touching only the backend pointer. No code path writes a role's `sq:body` region any more.
    
    Template moved from `extra.get(...)`/`item.*` to `role.*` fields — text is otherwise byte-identical. Item creation (`activate_role`/`add_dev` → `_create_core`) still renders this same template to populate the initial body, now via `role=RoleDef.from_extra(item.extra)` — at creation time `item.extra` already *is* the resolved value, so this reproduces the same definition with no behaviour change and no second resolution path.
    
    **ST2 — card drops mission/responsibilities.** `sq role <slug> show`'s card now shows: name/slug, title, model, can spawn, creates, skills. Mission and responsibilities print once, in the rendered definition below the card (`--json` unchanged, keeps every field).
    
    **ST3 — no-active-item branch keyed on the item.** `role_body` is deleted (no caller left in the show path). `show_role` keys the branch on `it is not None and r is not None` → render the definition; `it is None` → the activation hint; `it is not None` but resolution failed (e.g. a broken override) → a distinct "could not be resolved, run `sq check`" note (a case the old raw-file read used to paper over silently). Verified live: an activated role whose region I hand-corrupted keeps the corruption after `sq sync` (region genuinely untouched) while `show` renders the correct definition regardless; an unactivated dev slug still gets the activation hint, not a preview definition — this last one needed a real fix mid-task: my first pass keyed the branch on `r is not None` alone, which showed the full definition for *any* resolvable slug including a never-activated one (caught by `test_role_show_of_a_bundled_but_inactive_role_offers_an_activation_hint`, still green).
    
    **Negative clause holds.** `RoleDef.to_extra()`, `_EXTRA_FIELD_KEYS`, `_RECONCILED_EXTRA_KEYS`, `PERMITTED_EXTRA_SKEW` and its pin, `_ROLE_FIELDS` — all untouched (`git diff` shows zero lines in `_roles/_catalog.py`; `_itemfile.py` has an unrelated concurrent edit, not mine, and doesn't touch the skew set). The mirror is still fully written — a freshly activated role's file still carries every current key.
    
    **Bundled template touched → manifest regenerated** (`gen_template_manifest.py`): only the 0.14.0 entry for `agents/role.md.j2` moved (one hash line), one new blob inserted into the content store. That leaves the old blob orphaned in the store, which is the known `test_override_manifest_and_stamp_freshness.py` failure family (5 tests) per the rules — not run through `seed_content_store.py --rebuild` myself; that residue is explicitly the coordinator's to clear.
    
    **Managed-file diff, roster held constant.** Built two fresh scratch squads (default 8-role roster + one python-dev) — one on this branch's pre-task commit, one on my working tree — ran `sq init` + `sq dev add` + `sq sync` identically on both, `diff -rq .claude` and `diff CLAUDE.md`: both exit 0, byte-identical. Also drove: override added with no sync → `sq role <slug> show` picks it up on the very next command; present-and-empty region (simulating the future corpus migration) → renders the definition, not the hint.
    
    **Fallout in tests** (behaviour that only existed because sync used to rewrite the body — updated, not silenced): `test_sync_regenerates_a_corrupted_role_body_in_place` → rewritten as `test_sync_no_longer_touches_a_corrupted_role_body` (asserts sync leaves the corruption in place, `show` renders correctly anyway); the two mission-body tests in `test_role_projects_resolved_name_and_mission_onto_item_fields.py` now resolve the definition directly instead of reading a post-sync stored body; `test_skill_role_scope_link_unlink_hook.py`'s "and body" assertions/docstring dropped (the hook never touched body content in a way skill-linking could affect in the first place — the definition never carried the skills list); two CLI tests asserted literal `"mission:"` in `show` output as a proxy for "got the full card, not the fallback" — swapped for `"skills:"`/`"## Mission"` respectively, matching what the card now carries.
    
    Gates: `pyright`/`ruff check`/`ruff format --check` clean (repo-wide, ignoring one pre-existing E501 in `_v0_11_to_v0_14.py` from a concurrent in-flight edit in this tree — not mine, not in my file list). `tests/meta`: 261 passed, 5 failed — the known orphan-content-store family named above, same shape whether or not I touch a template. Targeted (every file I touched, 248 tests): all pass. `sq check`: clean.
    
    Left undone (deliberately, per scope): ST4 (drop full_name/title/mission/responsibilities/agreements/color/can_spawn from `_EXTRA_FIELD_KEYS`, description from `_RECONCILED_EXTRA_KEYS`, model conditional-for-dev-only) and ST5 (narrow `PERMITTED_EXTRA_SKEW` + its pin + `_ROLE_FIELDS`) — both still exactly as this ticket's own body specifies, for whoever picks up the follow-up.
    
    @tech-lead ready for review.
- [2026-09-01T10:17:35Z] Catherine Manager:
  - Integrated: read the diff rather than the handoff. The template substitution is clean, the description-over-mission precedence drop is the documented reconcile-not-preserve semantics, and the assert matches the narrowing-assert convention already in _base/_refs.
  - Test changes re-point rather than soften: the corrupted-body test now asserts sync leaves it alone AND show still renders correctly, which is strictly stronger than the heal-in-place assertion it replaced.
  - Content-store orphan (the pre-edit role.md.j2 blob) is mine to clear, not the task's — rebuilding once after the narration sweep stops touching bundled templates.
- [2026-09-01T10:23:37Z] Catherine Manager:
  - Full suite caught two failures the targeted runs did not reach: test_mine_excludes_a_roster_category_item_matching_workloads_own_guard and test_every_builtin_type_template_renders_the_required_markers_and_heading[role].
  - One defect: agents/role.md.j2 went from total (degraded to item.title) to requiring a resolved RoleDef, and _create_core builds one unconditionally for ROSTER_ROLE. svc.create('role', ...) with empty extra raises a bare KeyError from _catalog.py rather than a SquadsError. No sq create role CLI verb exists, so this is service-layer only.
  - Sent back to the same dev to decide total-vs-strict rather than patch, with the tests held as written. Status stays InReview.
- [2026-09-01T10:30:22Z] Elias Python:
  - Fixed a real gap the full suite caught that my targeted runs didn't reach: `_create_core` built `RoleDef.from_extra(item.extra)` unconditionally for ROSTER_ROLE, and `Service.create('role', ...)` is a legitimate, reachable service-layer call with no CLI verb gating it — `from_extra`'s bare `extra[X.FULL_NAME]`/`extra[X.SLUG]` subscripts raised a bare `KeyError` when called with no/partial `extra` (as `test_mine_excludes_a_roster_category_item_matching_workloads_own_guard` does deliberately). Same root cause broke the generic cross-type template smoke test for `[role]` under `StrictUndefined`.
    
    **Decision: strict, not total.** `agents/role.md.j2` keeps requiring `role.<field>` unconditionally — no Jinja-level degradation reintroduced. Every caller now guarantees a genuinely non-`None`, fully-populated `RoleDef`:
    - `role_definition_text`'s caller (`show_role`) already did — resolves via `resolve_role_with_base`, unchanged.
    - `_create_core` now builds one via a new `RoleDef.from_extra_or_item(extra, *, title, slug, description)` (`_roles/_catalog.py`) instead of `from_extra` — falls back field-by-field to the item's own `title`/`slug`/`description` exactly as the pre-inversion template's inline `extra.get(key, item.title)` calls did, so it never raises for any well-formed `Item` (title/slug are required non-blank fields). If a title were ever whitespace-only, `RoleDef.__post_init__`'s existing blank-`full_name` refusal fires — already a clean `SquadsError`, never a `KeyError`. Corrected the comment that asserted the old (false) premise.
    - The generic template-render test (`test_item_and_subentity_templates_render_structurally.py`) now passes a `role=` kwarg (built the same way) only for the `[role]` case — every other built-in type's render call is untouched.
    
    Not weakened: both flagged tests pass unmodified in their assertions — `test_mine_excludes...` still creates the role with empty `extra` and still asserts success + the `mine()` exclusion; `test_every_builtin_type...` still asserts the same markers for every type including `role`.
    
    Full suite: `uv run --all-extras pytest` — 4352 passed, 7 skipped, 0 failed. `tests/meta`: 266 passed (matches your rebuilt-content-store baseline). `sq check`: clean.
- [2026-09-01T10:36:15Z] Elias Python:
  - Precision fix on `from_extra_or_item`: `title=extra.get(X.TITLE, "")` didn't fall back to the item's own `title` the way the pre-inversion template's `extra.get('title', item.title)` did — on the one path this method exists to serve (a role item with no stored `extra.title`), the card's `**Role:**` line would have rendered blank instead of the item's title.
    
    Took the suggested fix: `title=extra.get(X.TITLE, "") or title` — consistent with how every other optional field in the same method already degrades (`.get(key, "") or fallback`), so the contract stays one shape across all five fallback fields rather than carving out an exception.
    
    Tightened the docstring to state what the code now actually does, precisely: falls back on absent *or* blank (not only a missing key, which is a slightly broader trigger than the old template's bare `.get(key, default)` — the same missing-or-blank pair `from_extra` already treats alike for `full_name`), rather than claiming an "exact" match to the old per-field Jinja calls that wasn't quite true.
    
    `pyright`/`ruff check`/`ruff format --check` clean. Full suite (`uv run --all-extras pytest`, once, to a file): 4352 passed, 7 skipped, 0 failed. `sq check`: clean.
- [2026-09-02T09:08:13Z] Catherine Manager:
  - Accepted InReview->Done on my own verification rather than an independent review, and recording why: this task blocks the corpus strip, and the strip's dedicated review cannot both cover this and be gated by it.
  - What I actually verified: read the full diff, ran the authoritative suite (green at each landing), confirmed the managed-file byte-identity evidence, and drove the degradation cases. The strip's review will still see this code as the ground it stands on.
- [2026-09-02T10:03:22Z] Catherine Manager:
  - Reopened Done->InProgress. I moved this to Done with ST4 and ST5 still at Todo, to unblock the corpus strip. That was the same error the capstone task was reopened for earlier in this release, and this time it was mine rather than an agent's.
  - It also bought nothing: the strip's role half is now Blocked on exactly the stage I waved through. Driven by the strip's implementer — empty a role body, strip all ten mirror keys, sq repair, then sq sync, and _refresh_catalog_extra writes every key back. That is the decision record's named failure verbatim: strip on repair, restore on sync.
  - Not amending the acceptance. ST4 and ST5 are the work; they get built.
- [2026-09-02T10:55:49Z] Elias Python:
  - ST4 and ST5 built; stage 3 is done and the corpus strip's role half is unblocked. Detail on each subtask's own discussion; the cross-cutting points are here.
    
    - **Nothing writes the mirror or the role body.** `to_extra()` is `{slug}` (+ `model` for a developer), `activate_role`/`add_dev` no longer write `description` explicitly, and `_create_core` empties a role's `sq:body` region. Driven on a fresh squad and on a hand-stripped legacy corpus: `sq repair` then `sq sync` restores none of the ten names, for a bundled role, a dev role, and a bundled role reduced to `{slug}` alone.
    - **Two corrections to this ticket's own body.** `RoleDef.from_extra` was *not* call-site-free — `resolve_role_for_item`'s orphaned-role fallback used it, and retiring it naively would have made every post-change role item a `KeyError` at that boundary. And `activate_role`/`add_dev` did *not* follow the narrowed table with no edit: both wrote `extra.description` outside `to_extra()`.
    - **A regression I introduced and closed.** `is_default` leaving the table means the catalog's designated role holds the designation with nothing stored, and four raw `extra.is_default` readers stopped seeing it — `set_default_role` cleared nobody and left two live defaults. All four now go through one resolved seam. Driven across `sync` and `repair` for a bundled role and a dev role: exactly one holder, the compiled default-role line naming it, `sq check` clean.
    - **For the strip's role half (`sq task 849`), one line to change with it.** `_sweep_empties_body`'s docstring still says "A role's body is not emptied here. Its writer has not retired — activating a role still renders the definition into the region." That writer has now retired, so the sentence is false as of this change. It sits in the strip's own uncommitted work, which I left alone.
    
    Gates on the final tree: `uv run --all-extras pytest` → **4486 passed, 8 skipped in 73.53s** (baseline 4471/8; +16 new, −1 removed for behaviour that no longer exists). `pyright` 0 errors, `ruff check`/`format --check` clean, `sq check` clean. One data file regenerated the sanctioned way: `tests/goldens/list.json` (`UPDATE_GOLDENS=1`), diff is one role's `extra` shrinking to `{slug}` and nothing else. No bundled template or spec touched, so no manifest regeneration is owed.
    
    @tech-lead ready for review.
<!-- sq:discussion:end -->
