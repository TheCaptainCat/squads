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
schema. Versions compare numerically, segment by segment, never as raw strings; so
`"0.10" > "0.2"` holds.
Post-1.0, a schema change ships only with a MAJOR release of squads. The upgrade path is always
`sq migrate up`, which rebuilds the index from the item files, applies the ordered migration
runners, rebuilds the index again, and stamps the new version. It never stamps past an item file
it cannot index: such a file, or a squad that does not fit its declared vocabulary, stops it
with exit `1` before any runner, with nothing migrated and the schema unchanged (see
[migration.md](migration.md#before-the-first-runner)).

### ID numbering, padding, and exhaustion

The global sequence number is the durable identity of an item — `TASK-<n>` and `TASK-NNNNNN` (in refs or filenames)
resolve to the same item forever. The *number* never changes across a retype or repair; only the *prefix* moves, and only on a retype.

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
frontmatter (its `subentities:` list), not in the body. Only prose (the `:body` and `:discussion` regions)
stays in the body markers. Frontmatter is the source of truth, and that is what
makes the index rebuildable from files alone (see [internals.md](internals.md) § 4).

### Frontmatter is flat

An item's frontmatter is one flat mapping, with no nested container:

- **Core keys**, the same on every item: `id`, `sequence_id`, `type`, `title`, `slug`, `status`,
  `description`, `parent`, `author`, `assignee`, `priority`, `severity`, `labels`, `refs`,
  `subentities`, `created_at`, `updated_at`, `created_session`, `modified_session`. A core key
  holding a value of the wrong type makes the item unreadable, and the error names the file.
  `slug` is written on every role, skill and operator, and on any other item whose file carries it.
- **Attributes**, every other key. A type declares the ones it carries in the workflow spec
  (`[items.<type>.attributes]`, see [Project-level overrides](#project-level-overrides)); a custom
  badge field is stored the same way, under its code. A declared attribute holding a value of the
  wrong kind, or a missing required one, is reported by `sq check` and never makes an item
  unreadable.
- **Unknown keys are kept.** A key no declaration names is carried through every write, `sq
  repair` and every migration, with its value. A write removes or changes only the keys its
  command targets, so a key whose declaration is removed from an override stays in the files.
  The one exception is a closed set of role-definition keys, which the role catalog answers
  (`full_name`, `mission`, `responsibilities`, `agreements`, `color`, `can_spawn`, `skills`,
  `is_dev`): on a role whose type does not declare them as attributes, `sq repair`
  removes them, as do `sq adopt`, `sq renumber` and `sq migrate up`, which end with the same
  rescan (see
  [adoption.md § "What `sq repair` writes"](adoption.md#what-sq-repair-writes)).
- **A hand edit is indexed before the next write.** A key added or changed by hand puts the file
  ahead of the index: the next write to that item is refused until `sq repair` has run, and
  `sq check` reports the drift. The key is kept from then on.
- **Values are kept in their JSON form.** A YAML-only value is written back as its JSON equivalent
  the next time its item is written: an unquoted date or timestamp becomes the string of the same
  value (`2026-11-01` becomes `'2026-11-01'`), and a mapping key that is not a string becomes one.

### Comment headers

Every comment in a discussion region (an item's own, or a story's, subtask's or finding's) opens
with a header line that sq writes, followed by the author's bullets indented under it:

```
- [2026-10-16T08:09:29Z] `tech-lead` Olivia Lead:
- [2026-10-16T08:09:30Z] `op-zo` Zoë Müller:
- [2026-10-16T08:09:31Z] `operator` Operator:
```

The grammar:

```
header    = "- [" timestamp "] `" slug "` " name ":"
timestamp = YYYY-MM-DDTHH:MM:SSZ      (UTC, whole seconds)
slug      = [a-z0-9][a-z0-9-]*        (the characters of an @mention)
name      = one or more characters, on the same line
```

- **A header starts at the left margin.** A line of the same shape that is indented is part of the
  comment above it, not the start of a new one: a nested `- [x] Done:` checkbox or a pasted log
  line never splits a comment.
- **The slug is the author's identity; the name is a snapshot.** The slug is the author's roster
  slug, the same one `--as` takes. The name is the author's display name at the moment the comment
  was written, kept for people to read. When a display name changes later, older headers keep the
  old name under the same slug. That is history, not drift, and nothing rewrites it. The writer
  collapses line breaks in a name to spaces, and writes the slug in place of an empty name.
- **Two author slugs are written for authors that are not roster entries:** `operator`, named
  `Operator`, for a comment written with `--as operator`, and `squads`, named `squads`, for an
  entry sq writes itself (when an item is retyped, for example).
- **One author namespace.** Every role (developer roles included) and every operator, live or
  retired, plus `operator` and `squads`, share one namespace, in which a slug names exactly one
  author. Skills are outside it: a skill never authors anything, and `--as`, `--author` and
  `--assignee` accept a role or an operator only. The slugs in the namespace follow two rules:

  ```
  operator slug = "op-" [a-z0-9] [a-z0-9-]*
  role slug     = [a-z0-9] [a-z0-9-]*, not "operator", not "squads", not starting with "op-"
  ```

  Together they keep every role slug, every operator slug and the two system slugs apart, so a
  header's slug alone tells you whether its author is sq, the anonymous author, an operator or a
  role.
- **Creating an operator with any other slug is refused**, through `sq operator add --slug` or an
  `sq import` operator `create`, with exit `1` and nothing written. The message gives the
  compliant form when one exists:

  ```
  error: operator slug 'Anna' must start with 'op-' and be lowercase letters, digits and hyphens (e.g. 'op-anna')
  ```

  A typed slug is stored as typed: it is never lowercased or prefixed. The derived slug (`op-` and
  the first name) always complies.
- **Creating a role with `operator`, `squads` or a slug that starts with `op-` is refused**, through
  `sq role activate`, `sq dev add` or `sq import`, with exit `1` and nothing written:

  ```
  error: slug 'op-dev' is reserved for operators (the 'op-' prefix); a role needs another slug
  ```

- **No comment can be written as `squads`.** `--as squads` is refused by item and sub-entity
  `comment`, by `sq board post`, and for an `sq import` comment (its `as`, or the `--as` default),
  whatever the roster holds, so the entries sq writes itself cannot be imitated:

  ```
  error: cannot act as 'squads': that slug is reserved for system entries
  ```

  `--as operator` always writes the anonymous author, whatever the roster holds.
- **`sq check` reports an entry that breaks these rules.** A role or operator that breaks them can
  still arrive, from a hand-edited file or from two branches that each added an operator under the
  same slug. The `roster_slug_valid` rule reports each such entry, live or retired, and each entry
  that shares its slug with another, once per entry, with the remedy:

  ```
  error OP-11: operator slug 'qa' does not start with 'op-'; it is also held by ROLE-5 — remedy: sq operator OP-11 rm --purge, then sq operator add "Anna Lee" --slug <compliant slug>
  ```

  The rule is one of the always-on squad-wide checks: it runs on every `sq check` at `error`, and
  cannot be selected, dropped or given another level (see
  [overrides.md § "Squad-wide checks"](overrides.md#squad-wide-checks-the-squad-table)). It never refuses a write, so the remedy it names can run.
  Headers the entry already wrote keep its old slug.
- **A squad holding such an entry does not migrate to 0.16.** `sq migrate up` refuses it until the
  entry is replaced; see
  [migration.md](migration.md#a-role-or-operator-whose-slug-breaks-the-rules).

A squad written by a release before 0.16 holds headers without the slug (`- [<timestamp>]
<name>:`). `sq migrate up` rewrites them once; see
[migration.md](migration.md#upgrading-to-016-the-schema-step).

### A roster slug never changes

The slug of a roster entry is fixed when the entry is created: a role's is its catalog key or
its project role file's name, whatever `--name` it is given, a developer role's is the `--slug`
given to `sq dev add` or else comes from `--tech` (`sq dev add --tech python` gives `python-dev`), a skill's from its catalog entry or the name
given to `sq skill add`, and an operator's from its first name (`op-` plus the first name) or
`sq operator add --slug`. After that no command, override or
migration changes it, and the entry's file keeps its name. Comment headers, item `author` and
`assignee` fields and `@mentions` all name an author by slug, so a slug that changed would orphan
them.

- **Display names are not identity.** Changing a role's or an operator's display name leaves its
  slug, its file name and every header already written as they were.
- **An override cannot rename.** A role override is bound to its slug by its file name, and one
  that declares a different `slug` is refused:

  ```
  error: role override …/.overrides/roles/architect.toml: declares slug 'arch' but the filename says 'architect' — the filename is canonical; rename the file or drop the 'slug' key
  ```

- **A purged slug can be taken again.** A slug freed by `rm --purge` may be given to a new entry,
  and creation does not look at comment history. Comments written before the purge then carry the
  new entry's slug, and read as its comments wherever an author is matched by slug; their name
  snapshot still shows who wrote them.

### Project-level overrides

A squad may customize bundled templates, roles, and item-type vocabulary under `.overrides/`, a
folder in the squad directory. The frozen surfaces are:

- **Layout:** `<squad-dir>/.overrides/{templates,roles}/` and three spec documents,
  `.overrides/workflow.toml`, `.overrides/roles.toml` and `.overrides/playbook.toml`. Templates
  mirror bundled template names 1:1; per-role files are TOML keyed by slug (e.g., `architect.toml`);
  `workflow.toml` is the squad's vocabulary delta — item types, statuses, lifecycles, badge
  collections, status roles, ref kinds, derived views, and the squad-wide checks it selects; `roles.toml` is a delta over the whole role
  catalog (its roles, bundles and the `[dev]` table developers are built from); `playbook.toml` is a delta over the playbook, the
  per-type guidance each role gets.
- **Precedence:** per-file, project → bundled. Presence of a file is the override. Templates
  override whole-file; a role resolves bundled, then `roles.toml`, then its per-slug file, merging
  field-wise; the workflow override composes over the bundled vocabulary and **may shadow a
  built-in**, not only add to it.
- **A role's name is stored.** A role is named when it is created: by `--name` (or, at `sq init`,
  a `--name` flag, `[init.names]` or the prompt), otherwise by the `full_name` its per-slug file,
  then `roles.toml`, then the bundled catalog gives it, and for a developer by the name pool. From
  then on the stored name is the role's name: no change to an override or to the bundled catalog
  renames an active role, and neither `sq sync` nor a migration does. See
  [overrides.md § "Which name wins"](overrides.md#which-name-wins).
- **Attribute grammar (frozen):** a type declares its attributes in `[items.<type>.attributes]`,
  one `<name> = { kind = …, required = …, settable = … }` entry each. `kind` is one of `str`,
  `list`, `bool`, `date`; `required` and `settable` default to `false` and `true`. An attribute may
  not take the name of a core key, of another attribute or badge field on its type, of a key
  `--json` adds to an item row (`badges`, `body`, `discussion`, `matched_subentities`), or
  `extra`, `path` or `prefix`. The `role` and `skill` attributes the bundled spec declares may be
  added to but not dropped or given another kind. `extra_fields` is not a key of a type and is
  refused at load.
- **Spec override grammar (frozen):** the same for all three spec documents. Deep recursive merge
  at leaf granularity — tables recurse per key, and a leaf value replaces its counterpart. A plain
  array is a leaf, replaced wholesale and never element-merged. **Splat-refs** are the opt-in for extending a bundled list without
  restating it: `$(path)` splices the bundled value at *path* as one element and `$(*path)` spreads
  a bundled list's elements into the surrounding list, with `$(self)` / `$(*self)` addressing the
  key being written. A path is a dot-joined chain of TOML bare keys (ASCII letters, digits,
  underscores, hyphens), with `self` the only special segment. Resolution is against the bundled spec
  only, so the merge is order-independent and cycle-free, and a splat only ever adds. A string is read
  as a token only when it *begins* with an unescaped `$(` and is a token in its entirety; `$$(`
  escapes a string that must literally begin `$(`. There is no interpolation. The sigil is reserved
  in **every** string position, keys as well as values: a token-shaped key is refused — there is no
  splice-into-a-key operation — and the refusal names the escape, so `$$(` still gets you the literal
  key you want. A top-level `[selected]` table shrinks named sections to the set that survives (in
  `workflow.toml` and `roles.toml`; the playbook has no section to shrink, so it refuses one). The
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
  (`# squads:override-base:<version>`) in a per-role file and in each of the three spec documents.
  `sq check` warns if the bundled counterpart changed since that base version (drift), and errors if
  a template is missing required markers. A template override must always carry the stamp. A
  per-role file for a bundled role, and a spec document that shadows a bundled entry, must carry it
  too — unstamped and shadowing is an error-level `sq check` finding (and a `sq workflow lint` one
  for the workflow override), though not a load-time refusal; an add-only spec document, or a
  per-role file defining a new role, needs no stamp. `sq migrate` never rewrites overrides; the `sq override`
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
A singular `default_backend: str` field is read as a single-element list, so both forms are valid
input.

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
sq role 2 rm --purge     # delete the entry and its file
sq skill 5 show
sq skill 5 link-role architect     # scope a custom skill to a role (and unlink-role to undo)
sq operator 3 show
```

`rm` on a role, skill or operator requires `--purge`. Without it, it exits `1`, writes nothing and
names the two commands to choose from: `rm --purge` to delete the entry, and `status Archived` to
retire it (offered only while the entry is live). See
[roles.md § "Removing a roster entry"](roles.md#removing-a-roster-entry).

**Creation commands stay verb-first** at the group level, receiving a catalog slug or a new name:

```bash
sq role activate architect           # group-level verb-first
sq role activate <slug> --name "…"   # with optional custom name
sq skill add <name>
sq operator add "<name>"
```

**Bundled catalog:** `sq role catalog` is the dedicated subcommand for the bundled-but-not-activated
role catalog (shows slug, name, title, default).

**Slug resolution:** for `role show`/`regen`/`rm`/`status`/`set-default`, slug is a valid address
form in addition to full ID and bare number. A slug that equals a verb of its group cannot be used
as an address, so creation refuses one: role activation refuses `activate`, `catalog` and `list` as a slug, and `sq skill add`
refuses `add`, with exit `1` and nothing written:

```
error: role slug 'list' is a verb of `sq role` and cannot be addressed by slug; pick another slug
```

`sq check`'s `roster_slug_valid` reports a role or skill that already holds such a slug, with its
remedy. Every operator slug starts with `op-`, which no `sq operator` verb does.

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
| `contract` | `prd`, `c` |
| `milestone` | `mile`, `m` |
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

- `sq migrate up` — rebuild the index from the item files, run every pending automatic migration,
  rebuild the index, stamp the new schema; refused with exit `1`, nothing migrated, when an item
  file cannot be indexed or the squad does not fit its declared vocabulary
- `sq migrate help` — the changelog index
- `sq migrate chlog vA..vB` — manual steps for migrations shipped in `(vA, vB]`
- `sq migrate repad <width>` — raise the filename-padding width (see Tier 1)
- `sq migrate rename-type <old> <new>` — bulk-rename every item of one type to another (same
  semantics, new prefix and folder), for when a vocabulary override renames a type you already
  have items in
- `sq migrate rename-status <type> <old> <new>` — bulk-relabel one type's items from one status
  name to another; a relabel, not a workflow move

On a squad whose schema differs from the package's, only `up` (on a squad behind the package),
`help` and `chlog` run; `repad`, `rename-type` and `rename-status` are refused like every other
command (see [migration.md](migration.md#what-runs-on-an-out-of-date-squad)).

Runner modules are private; never use `python -m`; `sq migrate` is the only entry point.

### Bulk import

`sq import <file>` loads a JSONL event stream in one process — the supported path for bringing
history in from another tracker. Every event is validated first (type and status vocabulary,
transition legality, actor registration, marker safety), collecting *all* problems with line
numbers before writing anything; only a fully clean file is applied, in a single transaction.
`--dry-run` stops after validation and prints the projected handle → ID plan; `--json` emits the
result machine-readably. The global `--at` sets the file-level default timestamp; `--as` sets the
default acting slug. Attribution has no silent fallback — an event with no `as` of its own, no
prior event's to inherit, and no `--as` fails validation naming the missing actor. Once the file
is applied, the items it touched are checked; an error-level finding is printed and the command
exits `3`, not `1`, because the write committed and stands. See [adoption.md](adoption.md).

### Exit codes (distinct codes for distinct failures)

Frozen contract:

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | squads runtime error (schema mismatch, corrupt index, validation failure, etc.) |
| `2` | Usage error (bad arguments, missing required flag) |
| `3` | Integrity findings reported: `sq check` found issues, or `sq import` applied the file and the integrity check that follows it found error-level issues |
| `4` | The result is incomplete — stdout carries a valid payload in its documented shape, and entries are missing |

The distinct code for integrity findings lets CI distinguish "issues were found" from "command errored".

#### Partial results and code `4`

A **partial result** is what a listing produces when its payload is valid and in its frozen shape,
but entries are missing because part of the corpus could not be read — an item file with no read
permission, a memory or notice file that has gone unreadable. The commands bound by this are
`sq inbox`, `sq search`, `sq board list`, `sq memory <role> list` and `sq memory <role> search`, and
any listing added later with the same property: it emits a result payload you are meant to consume,
and that payload can come back short.

- `4` means the command did what was asked. Everything that *could* be read is on stdout, in the
  shape that command always emits, and something is missing from it.
- `1`, `2` and `3` outrank `4`. It is returned only where the command would otherwise have returned
  `0`, so a partial result never masks a more specific outcome.
- It does not depend on `--json`. Human output returns `4` on the same condition.
- Commands outside the class keep the codes they had. `sq check` turns an unreadable file into an
  error-level issue and exits `3`, because a clean check over a partly-read corpus is a *false*
  clean. `sq repair` and `sq migrate up` report a mutation rather than a result, and keep `1`.

`4` is the one bit that says *stdout is worth parsing*, and it is available to a shell script that
parses nothing. A consumer that branches on `0`/`1`/`2`/`3` and treats anything else as an error is
safe under it: it stops, loudly, rather than reporting a short answer as the whole one.

Where a short answer is acceptable to a given caller, test for `4` explicitly rather than widening
what counts as success.

### Ref-kind vocabulary (declared, bound by semantic)

What is frozen here is the *validation behaviour* and the semantic binding, not any particular
kind name — the same shape as status-set validation below.

Ref kinds are declared vocabulary. The bundled set is the default; a project may declare its own,
and may rename or drop a built-in it does not use, subject to the same live-corpus refusal that
protects a type or a status. A kind the merged spec does not declare is still rejected, and the
refusal lists the accepted set. Engine behaviour binds to a kind's declared **semantic role**,
never to its name — so a renamed dependency kind keeps driving `sq blocked`, and a kind with no
semantic is navigational.

Four semantic roles are declarable today, and what the declared set must supply is checked rather
than named. The set of roles is an open set (see [Tier 3](#tier-3---json-output-shapes-stable-additive-changes-only)):
a later release may add one, so a reader of a ref kind's `role` or a graph edge's `edge_semantic`
tolerates a value it does not recognise.

- **`dependency`**, in the `blocker` or the `dependent` direction — the two ends of the one edge
  `sq blocked` walks. At most one kind per direction; declaring neither direction is legal and
  yields an empty `sq blocked` rather than a stranded item.
- **`preload`** — a skill's edge to the role whose generated pointer preloads it. Exactly one kind
  carries it, because the resolved list is materialised into generated agent config.
- **`supersession`** — what `sq check` reads on a superseding record. Zero is legal.
- **`default`** — the kind a ref written with no `--kind` resolves to. Exactly one kind carries it,
  and it is mandatory: such an edge is stored bare, without its kind, so the stored form must
  always resolve. Renaming that kind relabels those edges rather than re-pointing them, because the
  bare form binds to the semantic and never to a spelling.

A kind that declares no semantic role is navigational — display and traversal only — and that is
what a project-declared kind gets unless it says otherwise. A kind's key must be a TOML bare key
and may not contain `:`, the separator the stored `ID:kind` form partitions on. `sq workflow
ref-kinds` lists the set the active spec declares.

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
renamed or retyped within a major version. A key is frozen in its name, its JSON type, its presence
(`null` rather than omitted where a shape states that convention) and its meaning. What its *value*
promises depends on its class, and a field reference marks each key whose value is not a fixed
squads format with one of three words:

- **vocabulary** — a name your squad declares: an item type, a status, a priority or other badge
  code, a ref kind, a sub-entity kind or local id, a badge field (all from the active spec), or an
  assignee slug (from the roster). Frozen: that the value names an entry of that catalog or roster.
  Not frozen: which names exist. Read the catalog; never hardcode a name.
- **open set** — a value squads defines, from a set that may grow between majors. Handle a value
  you do not recognise without failing, and never infer anything from the set looking complete. The
  forms that exist today are listed with the key.
- **display** — human text. The key is frozen; its content is not, and is never parsed or compared.

In a field reference that carries these marks, a key with no mark has a fixed squads format, frozen
with the key: an item id, a boolean, `direction`'s `in`/`out`, nested `children`. A key moves to a
stricter class freely; it moves to a looser one only as a stated contract change.

The frozen surface includes:

- **Reading the board:** `list`, `tree`, `graph`, `inbox`, `search`, `blocked`, `workload`, `mine`,
  `show`, `refs`, `comments`, `create`, `check`, plus each sub-entity list command
  (`sq task <n> subtasks --json`, `sq feature <n> stories --json`, `sq review <n> findings --json`)
  and each single sub-entity (`sq feature <n> story <k> show --json`, and the same for a subtask or
  a finding), which emits that one sub-entity's object — the same shape the parent's `show --json`
  nests under `subentities`, `body` / `badges` / `discussion` included
- **Search, tree and graph:** their fields, in emitted order, with each key's class:

  `sq search --json` emits a bare array, one object per matching item:

  | Key | Class | Value |
  |---|---|---|
  | `id` | | the item id |
  | `title` | | the item's title, as stored |
  | `type` | vocabulary | item type |
  | `status` | vocabulary | status |
  | `hits` | | array of `{region, location, snippet}`, one per match |
  | `hits[].region` | open set | where the hit was found: `title`, `description`, `body`, `discussion#<n>` (the *n*-th comment), `<kind>:<local_id>` (a sub-entity's heading or body) or `<kind>:<local_id>:discussion#<n>`; the kind and local id inside it are vocabulary |
  | `hits[].location` | display | a human label for the same place |
  | `hits[].snippet` | display | the matching line |

  `sq tree --json` emits a bare array of root nodes; each node is:

  | Key | Class | Value |
  |---|---|---|
  | `id` | | the item id |
  | `type` | vocabulary | item type |
  | `title` | | the item's title, as stored |
  | `status` | vocabulary | status; join it to `sq workflow statuses --json` and `sq workflow roles --json` for open or settled |
  | `priority` | vocabulary | priority code, or `null` |
  | `assignee` | vocabulary | assignee slug, or `null` |
  | `blocked` | | boolean: the item is one `sq blocked` lists |
  | `badges` | vocabulary | object of badge field to badge code; keys and values both name spec entries |
  | `anchor` | | boolean: `true` only on a root invented for a parent cycle, which nobody wrote as a root |
  | `children` | | nested nodes of the same shape |

  `sq graph --json` emits one root object; each node is:

  | Key | Class | Value |
  |---|---|---|
  | `id` | | the item id |
  | `type` | vocabulary | item type |
  | `status` | vocabulary | status |
  | `priority` | vocabulary | priority code, or `null` |
  | `badges` | vocabulary | object of badge field to badge code |
  | `assignee` | vocabulary | assignee slug, or `null` |
  | `edge_kind` | vocabulary | the ref kind of the edge that reached this node, as spelled in the project; `null` on the root |
  | `edge_semantic` | open set | that kind's semantic role: today `dependency`, `preload`, `supersession`, `default`, or `null` (the root, a navigational kind, or a kind the spec does not declare). Branch on this, never on `edge_kind` |
  | `direction` | | `out` (the parent node carries the ref to this one; on a dependency edge, the parent depends on it), `in` (this node carries the ref to the parent), or `null` on the root |
  | `seen` | | boolean: the node was already expanded elsewhere in this graph, so its `children` is empty |
  | `children` | | nested nodes of the same shape |

  A graph node carries no `title`.
- **Item rows:** an item object from `list`, `show`, `create` or `mine` is the item's core keys,
  `path` (the item file's path relative to the squad folder, such as `tasks/TASK-NNNNNN-x.md`),
  each attribute its file stores, at the top level beside them, and the keys the command adds
  (`badges`, `body`, `discussion`, `matched_subentities`). There is no nested container. An
  attribute appears only when the file stores it, so a reader learns a type's possible attributes
  from `sq workflow types --json` (`attributes`: name to `{kind, required, settable}`), not from
  the rows. A key stored under the name of an added key stays in the file and out of the row.
- **Roster viewers:** `role catalog`, `role list`, `role <addr> show`, `skill <addr> show`,
  `operator list`, `operator <addr> show`. Skills have no dedicated `skill list` — use the generic
  `list -t skill`
- **The workflow catalogs** — the machine-readable form of your squad's *active* vocabulary,
  bundled plus any override, and the surface to read instead of hardcoding a name:

  | Command | One row per | Fields |
  |---|---|---|
  | `sq workflow types --json` | item type | `type`, `order`, `prefix`, `reserved`, `category`, `subentity_kind`, `lifecycle`, `fields`, `attributes`, `labels` |
  | `sq workflow subentity-kinds --json` | sub-entity kind | `subentity_kind`, `lifecycle`, `plural`, `local_prefix`, `container_heading`, `completion`, `maps_parent_story`, `fields` |
  | `sq workflow collections --json` | badge collection | `collection`, `label`, `ordered`, `default`, `badges` |
  | `sq workflow statuses --json` | status | `status`, `role`, `badge` |
  | `sq workflow roles --json` | status role | `role`, `settled`, `hidden`, `color`, `live`, `blocked` |
  | `sq workflow lifecycles --json` | lifecycle | `lifecycle`, `initial`, `states`, `transitions` |
  | `sq workflow views --json` | derived view | `view`, `source_kind`, `source_name` |
  | `sq workflow ref-kinds --json` | ref kind | `kind` (vocabulary), `label` (display), `hint` (display), `role` (open set), `direction` |

  Each emits a bare JSON array, one row per declared entry in a documented order, with **every key
  present on every row** — `null` for absent, never omitted. They are designed to be **joined**, and
  a reference always carries the identity key name of the row it points at: a type's or kind's
  `fields[].collection` keys into the collection catalog, a type's `subentity_kind` keys into the
  sub-entity kind catalog, and a status's `role` keys into the role catalog — that's where
  `settled` / `hidden` / `color` / `live` / `blocked` live. `role` is always the *resolved* role name, never
  null, so `null` stays available to a client meaning "not loaded yet". `terminal` and `is_open`
  are deliberately not fields anywhere: they are `settled` / `not settled` on the role catalog.
  A ref kind's `role` is its semantic role (`null` on a navigational kind), and `direction` is its
  end of the dependency edge (`null` on every kind but the two `dependency` ones). `role` is an
  open set: today it is one of `dependency`, `preload`, `supersession`, `default` or `null`.

  A type's or a kind's `lifecycle` keys into the lifecycle catalog the same way: `initial` is the
  starting status, `states` is every status the machine declares — in breadth-first order from
  `initial`, documented and deterministic — and `transitions` is every allowed move as
  `{from, to}` objects in that same order. See
  [workflow.md](workflow.md#joining-the-catalogs).

  A `views` row's own `source_name` keys into whichever catalog its `source_kind` names —
  `ref-kinds`, `subentity-kinds` or `types` — the one join whose destination is decided by a
  sibling field rather than fixed.
- **Derived views resolved against an item:** `sq workflow view <name> <id> --json` skips
  presentation entirely and emits the resolved source in the shape its own kind already has a
  serializer for — never a shared envelope. A `ref`/`subtree` source matches `sq tree --json`'s
  per-node rows; a `subentity` source matches the per-kind list `--json` (`sq <type> <n> <kind>s
  --json`); `role` matches `sq role <slug> show --json`; `self` matches the host item's own `show
  --json` plus a `spec` key, `{schema_version, override, digest}`; `playbook` has no existing
  counterpart, so its own shape is `{type, lane, roster}` (`lane` is `null` for a type outside
  every guide's lane domain). No shape carries a `fields`/`group_by`/`groups` key.

  In the `self` `spec` key, `digest` identifies the merged workflow spec that resolved the
  payload: the bundled spec with any project override applied. Compare it for **equality only**.
  It is opaque, so never order it, parse it or compute it yourself. Two different merged specs
  never share a digest, but the reverse is not promised: a squads release can change the digest
  with no change in meaning. Treat a changed digest as "re-read the catalogs" (`sq workflow types
  --json` and its siblings). `override` is `true` when a project `.overrides/workflow.toml` was
  merged into that spec. It is for display, not for detecting change. `digest` is a field
  addition to this shape, which this tier permits between majors.
- **Override inspection:** `override list --json` (an array of `{name, kind, base_version, state}`)
  and `override diff --json` (an array of `{name, kind, base_version, base_available, delta_mine,
  delta_upgrade}`, one row for the override named, or one per drifted override when none is named)
- **The reflog:** `sq reflog --json` emits the Tier 1 line schema —
  `{v, ts, actor, op, target, delta, session_id, parent_session_id}`. Note the difference from the
  file: the two session fields are always *present* here, `null` when absent, where on disk they
  are omitted. They carry the same untrusted, observability-only caveat either way
- **Notices and memory:** `board list --json`, `memory list --json`, `memory search --json`, and
  `memory show --json` — one object for the memory you addressed, `{slug, summary, created_at,
  tags, body}`, the whole entry including its body text. A `memory list --json` row carries
  `created_at` alongside `slug`, `filename` and `description`. That is a field addition, which this
  tier permits between majors, and it is named here rather than left to be discovered from a sample
  of output because any age or staleness display is built on it
- **The omissions report** — how a `--json` reader learns its listing is short. This is the
  machine-readable half of a partial result (exit code `4` above) and a property of every listing in
  that class, not a quirk of any one of them. Under `--json`, a command that left something out
  writes **one compact line to stderr** holding a single JSON object:

  ```
  {"omitted":[{"code":"unreadable","source":"TASK-<n>","message":"<path> could not be read: …"}]}
  ```

  - `omitted` holds one entry per thing the result leaves out. The report is written only when that
    list would be non-empty, so its presence is the signal: an absent report and an empty `omitted`
    mean the same thing. There is no `partial` boolean, because that is exactly "`omitted` is
    non-empty", and the exit code already carries the same bit for a caller that cannot parse.
  - `code` is the machine class of the omission, an open set. `unreadable` is the only value squads
    emits today. **Do not branch on it to decide whether the result is partial** —
    an entry whose `code` you do not recognise still means part of the result is missing.
  - `source` is what was left out, as squads identifies it: an item ID where there is one, otherwise
    a squad-relative path. It is display; do not parse it.
  - `message` is display: the human sentence — the same text human-mode output prints for that omission.
  - Every key is present on every entry, `null` for absent, matching the convention the workflow
    catalogs set.

  **Find the report as the one line of stderr that parses as a JSON object.** Stderr carries prose
  that is not part of any result — the `sq sync` version notice, for one — so "stderr is JSON" is
  false where "at most one line of stderr is JSON" holds. The report never goes to stdout, and
  stdout stays exactly one JSON document.

  **The payload shapes do not change for it.** No envelope, no added key, no sentinel row: a
  degraded listing emits the same frozen shape a clean one does, for the entries it could read.
  Human output keeps its `error: <message>` prose, one line per omission; `--json` emits the report
  *instead of* that prose, not alongside it
- **Discussion entries:** every entry of a `discussion` array in `show --json` (an item's own, and
  each sub-entity's, whether nested under `subentities` or from the sub-entity's own `show --json`)
  and every entry of `comments --json` is `{author, author_slug, ts, body}`. `author` is the
  display name the header recorded and `author_slug` is the author's slug (see
  [Comment headers](#comment-headers)); match an author on `author_slug`, never on `author`.
  `search --json` and `inbox --json` carry no `author_slug`: a search hit names the author by
  display name in its `location` and `snippet`, and an inbox row names no author
- **Bulk import:** `sq import --json` (with or without `--dry-run`)
- **Commands that stay human-output-only:** `repair`, `renumber`, `docs`, `sync`, `init`,
  `sq workflow show` (the cheatsheet), `sq workflow lint` (which reports through its exit code —
  0 clean, 1 on any error)

Between major versions, new fields may be added to any shape; old fields stay present, named, and
typed identically. Every shape above is covered by a regression test, so it cannot drift on you
unnoticed.

**Where each shape's fields are written down.** This document is the authority for every shape it
enumerates: the workflow catalogs, search, tree and graph, derived views, override inspection, the
reflog and the omissions report. Command help may describe a payload, but it is not the field
reference. The plainer listings (`list`, `blocked`, `workload`, `mine`) are not enumerated here:
the fields they emit are their contract. Listing a key here records a promise its shape already
makes, and leaving one out never exempts it: the promise above covers every field a shape emits.

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
and are part of the supported-surface documentation. The same `--install-completion` /
`--show-completion` flags also generate fish and PowerShell completion scripts; their install
steps are not verified, so those two shells sit outside the supported surface until they are.

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
| `write_managed` | (re)write the roster- and version-dependent files: backend config, compiled regions, and each managed skill's pointer and body-file shape |
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

**Four more methods are non-abstract, with a working default**, so they don't count against the
seven: `managed_entry_paths`, `restriction_fragment`, `render_role_entry` and
`render_skill_entry`. A bundled backend overrides them to declare its per-entry pointers and to
answer, respectively, which projected value currently constrains the session (rather than merely
configuring or supplying it) and what it would write for one entry without writing it — the seam
`sq check`'s currency comparison consumes. A third-party backend written
against the documented seven still instantiates and simply never participates in that comparison,
exactly as one that declares no `managed_entry_paths` never participates in the presence check.

**Every host answers the same five questions, in its own terms.** The containment rule above is
universal; a host's answer to each question is not, so a new backend answers all five from its own
host's documentation alone: whether an agent under this host can execute a command at all; which
projected values this host's configuration has a place for; which of those it must have to find
and dispatch an entry; which of those constrain the session rather than configure it; and what a
pure render of one entry looks like. See `docs/backends.md` for the full five and both bundled
backends' worked answers.

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
**Vocabulary**: a `--json` value that names an entry your squad declares (a type, status, badge code, ref kind, slug); which names exist is not frozen.  
**Open set**: a `--json` value from a squads-defined set that may grow between majors; tolerate one you do not recognise.  
**Display**: a `--json` value that is human text; never parse or compare it.
