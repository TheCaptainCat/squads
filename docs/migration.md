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

sq migrate up                          # if the squad is behind: runs the schema runners, repair, restamp
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
files is the usual case; when you are moving between versions, use the order above.

---

## The `sq migrate` command

| Command | Does |
|---------|------|
| `sq migrate up` | Runs every **automatic** migration whose target schema is newer than the squad's, in order; rebuilds the index; stamps the new `schema_version`. Then prints which (if any) leave **manual** steps. |
| `sq migrate help` | The **changelog index** — every shipped migration: release, schema bump, one-line summary, and whether it has manual steps. |
| `sq migrate chlog vFROM..vTO` | The **complete manual steps** for migrations shipped in `(vFROM, vTO]` (release versions, exclusive-low). This is the canonical place those runbooks live — not buried in prose. |

`sq migrate *` are the only commands exempt from the schema gate, so they always run even on an
out-of-date squad — read the steps *before* applying them.

---

## How versions are stamped

squads records **two** independent version numbers (in `.squads.toml` and `.squads.json`):

| Field | Meaning | Bumped when |
|-------|---------|-------------|
| `squads_version` | Package version that last wrote the managed files. Informational. | Every `sq init` / `sq sync` / `sq repair` / `sq migrate up`. |
| `schema_version` | The **durable-format contract** (see `_models/_schema.py` for the current value, or `sq migrate help` for the full changelog). While alpha it tracks the release that introduced the schema. | Only when the on-disk frontmatter / markers / layout change incompatibly. |

`squads_version` drives a **non-fatal** notice (`version_notice`): *"squads X detected … run `sq
sync`"* — about regenerating tool-owned files, not data. `schema_version` is the **hard gate**
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
