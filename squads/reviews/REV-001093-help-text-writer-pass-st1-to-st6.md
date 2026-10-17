---
id: REV-1093
sequence_id: 1093
type: review
title: 'Help text writer pass: ST1 to ST6'
status: Approved
author: reviewer
refs:
- TASK-1080
- REV-958
subentities:
- local_id: F1
  title: repair --renumber help claims refs are rewritten; exit line misses one exit-1
    cause
  status: Fixed
  severity: medium
- local_id: F2
  title: dev add --model help lists a closed set the command does not enforce
  status: Fixed
  severity: low
- local_id: F3
  title: repair exit-code line is 80 columns and renders with a one-word stub
  status: Fixed
  severity: low
- local_id: F4
  title: Rewritten remove help hardcodes bundled status names Archived and Cancelled
  status: Fixed
  severity: low
- local_id: F5
  title: CONTRIBUTING rule 6 drops R6's same-change clause for a new JSON shape
  status: Fixed
  severity: low
- local_id: F6
  title: skill epilog verb list breaks mid-word at 80 columns; guard does not read
    epilogs
  status: Verified
  severity: low
- local_id: F7
  title: CONTRIBUTING rule 9 still prescribes the no-rewrap marker the code dropped
  status: Verified
  severity: low
- local_id: F8
  title: Generated article is wrong for names like user_story or unit
  status: Verified
  severity: low
- local_id: F9
  title: Shared-flag drift tests omit --all, --status, --parent and --pronouns
  status: Verified
  severity: low
created_at: '2026-10-17T04:24:21Z'
updated_at: '2026-10-17T05:11:47Z'
---
<!-- sq:body -->
## Scope

The writer half of TASK-1080 (ST1 to ST6), uncommitted against 48262185: `CONTRIBUTING.md`, `docs/stability.md`, `docs/faq.md`, help strings and docstrings in 15 files under `src/squads/_cli/`, and two tests that pinned rewritten wording.

## How it was read

- The diff, read line by line.
- Every rendered screen at 80 columns, from an in-process walk of the dev tree's command tree in a scratch squad with one item of each bundled type (244 command records), plus the addressed role, operator and skill verbs driven by hand. Per-type duplicates were read once.
- Claims driven against the live CLI: exit 3 (`check`, broken override), exit 1 (`workflow lint`, `repair --renumber`), exit 4 (`search`, `inbox`, unreadable file), the top-level `--json` shape named on 27 commands, `--author op-<slug>`, `--assignee` refusing an ID, `inbox` and `mine` taking an operator slug, retype's status rule (read in the service), `tree --depth`, graph's `(seen)` marker and edge labels.
- Docs rows checked against live payloads: search `hits[].hash`, graph `edge_kind` and `direction` (a `blocks` ref, a `depends-on` ref and a related ref, from each end), faq code 3 against the import command's exit path.
- The three touched help test modules: 76 passed.

## What holds

- No blank option or argument cell, no summary over 72 characters or wrapped, no parenthesis in a summary, no body over 10 lines by the CONTRIBUTING count, no doubled backtick, role or `::`, no private name, item id or history word in any rendered screen.
- The `\f` notes on `tree`, `role catalog`, `role list` and `role set-default` do not render.
- `check` keeps exactly the four lines the feature asks for; the five partial-result commands carry the architect's line verbatim; `import` keeps its two-line do-not-retry note.
- Docs: `hits[].hash` is emitted and documented in order; the graph `direction` and `edge_kind` rows match the payload from both ends of a dependency edge; faq code 3 matches the import exit path.
- CONTRIBUTING states the three questions, the content table, R1 to R9, the tripwire count and the 80-column review test, and its anchor resolves.

Findings below. The REV-958 mapping is in the verdict comment.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1093 add-finding "…" --severity medium`; track with `sq review 1093 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — repair --renumber help claims refs are rewritten; exit line misses one exit-1 cause

<!-- sq:finding:F1:body -->
**Shape.** `sq repair --help` promises reference rewriting that one collision case does not do, and its exit-code line names only one of the two causes of exit 1.

**Driven.** Scratch squad, a second file carrying `TASK-23` under a different slug, and `TASK-22` holding a `blocks` ref to `TASK-23`:

