---
id: ADR-1312
sequence_id: 1312
type: decision
title: 'Board notices and memories: a one-line summary over a body'
status: Accepted
author: architect
refs:
- FEAT-1311:implements
- ADR-314
- ADR-1294
description: A notice stores a summary in its frontmatter over an optional body; list
  shows summaries, show the body; a multi-line summary warns
created_at: '2026-11-05T07:09:57Z'
updated_at: '2026-11-05T07:14:48Z'
---
<!-- sq:body -->
## Context

ADR-314 stores a board notice as light frontmatter (`author`, `posted_at`, optional `until`) over the
notice text, and a memory as a one-line `summary`, `created_at` and optional `tags` over a body.
ADR-1294 §1 and §2 render `sq board list --raw` into every `sq-role-<slug>` skill with each notice's
full text. On this repository that is 24 notice files and 14,673 characters of body (read), paid by
every spawn.

op-pierre's ruling on FEAT-1290 (2026-11-05): a memory and a board notice both have a one-line
summary and a full body; `list` shows summaries only and `show` the body; a summary that spans
several lines raises an `sq check` warning and is never refused; the 0.19 to 0.20 migration takes
each notice's whole body as its summary.

Board notice 22 holds throughout: every mechanism below is an operation the daemon serves, reading
the squad's own files, so it works the same against a hosted squad.

## Decision

### 1. The stored form of a notice

A notice keeps its file, `squads/board/<id>.md`, and gains a `summary` frontmatter key, as a memory
has:

```markdown
---
summary: Run board operations through the released tool
author: manager
posted_at: '2026-10-15T21:36:05Z'
until: '2026-11-07T00:00:00Z'
---
Optional freeform body.
```

- Keys in this order: `summary`, `author`, `posted_at`, optional `until`. No id key: the id stays the
  filename stem (ADR-314).
- The body is optional and stored as written. A notice posted without a body stores an empty body;
  the summary is not copied into it, since `show` prints the summary already.
- A new notice's id is the short hash of its author, `posted_at`, summary and body. An existing id is
  never recomputed: the migration renames nothing.
- A summary is one line: a line break is any separator `str.splitlines` splits on, as
  `title_single_line` reads a title. A multi-line summary is stored as given and warned on (§5).
- The memory format does not change. It already matches, except that `memory add` copies the summary
  into the body when none is given; that default stays.

### 2. Commands

- `sq board post "<summary>" [-m … | --file …] [--until <date>] --as <slug>`. The positional
  argument is the summary, required and non-empty after stripping. `-m` (repeatable) or `--file`
  gives the body; a post with neither is valid. `post -m "<text>"` without a summary is refused by
  the argument parser.
- `sq board list [--raw] [--json]`: one line per live notice, numbered, with its summary, author and
  expiry. No body.
- `sq board show <n> [--json]`: notice n in full, a header (summary, author, posted, until) and the
  body. It takes `--json` as `sq memory <role> show` does; it has no `--raw` or `--no-header`, since
  no skill renders a notice through a `!` line.
- Numbering is unchanged from ADR-314: `<n>` is the position in the live listing (unexpired, read
  from the files, sorted by `posted_at` then id), resolved fresh by each command. `list`, `show <n>`
  and `clear <n>` resolve against the same listing. An unreadable notice holds no number.
- `show` or `clear` with a number outside the listing exits 1 with nothing on stdout and sq's
  one-line error on stderr.
- `sq memory <role> add` and `sq board post` with a multi-line summary write the entry and answer
  with one warning in the response's `warnings`, the text of the §5 rule. Neither refuses.

### 3. The `--json` shapes

- `board list`: an array of `{n, id, summary, author, posted_at, until}`. `body` leaves the row.
- `board show <n>`: one object `{n, id, summary, author, posted_at, until, body}`; `body` is `""` when
  the notice has none.
- `board post` and `board clear`: unchanged envelope; the `entry` object gains `summary` beside
  `body`.
- Operations: `BOARD_SHOW` is new (a read, `GET`), with a `BoardShowRequest {n}`. `BoardPostRequest`
  becomes `{summary, body: str | None, until}`. `NoticeRow` drops `body` and gains `summary`;
  `Notice` gains `summary`.
- `sq memory` JSON is unchanged; its list rows keep the key `description` for the summary.

### 4. Rendering

`sq board list --raw` prints one numbered markdown item per notice:

```markdown
1. <summary> — <author>, until <until>
2. <summary> — <author>

Read a notice in full with `sq board show <n>`.
```

- `, until <until>` appears only when the notice has an expiry. No `posted_at`, no body.
- A multi-line summary prints its first line on the item and each further line indented three spaces,
  with ` — <author>…` appended to the last line, so the list stays valid markdown.
- The closing line prints only when the board lists at least one notice. An empty board prints `no
  current notices`, as today.
- The rest of ADR-1294 §1's raw-list contract stands: no ANSI, no wrapping, nothing on stdout unless
  the whole list was read.
