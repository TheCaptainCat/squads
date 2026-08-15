# The squads stability contract

squads is approaching its 1.0 release. This document defines the public surfaces that will be
stable after 1.0, and what each surface promises. The contract is tiered by durability: strongest
at tier 1, weakest at tier 5. Use this guide to decide what you can safely build on, and what may
shift with a new release.

## The migration promise

**Any squad created on any 0.x release reaches 1.0 intact via `sq migrate up`.**

This is the strongest promise the contract makes. Your items, your metadata, your folder structure
— all preserved. The migration runner is ordered and testable, with manual runbooks for the parts
that need judgment. See [migration.md](migration.md) for how it works.

---

## Tier 1: Durable `.md` format (strongest promise)

The on-disk format — item frontmatter, markers, and folder layout — is locked at 1.0.
**Your item files are your data.**

### Schema versioning and migrations

The format is versioned with a dotted string (e.g., `"0.3"`) that names the release introducing the
schema. Comparisons use `schema_tuple()`, never raw-string `<` or `>`; so `"0.10" > "0.2"` holds.
Post-1.0, a schema change ships only with a MAJOR release of squads. The upgrade path is always
`sq migrate up`, which applies the ordered migration runners, rebuilds the index, and stamps the new
version (see [migration.md](migration.md)).

### ID numbering, padding, and exhaustion

The global sequence number is the durable identity of an item — `TASK-<n>` and `TASK-NNNNNN` (in refs or filenames)
resolve to the same item forever. The *number* never changes across a retype or repair; the *prefix* stays fixed.

- **Display:** every human-facing surface (frontmatter `id:`, CLI output, `--json`) renders IDs unpadded (e.g. `TASK-<n>`).
  This is fixed and not user-configurable.
- **Filenames:** on disk, items use zero-padded names (`TASK-NNNNNN-slug.md`) for lexicographic sorting. The padding
  width is stored in the index with a default of 6, reconstructed by `sq repair`. Raised one-way via `sq migrate repad
  <width>` (never lowered). References written before a repad retain their original width — readers understand both.
- **Exhaustion:** `sq create` errors with an index-full message at capacity, never silently
  widening. If a squad fills its current filename width, raise the width explicitly and the counter
  continues.


### IDs are never reused

Removal preserves the counter high-water mark; a removed sequence number is permanently retired. A
gap in the sequence (e.g., `…TASK-<n>, TASK-<n+2>…` after removing `<n+1>`) is normal, sanctioned,
and reader-relyable — tools and humans must not treat a missing number as corruption. `sq check` and
`sq repair` both accept gaps as normal state.

**Removal vs. cancellation**: Cancelled items (a terminal status) remain on the books — they represent
considered-and-dropped work. A *removed* item is a hard delete — it should never have existed and leaves
the corpus entirely, no soft Archived state.

**Reference severance on removal**: When an item is forcibly removed, all incoming references from
other items are severed in the same transaction. No dangling refs survive; `sq check` stays clean.

### Sub-entity state lives in frontmatter

User stories' and subtasks' status, assignee, severity, and mapped story live in the parent item's
frontmatter (`Item.subentities`), not in the body. Only prose (the `:body` and `:discussion` regions)
stays in the body markers. This is **Invariant 1** — frontmatter is the source of truth — and it
makes the index rebuildable from files alone (see [internals.md](internals.md) § 4).

### Project-level overrides

A squad may customize bundled templates, roles, and item-type vocabulary under `.overrides/`, a
folder in the squad directory. The frozen surfaces are:

- **Layout:** `<squad-dir>/.overrides/{templates,roles}/` and `.overrides/workflow.toml`. Templates
  mirror bundled template names 1:1; roles are TOML files keyed by slug (e.g., `architect.toml`);
  `workflow.toml` is the squad's vocabulary delta — item types, statuses, lifecycles, badge
  collections, status roles.
- **Precedence:** per-file, project → bundled. Presence of a file is the override. Templates
  override whole-file; roles merge field-wise by slug; the workflow override composes over the
  bundled vocabulary and **may shadow a built-in**, not only add to it.
