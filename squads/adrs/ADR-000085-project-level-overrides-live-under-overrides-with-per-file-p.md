---
id: ADR-000085
sequence_id: 85
type: decision
title: Project-level overrides live under .overrides with per-file precedence, stamped
  staleness checks, and names in extra
status: Accepted
author: architect
refs:
- FEAT-000014
created_at: '2026-06-12T15:29:52Z'
updated_at: '2026-06-12T20:52:25Z'
---
<!-- sq:body -->
## Context

FEAT-000014 is the last explicitly-deferred item from the original plan, and it is a 1.0 blocker
for a structural reason: the moment we ship project-level overrides, the **override lookup path and
precedence rules become part of the durable on-disk contract** (FEAT-000013). Shipping them in 0.x
lets us get the layout right while we still can; bolting them on after 1.0 would mean either
breaking the contract or living with a mistake forever. This ADR settles the design so
implementation can proceed against a fixed shape.

Today the relevant mechanics are:

- **Templates** are bundled package data. `_rendering/_engine.py` builds one cached Jinja2
  `Environment` with `PackageLoader("squads._rendering", "templates")` and a single public
  `render(template_name, /, **ctx)` entry point. Resolution is strictly literal against the
  installed package — there is **no search path or fallback**. Item bodies render from
  `templates/items/<type>.md.j2`; role bodies from `templates/agents/role.md.j2`; sub-entity blocks
  from `templates/subentities/*`; backend artifacts (CLAUDE.md section, pointers, skills) from
  `templates/claude/*` and `templates/agents/*`.
- **Roles** come from `_roles/_catalog.py` (`RoleDef` dataclass: `slug`, `full_name`, `title`,
  `description`, `mission`, `responsibilities`, `agreements`, `model`, `color`, `is_default`). The 8
  bundled roles live in `PREDEFINED`; developer roles draw names from `DEV_NAME_POOL` via
  `dev_role(tech, name=None, seq, model)`. A role's definition is materialised as a ROLE **item**
  under `squads/agents/roles/ROLE-*.md` at `sq init` / `activate_role`, with its state in
  frontmatter `extra` (Invariant 1). The roster is **derived from active ROLE items**, not stored
  separately.
- **Naming today is fixed:** bundled roles carry hardcoded names; `sq dev add --name` is the only
  custom-name surface; there is no way to name roles at `sq init`.
- **Staleness precedent:** managed skills already carry `<!-- squads:managed -->` +
  `<!-- squads:version:{{ version }} -->` stamps, and `.squads.toml` records `squads_version` (last
  generator) and `schema_version`. `sq check` (`_services/_maintenance.py::check`) already emits
  `CheckIssue("warn"|"error", item, message)` for drift — the natural home for a staleness warning.

The questions this ADR must answer: **where** overrides live on disk, the **precedence** rule and
partial-override behaviour, how **staleness** across upgrades is detected and surfaced rather than
silently breaking, the **naming surface** at init and role creation, and **what joins the 1.0
durable contract**.

## Decision

### 1. Override locations — one umbrella directory under the squad folder

All project overrides live under a single umbrella directory, **`<squad-dir>/.overrides/`**, mirroring
the bundled `_rendering/templates/` tree exactly:

```
<squad-dir>/.overrides/
  templates/
    items/<type>.md.j2          # item body overrides
    subentities/*.md.j2
    agents/role.md.j2           # role body shape
    claude/*.md.j2              # backend artifact shapes
  roles/
    <slug>.toml                 # role definition overrides / additions
```

Rationale for the choices, deliberately:

- **`.overrides/`, not `.templates/`.** The body proposed `squads/.templates/`, but the scope is
  broader than templates (roles, and room for more later). One discoverable umbrella beats two
  sibling conventions and gives the contract a single named root. The leading dot keeps it out of
  the way and signals "configuration, not work items" — and crucially keeps it from colliding with
  the item-type folders the squad-folder scanner walks. **Confirmed by the operator (2026-06-12).**
- **Under the squad folder, not the project root.** It travels with `.squads.json` and the role
  items, is found by the same `_paths.resolve()` walk-up, and is guarded by the existing
  `abspath()` traversal check. The squad folder is already the unit of "this team's data."
- **`templates/` sub-tree mirrors the package tree 1:1.** An override is named by the **same
  relative path** the code already passes to `render()` (`items/task.md.j2`,
  `agents/role.md.j2`). No new naming scheme to learn or to freeze into the contract — the override
  key *is* the existing template name.