```
$ sq repair --renumber; echo $?
TASK-23: 2 files, different slugs
  kept       tasks/TASK-000023-gamma-widget.md
  renumbered tasks/TASK-000023-gamma-copy.md -> TASK-27 (...)
  references to TASK-23 left unchanged; check each by hand:
    tasks/TASK-000022-beta-widget.md   refs   TASK-23:blocks
1
```

**Against the help (rendered at 80 columns).**

- `--renumber`: "First give items that share a number after a merge fresh numbers, rewriting every reference to them." This holds for distinct IDs that share a number, not for one ID carried by two files: there, references are listed and left, as `docs/faq.md` says in bold ("References are not rewritten").
- Exit line: "Exit codes: 1 a file could not be read and kept its last entry." The command also exits 1 when references are left (`if result.unreadable or result.references_left` in the command). A script reading the help treats that exit 1 as an unreadable file.
- The faq exit-code table's row 1, edited in this pass, has the same gap: it names `sq repair` reporting an unreadable file and not the references left by `--renumber`. The faq's collision section does state it, so the table and the section disagree.

The wording was carried over, not introduced, but this pass rewrote both strings, and R4 and R7 require help to say what the command does.

**Fix.** `--renumber`: say that a shared ID's references are listed for checking by hand, not rewritten, for example "First renumber items that share a number after a merge; refs to a shared ID are listed, not rewritten." Exit line: name both causes in the one-line form. Faq row 1: add the `--renumber` case.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-17T04:28:15Z] `tech-writer` Theo Writer:
  - Fixed: --renumber now says refs to an ID that two files carry are listed for checking by hand, not rewritten; the exit line names both exit-1 causes; faq row 1 adds the --renumber case.
- [2026-10-17T05:03:28Z] `reviewer` Paul Reviewer:
  - Fixed in ea7977e7: --renumber now says refs to an ID two files carry are listed, not rewritten; the exit line names both causes; faq row 1 adds the --renumber case. Verified by reading the diff and rendering repair --help at 80 columns.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — dev add --model help lists a closed set the command does not enforce

<!-- sq:finding:F2:body -->
**Shape.** `sq dev add --model` reads "Model the agent runs on: `sonnet`, `opus` or `haiku`." That reads as a closed list, and the command neither enforces it nor lists everything the roster accepts.

**Driven.** `sq dev add --tech rust --model gpt` printed `added Elias Rust (rust-dev) ROLE-35` and exited 0.

**Read.** The role catalog loader's `VALID_MODELS` and the Claude Code frontmatter writer both accept `sonnet`, `opus`, `haiku` and `inherit`. The help omits `inherit`, and the dev command validates nothing.

**Fix.** Help text, this task: list what is accepted (`sonnet`, `opus`, `haiku` or `inherit`). Behaviour, not this task: `dev add` accepting any string, which the catalog path would refuse, is a bug for @qa to file, per the task's rule for help that meets wrong behaviour.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-17T04:28:16Z] `tech-writer` Theo Writer:
  - Fixed: --model reads "for example sonnet, opus, haiku or inherit". The missing validation is a separate bug for qa.
- [2026-10-17T05:03:30Z] `reviewer` Paul Reviewer:
  - Help text fixed in ea7977e7 (for example sonnet, opus, haiku or inherit). The dev add validation gap is still open as behaviour, for @qa to file as a bug.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — repair exit-code line is 80 columns and renders with a one-word stub

<!-- sq:finding:F3:body -->
**Shape.** A line this pass wrote breaks R9 and the CONTRIBUTING rule it added.

**Driven.** `sq repair`'s exit-code line is 80 characters after dedent, and renders at 80 columns as:

```
 Exit codes: 1 a file could not be read and kept its last entry. See sq docs
 faq.
```

It is the only writer-authored body line over 78 in the walk. The other over-78 lines, the comment group's three line-structured lines, are left to ST8 on purpose.

**Fix.** It goes away with the rewrite in the repair finding; keep the new line at 78 or under.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-17T04:28:17Z] `tech-writer` Theo Writer:
  - Fixed: the repair exit line is now 75 columns after dedent.
- [2026-10-17T05:03:32Z] `reviewer` Paul Reviewer:
  - Fixed in ea7977e7: the repair exit line is 69 columns and renders on one line.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Rewritten remove help hardcodes bundled status names Archived and Cancelled

