---
id: ADR-696
sequence_id: 696
type: decision
title: Validate the minimum semantics the engine needs, never trust a spec
status: Accepted
author: architect
refs:
- FEAT-691:addresses
- ADR-541
- ADR-604
- ADR-474
- ADR-85
- EPIC-538
- ADR-163
description: Engine behaviour keys off declared status roles, never literal status
  names; the loader enforces a per-capability floor and overrides may shadow built-ins
  under validation
created_at: '2026-07-29T15:18:18Z'
updated_at: '2026-08-15T14:19:46Z'
---
<!-- sq:body -->
## Context

The engine reaches into the workflow spec for two different kinds of thing. Most of what it
reads is *vocabulary* — type names, status names, prefixes, labels — and that axis is already
fully adopter-owned: `Item.type` and `Item.status` are plain `str`, the spec is the sole
vocabulary authority, and every non-roster type may be dropped, renamed, or re-prefixed. The
rest is *semantics* — "is this item still open", "is this status hidden from the default
list", "is this roster entry live" — and semantics is where the engine still cheats in two
opposite directions at once.

**It binds some semantics to literal names.** `_workflow/_models.py::_RESERVED_FLOOR` requires
every spec, bundled or overridden, to declare the literal statuses `Draft`, `Active`, and
`Archived`; the module docstring calls them "the agent-lifecycle statuses the engine binds by
literal name". The bindings themselves are few and enumerable — four create sites in
`_services/_roster.py`, four skill-seed sites in `_services/_maintenance.py`, and the
active-column tick in `_cli/_role.py` — but they are the reason those three names cannot move.

**And it trusts the spec for the rest.** A lifecycle can be declared that no engine behaviour
can actually drive, and nothing at load says so. One such hole was already closed —
`_check_reachable_settled` refuses a machine that can never reach a settled status, because
items stuck on it would break `sq blocked`, the default closed-item filter, and inbox
suppression. That check is the template this decision generalises: the engine states what it
needs, and the loader refuses a spec that does not supply it.

The semantic seam the engine should be reading is already in the spec and already exposed to
clients. `StatusSpec.role` names an entry in the `RoleSpec` catalog carrying
`settled`/`hidden`/`color`; `sq workflow statuses --json` and `sq workflow roles --json` publish
both halves; the bundled roster machine maps `Draft → pending`, `Active → active`,
`Archived → retired`; and `is_open`, `terminal_set`, and `hidden_by_default` are already
derived from the role, never from the name. The VS Code Roster view's hide-archived filter
already runs off `isHiddenByDefault(item, statusRoles, roleCatalog)` — role-derived, no status
literal. So the seam works; the engine is simply not using it everywhere.

One more fact makes this urgent rather than cosmetic. `_loader.py::_collect_additive_conflicts`
refuses **any** override key that names a built-in lifecycle, status, item type, collection,
sub-entity kind, or status role. A project therefore cannot rebind `role`, `skill`, or
`operator` to a renamed lifecycle at all — not even to one that declares the same three
semantics under different names. Any promise that a project's roster lifecycle is
customisable is unreachable while that restriction stands.

**The replacement for that restriction is already designed.** EPIC-538 settled a single shared
override engine — deep recursive merge at leaf granularity, an `active`-keyed deselect (renamed
`selected` in §4b), and eval-free splat-refs — reused by the workflow, playbook, and roles loaders, and explicitly framed as
replacing the additive-only policy. It also names the playbook as the fourth override kind and the
consolidation of the three bundled TOMLs into one directory. That design is settled input to this
decision, not something to re-derive: §4 and its sub-sections adopt it, and the parts of this
decision that are genuinely new are the semantic floor (§3), the role-keyed lookups that make the
floor expressible (§2), and the ordering that makes deselect safe without its own rulebook (§4b).

## Decision

### 1. The rule

Every engine behaviour that depends on lifecycle semantics resolves through a **declared
semantic role**, never through a literal status name; and the loader **refuses a spec that
does not declare the semantics that behaviour needs**. Validation replaces trust, and
validation replaces prohibition.

This holds for every item type, not just the roster. It yields two standing duties:

- **No status-name binding in engine code.** A site that needs "the live status of this type"
  asks the spec by role and gets whatever that project called it.
- **A capability floor, enforced at load.** Whatever a capability needs from a lifecycle is
  stated in code and checked when the spec is built, fail-closed, with every violation
  reported at once.

### 2. Role-keyed lookups replace the status literals

Two derived accessors on `WorkflowSpec`, computed from `machine_for(item_type).states` and the
existing `role_for(status)` — no new stored field, nothing an adopter declares twice:

- `live_statuses(item_type) -> frozenset[str]` — the states of that type's lifecycle whose
  resolved role carries the `live` flag (§2a). This is the **read predicate**: "is this entry
  on offer" is `item.status in live_statuses(item.type)`.
- `live_initial(item_type) -> str` — the status an entry squads *itself* scaffolds is created
  at: the lifecycle's `initial` when that status is live, otherwise the sole live status.
  R1′ (§3) is what makes this total.

**No role-*name*-keyed status accessor survives, because nothing needs one.** The read axis is
the `live` flag; settled-ness and default-hiding are already read off the role object
(`role_for(status).settled` / `.hidden`); and the create-at target is the lifecycle's own
`initial`. A generic `role_statuses(item_type, role_name)` / `sole_role_status(item_type,
role_name)` pair has no caller left once the sites below convert, so the two accessors are
**reshaped into the two above rather than kept alongside them** — accumulating a public accessor
with no caller is how the dead-code scan earns its keep.

`_RESERVED_FLOOR` and the `STATUS_DRAFT` / `STATUS_ACTIVE` / `STATUS_ARCHIVED` constants leave
`_workflow`'s surface. The nine converted call sites resolve into three groups, and the group a
site belongs to is a design question, not a mechanical substitution:

| Site | What it actually needs | After |
| --- | --- | --- |
| `_services/_roster.py` — `activate_role`, `add_dev`, `add_skill`, `add_operator` (4 sites) | the lifecycle's own `initial` — and `create()` already defaults to it | **drop the `status=` argument** |
| `_services/_maintenance.py` — the four system-skill seed sites (2 `Item(...)` constructions + their 2 matching reflog payloads) | created **live**, not merely created | `status=spec.live_initial(ROSTER_SKILL)` |
| `_cli/_role.py` — the roster table's tick column | the live predicate | `r.status in spec.live_statuses(ROSTER_ROLE)`, and the column header renamed off `Active` to match the flag |

The middle row is the one that does not follow the general rule, and it is worth stating why
rather than leaving an implementer to discover it. Those four sites are squads scaffolding its
own system skills, and a generated role entry preloads a skill **by slug**, independently of that
skill item's status. Seeding a system skill at a non-live `initial` would therefore leave a
freshly initialised squad with every role entry preloading three skills that were never
materialised — a config-invalid state produced by a clean `sq init`, in a project that did
nothing wrong. Scaffolding must create live; user-facing creation (`add_skill` for a custom
skill, the roster `add`/`activate` verbs) honours whatever `initial` the project declared.

**Carve-out: migration runners keep their frozen literals.** `_migrations/_v0_4_to_v0_5.py`
and `_v0_8_to_v0_10.py` each hold a private `_STATUS_ACTIVE = "Active"`. That is correct and
must not be "fixed": a migration transforms a corpus written at a pinned schema version, so it
must read the vocabulary that version actually used, never the live spec. The two are already
private module constants, not imports of the shared name, so the retirement in this section
does not touch them.

**Guard.** A `tests/meta` scan keeps the rule true after this lands: no bundled roster status
name may appear as a literal in `src/squads/` outside the bundled spec package (`_specs/`, which
holds `workflow.toml` and its two siblings) and `_migrations/`. This is the same shape as the
existing meta guards (stray ticket references, module-level mutable state) — a cheap, readable
scan, not a new framework.

**The spec package stays data-only, and the exemption depends on it.** The scan exempts the whole
of `_specs/` by directory rather than by filename, so any `.py` placed there would be silently
outside the guard. That is the correct shape for the scan — matching how its sibling guards exempt
a directory, and avoiding a filename list that goes stale the moment a fourth document lands — but
it means the exemption's safety rests on the directory containing no engine code. So that is a
standing property of the layout, not an accident of it: **`_specs/` holds the bundled documents and
a docstring-only package marker, and no logic ever moves there.** Anything that reads or interprets
those documents belongs to the loader that owns it (`_workflow`, `_roles`, `_interactions`), which
is where the scan can still see it. The directory's own name is a weaker guarantee than it used to
be: a package named for specs reads more like a code layer than the data-sounding name this package
carried earlier, which is precisely why the property is written down here rather than left to the
name to imply.

### 2a. The `live` flag: a fourth field on the status role

The materialisation axis gets **its own boolean on the status-role object**, alongside `settled`,
`hidden`, and `color`:

```toml
[roles.active]
settled = false
hidden  = false
color   = "positive"
live = true
```

**It cannot be a role name.** Keying materialisation off the role literally named `active` would
re-import name-locking at the role layer — the same trade §3 refuses on the status layer.

**And non-settled will not substitute for it**, which was worth checking rather than assuming.
Four bundled roles are non-settled: `active`, `attention`, `blocked`, and `pending`. So a project
declaring a roster status `Suspended` on a `blocked` role, or `Provisional` on `pending`, would
have both treated as live — an agent suspended or provisional is precisely one that should
*not* be materialised into the host's config. Non-settled means "not at rest"; live means
"on offer". Those are different questions and one flag cannot answer both.

**The name is `live`, not `materialised`.** `materialised` names the downstream effect — files
written by a backend — which is a roster-only consequence of a field that lives in vocabulary
shared by every item type; it would read as nonsense on a work status. `live` names what the
state *means*: this entry is on offer, and therefore available to be spawned, loaded, cited, and
assigned. Materialisation is then the consequence, which is the right causal direction, and it
leaves the same flag serving the participation gate (`--as` / `--assignee`) without a second name.
It also matches the grammar of its siblings — `settled` and `hidden` describe the state, not its
effect.

**It defaults to `false`, and the direction of that default is deliberate.** `hidden` defaults
false because wrongly hiding an item is worse than wrongly showing it. `live` defaults false
for the mirrored reason: wrongly offering an entry writes an agent into a host's config, which is
worse than wrongly withholding one. A custom role is therefore not live until its author says
so.

Adding the field is a **spec-format change and nothing more** — no schema bump and no migration
runner. Neither the role name nor the role's flags ever appear in item frontmatter or the index;
they are workflow-spec vocabulary. The bundled spec gains `live = true` on one role and the
default everywhere else, and `sq workflow roles --json` gains the field additively.

### 3. The floor: what a lifecycle must declare to be usable

**Universal, for every lifecycle.** Already enforced, restated here as the floor rather than
as five unrelated checks: every initial and transition status is declared; every state is
reachable from `initial`; at least one reachable status resolves to a settled role; every
explicit `status.role` names a declared role; every role's `color` is in the closed intent
palette; and the fallback role a role-less status resolves to is itself declared.

**Additional, for a lifecycle bound to a `category = "roster"` type.** The roster is the
strict case because its entries are materialised into the agent hosts' own files, so a
lifecycle the engine cannot drive corrupts generated backend config rather than merely making
an `sq` view odd:

- **R1 — at least one status whose role is `live`.** Zero means no entry could ever be
  materialised, so the squad's generated config could never present an agent.
- **R1′ — if the lifecycle's `initial` status is not live, exactly one status is live.**
  This is the narrow uniqueness the engine genuinely needs: it keeps `live_initial` (§2) total
  for the scaffolding path that must create an entry already on offer. When `initial` *is* live
  there is no ambiguity to resolve and any number of further live statuses is fine.
- **R2 — at least one settled status, reachable from a live status, that is not live.**
  Retirement must be reachable: an entry must be able to stop being live. The universal floor
  only requires *some* settled status to be reachable from `initial`, which a machine could
  satisfy without ever letting a live entry retire. Note that R2 asks for a *settled*
  non-live status, so a merely-paused state (non-live but non-settled, e.g. a `blocked`-role
  `Suspended`) satisfies the spirit of "stop being live" but not R2 — a lifecycle needs a real
  end as well as a pause, and may have both.

