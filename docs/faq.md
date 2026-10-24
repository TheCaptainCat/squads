# FAQ & troubleshooting

### `pip install squads` fails / wrong Python
squads requires **Python ≥ 3.14** (it uses PEP 649 deferred annotations and PEP 695 generics).
Install on 3.14, or run via uv which provisions it: `uvx --from squads sq …`.

### "no .squads.toml found … run `sq init`"
You're not inside a squad. Either `cd` into a project that has `.squads.toml` (sq walks up to find
it), pass `-C <path>` to run `sq` as if it were started in that folder (the project directory or any
folder inside it), or `sq init` / `sq adopt` to create one. With `-C`, the message names the folder
the search started from: `no .squads.toml found in <path> or any parent directory`.

### "-C … does not exist" / "is not a directory" / "cannot be entered: permission denied"
`-C` names the folder `sq` should run in, and `sq` enters it one component at a time, as `cd` does:
every component must exist, be a directory and be enterable, even one a later `..` would undo. The
path in the message is the first component that failed. `..` is resolved physically, like
`cd -P` or `git -C`: `-C link/..` is the parent of the link's target, not the folder holding the
link. `-C` never creates a folder, not even for `sq init`. Fix the path, create the folder, or fix
its permissions. The command does not run, and exits `2`.