<!-- sq:finding:F4:body -->
**Shape.** Two body sentences rewritten in this pass tell the reader to type a bundled status name. The engine reads these statuses from the active spec, and a project can rename or replace them.

- Role, operator and skill `remove`: "To keep it on record instead, set its status to `Archived`." (`register_remove_verb`, a new sentence in this pass).
- `<type> remove`: "set its status to `Cancelled` instead" on all nine types.

Under an override where the roster's retired status or a type's cancelled status has another name, both sentences name a status the transition refuses. R4 asks help to name where legal values come from, and the vocabulary-following help tests show the project already treats spec words in help as derived, not literal. The `list` body's `Accepted` and `Superseded` are introduced with "such as" and read as examples, so they are left alone.

**Fix.** Use the status's role rather than its bundled name: "set it to its retired status (see `sq workflow lifecycles`)" and "cancel it instead". Or derive the name from the active spec, as `--priority` does, which would be ST7's to place.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-17T04:28:18Z] `tech-writer` Theo Writer:
  - Fixed: both remove bodies name the status by what it does (the type's cancelled status, its archived status) and point at sq workflow lifecycles.
- [2026-10-17T05:03:34Z] `reviewer` Paul Reviewer:
  - Fixed in ea7977e7: both remove sentences now point at the archived or cancelled status via sq workflow lifecycles, with no literal name.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — CONTRIBUTING rule 6 drops R6's same-change clause for a new JSON shape

<!-- sq:finding:F5:body -->
**Shape.** CONTRIBUTING rule 6 drops the ordering clause of R6.

R6 (REV-958) and ADR-1025 §2 both say a `--json` field reference leaves help only in the same change that lands it in `docs/stability.md`, and that a new Tier 3 shape lands with its field reference in the docs. The new section's rule 6 says only where the reference lives and what help keeps. A contributor adding a command with a new `--json` shape would read rule 5 and rule 6, write the one-line `--json` description and the pointer, and land no field reference anywhere. That is the state REV-958 F3 found for `search`, `tree` and `graph`.

**Fix.** One sentence on rule 6: "A new `--json` shape lands its field reference in `docs/stability.md` in the same change."
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-17T04:28:19Z] `tech-writer` Theo Writer:
  - Fixed: CONTRIBUTING rule 6 now says a new --json shape lands its field reference in docs/stability.md in the same change.
- [2026-10-17T05:03:36Z] `reviewer` Paul Reviewer:
  - Fixed in ea7977e7: rule 6 now says a new --json shape lands its field reference in docs/stability.md in the same change.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — skill epilog verb list breaks mid-word at 80 columns; guard does not read epilogs

<!-- sq:finding:F6:body -->
**Shape.** The `sq skill` epilog's verb list is one unbreakable token wider than the screen, so it breaks mid-word at 80 columns. That breaks R9, and the guard cannot see it.

**Driven** (`COLUMNS=80 sq skill --help`, and the same through `tests/_help_tree.render_help`):

```
 Address a skill: sq skill <slug|id|n> VERB, where VERB is one of
 show|refs|link-role|unlink-role|regen|update|body|remove|comments|status|ref|c
 omment|view.
```

The role and operator lists fit today. Any added roster verb pushes them over the same way.

**Guard blind spot.** `tests/meta/test_every_help_screen_follows_the_help_rule.py` builds each screen's source from `command.help` only. An epilog is never measured, and the rendered check looks only for an ellipsis, so a mid-word wrap passes.

**Fix.** Join the verbs in `address_epilog` with a separator Rich can break at, such as `, ` or ` | `. Then extend the guard either to the epilog source or to any rendered line that ends inside a word.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-17T05:07:01Z] `python-dev` Elias Python:
  - Fixed: the epilog verb list joins with commas so it wraps; the guard now reads epilogs (an epilog word wider than the screen fails). Reverting the join turns 2 new tests red.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — CONTRIBUTING rule 9 still prescribes the no-rewrap marker the code dropped

<!-- sq:finding:F7:body -->
**Shape.** CONTRIBUTING rule 9 still tells a contributor to put line-structured text in a no-rewrap block (a `\b` line before it). In the installed Typer that prints a stray blank line, and the shipped help no longer uses it.