- **Workflow override grammar (frozen):** deep recursive merge at leaf granularity — tables recurse
  per key, and a leaf value replaces its counterpart. A plain array is a leaf, replaced wholesale
  and never element-merged. **Splat-refs** are the opt-in for extending a bundled list without
  restating it: `$(path)` splices the bundled value at *path* as one element and `$(*path)` spreads
  a bundled list's elements into the surrounding list, with `$(self)` / `$(*self)` addressing the
  key being written. A path is a dot-joined chain of TOML bare keys (ASCII letters, digits,
  underscores, hyphens), with `self` the only special segment. Resolution is against the bundled spec
  only, so the merge is order-independent and cycle-free, and a splat only ever adds. A string is read
  as a token only when it *begins* with an unescaped `$(` and is a token in its entirety; `$$(`
  escapes a string that must literally begin `$(`. There is no interpolation. The sigil is reserved
  in **every** string position, keys as well as values: a token-shaped key is refused — there is no
  splice-into-a-key operation — and the refusal names the escape, so `$$(` still gets you the literal
  key you want. A top-level `[selected]` table shrinks named sections to the set that survives. The
  document's top level is a closed key space: an unrecognised key is refused by name. Nesting is
  bounded at 300 levels on both the override and the bundled side (far above any hand-authored
  document; the deepest bundled key path is four); past it, the dotted path is named and the merge
  refuses rather than recursing.
- **Reserved surface (frozen):** the three roster type **keys** — `role`, `skill`, `operator` — must
  exist and may not be added to, renamed, or dropped; `category = "roster"` may not move into or out
  of those three. That is the whole of it. Every other field of a roster type, `lifecycle` included,
  is an ordinary validated field merge, and **no status name is reserved** — a project may name its
  lifecycle states anything, in any language, with any number of settled states. What a lifecycle
  must supply is checked rather than named. A roster lifecycle declares:
  - at least one live status — otherwise no entry of that type could ever be materialised;
  - a settled, non-live status reachable from a live one — otherwise an entry could never retire;
  - and, *when the lifecycle's `initial` is not itself live*, exactly one live status — so the entry
    squads scaffolds for itself has an unambiguous target. This is the rule that makes a
    parked-then-activated roster lifecycle declarable: name a non-live `initial` plus a single live
    status, and your own entries start parked until you move them. When `initial` is itself live
    there is nothing to disambiguate, and any number of further live statuses is fine.
- **Failure mode:** an invalid override is a **load-time hard stop** with a clean error, never a
  partially-applied spec or a traceback. `sq workflow lint` reports every violation at once with a
  location and a fix hint. A change refused against the live corpus — a dropped type or status live
  items still carry, or a `prefix`/`folder` change on a type that already has items — names the
  offending item IDs, and names only remedies a shipped command can actually perform.
- **Staleness & drift:** an override carries an `override-base` version stamp — an HTML comment
  (`<!-- squads:override-base:<version> -->`) in a template, a TOML comment
  (`# squads:override-base:<version>`) in a role or workflow override. `sq check` warns if the
  bundled counterpart changed since that base version (drift), and errors if a template is missing
  required markers. A workflow override that shadows a built-in must carry the stamp — unstamped and
  shadowing is an error-level `sq check` / `sq workflow lint` finding, though not a load-time refusal;
  an add-only override needs no stamp. `sq migrate` never rewrites overrides; the `sq override`
  command group (`scaffold` / `diff` / `update` / `list`) is the user-owned upgrade path. `sq
  override diff` shows two deltas: Δ-mine (your customisation vs current bundled) and Δ-upgrade
  (base-version bundled vs current bundled), so you see exactly what to merge.
- **Workflow spec validation:** `sq workflow lint` validates the workflow override for
  well-formedness, reference integrity, and liveness (reachability of live items). After a squad
  upgrade, `sq workflow lint` revalidates the spec.
- **Manifest:** `squads._rendering/templates_manifest.json` ships as package data, mapping
  version → {template_name → sha256_hex}, used for drift detection and base-version recovery.

See [docs/overrides.md](overrides.md) and [docs/workflow.md](workflow.md) § "Project workflow overrides".

### Reflog on-disk format

An append-only JSONL file at `<squad>/.reflog.jsonl` records every mutation — item creation and
status changes, metadata and body edits, comments, sub-entity and ref changes, parent links,
retypes, removals, and maintenance runs. It is **ADVISORY and explicitly NOT a
source of truth** — `load`, `check`, and `repair` never read it; `sq repair` rebuilds
`.squads.json` from frontmatter alone. A missing, truncated, or garbage reflog never affects state
or command behaviour.

The line schema (frozen field set):