**R1 was `exactly one` in this decision as first written, and that rationale is withdrawn, not
qualified.** The uniqueness was justified solely by giving the create path an unambiguous write
target. The lifecycle already declares one — `initial` — and the existing lifecycle checks already
validate it, so uniqueness was buying something the spec had all along. R1′ keeps exactly the
sliver of uniqueness that `initial` cannot cover, and nothing more. What this relaxation *gains*
is stated in the consequences: a project may declare a non-live `initial` and get a
parked-then-activated roster entry with no special casing anywhere in the engine.

All three clauses are derived from the role assignment and the `initial` the spec already carries.
None adds a field beyond §2a's flag.

**Why the floor does not require the role *names* `retired` and `pending`.** Requiring them
would re-import name-locking one level up — trading three reserved status names for two
reserved role names, with the same consequence for a project whose vocabulary differs. The
engine does not need them: it consumes retirement through `settled`, default-hiding through
`hidden`, and being-on-offer through `live`, all read off the role object, and the create-at
target through the lifecycle's `initial`. **No role name is engine-bound at all** except the
fallback role a role-less status resolves to. The bundled spec keeps `retired` and `pending`
because they read well; a project may declare others.

### 4. Overrides: shadowing is allowed and validated, not refused

The additive-only rule is replaced by **declared-override**. An override key that names a
built-in overrides it; the guardrail is the floor above plus the checks already in
`WorkflowSpec._validate`, not a blanket refusal.

The engine that performs the merge is **not new here**. EPIC-538 settled its design — one shared
override engine reused by the workflow, playbook, and roles loaders, built from deep recursive
merge, `selected`-based deselect, and splat-refs — and this section is that design, restated as a
decision with the floor rules it did not have. What follows says where the two agree, where this
extends the design, and the one place it contradicts it.

- **Merge granularity: deep recursive merge at leaf granularity.** An override supplies only the
  fields it changes; everything else inherits from the bundled built-in. Tables recurse per key;
  a leaf value replaces its counterpart. This is EPIC-538's formulation and it subsumes the
  "per-field merge" phrasing that stood here before — per-field is what recursion looks like one
  level down from a section, and the recursive statement is the correct general one because the
  spec nests (an `ItemSpec` holds a `LabelSpec`; a `Collection` holds `Badge`s). It also matches
  the precedent already frozen for role overrides ("roles merge field-wise by slug",
  `docs/stability.md`).
- **Plain arrays are leaves — replaced wholesale, never element-merged — unless a splat-ref is
  used.** A `transitions` map recurses because it is a table; a `badges` list, a `fields` list, a
  `parents` list, a `validators` list is replaced whole. Silently unioning list elements would
  produce a value nobody declared and nobody can read back from the TOML. §4a is the opt-in for
  appending without restating.
- **Deselect via `selected`** — §4b.
- **Splat-refs** — §4a.
- **What survives as prohibition.** The reserved-vocab core stands: the three roster type
  *keys* (`role`, `skill`, `operator`) must exist, and `category` may not move into or out of
  `roster`. **This contradicts, deliberately, both ADR-541's type-axis floor and EPIC-538's
  roster-locked invariant**, each of which forbids an override to "add, deactivate, field-merge,
  or rename/re-prefix" a `category = roster` type. Roster *membership* stays closed in both
  directions and a roster type key can never be dropped; but a roster type's other fields —
  its `lifecycle` above all, and its prefix, folder, labels, and order — become ordinary
  validated customisation, subject to the same uniqueness and live-item checks every other type
  faces. The reason is the constrain-don't-lock direction, which postdates both statements: a
  locked roster lifecycle makes the roster's declared states unnameable by the project whose
  agents they describe, and the safety a lock bought is bought instead by §3's floor. It is also
  the narrower claim on the evidence — the engine binds the roster by type **key**
  (`ROSTER_ROLE`/`ROSTER_SKILL`/`ROSTER_OPERATOR`) and by the fixed `category`, and binds nothing
  to a roster type's prefix or folder; no such literal exists in `src/` outside the migration
  runners, which read the vocabulary of the schema version they transform and are correctly frozen.
  A lock over a field no call site reads is a prohibition standing in for a check, which is what §1
  exists to retire. **This overrides that one clause and nothing else in either statement**, and the
  override is recorded at both ends: ADR-541's floor section and its category bullet are narrowed in
  place with a dated amendment note pointing here, so neither decision is left asserting the other's
  reverse. ADR-541 is not superseded as a whole — it remains the authority on the category taxonomy
  and the validator model; only its field-axis clause is overridden.
- **Failure shape.** `_collect_additive_conflicts` becomes `_collect_floor_violations`, keeping
  its two calling modes: fail-fast for `open_service` (raise on a non-empty collected list) and
  collect-all for `sq workflow lint` (one finding per violation, each carrying the override
  path and a fix hint). Refusal is a clean `SquadsError`, never a traceback.
- **Drift.** Under ADR-85, template and role overrides carry an `override-base` version stamp so `sq check`
  can warn when the bundled counterpart moves; a workflow override could not drift before,
  because it could only *add*. Now that it can shadow, it inherits the obligation: an override
  file that shadows at least one built-in key must carry an `override-base` stamp, read by the
  loader and fed to the existing drift warning. An override that only adds new keys needs no
  stamp, exactly as today. The playbook override, as the fourth override kind, inherits the same
  stamp and the same `sq override` verbs.

  **The stamp is the comment marker, not a spec key** — `# squads:override-base:<version>` on the
  file's first line, the same grammar the role TOML overrides already carry (and the HTML-comment
  form templates carry), read by one reader and rewritten by one verb. There is exactly one
  provenance carrier per override file, and it is this one; a top-level `override_base` spec key is
  not introduced, and writing one into a workflow override is refused by the closed top-level key
  space of §4b. Four reasons, in order of weight:

  1. **`sq override update` must not rewrite the adopter's document.** Re-stamping after a hand-merge
     is the whole point of the drift cycle, and it promises the override body is never touched. A
     comment stamp is a single-line substitution that provably preserves every other byte. Rewriting
     a *key* inside arbitrary TOML needs a round-tripping writer — the stdlib parser is read-only —
     and any serializer reformats and drops comments, in a file whose useful content is largely
     comments. That cost would be paid on every re-stamp, forever.
  2. **One grammar across every override kind.** This section already says the playbook override
     inherits *the same stamp*; a spec key would make workflow and playbook the only kinds whose
     provenance lives somewhere else, so "the same stamp" and a key spelling cannot both be true.
  3. **The loader gains nothing from a key.** A key would be loader-visible and typed — but the
     loader already holds the file's text before it parses it, so reading the comment costs it
     nothing and needs no strip-before-validation step (which a key *would* need, exactly as
     `[selected]` does, because the models forbid extras). The value is a version string; the
     stamp pattern is its validation, and a malformed stamp reads as absent, which is the
     fail-safe direction.
  4. **Two carriers for one fact would disagree**, with no rule for which wins.

  **What "must carry" means, and where it is enforced.** The obligation is reported, not a load-time
  refusal: a shadowing override with no stamp is an **error**-level finding from `sq workflow lint`
  and `sq check`; a stamp older than the running version keeps today's drift **warning**; an add-only
  override with no stamp reports nothing. Absent provenance is not a semantic hazard — the merged
  spec either satisfies the floor or it does not, and that verdict is unchanged by whether the file
  says what it was branched from — so refusing to run `sq` over a missing comment would be a hard
  stop the floor itself does not need. The floor's fail-fast refusals (above) stay hard stops; this
  one is not one of them.

  Two surfaces move with this and are part of the same obligation: the drift classifier keeps its
  three states, with an unstamped file classified not-current (a file with no base has by definition
  not been reconciled), and the workflow `sq override diff`'s Δ-mine — which today diffs against an
  empty reference on the grounds that the override is additive-only — must diff against the bundled
  spec once shadowing is possible, or it stops describing what the adopter actually changed.

### 4a. Splat-refs: composing onto a bundled list without restating it

Because arrays are leaves, appending one entry to a bundled list would otherwise mean copying the
whole list into the override and thereby freezing it against bundled improvements. **Splat-refs**
are the eval-free escape, exactly as EPIC-538 designed them:

- `$(path)` splices the bundled value at *path* as a single element; `$(*path)` spreads a bundled
  list's elements into the surrounding list. The star is the difference between one element and
  many, and it is what makes `["$(*self)", <new>]` mean append.
- `$(self)` / `$(*self)` addresses **the key currently being written**, which is the only usable
  idiom where the surrounding structure has no stable dotted name — the playbook's per-type role
  guides. Dotted paths address keyed tables (`$(*items.task.validators)`).
