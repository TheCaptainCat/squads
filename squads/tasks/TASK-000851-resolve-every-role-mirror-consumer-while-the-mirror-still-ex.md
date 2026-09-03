---
id: TASK-851
sequence_id: 851
type: task
title: Resolve every role-mirror consumer while the mirror still exists
status: Done
parent: FEAT-694
author: tech-lead
priority: high
refs:
- ADR-776:implements
- TASK-848:depends-on
- BUG-850:fixes
description: 'Every consumer of the role extra mirror resolves through the role catalog
  while the mirror is still written: separately shippable, no corpus change, no migration'
subentities:
- local_id: ST1
  title: Resolve roster and roster_all through the role resolver
  status: Done
- local_id: ST2
  title: Carry the operator-settable set in the resolver merge base
  status: Done
- local_id: ST3
  title: Resolve the four from_extra consumers
  status: Done
- local_id: ST4
  title: Move the skew discriminator off extra.mission
  status: Done
- local_id: ST5
  title: Resolve the remaining role-mirror readers
  status: Done
- local_id: ST6
  title: Prove the managed-file diff is zero, roster held constant
  status: Done
- local_id: ST7
  title: Resolve the authoring-owner title through the live roster
  status: Done
created_at: '2026-09-01T08:23:20Z'
updated_at: '2026-09-01T12:13:50Z'
---
<!-- sq:body -->
## Scope

**Stage 1 of ADR-776's second 2026-09-01 amendment §3, and only stage 1.** Every consumer of the
role `extra` mirror resolves through the role catalog instead — **while the mirror is still
written**. Nothing stops being stored here, no template changes, no migration, no corpus change.

This is deliberately a separately shippable increment, not a preparatory step. On its own it ends
the `sq role set-default` revert and the pre-sync disagreement between a role's computed card and
its stored body, both of which are live defects today. It can be finished, handed back and
committed with the two later stages not started.

Stage 2 (the producers invert) and stage 3 (stop writing, then strip) are the sibling tasks. Do
not reach into them: **removing a key here breaks the stage's own falsifiable property**, which
depends on the mirror still being present to diff against.

## The falsifiable property, and it is the whole acceptance

Hold the roster constant. Regenerate every managed file — the compiled `CLAUDE.md` and `AGENTS.md`
regions, every `.claude/` pointer, every generated skill — before the change and after it. **Diff
to zero.**

The one permitted class of difference is where the mirror was already wrong: a project override
the stored copy had not caught up with, or a designation the reconciler had reverted. That is
where the fix shows. A difference anywhere else is a regression, and the direction of the diff is
what tells them apart — so capture both sides rather than asserting "no diff" and moving on.

Generated skill text is roster-dependent through the `has_dev` gate, so a comparison against a
differently-rostered squad is a false positive. Hold the roster constant, on both sides.

## The substitution, per site

`resolve_role_with_base(slug, squad_dir, base=role_base_from_item(item, squad_dir))` is the one
seam. Every site below either goes through it, or reads a value the uniform record already
carries (`item.title`, `item.description`).

**1. `roster()` and `roster_all()` (`_services/_base.py:1089`, `:1110`) — the highest-consequence
site, and the one that degrades without raising.** Every `RoleView` is built off the mirror, and
that view is what `write_managed` compiles `CLAUDE.md`, `AGENTS.md` and every pointer from — the
files ADR-776 §5 deliberately keeps materialised. The per-field fallbacks decide the failure mode,
and the architect's table is the thing to read before touching this:

| `RoleView` field | fallback when the key is gone | outcome |
| --- | --- | --- |
| `full_name` | `it.title` | correct — `title` carries the resolved full name |
| `mission` | `it.description` | correct — `description` carries the resolved mission |
| `is_default` | key retained | correct |
| `title` (the role title) | `it.title` | **wrong, silently** — the role's title becomes the person's name |
| `responsibilities` | `()` | **empty, silently** |

The degradation set is exactly the two fields with no uniform-record home. Nothing raises; the
damage lands in generated agent configuration.

**2. `role_base_from_item` (`_roles/_resolver.py:364`) and `dev_base_from_item` (`:335`).** Both
take the operator-settable name from `item.title` rather than `extra.full_name`. The dev one reads
`item.extra[X.FULL_NAME]` as a **bare subscript** (`:355`) — it raises rather than degrading,
which makes it the cheap failure and the easy one to miss precisely because it is loud.

The merge base also gains `is_default`, and that is not optional once site 1 resolves — see the
next section.