- `v` — schema version (currently coupled to the index `SCHEMA_VERSION`); whether to decouple is open
- `ts` — ISO-8601 timestamp with Z suffix
- `actor` — who made the change (slug or operator ID)
- `op` — operation name, from a closed vocabulary:

  | `op` | Written when |
  |------|--------------|
  | `create` | an item is created |
  | `status` | an item's status changes |
  | `update` | item metadata changes (assignee, badge fields, labels, …) |
  | `body` | an item's body is set |
  | `comment` | a comment is appended |
  | `subentity` | a sub-entity is added, edited (status, assignee, fields, body), or removed |
  | `ref` | a ref is added, removed, or severed |
  | `link` | an item's parent is set or cleared |
  | `retype` | an item is retyped |
  | `default_role` | the default-role designation moves |
  | `remove` | an item is hard-removed (carries the gone-item snapshot) |
  | `repair` | `sq repair` rebuilds the index (including `--renumber`) |
  | `renumber` | `sq renumber` shifts a range of sequence numbers |
  | `migrate` | `sq migrate up` applies a batch |
  | `rename-type` | one line per item moved by `sq migrate rename-type` |
  | `rename-status` | one line per item moved by `sq migrate rename-status` |

- `target` — the affected item's formatted ID (its prefix names the type). Empty for the
  corpus-wide ops (`repair`, `renumber`, `migrate`), which are not item-scoped
- `delta` — before→after summary (not a replayable diff); its shape depends on `op`
- `session_id`, `parent_session_id` — *optional*, omitted entirely when absent. Best-effort,
  **untrusted, observability-only** identifiers read from the invoking environment; squads never
  mints or verifies them, and a forged or copied id is indistinguishable from a real one. Only the
  immediate parent is stored — walk the edges to reconstruct a chain. Lines written without them
  parse with both as absent; nothing is rewritten.

Lines are versioned and forward-compatible by field addition; readers key off `v` and ignore
unknown fields, skip a trailing partial line, and warn-skip interior bad lines. Durability: the
line is appended AFTER the index's atomic `os.replace` commit, inside the lock. Applied-without-logged is the tolerated failure (append failure warns, never rolls back); logged-without-applied is
impossible.

### Backend selection via `.squads.toml`

The `active_backends: list[str]` field in `.squads.toml` selects which agent backends a squad runs.
Pre-0.3, the singular `default_backend: str` field was used; it is read transparently as a
single-element list, so both forms are valid 0.3 input.

- An empty `active_backends = []` is valid — a "sq-only" squad with no agent files.
- Deactivation (dropping a backend from the list) leaves its files on disk untouched; `sq sync`
  stops refreshing and `sq check` stops verifying them.
- Order is not significant; the list is deduped first-occurrence.
- CLI: `--backend` is repeatable, with a `none` sentinel for empty.

---

## Tier 2: CLI grammar (SemVer-stable from 1.0)

Commands, arguments, and options freeze at 1.0 and follow SemVer thereafter. Removals, renames, and
breaking grammar changes are allowed only in MAJOR releases.

### Addressing rule

Every item is addressed by **full ID** or **bare number**, accepted everywhere. Addressing an
existing item through the wrong type is an error.

```bash
sq show TASK-<n>         # full ID (unpadded)
sq show TASK-NNNNNN      # also works (padded form for backward compatibility)
sq show 7                # bare number (resolves the item at sequence 7, whatever its type)
sq show BUG-<n>          # ERROR: item 7 is a task, not a bug
```


### Item-first grammar for agent types

Commands that address an existing role, skill, or operator follow the **item-first pattern** used
everywhere else:

```bash
sq role 2 show           # item-first: type, number, verb
sq role 2 regen          # regenerate
sq role 2 status <S>     # transition status
sq role 2 set-default    # move the default-role designation here
sq role 2 rm             # remove
sq skill 5 show
sq skill 5 link-role architect     # scope a custom skill to a role (and unlink-role to undo)
sq operator 3 show
```

**Creation commands stay verb-first** at the group level, receiving a catalog slug or a new name:

```bash
sq role activate architect           # group-level verb-first
sq role activate <slug> --name "…"   # with optional custom name
sq skill add <name>
sq operator add "<name>"
```

**Bundled catalog:** `sq role catalog` is the dedicated subcommand for the bundled-but-not-activated
role catalog (shows slug, name, title, default). The deprecated `sq role list --available` is gone.

**Slug resolution:** for `role show`/`regen`/`rm`/`status`/`set-default`, slug is a valid address
form in addition to full ID and bare number.