- **Roles as `roles/<slug>.toml`, not as `.md` bodies.** A role's durable state is structured
  (`RoleDef` fields), and Invariant 1 already keeps role state in frontmatter `extra`, not prose. A
  TOML file overriding/adding a role is a clean structured surface that feeds `RoleDef`; the role's
  rendered *body shape* is governed by overriding `templates/agents/role.md.j2`. This separates
  "what the role is" (data) from "how its file reads" (template) — the same split squads already
  makes everywhere.

### 2. Lookup order and precedence — project override → bundled default, per file

Resolution is a **two-entry search path, checked per template/role name**:

1. `<squad-dir>/.overrides/templates/<name>` (project) — if present, use it;
2. else the bundled `templates/<name>` (package default).

Implemented for templates by replacing the single `PackageLoader` with a Jinja2 `ChoiceLoader([
FileSystemLoader(<squad-dir>/.overrides/templates), PackageLoader(...) ])`. `render(name, ...)` and
every call site stay byte-for-byte identical — the search path is internal to the engine. (The
engine's `lru_cache(maxsize=1)` on the `Environment` must become keyed on the squad dir, or be
built per-resolve, so two squads in one process don't cross-contaminate.)

- **Partial override is the default and requires no ceremony.** Precedence is **per-file**, not
  all-or-nothing: drop `items/task.md.j2` and only task bodies change; every other template still
  resolves to the bundle. There is no "override everything or nothing" mode and no manifest listing
  what is overridden — presence of the file *is* the override.
- **No deep-merge of template contents.** A template file is overridden **whole** or not at all;
  we do not attempt block-level merging of Jinja2. (Markers still apply: an overridden item template
  must keep the required `<!-- sq:* -->` regions, enforced below.)
- **Roles merge by slug, field-wise.** `roles/<slug>.toml` for a **bundled** slug overrides only the
  fields it sets, inheriting the rest from `PREDEFINED` (so a team can rename `architect` or change
  its model without restating the mission). A **new** slug defines a wholly new role. This field-wise
  merge is the one place merging is allowed, because `RoleDef` is structured data, not free prose.

### 3. Staleness across upgrades — stamp, compare, warn, and the update loop (never silently break)

An override is authored against the bundled template/role of some squads version. A later upgrade
may change the bundled original (new required marker, new context variable, new `RoleDef` field).
We **detect and surface** this; we never silently break and never auto-rewrite a hand-authored
override. Overrides are **user-owned** content — the inverse of the tool-owned managed files — so
the team always merges upgrades by hand and then tells us they're done.

**Provenance stamp.** When a team scaffolds an override (via `sq override scaffold`, below), the
copied file carries `<!-- squads:override-base:<squads_version> -->` — the bundled version it was
branched from. This reuses the existing managed-file stamping convention; it is a comment, inert
to rendering. The stamp is the override's "I was last reconciled against vX" marker, and the whole
update loop turns on it.

**Drift detection in `sq check`, at two levels:**

- **Version drift (warn).** If an override's `override-base` is older than the running
  `squads_version`, and the *bundled* counterpart changed between those versions, emit
  `CheckIssue("warn", "<.overrides path>", "override may be stale: bundled <name> changed since
  v<base>; run `sq override diff <name>`, merge, then `sq override update <name>`")`. "Changed
  between versions" is determined by shipping a content hash of each bundled template per release (a
  generated manifest in package data) — cheap, exact, and needs no network. An override whose
  bundled counterpart did **not** change between `override-base` and current is silent: an old stamp
  alone is never a warning.
- **Structural breakage (error).** Independent of version: an overridden **item/role template that
  is missing a required marker region** (the `<!-- sq:* -->` anchors the section logic depends on)
  is an `error` — that genuinely breaks marker-safe editing (Invariant 3). An override that renders
  cleanly and keeps its markers is **never** downgraded to an error just for being old.

