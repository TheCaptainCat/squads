# FAQ & troubleshooting

### `pip install squads` fails / wrong Python
squads requires **Python ≥ 3.14** (it uses PEP 649 deferred annotations and PEP 695 generics).
Install on 3.14, or run via uv which provisions it: `uvx --from squads sq …`.

### "no .squads.toml found … run `sq init`"
You're not inside a squad. Either `cd` into a project that has `.squads.toml` (sq walks up to find
it), pass `--dir <path>` to point at a squad folder explicitly, or `sq init` / `sq adopt` to create
one.

### "corrupt index … run `sq repair`"
`.squads.json` failed to parse or validate (often a bad git merge). The frontmatter is the source of
truth, so just rebuild: `sq repair`. If two branches reused an ID number, `sq repair --renumber`.

### "a task's parent must be of type feature …"
The hierarchy is enforced: a **task**'s parent must be a **feature**, a **feature**'s parent an
**epic**. A bug or review is *not* a parent — attach it with a ref:
`sq task <n> ref add <bug> --kind fixes` (or `--kind addresses` for a review). Purely-technical tasks
have no parent.

### "<type> cannot move <X> → <Y>"
Each type has a status machine (see [workflow.md](workflow.md)). The transition you asked for isn't
allowed from the current state. Move through the valid path, or override with
`sq status <ID> <Y> --force` if you really mean it.

### "subtask STn → USn missing from FEAT-…"
A subtask references a user story that doesn't exist in the task's parent feature. Add the story
(`sq feature <n> add-story "…"`), remap the subtask (`--story`), or ensure the task's parent
is the right feature.

### "squads X detected (managed files at Y). Run `sq sync`."
You upgraded squads; the project's tool-owned files (the `squads`/`sq-<type>` skills, pointers,
`CLAUDE.md` section) are from an older version. `sq sync` regenerates them and stamps the config.
It never touches your authored content.

### Can I edit the markdown by hand?
No — the `.md` files are fully sq-managed. Set an item's body with `sq body <ID>` and a sub-entity's
with `sq story|subtask|finding body <ID> <LID>` (both take `-m` paragraphs or `--file`); comment with
`sq comment`; change metadata with `sq update`. Read anything back with `sq show` / `sq <kind> show`.
Don't edit the markers or frontmatter by hand — use the commands so the
index stays in sync. `sq check` catches violations; `sq repair` rebuilds the index from frontmatter.

### What's the difference between `repair`, `check`, and `sync`?
- **`check`** — read-only lint: markers, dangling parents/refs, invalid status, frontmatter↔index drift.
- **`repair`** — rebuild `.squads.json` from the `.md` frontmatter (`--renumber` fixes ID collisions).
- **`sync`** — regenerate the *tool-owned* managed files (skills, pointers, CLAUDE.md section) to the
  current squads version.

### Where are the timestamps? Can I keep history when migrating?
`created_at`/`updated_at` are in each item's frontmatter; comment entries carry their own dated line.
During a migration, the global **`--at <ISO>`** option forges the time for a command so the imported
history looks real — see [adoption.md](adoption.md).

### How do I work on several projects / move a squad?
The squad folder is self-contained (its `.squads.json` lives inside it). Move or copy it freely;
target any squad with `sq --dir <path> …`. Item paths are stored squad-folder-relative.

### How do I add another agent tool (not Claude Code)?
Implement a backend — see [backends.md](backends.md) — then `sq init --backend <name>`.

### Git: what do I commit, and what about conflicts?
Commit `.squads.toml`, the `squads/` folder, `CLAUDE.md`, and `.claude/`. `squads/.gitignore`
already excludes the lock/temp files. On a `.squads.json` conflict, take either side and
`sq repair`; for duplicate ID numbers, `sq repair --renumber`.
