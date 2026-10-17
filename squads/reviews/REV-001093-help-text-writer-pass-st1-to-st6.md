---
id: REV-1093
sequence_id: 1093
type: review
title: 'Help text writer pass: ST1 to ST6'
status: ChangesRequested
author: reviewer
refs:
- TASK-1080
- REV-958
subentities:
- local_id: F1
  title: repair --renumber help claims refs are rewritten; exit line misses one exit-1
    cause
  status: Open
  severity: medium
- local_id: F2
  title: dev add --model help lists a closed set the command does not enforce
  status: Open
  severity: low
- local_id: F3
  title: repair exit-code line is 80 columns and renders with a one-word stub
  status: Open
  severity: low
- local_id: F4
  title: Rewritten remove help hardcodes bundled status names Archived and Cancelled
  status: Open
  severity: low
- local_id: F5
  title: CONTRIBUTING rule 6 drops R6's same-change clause for a new JSON shape
  status: Open
  severity: low
created_at: '2026-10-17T04:24:21Z'
updated_at: '2026-10-17T04:25:22Z'
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
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-17T04:25:21Z] Paul Reviewer:
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
<!-- sq:discussion:end -->