**Behaviour on render:** a stale-but-structurally-valid override **still renders** (the warning is
advisory; we do not block the team's chosen format). A structurally-broken override fails the
`StrictUndefined`/marker contract loudly at use, and `sq check` flags it ahead of time. There is no
silent fallback to the bundle when an override is present — falling back silently would be its own
invisible breakage.

**The end-to-end stale-override update workflow.** This is the full loop a maintainer runs after a
`squads` upgrade. `sq migrate` never touches `.overrides/`; this command group is the entire upgrade
path for user-owned overrides:

1. **`sq check` warns.** After upgrading, the next `sq check` compares each override's
   `override-base` stamp against the running `squads_version` and the shipped per-release hash
   manifest, and emits the **version-drift warning** above for every override whose bundled
   counterpart actually changed. This is the signal that an override has fallen behind.
2. **`sq override diff <name>` shows BOTH deltas.** The maintainer inspects the drift with a diff
   that surfaces **two** comparisons side by side, so they can see their own customisation *and*
   what the upgrade changed underneath it:
   - **Δ-mine:** the user's override vs the **current** bundled template — what the team customised
     away from today's default (so a hand-merge preserves their intent).
   - **Δ-upgrade:** the **base-version** bundled template (the one recorded by `override-base`) vs
     the **current** bundled template — what the upgrade itself changed in the default since the
     override was branched. Both bundled revisions are recoverable: the current one is package data,
     and the base one is reconstructed from the per-release hash manifest plus the bundled archive
     it indexes. Seeing Δ-upgrade is what lets the maintainer fold new required markers / context
     variables / fields into their override deliberately rather than guessing.
3. **The maintainer merges by hand.** Overrides are user-owned; we **never** auto-rewrite them. The
   team edits `.overrides/templates/<name>` (or `roles/<slug>.toml`) to reconcile Δ-upgrade into
   their version while keeping Δ-mine. They keep whatever they want and adopt whatever the upgrade
   requires (notably any new required marker, or the warning will re-fire as a structural error).
4. **`sq override update <name>` re-stamps.** Once the merge is done, this rewrites the
   `squads:override-base:` stamp to the current `squads_version` — and nothing else; it does **not**
   touch the body the maintainer just merged. Re-stamping is the maintainer's assertion "I have
   reconciled this against the current default." The next `sq check` recomputes drift against the
   new base and the warning clears. (`sq override update` with no name re-stamps every override that
   currently has a clean, structurally-valid body — a bulk acknowledge after a review pass.)

**`sq override` command group — the authoring + upgrade UX, and part of the durable contract:**

- **`sq override scaffold <name>`** — copy the named bundled template (`items/task.md.j2`,
  `agents/role.md.j2`, …) or a role (`--role <slug>`) into `.overrides/`, stamped with the current
  `override-base`, as the starting point for editing. Refuses to clobber an existing override unless
  `--force`. This is the only command that *writes override bodies*, and it does so only on first
  scaffold.
- **`sq override diff [<name>]`** — show the two-delta comparison (Δ-mine and Δ-upgrade) described
  above for one override, or for every drifted override when no name is given. Read-only.
- **`sq override update [<name>]`** — re-stamp the override's `override-base` to the current
  `squads_version` after a hand-merge, clearing the drift warning. Body untouched. With no name,
  re-stamps every structurally-valid override.
- **`sq override list`** — list every present override, its kind (template / role), its
  `override-base`, and its current state (`current` / `drifted` / `broken`), so a maintainer sees
  the whole override surface and what still needs reconciling at a glance.

This four-command set (`scaffold` / `diff` / `update` / `list`) is the complete override-management
surface and joins the durable 1.0 contract; the warning text and stamp format are part of it.

### 4. Agent naming at creation time

Naming becomes a first-class input at both creation surfaces, with the bundled pool as fallback.
There are three layered ways to supply a name — declarative flags, the config table, and (at a
terminal) an interactive prompt — and they compose:

- **At `sq init`:**
  - **Declarative flags.** Repeatable `--name <slug>=<Full Name>` flags
    (e.g. `--name architect="Ada Lovelace" --name manager="Grace Hopper"`).
  - **Config table.** An optional `[init.names]` table in `.squads.toml` for the declarative,
    checked-in path.
  - **Interactive prompt (TTY only).** When the terminal **is a TTY**, `sq init` **prompts
    interactively** for each role whose name was not already supplied by a flag or `[init.names]` —
    **unless `--default-names` is passed**, which skips all prompting. When the terminal is **not a
    TTY** (CI, pipes, scripts), `sq init` behaves exactly as if `--default-names` were given: it
    **never** blocks on a prompt. The declarative flags and `[init.names]` **pre-answer** prompts —
    any role named there is not asked about — so the prompt only ever covers the gaps, and a fully
    declarative invocation is never interactive even at a TTY.
  - **Fallback.** Any role still un-named after flags, config, and (where applicable) prompting falls
    through to its bundled `RoleDef.full_name` (bundled roles) or the `DEV_NAME_POOL` (developers) —
    **unnamed roles still get a pool/bundled name**, never blank. `--default-names` and the non-TTY
    path simply take this fallback for every otherwise-unnamed role.
- **At role creation later:** `sq role activate <slug> --name "…"` and the existing
  `sq dev add --name "…"` accept a name; absent it, the same fallback applies. A `roles/<slug>.toml`
  override may also carry `full_name`, which seeds the name when that role is activated.
- **Flow to all surfaces.** The chosen name is written to the ROLE item's frontmatter
  `extra.full_name` (the single source of truth). Everything downstream already reads from there:
  `roster()` → `RoleView.full_name` → the CLAUDE.md **Agent roster** section
  (`claude/claude_section.md.j2`), the agent **pointer** files (`claude/pointer_agent.md.j2`), and
  the rendered **role body** (`agents/role.md.j2`). No new plumbing — the name rides the existing
  `extra` channel, so renaming is just a frontmatter update + `sq sync`.
- **Slugs are not renamable.** Names (`full_name`) are free; **slugs stay canonical** (`architect`,
  `tech-lead`, `<tech>-dev`) because they are the addressing key for skills, interactions, pointer
  filenames and `@mentions`. A team renames *who the architect is called*, not *the architect slot*.
  **Confirmed frozen by the operator (2026-06-12).**

### 5. What joins the durable 1.0 contract

These surfaces are frozen by FEAT-000013 the moment this ships, and must be listed verbatim in the
contract doc:

- **The override root and tree:** `<squad-dir>/.overrides/{templates,roles}/`, with the
  `templates/` sub-tree mirroring the bundled template names 1:1, and roles as `<slug>.toml`.
- **The precedence rule:** per-file, project override → bundled default; presence is the override;
  no whole-squad override mode; templates override whole-file, roles merge field-wise by slug.
- **The staleness + update contract:** the `squads:override-base:<version>` stamp; that `sq check`
  warns on version drift (bundled counterpart changed since the stamped base) and errors on missing
  required markers; that a valid override always renders; that `sq migrate` never rewrites overrides;
  and the **`sq override` command group — `scaffold` / `diff` / `update` / `list`** — as the entire
  user-owned upgrade path, including that `diff` shows both Δ-mine and Δ-upgrade and that `update`
  re-stamps the base (body untouched) to clear the warning.
- **The naming contract:** names live in ROLE-item `extra.full_name`; slugs are canonical and not
  renamable; unnamed roles fall back to the bundled pool. The init naming surface — declarative
  `--name slug=…` flags and `[init.names]`, plus interactive prompting at a TTY for the gaps
  (suppressed by `--default-names`, implied off when non-TTY) — is the contracted entry path.

What is **deliberately not** frozen (room to grow without a major bump): additional override
*categories* under `.overrides/` (the umbrella is extensible), and the exact wording/layout of the
interactive init prompts (the *presence* of prompting and the `--default-names`/TTY rule are
contracted; the prompt copy is not) — both are additive.

## Consequences

- **Engine change is contained.** Swap `PackageLoader` for a squad-aware `ChoiceLoader`; fix the
  `Environment` cache key. `render()`'s signature and all ~13 call sites are untouched. This is the
  only change to the rendering hot path.
- **Roles gain a merge step.** `_roles/_catalog.py` (or a thin resolver beside it) must layer
  `roles/<slug>.toml` over `PREDEFINED` field-wise and admit new slugs; `activate_role`/`add_dev`
  read through that resolver. The roster derivation, pointers and CLAUDE.md section are unchanged
  because they already read `extra`.
- **`sq check` gains two override checks** (version-drift warn, missing-marker error) and the build
  must ship a per-release content-hash manifest as package data — used both for drift detection and
  to recover the base-version bundled template for the `sq override diff` Δ-upgrade view.
- **New `sq override` command group** (`scaffold` / `diff` / `update` / `list`) is the authoring +
  upgrade UX. `scaffold` writes a stamped copy; `diff` is read-only and renders both Δ-mine
  (override vs current bundled) and Δ-upgrade (base-version bundled vs current bundled); `update`
  re-stamps `override-base` to clear the drift warning **without touching the body** (overrides are
  never auto-rewritten); `list` reports each override's kind, base and state. The group joins the
  durable contract.
- **`sq init` gains interactive prompting** for missing role names, gated on TTY and suppressible
  with `--default-names`; non-TTY implies `--default-names`. The declarative `--name slug=…` flags
  and `[init.names]` table pre-answer prompts, so scripted/CI init stays non-interactive and
  reproducible.
- **New `.squads.toml` keys** (`[init.names]`; nothing else needs persisting — overrides are
  discovered on disk, not registered). Round-trips through `to_toml()`.
- **Invariants preserved.** Frontmatter stays the source of truth (names in `extra`); markers stay
  enforced (the missing-marker error guards them); backends stay the only writers of `.claude/`
  (overrides live under the squad folder, consumed before the backend renders). `.overrides/` is the
  one explicitly **user-owned** tree, the mirror image of the tool-owned managed files — which is
  why `sq override update` re-stamps but never rewrites, and why the merge step is always manual.
- **Tests** must cover: a partial template override (one file shadows, rest bundled); a field-wise
  role override + a brand-new role slug; the full staleness loop — a drift warning from `sq check`,
  `sq override diff` rendering both deltas, a hand-merge, `sq override update` re-stamping and the
  warning clearing — vs a missing-marker override (error); `sq override list`/`scaffold` behaviour;
  and names supplied at `sq init` (flag, `[init.names]`, interactive prompt at a faked TTY,
  `--default-names`, and the non-TTY-implies-default path) and at `sq role activate` flowing to
  roster + pointer + CLAUDE.md.

## Status note

Recorded as **Proposed**. Acceptance is the operator's call (Pierre / @manager). Revised 2026-06-12
per the operator's two requested revisions (stale-override update workflow spelled out end-to-end
with the named `sq override` command set; init naming UX with TTY prompting + `--default-names`);
the `.overrides/` location and frozen slugs were confirmed in the same review. If the post-1.0
custom ref-kind facility (ADR-000049) is ever designed, `.overrides/` is its reserved home —
consistent with this umbrella.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T15:42:57Z] Pierre Chat:
  - Operator review (2026-06-12): .overrides location confirmed; frozen slugs confirmed. Two revisions before acceptance:
  - 1) Spell out the stale-override UPDATE workflow end-to-end — check warns, override diff shows both what I changed and what the upgrade changed, manual merge, then a re-stamp command clears the warning. Name the sq override subcommands; they join the contract.
  - 2) Naming UX: if the terminal is a TTY, sq init prompts interactively for missing names unless --default-names is passed; non-TTY implies --default-names. --name/[init.names] stay as the declarative path. @architect please revise; stays Proposed until then.
