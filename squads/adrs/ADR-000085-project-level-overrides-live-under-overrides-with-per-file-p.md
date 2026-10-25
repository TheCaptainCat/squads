---
id: ADR-85
sequence_id: 85
type: decision
title: Project-level overrides live under .overrides with per-file precedence, stamped
  staleness checks, and names in extra
status: Accepted
author: architect
refs:
- FEAT-14
- ADR-1007
created_at: '2026-06-12T15:29:52Z'
updated_at: '2026-10-25T21:37:10Z'
---
<!-- sq:body -->
## Context

Project-level overrides are part of the durable on-disk contract: the moment a squad can override
what squads bundles, the **override lookup path and precedence rules** are something adopters build
on, and changing them later means breaking the contract or living with a mistake. This decision fixes
that shape.

What squads bundles, and so what a project may want to override:

- **Templates** — package data under `_rendering/templates/`. Item bodies render from
  `items/<type>.md.j2`, role bodies from `agents/role.md.j2`, sub-entity blocks from
  `subentities/*`, derived views from `views/*`, and backend artifacts (the `CLAUDE.md` section,
  pointers, the `AGENTS.md` section) from `claude/*` and `agents_md/*`.
- **Roles** — the bundled role catalog (`_specs/roles.toml`, ADR-221). A role's definition is
  materialised as a ROLE item under `squads/agents/roles/` when it is activated, and the roster is
  derived from active ROLE items, not stored separately.
- **Spec documents** — the workflow spec (`_specs/workflow.toml`) and the playbook
  (`_specs/playbook.toml`), beside the role catalog.

The questions this decision answers: **where** overrides live on disk, the **precedence** rule and
partial-override behaviour, how **staleness** across upgrades is detected and surfaced rather than
silently breaking, the **naming surface** at init and role creation, and **what joins the 1.0
durable contract**. How the three spec documents merge is ADR-696's; how uniformly every override kind
honours this decision's promises is ADR-777's.

## Decision

### 1. Override locations — one umbrella directory under the squad folder

All project overrides live under a single umbrella directory, **`<squad-dir>/.overrides/`**:

```
<squad-dir>/.overrides/
  templates/                    # mirrors the bundled _rendering/templates/ tree 1:1
    items/<type>.md.j2
    subentities/*.md.j2
    agents/role.md.j2
    views/*.md.j2
    claude/*.md.j2
  roles/
    <slug>.toml                 # one role's definition: a bundled role overridden, or a new role
  roles.toml                    # the whole role catalog document (ADR-777)
  workflow.toml                 # the workflow spec document (ADR-696)
  playbook.toml                 # the playbook document (ADR-696)
```

- **`.overrides/`, not `.templates/`.** The scope is broader than templates, so one discoverable
  umbrella beats sibling conventions and gives the contract a single named root. The leading dot
  keeps it out of the way, signals "configuration, not work items", and keeps it from colliding with
  the item-type folders the squad-folder scanner walks. Confirmed by the operator.
- **Under the squad folder, not the project root.** It travels with `.squads.json` and the role
  items, is found by the same squad resolution, and is guarded by the same `abspath()` traversal
  check. The squad folder is the unit of "this team's data."
- **`templates/` mirrors the package tree 1:1.** An override is named by the **same relative path**
  the code passes to `render()` (`items/task.md.j2`, `agents/role.md.j2`). The override key *is* the
  existing template name.
- **Roles as TOML, not as `.md` bodies.** A role's definition is structured data, so a TOML file is
  the clean surface that feeds it; the role's rendered *body shape* is governed by overriding
  `templates/agents/role.md.j2`. This separates "what the role is" (data) from "how its file reads"
  (template).

### 2. Lookup order and precedence — project override, then bundled default, per name

- **Templates resolve per file.** The engine's loader checks `<squad-dir>/.overrides/templates/<name>`
  first and falls back to the bundled `templates/<name>`. The squad directory is an argument to every
  render entry point and the template environment cache is keyed on it, so two squads in one process
  never cross-contaminate. `render()`'s call sites are unchanged; the search path is internal to the
  engine.
- **Partial override is the default and requires no ceremony.** Precedence is **per name**, not
  all-or-nothing: drop `items/task.md.j2` and only task bodies change; every other template still
  resolves to the bundle. There is no "override everything" mode and no manifest of what is
  overridden — presence of the file *is* the override.
