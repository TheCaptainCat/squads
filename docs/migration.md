# Upgrading a squad to a new squads version

Upgrading the `squads` package is usually free: install the new version and run `sq sync`. A
*migration* — rewriting on-disk content — is only needed when a release changes the **durable
on-disk format** (item frontmatter, sq markers, or the folder layout). When that happens, `sq` tells
you and `sq migrate` handles it.

Companion to [adoption.md](adoption.md) (importing a *foreign* project into squads). This doc is
about moving an *existing squad* from one squads version to the next.

---

## TL;DR

```bash
pip install -U squads                  # or: uvx squads@<new> …
git switch -c chore/upgrade-squads     # clean rollback point

sq migrate up                          # if the squad is behind: reindex, check, run the schema runners, repair, restamp
sq migrate chlog v<old>..v<new>        # any manual (LLM-assisted) steps for that release range
sq check                               # validate FIRST — see below; fix anything it reports
sq sync                                # then regenerate tool-owned files (.claude/, CLAUDE.md, skills)
sq check                               # confirm the regenerated files are clean
git add -A && git diff --cached        # review, then commit
```

**Run `sq check` before `sq sync`, not after.** `sq sync` regenerates your tool-owned files from
the roster as it currently stands, and a roster entry the new version considers invalid — a status
its lifecycle no longer declares, say — is simply not written out. That is `sync` doing its job, but
it is silent: it exits `0`, and the entry's `.claude/` pointer and its line in `CLAUDE.md` are
gone with no message. `sq check` is the command that names the problem, so running it first turns a
silent strip into a list of entries to fix. Running it again after `sync` is the cheap confirmation
that what got written is what you wanted.

Nothing is lost either way — the durable definitions under `squads/agents/roles/` are never touched
by `sync`, and putting an entry back at a live status restores its pointer and its `CLAUDE.md` line
inside that same command, with no second `sq sync` needed. Checking first just saves you finding
out from an agent that has stopped being spawnable.

You don't need to track when a migration is due: on an out-of-date squad **`sq` stops every command
and tells you to run `sq migrate up`**. If the squad is current, `sq migrate up` is a no-op. The
version notice you see on an ordinary command points at `sq sync`, since refreshing the managed
files is the usual case; it is not shown while the squad's schema differs from the package's,
because `sq sync` is refused until it matches. When you are moving between versions, use the order
above.

---

## The `sq migrate` command

