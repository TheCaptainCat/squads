# The squads stability contract

squads is approaching its 1.0 release. This document defines the public surfaces that will be
stable after 1.0, and what each surface promises. The contract is tiered by durability: strongest
at tier 1, weakest at tier 5. Use this guide to decide what you can safely build on, and what may
shift with a new release.

## The migration promise

**Any squad created on any 0.x release reaches 1.0 intact via `sq migrate up`.**

This is the strongest promise the contract makes. Your items, your metadata, your folder structure
— all preserved. The migration runner is ordered and testable, with manual runbooks for the parts
that need judgment. See [migration.md](migration.md) and the runner source (`_migrations/` in the
repo) for how it works.

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

The global sequence number is the durable identity of an item — `TASK-7` and `TASK-000007` (in refs or filenames)
resolve to the same item forever. The *number* never changes across a retype or repair; the *prefix* stays fixed.

- **Display:** every human-facing surface (frontmatter `id:`, CLI output, `--json`) renders IDs unpadded (e.g. `TASK-7`).
  This is fixed and not user-configurable.
- **Filenames:** on disk, items use zero-padded names (`TASK-000007-slug.md`) for lexicographic sorting. The padding
  width is stored in the index with a default of 6, reconstructed by `sq repair`. Raised one-way via `sq migrate repad
  <width>` (never lowered). References written before a repad retain their original width — readers understand both.
- **Exhaustion:** `sq create` errors with an index-full message at capacity, never silently
  widening. If a squad fills its current filename width, raise the width explicitly and the counter
  continues.


### IDs are never reused

Removal preserves the counter high-water mark; a removed sequence number is permanently retired. A
gap in the sequence (e.g., `…TASK-000006, TASK-000008…` after removing 000007) is normal, sanctioned,
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

A squad may customize bundled templates and roles under `.overrides/`, a folder in the squad
directory. The frozen surfaces are:

- **Layout:** `<squad-dir>/.overrides/{templates,roles}/`. Templates mirror bundled template names
  1:1; roles are TOML files keyed by slug (e.g., `architect.toml`).
- **Precedence:** per-file, project → bundled. Presence of a file is the override. Templates
  override whole-file; roles merge field-wise by slug.
- **Staleness & drift:** overrides carry a `<!-- squads:override-base:<version> -->` stamp. `sq
  check` warns if the bundled counterpart changed since that base version (drift), and errors if a
  template is missing required markers. `sq migrate` never rewrites overrides; the `sq override`
  command group (`scaffold` / `diff` / `update` / `list`) is the user-owned upgrade path. `sq
  override diff` shows two deltas: Δ-mine (your customisation vs current bundled) and Δ-upgrade
  (base-version bundled vs current bundled), so you see exactly what to merge.
- **Manifest:** `squads._rendering/templates_manifest.json` ships as package data, mapping
  version → {template_name → sha256_hex}, used for drift detection and base-version recovery.

See [docs/overrides.md](overrides.md).

### Reflog on-disk format

An append-only JSONL file at `<squad>/.reflog.jsonl` records every mutation: create, status,
update, comment, ref, sub-entity, retype, remove, migrate. It is **ADVISORY and explicitly NOT a
source of truth** — `load`, `check`, and `repair` never read it; `sq repair` rebuilds
`.squads.json` from frontmatter alone. A missing, truncated, or garbage reflog never affects state
or command behaviour.

The line schema (frozen field set):

- `v` — schema version (currently coupled to the index `SCHEMA_VERSION` at 0.3); whether to decouple is open
- `ts` — ISO-8601 timestamp with Z suffix
- `actor` — who made the change (slug or operator ID)
- `op` — operation name (closed vocabulary: create, status, update, comment, ref, subentity,
  retype, remove, migrate)
- `target` — item ID + type
- `delta` — before→after summary (not a replayable diff)

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
sq show TASK-7           # full ID (unpadded)
sq show TASK-000007      # also works (padded form for backward compatibility)
sq show 7                # bare number (resolves the item at sequence 7, whatever its type)
sq show BUG-7            # ERROR: item 7 is a task, not a bug
```


### Item-first grammar for agent types

Commands that address an existing role, skill, or operator follow the **item-first pattern** used
everywhere else:

```bash
sq role 2 show          # item-first: type, number, verb
sq role 2 regen         # regenerate
sq role 2 rm            # remove
sq skill 5 show
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

**Slug resolution:** for `role show`/`regen`/`rm`, slug is a valid address form in addition to full
ID and bare number.

**Standalone list commands removed:** `sq role list`, `sq skill list`, `sq operator list` are
removed pre-1.0 in favour of `sq list -t <type>`.

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
number is the stable identity: a `TASK-000020` becomes `BUG-000020`, the `.md` file moves folders and
reprefixes, body bytes are preserved verbatim, and incoming edges (refs, children parent, prose
mentions) are rewritten in the same transaction. `sq check` stays clean.