- **A template is overridden whole.** No block-level merging of Jinja2. An overridden item or role
  template must keep the required sq marker regions, enforced below.
- **Structured documents merge.** A role file, the catalog document and the two spec documents merge
  over their bundled base through the shared engine (ADR-696 §4): leaf-granular deep merge,
  splat-refs against the bundled base, a closed top-level key space. A role file for a **bundled**
  slug overrides only the fields it sets, so a team can change a role's model without restating its
  mission; a file for a **new** slug defines a wholly new role. A role's definition resolves bundled
  catalog, then the catalog document, then its per-slug file, most specific last (ADR-777).

### 3. Staleness across upgrades — stamp, compare, warn, and the update loop

An override is authored against the bundled original of some squads version, and a later upgrade may
change that original (a new required marker, a new context variable, a new role field). We **detect
and surface** this; we never silently break and never auto-rewrite a hand-authored override.
Overrides are **user-owned** content — the inverse of the tool-owned managed files — so the team
merges upgrades by hand and then says it has done so.

**Provenance stamp.** `sq override scaffold` writes the bundled version an override was branched from
into the file as a `squads:override-base:<version>` stamp — an inert comment in the file's own syntax.
The stamp is the override's "last reconciled against vX" marker, and the update loop turns on it.

**Drift detection in `sq check`:**

- **Version drift (warn).** An override whose stamp is older than the running squads version **and**
  whose bundled counterpart actually changed since that version is reported as possibly stale, naming
  `sq override diff` and `sq override update`. "Changed" is decided by the per-release manifest
  shipped as package data, which records a content hash of every overridable bundled artifact per
  release and carries the content of every revision it names (ADR-777). An override whose bundled
  counterpart did **not** change is silent: an old stamp alone is never a warning.
- **Structural breakage (error).** An overridden **item or role template missing a required marker
  region** is an error, because it breaks marker-safe editing (ADR-74). An override that renders
  cleanly and keeps its markers is never an error just for being old.
- **Missing provenance (error).** A shadowing override with no stamp is an error for every kind; an
  add-only override with no bundled counterpart needs none (ADR-777 §6).

**Behaviour on render:** a stale but structurally valid override **still renders** — the warning is
advisory and the team's chosen format is not blocked. There is no silent fallback to the bundle when
an override is present; falling back silently would be its own invisible breakage.

**The update loop.** `sq migrate` never touches `.overrides/`; this loop is the entire upgrade path
for user-owned overrides:

1. **`sq check` warns** for every override whose bundled counterpart changed since its stamp.
2. **`sq override diff <name>` shows both deltas**: **Δ-mine**, the override against the current
   bundled original (what the team customised), and **Δ-upgrade**, the stamped-base bundled original
   against the current one (what the upgrade changed underneath), recovered from the manifest.
3. **The maintainer merges by hand**, folding Δ-upgrade in while keeping Δ-mine.
4. **`sq override update <name>` re-stamps** the override to the running version and touches nothing
   else, asserting "reconciled against the current default"; the next `sq check` clears the warning.
   With no name it re-stamps every structurally valid override at once.

**The `sq override` command group:**

- **`sq override scaffold`** — copy a bundled default into `.overrides/`, stamped: a template by
  name, one role (`--role <slug>`), a new role (`--new <slug>`), or a whole document (`workflow`,
  `playbook`, `roles`). Refuses to clobber an existing override unless `--force`. It is the only
  command that writes override bodies.
- **`sq override diff [<name>]`** — the two-delta comparison, for one override or every drifted one.
  Read-only.
- **`sq override update [<name>]`** — re-stamp after a hand-merge. Body untouched.
- **`sq override list`** — every present override with its kind, base version and state (`current`,
  `drifted`, `broken`).

### 4. Agent naming at creation time

Naming is a first-class input at both creation surfaces, with the bundled pool as fallback. There
are three layered ways to supply a name, and they compose:

- **At `sq init`:**
  - **Declarative flags.** Repeatable `--name <slug>=<Full Name>`.
  - **Config table.** An optional `[init.names]` table in `.squads.toml`, the checked-in path.
  - **Interactive prompt (TTY only).** At a terminal, `sq init` prompts for each role not already
    named by a flag or `[init.names]`, **unless `--default-names` is passed**. Off a terminal (CI,
    pipes, scripts) it behaves exactly as if `--default-names` were given and **never** blocks. The
    flags and the table pre-answer prompts, so a fully declarative invocation is never interactive.
  - **Fallback.** A role still unnamed gets its catalog name (bundled roles) or a name from the
    developer pool — never blank.
