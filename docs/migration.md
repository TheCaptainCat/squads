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
| `squads_version` | Package version that last wrote the managed files. Informational. | In `.squads.toml`, the copy the version notice reads: every `sq init` / `sq sync` (and `sq adopt` when it creates the file). In `.squads.json`: every index rebuild (`sq repair`, and the one ending `sq migrate up`). |
| `schema_version` | The **durable-format contract** (`sq migrate help` lists every schema with its changelog). While alpha it tracks the release that introduced the schema. | Only when the on-disk frontmatter / markers / layout change incompatibly; `sq migrate up` stamps it. |

`squads_version` drives a **non-fatal** notice: *"squads X detected … run `sq sync`"* — about
regenerating tool-owned files, not data. It is printed only while the schema matches, and `sq
sync` clears it: `sq repair` and `sq migrate up` leave `.squads.toml`'s copy as it was.
`schema_version` is the **hard gate**: if the squad's value differs from the one the installed
package reads, it stops the command — behind → *"run `sq migrate up`"*, ahead → *"upgrade the
squads package"*.

---

## The three tiers of on-disk state

Only the third tier can ever require a migration:

| Tier | Examples | How it updates | Migration? |
|------|----------|----------------|------------|
| **Tool-owned / managed** | `.claude/**`, the `CLAUDE.md` and `AGENTS.md` sections | `sq sync` regenerates from templates | **Never** — disposable, never hand-edited. |
| **The index** | `squads/.squads.json` | `sq repair` rebuilds it from frontmatter | **Never (for data)** — it's derived; an index-only change just needs a tolerant reader + `sq repair`. |
| **Durable item files** | `squads/<type>/PREFIX-NNNNNN-*.md` (frontmatter + sq markers + body) | hand/agent-authored = **source of truth** | **Only this tier** — and `sq migrate up` rewrites the `.md`; `repair` then rebuilds the JSON. |

A managed skill's own file, `squads/agents/skills/SKILL-NNNNNN-<slug>.md`, is a durable item like
any other: its frontmatter is in the third tier, and deleting the file loses the item. Its body
holds only a view tag; the definition `sq skill <slug> show` prints is rendered from the bundled
templates when read, so a release can change it with no migration.

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

## Upgrading to 0.16: the schema step

0.16 changes the durable format, so a squad written by an earlier release is stopped until
`sq migrate up` has run. The 0.16 step has several parts, and **it checks every part before it
writes any file.** If any part finds a problem, the step writes nothing, the schema stamp stays as
it is, the command exits `1`, and it lists every problem found, not only the first. Each part's
problems are described below with what to do about them. `sq migrate chlog v0.15.0..v0.16.0`
prints the same steps.

**Fix a refused run with an earlier release.** Until the migration completes, this release runs
nothing on the squad but `sq migrate up`, `sq migrate help` and `sq migrate chlog`, so a roster
change (adding a role or an operator back) is made with a release that reads the squad's current
schema, then `sq migrate up` is run again with this one. The refusal names such a release:

```
Change the roster with a squads release that reads schema v0.15 (v0.15.0 is one).
```

A squad stamped below 0.15 has its earlier steps applied in the same run, before the 0.16 step
looks at it. If the 0.16 step then refuses, those earlier steps stay applied but the stamp does
not move, and the message says so:

```
Earlier steps of this run have already been applied, so running again is safe, and the files are now in the shape of schema v0.15: change the roster with a squads release that reads schema v0.15 (v0.15.0 is one).
```

With 0.15.0, run `sq migrate up` first (it brings the squad to 0.15), make the change, then run
`sq migrate up` with 0.16.

### Comment headers name the author's slug

Each comment header gains its author's slug, between backticks, in front of the name:

```diff
-- [2026-10-16T08:08:22Z] Robert Architect:
+- [2026-10-16T08:08:22Z] `architect` Robert Architect:
```