### Migrate sub-app surfaces

The `sq migrate` sub-app's frozen surface:

- `sq migrate up` — run every pending automatic migration, rebuild the index, stamp the new schema
- `sq migrate help` — the changelog index
- `sq migrate chlog vA..vB` — manual steps for migrations shipped in `(vA, vB]`
- `sq migrate repad <width>` — raise the filename-padding width (see Tier 1)

Runner modules are private; never use `python -m`; `sq migrate` is the only entry point.

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

The eight built-in kinds are frozen: `related` (default, no colon needed), `blocks`, `depends-on`,
`implements`, `fixes`, `addresses`, `supersedes`, `duplicates`. Unknown kinds are rejected.

A project-declared custom-kind extension is reserved for a future release and will be additive and
non-breaking. The built-in kinds' meanings stay fixed.

### Bug lifecycle and status-set validation

Bugs have their own workflow (not the generic work-item machine):

```
Initial: Open
Open → { InProgress, WontFix, Cancelled }
InProgress → { Fixed, Blocked, WontFix, Cancelled }
Fixed → { Verified, InProgress }
Verified → { InProgress }
Blocked → { InProgress, WontFix, Cancelled }
WontFix → { Open }
Cancelled → { Open }
Terminal: Verified, WontFix, Cancelled
```

Status-setting validates against the **type's workflow at set-time**: an out-of-workflow status
(e.g., `Done` for a bug) is rejected with `StatusNotInWorkflowError` when set. `--force` relaxes
only the transition edge, never the vocabulary check.

---

## Tier 3: `--json` output shapes (stable; additive changes only)

Read commands emit stable JSON shapes. **Additive** means fields may be added, never removed or
renamed or retyped within a major version. The frozen surface includes:

- Commands: `list`, `tree`, `inbox`, `search`, `blocked`, `workload`, `mine`, `show`, `refs`,
  `create`, `check`, plus sub-entity list commands (`sq task <n> subtasks --json`, etc.)
- The catalog viewers: `role catalog`, `skill list -t skill`, `operator list -t operator` (all
  with `--json`)
- Commands that stay table-only: `repair`, `docs`, `workflow`, `override list`, `override diff`

Each shape has a pinned golden-file test (see `tests/` in the repo). Between major versions, new
fields may be added to any shape; old fields stay present, named, and typed identically.

---

## Tier 4: Python import paths (explicitly NOT public)

The underscore-prefixed module convention (`squads._models`, `squads._service`, `squads._backends._claude_code`, …)
is the contract: **internal modules are not re-exported by package `__init__` files, and are not
part of the public API.** This is not a breaking change to state — squads has never shipped a
public library interface — but it is explicitly pinned to let integrators know where the boundaries
are.

The import graph is acyclic and strict typing (`pyright` strict mode, `ruff`) are the guards.
Forward references work without `from __future__ import annotations` because the floor is **Python ≥
3.14**, and PEP 649 lazy annotations are available.

### Shell completion

Verified install steps for bash and zsh completion are documented in the [top-level README](../README.md)
and are part of the supported-surface documentation. Completion may be added to other shells
additively post-1.0.

---

## Tier 5: Generated `.claude/` files (regenerable, never migrated)

Everything under `.claude/` is tool-owned and regenerable; deleting it loses nothing. Real definitions
live under the squad folder (`squads/agents/roles/`, `squads/agents/skills/`). `sq sync` regenerates
all tool-owned files to the current version.

### Backend ABC surface

Backends register behind the `AgentBackend` abstract base class. The frozen ABC methods:

- `generate_role_entry(slug: str, ctx: BackendContext) -> str` — return the role-entry body (renamed
  from `generate_role_pointer` to reflect that a backend may write a file or a section, not just a
  pointer).
- `generate_skill_entry(name: str, ctx: BackendContext) -> str` — skill-entry body (renamed from
  `generate_skill_pointer` for the same reason).

Implementations are registered via `_BUILTIN_BACKEND_MODULES` list or the `register()` hook. squads
ships two backends at 1.0 — `claude_code` and `agents_md` — and both pass a shared conformance
suite.

Backend selection: `sq init --backend <name>` or `active_backends` in `.squads.toml`.

---
---

## Glossary

**Durable**: stored on disk and considered source of truth; survives migrations and upgrades.  
**Regenerable**: tool-owned; can be deleted and rebuilt without losing data or state.  
**SemVer**: Semantic Versioning (MAJOR.MINOR.PATCH). Breaking changes allowed only in MAJOR releases.  
**Additive**: new fields may be added; removals, renames, or type changes are not.  
**Frozen**: locked at 1.0 and subject to the stability contract.