- The role skill's third `!` line (ADR-1294 §2) and `sq-greeting`'s step 6 (ADR-1294 §4) keep the
  command `sq board list --raw`; their text does not change, their output becomes the index above.
- `sq board list` without `--raw` prints the same fields, one styled line per notice.

### 5. The warnings in `sq check`

Two squad-global validators, always on, default level `warn`:

- `notice_summary_single_line`: for each live notice whose summary holds a line break, one warning
  naming the notice by number and id, with the remedy: post it again with a one-line summary and the
  rest as its body (`sq board post "<summary>" --file <body> --as <author>`, with `--until` when it
  has one), then `sq board clear <n>`. The new post lists after every existing notice, so `<n>` still
  names the old one.
- `memory_summary_single_line`: for each memory whose summary holds a line break, one warning naming
  `<role>/<slug>`, with the remedy: `sq memory <role> forget <slug>`, then `sq memory <role> add
  "<summary>" --file <body> --slug <slug>`.

They join `ALWAYS_ON_SQUAD_GLOBAL_NAMES` and `DEFAULT_SQUAD_GLOBAL_LEVEL` beside
`display_config_valid`: a defect in any squad, so no `[squad] validators` selection names them or
changes their level. An expired notice is not checked, since it lists nowhere. A file neither store
can read is skipped; its read error is reported by `board list` and `memory list` as today. The
post and add warnings of §2 carry the same message. Each rule has a breach test in `tests/check/`.

### 6. The migration

A step of the unreleased 0.19 to 0.20 runner (board notice 17), after its refusal pre-scan, so a
refused run still writes nothing. For each `squads/board/*.md`, expired notices included:

- Frontmatter already holds `summary`: left untouched. A second run is a no-op.
- Otherwise the stripped body is copied into `summary`, the body is kept as it is, and `author`, `posted_at`,
  `until` and any other key are written back unchanged, in the §1 order with other keys after. The
  file keeps its name, so the notice keeps its id and its place in the listing. The write is atomic.
- A file that does not read or parse is left untouched and named in the run's outcome; the step
  refuses nothing.

Memories are not touched. The release's `manual` text says that every migrated notice now lists its
whole text as its summary, that `sq check` warns on each multi-line one, and gives the §5 remedy.

## Decisions narrowed

Each is a clause-level change (board rule 6): narrowed in place with a dated note, linked `related`.

- **ADR-314, Decision, the board paragraph.** A notice's frontmatter is `summary`, `author`,
  `posted_at`, optional `until`, over an optional body; a summary of either tier is one line, and
  `sq check` warns otherwise.
- **ADR-1294 §1, "Raw lists".** The board prints one numbered item per notice with its summary,
  author and expiry, and a closing line naming `sq board show <n>`. The sentence that a one-line
  summary would send the agent to another command is reversed by the ruling.
- **ADR-1294 §2, item 3.** `sq board list --raw` renders the notices' summaries, not their content.

## Consequences

- The board section of each `sq-role-<slug>` skill shrinks from every notice's text to one line per
  notice, once the notices are rewritten. Until then a migrated board renders as large as before;
  the warnings are the signal to rewrite.
- This repository's own squad warns on every multi-line notice once migrated, and `sq check` is a
  clean gate here: whoever migrates this squad rewrites its notices in the same change.
- Rewriting a notice through post and clear gives it a new `posted_at` and moves it to the end of the
  listing; the numbers after the old position shift by one.
- A script that posts with `sq board post -m "<text>"` breaks: the summary is now a required argument.
- The VS Code client reads `summary` from `board list --json` and the body from `board show <n>
  --json` (FEAT-1311 US4). ADR-427 names `sq board list --json` and no shape, so it is unchanged.

## Alternatives rejected

- **The summary as the body's first line, no new key.** Nothing to migrate and nothing stored twice,
  but the ruling makes summary and body separately authored, a multi-line summary must be
  representable for the warning to have something to read, and a memory already stores its summary
  in frontmatter. Two parse rules for two lighter tiers is worse than one key.
- **Refusing a multi-line summary at write time.** Ruled out by op-pierre: warn, never refuse.
- **A `board edit` verb that keeps `posted_at`.** Neither tier has an edit verb, and the ruling asks
  for none. Post and clear already fix a notice; an edit verb can be added if losing `posted_at`
  proves to matter.
- **Printing only the first line of a multi-line summary in `list`.** It would shrink a migrated
  board at once, but it hides text without saying so and makes `list` disagree with the stored
  summary. The warning is the mechanism the ruling chose.
- **Binding rules instead of squad-global validators.** The binding rules carry no level table; the
  always-on squad-global members do, and already hold `warn` defaults.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-11-05T07:14:17Z] `op-pierre` Pierre Chat:
  - Ruling (2026-11-05): I accept this decision with one change: the migration copies each notice's body into its summary and keeps the body as it is, rather than moving it. No edit command is added; post and clear, forget and add stay the way to rewrite.
<!-- sq:discussion:end -->