- **At role creation later:** `sq role activate <slug> --name "…"` and `sq dev add --name "…"`
  accept a name; absent it, a role override's name and then the same fallback apply.
- **Where the name lives.** The chosen name is written to the ROLE item's `title` (ADR-766,
  ADR-1007), and every downstream surface — the roster, the `CLAUDE.md` agent roster, the agent
  pointer, the rendered role body — reads it from there. The catalog and an override supply a name
  only when the role is created; after that the stored name is the role's name, and a rename goes
  through `sq role <slug> update --title` followed by `sq sync`.
- **Slugs are not renamable.** Names are free; **a stored slug is identity** (ADR-971), because it is
  the addressing key for skills, interactions, pointer filenames and `@mentions`. A team renames
  *who the architect is called*, not *the architect slot*. Confirmed frozen by the operator.

### 5. What joins the durable 1.0 contract

- **The override root and tree:** `<squad-dir>/.overrides/`, with `templates/` mirroring the bundled
  template names 1:1, roles as `roles/<slug>.toml`, and the three spec documents beside them.
- **The precedence rule:** per name, project override then bundled default; presence is the
  override; no whole-squad override mode; templates override whole-file, structured documents merge.
- **The staleness and update contract:** the `squads:override-base:<version>` stamp; that `sq check`
  warns on version drift only when the bundled counterpart changed, and errors on a missing required
  marker; that a valid override always renders; that `sq migrate` never rewrites overrides; and the
  **`sq override` group — `scaffold` / `diff` / `update` / `list`** — as the entire user-owned
  upgrade path, with `diff` showing both deltas and `update` re-stamping without touching the body.
- **The naming contract:** names live in the ROLE item's `title`; slugs are canonical and not
  renamable; an unnamed role falls back to the catalog or the pool. The init surface — `--name
  slug=…` flags and `[init.names]`, plus TTY prompting for the gaps, suppressed by
  `--default-names` and off when not a TTY — is the contracted entry path.

Deliberately **not** frozen: additional override categories under `.overrides/` (the umbrella is
extensible), and the wording and layout of the interactive init prompts (their *presence* and the
`--default-names`/TTY rule are contracted, the copy is not).

## Consequences

- **The rendering hot path changes in one place.** The template loader searches the squad's
  overrides before the package; `render()`'s call sites are untouched.
- **Roles resolve through a merge.** Activation and `sq dev add` read a role's definition through
  the catalog-then-override resolution rather than the bundled catalog alone.
- **`sq check` carries the override checks** (version drift warn, missing marker error, missing
  provenance error), and the build ships the per-release manifest as package data, used both for
  drift detection and for the Δ-upgrade view.
- **`sq init` prompts for missing role names** only at a TTY and never without one, so scripted and
  CI init stays non-interactive and reproducible.
- **One new `.squads.toml` key**, `[init.names]`. Nothing else needs persisting: overrides are
  discovered on disk, not registered.
- **Invariants preserved.** Frontmatter stays the source of truth (names in the ROLE item's
  `title`); markers stay enforced (the missing-marker error guards them); backends stay the only
  writers of `.claude/` (overrides live under the squad folder and are consumed before the backend
  renders). `.overrides/` is the one explicitly **user-owned** tree, the mirror image of the
  tool-owned managed files — which is why `sq override update` re-stamps but never rewrites, and why
  the merge step is always manual.
- **Tests cover:** a partial template override; a field-wise role override and a new role; the full
  staleness loop (a drift warning, both deltas in `diff`, a hand-merge, `update` clearing the
  warning) against a missing-marker override (error); `list` and `scaffold`; and names supplied at
  `sq init` (flag, `[init.names]`, a prompt at a faked TTY, `--default-names`, the non-TTY path) and
  at `sq role activate`, flowing to the roster, the pointer and `CLAUDE.md`.

## Provenance