**Status flags on a roster entry:** `status` takes `--force` on all three types — overriding a
transition the lifecycle disallows, exactly as on a work item — and `--unlink`, which on a
retirement severs the severable dependency a refusal named rather than overriding the refusal.
Neither flag can override the two conditions that refuse a retirement outright; see
[roles.md § "Retiring a roster entry"](roles.md#retiring-a-roster-entry).

**Active-roster list commands:** `sq role list` lists the activated role roster — a
live/not-live marker per row, distinct from the bundled `sq role catalog` — and `sq operator
list` enumerates registered operators; both take `--json`. `sq skill list` has no dedicated verb;
use `sq list -t skill` for skills.

### Type-command aliases

Aliases are input sugar; canonical type names always appear in output, errors, and `--json`.
The alias table (frozen at 1.0):

| Canonical | Aliases |
|-----------|---------|
| `epic` | `e` |
| `feature` | `feat`, `f` |
| `task` | `t` |
| `bug` | `b` |
| `decision` | `dec`, `d` |
| `review` | `rev`, `r` |
| `guide` | `g` |

Each alias is fully equivalent to its canonical type across every verb and sub-entity chain
(e.g., `sq f 26 story 4 show` ≡ `sq feature 26 story 4 show`). Adding a new alias is additive and
allowed post-1.0; removing or repurposing an existing alias is breaking and is not.

### Retype an item in place

The verb `sq <type> <n> retype <new-type>` changes an item's type while preserving its number. The
number is the stable identity: a `TASK-<n>` becomes `BUG-<n>`, the `.md` file moves folders and
reprefixes, body bytes are preserved verbatim, and incoming edges (refs, children parent, prose
mentions) are rewritten in the same transaction. `sq check` stays clean.

### Migrate sub-app surfaces

The `sq migrate` sub-app's frozen surface:

- `sq migrate up` — run every pending automatic migration, rebuild the index, stamp the new schema
- `sq migrate help` — the changelog index
- `sq migrate chlog vA..vB` — manual steps for migrations shipped in `(vA, vB]`
- `sq migrate repad <width>` — raise the filename-padding width (see Tier 1)
- `sq migrate rename-type <old> <new>` — bulk-rename every item of one type to another (same
  semantics, new prefix and folder), for when a vocabulary override renames a type you already
  have items in
- `sq migrate rename-status <type> <old> <new>` — bulk-relabel one type's items from one status
  name to another; a relabel, not a workflow move

Runner modules are private; never use `python -m`; `sq migrate` is the only entry point.

### Bulk import

`sq import <file>` loads a JSONL event stream in one process — the supported path for bringing
history in from another tracker. Every event is validated first (type and status vocabulary,
transition legality, actor registration, marker safety), collecting *all* problems with line
numbers before writing anything; only a fully clean file is applied, in a single transaction.
`--dry-run` stops after validation and prints the projected handle → ID plan; `--json` emits the
result machine-readably. The global `--at` sets the file-level default timestamp; `--as` sets the
default acting slug. Attribution has no silent fallback — an event with no `as` of its own, no
prior event's to inherit, and no `--as` fails validation naming the missing actor. See
[adoption.md](adoption.md).

### Exit codes (distinct codes for distinct failures)

Frozen contract:

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | squads runtime error (schema mismatch, corrupt index, validation failure, etc.) |
| `2` | Usage error (bad arguments, missing required flag) |
| `3` | Check failures (one or more issues found by `sq check`) |

The distinct code for check failures lets CI distinguish "check found issues" from "command errored".

### Ref-kind vocabulary (closed at 1.0)

The nine built-in kinds are frozen: `related` (default, no colon needed), `blocks`, `depends-on`,
`implements`, `fixes`, `addresses`, `supersedes`, `duplicates`, `scopes`. Unknown kinds are rejected.

A project-declared custom-kind extension is reserved for a future release and will be additive and
non-breaking. The built-in kinds' meanings stay fixed.

### Status-set validation

What is frozen here is the *validation behaviour*, not any particular status name — see Tier 1's
reserved surface: a project may name its lifecycle states anything.

Setting a status validates against **the type's own lifecycle, at set-time**, in two independent
steps:

1. **Vocabulary.** The target status must be one the type's lifecycle declares. It need not be
   reachable from where the item currently sits — just declared. A status outside that set is
   refused, and the error lists the type's whole allowed set.
2. **Transition.** The edge from the current status to the target must be one the lifecycle
   declares.

`--force` relaxes step 2 only — it jumps a missing edge — and **never** step 1. Forcing a status
the type's lifecycle does not declare is still refused, with the same message and the same exit
code as without the flag. Whatever you name your states, that boundary holds: no status can enter
an item's frontmatter unless its own type's lifecycle declares it.

Two things follow that machine-readable clients can rely on:

- The squad's whole declared status vocabulary is readable up front — `sq workflow statuses --json`,
  joined to `sq workflow roles --json` for each status's behaviour. Don't infer the vocabulary from
  whatever statuses happen to appear in your corpus. Which of those statuses a *given type*
  accepts, and the edges between them, is printed by `sq workflow show`; a refused set also lists
  that type's allowed set in full.
- "Is this item finished?" is a property of the status's **role**, not its name (`settled` on the
  role catalog). Never hardcode a status name to detect a resting state.