**Driven** with a probe command. A paragraph after the first keeps its authored line breaks without any marker. A `\b` before a later paragraph renders as two blank lines instead of one. The dev's handoff found the same, so the comment group, renumber and the epilogs use plain later paragraphs.

**Fix (ST11, CONTRIBUTING).** Rule 9 should say line-structured text goes in a paragraph after the first, under 78 columns, with no marker. Logged here so the rule does not ship contradicting the code; the dev already routed it to @tech-writer.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-17T05:07:36Z] `tech-writer` Theo Writer:
  - Fixed: CONTRIBUTING rule 9 now says later paragraphs keep their authored line breaks, line-structured text is a later paragraph with no marker (a backspace-b line prints a stray blank line), and an epilog line that must stand alone is its own paragraph.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Generated article is wrong for names like user_story or unit

<!-- sq:finding:F8:body -->
**Shape.** `common.article` chooses the article by first letter, and FEAT-1024 US8 asks for a correct article for any declared type name.

**Driven** in-process: `article("user_story")` and `article("unit")` return `an`, and `article("hour")` returns `a`. A project declaring `user_story` or `unit` gets "Create an user_story." and "Operate on an unit by number or ID." on its root listing and create menu. The bundled names and the guard's `investigation` fixture are all right.

**Fix.** Either pin the article in the type's labels and fall back to the heuristic, or word the two generated summaries so they need no article (for example "Create one `<type>` item." or "Work on `<type>` items by number or ID."). The second is simpler and holds for any name.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-17T05:07:03Z] `python-dev` Elias Python:
  - Fixed: article() decides on the spoken first sound (silent h, u/eu/one as a consonant sound) with a 16-row test table. Going back to first-letter turns 7 rows red.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Shared-flag drift tests omit --all, --status, --parent and --pronouns

<!-- sq:finding:F9:body -->
**Shape.** The ST7 drift tests leave out `--all`, which FEAT-1024 US5 names explicitly, along with `--status`, `--parent` and `--pronouns` from the ST4 table.

- `tests/meta/test_shared_flags_are_declared_once.py` `SHARED_FLAGS` has no `--all`, `--status`, `--parent`, `--label`, `--type`, `--pronouns` or `--force`. A new command can declare `typer.Option(False, "--all", help="Include done items.")` inline and both tests stay green. `--force` and `--all` carry several meanings (`refs --all` means both directions), which is why they cannot simply be added to the literal scan. That is also why the wording table must hold them.
- `tests/cli/test_shared_flags_read_the_same_everywhere_cli.py` `WORDINGS` covers `--force` but not `--all`, `--status`, `--parent` or `--pronouns`.

The shipped wording is right today (read and rendered: `list`, `tree`, `graph` and `mine` all read "Include closed items."). The gap is that nothing holds it.

**Fix.** Add `--all` (two meanings: "Include closed items." and "Show both directions."), `--status`, `--parent` and `--pronouns` to `WORDINGS`. Add `--all` to `SINGLE_MEANING` only if `refs` moves to its own factory.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-17T05:07:05Z] `python-dev` Elias Python:
  - Fixed: --all, --status, --parent and --pronouns are in the wording table, each with every meaning. Rewording any one turns 1 test red (3 runs).
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-17T04:25:21Z] `reviewer` Paul Reviewer:
  - Verdict: ChangesRequested. One medium and four low findings, all text the writer can fix in place. Everything else checked holds (see the body). The F2 validation gap is a bug for @qa, not part of this task.
    
    REV-958 mapping, for this pass:
    - F1 maintainer reasoning, private names: resolved (ST5). No private name, history word or item id renders; check keeps its four lines; the `\f` notes do not render.
    - F2 blank descriptions: text resolved (ST4), 0 blank in the walk. Declaring each shared flag once is still owed by ST7.
    - F3 JSON field reference: resolved (ST2). 13 bodies trimmed; `hits[].hash` added; graph rows corrected; help-as-authority sentence gone; ref-kinds row present.
    - F4 layout: partly. Writer bodies are at 78 or under except repair (F3 here), and summaries are one line of 72 or fewer. ST8 owes the comment group lines, the three epilogs, retype NEW-TYPE, reflog `--op` and the usage placeholders.
    - F5 exit codes: resolved (ST3), one form everywhere, faq row 3 names import. The repair line's missing cause is F1 here.
    - F6: out of scope, its own item.
    - F7 markup: writer text is single-backtick throughout, with no bracket tags. ST8 owes the mechanical pass over untouched strings: board post `--as` 'op-<slug>', `--sort` "(e.g. priority)", the `--badge` CODE=VALUE literals.
    - F8 same flag, different words: wordings unified at every site, `--all`, `--author` and `-m` corrected, hand-written defaults removed. ST7 owes the single definition and the `--as` "(required)".
    - F9 summaries: hand-written ones resolved (ST6). ST9 owes the generated ones ("Create a epic.", "a epic", sub-entity verbs, "Scaffold a").
    - F10 flags described twice: resolved (ST6).
    - F11 nothing holds the rule: CONTRIBUTING section done (ST1, plus F5 here). ST10 owes the guard.
    
    @tech-writer F1 to F5 are yours. Re-render repair and dev add at 80 columns after the fix.
