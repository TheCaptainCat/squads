---
id: REV-958
sequence_id: 958
type: review
title: 'The --help surface: what belongs in a command''s help text'
status: Requested
author: tech-writer
refs:
- MILE-934:targets
- REV-956
description: A read of every rendered --help body and flag description, settling what
  help text is for versus a module docstring or docs/.
created_at: '2026-09-15T10:12:29Z'
updated_at: '2026-09-15T10:13:23Z'
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
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-15T10:13:23Z] Theo Writer:
  - Scoped by driving the live command tree rather than reading the source, because most of the item-type surface is generated per type and a source-only read undercounts it badly: 107 written command functions, 239 canonical leaf commands rendered (456 with aliases). Sampled at HEAD via an exported copy, since a dev is mid-edit in this tree.
    
    What the sampling changed about the framing. The surface is not long — median help body is one line, and 143 of 239 leaves are one-liners. Eighteen leaves carry ten lines or more, and that 7.5% is the whole of what provoked this. The other end is the larger problem by count: 72 options and arguments have no description at all against 215 that do, including `--type`, `--status`, `--parent`, `--assignee` and `--title`. `sq search` has both faults at once — a 28-line body about the JSON envelope above three flags with nothing said about them. So the item scopes two opposite failures at the two ends of one surface, not one.
    
    Two things worth knowing before the pass runs. `docs/stability.md` names `search`, `graph` and `tree` in the frozen `--json` set but does not enumerate their fields — the help text is currently the only place those are written down, so moving them out is not free and the item says so rather than assuming the docs already carry it. And the exit-code paragraph is hand-written in eight commands in two different forms, five of which are being rewritten right now for the fifth code; `sq check`'s "see `sq docs faq` for the full table" is the in-tree precedent, and settling the form before that divergence sets is cheaper than after.
    
    Deliberately not in it: no findings (nothing to find until the pass runs), no docs rewrite, no CLI redesign, no flag or behaviour change, and no position on the designs whose rationale sits in `check`'s and `role catalog`'s help bodies — that is REV-956's ground, and the item draws the line explicitly so the two do not collide.
    
    @manager — REV-958 authored, targeting MILE-934, related to REV-956, left in its initial status. `sq check` clean. Two things to route: it trips the same advisory REV-956 did (author `tech-writer`, lane expects `reviewer`), so the same decision applies about who runs it; and MILE-934's own "does not belong here" line excludes docs sweeps with no adopter-visible effect — this is adopter-visible text rather than a docs sweep, but the targets ref is yours to confirm. TASK-946 (docs for the 0.15 memory/board read views) is adjacent and separate; nothing here overlaps it.
<!-- sq:discussion:end -->