Bundled example — the bug lifecycle that ships by default (fully overridable, like every bundled
lifecycle):

```
Initial: Open
Open → { InProgress, WontFix, Cancelled }
InProgress → { Fixed, Blocked, WontFix, Cancelled }
Fixed → { Verified, InProgress }
Verified → { InProgress }
Blocked → { InProgress, WontFix, Cancelled }
WontFix → { Open }
Cancelled → { Open }
```

With the bundled vocabulary, `Verified`, `WontFix` and `Cancelled` resolve to roles that are both
settled and hidden — so those are the bug's resting states, and `sq list` / `sq tree` leave them
out unless you pass `--all` or name the status. `settled` and `hidden` are separate axes on the
role catalog: a status can be settled without being hidden (bundled `Accepted` is).

---

## Tier 3: `--json` output shapes (stable; additive changes only)

Read commands emit stable JSON shapes. **Additive** means fields may be added, never removed or
renamed or retyped within a major version. The frozen surface includes:

- **Reading the board:** `list`, `tree`, `graph`, `inbox`, `search`, `blocked`, `workload`, `mine`,
  `show`, `refs`, `comments`, `create`, `check`, plus each sub-entity list command
  (`sq task <n> subtasks --json`, `sq feature <n> stories --json`, `sq review <n> findings --json`)
  and each single sub-entity (`sq feature <n> story <k> show --json`, and the same for a subtask or
  a finding), which emits that one sub-entity's object — the same shape the parent's `show --json`
  nests under `subentities`, `body` / `badges` / `discussion` included
- **Roster viewers:** `role catalog`, `role list`, `role <addr> show`, `skill <addr> show`,
  `operator list`, `operator <addr> show`. Skills have no dedicated `skill list` — use the generic
  `list -t skill`