- [2026-10-17T05:04:22Z] `reviewer` Paul Reviewer:
  - Second pass: the writer fixes (ea7977e7) and the uncommitted ST7 to ST10 code pass. Recommend **Approved**. F1 to F5 are Fixed. F6 to F9 are new and all low; none blocks.
    
    Checked:
    - **ST7.** Every shared flag comes from a factory or constant in `_cli/_common.py`. Wording was read across all 343 screens of the walk and is identical per meaning. `--as` keeps "(required)": the add sites (`comment`, `board post`) read "Author: a role slug or `op-<slug>` (required).", and comment edit and remove read "The comment's author (required)."; both are validated by hand, so this is consistent. The scanner's self-check catches a literal `--file` and passes `--title`. It cannot see an option built from `from typer import Option`, and none exists. Gaps in what it holds: F9.
    - **ST8.** At 80 columns the comment group, renumber, retype and reflog `--op` render as intended, with no ellipsis anywhere. The roster usage line is `sq role <slug|id|n> show`, and the addressed verbs still parse. The `\b` stray blank line is confirmed with a probe (F7). The skill epilog breaks mid-word (F6).
    - **ST9.** Bundled: "Create an epic.", "Operate on an epic by number or ID.", story, subtask and finding verbs in kind labels. Custom override (`investigation`/`analysis`, `incident`/`action`, `action_item`): "an investigation", "List this item's analyses.", "Scaffold an analysis", "Operate on an analysis by number or local ID." Article edge cases: F8.
    - **ST10.** `LONG_BODIES` is empty. The stale-entry and off-list unit test passes. Both walks run, the custom one asserting `sq investigation analysis`. Falsified in-process on the live tree: a blank `graph --depth` description and an 11-line `graph` body are each reported. The guard misses epilogs: F6.
    - **Extras.** `<kind> remove` names the mapping kind only for story ("A story that a subtask still maps to is refused"; subtask and finding say only that the id is never reused): correct. `LOCAL-ID` on every sub-entity verb: correct. Retype NEW-TYPE points at `sq workflow types` with no enumeration: correct, although its second sentence repeats the body.
    - **Tests.** 121 passed over the new and touched help tests.
    
    REV-958 recommendation. Close F1, F2, F3, F5, F8, F10 and F11 as Fixed, citing c05d4b11 and ea7977e7, plus the ST7 to ST10 commit when it lands. Close F4, F7 and F9 as Fixed with the same citations; F6, F7 and F8 here are follow-ups, not reopeners. F6 still has no item of its own: file one first (BUG-1042 is adjacent but different), then close F6 as WontFix pointing at it. Separately, BUG-1044 (create help understates `op-` slugs) is answered by the shipped `--author` and `--assignee` text and can be verified.
    
    @manager REV-1093 is at InReview; Approved is the main loop's to set. @python-dev F6, F8 and F9. @tech-writer F7 with ST11.
- [2026-10-17T05:04:37Z] `reviewer` Paul Reviewer:
  - Clarification on the REV-958 line above: all of REV-958 F1-F5 and F7-F11 close as Fixed with those citations; only REV-958 F6 waits on its own item. This review's F6-F9 are low follow-ups and do not reopen anything.
- [2026-10-17T05:11:47Z] `manager` Catherine Manager:
  - Approved: F1-F5 verified by the reviewer, F6-F9 fixed with falsified tests; full suite 13795 passed, 0 failed.
<!-- sq:discussion:end -->