| Command | Does |
|---------|------|
| `sq migrate up` | Rebuilds the index from the item files and checks the squad can be migrated (see [below](#before-the-first-runner)); runs every **automatic** migration whose target schema is newer than the squad's, in order; rebuilds the index; stamps the new `schema_version`. Then prints which (if any) leave **manual** steps. On a squad already at the current schema it changes nothing. |
| `sq migrate help` | The **changelog index** — every shipped migration: release, schema bump, one-line summary, and whether it has manual steps. |
| `sq migrate chlog vFROM..vTO` | The **complete manual steps** for migrations shipped in `(vFROM, vTO]` (release versions, exclusive-low; a prerelease bound such as `v0.14.0rc1` sorts below its release). This is the canonical place those runbooks live — not buried in prose. |

### What runs on an out-of-date squad

On a squad whose `schema_version` differs from the package's, `sq` refuses every command except
these three, and `--help` on any command. `--help` counts only as an option of its own: not after
`--`, and not as the value of another option (`-m --help` is a message, and is gated like the rest
of the command; in `-m -m --help` the message is `-m` and `--help` is help). `-h` is not a help
option of `sq`. The gate applies however the squad is reached, from a folder inside the project or
through `-C`, wherever its folder sits: at the project root (`squad_dir = "."`), several levels
down, or behind a symlink.

| Command | Squad behind the package | Squad ahead of the package |
|---------|--------------------------|----------------------------|
| `sq migrate up` | runs | refused: upgrade the squads package |
| `sq migrate help`, `sq migrate chlog` | run | run |

`help` and `chlog` let you read the steps *before* applying them. `sq migrate repad`, `sq migrate rename-type` and
`sq migrate rename-status` are maintenance commands for a squad at the current schema, and are
refused like any other command until `sq migrate up` has run. If `sq migrate up` refuses because
your workflow override no longer declares a type or status your items still use, restore the
declaration, migrate, rename at the current schema, then drop it.

### Before the first runner

`sq migrate up` first rebuilds the index (`.squads.json`) from the item files, so the runners see
the squad as its files describe it. An item file the index did not hold gains an entry, and an
entry whose file is gone is dropped. When either happens, the output says so on one line:

```
  index reconciled with the files: dropped MILE-<n> (no file backs it)
```

With a readable index, the rebuild looks only where the index already keeps items. With no index,
or one that does not parse, it takes every item-shaped file under the squad directory for an item.

The run then stops with exit `1` when it cannot migrate the whole squad. Nothing is migrated and
the schema is unchanged. The message names each file or item and says what to do:

- **An item file cannot be indexed.** Its bytes are not valid UTF-8, its frontmatter does not
  parse, it has no usable `id`, two files carry the same id, or two different ids share one
  number. Correct each file, or, when it is not one of the squad's items, move it out of the
  folder it sits in. For a shared number the message gives the steps of a renumber by hand.
- **The squad does not fit its own vocabulary.** An item has a type or status your workflow
  spec (bundled plus override) does not declare, an indexed file sits where no type of the squad
  lives, or a file named for an item, where the squad keeps items of its type, has no index
  entry. Restore the declaration in the override, correct the frontmatter, or move the file, as
  the message says.
- **A stored badge code is not declared by its collection.** An item's or sub-entity's badge
  field (a `priority` or `severity`, say) holds a code its collection does not list. The message
  names each item, field, code and file; correct the frontmatter value by hand. A value that is
  not a single code, such as a list, is refused before any runner too.
- **The workflow override or playbook override does not load.** `sq migrate up` never falls
  back to the bundled vocabulary. Correct the file.

```
error: no migration has run: the corpus does not fit the vocabulary this squad declares:
  - item TASK-<n> has status 'Bogus' which is not declared in the workflow spec
correct the named frontmatter by hand, then re-run `sq migrate up`. The schema is unchanged.
```

Fix the cause and run `sq migrate up` again. When there was a readable index, the rebuilt index
is kept even when the run stops, so `.squads.json` may show a change; no item file has been
touched. When there was none, a refused run writes no index. If the refusal is about files the
rebuild took for items, the message offers to restore the index first: from version control, or
with the index rebuild of a squads release that reads the squad's schema (the message names
one).

Two refusals can come later, once runners have started, and both leave the schema unchanged. A
runner that needs a new id when every id at the current padding is used stops the run: widen the
padding with a release that reads the squad's schema, then upgrade and re-run. Any other error
from a runner or from the closing index rebuild ends with *"The squad is still at schema vX: fix
the cause, then re-run `sq migrate up`, which rebuilds the index from the files first."*

---

## How versions are stamped

squads records **two** independent version numbers (in `.squads.toml` and `.squads.json`):

| Field | Meaning | Bumped when |
|-------|---------|-------------|
| `squads_version` | Package version that last wrote the managed files. Informational. | Every `sq init` / `sq sync` / `sq repair` / `sq migrate up`. |
| `schema_version` | The **durable-format contract** (see `_models/_schema.py` for the current value, or `sq migrate help` for the full changelog). While alpha it tracks the release that introduced the schema. | Only when the on-disk frontmatter / markers / layout change incompatibly. |

`squads_version` drives a **non-fatal** notice (`version_notice`): *"squads X detected … run `sq
sync`"* — about regenerating tool-owned files, not data. It is printed only while the schema
matches. `schema_version` is the **hard gate**
(`require_current_schema`): if the squad's value differs from the build's `SCHEMA_VERSION` it stops
the command — behind → *"run `sq migrate up`"*, ahead → *"upgrade the squads package"*.

---

## The three tiers of on-disk state

Only the third tier can ever require a migration:

| Tier | Examples | How it updates | Migration? |
|------|----------|----------------|------------|
| **Tool-owned / managed** | `.claude/**`, `CLAUDE.md` section, `squads/agents/skills/sq-*.md` | `sq sync` regenerates from templates | **Never** — disposable, never hand-edited. |
| **The index** | `squads/.squads.json` | `sq repair` rebuilds it from frontmatter | **Never (for data)** — it's derived; an index-only change just needs a tolerant reader + `sq repair`. |
| **Durable item files** | `squads/<type>/PREFIX-NNNNNN-*.md` (frontmatter + sq markers + body) | hand/agent-authored = **source of truth** | **Only this tier** — and `sq migrate up` rewrites the `.md`; `repair` then rebuilds the JSON. |

### What counts as a breaking change

`Item.from_frontmatter` reads a **fixed set of known keys** plus the nested `extra:` map, which
defines compatibility:

- **Non-breaking (no migration):** adding metadata under `extra:` (round-trips through `repair`);
  dropping a key (falls back to a default); adding a key to `.squads.toml` (`extra="ignore"`).
- **Breaking (needs a runner + `schema_version` bump):** a new top-level required key (one
  `from_frontmatter` doesn't read is **silently dropped on `sq repair`**); renaming/retyping a known
  key; renaming a marker tag; changing a sub-entity block shape; changing the folder layout / ID format.


---

## When a release adds an item type

A new bundled item type is a vocabulary change, not a data change: the declaration ships in the
package, and what an existing squad is missing is only the two things a declaration never produces
on disk — the type's own folder, and the generated agent-facing surface a squad created *after* the
declaration would already have (the type's managed `sq-<type>` skill, its pointer, and the compiled
`CLAUDE.md` / `AGENTS.md` regions that name it).

`sq migrate up` creates both. **No existing item is rewritten** — every write is either a path that
did not exist or a generated region the migration is the first author of, so it is safe to re-run
and a second pass changes nothing. A type your own workflow override has dropped is skipped: the
migration scaffolds against your active spec, not the bundled one, so it never creates a folder for
a type your squad does not declare.

Run `sq sync` afterwards if your squad customises which skills a role loads — the migration
deliberately regenerates only the new type's surface, and leaves each role's own resolved
preload list to `sync`, which is where it belongs. On a squad that hasn't customised it, `sync`
converges to the same result and changes nothing.

Read the release's own entry with `sq migrate chlog vFROM..vTO` before running it; a type-adding
migration needs no manual step, and its entry says so rather than leaving you to guess.

---

## Upgrading to 0.16: `-C` replaces `--dir`

This change touches no file in the squad, so it needs no migration. It changes how scripts and
agent prompts point `sq` at a squad.

`--dir` is refused wherever it is written as an option, with exit `2` and nothing written (as the
value of another option, such as `-m --dir`, it is plain text):

```text
error: --dir is no longer supported; use -C <path> to run sq as if started in <path> (the project directory, or any folder inside it)
```

`sq -C <path> <command>` behaves as `cd <path> && sq <command>` would: `sq` walks up from `<path>`
to the first `.squads.toml`, exactly as it does from the folder you run it in. `-C` goes before the
command and before `--help` or `--version`: after a command it is refused as an unknown option, and
after `--help` or `--version` it is ignored. It can be repeated, as in git: a relative path is
taken against the previous `-C`, an absolute one replaces what came before. Relative `--file`
paths and the `sq import` event file are read from `<path>` too. `-C` never creates a folder: a path with a component that does not exist, is not a directory
or cannot be entered is refused with exit `2`.

Replacing `--dir` in a script:

| Where the squad folder sits | Before | After |
|-----------------------------|--------|-------|
| Inside its project (`squad_dir = "squads"`, `"."`, `"work/squad"`) | `--dir path/to/squads` | `-C path/to/squads` or `-C path/to/project` |
| Outside its project (`squad_dir = "../shared"` or an absolute path) | `--dir path/to/shared` | `-C path/to/project` |

For a squad outside its project tree, `-C` must name the project: the squad folder itself has no
`.squads.toml` above it, so `-C path/to/shared` is reported as not initialised. The same holds for
any folder with no `.squads.toml` above it. Where `--dir` used to run on defaults for such a
folder, `-C` reports `no .squads.toml found in <path> or any parent directory` and exits `1`.

`sq -C <path> init` and `sq -C <path> adopt` create the project at `<path>` (its `.squads.toml`,
and the squad folder `--squad-dir` names inside it).

---

## Migration history (early schema evolution)

`sq migrate up` runs every pending step in order and restamps the config. The two earliest
migrations, in detail:

- **0.1 → 0.2** (`_migrations/_v0_1_to_v0_2.py`): folds `extra.ref_kinds` into inline `ID:kind` refs;
  upgrades subtask/story headings (`[ ]`/`[x]` checkboxes, `(→ USn)` suffixes) into the sq-owned
  `:meta` regions and builds the summary tables; gives legacy reviews an empty findings container.
  *Tolerant* (`from_frontmatter` folds the old `ref_kinds`), so rewrite-then-`repair` reconstructs the
  index even from a pre-0.2 squad. **One manual step** (`sq migrate chlog v0.1.1..v0.2.0`): a pre-0.2
  review's free-form prose findings can't be parsed automatically — an agent recreates each as
  `sq review <n> add-finding … --severity …`, then deletes the stale prose.
- **0.2 → 0.3** (`_migrations/_v0_2_to_v0_3.py`): backfills `sequence_id` into every item's
  frontmatter (derived once from its id); **lifts each sub-entity's body `:meta` state into the new
  `subentities:` frontmatter list and deletes the `:meta` markers** (sub-entity state is now
  single-sourced in frontmatter); and renders the human-readable `:head` region under every
  sub-entity (status / assignee-name / severity / story badges, resolving names from the role files
  and a subtask's story title from its parent feature). The prose (`:body` / `:discussion`) and the
  `:summary` table are untouched. Fully automatic; idempotent.

(`store.load()` reads `.squads.json` as-is and does **not** fold the item shape — which is why the
gate routes you through `sq migrate up` instead of letting a half-read index drift.)

Every migration since, release by release, is in the live changelog — run `sq migrate help` for
the index and `sq migrate chlog vFROM..vTO` for any given range's manual steps.