- **The workflow catalogs** — the machine-readable form of your squad's *active* vocabulary,
  bundled plus any override, and the surface to read instead of hardcoding a name:

  | Command | One row per | Fields |
  |---|---|---|
  | `sq workflow types --json` | item type | `type`, `order`, `prefix`, `reserved`, `category`, `subentity_kind`, `lifecycle`, `fields`, `labels` |
  | `sq workflow subentity-kinds --json` | sub-entity kind | `subentity_kind`, `lifecycle`, `plural`, `local_prefix`, `container_heading`, `completion`, `maps_parent_story`, `fields` |
  | `sq workflow collections --json` | badge collection | `collection`, `label`, `ordered`, `default`, `badges` |
  | `sq workflow statuses --json` | status | `status`, `role`, `badge` |
  | `sq workflow roles --json` | status role | `role`, `settled`, `hidden`, `color`, `live` |

  Each emits a bare JSON array, one row per declared entry in a documented order, with **every key
  present on every row** — `null` for absent, never omitted. They are designed to be **joined**, and
  a reference always carries the identity key name of the row it points at: a type's or kind's
  `fields[].collection` keys into the collection catalog, a type's `subentity_kind` keys into the
  sub-entity kind catalog, and a status's `role` keys into the role catalog — that's where
  `settled` / `hidden` / `color` / `live` live. `role` is always the *resolved* role name, never
  null, so `null` stays available to a client meaning "not loaded yet". `terminal` and `is_open`
  are deliberately not fields anywhere: they are `settled` / `not settled` on the role catalog.

  **`lifecycle` is the exception: it names a machine, but no catalog in this release publishes
  one.** Treat it as a grouping key — equal values mean two entries bind the same machine — and note
  that no other `--json` surface exposes lifecycle membership either, `sq workflow statuses` being a
  flat vocabulary list. See [workflow.md](workflow.md#joining-the-catalogs).
- **Override inspection:** `override list --json` (an array of `{name, kind, base_version, state}`)
  and `override diff --json` (`{name, kind, base_version, base_available, delta_mine,
  delta_upgrade}`)
- **The reflog:** `sq reflog --json` emits the Tier 1 line schema —
  `{v, ts, actor, op, target, delta, session_id, parent_session_id}`. Note the difference from the
  file: the two session fields are always *present* here, `null` when absent, where on disk they
  are omitted. They carry the same untrusted, observability-only caveat either way
- **Notices and memory:** `board list --json`, `memory list --json`, `memory search --json`
- **Bulk import:** `sq import --json` (with or without `--dry-run`)
- **Commands that stay human-output-only:** `repair`, `renumber`, `docs`, `sync`, `init`,
  `sq workflow show` (the cheatsheet), `sq workflow lint` (which reports through its exit code —
  0 clean, 1 on any error)

Between major versions, new fields may be added to any shape; old fields stay present, named, and
typed identically. Every shape above is covered by a regression test, so it cannot drift on you
unnoticed.

---

## Tier 4: Python import paths (explicitly NOT public)

The underscore-prefixed module convention (`squads._models`, `squads._services._service`,
`squads._backends._claude_code`, …)
is the contract: **internal modules are not re-exported by package `__init__` files, and are not
part of the public API.** This is not a breaking change to state — squads has never shipped a
public library interface — but it is explicitly pinned to let integrators know where the boundaries
are.

### Shell completion

Verified install steps for bash and zsh completion are documented in the [top-level README](../README.md)
and are part of the supported-surface documentation. Completion may be added to other shells
additively post-1.0.

---

## Tier 5: Generated `.claude/` files (regenerable, never migrated)

Everything under `.claude/` is tool-owned and regenerable; deleting it loses nothing. Real definitions
live under the squad folder (`squads/agents/roles/`, `squads/agents/skills/`). `sq sync` regenerates
all tool-owned files to the current version.

**A roster entry's generated files track its status.** Retiring a role, skill or operator (moving it
to a status the lifecycle does not declare as live) withdraws its generated per-entry file, where it has
one, and its line in every compiled region; reactivating re-renders both in full, with no `sq sync`
needed. The definition under
the squad folder is never touched by a status change — so no content is lost, only its projection.

### Backend ABC surface

Backends register behind the `AgentBackend` abstract base class. It has **exactly seven** abstract
methods, and **it does not grow** — that no-growth promise is what makes the behaviour below free
for a new backend rather than something each one reimplements:

| Method | Responsibility |
|---|---|
| `ensure_scaffold` | create the backend's directories and base config; idempotent, never clobbers user content |
| `write_managed` | (re)write the roster- and version-dependent files: skill definitions, backend config, compiled regions |
| `generate_role_entry` | write this backend's entry for one role (a whole file or a section — either is valid) |
| `generate_skill_entry` | write this backend's entry for one skill |
| `remove_artifacts` | delete the backend's entry/entries for one item |
| `candidate_orphans` | report, read-only, the on-disk pointer/skill files this backend does *not* manage — warn-only candidates for `sq init` / `sq adopt` to print, never deleted |
| `managed_paths` | report, read-only, the paths this backend owns and that `sq check` expects to exist |

Two consequences a backend author should count on:

- **Status-awareness is not yours to implement.** No method takes or returns a status, and no
  backend ever sees one. The projection rule above — materialise an entry while its status is
  live, withdraw it otherwise — lives entirely in squads and is expressed through
  `remove_artifacts` plus a recompiled managed region. Implement the seven methods and withdrawal
  works.
- **Each backend stamps its own generated files.** Every managed region a backend injects into an
  otherwise user-owned file, and every file it owns outright, must carry a "regenerated by
  `sq sync`; do not edit by hand" notice where a reader actually sees it. Shared helpers wrap a
  managed region so this is consistent rather than reimplemented.

squads ships two backends — `claude_code` and `agents_md` — and both satisfy the same conformance
suite a third-party backend is held to. Backends self-register on import; see
[backends.md](backends.md) for the registration hook and a worked example.

Backend selection: `sq init --backend <name>` or `active_backends` in `.squads.toml`.

---

## Glossary

**Durable**: stored on disk and considered source of truth; survives migrations and upgrades.  
**Regenerable**: tool-owned; can be deleted and rebuilt without losing data or state.  
**SemVer**: Semantic Versioning (MAJOR.MINOR.PATCH). Breaking changes allowed only in MAJOR releases.  
**Additive**: new fields may be added; removals, renames, or type changes are not.  
**Frozen**: locked at 1.0 and subject to the stability contract.
