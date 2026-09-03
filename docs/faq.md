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
truth, so just rebuild: `sq repair` — on a clean working tree, since it
[rewrites item files too](#does-sq-repair-change-my-files). If two branches reused an ID number,
use `sq repair --renumber` to fix it after the merge (see **Handling ID collisions** below).

### "a task's parent must be of type feature …"
The hierarchy is enforced: a **task**'s parent must be a **feature**, a **feature**'s parent an
**epic**. A bug or review is *not* a parent — attach it with a ref:
`sq task <n> ref add <bug> --kind fixes` (or `--kind addresses` for a review). Purely-technical tasks
have no parent.

### "<type> cannot move <X> → <Y>"
Each type has a status machine (see [workflow.md](workflow.md)). The transition you asked for isn't
allowed from the current state. Move through the valid path, or override with
`sq <type> <n> status <Y> --force` if you really mean it.

### "subtask STn → USn missing from FEAT-…"
A subtask references a user story that doesn't exist in the task's parent feature. Add the story
(`sq feature <n> add-story "…"`), remap the subtask (`--story`), or ensure the task's parent
is the right feature.

### "squads X detected (managed files at Y). Run `sq sync`."
You upgraded squads; the project's tool-owned files (the `squads`/`sq-<type>` skills, pointers,
`CLAUDE.md` section) are from an older version. `sq sync` regenerates them and stamps the config.
It never touches your authored content.

### Can I edit the markdown by hand?
No — the `.md` files are fully sq-managed. Set an item's body with `sq <type> <n> body` and a
sub-entity's with `sq <type> <n> <kind> <k> body` (both take `-m` paragraphs or `--file`, both
**replace** the body and so refuse once one has been written — `--append` to add, `--force` to
replace on purpose); comment
with `sq <type> <n> comment`; change metadata with `sq <type> <n> update`. Read anything back with
`sq show <n>` (any type) or `sq <type> <n> show` — and read it that way only: the command is the
read surface, not the file, because it resolves state the file does not carry.
Don't edit the markers or frontmatter by hand — use the commands so the
index stays in sync. `sq check` catches violations; `sq repair` rebuilds the index from frontmatter
and rewrites item files while it is there ([what it writes](#does-sq-repair-change-my-files)).

### What's the difference between `repair`, `check`, and `sync`?
- **`check`** — read-only lint: markers, dangling parents/refs, invalid status, frontmatter↔index drift.
  The only one of the three that writes nothing.
- **`repair`** — rebuild `.squads.json` from the `.md` frontmatter (`--renumber` fixes ID collisions),
  **and rewrite item files** on the same pass. See [Does `sq repair` change my
  files?](#does-sq-repair-change-my-files) below.
- **`sync`** — regenerate the *tool-owned* managed files (skills, pointers, CLAUDE.md section) to the
  current squads version.

### Does `sq repair` change my files?
Yes. Alongside the index rebuild, `sq repair` removes from your item files what squads now computes
on every read rather than stores: the sub-entity roll-up table and each block's badge line; a
**role's** stored body (emptied, not deleted — the marker pair stays); and the `extra` keys a role
item mirrored from its definition. It also canonicalises any legacy ref encoding. A role keeps its
`slug`, its default-role designation, and a developer role's `model`, `is_dev` and `tech`, and
`sq role <slug> show` renders its definition fresh from the catalog and your own role overrides.

**Run it on a clean working tree** — it cannot separate its changes from yours. Every command that
reaches the same rewrite — `sq repair`, `sq adopt`, `sq renumber`, and the index rebuild at the end
of `sq migrate up` — prints one line counting the item files it rewrote, and names those items in
the reflog. That is a count and a list of ids, not the change itself, so read `git diff` for what
actually moved. A squad carrying none of that content is left byte-for-byte alone, and a second run
is always a no-op.

**No skill body is touched** — not one you wrote, and not a template-owned one either. Neither is
any other item's body, any sub-entity's body or discussion, any operator item, or any frontmatter
field on anything that is not a role.

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
`sq repair` — resolve the conflict and commit first, because `sq repair` may also
[rewrite item files](#does-sq-repair-change-my-files) and cannot separate that diff from yours.

### Handling ID collisions
When two branches diverge and both create new items, they bump the same counter and mint the same ID
numbers. On merge, the tree holds duplicate files. Fix this in one of two ways:

**Preferred: pre-merge block-shift (on the yielding branch, before merge)**

If you control the branch that will yield to main (or the destination branch), run `sq renumber`
**before merging** — while both sets of IDs are still unambiguous:

```bash
# On the yielding branch, after your final commit:
# 1. Get the destination branch's current counter:
git show main:squads/.squads.json | jq .counter    # → let's say it's 287

# 2. Shift this branch's IDs into a reserved block above that counter:
sq renumber --from <N> --onto 287
#  N = your branch's counter at the merge-base (e.g., 280, or base_counter + 1)
```

This **preserves referential intent**: the rewrite happens before the second copy of each ID exists,
so every reference in the tree still means exactly what it says. IDs created on this branch move
into the reserved range; refs to them follow along atomically.

**Fallback: post-merge collision repair (after merge, on the merged tree)**

If collisions slip through to the merge, use `sq repair --renumber` on the merged result:

```bash
git merge <branch>
# Resolve the .squads.json conflict by taking either side, then commit the merge
sq repair --renumber     # detects duplicates, assigns fresh numbers, rewrites refs
```

Commit the merge before running it: `sq repair --renumber` performs the same item-file rewrite as
plain `sq repair` ([what it writes](#does-sq-repair-change-my-files)), and you want that diff on
its own rather than mixed into an unresolved merge.

This **guarantees uniqueness and no dangling refs**, but **cannot preserve intent** — when two
files claim the same ID, the tool rewrites **all** references to that ID to point to the winner,
even if some were meant for the loser. Use this only when duplicates already exist; the pre-merge
path is safer when you have the chance.

### What exit codes does `sq` use?

The documented, stable contract:

| Code | Meaning | When you see it |
|------|---------|-----------------|
| `0` | Success | Command completed normally (including `sq check` with no errors, or warnings only). |
| `1` | squads could not complete what you asked | A `SquadsError` (unknown ID, invalid transition, etc.), a schema-version mismatch (`sq migrate up` is needed), or a command that finished only partly and named what it could not read — `sq board list` and `sq repair` when they report a file that is not readable. |
| `2` | Usage error | Invalid `--at` timestamp format; Typer/Click usage errors (unknown option, missing required argument). |
| `3` | `sq check` found error-level issues | One or more `error`-level issues were reported. `warn`-level-only results still exit 0. |

Code `3` is the useful one for CI gates — scripts can use `sq check || exit 1` or test the code
directly. Codes `1` and `2` indicate a broken invocation or squad state, not a lint failure.

**A degraded read is a non-zero exit.** When `sq board list` or `sq repair` prints
`error: <path> …` for a file it could not read, it exits `1` even though it listed or rebuilt
everything else — a caller testing `$?` needs to see that the answer is short. In the same
situation `sq check` reports the file as an error-level issue, so it exits `3` like any other
error-level finding. `--json` output is unaffected in shape: `sq board list --json` still writes a
bare, valid array to stdout and names the unreadable files on stderr.

The formal stability contract (tiers, versioning, post-1.0 semantics) lives in
`docs/stability.md`.