**3. The four `RoleDef.from_extra` sites.** `_services/_validators.py:761` (`sq check`'s
pointer-currency expectation — ADR-781 §2c's guarantee is void if this keeps reading the mirror),
`_services/_base.py:1403`, `:1454`, and `_services/_items.py:481`. `from_extra` itself is **not**
deleted here; it is the mirror's reader and retires with the mirror, in stage 3.

**4. `_without_permitted_extra_skew`'s discriminator (`_itemfile.py:132`).** It identifies a role
by `extra.mission`. Moving it now, while that key still exists, is what makes it *testable*: the
new discriminator can be asserted to give the same answer as the old one over the same corpus, a
stronger test than anything available after the key is gone.

**5. The remaining readers.** `sq role list` (`_cli/_role.py`, table and `--json`),
`ServiceCore._author_of` (`_services/_base.py:1059`, whose role branch takes `item.title` while
its operator branch keeps `extra.full_name`), and `show`'s two `RoleNotFoundError` fallbacks.

**Not in scope, and named so it is not helpfully added:** the migration runner's frozen local copy
of this projection (`_migrations/_v0_11_to_v0_14.py:136-176`) **must not** be taught to resolve.
Its own docstring records why it is local — `_services` imports the migration registry, so calling
`Service` from a runner is a real cycle — and a runner is frozen against the corpus vocabulary of
the version it transforms, which still carries the mirror. Leave it reading `extra`.

## `is_default` becomes a required member of the merge base

`role_base_from_item`'s docstring already states the rule it is meant to hold: "The item is
authoritative for exactly the fields an operator can set on it through the CLI, and for no
others." `is_default` **is** operator-settable, through `sq role set-default`
(`_services/_roster.py:154-215`), and it is missing from that set — the base carries only
`full_name`. That omission is the defect, not the key table.

Two things follow, and both are this stage's:

- **The revert ends.** `_refresh_catalog_extra` (`_services/_maintenance.py:886-900`) writes back
  `resolve_role_with_base(...).to_extra()`. With the item's designation in the base, the resolved
  value *is* the operator's value, so the write-back is a no-op instead of a reversion. No key
  leaves any table to achieve this.
- **It is load-bearing for site 1, immediately.** Once `roster()` resolves rather than reading
  `extra`, `RoleView.is_default` comes from the resolved definition. If the base does not carry
  the designation, the compiled managed region's default-role line reverts to the catalog's answer
  at render time — a fresh instance of the same defect, introduced by the fix for it. The carry is
  permanent: it stays after stage 3 removes the mirror, because it is then the only path the
  value has.

## Cost

Resolution is per role and reads the override TOML per call; the roster sweep does ten in this
repository. If that profiles as a real cost, resolve once per sweep and thread the result through.
Never by reintroducing a stored copy.

## Acceptance

- With the roster held constant, every managed file — both compiled regions, every `.claude/`
  pointer, every generated skill body — is byte-identical before and after, **except** where the
  mirror was already stale or reverted. Both sides captured, the differences enumerated and each
  one attributed to a specific pre-existing wrongness.
- A project override declared in `.overrides/roles.toml` reaches the compiled managed regions and
  the pointers on the next regeneration, with no `sq sync` having healed the mirror first.
- `sq role qa set-default` survives `sq sync`: the designation holds, no other role holds it, and
  the compiled default-role line names the designated role. Proven at the behaviour level.
- No `RoleView` field is read off `extra` any more; `roster()`/`roster_all()` resolve, and a test
  asserts the role *title* and *responsibilities* specifically — the two silent-degradation fields.
- `dev_base_from_item` and `role_base_from_item` take the name from `item.title`; a role item with
  no `extra.full_name` at all resolves correctly through both rather than raising.
- `sq check` reports a drifted role pointer as drifted and a current one as current, with the
  expectation resolved — proven on a squad carrying a project override the mirror disagrees with.
- `_without_permitted_extra_skew` grants a non-dev role its exemption without reading
  `extra.mission`, and gives the same answer as the old discriminator over a corpus that still
  carries the key.
- **The mirror is still written.** `RoleDef.to_extra()`, `_EXTRA_FIELD_KEYS`,
  `PERMITTED_EXTRA_SKEW` and its pinned test are unchanged by this task; every role file still
  carries every key it carries today; no template changes; no migration; the corpus is untouched.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite are clean. `sq check` is clean on this repository.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 851 add-subtask "<title>"`; track with `sq task 851 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Resolve roster and roster_all through the role resolver

<!-- sq:subtask:ST1:body -->
`roster()` (`_services/_base.py:1089`) and `roster_all()` (`:1110`) build every `RoleView` from
`item.extra` — `full_name`, `title`, `is_default`, `mission`, `responsibilities`. Both resolve
instead, through
`resolve_role_with_base(slug, squad_dir, base=role_base_from_item(item, squad_dir))`.

**This is the highest-consequence site in the stage, and the reason is the failure mode rather
than the blast radius.** The view is what `write_managed` compiles `CLAUDE.md`, `AGENTS.md` and
every `.claude/` pointer from — files ADR-776 §5 deliberately keeps materialised, read by an agent
host before any agent exists to notice. It is not a `from_extra` call, so a grep for the obvious
pattern misses it. And it does not raise: three of the five fields survive on their fallbacks
because `title`/`description` carry the resolved values, while the role *title* silently becomes
the person's name and `responsibilities` silently empties. The degradation set is exactly the two
fields with no uniform-record home.

`is_default` must come through the merge base once this resolves — see the sibling subtask. Left
unaddressed, `RoleView.is_default` starts answering from the catalog and the compiled default-role
line reverts at render time: the same defect this work fixes, reintroduced by its own fix.

`roster()` filters to live statuses and `roster_all()` does not; that split is untouched. So is
every caller — this changes where the values come from, not the shape of what is returned.

Resolution is per role and reads the override TOML per call; ten roles in this repository. If that
profiles as a real cost, resolve once per sweep and thread the result. Never by reintroducing a
stored copy.

Test the two silent fields by name, not the record as a whole: a role whose catalog title differs
from its full name, and a role with a non-empty responsibilities list, both asserted through a
regenerated managed file rather than through the view object.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Carry the operator-settable set in the resolver merge base

<!-- sq:subtask:ST2:body -->
`role_base_from_item` (`_roles/_resolver.py:364`) states the rule it exists to hold: "The item is
authoritative for exactly the fields an operator can set on it through the CLI, and for no
others." Today it carries `full_name` alone for a bundled role, and delegates to
`dev_base_from_item` (`:335`) for a dev role.

Two changes, both to the operator-settable set rather than to any key table:

**The name comes from `item.title`.** Both functions take it from `extra.full_name` today, and
`dev_base_from_item` does it as a **bare subscript** (`item.extra[X.FULL_NAME]`, `:355`), so it
raises rather than degrading. Keep the existing tolerance at both: a blank or whitespace-only
stored name is treated as absent and falls back, because a read boundary must tolerate a value an
earlier release wrote and called healthy.

**`is_default` joins the set.** It is operator-settable through `sq role set-default`
(`_services/_roster.py:154-215`) and it is missing from the base — which is the whole of the
revert defect. `_refresh_catalog_extra` (`_services/_maintenance.py:886-900`) writes back
`resolve_role_with_base(...).to_extra()`; with the designation in the base the resolved value is
the operator's, so the write-back is a no-op instead of a reversion. Nothing leaves a key table to
achieve this, and the mirror stays written.

The carry is **permanent**, not a stepping stone. Once the roster resolves, the designation has no
other path to the compiled default-role line, and after the mirror is removed entirely it has no
other path at all.

Falsify both halves: drop the `is_default` carry, watch a designation-survives-sync test go red;
put the bare subscript back, watch a role item with no `extra.full_name` raise. Restore, watch
both go green, and report both.

This is the subtask that closes BUG-850. The bug does not wait on the later stages.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Resolve the four from_extra consumers

<!-- sq:subtask:ST3:body -->
The four `RoleDef.from_extra(item.extra)` call sites resolve instead, through
`resolve_role_with_base(slug, squad_dir, base=role_base_from_item(item, squad_dir))`:

- **`_services/_validators.py:761`** — `sq check`'s pointer-currency expectation. It renders what
  the pointer *should* say and compares it against the file on disk. Built from the mirror, that
  expectation is only ever as fresh as the last sync, so a pointer that genuinely drifted from a
  project override reads as current. ADR-781 §2c's currency guarantee is void until this resolves,
  which makes it the site with the most reach beyond this feature.
- **`_services/_base.py:1403` and `:1454`** — two of the three `generate_role_entry` calls in the
  roster projection path.
- **`_services/_items.py:481`** — the third.

`RoleDef.from_extra` itself is **not** deleted here. It is the mirror's reader and it retires with
the mirror, in the sibling stage-3 task. Leaving it in place with no call sites for the length of
one stage is deliberate: this stage's property is that the mirror is still fully present and still
fully written, so nothing about it changes.

The validator carries a documented precondition worth preserving: `role_skills` must already hold
the freshly resolved preload-skill list, because the pure system-membership fallback does not know
about `scopes`-preloaded skills. Resolving the `RoleDef` does not resolve that map; do not conflate
them.

Prove the validator at the behaviour level, on a squad carrying a project override the stored
mirror disagrees with: a genuinely drifted pointer reports drifted, and a genuinely current one
reports current. Both directions — a check that reports everything as drifted passes the first
half of that test.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Move the skew discriminator off extra.mission

<!-- sq:subtask:ST4:body -->
`_without_permitted_extra_skew` (`_itemfile.py:93-140`) decides which `extra` keys are exempt from
the frontmatter/index skew guard for a given item, and it identifies a role by `extra.mission` —
documented at `:132` and argued for at length above it as "the one key only a role's own
`RoleDef.to_extra()` merge ever writes".

Move it to a key the shrink retains: `extra.slug` on a role item, or the item's own type.

**Moving it in this stage rather than the one that removes the key is what makes it testable.**
While `extra.mission` is still written, the new discriminator can be asserted to give the *same
answer as the old one* over the same corpus — every role, dev and non-dev, plus the negative
cases. After the key is gone there is nothing left to compare against, and the test degrades to
asserting the new behaviour against itself.

Rewrite the paragraph that justified the old choice rather than appending a correction beneath it.
It argues specifically about why `extra.mission` is safer than resolving the slug against the
bundled catalog, and that argument does not survive the key.

Three properties the replacement must keep, each currently load-bearing and each with its own
reason in the docstring:

- a **dev** role gets none of `RoleDef.extra_keys()` — only the narrower exemption that applies to
  it — because every other field on a dev role is an ordinary transaction-guarded field, and
  widening reopens a real loss class;
- any **other** role gets the whole permitted set, deliberately widened to "any non-dev role"
  rather than narrowed to "any bundled-slug role", because this module has no `squad_dir` with
  which to replicate the resolver's override handling;
- **anything else** gets none of it, so a coincidental key-name collision with another item type's
  own `extra` (a skill item's own `model`) is never this exemption's business.

`PERMITTED_EXTRA_SKEW` and its literal pin (`tests/unit/test_role_def_extra_keys.py`) are **not**
touched here. They narrow when the keys leave `to_extra()`, in the sibling stage-3 task; this
stage leaves the frozenset exactly as it is.

Falsify it: break the discriminator, watch a non-dev role's skew exemption test go red, restore
it, watch it go green — and report both.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Resolve the remaining role-mirror readers

<!-- sq:subtask:ST5:body -->
The readers left after the roster, the merge base, the `from_extra` sites and the skew
discriminator:

- **`sq role list`** (`_cli/_role.py`) reads `extra.full_name` and `extra.title` for both the
  table and its `--json` payload. Resolve, so the list agrees with `sq role <slug> show` — today
  they can disagree, because `show` already resolves on its main branch and `list` does not.
- **`ServiceCore._author_of`** (`_services/_base.py:1059`) resolves a display name from
  `extra.full_name`, in one lookup serving role **and** operator items. Operator items keep the
  key and are out of scope entirely; only the role branch changes, and `item.title` is the value
  it wants. Resolving through the catalog here would be wrong as well as expensive: this is a
  display name on a comment attribution, and `item.title` already carries it.
- **The two `RoleNotFoundError` fallbacks** in `show` — the card
  (`_cli/_role.py`, the `rows = [...]` in the `except` arm) and `_role_json_payload`'s. This
  branch exists for a slug with no bundled entry, no dev base and no override file, which is
  exactly the case where nothing can be resolved. Rebuild it from `item.title`,
  `item.description`, `item.status` and the retained `extra` keys. **Do not widen the `except`** —
  its narrowness is deliberate and documented in place: a broader catch swallowed an *invalid*
  project override, so the refusal disappeared and the card rendered from the stored item as
  though the broken override were not there.

`_role_json_payload`'s main branch already resolves and is unchanged; its payload keeps every
field it returns today.

Sweep for stragglers rather than trusting this list: after the change, a repository-wide search
for reads of the mirror keys against a role item should return only the migration runner's frozen
local copy, which stays as it is. Assert that as a test, not as a one-off grep in a handoff note.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Prove the managed-file diff is zero, roster held constant

<!-- sq:subtask:ST6:body -->
The stage's falsifiable property, made into a test rather than a procedure someone remembers to
follow.

Hold the roster constant. Regenerate every managed file on both sides — the compiled `CLAUDE.md`
and `AGENTS.md` regions, every `.claude/` pointer, every generated skill body — and diff.

**Expect zero, except where the mirror was already wrong.** That exception is not a loophole: it
is where the fix shows, and it is the only thing distinguishing this change from a no-op. So
capture both sides rather than asserting emptiness — enumerate each difference and attribute it to
a specific pre-existing wrongness (a project override the stored copy had not caught up with, a
designation the reconciler had reverted). A difference nobody can attribute is a regression.

Construct the wrongness deliberately rather than hoping the corpus supplies it: a squad with
`.overrides/roles.toml` redeclaring a role's `title` and `responsibilities`, synced *before* the
override was added, so the stored mirror and the resolver genuinely disagree. Before the change
the regenerated files carry the stale text; after it they carry the override. That is the
assertion that proves the substitution reached the materialised surfaces, and it is the one a
"diff to zero" test alone would let pass while silently proving nothing.

**Hold the roster constant on both sides.** Generated skill text is roster-dependent through the
`has_dev` gate, so comparing a dev-bearing squad against a dev-less one produces a confident false
positive — the failure mode here is a regression report against code that is correct.

Also assert the negative for the stage as a whole, because the stage is defined as much by what it
does not do: every role file still carries every `extra` key it carries today,
`RoleDef.to_extra()` and `_EXTRA_FIELD_KEYS` are unchanged, `PERMITTED_EXTRA_SKEW` and its literal
pin are unchanged, no bundled template changed, and the corpus is byte-identical. A test that
fails if a later stage's work is pulled forward into this one is worth more here than in most
places, because the stage's shippability depends on it.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Resolve the authoring-owner title through the live roster

<!-- sq:subtask:ST7:body -->
The one role-mirror consumer the stage missed, and the reason acceptance clause 2 is breached on
the exact surface it names.

## The defect, driven

With `squads/.overrides/roles.toml` carrying:

```toml
[roles.reviewer]
title = "OVERRIDE-TITLE"
```

a fresh `init` + `sq role activate reviewer` + `sq sync` renders `CLAUDE.md` line 17 as
`OVERRIDE-TITLE` and line 107 as `code reviewer`. `squads:start` is line 3 and `squads:end` is
line 123, so **both disagreeing lines sit inside the same compiled managed region** — the file
contradicts itself about one role's title.

## The mechanism

`_interactions/__init__.py`'s `authoring_owner` resolves the display title with
`role_by_slug(slug).title`. `role_by_slug` takes no `squad_dir`: it is a bundled `_BY_SLUG`
lookup and cannot see a project override. The live resolved titles are threaded in as
`role_titles` but are consulted **only** inside the `RoleNotFoundError` branch — so a role that
*is* in the bundled catalog, which is every role an override is most likely to retitle, never
reaches them.

Line 17 is correct because the roster section renders `r.title` off the `RoleView` this stage
already moved onto the resolver. Line 107 is the authoring bullet, which goes through
`authoring_owner`. Two renderings of one value, one resolved and one not.

Two callers render from the same function, and both are in scope:

- `_rendering/templates/claude/claude_section.md.j2` — the compiled `CLAUDE.md`/`AGENTS.md`
  managed region, passing `_role_titles` built from the live roster views;
- `_rendering/templates/workflow.md.j2` — the workflow cheatsheet, shared by the generated
  `squads` skill body and `sq workflow`, passing `role_titles` built the same way.

## The fix

Consult the live `role_titles` map **first** when it carries the slug, and fall back to the
bundled catalog, then to the existing `RoleNotFoundError` path. `role_titles` is already threaded
to both call sites and already carries the resolved title, so this is an ordering change inside
one function — not new plumbing, and not a `squad_dir` parameter on `role_by_slug`.

**The docstring's stated reason for catalog-first does not survive checking, and correcting it is
part of this subtask.** It claims the catalog stays first because "its titles are the lower-case
sentence forms this prose is written around, while a live roster entry carries the display-cased
form". A roster entry's `title` is the role title, not the person's name — the display-cased form
is `full_name`, a different field. This repository's own generated `CLAUDE.md` is the standing
proof: with no override in play, the roster line and the authoring bullet both read `code
reviewer`. Verify that on a no-override squad before and after, then rewrite the paragraph to say
what the ordering actually does.

A caller that passes no `role_titles` at all (the bundled reference render) keeps today's
behaviour exactly.

## Done when

- With a project override retitling a bundled role, **every** line of the compiled managed region
  that names that role's title carries the override — proven by asserting the region contains no
  occurrence of the bundled title for that slug, not by checking the two known line numbers.
- The generated `squads` skill body and `sq workflow` carry the override too.
- A role declared **only** in `.overrides/roles/<slug>.toml`, with no bundled catalog entry, still
  gets its authoring bullet — the existing `RoleNotFoundError` path is not regressed by the
  reordering.
- A caller passing no `role_titles` is unchanged.
- On a squad with no override, the compiled region is byte-identical before and after, roster held
  constant.
- `authoring_owner`'s docstring states the real ordering rule; the "display-cased form" claim is
  gone.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
- [2026-09-01T11:47:22Z] Elias Python:
  - Fixed, driven both ways.
    
    **The fix — caller-side ordering inside `authoring_owner`, no signature change anywhere.** `role_titles` (the live slug->title map, already threaded to both renderers) is now consulted **first**; the bundled `role_by_slug` catalog is the fallback for a caller that threads no roster (a bundled reference render); the `RoleNotFoundError` arm past it returns `None` as before. I did not add a `squad_dir` to `role_by_slug`: the resolved value was already in hand at the call site, so plumbing a second resolution path would have been redundant work for the same answer — and `_interactions` cannot reach the resolver-backed roster itself without inverting the `_interactions` -> `_rendering/_engine` import edge.
    
    **Docstring corrected**, per the subtask. The "a live roster entry carries the display-cased form" claim was false — a `RoleView.title` is the role title in the catalog's own casing; the display-cased value is `full_name`, which this function never reads. Replaced with what the ordering actually does and why the two sources agree on a no-override squad.
    
    **Falsification** (durability-class, both directions): swapped the pre-change `__init__.py` back in -> 3 of the 4 new tests red (compiled region, generated `squads` skill body, `sq workflow`); restored -> all 4 green. The fourth test (a role declared only in `.overrides/roles/<slug>.toml`, put in a lane by a playbook override, still gets its bullet) passes on **both** sides — that is its job, it is the no-regression control for the old `RoleNotFoundError` path.
    
    **Driven proof, before and after:** the reported repro renders line 17 `OVERRIDE-TITLE` and line 107 `code reviewer` before; after, both read `OVERRIDE-TITLE` and the bundled title occurs **zero** times in the whole file. The cheatsheet half (not in the reported repro) is fixed too: `sq workflow` and the generated `squads` skill body both carry the override.
    
    **No-override render is byte-identical.** Two full `init` + `role activate` + `sync` runs, roster held constant, one on the pre-change tree and one on the fixed tree, diffed recursively with only timestamps normalised: zero differences across `CLAUDE.md`, `AGENTS.md`, all eight `.claude/` pointers, every generated skill and every role body.
    
    **Test added:** `tests/integration/test_an_overridden_role_title_reaches_every_authoring_surface.py`, four cases, all behavioural through the service/CLI. The region assertion is by **absence** as the subtask asks — the bundled title (read off the catalog, never spelled as a literal) occurs nowhere between `squads:start` and `squads:end` in either compiled file — plus the generated skill body, `sq workflow` through the CLI runner, and the override-declared-role control.
    
    **Two existing tests needed a fixture correction, and it is worth a look because it is where the false docstring claim came from.** `tests/unit/test_managed_section_and_cheatsheet_goldens.py`'s `_PINNED_ROSTER` and `tests/unit/test_dropped_type_authoring_prose_no_crash.py` both handed the renderer a roster whose `title` was display-cased (`"Code reviewer"`, `"Product owner"`, `"Manager"`) — values the resolver never produces for those slugs. Invisible while the authoring bullet ignored the roster; once it reads it, the bullets rendered `The **Product owner** authors ...`. I corrected the fixtures to the titles the catalog actually carries (`code reviewer`, `product owner`, `manager`, ...) rather than re-pinning the mis-cased bytes: **no assertion was loosened** — every existing assertion string, including `"The **product owner** authors **epics**"`, is unchanged, and the byte-exact goldens stay byte-exact. The regenerated `claude_md_section.txt`/`agents_md_section.txt` differ only in the roster lines, which now match what this repository's own committed `CLAUDE.md` renders (`- **Catherine Manager** — manager (\`manager\`)`); they previously did not. If you would rather that fixture change came as its own item, say so and I will back it out.
    
    Gates on the final tree: `4356 passed, 7 skipped in 90.28s` (baseline 4352 + the 4 new), 0 FAILED; `pyright` 0 errors; `ruff check` and `ruff format --check` clean; `sq check` clean. No bundled template touched, so no manifest/content-store regen is implied.
    
    @manager ST7 is complete; the parent's status is yours to move.
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-01T09:44:06Z] Elias Python:
  - Implemented all six subtasks. Every role-mirror consumer now resolves through the catalog while the mirror stays fully written (no key removed, no template touched, no migration, no corpus change).
    
    **The seam**: `resolve_role_for_item(item, squad_dir)` in `_roles/_resolver.py` — wraps `role_base_from_item` + `resolve_role_with_base`, falling back to `RoleDef.from_extra` only for the genuinely-orphaned custom-role edge case (no catalog entry, no override file). Used by `roster()`/`roster_all()` (via a new `_role_view` helper), `_resync_role_skills`, `_project_roster_item`, `regen()` (items.py), and `backend_entry_drift` (sq check).
    
    **is_default carry (ST2, closes BUG-850)**: `role_base_from_item`/`dev_base_from_item` now carry `is_default` from `extra.is_default` alongside `full_name` (now sourced from `item.title`, not `extra.full_name`, so a role item with no stored `full_name` at all resolves correctly rather than raising). Falsified live: disabled the carry → `sq role set-default` + sync reverted to the catalog default (red); restored → held (green). Same drill on `dev_base_from_item`'s bare-subscript read: restored it → `KeyError` on a role item missing `extra.full_name` (red); reverted to `item.title` → resolves clean (green).
    
    One correction to my own first pass, recorded so it isn't rediscovered: I initially widened the carried set to every CLI-`--set`-able role field (title/mission/responsibilities/model/color), reasoning from `EXTRA_FIELDS["role"]`'s declared allowlist. That broke `test_operator_named_roles_survive_sync.py` and two `test_roles_catalog_document_reaches_an_activated_role.py` cases, which pin the opposite, pre-existing, intentional behavior: `_refresh_catalog_extra` treats a `--set` on any of those fields as staleness to *converge* on the next sync, never a designation to *preserve* — only `full_name`/`is_default` have dedicated verbs that make the stored value the operator's lasting answer. Reverted to the narrow carry the task specifies. Net effect: `sq role <slug> update --set color=...` still writes `extra.color` (unaffected), but the immediate pointer regen inside `update()` now shows the catalog's answer rather than the ad-hoc value — a narrower visibility window than before this stage (previously visible until the next sync; now never, matching how the field was always going to end up). Flagging this as a real, if minor, UX narrowing in case it wants its own decision later — `tests/service/test_generic_extra_field_metadata.py::test_setting_a_role_extra_field_regenerates_its_claude_pointer` documents the new behavior.
    
    **Skew discriminator (ST4)**: `_itemfile._exempt_extra_keys` now keys off `item.type == ROSTER_ROLE` instead of `extra.mission` presence — outlives the mirror, and `PERMITTED_EXTRA_SKEW`'s frozenset/pin are untouched.
    
    **sq check gap found and closed in the same file**: `backend_entry_drift` calling `resolve_role_for_item` meant a role with a genuinely-invalid override (blank field, bad key) now raises during the pointer-currency scan — uncaught, that aborted the *whole* `sq check` run ("could not scan the corpus"), swallowing every other finding. Caught `SquadsError` there and return no finding (the override's own invalidity is already reported by `_check_role_override_resolves`, unrelated to this stage) — see `tests/integration/test_blank_role_override_field_breaks_no_generated_surface.py`.
    
    **ST6 proof** (`tests/integration/test_role_override_reaches_managed_files_before_a_healing_sync.py`): constructed wrongness per the acceptance's own instruction — a squad synced once (baseline), *then* a per-slug override added, *no* sync afterward. `roster()`/`roster_all()`, `refresh_managed()`'s compiled regions, and `regen()`'s per-entry pointer all carry the override immediately; the item's own stored mirror is asserted stale throughout. Same file also carries the `sq role set-default` survives-sync behavioural proof and the is_default falsification. A held-roster, no-constructed-wrongness sync-twice run diffs to zero (driven, not committed as a test — the existing sibling test `test_a_repair_after_the_sync_changes_nothing_about_the_roster` already covers that shape).
    
    **Fallout fixed along the way** (pre-existing tests whose *assumptions* changed correctly, not regressions): three tests in `test_role_projects_resolved_name_and_mission_onto_item_fields.py` and two in `test_roles_catalog_document_reaches_an_activated_role.py` asserted the old mirror-lag behavior (a pointer regen using a stale index-loaded value, or `sq check` staying silent about a genuinely-drifted pointer before a sync). Updated each to assert the corrected behavior, with the mechanism explained in the docstring/comment at the point of change — happy to walk through any of them.
    
    **Known-red, not mine**: `tests/cli/test_sync_reports_a_drifted_roster_item.py::test_sync_command_warns_on_a_drifted_role_and_still_exits_clean` and `tests/service/test_sync_skips_a_drifted_roster_item.py::test_a_drifted_role_is_skipped_and_named_while_the_rest_of_the_roster_syncs` fail on this tree, traced to a concurrent sibling's uncommitted removal of `_refresh_role_skills_extra` from `_services/_maintenance.py`/`_services/_base.py` (the skills-cache retirement) — confirmed via a disposable worktree at clean HEAD, where both pass. `_services/_maintenance.py` isn't in my file list; left untouched.
    
    Gates: `pyright`/`ruff check`/`ruff format --check` clean. `tests/meta` 261 passed, 5 failed (all `test_override_manifest_and_stamp_freshness.py`, the orphan-content-store residue named as the coordinator's). Targeted (129 tests across every file touched): all pass. Full suite: 4345 passed, 7 failed (the 2 above + the same 5 orphan-store), 7 skipped — stable across three runs. `sq check`: clean.
    
    @qa the BUG-850 acceptance is proven behaviourally in the new test file above; ready to close alongside this task. @tech-lead flagging the `--set`-field visibility narrowing above for your call on whether it needs its own decision.
- [2026-09-01T10:38:56Z] Catherine Manager:
  - Reopened Done->InProgress. Acceptance clause 2 is breached on the exact surface it names, driven not inferred: with squads/.overrides/roles.toml carrying [roles.reviewer] title = OVERRIDE-TITLE, a fresh init + role activate + sync renders CLAUDE.md line 17 as OVERRIDE-TITLE and line 107 as 'code reviewer'. squads:start is line 3 and squads:end is line 123, so both disagreeing lines sit inside the compiled managed region.
  - Mechanism: _interactions/__init__.py calls role_by_slug(slug).title, and role_by_slug takes no squad_dir — it is a bundled _BY_SLUG lookup. The live resolved titles are consulted only in the RoleNotFoundError branch, so a bundled role whose title an override changes never resolves.
  - Not amending the acceptance to match what shipped. The clause says an override reaches the compiled managed regions; it reaches one line of them and not another. Scope of the reopen is that consumer only — everything else the review drove is clean.
- [2026-09-01T11:21:23Z] Olivia Lead:
  - - Remaining scope written down as **ST7**, and it is the whole of the reopen. Everything else in this task was driven clean by REV-854 — the mirror stripped key by key and separately poisoned with wrong values, `CLAUDE.md`, all eight `.claude/` pointers and the role bodies regenerating byte-identical, and `sq role set-default` surviving sync on both a bundled and a developer role. ST1–ST6 stay Done.
    
    - **The acceptance is not amended.** Clause 2 already says a project override "reaches the compiled managed regions and the pointers on the next regeneration". It reaches line 17 and not line 107 of the same region, so the clause is breached, not mis-worded.
    
    - The consumer is `authoring_owner` in `_interactions/__init__.py`, which resolves the display title with `role_by_slug(slug).title`. `role_by_slug` takes no `squad_dir` — it is a bundled `_BY_SLUG` lookup — and the live `role_titles` map, already threaded to both call sites and already carrying the resolved title, is consulted only inside the `RoleNotFoundError` branch. So a role that *is* in the bundled catalog, which is every role an override is likely to retitle, never reaches it.
    
    - **Two renderers, not one.** `templates/claude/claude_section.md.j2` (the compiled `CLAUDE.md`/`AGENTS.md` region) and `templates/workflow.md.j2` (the cheatsheet, shared by the generated `squads` skill body and `sq workflow`) both call it. The cheatsheet half was not in the reported repro; it has the same defect.
    
    - **One correction to the code's own reasoning, and it is why ST7 asks for a docstring rewrite too.** `authoring_owner`'s docstring justifies catalog-first on the ground that "a live roster entry carries the display-cased form". A roster entry's `title` is the role *title*; the display-cased form is `full_name`, a different field. This repository's own generated `CLAUDE.md` is the standing proof — with no override, the roster line and the authoring bullet both read `code reviewer`. The stated reason for the ordering does not hold, so the ordering can be inverted with no change to any no-override rendering.
    
    - ST7's own bar is behavioural rather than positional: assert the compiled region contains **no** occurrence of the bundled title for the overridden slug, rather than checking the two known line numbers — the same defect on a third line would otherwise pass.
    
    - @python-dev ST7 is the only outstanding work here; the rest of the task is verified. @manager reopening scope is this one consumer and does not reach the sibling tasks.
<!-- sq:discussion:end -->