The stale-override update loop with its named `sq override` command set, and the init naming UX with
TTY prompting plus `--default-names`, were revisions the operator asked for before acceptance. The
`.overrides/` location and the frozen slugs were confirmed in the same review.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T15:42:57Z] `op-pierre` Pierre Chat:
  - Operator review (2026-06-12): .overrides location confirmed; frozen slugs confirmed. Two revisions before acceptance:
  - 1) Spell out the stale-override UPDATE workflow end-to-end — check warns, override diff shows both what I changed and what the upgrade changed, manual merge, then a re-stamp command clears the warning. Name the sq override subcommands; they join the contract.
  - 2) Naming UX: if the terminal is a TTY, sq init prompts interactively for missing names unless --default-names is passed; non-TTY implies --default-names. --name/[init.names] stay as the declarative path. @architect please revise; stays Proposed until then.
- [2026-06-12T15:45:27Z] `architect` Robert Architect:
  - Revised per the operator's two rulings (2026-06-12); stays Proposed — acceptance is op-pierre / @manager.
  - §3 now spells out the stale-override update loop end-to-end and names the command group. The loop: (1) sq check warns on version drift — an override whose override-base predates the running squads_version AND whose bundled counterpart actually changed (per the shipped per-release content-hash manifest); an old stamp alone is silent. (2) `sq override diff <name>` shows BOTH deltas: Δ-mine (override vs current bundled = what the team customised) and Δ-upgrade (base-version bundled vs current bundled = what the upgrade changed underneath). The base-version bundled is recovered from the hash manifest. (3) the maintainer merges by hand — overrides are user-owned, never auto-rewritten. (4) `sq override update <name>` re-stamps override-base to the current version (body untouched) and the next sq check clears the warning.
  - Final `sq override` command surface (joins the durable contract): scaffold <name> (stamped copy into .overrides/, --force to clobber, --role <slug> for roles — the only writer of override bodies); diff [<name>] (read-only two-delta view, all drifted if no name); update [<name>] (re-stamp only, bulk-acknowledge if no name); list (each override's kind/base/state: current|drifted|broken). sq migrate still never touches .overrides/ — this group is the entire user-owned upgrade path.
  - §4 naming UX revised: at a TTY, sq init prompts interactively for each role still un-named after flags/[init.names], UNLESS --default-names is passed; non-TTY behaves exactly as --default-names (never blocks). The repeatable --name slug="Full Name" flags and [init.names] remain the declarative path and pre-answer prompts (named roles are not asked). Unnamed-after-everything still falls back to the bundled pool, never blank. Reflected in §5 contract and Consequences; the prompt presence + --default-names/TTY rule are contracted, the prompt copy is not.
  - Also folded the confirmed rulings into the body: .overrides/ location and non-renamable canonical slugs marked confirmed (2026-06-12).
- [2026-06-12T20:52:24Z] `op-pierre` Pierre Chat:
  - Revision reviewed — the override update workflow (check warn → override diff with both deltas → manual merge → override update re-stamp) and the TTY naming UX with --default-names answer my questions. Accepted.
- [2026-08-03T08:41:57Z] `architect` Robert Architect:
  - Dropped the "Recorded as Proposed. Acceptance is the operators call" opener and retitled the section to Provenance, as part of the sweep across the ten retroactive decisions. The revision history it also carried is genuinely useful and is kept intact.
  - Verified in force end to end while in there, and it needs nothing else: `.overrides/templates|roles` resolution, the `ChoiceLoader` template precedence, field-wise role merge, the `override-base` stamp, the per-release content-hash manifest shipping as package data, all four `sq override` verbs including the two-delta diff, and `[init.names]`/`--name`/`--default-names`. `.overrides/workflow.toml` is a third category sanctioned by this decisions own "additional override categories are not frozen" clause.
  - One watch item rather than a defect, recorded so it is not rediscovered: when the shared deep-merge engine ADR-696 section 4 describes lands, the clause to reconcile is "templates override whole-file, roles merge field-wise" — a uniform merge model touches exactly that sentence.
- [2026-10-25T21:37:10Z] `architect` Robert Architect:
  - 2026-10-25 audit: rewritten in present tense; the decision and its frozen surface are unchanged. Folded in the five override kinds (`.overrides/roles.toml`, `workflow.toml`, `playbook.toml` beside templates and roles), merging through ADR-696, drift gated on the content manifest for every kind (ADR-777), and the unstamped-shadowing error. Names now live in ROLE `title` (ADR-766/1007), are set only at creation, and change through `sq role <slug> update --title`. Removed the pre-implementation Context and the ADR-1007 note.
<!-- sq:discussion:end -->