The step rewrites the header line of every comment, in each item's discussion and in each story's,
subtask's and finding's. Nothing else changes: a comment's own lines stay byte for byte, no
frontmatter changes (so no item's `updated_at` moves), and a header-shaped line in an item's body,
outside any discussion, is left alone. The run reports what it did under the step:

```
  0.16.0 (schema v0.15→v0.16): Comment headers name the author's permanent slug. Every operator carries a stored slug and full name. — 1 changed
    4 comment header(s) rewritten in 1 file(s); 0 already carried a slug
    0 operator(s) given a stored slug or full name
```

A header that already carries a slug is left as it is, so the step can be run again safely.
Review the diff before you commit it. The new grammar is in
[stability.md](stability.md#comment-headers).

**How a slug is found.** An old header holds only a name, so the step looks each name up among the
squad's roles and operators, retired ones included, plus the two names sq writes itself: `Operator`
(a comment written with `--as operator`) and `squads` (an entry sq wrote, such as a retype). A
role is matched by its name (the `Name` column of `sq role list`). An operator is matched by its
full name, or by its slug when it has none, which is what the earlier release wrote in its
comments. Every name is resolved before any file is written. There is no option that maps a name
to a slug by hand.

**When it refuses**, the report gives one line per header (the file, relative to the squad
folder, and the line number), then the count, then one line per name that failed with the number
of headers and files that carry it:

```
error: tasks/TASK-NNNNNN-add-login.md:37: 'Mara Tester' matches no roster entry
1 problem(s) found.
  'Mara Tester': 1 header(s) in 1 file(s)
Correct the roster, or correct the line by hand, then run `sq migrate up` again; `sq migrate chlog v0.15.0..v0.16.0` has the steps.
This step wrote nothing and the schema stamp is unchanged.
Change the roster with a squads release that reads schema v0.15 (v0.15.0 is one).
The squad is still at schema v0.15: fix the cause, then re-run `sq migrate up`, which rebuilds the index from the files first.
```

What each line means, and what to do before running `sq migrate up` again:

- **`'<name>' matches no roster entry`.** The role or operator that wrote those comments is no
  longer in the squad, usually because it was removed with `rm --purge`. Add it back under that
  name with the earlier release: `sq role activate <slug> --name "<name>"` for a role (`sq role
  catalog` lists the slugs), `sq dev add --tech <tech> --name "<name>"` for a developer role, and
  `sq operator add "<name>" --slug <old-slug>` for an operator (`--slug` keeps the slug its items
  still name as author or assignee, and must follow the operator rule in
  [the next section](#a-role-or-operator-whose-slug-breaks-the-rules), or the run refuses it). A
  retired entry counts, so it can be retired again afterwards. If the entry is still there under a newer name, the old and the new name cannot both
  resolve to it: replace the old name in those header lines by hand.
- **`'<name>' matches 2 entries: <slug>, <slug>`.** Two entries share that name. Every header with
  the name then belongs to one of them only, so decide which, and give the other a distinct name
  for the run by editing its file: `title:` for a role, `full_name:` under `extra:` for an
  operator. The earlier release's `sq check` reports the edit as drift until `sq repair`, which
  `sq migrate up` makes unnecessary, since it rebuilds the index from the files first. After the
  migration, put the name back the same way and run `sq repair`.
- **`'<text>' is not a timestamp sq writes`.** A line at the left margin inside a discussion looks
  like a header, but its bracket does not hold a timestamp sq writes. If it is text pasted into a
  comment, indent it so it sits under that comment. If it is a header, correct its timestamp to
  the form `2026-06-07T10:00:00Z`.
- **A discussion region that "is not closed".** The region's closing marker line is missing.
  Restore it (from version control, for example).
- **A region marker that "shares its line with text" or "is not a well-formed sq marker".** Put
  each `sq:` marker on a line of its own, spelled as sq writes it (`<!-- sq:discussion -->`, one
  space on each side of the tag).

### A role or operator whose slug breaks the rules

Before it resolves any header, the step checks every role and operator, retired ones included,
against the slug rules (see [stability.md § "Comment headers"](stability.md#comment-headers)):

- an operator's slug is `op-` followed by lowercase letters, digits and hyphens;
- a role's slug is lowercase letters, digits and hyphens, and is neither `operator` nor `squads`
  nor anything that starts with `op-`;
- no slug is held by two entries.

An entry that breaks a rule refuses the run like an unresolvable header: nothing is written, the
schema stamp is unchanged and the command exits `1`. Each entry gets one line, naming its file, its
slug, the rule and the other holders, in the same report and count as the header failures; the
headers that name it are not listed again:

```
error: agents/roles/ROLE-000005-qa.md: role slug 'qa' is not unique; also held by OP-9
operators/OP-000009-qa.md: operator slug 'qa' does not start with 'op-'; also held by ROLE-5
2 problem(s) found.
```

The run refuses rather than only reporting because this is the last point where the slug can
change. Once the headers carry it, nothing rewrites them: a reserved slug would turn comments into
entries sq wrote itself, `operator` would make them anonymous, and a slug shared with a role would
make them editable by whoever holds it.

What to do for each, with the release the squad is stamped for, before running `sq migrate up`
again:

- **An operator.** Run `sq operator <id> rm --purge`, using the ID in the line, then
  `sq operator add "<the same full name>"`, which takes `op-` and the first name unless you pass a
  compliant `--slug`. The purge is required: with that release a plain `rm` drops the entry from
  the index but keeps its file, and the next run reads that file again. The comments that named the
  operator then resolve to the new slug. Reassign the open items assigned to the old slug with
  `sq <type> <n> update --assignee <new slug>`. An item's `author` keeps the old slug, and
  `sq check` reports it as not registered.
- **A role.** Give the role's project definition a compliant slug (the file under
  `<squad folder>/.overrides/roles/`, renamed, and its `slug` line with it), run
  `sq role activate <new slug>`, then `sq role <id> rm --purge` for the old entry.
- **A slug held by two entries.** Both entries are listed, each naming the other. Replace the one
  that breaks a rule above, or the one you can spare, the same way.

An operator that the earlier release's importer created took a slug derived from its whole name,
without `op-` (`Ann Lee` became `ann-lee`), so it is refused here unless it was given an `op-`
slug when imported.

### Every operator carries a stored slug and full name

An operator that an earlier release's importer created has neither a `slug` nor a `full_name`
under `extra:` in its file. `sq migrate up` writes both: the slug is the one the operator already
answers to, and the full name is its title. Only the frontmatter of those operators changes, and
an operator that already had both is not touched. The run reports how many it filled in:

```
    1 operator(s) given a stored slug or full name
```

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

## Upgrading to 0.15: view declarations

0.14 shipped derived views with a `fields`/`group_by`/`order_by` projection grammar, and a view
could be attached to a type with `items.<type>.views = […]`. 0.15 removes all four keys: a view
now declares only where its data comes from, and everything else — which columns, how they're
grouped, and where the view appears — moved elsewhere. If your own `.overrides/workflow.toml`
still carries the 0.14 grammar, upgrading breaks the load, on purpose, naming the retired key:

```
error: this squad's workflow override could not be loaded, so no command can answer with the vocabulary it declares.
  cause: …/.overrides/workflow.toml: views.milestone_rollup.group_by: 'group_by' was retired — grouping is the presentation template's own job now (Jinja `groupby`), not a declared key — remove it; a `[views.<name>]` table declares only `source` now.; …/.overrides/workflow.toml: views.milestone_rollup.order_by: 'order_by' was retired — ordering is the presentation template's own job now (Jinja `sort`), not a declared key — remove it; a `[views.<name>]` table declares only `source` now.; …/.overrides/workflow.toml: views.milestone_rollup.fields: 'fields' was retired — choosing and labelling which columns render is the presentation template's own job now — write the fields a resolved record actually has directly in Jinja, not a declared key — remove it; a `[views.<name>]` table declares only `source` now.
  Fix the file, then re-run. `sq workflow lint` reports every problem at once with a fix hint.
```

An `items.<type>.views` type attachment gets its own version of the same message:

```
error: this squad's workflow override could not be loaded, so no command can answer with the vocabulary it declares.
  cause: …/.overrides/workflow.toml: items.milestone.views: 'views' was retired — a view is placed with a `sq:view:<name>` tag in a document body now, not attached to a type — remove the key; place the view's tag with `sq <type> <n> view add <name>` instead.
  Fix the file, then re-run. `sq workflow lint` reports every problem at once with a fix hint.
```

Converting covers three moving pieces, worked below against a `milestone_rollup` override in the
shape a 0.14 squad might have carried.

### 1. Declaration: collapse to `source`

0.14:

```toml
[views.milestone_rollup]
source = { kind = "ref", name = "targets" }
group_by = "status_role"
order_by = ["type", "id"]

[[views.milestone_rollup.fields]]
code = "id"
label = "Id"

[[views.milestone_rollup.fields]]
code = "title"
label = "Title"

[[views.milestone_rollup.fields]]
code = "status"
label = "Status"
```

0.15 — delete every key but `source`:

```toml
[views.milestone_rollup]
source = { kind = "ref", name = "targets" }
```

If you never customised `fields`/`group_by`/`order_by` on the bundled `milestone_rollup`, there is
nothing to convert here: drop your whole `[views.milestone_rollup]` section and the bundled
one-line declaration takes over. If your override also attached a view to a type
(`items.<type>.views = […]`), delete that key too — see placement, below.

### 2. Template: move grouping and ordering into Jinja

The projection's `fields`/`group_by`/`order_by` become ordinary Jinja over `source` — the resolved
records themselves, unflattened — plus `item` (the host the view resolved against) and `spec` (the
active workflow spec). `sq override scaffold views/milestone_rollup.md.j2` starts you from the
bundled rendering; a minimal replacement for the projection above looks like:

```jinja
{% for kind, members in source | groupby('type') %}
### {{ kind }}
{% for r in members | sort(attribute='sequence_id') %}
- **{{ r.id }}** {{ r.status | badge(spec) }} — {{ r.title }}
{% endfor %}
{% endfor %}
Outstanding: {{ (source | selectattr('status', 'ne', 'Done') | list) | length }}
```

This is a deliberately small example. The bundled `milestone_rollup` template groups on
`spec.is_delivered(...)`/`spec.role_for(...).settled` rather than a literal status — read
["Derived views: field reference"](workflow.md#derived-views-field-reference) before converting
a real `group_by = "status_role"`, which needs that same distinction.

### 3. Placement: the dedicated verb, never the body

0.14 put `milestone_rollup` on every milestone automatically, through the type attachment. 0.15
places it with a verb instead:

```
sq milestone <n> view add milestone_rollup
```

which inserts the `sq:view:milestone_rollup` tag into the milestone's body at the view's declared
`position` — the end of the body unless you set one (see
["Derived views: field reference"](workflow.md#derived-views-field-reference)).
`templates/items/milestone.md.j2` already seeds this tag on every *new* milestone, and upgrading
(`sq migrate up`) places it on the milestones that predate the upgrade (the exceptions are in
[the next subsection](#after-sq-migrate-up-seeded-views)), so `view add` is mainly needed for a
view you declared yourself, on a type whose creation template doesn't seed its tag. Typing the tag
into a body by hand is refused, deliberately:

```
error: body must not contain sq marker comments (<!-- sq:… -->). Write the tag without its HTML-comment wrapper (e.g. sq:body rather than the comment form) — backtick-wrapping does not neutralize a well-formed tag.
```

A tag is never taken back out. `sq <type> <n> view disable <name>` turns it off instead: the tag
stays in the body as `sq:view:<name>:disabled` and renders nothing, and `view add` turns it back
on.

### The result

With the minimal template from step 2 in place, `sq milestone <n> show` renders the roll-up in
place, computed fresh on every read — for a milestone with one linked feature:

```
### feature
- **FEAT-<n>** ⚪ Draft — Ship the widget
Outstanding: 1
```

The bundled template renders the same milestone in three buckets instead — see
[§ "Milestones"](workflow.md#milestones).

### After `sq migrate up`: seeded views

Every document is **seeded** with the views its type calls for: a milestone with
`milestone_rollup`, a role with `role_definition`, the three permanently-system skills
(`squads`, `greeting`, `sq-memory`) each with its own view, and each per-item-type `sq-<type>`
skill with `item_skill`. A seeded view's tag stays in the document for good — enabled or
disabled — and `sq check` reports a document that is missing one (see
["Derived views: field reference"](workflow.md#derived-views-field-reference)).

`sq migrate up` places those tags for you. It adds the roll-up tag to each existing milestone,
and it replaces the text in every role, permanently-system skill and `sq-<type>` skill body with
that document's tag. That includes an `sq-<type>` skill whose text you wrote yourself: copy such
a runbook into a skill of its own before upgrading. The run reports how many files it changed. An
empty body, a body that already carries its tag, and a custom skill are left as they are.

Before it rewrites anything, `sq migrate up` rebuilds the index from the item files. An indexed
milestone whose file is gone is dropped from the index there, and named on the run's
`index reconciled with the files` line. An item file the run cannot read or parse stops it before
any document is rewritten, with the schema unchanged (see
[migration.md § "Before the first runner"](#before-the-first-runner)).

A document the migration reads but cannot safely rewrite is skipped rather than aborting the
run, and named by id in its output:

- a milestone whose body has no `sq:body` region;
- a milestone whose tag you had already moved outside `sq:body` by hand. `sq check` warns that
  the tag never renders there, and `view add` refuses while it is out of region, but the next
  body write places a second copy inside the body and `sq check` then reports a duplicate. Move
  the out-of-region line inside `sq:body` by hand, or delete it and run
  `sq milestone <n> view add milestone_rollup`;
- a role or skill body holding marker-shaped content the migration does not recognise.

`sq check` then reports each skipped document that still lacks its tag, at error level. For a
milestone, the error names two single-command remedies — restore its `sq:body` region first if
that is what is missing:

```
error MILE-000021-ship-1-0.md: missing seeded view tag <!-- sq:view:milestone_rollup --> — restore it with `sq milestone 21 view add milestone_rollup`, or disable it with `sq milestone 21 view disable milestone_rollup`
```

**A role or skill that still holds old generated text.** A role or skill body refuses prose, so
its old text cannot be edited away in place, and `view add` alone would render the old text and the live
definition together. `sq check` names the remedy in full, filled in for the document:

```
error ROLE-000001-dev-agent.md: missing seeded view tag <!-- sq:view:role_definition --> — the body already carries prose; the remedy that converges to a single live rendering: (1) drop 'role_definition' from [selected] in .overrides/workflow.toml; (2) clear the text with `echo '{"op": "body", "target": "ROLE-1", "body": "", "force": true, "as": "dev-agent"}' | sq import -`; (3) restore 'role_definition' to [selected]; (4) `sq role dev-agent view add role_definition`
```

1. Drop the view from `[selected]` in `.overrides/workflow.toml`, listing every view you keep:

   ```toml
   [selected]
   views = ["milestone_rollup", "squads_skill", "greeting_skill", "memory_skill", "item_skill"]
   ```

2. Clear the body. A skill takes `sq skill greeting body -m "" --force`. A role has no `body`
   verb, so pipe a one-event import to `sq import -`, as the error shows. Marker-shaped content
   is cleared along with the rest.
3. Put the view back in `[selected]` (or delete the `[selected]` table if it lists every view).
4. Run `sq role dev-agent view add role_definition`, or `sq skill <slug> view add <name>` for a
   skill.

The document then renders only its live definition, and `sq check` is clean for it.
`view disable` is not a substitute: the document would then render the old text alone, and
only these four steps remove it.

**An `sq-<type>` skill you wrote yourself.** A custom skill whose slug a type declared later
now names, such as `sq-widget` once you declare `widget`, keeps its text, and `sq check` names
five steps:

```
error SKILL-000021-sq-widget.md: missing seeded view tag <!-- sq:view:item_skill --> — the body already carries prose, and 'sq-widget' still documents the declared type 'widget', so this may be an author's own runbook rather than stale legacy text; the remedy that preserves it: (1) `sq skill add <new-slug>` and move the prose there; (2) drop 'item_skill' from [selected] in .overrides/workflow.toml; (3) clear sq-widget's own text with `sq skill sq-widget body -m "" --force`; (4) restore 'item_skill' to [selected]; (5) `sq skill sq-widget view add item_skill`
```

For example, `sq skill add widget-runbook --desc "…"` and `sq skill widget-runbook body -m "…"`
with the runbook's text, then steps 2–5. `sq check` is then clean for both skills. A squad
brought in with `sq adopt` from a folder older than 0.14 skips the migration, so `sq check`
reports the same states on its roles and skills, with the same remedies.

`sq migrate chlog v0.14.0..v0.15.0` prints the migration's own manual steps.

---

## Migration history (early schema evolution)

`sq migrate up` runs every pending step in order and restamps the config. The two earliest
migrations, in detail:

- **0.1 → 0.2**: folds `extra.ref_kinds` into inline `ID:kind` refs;
  upgrades subtask/story headings (`[ ]`/`[x]` checkboxes, `(→ USn)` suffixes) into the sq-owned
  `:meta` regions and builds the summary tables; gives legacy reviews an empty findings container.
  *Tolerant* (`from_frontmatter` folds the old `ref_kinds`), so rewrite-then-`repair` reconstructs the
  index even from a pre-0.2 squad. **One manual step** (`sq migrate chlog v0.1.1..v0.2.0`): a pre-0.2
  review's free-form prose findings can't be parsed automatically — an agent recreates each as
  `sq review <n> add-finding … --severity …`, then deletes the stale prose.
- **0.2 → 0.3**: backfills `sequence_id` into every item's
  frontmatter (derived once from its id); **lifts each sub-entity's body `:meta` state into the new
  `subentities:` frontmatter list and deletes the `:meta` markers** (sub-entity state is now
  single-sourced in frontmatter); and renders the human-readable `:head` region under every
  sub-entity (status / assignee-name / severity / story badges, resolving names from the role files
  and a subtask's story title from its parent feature). The prose (`:body` / `:discussion`) and the
  `:summary` table are untouched. Fully automatic; idempotent.

Every migration since, release by release, is in the live changelog — run `sq migrate help` for
the index and `sq migrate chlog vFROM..vTO` for any given range's manual steps.