### "--dir is no longer supported; use -C <path> …"
`sq` takes `-C`, and refuses `--dir` wherever it is written as an option. `-C` does
not name the squad folder; it names the folder `sq` starts in, and `sq` walks up from there to
`.squads.toml` as usual. For a squad inside its project, `-C path/to/squads` or `-C path/to/project` both work. For a
squad kept outside its project tree (`squad_dir = "../shared"` or an absolute path), use
`-C path/to/project`. See [migration.md](migration.md#upgrading-to-016--c-replaces---dir).

### "Missing option '--author'"
Every item is authored by a registered role, so `sq create <type>` requires `--author <slug>` and
exits 2 without it. `sq role list` shows the role slugs this squad has activated; a human authors
with `--author op-<slug>`.

### "unknown slug '…'; valid slugs: …"
`--author`, `--as` and `--assignee` take a registered slug: a role slug (`architect`, `qa`, …), a
developer's slug once you have added it with `sq dev add` (`python-dev` for `--tech python`), or `op-<slug>` for a
human registered with `sq operator add`. Anything else is refused (exit 1) and nothing is written;
the error lists the slugs that would have worked.

### "corrupt index … run `sq repair`"
`.squads.json` failed to parse or validate (often a bad git merge). The frontmatter is the source of
truth, so just rebuild: `sq repair` — on a clean working tree, since it
[rewrites item files too](#does-sq-repair-change-my-files). If two branches reused an ID number,
use `sq repair --renumber` to fix it after the merge (see **Handling ID collisions** below).

### "waiting for the index lock …" / "the index lock … is held by another sq process"
Every write takes a lock on `.squads.json.lock`, so two `sq` commands that write at once run one
after the other. A command that has waited about a second prints
`waiting for the index lock <path>…` on stderr and keeps waiting. If the lock is still held after
10 seconds, it exits `1` with `error: the index lock <path> is held by another sq process; nothing
was written, retry the command`. Nothing was written, so run the command again; if it keeps
failing, look for an `sq` process that is still running. The notice and the error go to stderr
only, so `--json` output on stdout stays clean.

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

### I upgraded squads: do I need to do anything?
Run `sq sync`. It regenerates the project's tool-owned files (the `squads`/`sq-<type>` skills,
pointers, the `CLAUDE.md` and `AGENTS.md` sections) from the installed version. Nothing warns you
that they are older than the installed `sq`, so make it part of every upgrade. `sq sync` never
touches your authored content or `.squads.toml`. If the release changed the on-disk format, `sq`
stops every command and asks for `sq migrate up` first; see [migration.md](migration.md).

### What is the `squads_version` line in my `.squads.toml`?
squads does not use that key: no command reads, writes or removes it, so you can delete the
line.

### "working_language … is not a language tag squads recognises; using English (en)"
The `working_language` value in `.squads.toml` is not a BCP 47 tag squads knows, so the squad
works in English. Use a hyphenated tag such as `fr`, `de` or `pt-BR` (not `fr_FR`), then run
`sq sync` to refresh the managed files. See
[adoption.md § "The working language"](adoption.md#the-working-language).

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
  current squads version. It also rebuilds the frontmatter of a managed skill file that lost it,
  from the file name and the skill catalog, and keeps the body; `check` and `repair` name `sync`
  as the fix for that file.

### Does `sq repair` change my files?
Yes. Alongside the index rebuild, `sq repair` removes from your item files what squads computes on
every read rather than stores: the sub-entity roll-up table and each block's badge line, and the
keys a role item mirrored from its definition (`full_name`, `mission`, `responsibilities`,
`agreements`, `color`, `can_spawn`, `skills`, `is_dev`). It also canonicalises any legacy ref
encoding. A role keeps its name, its `slug`, its default-role designation, a developer role's
`model` and `tech`, and any other key.

A **role** or **generated skill** whose body is empty gets its view tag written back — the one
line that makes `sq role <slug> show` / `sq skill <name> show` render the definition fresh from the
catalog and your own overrides. A role or skill body that holds prose is left alone: `show`
prints that prose in place of the definition. `sq check` accepts it on a role; on a generated
skill it reports a missing seeded view tag, with the steps that restore the rendered definition.

**Run it on a clean working tree** — it cannot separate its changes from yours. Every command that
reaches the same rewrite — `sq repair`, `sq adopt`, `sq renumber`, and the index rebuild at the end
of `sq migrate up` — prints one line counting the item files it rewrote, and names those items in
the reflog. That is a count and a list of ids, not the change itself, so read `git diff` for what
actually moved. A squad carrying none of that content and no empty role or skill body is left
byte-for-byte alone, and a second run is always a no-op.

**No body with content is touched** — not a role or skill body you wrote, not any other item's
body, and not any sub-entity's body or discussion. Neither is any operator item, or any frontmatter
field on anything that is not a role.

### Where are the timestamps? Can I keep history when migrating?
`created_at`/`updated_at` are in each item's frontmatter; comment entries carry their own dated line.
During a migration, the global **`--at <ISO>`** option forges the time for a command so the imported
history looks real — see [adoption.md](adoption.md).

### How do I work on several projects / move a squad?
The squad folder is self-contained (its `.squads.json` lives inside it). Move or copy it freely,
and point `squad_dir` in the project's `.squads.toml` at its new place. Item paths are stored
squad-folder-relative. To work on another project without changing directory, use
`sq -C <project> …`.

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
sq repair --renumber     # gives colliding files fresh numbers
```

Commit the merge before running it: `sq repair --renumber` performs the same item-file rewrite as
plain `sq repair` ([what it writes](#does-sq-repair-change-my-files)), and you want that diff on
its own rather than mixed into an unresolved merge.

What it does depends on the collision:

- **Distinct IDs that share a number** (say `TASK-<n>` and `BUG-<n>`, which carry the same number
  but are two different IDs): every file but one gets a fresh number, and every reference to it is
  rewritten. The IDs differ, so each reference is unambiguous.
- **The same ID in two files** (both branches created `TASK-<n>`, so one ID is carried by two
  files): when every file has a different slug, one keeps the ID and the others get fresh numbers.
  The kept file is the one the index already points at, otherwise the first by path. Only each
  renumbered file's own `id`, `sequence_id` and filename change. **References are not rewritten.**
  A reference to `TASK-<n>` could mean either copy, so the command lists every one it finds instead
  (file, frontmatter key or body/comment line, and the text) and exits `1` while any remain. Check
  each one by hand.
- **Refused:** two files with the same slug, byte-identical copies, or a file outside its type's
  folder. Those are copies, not a merge collision. Nothing is renamed, and the files are reported
  the way plain `sq repair` reports them (below).

Use this only when collisions already exist. The pre-merge path is safer when you have the chance,
because it keeps every reference meaning what it says.

**Two files with the same ID.** `sq check` reports each such ID as an error, naming every file
that carries it. Plain `sq repair` will not pick one: it keeps the previous index entry for that
ID, names the files and exits `1`. `show` renders the indexed file with a warning, and every write
to that ID is refused until it is resolved. Merge the content you want into one file, delete the
other, and run `sq repair`, or use `sq repair --renumber` as above.

### What exit codes does `sq` use?

The documented, stable contract:

| Code | Meaning | When you see it |
|------|---------|-----------------|
| `0` | Success | Command completed normally (including `sq check` with no errors, or warnings only). |
| `1` | squads could not complete what you asked | A `SquadsError` (unknown ID, invalid transition, etc.), a schema-version mismatch (`sq migrate up` is needed), `sq repair` (or the rebuild that ends `sq migrate up`) reporting a file it could not read while rebuilding, or `sq repair --renumber` leaving references to an ID that two files carry for you to check by hand. |
| `2` | Usage error | Invalid `--at` timestamp format; Typer/Click usage errors (unknown option, missing required argument). |
| `3` | Error-level issues were found | `sq check` reported one or more `error`-level issues, or `sq import` applied the file and the check of the items it touched found one. The import's events are on disk: do not retry it, read `applied` from its `--json` output. `warn`-level-only results still exit 0. |
| `4` | The answer is short | A listing finished and named what it could not read: `sq board list`, `sq inbox`, `sq search`, `sq memory <role> list`, `sq memory <role> search`. stdout still carries a valid payload in its usual shape. |

Code `3` is the useful one for CI gates — scripts can use `sq check || exit 1` or test the code
directly. Codes `1` and `2` indicate a broken invocation or squad state, not a lint failure.

**A degraded read is a non-zero exit, and it has a code of its own.** When one of the five listings
on code `4` cannot read part of the corpus, it prints everything it *could* read, names what it
skipped on stderr, and exits `4` — "the answer is short", which is a different sentence from `1`'s
"there is no answer". A caller testing `$?` still sees a failure; a caller that knows `4` also
learns that stdout is worth parsing. `sq repair` reports a mutation rather than a result and keeps
`1` when it carries an unreadable file, and `sq check` turns the same file into an error-level issue
and exits `3` like any other error-level finding. `--json` output is unaffected in shape:
`sq board list --json` still writes a bare, valid array to stdout, and names what it left out in one
JSON line on stderr.

The formal stability contract (tiers, versioning, post-1.0 semantics) lives in
`docs/stability.md`.
