---
id: REV-958
sequence_id: 958
type: review
title: 'The --help surface: what belongs in a command''s help text'
status: ChangesRequested
author: tech-writer
assignee: reviewer
refs:
- MILE-934:targets
- REV-956
description: A read of every rendered --help body and flag description, settling what
  help text is for versus a module docstring or docs/.
subentities:
- local_id: F1
  title: Help bodies carry maintainer reasoning and private names
  status: Open
  severity: high
- local_id: F2
  title: One in four option and argument descriptions is blank
  status: Open
  severity: high
- local_id: F3
  title: JSON field reference fills the help body of 13 commands
  status: Open
  severity: medium
- local_id: F4
  title: Help is written for a layout the renderer does not produce
  status: Open
  severity: medium
- local_id: F5
  title: Exit-code prose in 11 commands, in three forms
  status: Open
  severity: medium
- local_id: F6
  title: A per-item verb's help needs a real item to open
  status: Open
  severity: medium
- local_id: F7
  title: Five markup dialects, none rendered; brackets are consumed
  status: Open
  severity: medium
- local_id: F8
  title: Same flag, different words; text that contradicts its screen
  status: Open
  severity: low
- local_id: F9
  title: Summaries name the mechanism or stay generic
  status: Open
  severity: low
- local_id: F10
  title: Flags described in the body and again in the panel
  status: Open
  severity: low
- local_id: F11
  title: Nothing holds a help change to the rule
  status: Open
  severity: low
created_at: '2026-09-15T10:12:29Z'
updated_at: '2026-10-09T18:13:10Z'
---
<!-- sq:body -->
## Scope

Typer renders a command function's docstring as its `--help` output, and every `help=` string on
an option or argument as that flag's line. Both are adopter-facing documentation, written in a
slot that looks like source. This is a read of that rendered surface — all of it, not a sample —
asking one question of each command: **does what a person sees when they type `--help` answer the
question they typed it to ask?**

The pass produces a rule someone can apply, and findings against the commands that break it. It
does not produce rewrites of `docs/`, and it does not touch what the commands do.

## What the surface is, measured

Driven off the live command tree rather than the source files, because most of the item-type
surface is generated per type rather than written out:

- **239 canonical leaf commands** under 94 groups (456 including the type-command aliases).
- **Median help body: 1 line. Mean 3.6.** 143 leaves have a one-line body; 14 have none at all.
- **18 leaves carry a body of 10 or more lines.** That is 7.5% of the surface, and it is where
  everything that provoked this sits: `graph` (35), `check` (32), `override scaffold` (30),
  `search` (28), `role catalog` (27), `import` (26), `tree` (24), `override diff` (23).
- Rendered at 100 columns those become 53, 40, 53, 41, 31, 41, 50 and 41 lines on screen. At 80
  columns — the more common terminal — they are longer.
- **215 options and arguments carry help text; 72 do not.** 33 of the 72 are `--json`. The rest
  include `--type`, `--status`, `--parent`, `--label`, `--assignee`, `--title`, `-m/--message`,
  `--append` and `--force`.

The first conclusion is that this is not one problem. It is two opposite failures at the two ends
of one surface, and a rule that only addresses the long end leaves the larger half untouched.

### The long end: maintainer reasoning in a reader's slot

`sq check` is the clearest specimen, and the most-run command here. Its help body is 32 lines. Two
of them are actionable — the summary and the exit-code line. The remaining 30 argue why the
command degrades the way it does when the workflow spec fails to load, and they do it in the
register of a design note: "gating 'invalid' on `open_service` actually raising — rather than on
any error-level lint finding existing — is what keeps the two from disagreeing". It names
`_check_issue_sort_key`, `workflow_stamp_finding` and `squads._errors.PlaybookConfigError`. The
command has exactly two flags, and one of them is `--help`.