- [2026-06-12T15:45:27Z] Robert Architect:
  - Revised per the operator's two rulings (2026-06-12); stays Proposed — acceptance is op-pierre / @manager.
  - §3 now spells out the stale-override update loop end-to-end and names the command group. The loop: (1) sq check warns on version drift — an override whose override-base predates the running squads_version AND whose bundled counterpart actually changed (per the shipped per-release content-hash manifest); an old stamp alone is silent. (2) `sq override diff <name>` shows BOTH deltas: Δ-mine (override vs current bundled = what the team customised) and Δ-upgrade (base-version bundled vs current bundled = what the upgrade changed underneath). The base-version bundled is recovered from the hash manifest. (3) the maintainer merges by hand — overrides are user-owned, never auto-rewritten. (4) `sq override update <name>` re-stamps override-base to the current version (body untouched) and the next sq check clears the warning.
  - Final `sq override` command surface (joins the durable contract): scaffold <name> (stamped copy into .overrides/, --force to clobber, --role <slug> for roles — the only writer of override bodies); diff [<name>] (read-only two-delta view, all drifted if no name); update [<name>] (re-stamp only, bulk-acknowledge if no name); list (each override's kind/base/state: current|drifted|broken). sq migrate still never touches .overrides/ — this group is the entire user-owned upgrade path.
  - §4 naming UX revised: at a TTY, sq init prompts interactively for each role still un-named after flags/[init.names], UNLESS --default-names is passed; non-TTY behaves exactly as --default-names (never blocks). The repeatable --name slug="Full Name" flags and [init.names] remain the declarative path and pre-answer prompts (named roles are not asked). Unnamed-after-everything still falls back to the bundled pool, never blank. Reflected in §5 contract and Consequences; the prompt presence + --default-names/TTY rule are contracted, the prompt copy is not.
  - Also folded the confirmed rulings into the body: .overrides/ location and non-renamable canonical slugs marked confirmed (2026-06-12).
- [2026-06-12T20:52:24Z] Pierre Chat:
  - Revision reviewed — the override update workflow (check warn → override diff with both deltas → manual merge → override update re-stamp) and the TTY naming UX with --default-names answer my questions. Accepted.
<!-- sq:discussion:end -->