- **`self` means the nearest enclosing *keyed* path, at any depth.** A list position contributes
  nothing to the path, because a list index has no dotted name to contribute — so `self` inside a
  list, or inside a list inside a list, still means the key those lists hang from. This is
  definitional rather than a special case: it is what "the key currently being written" already says,
  made explicit because nesting invites the other reading. Three things follow, and all three are
  intended. Two `self` tokens at different list depths under one key resolve to the same base value.
  A `$(*self)` nested inside a sub-list spreads the key's list into that sub-list — permitted,
  because the shape of the destination is the models' business and not the engine's (see "What a
  splat-ref owes"), which is the same answer the abbreviation rule gives everywhere else. And
  spreading a base list that is **empty** yields just the new elements: an empty list is a value the
  base holds, so it composes to nothing added, which is distinct from a *missing* key — that
  dangles. Compose-only also permits the same base list to be spread twice, duplicating it; nothing
  needs it to behave as a set.
- **A path segment is a TOML bare key** — `A-Za-z0-9_-`, one or more characters — so the grammar
  addresses exactly what TOML can key without quotes. That single rule fixes what three separate
  restrictions would otherwise each need arguing: a hyphenated key (`user-story`, `tech-lead` —
  the natural spelling for multi-word vocabulary in this project) is addressable; a leading digit is
  addressable; and a non-ASCII key is *not*, because TOML bare keys are ASCII, so such a key is a
  quoted key and falls under the constraint below rather than being an arbitrary asymmetry.
  Anchoring on TOML's own definition is what keeps the grammar from drifting narrower than the
  documents it addresses — the alternative, an identifier-shaped path, silently excludes names the
  spec is free to declare, and by the abbreviation rule a value the adopter may write literally must
  stay expressible as a reference.
- **A key that requires TOML quoting is not addressable, and the constraint binds the bundled
  documents rather than any adopter.** `.` is the path delimiter, so a key containing a dot is
  irreducibly ambiguous in a path; a quoted-segment sub-grammar would be a second nested syntax for
  a case no document has. It costs nothing to leave out, and the reason is structural: **resolution
  is base-only, so a dotted path can only ever address a key of the bundled document.** An adopter's
  own vocabulary is never the target of a path — a brand-new key has no bundled counterpart and
  dangles by design, whatever it is spelled, and an adopter *declaring* a hyphenated type addresses
  bundled paths from inside it perfectly well, because the hyphen is in the destination and not in
  the path. So the addressability rule is a constraint on squads' own key names, discharged by a
  standing guard over the bundled documents (every key a TOML bare key), in the same scan that keeps
  a bundled string value from beginning `$(`. No adopter can reach it, which is why there is nothing
  for an adopter to learn.
- **Resolution is against the bundled base only.** No override value is ever a splat target, so
  there are no cycles, and the merge is order-independent: two overrides of unrelated keys
  produce the same result in either order. This is the property that keeps the engine free of an
  evaluation order to reason about, and it must not be relaxed for convenience.
- **Compose-only.** A splat adds; it never removes an element. Removal is `selected`'s job, at
  section granularity, or a wholesale array replacement at value granularity.
- **Fail-closed** on a dangling path, a misused spread, a malformed token, an unparsed token
  surviving resolution, or nesting past the walk's declared bound. All five are stated exactly in
  "What a splat-ref owes" below, because the boundary between them and what the models own is the
  whole question.
- **A splat-ref is an abbreviation for a value the adopter could have written literally**, and is
  held to the same standard as that literal — no stricter and no looser. This is the rule that
  settles what the engine may check. `$(items.task.validators)` *means* "the value the bundled spec
  holds there"; its purpose is to avoid restating a bundled value that would otherwise stop
  tracking the bundled spec. An abbreviation refused where its expansion is accepted is a broken
  abbreviation — the adopter could not express through a splice a value they are permitted to write
  out longhand, and the two forms would produce the same merged mapping with different verdicts.
- **`$(*self)` on a key with no bundled counterpart dangles**, and therefore fails closed. This is
  right: a brand-new custom type has no bundled list to append to, and `["$(*self)", x]` there is
  a mistake, not an empty append.

**This is the mechanism by which a custom role enters a type's playbook guidance**, and it settles
that question rather than leaving it open: the project writes the type's `roles` array as
`["$(*self)", { slug = "my-role", … }]`, inheriting every bundled guide and adding its own.

**What a splat-ref owes, and what it does not.** The engine merges raw mappings and holds no schema,
so every check it performs must be a property of **the token and its operator**, never a claim about
what shape a destination ought to hold. That yields exactly four failures, and no fifth:

1. **A dangling path** — the addressed base path does not exist.
2. **A spread whose target is not a list** — `$(*path)` where the base value is not a list. "Spread
   these elements" is undefined for a non-list, so the operator itself is unsatisfiable.
3. **A spread with no surrounding list** — `$(*path)` as a whole value rather than a list element.
   Same reason: nothing to spread into.
4. **A malformed or surviving token** — a value in token territory (below) that is not a well-formed
   whole-value token: an unparsable path, an unclosed token, a double star, a stray token left after
   resolution. Reported *as a malformed token*, quoting the path and what a path may contain — not as
   a surviving literal, which describes a different mistake and tells the author to do what they
   already did.

Those four are what the *grammar* can be wrong about. One further refusal is owed for a reason that
is not about the grammar at all:

5. **Nesting beyond a declared bound** — a document nested deeper than the engine will walk is
   refused, naming the dotted path where the bound was hit. This is **not** a policy about how deep a
   spec may be: it is what keeps an interpreter recursion limit from surfacing as a traceback. The
   bound therefore has to satisfy two properties rather than being a taste call — far above anything a
   hand-authored document reaches (the deepest key path in any bundled document is four levels), and
   far below the interpreter's own headroom, with room for the copy the merge performs at each level.
   It binds **both** walks, the override's resolution and the merge's traversal of the untouched base,
   and it must be checked *before* recursing or copying, since a deep base subtree fails inside the
   copy rather than in the engine's own frame.

**The no-traceback contract stays unqualified, and this is why.** "Either it succeeds or it is
refused cleanly" is a promise about what a `sq` invocation does to the person running it, and a wall
of Python satisfies neither branch. The engine's inputs are adopter-authored files by design and the
TOML parser accepts a document far deeper than the walk survives — a single legal line of dotted keys
reaches it — so nothing upstream guards this and the guard has to live here. Given that the fix is one
counter and one comparison, the honest move is to make the contract true rather than to narrow it:
weakening a stated invariant to match code that could cheaply satisfy it is how invariants stop
meaning anything. A bounded refusal also lands on the same violation channel as everything else, so
it collects in lint mode instead of aborting the pass.

**A splice is never checked against the shape of the key it lands on**, and the earlier wording "a
table where a scalar is due" is withdrawn rather than reinterpreted. Two reasons, the second
decisive. First, "where a scalar is due" is schema knowledge, which the engine deliberately does not
have; the only schema-free reading is a comparison against the *base's* shape at the destination.
Second, that reading would make a splice stricter than the literal it abbreviates: `deep_merge`
knowingly lets a hand-written leaf replace its counterpart with a different shape, so an adopter
could write the offending value out longhand and get it through. By the abbreviation rule above, that
settles it — the splice is accepted and the shape question belongs where every other shape question
already lives.

Nothing is unguarded by this. A splice can only ever produce a value the **bundled document itself**
holds, landing at the wrong key, and the strictly-typed models reject exactly that at load with a
per-field type error. Shape is the models' plane; composition is the engine's.

The cost is real and is not specific to splices: a shape error arrives as a model-validation error
rather than a collected violation, so `sq workflow lint` reports it as one finding and stops instead
of listing it beside the others. That is equally true of the hand-written value, which is the point —
privileging splice-caused shape errors as the one collectable kind would make lint's behaviour read
as arbitrary. The concern is legitimate and belongs to a different question: **whether the loader
translates a model-validation error into per-field lint findings** rather than one opaque one. A
`ValidationError` carries a list of per-field errors, so that is answerable, and answering it fixes
the whole class at once instead of one privileged sliver. It is not folded into the splat grammar.

**Token territory: a string is in token territory only if it begins with an unescaped `$(`.** The
predicate is the same for a value and for a key; what territory *means* differs by position, and both
are stated together below under "The sigil is reserved in every string position". For a value, token
territory means the string must be a well-formed whole-value token or it fails closed (rule 4). A
value that merely *contains* `$(` somewhere after its first character is data: it is left verbatim,
no violation, no escape required. `$$(` at the start escapes a string that must literally begin `$(`.

This narrows a detection predicate that was wider than the recognition rule it enforces. The
recognition rule — stated three times — is that a token is recognised only when it is the **entire**
string value; a check that fires on `$(` *anywhere* therefore rejects strings the grammar was never
going to interpret. It has to be narrowed rather than papered over, because **the splat sigil is
POSIX command-substitution syntax**, and one of the three documents this engine serves carries shell
content: a playbook entry's `commands` are command lines, and its guidance arrays quote them. Under
the wide predicate `git commit -m "$(cat msg)"` is a load failure explained in terms of a grammar the
author never used, and every tool that ever writes a bundled string into an override file inherits a
standing duty to escape on the way out — a duty that also makes the written file differ from its
bundled source on every such line, so `sq override diff`'s Δ-mine would show differences the adopter
did not make. Narrowing the predicate removes the duty instead of distributing it; it is not a change
of sigil, and the token syntax is untouched.

Two consequences, both accepted deliberately:

- **An interpolation attempt stays literal.** `prefix = "text $(items.task.prefix)"` is data, not a
  violation. The grammar never offered interpolation, a token has always had to be the whole value,
  and the alternative is the shell collision above.
- **Only a leading `$(` needs escaping**, so the writers' duty is vacuous by construction if no
  bundled string value begins `$(` — which none does. That is worth a cheap standing guard over the
  bundled documents rather than a rule someone must remember: the same shape as the existing scans
  for stray ticket references and module-level mutable state.

**The sigil is reserved in every string position of the document — keys as well as values — and
token territory is the same predicate in both: a string is in token territory if and only if it
begins with an unescaped `$(`.** What differs between the two positions is only what territory
*means*:

- **In a value**, token territory means the string must be a well-formed whole-value token: it is
  resolved, or it is refused as malformed.
- **In a key**, token territory means the string is **refused**. It is neither resolved nor passed
  through. There is no defined splice-into-a-key operation — a path addresses a *value*, and a value
  is not a key — so a token in key position is not a feature being declined, it is a construct with
  no meaning, and the only thing it can be is a mistake.
- **`$$(` unescapes to `$(` in both positions.** Every literal string stays expressible as a key and
  as a value.
- **A string that merely contains `$(` after its first character is data in both positions**, left
  verbatim.

**Refusing a key is not the engine judging vocabulary**, which it must never do, and two things keep
it on the right side of that line.

First, **the escape means no vocabulary is withdrawn.** A project that genuinely wants a key spelled
`$(items.task)` writes `$$(items.task)` and gets it. The requirement is that vocabulary be spelled
unambiguously in a document where `$(` is reserved — not that some vocabulary is forbidden. This is
also the line between this refusal and the one refused for splices: there, holding a splat-ref to the
base's shape would have made a value expressible literally but *inexpressible* as a reference, with no
escape to recover it. The test that separates the two is whether the adopter retains a way to say the
thing. Here they do; there they did not.

Second, **deferring to the models would defer to nobody.** For a value the models are a real backstop
— fields are typed and extras forbidden — which is exactly why shape belongs to them. For a key they
are deliberately not: a section's keys *are* the open vocabulary, so the models accept any string. A
spec declaring an item type literally named `$(items.task)` loads clean, takes a prefix-map entry, and
resolves a folder; nothing downstream is in a position to notice. So a token-shaped key is the one
place where the engine's own refusal is the only thing standing between a typo and a minted vocabulary
entry — which is precisely the rationale the surviving-token rule was given in the first place, at its
strongest rather than at its weakest.

A supporting reason, not a load-bearing one: `$` is not legal in a TOML bare key, so reaching token
territory in a key position takes a deliberately quoted key. The mistake is rare. Its consequence —
a type or status that exists, is addressable, and is spelled like a broken reference — is not
proportionate to its rarity, and consistency argues the same way, since an unrecognised key at the
document's *top* level already fails closed under §4b. Passing the identical mistake at a nested level
would make the verdict a function of depth.

Two implementation constraints, both verified against the parser rather than assumed:

- The override must use TOML's **inline-array** form for a splatted array of tables
  (`roles = ["$(*self)", { … }]`), not the `[[types.<t>.roles]]` header form, which has no slot
  for a token. Heterogeneous arrays are valid TOML 1.0 and `tomllib` accepts the mixed
  string-and-table list, so the form parses; the header form simply cannot express it.
- Splat resolution must complete **before** any model validation. The models set
  `extra="forbid"` and are strictly typed, so a `str` token sitting where a `list[Field]` is due
  would be rejected as a type error before it ever got resolved.

### 4b. Deselect via `selected`: shrinking the spec

A project drops a built-in by naming it in a `selected` list — the surviving set, not the removed
set — with replace-wholesale semantics, because the point of the mechanism is to shrink. It
applies to every keyed section of the workflow spec: `items`, `statuses`, `lifecycles`,
`collections`, `subentity_kinds`, **and `roles`** (the status-role catalog, which EPIC-538's list
predates — adding it is a completion, not a change of intent).

**`selected` needs no validation of its own, and that is the whole point.** Every unsafe drop is
already caught by a check that runs on the *resulting* spec, so the mechanism reduces to an
ordering rule rather than a new rulebook:

1. resolve splat-refs against the bundled base;
2. deep-merge the override's declarations over the bundled spec;
3. apply each section's `selected` deselect;
4. build the spec and run the whole floor of §3 on the result;
5. run the live-index cross-check.

What falls out, with no deselect-specific guard written anywhere:

- A `selected` list that drops the last live status from a roster type's lifecycle **fails
  R1** — because R1 counts live statuses on the merged, post-deselect spec and finds zero. A
  `selected` list that drops the live status a lifecycle's non-live `initial` depended on
  fails **R1′** the same way.
- Dropping a status still named by a surviving lifecycle's `initial` or `transitions` fails
  `_check_lifecycle_statuses`; dropping a lifecycle still bound by a surviving `ItemSpec.lifecycle`
  fails `_check_item_refs`; dropping the fallback role a role-less status resolves to fails
  `_check_role_references`.
- Dropping a status or type still held by live items fails the existing live-index guard,
  `validate_against_index_fail_closed`, listing the offending item IDs.
- Dropping a roster type key fails the reserved-vocab core.

The one thing `selected` genuinely owes is **provenance in the message.** A floor violation caused
by a deselect must say so: "lifecycle `agent` has no live status" is unactionable
if the adopter cannot see that their own `selected` line removed it. The collected report notes,
per violation, when a missing key was *dropped from a `selected` list* rather than never declared.

**The mechanism is spelled `selected`, in one top-level table.** EPIC-538 put a per-section
top-level `active` key inside each section, and that shape has two problems. It **does not parse**:
a top-level key inside a section table collides with a sub-table of the same name, and the bundled
spec has exactly that collision — `[roles.active]` is a declared status role, so `[roles]` cannot
also carry an `active` key, and `tomllib` rejects the file outright with `Cannot declare ('roles',
'active') twice`. The same hazard exists in every other section for any project that names a type,
status, or collection `active`. And the word itself was **doing two jobs**: `active` as a deselect
key sitting next to `active` as a status-role name is confusing to read even where it happens to
parse. Both are fixed by lifting the lists into one top-level `[selected]` table keyed by section
name:

```toml
[selected]
items = ["epic", "feature", "task", "role", "skill", "operator"]
statuses = [...]
```

`selected` also says the right thing — the list is the surviving set, not the removed one. The key
space of `[selected]` is a closed, code-defined set of section names (`items`, `statuses`,
`lifecycles`, `collections`, `subentity_kinds`, `roles`), so no vocabulary key can ever collide
with it, an unknown key fails closed, and every deselect in the spec is readable in one place —
which for a shrink operation beats scattering it across six tables. The raw `[selected]` table is
consumed and stripped by the loader before the sections are model-validated, since
`extra="forbid"` would otherwise reject it.

**The document's own top level is a closed key space on the same terms, and it is checked the same
way `[selected]`'s is** — the caller supplies the accepted key set, the engine knows nothing about what
the names mean, and an unrecognised key is a collected violation naming it. The workflow (and playbook)
override document may therefore carry only the declared section names plus `selected`. Keeping it on the
engine's violation channel rather than in the loader is deliberate: it is how the failure stays
collectable in lint's collect-all mode instead of arriving as a model error that stops the pass. This has to be stated and
implemented at the raw-mapping layer rather than left to `extra="forbid"`, because the model never
sees such a key: the loader builds each spec model from an explicit payload of named sections, so a
stray top-level key is **dropped in the gap between the parsed document and the model** and reaches no
validator at all. That is the same fail-open class as a deselect that silently does nothing — the
resulting spec is valid, it is simply not the spec the adopter wrote — and it is why a mistyped section
name (`[item.task]` for `[items.task]`) currently produces no error and no effect.

Two things depend on this being explicit rather than assumed. A mistyped or misplaced section is the
most likely large-scale override mistake there is, and it should say so instead of quietly doing
nothing. And the retired `override_base` key (§4's Drift bullet) is refused **by this rule** — the
statement that it "fails closed as an unknown key" is only true because the top-level key space is
closed here, not because a model rejects it.

**A role override's top level is deliberately not closed**, and the difference is structural rather
than an inconsistency to harmonise. A role override's top-level keys are the *fields of a role*, a set
that grows release to release, so the resolver skips unknown keys on purpose for forward
compatibility — a project override written against a newer squads keeps working on an older one. The
workflow document's top level is a fixed set of section names defined in code, which never has that
problem. Consequence worth naming: the retired key written into a *role* override is ignored rather
than refused, and the adopter learns of it from `sq check` reporting the file unstamped. That is the
fail-safe direction and nothing depends on the key, precisely because the stamp is a comment.

### 4c. One engine, two addressing conventions

The engine is shared by the workflow, playbook, and roles loaders, as EPIC-538 settled. It takes
a bundled base and an override and knows nothing about which file they came from. But the three
loaders address their overrides differently, and that difference is deliberate, not a
harmonisation debt:

- **Workflow and playbook: a single-file delta with keyed tables** (`.overrides/workflow.toml`,
  `.overrides/playbook.toml`). Each is one interdependent document — a type references a
  lifecycle which references statuses; a playbook entry references role slugs and a type name.
  Splitting a referentially coupled graph across per-key files would scatter it and make a single
  base stamp meaningless.
- **Roles: a per-slug delta file** (`.overrides/roles/<slug>.toml`), which is what ships today and
  what stays. The role catalog is a flat registry of independent entities with no cross-entity
  structure, so the filename *is* the key. One file per role is what lets `sq override
  scaffold`/`diff`/`update` work per role and each role carry its own base stamp — a project can
  be current on one role and stale on another, which a single fused file could not express.

**Deselect lives only in the workflow spec; the other two derive theirs.** This is the reason the
asymmetry costs nothing:

- The **playbook's** active type set is not independently declarable — the coverage rule already
  requires a playbook entry for exactly the spec's non-roster types, so dropping a type from the
  workflow spec drops its playbook entry as a consequence. (That consequence is not yet real:
  the playbook resolves against the bundled spec at import rather than against the active one,
  which is the same statelessness seam this depends on.)
- The **roles catalog** needs no deselect because a bundled role is a menu entry, not a roster
  member: nothing is materialised until `sq role activate`, so declining a role is simply not
  activating it. A project cannot hide an unwanted role from `sq role catalog`, which is a
  cosmetic gap with an existing remedy, and deliberately not a feature.

### 5. Where enforcement lives

All of §3 is Plane 1 — spec-load validation inside `WorkflowSpec._validate` and the loader's
collected report, before any item is read. §4's merge and its collected violations live in
`_loader.py`, in the shared engine §4c describes. The live-index cross-check
(`validate_against_index` / `validate_against_index_fail_closed`) still runs after the merge and
the deselect, so an override that drops a status live items still carry keeps failing closed with
the offending IDs listed. §5a extends what it compares.

Nothing here is checked at read time or tolerated at runtime. A spec that reaches `Service` has
already satisfied everything the engine will assume about it.

### 5a. The live-corpus cross-check compares a type's prefix and folder, not only its name

The cross-check as it stands compares each live item's **`type` and `status` names** against the
merged spec. Two more of a type's fields are load-bearing for items already written under them, and
changing either against a non-empty corpus is unsafe:

- **`prefix`** — an item's prefix is durable, carried in its frontmatter `id` and re-derived from
  that id on every read, never resolved from the spec. Re-prefixing a type therefore does not
  rename anything already written.
- **`folder`** — an item's directory is a pure function of the spec (`folder_for`). Re-foldering a
  type moves where the type *is*, not where its items are.

**Both fail through the same code path, and the failure is severe.** The single on-disk scan behind
`sq repair`, `sq check`'s index-reconciliation, and the padding bump resolves each type's directory
from the spec **and globs that type's declared prefix**. A prefix change makes the glob ask for
files that do not exist; a folder change makes the directory not exist. Either way the type's whole
corpus drops out of the scan, so `sq check` reports every one of its items as indexed-but-missing,
and a routine `repair` rebuilds the index from the empty scan and **drops them all from it**,
reporting them as missing rather than refusing. Per-item reads keep working in the interim only
because each item's path is stored — which makes the damage quiet until someone repairs, the worst
property such a failure can have. Neither field is more dangerous than the other and they get one
clause, not two.

**The rule.** For every type in the merged spec that has at least one live item, that type's
declared `prefix` and `folder` must equal the values its existing items were written under. A
mismatch fails closed, listing the offending item IDs, in the shape and wording the cross-check
already uses for a dropped type or status.

Three properties make this the smallest possible statement of it:

- **It stores nothing new.** Both expected values are recoverable from the items themselves — the
  prefix from each item's id, the directory from each item's stored path, which is itself
  recomputed from the scan on repair. Declaring a per-type prefix/folder in the index would be a
  second source of truth for something already on disk, which the index is forbidden to hold.
- **It belongs on the cross-check plane, not the floor.** A spec that re-prefixes a type is
  perfectly valid in the abstract; it is wrong only against *this* squad's corpus. So it runs at
  §4b's step 5 with the rest of the cross-check — after the merge, the deselect, and `_validate` —
  which also means it collects in `sq workflow lint` for free and fails fast for `open_service`,
  with no new mode.
- **An empty corpus is unaffected.** A type with no items re-prefixes and re-folders freely, which
  is the case the capability was actually asked for: choosing your vocabulary when you adopt
  squads, or for a type you have not started using.

**What the refusal may say, and what it may not.** No shipped verb realigns an existing corpus to a
changed prefix or folder. The two performable ways forward are to **revert that field in the
override**, or to make the change **while the type has no items**; the message names those and
nothing else. It must not name a migration, because there is none — under the standing rule that a
refusal may never assert a remedy no command performs, an unperformable remedy is worse than an
honest dead end. If an alignment verb lands later, this clause is restated to name it; until then
the message says plainly that the change cannot be applied to items already written.

## Alternatives considered

**Lock the roster lifecycle: keep `_RESERVED_FLOOR` and refuse any roster override.** The
strongest argument for it is real: it is free, it is already implemented, and it makes every
roster-facing binding trivially correct — the engine can say `Active` because `Active` is
guaranteed to exist and to mean what it means. It loses on two counts. First, it is a
prohibition standing in for a check the engine needs anyway: the roster is not the only place
a loose lifecycle hurts, and a project that renames `Archived` to `Retired` breaks nothing the
engine cannot verify. Second, it makes the reserved surface a matter of history rather than
necessity — three status names are frozen because three call sites were written before the
role catalog existed, not because the engine cannot express itself without them. Locking is
cheaper to ship and more expensive to keep: every future capability inherits the temptation to
name a literal, because the floor tells it a name is safe.

**Require the role names `active`, `retired`, and `pending` in every spec.** Simple, and it
matches how the roster reads today. Rejected: it moves the lock from the status axis to the
role axis without reducing it, and no role name is needed at all — being-on-offer comes through
§2a's `live` flag, retirement and default-hiding through `settled`/`hidden`, and the create-at
target through the lifecycle's `initial`. All four are properties, not names.

**Let the spec declare the mapping in a `[capabilities]` table** (e.g.
`roster.live_status = "Live"`). Rejected: it stores what is already derivable. The role
assignment on each status *is* the mapping; a second declaration of it can disagree with the
first, and then the engine has two answers and no rule for which wins.

**Replace a shadowed table wholesale instead of merging recursively.** Simpler to implement and
to explain. Rejected because the realistic override is narrow — rebind one lifecycle, relabel
one status — and wholesale replacement forces the adopter to copy every other field of the
built-in entry, which then silently stops tracking the bundled spec on upgrade. That is the
drift problem the per-file override design already learned once. The same argument is why arrays
get a splat-ref escape (§4a) rather than being left as pure leaves: a bundled list an adopter has
to copy in order to extend is a bundled list that stops improving.

**Express removal by shadowing a key with an empty or sentinel value** instead of a `selected`
list — `[items.guide]` with some `drop = true` marker, say. Rejected: it makes absence a property
of the thing being removed, so the reader of a section has to inspect every entry to learn what
the spec actually contains, and it gives a type two contradictory states to hold (declared, and
declared-as-absent). `selected` states the surviving set in one place, which is both readable and
trivially diffable against the bundled set.

**Use non-settled as the materialisation axis instead of adding a flag.** The most attractive
option, because it adds nothing: the role object already says whether a status is at rest, and
"not at rest" sounds like "live". Rejected on the evidence — four bundled roles are non-settled
(`active`, `attention`, `blocked`, `pending`), so an adopter's `Suspended` on a `blocked` role or
`Provisional` on `pending` would be read as live and written into the host's config. That is
backwards in the one direction that matters, and no re-assignment of the bundled roles fixes it
without making "blocked" mean "not present", which it does not.

**Name the flag `materialised`.** Rejected: it names the backend-side effect rather than the state,
on a field that lives in vocabulary every item type shares, so it reads as nonsense on a work
status and it forecloses the same flag serving the participation gate. `live` names the meaning
and lets materialisation be the consequence.

**Keep R1's `exactly one` and let the create path use it.** Rejected because it is redundant — the
lifecycle's `initial` already names a create-at status, validated by checks that already exist, so
uniqueness was securing something the spec supplied all along. Keeping it would also cost the
parked-then-activated capability for no gain, since a non-live `initial` is only expressible when
more than the single live status is permitted.

**A general expression language in the override instead of splat-refs.** Rejected on the
standing no-`eval` line: splat-refs are a path splice with a closed grammar, a single resolution
pass, and no user-supplied code. Anything richer would put an evaluator in the load path of every
`sq` invocation and would make a malformed override a security question rather than a validation
one.

**Tolerate a loose spec at runtime instead of refusing it at load** (fall back to a default
when a needed role is absent). Rejected: the fallback would be invisible, would differ per
call site, and for the roster would mean writing agent-host config from a guess. The one
existing runtime fallback — a role-less status resolving to `pending` — is deliberately
fail-safe-*visible*, and even that requires the fallback role to be declared.

## Consequences

- The reserved surface shrinks to what is structurally necessary: three type **keys** and
  their fixed `category`. No status name is reserved. A project may name its roster lifecycle
  states anything, in any language, with any number of retired-side states.
- Every capability that needs lifecycle semantics now has one place to say so and one place to
  be checked. The next such capability adds a clause to §3's floor rather than a literal to a
  call site.
- **A parked-then-activated roster entry becomes declarable, with no special casing anywhere.**
  A project that declares its roster lifecycle's `initial` status *non-live* gets exactly that:
  `sq role activate <slug>` (or `skill add`, or `operator add`) creates the entry at `initial`,
  nothing is materialised, and a later transition to a live status is what puts the agent in
  front of the host. The engine needs no branch for it — the create path reads `initial` and the
  projection reads the flag, and the two simply disagree for a while. This is the capability the
  bundled two-state lifecycle no longer has, now available to anyone who wants it without the
  bundled spec carrying a state it never used.
- **One verb reads oddly under that choice.** `sq role activate` means "add this bundled role to
  my roster", and with a non-live `initial` it adds without activating. The wart is pre-existing
  and this decision does not rename anything; it is worth knowing before an adopter reads it as a
  bug.
- **Cost to adopters: a workflow override can now be wrong in a new way.** Shadowing a
  built-in lifecycle can violate R1/R2 or strand live items, and the failure is a hard stop at
  load — `sq` refuses to run until the override is fixed. `sq workflow lint` reports every
  violation at once with a fix hint, and the failure is at load rather than mid-command, but
  the sharp edge is real and is the direct price of the freedom.
- **Cost to adopters: shadowing creates upgrade work that adding never did.** A shadowed
  built-in stops tracking the bundled spec. The `override-base` stamp makes the drift visible
  instead of silent, which is the most that can be done — `sq override diff` and the manual
  merge become part of the adopter's upgrade path for the workflow spec too.
- No existing squad breaks. Every squad on disk carries either no workflow override or an
  additive one, and both remain valid: the floor's universal clauses are already satisfied by
  the bundled machines, and R1/R2 hold for the bundled roster lifecycle
  (its `Active` status is live and is the lifecycle's `initial`, satisfying R1 and vacating R1′;
  its retired status is settled, non-live, and reachable from the live one, satisfying R2). No schema bump and no migration runner is owed.
- `docs/stability.md` currently freezes "workflow overrides are **additive-only**" and lists
  the three reserved statuses as part of the override contract. Both statements become wrong
  when this lands and need a rewrite before 1.0, alongside the roster-lifecycle grammar.
- **Splat-refs add a resolution pass every load must run, and a new class of override error.**
  Three failure modes an adopter did not have before — a dangling path, a type mismatch, a
  surviving unparsed token — each of which fails the whole load. The mitigation is that all three
  are load-time and collected, and the last one exists precisely so a typo cannot become silent
  data. The cost is real: the override file is no longer purely declarative, and reading one now
  requires knowing the bundled base it composes against.
- **Deselect makes a spec harder to read in exchange for making it possible to shrink.** What a
  project's vocabulary actually *is* becomes a function of the bundled set, the override's
  declarations, and the `selected` lists together. `sq workflow lint` and the type catalog surface
  are the only honest answer to "what types do I have"; hand-reading the override file is not.
- **The playbook cannot honour its half of this until it resolves per-request.** It is an
  import-time singleton over the bundled spec, so a `.overrides/playbook.toml` merged by the
  shared engine would still be composed against, and validated for coverage against, the bundled
  type set rather than the project's. The engine and the fourth override kind are separable work,
  but the playbook override is not correct without the statelessness change beneath it.
- **The `live` flag is a fourth thing a spec author must understand about a status role**, and
  the one whose default they are most likely to get wrong by omission — a project that declares a
  custom roster role and forgets `live = true` gets a spec that fails R1 at load rather than a
  squad that quietly offers nothing, which is the right failure but still a failure they have to
  read an error to understand.
- **Relaxing R1 to "at least one" admits a spec with several live statuses**, which nothing in
  the engine needs but nothing forbids either. Two live statuses mean two ways to be on offer
  — a plausible adopter design (`Live` and `Trialling`, say) that the projection handles without
  caring, and that no accessor has to disambiguate because `live_initial` only has to pick when
  `initial` itself is non-live. The cost is that "which status does a live entry hold" stops
  having a single answer, so anything reporting on the roster must show the status rather than a
  yes/no.
- **Per-loader addressing stays split, which is a documentation cost.** An adopter learns two
  conventions — one file per role, one file for everything else — and the reason (flat registry
  versus coupled document) has to be stated wherever the override layout is documented, or it
  reads as an inconsistency.
- **Re-prefixing and re-foldering are adoption-time freedoms, not ongoing ones** (§5a). A project
  chooses its prefixes and folders before it has items of that type, or reverts the change; there is
  no way to carry an existing corpus across either. That is a real limit on the "shadow any field"
  promise, and it is stated as a limit rather than hidden behind a refusal that hints at a migration.
  It also affects the roster in practice more than any other category, because a squad has role,
  skill and operator items from the moment it is initialised — the roster's prefix and folder are
  mergeable in the same sense every other type's are, and equally unusable once entries exist.
- **The honest dead end names a piece of work rather than concealing one.** An alignment verb — walk
  the type's files, rewrite each item's id, rename each file, rewrite incoming ref edges, rebuild the
  index — is a composition of mechanics squads already ships in two places: the padding bump already
  walks and renames every item file and then repairs, and the retype verb already rewrites one item's
  id, moves its file, and rewrites the edges pointing at it, atomically. So the gap is small and
  known, not open-ended. It stays a gap until someone builds it, and no message pretends otherwise.
- The forward door this leaves open: the same floor mechanism can carry per-capability
  requirements for future non-roster capabilities (a velocity capability needing a declared
  in-progress role, say) without another decision on the mechanism itself.

## Amendment note

**2026-07-30 — reconciled with EPIC-538's settled override-engine design.** As first written,
this decision replaced the additive-only rule with a merge of its own devising ("per-field, with
collection-valued fields replaced wholesale") and cited no prior design. EPIC-538 had already
settled one: a single shared override engine — deep recursive merge at leaf granularity,
`selected`-based deselect, eval-free splat-refs — reused by the workflow, playbook, and roles
loaders, plus the playbook as a fourth override kind. An implementer following the earlier text
alone would have built a narrower engine than the one already designed.

What changed: §4's merge is restated in EPIC-538's terms (recursive at leaf granularity, arrays as
leaves) and now cites it as settled input; §4a absorbs splat-refs, including `$(self)`/`$(*self)`,
the bundled-base-only resolution that keeps the merge order-independent, and the fail-closed rules;
§4b absorbs `selected`-based deselect and resolves it against this decision's floor as a single
ordering rule rather than a second rulebook; §4c rules on the per-loader addressing split and on
where deselect belongs. Two corrections to the absorbed design are recorded in place: the deselect
lists are lifted into one top-level table because a per-section `active` key does not parse against
the bundled `[roles.active]`, and a splatted array of tables must use TOML's inline-array
form. The one deliberate contradiction — a roster type's non-`category` fields are field-mergeable,
against both ADR-541's floor and EPIC-538's roster-locked invariant — is stated in §4 with its
reason.

What did not change: §1's rule, §2's role-keyed lookups and the retirement of the status literals,
§3's universal and roster floors including R1/R2, and §5's enforcement plane. Those are this
decision's own contribution and EPIC-538 does not speak to them.

**2026-07-30 — the materialisation axis becomes a flag, `initial` becomes the create-at target,
and the deselect mechanism is renamed.** Three rulings, each of which retires something this
decision previously asserted rather than sitting beside it.

- **§2a is new: `live`, a fourth boolean on the status role.** The materialisation axis was
  keyed off the role literally named `active`, which is the name-locking §1 exists to forbid, one
  layer up. Non-settled was checked as a substitute and rejected on the evidence (four bundled
  roles are non-settled, so a `blocked`-role `Suspended` would read as live). §2's accessors are
  reshaped onto the flag: `role_statuses`/`sole_role_status` become
  `live_statuses`/`live_initial`, and **no role-name-keyed status accessor survives**,
  because after this nothing needs one.
- **§3's R1 relaxes from `exactly one` live status to `at least one`, and the uniqueness
  rationale is withdrawn rather than qualified.** As first written, R1 required exactly one because
  the create path needed an unambiguous write target. The lifecycle already declares one —
  `initial` — and the existing checks already validate it. R1′ keeps only the sliver `initial`
  cannot cover: when `initial` is itself non-live, exactly one status must be live, so
  scaffolding can still create an entry already on offer. R2 is restated against the flag rather
  than the role name.
- **§4b's deselect mechanism is `selected`, in one top-level table.** The placement fix recorded in
  the previous amendment stands on the parse collision; the word changes because `active` as a
  deselect key beside `active` as a status-role name was confusing independently of that, and
  because the list is the surviving set, which is what `selected` says.

The call-site table in §2 is rewritten accordingly, and it is no longer a substitution table: the
nine sites split three ways, and one of the three does not follow the general rule. Squads'
own system-skill seeding must create *live*, not merely create at `initial`, because a generated
role entry preloads a skill by slug regardless of that skill's status — seeding at a non-live
`initial` would leave a clean `sq init` with role entries preloading skills that were never
materialised.

**2026-07-30 — the flag is renamed `offered` → `live`.** `offered` named the flag correctly but
too narrowly: it reads as roster-projection vocabulary specifically, when the flag actually sits
on the status-role object every item type's statuses resolve through. `live` generalises — a
status declares that entities resting there are the current, in-force instance of themselves,
and each capability (the roster projection today, a future one tomorrow) decides what that
licenses.

The rename is disambiguation, not just substitution, because "live" already had a looser,
established meaning in this codebase: not-settled, or simply "in use"/"currently the real one"
(a live squad, a live index, a live spec). §2a's flag is deliberately **narrower** than
not-settled — three bundled roles (`pending`, `attention`, `blocked`) are themselves non-settled
without being live, exactly the evidence this decision already used once to reject non-settled
as a substitute (§"Use non-settled as the materialisation axis instead of adding a flag"). That
rejection reads, if anything, more pointed now that the rejected alternative and the adopted flag
share a name: rejecting "non-settled" as the axis was never about the word, it was about the
four-non-settled-roles evidence, and that evidence is restated unchanged. Every other loose
"live" in this document and in `src/` was checked against the same test — does it mean "not
settled", or could a reader mistake it for this flag — and left alone where it means the plain
verb or "in use" (e.g. "the live spec", "live items", "the live-index cross-check": all mean
"the currently-active one", never this flag) and reworded the one place it did not (§3's R2 note,
which used "live" for "not at rest" beside "unoffered" for the flag — now "non-live but
non-settled").

§2's accessors are renamed `offered_statuses`/`offered_initial` → `live_statuses`/`live_initial`;
§2a's field is renamed `offered` → `live`; every derived wording (R1/R1′/R2, the call-site table,
the bundled TOML) restates against `live`/`non-live` in place of `offered`/`unoffered`. No
semantics move: the flag's meaning, its default, R1/R1′/R2, and the nine call-site verdicts in §2
are exactly as decided above, under a new name.

**2026-07-31 — the roster field axis is settled at both ends, and the provenance carrier is the
comment stamp.** Two clarifications to §4, neither changing a position this decision took.

- **The roster field-merge override is now recorded reciprocally, and the type axis is drawn
  exactly.** §4's prohibition bullet already ruled that a roster type's non-`category` fields are
  field-mergeable; what it lacked was the other end of the override, so the earlier statement it
  overrides was still readable as live. §4 now states the evidence for the narrower claim (the engine
  binds the roster by type key and by `category`; it binds nothing to a roster type's prefix or
  folder), and ADR-541 carries a matching dated note narrowing its floor section, category bullet,
  Plane-1 rule list, and `meta_kind` consequence in place. The line, spelled once for the
  implementer: **locked** — the three type keys must exist, may not be added to, dropped (including
  via `selected`), or renamed, and `category` may not move a type into or out of `roster`;
  **mergeable under the full floor** — `lifecycle`, prefix, folder, labels, order, and every other
  non-identity field. This settles the one open check in the loader's roster floor.

  ADR-541 is not retired by this: only one of its clauses is overridden, and it remains the sole
  authority on the category taxonomy and the validator model. Retiring a whole decision for a
  clause-level reversal would falsely retire everything else it says. **The general shape, since this
  is the first recorded instance:** a whole-decision replacement gets a `supersedes` edge and moves
  the replaced decision to `Superseded`, whose body then stands as history; a clause-level reversal
  leaves both decisions Accepted, states the override and its exact scope in the newer, narrows the
  reversed clause **in place** in the older with a dated note pointing forward, and links them with a
  `related` edge. What must never survive either shape is a body that still asserts what a later
  Accepted decision reversed.

- **One provenance carrier: the `# squads:override-base:<version>` comment.** §4's Drift bullet as
  first written named a top-level `override_base` spec key, which would have been a second carrier
  beside the comment stamp the role and template overrides already use and `sq override` already
  writes, reads, and re-stamps. The key is not introduced. The reasons are recorded in place in §4:
  re-stamping must not rewrite the adopter's document (a comment substitution preserves every other
  byte; rewriting a key needs a round-tripping serializer that reformats and drops comments); one
  stamp grammar across every override kind, which this decision already asserted for the playbook;
  the loader gains nothing from a key, since it holds the file text before it parses it, and a key
  would need stripping before model validation exactly as `[selected]` does; and two carriers for one
  fact disagree. An override that writes `override_base` as a key is refused as an unknown top-level
  key — the right outcome, since a mistyped provenance declaration must not read as silently absent.
  `[selected]` stays the only top-level table the loader consumes and strips. (What makes that refusal
  actually happen is stated in §4b: see the 2026-07-31 note on the closed top-level key space, without
  which the key is dropped before any validator sees it.)

  §4 also pins what "must carry" means, which was not stated: unstamped **and** shadowing is an
  error-level `sq check` / `sq workflow lint` finding, an older stamp keeps the drift warning, an
  add-only override needs nothing — and none of the three is a load-time refusal, because absent
  provenance does not change whether the merged spec satisfies the floor.

**2026-07-31 — the live-corpus cross-check gains `prefix` and `folder` (new §5a).** This decision
made every non-roster type's prefix and folder mergeable, and then made the roster's mergeable too,
without saying what happens when the type already has items. The answer was not "nothing": an item's
prefix is durable in its frontmatter id while its directory is resolved from the spec, and the single
on-disk scan behind repair and index-reconciliation resolves the directory from the spec *and* globs
the declared prefix — so changing either field silently blinds the scan to that type's whole corpus,
after which a routine repair drops every one of its items from the index. §5a adds the missing
clause: for any type with at least one live item, the declared prefix and folder must match what its
items were written under, checked on the cross-check plane, listing the offending IDs, storing
nothing new (both expected values are recoverable from the items). An empty corpus is unaffected, so
the capability survives for the case it was asked for — choosing vocabulary at adoption, or for a
type not yet in use.

Two things are recorded rather than smoothed over. The refusal names only the two performable ways
forward (revert the field, or change it while the type has no items) and deliberately names no
migration, because none is shipped; asserting one would breach the standing rule against remedies no
command performs. And the resulting limit is stated in the consequences as a limit: re-prefixing and
re-foldering are adoption-time freedoms, which bites the roster hardest, since a squad has roster
items from initialisation. The alignment verb that would lift the limit is a composition of shipped
mechanics, not an unknown, which is why the gap can be named precisely while staying a gap.

This is an addition to the enforcement plane, not a reversal of anything above: §3's floor, §4's
merge, and the roster ruling all stand exactly as decided.

**2026-07-31 — §4a's failure set is stated exactly, token detection narrows to a leading `$(`, and
§4b closes the document's top-level key space.** Three corrections, each closing a place where this
decision asserted something the engine either could not do or would not reach.

- **The type-mismatch criterion loses its second half.** §4a said a splat-ref fails closed on "a type
  mismatch (a spread into a non-list, **a table where a scalar is due**)". The first clause is a
  property of the spread operator and stands; the second is schema knowledge the engine deliberately
  does not hold, and its only schema-free reading — compare against the base's shape at the
  destination — would make a splice **stricter than the literal it abbreviates**, since a hand-written
  leaf may replace its counterpart with a different shape. §4a now states the governing rule (a
  splat-ref is an abbreviation held to the same standard as its expansion), enumerates the four
  failures that follow from it, and withdraws the second clause rather than reinterpreting it. Shape
  stays with the models, which reject exactly this with a per-field error. The one real cost — a shape
  error is not a collected violation, so `sq workflow lint` reports it alone — is recorded as belonging
  to a separate question, whether the loader translates a `ValidationError` into per-field findings;
  that fixes the whole class rather than privileging the splice-caused sliver, and it is not folded
  into the grammar.
- **A value is in token territory only if it *begins* with an unescaped `$(`.** The detection
  predicate was wider than the recognition rule it enforces — a token has always had to be the entire
  string value, while the check fired on `$(` anywhere. The narrowing matters because the sigil *is*
  POSIX command substitution and one of the three documents this engine serves carries command lines:
  under the wide predicate an ordinary shell snippet is a load failure explained in terms of a grammar
  its author never used, and every tool that writes a bundled string into an override file would owe a
  standing escape duty that also makes the written file differ from its bundled source. Narrowing
  removes the duty rather than distributing it, with no change to the token syntax. Two accepted
  consequences are recorded in place: an interpolation attempt stays literal, and since only a leading
  `$(` needs escaping the writers' duty is vacuous while no bundled string value begins `$(` — which
  is worth a cheap standing guard over the bundled documents rather than a rule to remember. §4a also
  states that the grammar and the escape are value-only, keys being vocabulary that is never resolved.
- **The override document's top level is a closed key space, enforced at the raw-mapping layer.** The
  claim that a retired `override_base` key "fails closed as an unknown key" rested on `extra="forbid"`
  being reached, and it is not: each loader builds its spec model from an explicit payload of named
  sections, so an unrecognised top-level key is dropped in the gap between the parsed document and the
  model and reaches no validator — as does a mistyped section name, silently and with no effect. §4b
  now closes that key space explicitly, on the same terms it already closed `[selected]`'s. A role
  override's top level stays deliberately open, because its keys are a role's fields and that set grows
  between releases, so forward-compatible leniency is right there and a closed section-name set is
  right here; the consequence, that the retired key is ignored rather than refused in a role override
  and surfaces as an unstamped file, is stated rather than smoothed.

None of the three changes a position: §1's rule, §3's floor, §4's merge and roster ruling, §4b's
deselect and §5/§5a's enforcement planes all stand as decided.

**2026-07-31 — §4a's path grammar anchors on TOML bare keys, `self` is defined through list nesting,
and the walk carries a declared depth bound.** Three clauses §4a left undefined, each of which had a
task body either silent or stating a contract the grammar did not meet.

- **A path segment is a TOML bare key** (`A-Za-z0-9_-`), replacing an identifier-shaped path that
  excluded hyphens and leading digits while accepting non-ASCII everywhere except the first character.
  Anchoring on TOML's own key definition settles all three at once — hyphenated and digit-leading keys
  become addressable, and a non-ASCII key becomes *correctly* unaddressable as a quoted key rather
  than by accident of a character class. The reason it must be widened rather than documented as a
  restriction is the abbreviation rule: a value the adopter may write literally has to stay
  expressible as a reference, and a grammar narrower than the vocabulary the spec may declare
  silently withdraws that for a class of legal names.

  A key needing TOML quotes stays unaddressable — `.` is the path delimiter, so a dotted key is
  irreducibly ambiguous, and a quoted-segment sub-grammar would be a second nested syntax for a case
  no document has. What makes that cost nothing is a fact worth recording plainly, because two
  readings of this exposure had it the wrong way round: **resolution is base-only, so a path can only
  ever address a key of the bundled document.** An adopter's own vocabulary is never a path target —
  a brand-new key dangles by design however it is spelled, and a hyphenated custom type addresses
  bundled paths from inside itself perfectly well, because the hyphen sits in the destination, not in
  the path. The constraint therefore binds squads' own documents, discharged by a standing guard that
  every bundled key is a TOML bare key, folded into the same scan that keeps a bundled string value
  from beginning `$(`. There is nothing here for an adopter to learn because there is nothing they can
  reach.

- **`self` means the nearest enclosing keyed path, at any list depth**, since a list index has no
  dotted name to contribute. Definitional rather than a new rule — it is what "the key currently
  being written" already meant — and stated because nesting invites the other reading. The three
  behaviours that follow are intended: two `self` tokens at different list depths under one key
  resolve alike; a nested `$(*self)` spreads the key's list into the sub-list, permitted because the
  destination's shape is the models' plane and not the engine's, exactly as the abbreviation rule
  decides everywhere else; and spreading an *empty* base list adds nothing, which is a value the base
  holds and so is distinct from a missing key, which dangles. Compose-only also permits one base list
  to be spread twice.

- **The walk carries a declared depth bound**, exceeded → a refusal naming the dotted path. The
  alternative was to qualify the no-traceback contract, and that is the wrong direction: the promise
  is about what an invocation does to the person running it, a wall of Python satisfies neither
  branch, the inputs are adopter-authored by design, and the TOML parser accepts documents far deeper
  than the walk survives — a single legal line of dotted keys reaches it — so no upstream layer can
  guard it. Weakening a stated invariant to match code that could cheaply satisfy it is how
  invariants stop meaning anything. The bound is specified by its two properties rather than as a
  number (far above any hand-authored document, far below the interpreter's headroom with room for
  the per-level copy), binds both the resolution and merge walks, and is checked before recursing or
  copying, since a deep untouched base fails inside the copy rather than in the engine's own frame.

No position above changes; all three fill gaps rather than revising rulings.

**2026-07-31 — a token-shaped key is refused, and the sentence that said otherwise is replaced.**
The earlier wording, *"the token grammar and the escape apply to values, not keys… a key is never
resolved, scanned, or unescaped"*, was not merely ambiguous: it bundled one correct claim with one
wrong one and left the operative case unstated. "Never resolved" is right — there is no
splice-into-a-key operation, because a path addresses a value and a value is not a key. "Never
unescaped" was wrong. And "refused" — which is neither of those — was the case the sentence needed to
settle and did not, so it could be and was read both ways.

The rule now reads in one place, symmetrically. **The sigil is reserved in every string position,
keys as well as values, and token territory is one predicate in both: a string begins with an
unescaped `$(`.** In a value, territory means resolve-or-refuse-as-malformed. In a key, territory
means **refuse** — never pass through, never substitute. `$$(` unescapes in *both* positions, and a
string that merely contains the sigil after its first character is data in both.

The escape is what keeps this from being the engine legislating vocabulary, which it must not do: a
project wanting a key spelled `$(items.task)` writes `$$(items.task)` and gets it, so the requirement
is unambiguous spelling in a document where the sigil is reserved, not a restriction on which names
exist. That is also the line between this refusal and the one refused for splices — there, holding a
splat-ref to the base's shape would have left a value expressible literally but inexpressible as a
reference, with no escape to recover it. **Whether the adopter retains a way to say the thing** is the
test, and it separates the two cases cleanly.

The other half of the reasoning is why "leave it to the models" is not available here, as it is for
shape. For a value the models are a genuine backstop — typed fields, extras forbidden. For a key they
are deliberately not, because a section's keys *are* the open vocabulary: a spec declaring an item type
literally named `$(items.task)` loads clean, takes a prefix-map entry, and resolves a folder. Nothing
downstream is positioned to notice, so the engine's refusal is the only thing between a typo and a
minted vocabulary entry — the surviving-token rationale at its strongest rather than its weakest. It
is also what keeps the verdict from depending on depth, since an unrecognised key at the document's top
level already fails closed under §4b.

**2026-07-31 — §2's Guard names the bundled spec package by its current path, and the exemption's
premise is written down.** The scan's exempt location is the package holding the bundled documents,
now `_specs/`; the clause named the path it carried when this decision was written, which left an
Accepted decision and its own enforcement disagreeing about where the exemption applies. One path
string — the rule, the migration carve-out, and everything §2 decides are untouched, and both
migration runners still hold their frozen `_STATUS_ACTIVE` exactly as the carve-out requires.

The clause also now states what the exemption rests on. The scan exempts that package **by
directory**, which is the right shape — its sibling guards do the same, and a filename list would go
stale the moment a fourth document lands — but it means any `.py` placed there is silently outside
the guard. Under the older name that read as self-evidently harmless; a package named for specs reads
more like a code layer, so the premise is now carried by convention alone. Written down, it is a
standing property instead: the package holds the bundled documents and a docstring-only marker, and
no logic moves there — anything that reads or interprets those documents belongs to the loader that
owns it, where the scan can still see it. Not a defect and not worth a second guard; worth a sentence,
because an exemption whose justification is only implied is one an unrelated change can quietly
invalidate.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-30T08:42:46Z] Robert Architect:
  - [amendment — 2026-07-30] Reconciled with EPIC-538's settled override-engine design, which neither the brief nor I had found. As first written this decision replaced additive-only with a merge of its own devising and cited no prior design; EPIC-538 had already settled one, and an implementer following the earlier text would have built a narrower engine.
  - Absorbed: deep recursive merge at leaf granularity (§4, restated in EPIC-538's terms — 'per-field' was recursion seen one level down, and the spec nests); arrays as leaves with splat-refs as the opt-in (§4a) including $(self)/$(*self), bundled-base-only resolution, compose-only, and the fail-closed rules; active-based deselect (§4b); the playbook as the fourth override kind, inheriting the override_base stamp and the sq override verbs.
  - The active/floor interaction resolved as an ORDERING rule, not a second rulebook: resolve splats against the bundled base, deep-merge, apply active, then run the whole floor, then the live-index cross-check. Every unsafe drop is then caught by a check on the resulting spec — dropping the last active-role status fails R1 because R1 counts on the post-deselect spec; a status still named by a surviving lifecycle fails _check_lifecycle_statuses; a status still held by live items fails validate_against_index_fail_closed. active owes no validation of its own, only provenance in the message so an adopter can see their own active line caused the violation.
  - Two corrections to the absorbed design, both verified against tomllib rather than assumed. (1) A per-section top-level 'active' key DOES NOT PARSE: the bundled spec declares [roles.active], so [roles] cannot also carry an active key — tomllib rejects the file with "Cannot declare ('roles','active') twice". Lifted into one top-level [active] table keyed by section name; the key space is closed and code-defined so no vocabulary can collide, and every deselect reads in one place. The word active is kept, only its position moves. (2) A splatted array of tables must use TOML's inline-array form (roles = ["$(*self)", {…}]) — the [[types.t.roles]] header form has no slot for a token. Heterogeneous arrays are valid TOML 1.0 and tomllib accepts the mixed list, so the inline form works.
  - Also extended active to the roles (status-role catalog) section — EPIC-538's five-section list predates that catalog, so this is completion not change; and ruled that deselect belongs to the workflow spec ONLY: the playbook's active type set is derived from the coverage rule, and the roles catalog needs none because a bundled role is a menu entry that nothing materialises until sq role activate.
  - Ruled on per-loader granularity: one engine, two addressing conventions, deliberately. Single-file keyed-table deltas for workflow and playbook (each is one referentially coupled document; splitting it per key would scatter the graph and make a single base stamp meaningless), per-slug files for roles (a flat registry of independent entities, so the filename is the key — which is what lets sq override diff/update work per role and each role carry its own stamp).
  - One deliberate contradiction stated in place rather than slid past: a roster type's non-category fields (its lifecycle above all) ARE field-mergeable, against both ADR-541's type-axis floor and EPIC-538's roster-locked invariant. Roster membership and the type keys stay closed. Reason is the constrain-don't-lock direction, which postdates both; the safety the lock bought is bought instead by §3's floor. Supersedes that one invariant clause and nothing else.
  - @manager amendment note added to the body; status left Accepted, nothing committed.
- [2026-07-30T09:38:06Z] Pierre Chat:
  - Confirmed on the playbook: the bundled playbook stays a module-level immutable, and the merged (override-applied) playbook lives in the request context. Same split the workflow spec already uses — bundled base cached as code, per-squad resolution per request. The playbook override cannot ship before that seam exists.
- [2026-07-30T09:52:05Z] Pierre Chat:
  - Rename the deselect mechanism from 'active' to 'selected': one top-level [selected] table with a sub-key per section (items, statuses, lifecycles, collections, subentity_kinds, roles). Besides the parse collision, 'active' as a deselect key sitting beside 'active' as a status-role name was confusing on its own.
  - On the materialisation axis: do not key it off a role name. Check first whether non-settled suffices — it does not, since attention, blocked and pending are all non-settled, so a Suspended or Provisional roster status would be treated as offered. It needs its own boolean on the status role object, alongside settled and hidden.
  - And the create-at write target needs neither a flag nor a name: the lifecycle already declares initial (agent lifecycle: initial = 'Active'). Use it. R1's 'exactly one' was justified by giving the create path an unambiguous target, so it relaxes to 'at least one' — which also lets an adopter declare an unflagged initial status and get a parked-then-activated entry with no special casing.
- [2026-07-30T10:01:22Z] Robert Architect:
  - [amendment — 2026-07-30] Folded in op-pierre's three rulings. New §2a defines the offered flag; §3's R1 relaxes to at-least-one with a new R1'; §4b's deselect is renamed selected; §2's call-site table rewritten. Second amendment note added to the body.
  - Flag name: offered, not materialised. materialised names the backend-side effect on a field that lives in vocabulary every item type shares — it reads as nonsense on a work status and forecloses the same flag serving the participation gate. offered names what the state means, makes materialisation the consequence (right causal direction), and matches the grammar of settled/hidden. Defaults false: wrongly offering an entry writes an agent into a host's config, which is worse than wrongly withholding one — the mirror of why hidden defaults false.
  - R1 is now 'at least one offered status'. R1' is new and narrow: if the lifecycle's initial is not offered, exactly one status must be offered — the only sliver initial cannot cover, needed so scaffolding can create an entry already on offer. R2 restated against the flag: at least one settled, unoffered status reachable from an offered one. The old exactly-one rationale is withdrawn in place, not left standing.
  - Per-call-site verdict on TASK-699's nine converted sites, checked in the code. The four _services/_roster.py creates want initial — and better than expected: create() already defaults status to spec.initial_status(item_type) at _base.py:460, so those four should simply DROP the status= argument. The _cli/_role.py tick wants the flag predicate (offered_statuses) and its column header should stop saying Active. The four _services/_maintenance.py seed sites want NEITHER: they are squads scaffolding its own system skills, and a generated role entry preloads a skill by slug regardless of that skill's status, so seeding at an unoffered initial would leave a clean sq init with every role entry preloading three never-materialised skills — the exact state TASK-700's validator is being written to report, manufactured by squads. They need offered_initial(), which is what R1' makes total.
  - Consequence for TASK-700/701/702's implementers: after this, NO role-name-keyed status accessor has a caller. role_statuses and sole_role_status (both landed by TASK-699) should be reshaped into offered_statuses and offered_initial, not kept alongside them — otherwise the codebase gains two dead public accessors for the dead-code scan to flag.
  - All three rulings hold. The only correction is the seeding case above, which is a gap in ruling 3's scope rather than an error in it. Verified separately: selected collides with nothing in the bundled spec, and adding offered to RoleSpec is a spec-format change only — neither the role name nor its flags appear in item frontmatter or the index, so no schema bump and no migration, per the same reasoning ADR-604 used.
  - @manager both ADRs left Accepted with dated amendment notes; sq check clean, nothing committed.
- [2026-07-30T15:07:10Z] Pierre Chat:
  - Rename the flag from 'offered' to 'live'. 'offered' is too specific: it describes the roster's backend projection, but the flag sits on the status-role object that every item type's statuses resolve through, so the name has to read sensibly for any lifecycle. 'live' generalises — a status declares that entities resting there are the current, in-force instance of themselves, and each capability decides what that licenses; the roster projection is only the first consumer.
  - The rename must also disambiguate the word, or it reproduces the problem it fixes: 'live' is already used loosely in about 67 places in src/ to mean not-settled, and the flag is deliberately narrower than that — pending, attention and blocked stay non-settled without being live. Define it precisely where it is declared and clean the loose prose uses in the same pass.
- [2026-07-30T15:44:24Z] Elias Python:
  - Renamed the flag offered -> live across src/, tests/, docs/, CHANGELOG, and the VS Code client, per op-pierre's ruling above.
  - Both ADRs stay Accepted; each got a new dated amendment note in the body recording the rename (no semantics changed).
  - Disambiguation pass over 'live' in src/: kept the existing loose uses that mean the plain verb or 'in use' (a live squad, the live spec, live items) since they cannot be misread as the flag; reworded the one spot in _workflow/_models.py's R2 docstring that used 'live' for 'not at rest' next to 'offered' for the flag (now reads 'non-live but non-settled').
- [2026-07-31T09:56:21Z] Pierre Chat:
  - Deferred, for a later increment: 'role' means two different things and it is confusing. The agent role (sq role, the roster type) and the status role (the semantic object carrying settled/hidden/live) share the word throughout.
  - The collision is structural, not only prose: two classes are both named RoleSpec — _roles/_models.py:10 for the agent kind and _workflow/_models.py:356 for the status kind — alongside RoleDef for the agent kind, [roles.*] in workflow.toml meaning status roles, _roles/_catalog.py meaning agent roles, and role_for(status) returning the status kind. Renaming one axis is a vocabulary decision touching the spec format, so it wants its own decision rather than riding a fix task.
- [2026-07-31T13:54:42Z] Robert Architect:
  - [amendment — 2026-07-31] Two clarifications to §4; neither changes a position this decision took.
  - Roster field axis, settled at both ends. §4 already ruled a roster type's non-category fields field-mergeable; what it lacked was the reciprocal record, so ADR-541's wider clause was still readable as live. §4 now carries the evidence for the narrower claim and ADR-541 carries a matching dated note narrowing its floor in place. The line for the implementer: LOCKED = the three type keys must exist, may not be added to, dropped (including via selected), or renamed, and category may not move a type into or out of roster. MERGEABLE under the full floor = lifecycle, prefix, folder, labels, order, and every other non-identity field. That closes the open check in the loader's roster floor.
  - One provenance carrier: the '# squads:override-base:<version>' comment, not a top-level override_base spec key. The key is not introduced. Weightiest reason: re-stamping must not rewrite the adopter's document — a comment substitution preserves every other byte, while rewriting a key needs a round-tripping TOML serializer we do not have and which would reformat and drop comments in a file whose useful content is mostly comments. Then: one stamp grammar across every override kind, which this decision already asserted for the playbook; the loader gains nothing from a key, since it already holds the file text before parsing it, and a key would need stripping before model validation exactly as [selected] does; and two carriers for one fact disagree with no rule for which wins. An override writing override_base as a key fails closed as an unknown key, which is the right outcome for a mistyped provenance declaration.
  - Also pinned what 'must carry' means, which was unstated: unstamped AND shadowing is an error-level sq check / sq workflow lint finding; an older stamp keeps the existing drift warning; an add-only override needs nothing. None of the three is a load-time refusal — absent provenance does not change whether the merged spec satisfies the floor. Two surfaces move with it: the drift classifier keeps its three states with an unstamped file classified not-current, and the workflow 'sq override diff' Δ-mine must start diffing against the bundled spec instead of an empty reference.
  - @manager both ADRs left Accepted with dated amendment notes; related edge added ADR-541 → ADR-696. Nothing committed.
- [2026-07-31T14:05:10Z] Robert Architect:
  - [amendment — 2026-07-31] New §5a: the live-corpus cross-check compares a type's prefix and folder, not only its name. This decision made every type's prefix and folder mergeable — the roster's included — without saying what happens when the type already has items. It is not nothing, and the mechanism is worse than I first characterised it.
  - Corrected mechanism, verified in the code rather than reasoned about. _services/_maintenance.py::_iter_item_files — the single on-disk scan behind sq repair, sq check's index_reconciled, and repad — resolves each type's directory from spec.items[t].folder AND globs f'{ts.prefix}-*.md'. So a PREFIX change blinds the scan exactly as totally as a folder change does: the files carry the old prefix and the glob asks for the new one. Consequence in both cases: every item of that type disappears from the scan, index_reconciled reports each as 'in index but no markdown file found' (error), and a routine repair rebuilds from the empty scan and DROPS them all from the index, reporting them as missing_ids rather than refusing. Per-item reads keep working meanwhile only because Item.path is persisted and item_file() reads it — which makes the damage quiet until someone repairs.
  - So prefix and folder are one failure through one code path with one blast radius, and they get one clause, not two. I had told the coordinator a re-prefix 'splits the corpus but every item is still readable'; the split is real but it is not the important part, and that framing understated the prefix half. Also correcting my own earlier claim that an item's path is not persisted — it is, in the index (Item.path), which is why the failure is quiet rather than immediate.
  - The rule: for every type in the merged spec with at least one live item, the declared prefix and folder must equal the values its existing items were written under; a mismatch fails closed listing the offending IDs, in the shape and wording the cross-check already uses for a dropped type or status. It stores nothing new — the prefix is recoverable from each item's id and the directory from each item's stored path, so no per-type prefix/folder goes into the index (which is forbidden to hold what the .md files already carry). It sits on the cross-check plane, not the floor, because a re-prefixing spec is valid in the abstract and wrong only against this corpus — so it runs at §4b step 5, collects in sq workflow lint for free, and fails fast for open_service with no new mode. An empty corpus is unaffected.
  - Remedy discipline per ADR-697 §7: no shipped verb realigns an existing corpus, so the message names the two performable ways forward (revert the field, or make the change while the type has no items) and names no migration. The consequences state the resulting limit as a limit — re-prefixing and re-foldering are adoption-time freedoms, which bites the roster hardest since a squad has roster items from sq init — and record that the alignment verb which would lift it is a composition of shipped mechanics (repad already walks and renames every item file then repairs; retype already rewrites one item's id, moves its file and rewrites incoming edges atomically), so the gap is named precisely while staying a gap.
  - Nothing above is reversed: §3's floor, §4's merge and the roster ruling stand as decided. Recorded as an amendment rather than a new decision on this decision's own terms — its consequences already leave the floor mechanism open to carrying further clauses without another decision on the mechanism.
- [2026-07-31T14:27:59Z] Robert Architect:
  - [amendment — 2026-07-31] Three corrections to §4a/§4b, each closing a place where this decision asserted something the engine either could not do or would not reach. No position changes.
  - §4a's type-mismatch criterion loses its second half. 'A table where a scalar is due' is schema knowledge the engine does not hold, and its only schema-free reading (compare against the base's shape at the destination) would make a splice STRICTER than the literal it abbreviates, since deep_merge knowingly lets a hand-written leaf replace its counterpart with a different shape. The governing rule is now stated: a splat-ref is an abbreviation for a value the adopter could have written literally, held to the same standard as that expansion — no stricter, no looser. An abbreviation refused where its expansion is accepted is a broken abbreviation. The four failures that follow are enumerated (dangling path; spread against a non-list; spread with no surrounding list; malformed or surviving token) and there is no fifth. Shape stays with the models, which reject exactly this per-field.
  - The collect-all cost is real and I am not accepting it silently: a shape error arrives as a model-validation error, so sq workflow lint reports it alone rather than beside the others. But that is equally true of the hand-written value, so making splice-caused shape errors the one collectable kind would read as arbitrary. Recorded as a separate question — whether the loader translates a ValidationError into per-field lint findings, which a ValidationError's per-field list makes answerable and which fixes the whole class instead of one privileged sliver. Not folded into the splat grammar.
  - Token territory narrows: a value is in token territory only if it BEGINS with an unescaped '$('. The detection predicate was wider than the recognition rule it enforces — a token has always had to be the entire string value while the check fired on the sigil anywhere. This matters because the sigil IS POSIX command substitution and the playbook carries command lines: under the wide predicate an ordinary shell snippet is a load failure explained in terms of a grammar its author never used, and every tool writing a bundled string into an override file would owe a permanent escape duty that also makes the written file differ from its bundled source (corrupting sq override diff's delta-mine). Narrowing removes the duty rather than distributing it. Token syntax unchanged — this is not a sigil change. Accepted consequences recorded in place: an interpolation attempt stays literal, and only a leading sigil needs escaping, so the writers' duty is vacuous while no bundled string value begins with it (worth a standing guard over the bundled documents rather than a rule to remember). Also stated: the grammar and the escape are value-only; keys are vocabulary and are never resolved.
  - §4b closes the override document's top-level key space, enforced at the raw-mapping layer. Verified rather than assumed: the claim that a retired override_base key 'fails closed as an unknown key' rested on extra=forbid being reached, and it is not reached. Each loader builds its spec model from an explicit payload of named sections, so an unrecognised top-level key is dropped in the gap between the parsed document and the model. Driven against the real loader: an override containing only override_base and a bogus section loads clean and sq workflow lint reports nothing. A mistyped section name behaves the same way — silently, with no effect — which is the same fail-open class as a deselect that never happens. A role override's top level stays deliberately open (its keys are a role's fields, a set that grows between releases, so forward-compatible leniency is right there while a closed section-name set is right for the workflow document); the consequence that the retired key is ignored rather than refused in a role override, surfacing as an unstamped file, is stated rather than smoothed.
- [2026-07-31T14:48:28Z] Robert Architect:
  - [amendment — 2026-07-31] Closed the three §4a clauses left undefined: the path grammar, self through list nesting, and the walk's depth bound. No position above changes.
  - PATH GRAMMAR — a path segment is a TOML bare key (A-Za-z0-9_-), replacing the identifier-shaped path that excluded hyphens and leading digits while accepting non-ASCII everywhere but the first character. Anchoring on TOML's own key definition settles all three at once: hyphenated and digit-leading keys become addressable, and a non-ASCII key becomes correctly unaddressable as a quoted key rather than by accident of a character class. Widened rather than documented as a restriction because of the abbreviation rule — a value the adopter may write literally must stay expressible as a reference, and a grammar narrower than the vocabulary the spec may declare silently withdraws that for a class of legal names.
  - A correction to how the exposure was characterised, verified by driving the engine rather than reading it. Two readings had it as adopter vocabulary being unaddressable; it is not. Resolution is base-only, so a path can only ever address a key of the BUNDLED document. Driven: a hyphenated key in the base with an explicit path is refused as a malformed path (the real bite); an adopter's hyphenated custom key with $(*self) dangles, which is correct and would dangle identically under any grammar, because a brand-new key has no bundled list to append to; and a hyphenated custom key addressing a bundled path merges cleanly today, because the hyphen sits in the destination and not in the path. So the restriction binds squads' own key names, not any adopter's.
  - A key needing TOML quotes stays unaddressable: '.' is the path delimiter, so a dotted key is irreducibly ambiguous, and a quoted-segment sub-grammar would be a second nested syntax for a case no document has. Discharged by a standing guard that every bundled key is a TOML bare key, folded into the same scan that keeps a bundled string value from beginning with the sigil. Audited: all 353 workflow, 77 roles and 131 playbook keys are already TOML bare keys, so the guard passes as written. Nothing for an adopter to learn because nothing they can reach.
  - SELF THROUGH NESTING — self means the nearest enclosing KEYED path at any list depth, since a list index has no dotted name to contribute. Definitional, not a new rule: it is what 'the key currently being written' already meant, stated because nesting invites the other reading. Three intended consequences: two self tokens at different list depths under one key resolve alike; a nested spread puts the key's list into the sub-list, permitted because the destination's shape is the models' plane and not the engine's — the same answer the abbreviation rule gives everywhere else, so F9's 'should this be a violation because the surrounding shape is not the key's shape' is already decided by §4a rather than needing a fresh judgement; and spreading an EMPTY base list adds nothing, which is a value the base holds and so is distinct from a missing key, which dangles. Compose-only also permits one base list to be spread twice.
  - DEPTH BOUND — the walk carries a declared bound, exceeded → a refusal naming the dotted path, rather than qualifying the no-traceback contract. Qualifying is the wrong direction: the promise is about what an invocation does to the person running it, a wall of Python satisfies neither branch, the inputs are adopter-authored by design, and the TOML parser accepts documents far deeper than the walk survives (a single legal line of dotted keys reaches it), so no upstream layer can guard it. Weakening a stated invariant to match code that could cheaply satisfy it is how invariants stop meaning anything. Specified by two properties rather than a number — far above any hand-authored document (the deepest bundled key path is four levels), far below the interpreter's headroom with room for the per-level copy — binding BOTH walks, and checked before recursing or copying, since a deep untouched base fails inside the copy rather than in the engine's own frame.
- [2026-07-31T15:27:15Z] Robert Architect:
  - [amendment — 2026-07-31] Replaced the value-only sentence on keys. It was not merely ambiguous: it bundled one correct claim with one wrong one and left the operative case unstated. 'Never resolved' is right — there is no splice-into-a-key operation, because a path addresses a value and a value is not a key. 'Never unescaped' was wrong. And 'refused', which is neither, was the case the sentence had to settle and did not, so it could be read both ways and was.
  - The rule now reads in one place, symmetrically: the sigil is reserved in EVERY string position, keys as well as values, and token territory is one predicate in both — a string begins with an unescaped sigil. In a value, territory means resolve-or-refuse-as-malformed. In a key, territory means REFUSE: never pass through, never substitute. The escape unescapes in BOTH positions, and a string that merely contains the sigil after its first character is data in both.
  - Why refusing a key is not the engine legislating vocabulary. The escape keeps every name expressible — a project wanting a key spelled with the sigil escapes it and gets it — so the requirement is unambiguous spelling in a document where the sigil is reserved, not a restriction on which names exist. That is also the line between this refusal and the one refused for splices: there, holding a splat-ref to the base's shape would have left a value expressible literally but inexpressible as a reference, with no escape to recover it. Whether the adopter retains a way to say the thing is the test, and it separates the two cases cleanly.
  - The second half of the reasoning, verified rather than asserted: 'leave it to the models' is not available for keys the way it is for shape. For a value the models are a genuine backstop (typed fields, extras forbidden). For a key they are deliberately not, because a section's keys ARE the open vocabulary. Driven through the real loader — a spec declaring an item type literally named with a token loads clean, takes a prefix-map entry (JNK -> the token name), and resolves a folder. Nothing downstream is positioned to notice, so the engine's refusal is the only thing between a typo and a minted vocabulary entry. That is the surviving-token rationale at its strongest, not its weakest. It also keeps the verdict from depending on depth, since an unrecognised key at the document's top level already fails closed under §4b.
- [2026-08-03T08:14:55Z] Catherine Manager:
  - Observation for whoever next revisits the status-role catalog, recorded rather than actioned. The active role carries live = true, which is the roster axis, but its members include the work statuses Fixed, InProgress, InReview and ChangesRequested — so those inherit a roster property meaninglessly. One role serves two unrelated axes because their settled/hidden/color triples coincide. Latent today: both live_statuses consumers are gated to roster types, though _services/_items.py computes is_retirement from item.type before that gate, so a bug moving Fixed to Verified computes as a retirement and is discarded only by the following line. Not filed as a defect and not scheduled.
- [2026-08-03T08:15:37Z] Catherine Manager:
  - Correcting the previous note, which had the relationship backwards. The active role is the general in-flight role and the roster Active status uses it — the role is not a roster role borrowed by work statuses, so there is no conflation of two axes. A live flag declared on shared role vocabulary is this decision working as specified: roles are shared, and each consumer reads the axes its own domain cares about. Nothing consults live for a work item, so nothing is mis-declared and the catalog needs no revisit on this account. What does stand is narrower and is a code point: _services/_items.py computes is_retirement from item.type before the roster gate on the following line, deriving a value that is meaningless for a work item and harmless only because the caller discards it. Recorded as fragility, not as a defect.
- [2026-08-15T14:19:46Z] Robert Architect:
  - **Key-space extension recorded against this decision (2026-08-06).** The playbook override document (`.overrides/playbook.toml`), whose grammar, merge, stamp and validation this decision owns, gains one key on its role-guide entries: `authors`, boolean, defaulting `false`, additive — renaming nothing, removing nothing, retyping nothing. The guide model forbids extras, so its field set is that key space and this widens it; an adopter may now declare a guide as the in-lane author of the type it hangs under.
  - The key's semantics belong to ADR-163's create-lane and are specified there, in its §2, which also names this document as the surface it extends. `related` refs run both ways so the extension is reachable from the end that owns the key space — the freeze is only auditable if every addition is recorded here, not just where it is used.
<!-- sq:discussion:end -->
