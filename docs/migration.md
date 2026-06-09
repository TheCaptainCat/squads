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
sq sync                                # regenerate tool-owned files (.claude/, CLAUDE.md, skills)
sq check                               # validate: markers intact, parents/refs/stories consistent
git add -A && git diff --cached        # review, then commit
```

You don't need to track when a migration is due: on an out-of-date squad **`sq` stops every command
and tells you to run `sq migrate up`**. If the squad is current, `sq migrate up` is a no-op.

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
| `schema_version` | The **durable-format contract** (currently **`"0.2"`**, `_models/_schema.py`). While alpha it tracks the release that introduced the schema. | Only when the on-disk frontmatter / markers / layout change incompatibly. |

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

## Authoring a migration (for contributors)

When a release changes the durable format:

1. **Add a runner** `src/squads/_migrations/_vA_to_vB.py` (dotted versions as underscores, e.g.
   `_v0_2_to_v0_3.py`) exposing `migrate(paths) -> int` — per-file,
   **idempotent**, **marker-safe** (edit only via `_sections`), **utf-8-pinned**, and it must **not**
   write the index (`repair` rebuilds it). If the step needs judgement, put an LLM runbook in a
   module-level `MANUAL` string instead of (or alongside) the deterministic logic.
2. **Register it** — append a `Migration(...)` to `_migrations/_registry.py::MIGRATIONS` (carrying the
   release `version`, `from_schema`/`to_schema` as dotted schema strings, one-line `summary`, `run=…`,
   and `manual=…`), and **bump** `_models/_schema.py::SCHEMA_VERSION`.
3. **Prefer non-breaking** — if the new data can live under `extra:` or be defaulted by
   `from_frontmatter`, you avoid a runner entirely.
4. **Keep `from_frontmatter` tolerant** of the previous shape for one cycle, so `repair` reconstructs
   the index correctly from a not-yet-rewritten file.
5. **Document & test** — a `### Migration` note in `CHANGELOG.md`; tests that build an old-format file
   in a `tmp_path` squad, run the runner (assert new shape + intact body + idempotent), and assert the
   schema gate blocks until `sq migrate up`.

The `manual` string is the source of truth for the runbook — `sq migrate chlog` renders it. Runner
modules are **private**; never expose them as `python -m …`. `sq migrate` is the only entry point.

```python
# src/squads/_migrations/_registry.py
MIGRATIONS = [
    Migration("0.2.0", "0.1", "0.2", "…summary…", _v0_1_to_v0_2.migrate, manual=_v0_1_to_v0_2.MANUAL)
]
# src/squads/_models/_schema.py
SCHEMA_VERSION = "0.3"  # dotted alpha string; compare with schema_tuple(), not < / >
```

---

## Status today

`schema_version` is **`"0.3"`**. `sq migrate up` runs every pending step in order and restamps the
config:

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