`sq role catalog` is the same shape: 27 lines, of which roughly 20 defend a column's existence
("Without them an all-false column is ambiguous between a holder this listing cannot show and no
holder at all"). Two flags, one undocumented.

`sq search` inverts the priority explicitly. Its `--type`, `--status` and `--json` flags have no
help text at all, above a 28-line body that renders a JSON shape block and a region-naming scheme.
A person reading it learns the envelope of a payload they have not yet asked for, and nothing
about the flag they were reaching for.

`sq override scaffold` is long for a different reason and should not be judged by the same test:
its 30 lines are genuinely about how to use the command, but five of its flags are described twice
— once in prose, once in the options panel a few lines below. That is redundancy, not leakage, and
the fix is different.

### The short end: flags with nothing said about them

`sq list` renders five flags — `--type`, `--status`, `--parent`, `--label`, `--assignee` — as bare
names with an empty description column, directly beneath 13 lines of prose about which items are
hidden by default. `sq tree` does the same for three, plus its `root_id` argument. The flags a
person reaches for first are the blank ones.

`--json` is undocumented at all 33 sites. That may be a defensible convention rather than 33
omissions, but it is currently undeclared either way, and it sits immediately under the prose that
describes the payload in detail on the commands that have such prose.

### Markup: four dialects, none of them rendered

Of the 96 written command docstrings: 31 use RST double-backticks, 21 use single backticks, 3 use
Markdown bold, 2 use an RST `::` literal-block marker, and 49 use no markup at all. Six mix two
dialects in one docstring. The app sets no `rich_markup_mode`, so none of this is interpreted —
`` ``--all`` `` reaches the reader with its doubled backticks visible, and `**Exit codes:**` with
its asterisks. Four Sphinx cross-reference roles render verbatim, role marker and all, three of
them naming a private function or a private module path.

Picking one dialect is a writing decision. Turning on a renderer is not, and the escaping hazard
this project already knows — Rich reads `[...]` as markup — is on the other side of that choice.
The pass should settle the first and state the second as a question, not answer it here.

### Consistency, on a concept that is about to move

Eight commands carry a hand-written exit-code paragraph: `board list`, `import`, `repair`,
`inbox`, `search`, `reflog`, `check`, `migrate up`. They do not agree on form. `check` and
`reflog` name the code and point at the table — "see `sq docs faq` for the full table". `search`
and `inbox` inline the whole contract, including how the degraded case is signalled and what the
JSON array does about it.

A fifth exit code lands across five of those commands in this release, which means five paragraphs
are being rewritten by hand right now, and the table in `docs/faq.md` goes stale in the same
stroke. The pass should decide which of the two forms is the standard before that divergence sets,
and say what the help text owes a reader versus what the table owes them.

A second instance, with the opposite verdict available. `--priority` reads as
`Priority: urgent|high|medium|low.` on the item verbs and as
`Priority code (as defined by your workflow's priority collection).` on `list` and `tree`. That is
not a copy-paste drift: both are derived from the active spec by the same helper, and the item
verbs can enumerate because they know their type while the type-agnostic commands cannot. The
divergence may be correct. Naming it and concluding "these differ for a reason, leave them" is a
finding of the same value as changing one.

## What this pass settles

1. **The rule.** What belongs in a command's help body, what belongs in the module or function
   docstring a maintainer reads, and what belongs in `docs/`. Stated as something a person can
   apply to a docstring they are writing, and as something a reviewer can hold a change to — not
   as a list of the commands that are currently wrong.
2. **Length or order.** Whether 53 lines is itself the defect, or whether the test is that the
   first three lines answer the question a reader arrived with. A short help body that buries the
   answer fails a test that a long one can pass.
3. **`--json` shapes.** `docs/stability.md` is the contract for which shapes are frozen. It names
   `search`, `graph` and `tree` in that frozen set but does not enumerate their fields — the help
   text is currently the only place those are written down. So "move it to the docs" is not a free
   move, and the pass must say where the field-level detail lands and what the help text keeps.
   Deciding it is enough; carrying it out is separate work.
4. **The blank half.** Whether every flag gets a description, whether `--json` is a declared
   exception, and what a one-line flag description is for.
5. **Markup.** One dialect, applied everywhere, chosen for a surface that renders none of them.
6. **What an adopter arrives with.** They have this project's tool, not this project's repository.
   Adopter-facing text describes the tool: no item ids, no repository or build-process content, no
   private identifiers, no cross-references to source. Where a help body is found to be carrying a
   maintainer's reasoning, the reasoning is usually worth keeping — the finding is about where it
   lives, not that it should go.

## What this pass is not for

- **Not a rewrite of `docs/`.** Where content is judged to belong in the docs, the pass records
  that and stops. Moving it is separate work.
- **Not a CLI surface redesign.** No command is added, removed, renamed, split or merged, and no
  group is restructured.
- **Not a behaviour or flag change.** No flag is added, removed, renamed or given a different
  default, and no output changes except the help text itself. Where help text is found to be
  accurate about behaviour that is itself wrong, that is a defect to raise separately, not to fix
  here.
- **Not a docstring sweep of the engine.** Only text that reaches a reader through `--help` is in
  scope. A module or private-function docstring is a maintainer's document and is judged only when
  a command's help body is found to be one.

## Where this meets the structural review

The structural review of the engine is the sibling of this one, and they touch in one place. Two
of the longest help bodies — `check`'s degradation argument and `role catalog`'s column defence —
are prose about designs that review is separately judging. The split: whether the design is right
is that review's question, and this one takes no position on it. This one decides only whether
that prose belongs in the slot a person sees when they type `--help`, and where it goes if not.
The same applies to `search`'s region-naming scheme and `graph`'s edge-semantic rule. Both are
correct and both are load-bearing for a consumer; neither fact settles where they are written.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 958 add-finding "…" --severity medium`; track with `sq review 958 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Help bodies carry maintainer reasoning and private names

<!-- sq:finding:F1:body -->
**Shape.** The rendered help argues why the implementation is built the way it is, names private functions, classes, modules and internal types, or narrates history. A reader with the tool and no repository cannot follow any of it, and it pushes what they came for off the screen. Breaks R3 (and R2's test: no reader types anything differently for having read it).

Line numbers are lines of the help body as written; "r80" is the whole rendered screen at 80 columns. All renders driven from the dev tree. Quotes are shown with single backticks where the rendered text shows doubled ones.

**Private identifiers and source cross-references (driven).** Four Sphinx roles render verbatim, role marker included, and every one names something an adopter cannot import or open:

- `sq check` (32 lines, r80 59): line 8 `:func:` role naming `_check_issue_sort_key`; line 27 `:class:` role naming `squads._errors.PlaybookConfigError`. Also `CheckIssue` (lines 12, 26), `workflow_stamp_finding` (19), `svc.check()` (20), `open_service` (21, 27).
- `sq repair` (12 lines, r80 31): line 3 `:func:` role naming `common.get_service_bypassing_index_cross_check`; line 4 `get_service`.
- `sq workflow view` (11 lines, r80 28): `:func:` role naming `_playbook_json_payload` as the place to learn the `playbook` shape; also a package template path, `templates/views/<name>.md.j2`, described as "adopter-overridable" to the adopter reading it.
- `sq migrate up` (9 lines, r80 22): "(`_cli/_main.py`'s own `repair` command)".
- `sq workflow lint` (8 lines): "This command intentionally does NOT go through `open_service`".
- `sq list` (13 lines, r80 46): lines 12-13, "deriving filter/threshold semantics from `fields_for()` rather than a hand-written per-axis pair".
- `sq workflow lifecycles`: "(never the raw `frozenset` order)".

**Design defence in the reader's slot (driven).**

- `sq check`: lines 10-32, 23 of 32. What a reader acts on is the summary and the exit-code lines (1, 3-4). Lines 16-23 defend why "invalid" is gated on the service failing to open; lines 25-32 defend why a playbook failure is a separate issue and why its message names no command. The command has one flag besides `--help`.
- `sq role catalog` (27 lines, r80 57): lines 10-27 explain what the default column means inside and outside a squad and why two JSON fields repeat on every row ("Without them an all-false column is ambiguous between..."). One flag, undescribed.
- `sq role list` (6 lines): lines 3-6, why this listing can name every holder and the catalog cannot.
- `sq repair`: lines 3-7, which service accessor it uses and why; lines 10-12 justify the exit code ("so a caller gating on `$?` cannot mistake...").
- `sq tree` (24 lines, r80 67): lines 13-17, why a parent cycle gets an invented anchor ("every member of a cycle has a parent, so a cyclic component would otherwise be absent...", "a tiebreak rather than a real root").
- `sq workflow statuses`: "Catalog-only: no per-item `role`/`is_active` field is added to any item surface".
- `sq workflow collections`: "once per spec instead of duplicated onto every item".
- `sq override scaffold`: "the two are not interchangeable and this command distinguishes them so they can't be confused".
- `sq skill <addr> body`: "probing whether the verb is permitted here costs nothing".
- `sq migrate up`: lines 6-9, why its code matches `sq repair`'s.
- `sq import`: line 16, "rather than attributing to whatever role this squad happens to be configured to default to".

**History (driven).** `sq search` line 10: "a stable superset of the legacy `{id, title, hits}`". `sq workflow roles`: "`settled` is the old `terminal`". `sq check` line 31: "There is today no dedicated playbook lint surface to name instead". A reader of 0.16 has no "legacy" or "old" to compare against.

**Shouted caveats in a flag description (driven).** `sq reflog --tree`: seven rendered lines at 80 columns, including "BEST-EFFORT, UNTRUSTED, OBSERVABILITY-ONLY — reflects declared lineage; a copied session id appears as a legitimate edge." One plain sentence carries the same warning.

**Fix.** None of this reasoning is wrong and most of it is worth keeping; the defect is where it lives.

- Reasoning about one piece of code moves to a comment at that code (why `repair` takes the bypassing accessor belongs on that line).
- Reasoning about a design moves to the docstring of the helper or module that implements it. The per-type commands already work this way (read): the registration helpers in `_cli/_items.py` and `register_status_verb` in `_cli/_common.py` carry the maintainer's notes, and the nested command docstring is one line.
- Where a maintainer wants a note to stay in the command function's own docstring, it goes after a form feed: Typer cuts the rendered help at `\f` (driven with a probe command; no command in the tree uses it yet).
- What a caller depends on is contract, not reasoning, and goes to the docs. That part is the subject of the JSON-reference and exit-code findings.
- What `sq check` keeps: the summary, the exit-code line, one sentence that output order is stable, one sentence that a broken workflow or playbook override is reported as an issue and the remaining checks still run.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — One in four option and argument descriptions is blank

<!-- sq:finding:F2:body -->
**Shape.** An option or argument renders as a bare name with an empty description cell. Breaks R4 and R5.

**Measured (driven, from a walk of the live command tree).** 741 options and arguments render across the 225 canonical leaves and their 47 groups, `--help` itself excluded. 186 are blank, one in four. 115 of the 225 leaves show at least one blank. They come from about 66 distinct declarations: most of the count is a per-type or per-kind command registered once and rendered many times, so the fix is far smaller than the count.

| Blank | Sites | Where |
|---|---|---|
| `--json` | 79 of 91 | every command that takes it except `tree`, `override list`, `override diff` and the `workflow` catalogs |
| `--assignee` | 17 | `list`, `tree`, `<type> update`, the three `add-<kind>` verbs, the three `<kind> update` verbs |
| `STATUS` argument | 12 | `<type> status`, and `status` on role, operator and skill |
| `--title` | 12 | `<type> update`, the three `<kind> update` verbs |
| `--force` | 12 | `<type> status`, the three `<kind> update` verbs |
| `--add-label`, `--rm-label` | 9 each | `<type> update` |
| `-m/--message` | 9 | `add-<kind>`, `<kind> body`, `<kind> comment` |
| `--type/-t`, `--status/-s` | 3 each | `list`, `tree`, `search` |
| `--status`, `--clear-assignee`, `--append` | 3 each | the `<kind>` verbs |
| address argument | 3 | the `role`, `operator` and `skill` address groups |
| `--parent` | 2 | `list`, `skill add` |
| `--label`, `ROOT_ID`, `slug`, `name`, `--desc`, `--when-to-use`, `--allowed-tools` | 1 each | `list`; `tree`; `role activate`; `skill add` (all four of its options and its argument) |

**The blank ones are the ones reached first (driven).** `sq list` renders `--type`, `--status`, `--parent`, `--label` and `--assignee` empty, under a 13-line help body. `sq search` renders all three of its options empty under a 28-line one. `sq skill add` describes nothing at all: one argument and four options, every cell empty. `sq <type> status` leaves both its argument and `--force` empty, on the verb an agent runs most.

**Not one of these is hard to describe (driven).** Most of the blank flags are already described on a sibling command: `--assignee` is "Role slug or ID." on `create`, `--append` is "Append instead of replacing." on `<type> body` and blank on `<kind> body`, `--label` is "Label (repeatable)." on `create`, `--force` is "Force an invalid transition." on `<type> update` and blank on `<type> status`, which is documented as its shortcut.

**`--json`.** Position taken in R5: described on every command that takes it, never left blank by convention. A blank cell cannot be told from an omission, a convention has to be declared somewhere the `--help` reader looks and the cell is the cheapest such place, and the tree already describes 12 of the 91, in wordings that follow no one pattern ("Emit machine-readable JSON.", "Emit the nested subtree as JSON.", "Emit the machine type catalog."), so no convention is in force today. One line, naming the top-level shape: an array with one object per row, or a single object.

**Fix.** Give every option and argument a `help=`, one line, per R4. Declare each shared flag's text once and reuse it, so the per-type, per-kind and roster registrations cannot drift (the `--priority` help is already built this way, read). For `STATUS`, name where the legal values come from. Roughly 66 declarations, many of them a string that already exists elsewhere in `_cli/`.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — JSON field reference fills the help body of 13 commands

<!-- sq:finding:F3:body -->
**Shape.** The help body is a reference for the `--json` payload: a field list, a shape block, the vocabulary of a field's values, instructions for joining one payload to another. A person who typed `--help` to learn what the command does reads the envelope of an output they have not asked for. Breaks R6.

**Offending commands (driven).** Lines are lines of the help body as written; r80 is the whole screen at 80 columns.

| Command | Body | JSON reference | r80 |
|---|---|---|---|
| `sq graph` | 35 | lines 3-30: field list, 11-line shape block, 12 lines on `edge_kind` / `edge_semantic` / `direction` | 73 |
| `sq search` | 28 | lines 4-22: the `region` naming scheme, 11-line shape block | 51 |
| `sq tree` | 24 | lines 19-24: field list, `anchor`, the join to the status catalog | 67 |
| `sq role catalog` | 27 | lines 19-26: `default_role`, `default_role_source` and their values | 57 |
| `sq workflow types` | 15 | lines 3-15, everything after the summary | 30 |
| `sq workflow roles` | 11 | lines 3-11 | 25 |
| `sq workflow view` | 11 | lines 4-11: which other command's shape each source kind matches | 28 |
| `sq workflow subentity-kinds` | 10 | lines 3-10 | 24 |
| `sq workflow lifecycles` | 10 | lines 3-10 | 23 |
| `sq workflow collections`, `statuses`, `ref-kinds` | 8 each | everything after the summary | 18-20 |
| `sq workflow views` | 5 | lines 3-5 | 14 |

`sq override list` and `sq override diff` each give the shape in one or two lines at the end of the body, which is the proportion R6 allows.

**Two different situations, and the fix differs.**

1. *The docs already carry it (read).* `docs/stability.md`, in its tier for `--json` shapes, tabulates the field set of seven workflow catalogs (`types`, `subentity-kinds`, `collections`, `statuses`, `roles`, `lifecycles`, `views`) and describes the joins and the `workflow view` shapes in prose. `docs/roles.md` describes `sq role catalog --json`'s `default_role` and `default_role_source`, their values, and the footer of the plain listing. Those nine help bodies restate the docs and can shrink to the summary, the one-line `--json` description and a pointer, with nothing to move first. `sq workflow ref-kinds` is the exception: no document under `docs/` lists its fields (a search for the command with `--json` finds one mention, without them), so it belongs to the second group.
2. *The help is the only place it is written (read).* The same document says of the remaining shapes that "the authority is the command's own `--json` output together with what `sq <command> --help` says about it: `sq search`, `sq tree` and `sq graph` document their shapes there in full". For those three, and for `workflow ref-kinds`, removing the reference from help deletes it. It has to land in the docs in the same change that takes it out of help, and that sentence in the stability document has to change with it.

**Position.** Field-level reference lives in `docs/stability.md` beside the freeze it documents. Help keeps three things: the one-line `--json` description naming the top-level shape; any sentence a caller needs in order not to misuse the payload; a pointer, `Fields: sq docs stability`. The don't-misuse sentences worth keeping, one each:

- `sq graph`: branch on `edge_semantic`, never on `edge_kind`, which a project can rename.
- `sq tree`: a node with `anchor` true is an invented root for a parent cycle, not an item somebody made a root.
- `sq search`: `region` says where the hit was found; the docs list its values.

On that footing `sq graph` goes from 35 lines to about 8 and `sq search` from 28 to about 6 (inferred from the lines that remain).

**Out of this review's hands.** Writing the reference into the docs is separate work. This finding records where it goes and that the move and the trim are one change for `search`, `tree`, `graph` and `workflow ref-kinds`.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Help is written for a layout the renderer does not produce

<!-- sq:finding:F4:body -->
**Shape.** The text is written for a layout the renderer does not produce. Four variants, one cause: nobody looked at the rendered screen at 80 columns. Breaks R9, and R1 for the summary variant.

**Mechanism (read in the installed Typer, then driven with a probe command).** Typer joins the lines of the first paragraph of a help body and leaves every later paragraph's source line breaks in place. Rich then wraps each of those lines to the terminal. The help bodies are wrapped in source at up to 96 columns after dedent, so on an 80-column terminal a source line becomes one full line plus a stub.

**1. Ragged bodies (driven).** 43 of the 44 distinct help bodies that go beyond a summary have at least one line over 78 columns; 255 of their 364 body lines re-wrap at 80. That is 71 rendered leaves. `sq check` at 80 columns:

```
 Output (console and ``--json`` alike) is sorted into a deterministic total
 order —
 squad-global issues first, then by item, error before warn, then message — so
 it is
 diffable/stable across runs; see :func:`_check_issue_sort_key`.
```

Worst by share of lines that break: `sq role catalog` 22 of 23, `sq check` 20 of 26, `sq graph` 19 of 30, `sq override scaffold` 17 of 23, `sq import` 16 of 20, `sq tree` 16 of 19. The per-type verbs are in it too: `<type> remove` 4 of 5, `<type> body` 3 of 3, `<type> retype` 2 of 3. This is why the eight longest bodies run 51 to 75 lines on an 80-column screen against 34 to 52 at 100.

**2. Enumerations cut off (driven).** A description holding one long unbreakable token is truncated with an ellipsis, and the values past the cut are not shown anywhere.

- `sq <type> retype`, the `NEW-TYPE` argument, nine commands: renders `epic|feature|task|bug|decision|contract|milest…`. `milestone`, `review` and `guide` are lost at 80 columns.
  The suite knows (read, `tests/cli/test_help_text_follows_spec_vocabulary.py`): its retype test asserts the cut string `...contract|milest` and comments that the last types "no longer fit and the column ends in an ellipsis". The sibling test for a project-declared type asserts only that the type's name occurs in the output, which the usage line `sq incident N retype` satisfies whether or not the enumeration shows it (inferred from reading, not run). Both assertions move with the fix.
- `sq reflog --op`: renders `(create/status/update/body/comment/subentity/ref/…`. Nine of the sixteen operation names are lost at 80 columns, and seven are still lost or cut mid-word at 100.

**3. Summaries wrapped in source (driven).** A parent's Commands table keeps a summary's source line break. Three summaries are written over two or three lines and render ragged in every table that lists them:

```
│ renumber   Pre-merge block-shift: reassign this branch's local IDs into a    │
│            range disjoint from                                               │
│            another branch's, preserving referential intent.                  │
```

`sq renumber` (131 characters), `sq workload` (124), and `sq <type> comments` (167 characters over three source lines, nine commands). 30 of the 105 distinct summaries exceed 72 characters, so they wrap inside the table at 80 columns even when written on one line; the median is 63.

**4. Example blocks collapsed (driven).** The epilogs of `sq role`, `sq operator` and `sq skill` are written as an aligned block of example invocations and render as one run-on paragraph:

```
 Address an operator:  sq operator <slug|id|n> show|rm|status Examples:  sq
 operator op-alice show   sq operator 2 rm            sq operator op-alice
 status Archived Note: a slug matching a group verb (add, list) is
 unaddressable by slug; use the full ID or bare number instead.
```

The shape blocks in `sq search` and `sq graph` keep their line breaks but lose their continuation: a line of the JSON sample that passes 78 columns wraps to column 1 (`"status":` on one line, `"InProgress",` on the next). The aligned `Δ-mine:` / `Δ-upgrade:` legend in `sq override diff` and the indented `git show` command in `sq renumber` survive only because they happen to be short.

**Related, same family (driven).** The usage line for the addressed roster verbs prints both the placeholder and the argument's own name: `Usage: sq role <slug|id|n> ADDR show [OPTIONS]`. The sub-entity verbs print two identical placeholders: `Usage: sq feature N story N show [OPTIONS]`.

**Fix.** Wrap body paragraphs at 78 columns after dedent. Put anything that depends on its line structure in a no-rewrap block (`\b` on the line before it; driven, it holds) and keep it under 78. Replace a long inline enumeration with the command that lists the vocabulary, or break it into separate words the renderer can wrap. Write every summary on one source line, 72 characters or fewer. Give the two address placeholders distinct names and drop the duplicate.

Variant 1 goes away by itself if the renderer is changed to one that re-flows paragraphs; that choice is raised as a question in the markup finding, and the other three variants stand either way.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Exit-code prose in 11 commands, in three forms

<!-- sq:finding:F5:body -->
**Shape.** A hand-written exit-code paragraph, in a form that differs from command to command, restating a contract the docs already hold as a table. Breaks R7.

**Measured (driven).** Eleven commands carry exit-code prose in their help body. Two point at the table; nine inline the contract.

| Command | Exit-code lines / body | Form |
|---|---|---|
| `sq check` | 2 / 32 | codes, then "See `sq docs faq` for the full exit-code table." |
| `sq reflog` | 1 / 11 | "0 = normal; 1 = error; see `sq docs faq` for the full table." |
| `sq inbox` | 5 / 7 | inlines code 4, the stderr line, the JSON line, "shape is unchanged" |
| `sq search` | 5 / 28 | same paragraph, reworded |
| `sq board list` | 4 / 6 | same paragraph, reworded |
| `sq memory <role> list` | 5 / 7 | same paragraph, reworded |
| `sq memory <role> search` | 4 / 6 | "Same degrade-signal rule as `sq memory <role> list`", then restates it anyway |
| `sq import` | 8 / 26 | two paragraphs on codes 1 and 3 |
| `sq repair` | 4 / 12 | code 1, plus three lines justifying it |
| `sq migrate up` | 7 / 9 | code 1, plus four lines on why it matches `sq repair` |
| `sq workflow lint` | 4 / 8 | prose, split between the summary ("and exit 0/1") and the body |

**What is wrong with it.**

- *Five copies of one contract.* `inbox`, `search`, `board list`, `memory list` and `memory search` each describe the same partial-result signal: exit 4, one `error:` line per skipped file on stderr, one JSON line under `--json`, payload shape unchanged. `docs/faq.md` and `docs/stability.md` both state exactly this, once, for all five by name (read). The five paragraphs are five places to edit when it changes, and on four of the five commands they are most of the help body.
- *One line that says nothing.* `sq reflog`'s "0 = normal; 1 = error" is the general contract every command has.
- *Three notations.* `Exit codes:` plain, `**Exit codes:**` with visible asterisks (`reflog`), and running prose (`workflow lint`, `memory search`). Codes are written `0 = ...`, `0 when ...` and `exits 0 with ...`.
- *Vocabulary the reader was never given.* "degrade-signal rule" (`memory search`), "the integrity catalog", "the pre-pass" and "applied-and-flagged" (`import`).

**The standard.** Of the two forms in the tree, the pointer form is the one to keep, with this division of labour:

- A command with no code of its own says nothing about exit codes.
- A command with a code of its own says one line, in one notation: `Exit codes: 0 clean, 4 some files could not be read (the rest is still printed). See sq docs faq.`
- The help owes the reader the code and what it means for them in six words. The table owes them the mechanics: what goes to stderr, what the JSON reader sees, why the code is distinct from 1.
- One kind of sentence stays in help because it prevents misuse at the moment of typing: a code that is non-zero although the work was applied. `sq import`'s "exit 3 means the events are on disk; do not retry on non-zero, read `applied` from `--json`" is that sentence and should survive, in two lines, not eight.

**A dependency to carry with the fix (read).** The pointer form is only as good as the table. `docs/faq.md`'s row for code 3 names `sq check` alone, while `sq import`'s help claims 3 as well and the command raises it (`_cli/_import.py`). Whoever shortens `import`'s paragraph needs the table to say so first. Changing the table is outside this review.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — A per-item verb's help needs a real item to open

<!-- sq:finding:F6:body -->
**Shape.** The help for a per-item verb cannot be displayed unless the number in the command resolves to an existing item of that type. The text is fine; a reader cannot get to it. This is the one finding here that no change of wording fixes.

**Driven, in this repository's own squad.**

| Command | Result |
|---|---|
| `sq task 954 show --help` | the help for `show`, exit 0 |
| `sq task 1 show --help` | `error: 1 is ROLE-1 (role), not a task`, exit 1 |
| `sq task 999999 show --help` | `error: no item with number 999999 (use TASK-999999 or bare 999999)`, exit 1 |
| `sq task x show --help` | `error: invalid item id 'x' (use a bare number or a full ID like TYPE-NNNNNN)`, exit 1 |
| `sq task show --help` | the help for the `task` group, not for `show`, exit 0 |
| `sq skill nosuch show --help` | `error: no skill with slug, ID, or number 'nosuch'`, exit 1 |
| `sq role nosuch show --help` | the help for `show`, exit 0 |

**Driven, from a directory with no squad.** `sq task 1 show --help` prints `error: no .squads.toml found in this or any parent directory — run sq init` and exits 1. `sq list --help` and `sq check --help` render normally from the same directory.

**Reach.** 138 of the 225 canonical leaves are per-type verbs behind this gate (six types with 13 leaves, three with 20), and the 12 addressed `skill` verbs behave the same way. Before `sq init`, and in a new squad that has no item of a given type yet, none of that help can be read (inferred for the empty squad: it is the same refusal as the `999999` row). That is the moment a newcomer is most likely to ask. The `role` address group shows that the other behaviour is available: it renders help for a slug that does not exist.

The root help makes it worse by advertising the route: "per-command help: `sq <command> --help`". For `sq task`, that prints a Commands table whose every row needs a valid number before its own help will open, and the group help does not say so.

**Fix.** Outside the text. `--help` on a leaf should render without resolving the address in front of it, as it already does for `role`. That is a change to how the item and skill groups resolve their address, so it needs its own item and its own tests; this review records it and does not size it. A text-only mitigation, if the behaviour stays: one line in each type group's help saying that any existing number of that type works as a placeholder for reading a verb's help.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Five markup dialects, none rendered; brackets are consumed

<!-- sq:finding:F7:body -->
**Shape.** Help text is marked up in a syntax the renderer prints verbatim, in several syntaxes at once. And the one syntax the renderer does interpret is the one nobody is writing for. Breaks R8.

**Measured on the 105 distinct help bodies behind the 225 canonical leaves (driven).**

| Dialect | Bodies | What the reader sees |
|---|---|---|
| RST double backticks | 31 | the doubled backticks, around every flag and value |
| single backticks | 20 | single backticks |
| both in one body | 5 | `check`, `repair`, `tree`, `role list`, `memory search` |
| emphasis with single asterisks | 6 | `*were*` (`inbox`, `search`), `*n*`-th (`search`), `*refused*` (`role activate`), `*contents*` (`migrate repad`), `*codes*` (`workflow collections`), `*for the active squad*` (`role catalog`) |
| bold with double asterisks | 3 | `**Exit codes:**` (`reflog`), `**separate**` (`check`), `**branch on this field**` (`graph`) |
| RST literal-block marker | 2 | a line ending `Shape::` (`graph`) and one ending `)::` (`search`) |
| Sphinx cross-reference roles | 4, in 3 bodies | the role marker and target verbatim (`check` twice, `repair`, `workflow view`) |
| no markup | 59 | |

Option descriptions use a third quoting convention: single quotes around a literal value (`'-' = stdin`, `'dot'`, `'workflow'`) at 59 rendered sites, single backticks at 14.

`sq graph` also contains a Markdown fence quoted inside RST double backticks, which renders as four backticks, a space, three backticks and the word mermaid.

**The renderer is not off (driven).** The app passes no markup mode, and in the installed Typer (0.26.7) the default is Rich console markup, not none: the app object reports `rich_markup_mode == 'rich'`. So backticks, asterisks and RST are printed as typed, and square brackets are interpreted. A probe command with a help body containing `a [x] checkbox` renders `a checkbox`, and the same in an option description. The bracket hazard this project already manages for console output is therefore live in help text today.

Nothing in the tree trips it at present: a scan of every help body and option description for a bracketed span starting with a lowercase letter, `#`, `/` or `@` (what Rich reads as a tag) finds none, and the spans that do appear (`[...]`, `[<ts>]`, `[OPTIONS]`) are left alone. It is one docstring away, and the failure is silent: the words vanish and nothing errors.

**Decided here: the dialect.** Plain text, with single backticks around anything typed literally (a command, a flag with its value, a status name). Nothing else: no doubled backticks, no asterisks, no `::`, no cross-reference roles. Placeholders in angle brackets, alternatives with a bar. No square brackets around a lowercase word while the renderer is Rich. Single backticks win because they are what the 20 single-backtick bodies, the root help and the option descriptions already use, and they read correctly whether or not anything renders them.

**Not decided here: the renderer.** Stated as a question for the operator, with what each answer does (driven with one probe body under each mode):

- *Rich markup (today).* Backticks literal; a bracketed lowercase span is consumed; source line breaks kept in every paragraph after the first.
- *Markdown.* Single and double backticks and bold are rendered and their delimiters removed; brackets are safe; paragraphs re-flow, which removes the ragged wrapping recorded in the layout finding; an indented block is kept as code. With colour off, a code span has nothing left to mark it. Tests that assert on rendered help text would move with it (inferred, not run).
- *None.* Everything literal, brackets safe, paragraphs re-flow, and the boxed Options and Commands panels are replaced by Click's plain lists.

The dialect above is right under all three, so the text can be fixed before the question is answered.

**Fix.** Convert the 31 double-backtick bodies and the five mixed ones to single backticks; drop the asterisks; replace the two `::` markers with a plain colon; remove the four cross-reference roles (they go with the maintainer reasoning they belong to); settle literal values in option descriptions on single backticks.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-09T18:13:10Z] Pierre Chat:
  - 2026-10-09: the renderer stays on Rich markup. Bodies are re-wrapped at 78 columns with the rewrite, and the surface test fails on a bracket tag or an over-wide line. Markdown mode was ruled out because it deletes angle-bracket placeholders outside backticks and strips backticks in colour-off output.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Same flag, different words; text that contradicts its screen

<!-- sq:finding:F8:body -->
**Shape.** One flag with one meaning is described in different words on different commands, or the description restates or contradicts something else on the same screen. Breaks R4's last clause: the same flag carries the same words everywhere, from one definition.

**Same meaning, different words (driven).** Counts are distinct wordings among the canonical leaves, a blank counted as one.

| Flag | Wordings | Examples |
|---|---|---|
| `--file` | 5 | "Read the body from a file ('-' = stdin)." (`create`), "Body from a file ('-' = stdin)." (`body`, `add-<kind>`), "Comment from a file ('-' = stdin)." (`comment`), "Notice body from a file ('-' = stdin)." (`board post`), "Read a longer body from PATH ('-' for stdin)." (`memory add`) |
| `-m/--message` | 5 | "Body paragraph; repeat for several (or use --file)." (`create`), "Body paragraph." (`body`), "A talking point." (`comment`), "The notice text." (`board post`), blank on nine sub-entity verbs |
| `--force` on a status change | 3 | "Force an invalid transition." (`<type> update`), blank (`<type> status`, `<kind> update`), "Override the lifecycle's own disallowed transition edge. Never overrides a refusal that the resulting config would be invalid." (role, operator, skill `status`) |
| `--raw` | 3 | "Plain text output (opt out of markdown render)." (`show`), "Print plain body text (no markdown rendering)." (role, operator, skill `show`), "Plain markdown output (opt out of Rich markdown render)." (`workflow show`) |
| `--desc` | 3 | "Short summary (shown in lists; not the body)." (`create`), "Short summary (not the body)." (`update`), blank (`skill add`) |
| `--author` | 2 | "Authoring agent (role slug); must be registered." (eight `create` commands), "Authoring agent (role slug)." (`create guide`, `<type> update`) |
| `--all` meaning closed items | 2 | "Include closed (done/cancelled) items." (`list`, `tree`), "Include closed items." (`graph`, `mine`) |
| `--depth` | 2 | "Maximum depth from root (root = 0)." (`tree`), "BFS depth (default 2; 0 = root only)." (`graph`) |
| `--tech` | 2 | "Technology (e.g. python, react)." (`create guide`), "Technology, e.g. dotnet, python, react." (`dev add`) |

Whether `-m` repeats is stated on `create` and nowhere else, so a reader of `comment` cannot tell that it does.

**Text that disagrees with its own screen (driven).**

- `sq list --all` and `sq tree --all`: "Include closed (done/cancelled) items." sits under a body that spends five lines explaining that closed is category-aware and that a records item hides on `Superseded` or `Deprecated`, neither of which is done or cancelled.
- `--author`: "Authoring agent (role slug)", while `--as` on `comment` reads "Author: a role slug or 'op-<slug>'". An operator can author an item (read, from the generated project instructions), so the `--author` text is the incomplete one.
- Required, said two ways. `--author` is marked by the panel (an asterisk and `[required]`). `--as` on `comment` and `board post` is not marked and says "(required)" in its own text instead, so the two required flags of one workflow look different.
- Defaults, said twice. `sq graph --depth`: "BFS depth (default 2; 0 = root only). [default: 2]". `sq graph --direction`: "'both' (default). [default: both]". `sq adopt --squad-dir`: "(default if no .squads.toml yet). [default: squads]". The bracketed half is printed by the renderer.

**Judged and left alone.** `--priority` reads "Priority: urgent|high|medium|low." on the item verbs and "Priority code (as defined by your workflow's priority collection)." on `list` and `tree`. Both come from the active spec through one helper (read, `_cli/_items.py` and `_cli/_create.py`): a command that knows its item type can enumerate that type's collection, and a type-agnostic filter cannot, because the answer differs per type. The difference is information. `--kind` on `graph` ("Ref kind to follow") against `ref add` ("Edge kind ...") and `--all` on `refs` ("Both directions.") are different meanings under a shared name and are also correct as they stand. The `override` trio's `--role`, `--workflow`, `--playbook` and `--roles-catalog` vary only in their verb, which is right.

**Fix.** One shared definition per flag in `_cli/_common.py`, used by every registration that takes it. Drop hand-written defaults and "(required)" where the panel prints them; where a flag is required but validated by hand, say so in the same words each time. Correct `--all` to "Include closed items." and `--author` to name operators.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Summaries name the mechanism or stay generic

<!-- sq:finding:F9:body -->
**Shape.** The first line of a help body, which is also the row a parent's Commands table shows, names the mechanism instead of the outcome, is generic where the command is specific, or is built from a template that does not fit its slot. Breaks R1. (Summaries that are too long or wrapped in source are recorded with the layout finding.)

**Mechanism or internal vocabulary in the summary (driven).**

- `sq graph`: "Show the ref graph around an item (ego-centric BFS traversal)."
- `sq renumber`: "Pre-merge block-shift: reassign this branch's local IDs into a range disjoint from another branch's, preserving referential intent."
- `<type> view add`, and the same on role and skill, eleven commands: "Place the sq:view:NAME tag enabled, or re-enable it if disabled (idempotent)." `view disable`: "Disable the sq:view:NAME tag (placed disabled if absent) — never removed." Neither says what a view is or what the reader gets by placing one.
- `<type> comments`, nine commands: "Read back the item's top-level discussion (the dedicated, machine-readable verb — `show --comments` renders the same discussion inline alongside the rest of the item)." The parenthesis is longer than the sentence.
- `sq workflow lint`: "Validate the workflow override spec — collect ALL errors and exit 0/1."
- `add-story`, `add-subtask`, `add-finding`: "Scaffold a story on this item." The verb the reader typed is add; scaffold is the implementation's word.

**Generic where the command is specific (driven).**

- `sq feature <n> stories`, `sq task <n> subtasks`, `sq review <n> findings`: all three read "List this item's sub-entities." The command name is the specific word and the help replaces it with the internal category. The sibling verbs do it too: "Show the sub-entity's status/assignee, body, and discussion.", "Comment on the sub-entity's discussion.", "Hard-delete this sub-entity". The `update` verb on the same group gets it right, "Update the finding's metadata", so the kind's name is available at registration.
- `status` on role, operator and skill: "Transition the entity's status (shortcut for the work-item `status` verb)." There is no work-item verb this one abbreviates; a reader cannot act on the parenthesis.

**Template does not fit the slot (driven).**

- "Operate on a epic by number." and "Create a epic." The article is fixed in the template. With the bundled types only `epic` trips it; a project that declares `incident` gets the same.
- The type groups read "Operate on a task by number." while the argument beside it reads "task number or id."

**Fix.** Rewrite each summary as one sentence, verb first, in terms of what the reader gets. Pass the kind's own singular and plural labels into the sub-entity verbs' summaries the way `update` already does. Reword the two templates so they need no article, or derive it from the type name's first letter.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — Flags described in the body and again in the panel

<!-- sq:finding:F10:body -->
**Shape.** The body describes a flag in prose that the options panel a few lines below describes again, or describes the flags collectively where the panel leaves them blank. Nothing here is maintainer reasoning: the text is for the reader and about using the command. It is said twice, or in the wrong one of the two slots. Breaks R4: a flag is described once, in the panel, and the body adds only how flags combine.

**Described twice (driven).**

- `sq override scaffold` (30 lines, 75 rendered at 80 columns). Lines 9-30 are four paragraphs, one each for `--new`, `--workflow`, `--playbook` and `--roles-catalog`; each of those flags has its own description in the panel, and the `NAME` argument's description lists `'workflow'`, `'playbook'` and `'roles'` a third time. `--role`, the one selector with no paragraph of its own, appears only as what the role catalog is not (lines 24 and 29).
- `sq override diff` (23 lines, 52 rendered). Lines 10-19, three paragraphs for `--workflow`, `--playbook` and `--roles-catalog`, each restating its flag and its positional spelling.
- `sq import` (26 lines). Lines 14-16 state the no-fallback rule for `--as`; the `--as` description states it again in full.
- `sq <type> body`, `sq <type> <kind> <k> body` and `sq skill <addr> body`. The body explains that replacing is refused without `--force`; `--force` reads "Replace an already-written body (destructive, no undo)." The overlap is small, and the body's extra half-sentence (a bare `body` on an occupied item is a safe probe) is the part worth keeping.

**Described in the wrong slot (driven).**

- `sq tree`, lines 7-11: "Filters (--type, --status, --assignee, --category, --priority) narrow the tree to matching nodes", while `--type`, `--status` and `--assignee` are blank in the panel directly below.
- `sq list`, lines 9-13: one paragraph covering `--category`, `--priority`, `--min-priority`, `--badge` and `--min-badge`, each of which has its own description in the panel, above five other filters that have none.
- `sq search`, line 3: `--type` and `--status` "AND-compose with the query", both blank in the panel.

**Fix.** Move each flag's sentence into that flag's `help=` and delete it from the body. Keep in the body only what no single flag can say: for `override scaffold`, that there are four kinds of override and that the positional name and the flag are two spellings of one choice, in about five lines; for `tree`, that ancestors of a match are kept and dimmed.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — Nothing holds a help change to the rule

<!-- sq:finding:F11:body -->
**Shape.** Not a defect in any one command: the absence of anything that would have caught the others. The help rule exists nowhere a contributor reads, and no test looks at the content of the surface.

**What exists today (read).** The tests named for help text under `tests/cli/` pin the rendered width, pin that output is unstyled, and check that spec-derived help follows the active vocabulary. A search of `tests/` for code that walks the command tree or reads a parameter's help finds one module, the gate on the reflog operation vocabulary. Nothing asserts that an option has a description, that a summary fits a line, or that a body is free of private names. One test asserts a truncated enumeration as the expected output. `CONTRIBUTING.md` and the project instructions say nothing about what a command's help is for. That is how one in four descriptions came to be blank and four source cross-references came to ship as help: each was a reasonable docstring to the person writing it, in a slot that looks like source.

**What is cheap to hold mechanically.** The whole surface can be walked in-process from the Click tree in a few seconds (driven: 550 command records, 225 canonical leaves, each rendered at two widths, under four seconds). A test over that walk can assert, for every canonical command:

- every option and argument has a non-empty description;
- the summary is one source line of at most 72 characters;
- the rendered help contains no doubled backtick, no `:func:` or `:class:` role, and no `::` line ending;
- no body line exceeds 78 columns after dedent;
- no rendered line at 80 columns ends in a truncation ellipsis.

Each of those would fail today, so each lands with the fix for its finding, not before. The walk has to cover the per-type and per-kind commands through the live tree, not the source: 66 blank declarations render as 186 blank cells, and a source-level check undercounts by that ratio.

**What is not mechanical.** Whether a sentence is maintainer reasoning, and whether a body's first lines answer the reader's question, are a reviewer's call. For those the rule has to be written where a contributor finds it before writing a docstring.

**Fix.** Put the rule from this review's discussion in the contributor guidance, in its own short section. Add the walk-based test with the five assertions above, each enabled as its finding is fixed.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-15T10:13:23Z] Theo Writer:
  - Scoped by driving the live command tree rather than reading the source, because most of the item-type surface is generated per type and a source-only read undercounts it badly: 107 written command functions, 239 canonical leaf commands rendered (456 with aliases). Sampled at HEAD via an exported copy, since a dev is mid-edit in this tree.
    
    What the sampling changed about the framing. The surface is not long — median help body is one line, and 143 of 239 leaves are one-liners. Eighteen leaves carry ten lines or more, and that 7.5% is the whole of what provoked this. The other end is the larger problem by count: 72 options and arguments have no description at all against 215 that do, including `--type`, `--status`, `--parent`, `--assignee` and `--title`. `sq search` has both faults at once — a 28-line body about the JSON envelope above three flags with nothing said about them. So the item scopes two opposite failures at the two ends of one surface, not one.
    
    Two things worth knowing before the pass runs. `docs/stability.md` names `search`, `graph` and `tree` in the frozen `--json` set but does not enumerate their fields — the help text is currently the only place those are written down, so moving them out is not free and the item says so rather than assuming the docs already carry it. And the exit-code paragraph is hand-written in eight commands in two different forms, five of which are being rewritten right now for the fifth code; `sq check`'s "see `sq docs faq` for the full table" is the in-tree precedent, and settling the form before that divergence sets is cheaper than after.
    
    Deliberately not in it: no findings (nothing to find until the pass runs), no docs rewrite, no CLI redesign, no flag or behaviour change, and no position on the designs whose rationale sits in `check`'s and `role catalog`'s help bodies — that is REV-956's ground, and the item draws the line explicitly so the two do not collide.
    
    @manager — REV-958 authored, targeting MILE-934, related to REV-956, left in its initial status. `sq check` clean. Two things to route: it trips the same advisory REV-956 did (author `tech-writer`, lane expects `reviewer`), so the same decision applies about who runs it; and MILE-934's own "does not belong here" line excludes docs sweeps with no adopter-visible effect — this is adopter-visible text rather than a docs sweep, but the targets ref is yours to confirm. TASK-946 (docs for the 0.15 memory/board read views) is adjacent and separate; nothing here overlaps it.
- [2026-10-09T15:44:05Z] Paul Reviewer:
  - **The rule for help text.** The findings on this review are held to it, and cite it by number.
    
    `--help` is read by someone who has the tool and not the repository, about to type the command. It answers three questions in this order: what does this do, what do I type, what do I get back or lose. A sentence that answers none of the three is in the wrong place.
    
    **R1. Summary.** The first paragraph is one sentence on one source line, 72 characters or fewer, verb first, in the reader's words. It is also the row the parent's Commands table prints, so it stands alone: no mechanism, no parenthesis, no comparison with a sibling.
    
    **R2. Body.** Optional. 143 of the 225 commands have none and most need none. A sentence earns its place if a reader who has never seen the source would type something different, or read the output differently, for having read it. That admits a default that surprises, what is written or destroyed and whether it can be undone, when the command refuses and the way out, the one sibling it gets confused with, and one example where the shape of the invocation is not obvious. Order is the test, length is the tripwire: the first three lines after the summary answer the commonest question, and a body past 10 source lines needs a reason a reviewer accepts. "The contract has nowhere else to live" is not one. A 53-line screen is not itself the defect; a short body that buries the answer fails where a long one that leads with it can pass.
    
    **R3. Never in help.** Why the implementation is built as it is. A defence of the design against an alternative. The name of a function, class, module, package path or internal type. History ("legacy", "the old", "today there is no"). An invariant the reader cannot observe. Its home is a comment at the code it explains, or the docstring of the helper or module that implements it. If it must stay in the command function's own docstring it goes after a form feed (`\f`), which Typer does not render. If a caller depends on it, it is contract and not reasoning, and goes to `docs/` (R6, R7).
    
    **R4. Options and arguments.** Every one has a description. One line: what the value is and what it does here, with where the legal values come from (`see sq workflow ref-kinds`) or their format (`CODE=VALUE`). It never restates what the panel already prints (the default, required). A flag is described once, in the panel; the body adds only how flags combine. The same flag with the same meaning has the same words on every command, from one shared definition.
    
    **R5. `--json`.** Described on every command that takes it: one line naming the top-level shape. Not a blank by convention. A blank cell cannot be told from an omission, and the cell is the cheapest place to declare anything.
    
    **R6. JSON field reference.** Lives in `docs/stability.md`, beside the freeze it documents. Help keeps the R5 line, any sentence a caller needs in order not to misuse the payload, and a pointer. Where the docs do not yet carry a shape, the reference leaves help in the same change that lands it in the docs, not before.
    
    **R7. Exit codes.** A command with no code of its own says nothing. A command with one says one line and points at the table: `Exit codes: 0 clean, 3 error-level issues found. See sq docs faq.` The mechanics live with the table. One exception stays in help, briefly: a code that is non-zero although the work was applied.
    
    **R8. Markup.** Plain text, single backticks around anything typed literally. No doubled backticks, no asterisks, no `::`, no cross-reference roles. Angle brackets for a placeholder, a bar between alternatives. No square brackets around a lowercase word while the renderer is Rich.
    
    **R9. Layout.** Body paragraphs wrap at 78 columns after dedent. Anything that depends on its line structure goes in a no-rewrap block (`\b`) and stays under 78. No unbreakable enumeration longer than the description column.
    
    | Content | Home |
    |---|---|
    | What it does, what to type, what comes back or is lost | help |
    | Why the code is this way | a comment, or the helper's or module's docstring |
    | Field lists, exit-code mechanics, anything a script depends on | `docs/`, pointed at from help |
    
    **Holding a change to it.** Render the command at 80 columns and read the screen, not the diff. Does the first screen answer the three questions? Is any name on it something an adopter cannot type or open? Is every cell of the panel filled?
- [2026-10-09T15:44:10Z] Paul Reviewer:
  - Verdict: **ChangesRequested**. Eleven findings, two of them high. The rule the scope asked for is the comment above this one; the findings cite it as R1 to R9.
    
    **How it was read.** The dev tree's live command tree, walked in-process and rendered at 80 and 100 columns (550 command records), with a sample checked line for line against `sq <command> --help` run for real. The 109 distinct rendered help screens behind the 225 canonical leaves were read, per-type duplicates taken as one, along with every non-item group screen and a sample of the per-type ones. Each claim in a finding is marked driven, read or inferred. Nothing under `src/`, `tests/` or `docs/` was touched.
    
    **Ranked.**
    
    1. F2, high: one in four descriptions is blank (186 of 741 rendered, about 66 declarations). The largest reach and the cheapest fix per site; `--json` is settled here, described everywhere.
    2. F1, high: maintainer reasoning and private names in the reader's slot. `sq check` first: 23 of its 32 lines.
    3. F3, medium: JSON field reference filling 13 help bodies. Nine can shrink now; `search`, `tree`, `graph` and `workflow ref-kinds` are the only place their fields are written, so their trim is tied to a docs change.
    4. F5, medium: exit-code prose in 11 commands, three forms, five copies of the exit-4 contract. Pointer form is the standard.
    5. F4, medium: 43 of 44 multi-paragraph bodies render ragged at 80 columns; two enumerations are cut off, one of them asserted by a test as expected output.
    6. F7, medium: five markup dialects printed verbatim. Single backticks decided. The renderer is a question for op-pierre, below.
    7. F6, medium: a per-item verb's help will not open without a real item of that type, and not at all before `sq init`. Behaviour, not wording.
    8. F8, F9, F10, low: same flag in different words, summaries that name the mechanism, flags described twice. They fall out of the edits for F1 to F4 if done in the same pass.
    9. F11, low: nothing holds a change to the rule. The guard lands last, assertion by assertion.
    
    **How the fix splits (inferred, rough).**
    
    - *Tech writer, wording.* About 25 help bodies to rewrite (the 18 long ones, the four short exit-4 listings, a few more), about 30 summaries, about 45 distinct flag descriptions. One deliverable: the strings, written against the rule and checked on a rendered screen. Roughly a day to a day and a half, and it wants the stronger model.
    - *Developer, placement.* Put the strings in (`help=` on about 66 declarations, shared definitions in `_cli/_common.py`), move the reasoning F1 lists to comments and helper docstrings, re-wrap to 78 and add the no-rewrap blocks, fix the two cut-off enumerations and the two tests that pin one, fix the article and kind-name templates and the usage placeholders, add the walk test. Mostly `_cli/_main.py`, `_items.py`, `_workflow_cmd.py`, `_override.py`, `_role.py`, `_skill.py`. Roughly a day and a half to two days, including the tests that assert on help strings. One task with a subtask per finding fits; the writer's strings come first.
    - *Outside that task.* F6 is a behaviour change and wants its own item. F3 and F5 each need a docs change before or with the trim: the field reference for `search`, `tree`, `graph` and `workflow ref-kinds` into `docs/stability.md`, and `sq import` named on the exit-code table's row for 3. Roughly half a day of writing.
    
    **Question for op-pierre (F7).** Help renders through Rich console markup today because that is the installed Typer's default, not because anyone chose it: square brackets are interpreted and backticks are not. Markdown mode would render the backticks, re-flow paragraphs (which removes most of F4's first variant) and make brackets safe, at the cost of moving the tests that assert on help text (the three modes driven with a probe command; the test cost inferred). The dialect in R8 is right under either, so the wording work does not wait on the answer.
    
    **The scope's measurements.**
    
    - Held: 456 leaves with aliases; 18 bodies of ten lines or more, the same eight on top with the same line counts; median one line, 143 one-liners; the rendered heights at 100 columns to within a line, `role catalog` excepted (34, not 31); 31 double-backtick bodies, 3 bold, 2 literal-block markers, 4 cross-reference roles.
    - Off: "239 canonical leaves" counts 14 hidden `sq create <alias>` commands; the canonical figure is 225, and those 14 are the "14 with no body at all", so no canonical command lacks one. "94 groups" includes the alias groups; 47 are canonical.
    - Off: "215 described, 72 not, 33 of them `--json`" counts declarations in source. As rendered it is 555 described and 186 blank, and `--json` is 91 sites of which 12 are described, so it is not undescribed everywhere.
    - Off: eleven commands carry exit-code prose, not eight; `memory list`, `memory search` and `workflow lint` were missed.
    - Off: "the app sets no markup mode, so none of this is interpreted". It sets none, and the default interprets square brackets. The bracket hazard is on this side of the renderer choice, not the other.
    - Not in the scope at all: the ragged wrap at 80 columns, the cut-off enumerations, emphasis asterisks in six bodies, and F6.
    
    **Judged and left alone.** `--priority` enumerating on the item verbs and not on `list` and `tree` is correct and is information (F8 records why). No position is taken on the designs whose rationale F1 moves; that belongs to the structural review.
    
    @manager REV-958 is at ChangesRequested with F1 to F11 open. Routing is yours: a writer pass for the strings, a python-dev task to land them, a separate item for F6 if you want it acted on, and the renderer question for op-pierre. `sq check` is clean for this review.
<!-- sq:discussion:end -->
