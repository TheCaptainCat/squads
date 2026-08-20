---
id: TASK-719
sequence_id: 719
type: task
title: Document the shadowing override grammar for adopters
status: Done
parent: FEAT-713
author: tech-lead
assignee: tech-writer
priority: medium
refs:
- ADR-696:implements
- EPIC-538
- TASK-718:depends-on
description: Adopter docs for deep-merge, splat-refs and selected; rewrite the additive-only
  contract
subentities:
- local_id: ST1
  title: Override grammar reference in the overrides guide
  status: Done
  story: US1
- local_id: ST2
  title: Rewrite the published override stability contract
  status: Done
  story: US2
- local_id: ST3
  title: Drop and rename behaviour, plus the changelog entry
  status: Done
  story: US3
created_at: '2026-07-31T13:37:32Z'
updated_at: '2026-08-03T07:45:59Z'
---
<!-- sq:body -->
## What to write

The shadowing workflow override is the first adopter-visible piece of the customization work,
so the adopter-facing documentation of the override grammar lands with it. Two published
statements about overrides become **wrong** the moment shadowing ships, and one grammar is
entirely undocumented today.

This is documentation only — no code, no tests, no spec changes. Read the implementation and
the governing decision before writing; do not describe intended behaviour you have not
verified against the code that shipped.

## 1. The grammar, in `docs/overrides.md`

`docs/overrides.md` already documents the workflow override's sections (items, statuses,
lifecycles, collections, status roles) and the drift/reconciliation workflow. It documents them
as **additive-only**. Rewrite that framing and add the three mechanisms an adopter now has:

- **Deep merge.** An override supplies only the fields it changes; everything else inherits
  from the bundled entry. Tables recurse per key; a leaf value replaces its counterpart. Show
  the one realistic case: re-prefix or relabel a built-in type by declaring a single field.
- **Plain arrays are leaves.** An array in an override replaces the bundled array wholesale —
  no element is silently unioned in. Say why: a unioned list is a value nobody declared and
  nobody can read back from the TOML.
- **Splat-refs**, the eval-free way to append to a bundled list without restating (and thereby
  freezing) it. `$(path)` splices the bundled value at that path in as one element; `$(*path)`
  spreads a bundled list's elements into the surrounding list, which is what makes
  `["$(*self)", <new>]` mean "append". `$(self)` / `$(*self)` addresses the key currently being
  written; dotted paths address keyed tables elsewhere. Resolution is against the bundled base
  only, so the merge is order-independent and there are no cycles. A splat only ever adds.
  Say what a path is made of and what `self` means, because both are guessed wrong: a path
  addresses bundled keys by their names as TOML writes them unquoted, so a hyphenated or
  digit-leading key needs nothing special, and `self` is the key currently being written — at any
  list depth, since a list position has no name to contribute.
  Document the two forms that trip people up: a splatted array of tables must use TOML's
  **inline-array** form (`roles = ["$(*self)", { … }]`) because the `[[…]]` header form has no
  slot for a token; and a token is recognised only when it is the entire string value.
- **Where the splat sigil does and does not apply**, because an adopter will otherwise assume
  they must escape their own shell snippets. Only a value that *begins* with `$(` is read as a
  token; a value that merely contains `$(` anywhere after its first character is ordinary data,
  left verbatim and needing no escaping — which is why a command line such as
  `git commit -m "$(cat msg)"` passes through untouched. `$$(` escapes a value that must
  literally begin `$(`, and that is the only position where escaping is ever needed. There is no
  interpolation: `"text $(items.task.prefix)"` is the literal text. And the grammar applies to
  values only — a key is never resolved or unescaped.
- **`selected`**, the way to shrink. One top-level `[selected]` table with one key per section
  (`items`, `statuses`, `lifecycles`, `collections`, `subentity_kinds`, `roles`), each listing
  the **surviving** set, not the removed one. Show a worked drop.
- **What still refuses**, stated as a short, honest list rather than buried: the three roster
  type keys must exist, and a type's `category` cannot move into or out of `roster`. Everything
  else is ordinary vocabulary.
- **The new ways an override can be wrong**, because they are the adopter's real cost: a
  dangling splat path, a malformed token, an unrecognised top-level key (a mistyped section name
  is the common one), a shadowed lifecycle that fails the load-time floor, and a drop that
  strands live items. All are load-time and collected — point at `sq workflow lint` as the
  instrument that reports every one at once, and say plainly that a bad override is a hard stop
  until it is fixed.
- **Reading an override now requires knowing the bundled base it composes against.** Say so.
  The file stopped being purely declarative when splat-refs arrived, and `sq workflow lint`
  plus the type catalog — not hand-reading the file — are the honest answer to "what types do
  I actually have".
- **`override_base` / the drift stamp** for a shadowing override: a shadowed built-in stops
  tracking the bundled spec, so the stamp exists to make that drift visible instead of silent.
  Fold this into the existing staleness/reconciliation section rather than starting a second
  one; match whichever carrier actually shipped.

## 2. The stability contract, in `docs/stability.md`

`docs/stability.md` freezes "workflow overrides are **additive-only**" as part of the 1.0
override contract, and elsewhere presents a fixed reserved-status set. Both statements are
wrong once shadowing lands. Rewrite them to what the contract actually is now: overrides may
shadow a built-in under validation; the reserved surface is the three roster type **keys** and
their fixed `category`; **no status name is reserved** — a project may name its lifecycle
states anything, in any language.

`docs/stability.md` is a downstream summary of the decision set, not an independent authority.
Where the two disagree, the decision wins and the doc is what changes. If you find a third
place stating the old contract (`docs/adoption.md`, `docs/workflow.md`, `docs/faq.md`, the
`sq override scaffold workflow` starter comment, a command's `--help`), fix it in the same
pass — a contract stated twice goes stale once.

## 3. CHANGELOG

Add the entry to the unreleased section as this lands, not batched at release time. Adopter
language: what an adopter can now do that they could not before, and the two costs (a
shadowed built-in stops tracking the bundled spec; a bad override is a load-time hard stop).

A **Fixed** entry is required alongside it, in its own right: an unrecognised top-level key in
an override document used to be silently ignored, so a mistyped section name — `[item.task]` for
`[items.task]` — meant the whole override did nothing, with no error and no effect; it is now
refused with a message naming the key. Adopters have been hitting this, so it must be stated as
a fix and not left to ship as an unmentioned side effect of the new grammar.

## Conventions

- **Adopter-facing docs describe the tool for people adopting it.** No `sq` item IDs, no
  decision/feature/task references, no GitHub links, and no repo-process content (CI gates,
  test internals, packaging, how the team works). If a rationale only makes sense by citing
  an internal artefact, restate the rationale in the adopter's terms or leave it out.
- No build-process narration anywhere in the text: no phases, rounds, waves, increments, "this
  pass", "previously", or references to who implemented what.
- No status or lifecycle prose about the docs themselves.
- Every command, flag, and TOML snippet must be **run or read against the shipped code** before
  it goes in the page. A worked example that does not parse is worse than no example.
- Match the voice and structure of the surrounding pages: task-first headings, short worked
  snippets, the TL;DR-then-detail shape `docs/overrides.md` already uses.
- `sq check` clean before handing back.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 719 add-subtask "<title>"`; track with `sq task 719 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Override grammar reference in the overrides guide | US1 |
| ST2 | Done |  | Rewrite the published override stability contract | US2 |
| ST3 | Done |  | Drop and rename behaviour, plus the changelog entry | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Override grammar reference in the overrides guide

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a spec author, I want to shadow a built-in status/lifecycle/type via override instead of only adding new ones
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
The grammar reference in `docs/overrides.md`.

That page already documents the workflow override's sections and its drift/reconciliation
workflow, framed as additive-only. Rewrite the framing and document the three mechanisms an
adopter now has, each with a worked snippet that has been parsed against the shipped code:

- **Deep merge** — declare only the fields you change; tables recurse per key, a leaf value
  replaces its counterpart. Lead with the realistic case: re-prefix or relabel a built-in type
  in one field.
- **Plain arrays are leaves** — an override array replaces the bundled array wholesale, with no
  element silently unioned in. Say why: a unioned list is a value nobody declared and nobody can
  read back from the file.
- **Splat-refs** — `$(path)` splices the bundled value at that path in as one element; `$(*path)`
  spreads a bundled list's elements into the surrounding list, which is what makes
  `["$(*self)", <new>]` mean append. `$(self)` / `$(*self)` addresses the key being written;
  dotted paths address keyed tables elsewhere. Resolution is against the bundled base only, so
  the merge is order-independent with no cycles; a splat only ever adds. Say what a path is made of
  and what `self` means, since both are guessed wrong: a path addresses bundled keys by their names
  as TOML writes them unquoted, so a hyphenated or digit-leading key needs nothing special, and
  `self` is the key currently being written — at any list depth, a list position having no name to
  contribute.
  Cover the two forms that trip people up: a splatted array of tables must use TOML's
  inline-array form because the double-bracket header form has no slot for a token, and a token
  is recognised only when it is the entire string value.
- **Where the sigil applies, and where it is just text** — an adopter will otherwise assume they
  must escape their own shell snippets, and they do not. Only a value that *begins* with `$(` is
  read as a token; a value that merely contains `$(` after its first character is ordinary data,
  left verbatim, needing no escaping — so a command line such as `git commit -m "$(cat msg)"`
  passes through untouched. `$$(` escapes a value that must literally begin `$(`, the only
  position where escaping is ever needed. There is no interpolation: `"text $(items.task.prefix)"`
  is that literal text. The grammar applies to values only; a key is never resolved or unescaped.
- **`selected`** — one top-level table with a key per section, each listing the **surviving** set
  rather than the removed one. Show a worked drop.

Then the two things an adopter needs and will not infer:

- **What still refuses**, as a short honest list: the three roster type keys must exist, and a
  type's `category` cannot move into or out of `roster`. Everything else is ordinary vocabulary.
- **The new ways an override can be wrong** — a dangling splat path, a malformed token, an
  unrecognised top-level key (a mistyped section name being the common one), a shadowed lifecycle
  that fails the load-time floor, and a drop that strands live items. All load-time and
  collected; point at `sq workflow lint` as the instrument that reports every one at once, and
  say plainly that a bad override is a hard stop until it is fixed. Also say that reading an
  override now requires knowing the bundled base it composes against, and that `sq workflow lint`
  plus the type catalog — not hand-reading the file — are the honest answer to "what types do I
  actually have".

Fold the base-version stamp for a shadowing override into the page's existing staleness and
reconciliation section rather than starting a second one, and match whichever carrier actually
shipped.

Acceptance: every snippet on the page parses and every command runs as printed; a reader who
knows only the bundled spec can shadow a field, append to a bundled list, and drop a type using
only this page, and can tell from the page alone whether a value of theirs containing `$(` needs
escaping.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Rewrite the published override stability contract

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — Shadowed roster lifecycle validated against the R1/R1'/R2 floor
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
The published stability contract in `docs/stability.md`.

That page freezes "workflow overrides are **additive-only**" as part of the 1.0 override
contract, and elsewhere presents a fixed reserved-status set as part of the same contract. Both
statements become wrong when shadowing ships, and a wrong stability promise is worse than a
missing one.

Rewrite them to the contract as it actually stands: an override may **shadow** a built-in under
validation; the reserved surface is the three roster type **keys** and their fixed `category`;
**no status name is reserved** — a project may name its lifecycle states anything, in any
language, with any number of settled states. Keep the page's existing tier/table structure and
its voice; this is a correction inside the established shape, not a new section.

`docs/stability.md` is a downstream summary of the decision set, not an independent authority:
where the two disagree the decision wins and the doc is what changes. Read the decision text,
not a summary of it, before rewriting the clause.

If the old contract is stated in a third place — `docs/adoption.md`, `docs/workflow.md`,
`docs/faq.md`, the `sq override scaffold workflow` starter comment, a command's `--help` — fix it
in the same pass and list every location you touched. A contract stated in two places goes stale
in one of them.

Acceptance: no page, starter file, or help string still says the workflow override is
additive-only or that a status name is reserved; the reserved surface is described identically
everywhere it appears.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Drop and rename behaviour, plus the changelog entry

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US3 — Every consumer absorbs a dropped/renamed/re-prefixed type cleanly
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
What an adopter sees when a type is dropped, renamed, or re-prefixed — plus the changelog entry.

Document the observable consequences, because they are what an adopter meets in practice and
they are not inferable from the grammar:

- A dropped type stops appearing anywhere: no generated per-type skill, no folder, no prefix, no
  entry in `sq check`'s parent and sub-entity rules, no pointer-file mention.
- A renamed or re-prefixed type appears under its new name and prefix everywhere, with nothing
  left pointing at the old one.
- A drop that is **not** safe is refused, and the refusal names what still references the key —
  including when the adopter's own `selected` line is what removed it.
- Existing items carrying a type or status the override drops are the common first failure: the
  load refuses and lists the offending item IDs. Say what the remedy is (restore the key, or
  move the items) rather than only that it fails.

Then the changelog: add the entry to the unreleased section as this lands rather than batching it
at release time. Adopter language — what an adopter can now do that they could not before, and
the two real costs: a shadowed built-in stops tracking the bundled spec, and a bad override is a
load-time hard stop rather than a mid-command surprise.

One **Fixed** entry is required alongside it and must not be folded into the feature line: an
unrecognised top-level key in an override document used to be silently ignored, so a mistyped
section name — `[item.task]` written for `[items.task]` — meant the entire override did nothing,
with no error and no effect; it is now refused with a message naming the key. Adopters have been
hitting this, so it reads as a fix in its own right rather than an unmentioned side effect of the
new grammar.

Acceptance: the behaviour described matches a drop and a rename actually performed against the
shipped code; the changelog entry sits in the unreleased section and reads as adopter-facing
release notes, with no internal references; the silently-ignored-key behaviour appears under
Fixed, phrased so an adopter who hit it recognises their own symptom.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-31T14:40:42Z] Olivia Lead:
  - Body and ST3 now require a CHANGELOG Fixed entry of its own for the silently-ignored unrecognised top-level key — a mistyped section name meant the whole override did nothing, with no error and no effect (ADR-696 §4b). Adopters have hit it, so it must not read as a side effect of the new grammar.
  - Also carried §4a into the grammar page: only a value that BEGINS with the sigil is a token, one that merely contains it later is data needing no escaping (so a shell command line is inert), there is no interpolation, and the grammar is value-only. Without that the writer would document an escape duty that does not exist.
- [2026-07-31T14:54:57Z] Olivia Lead:
  - Added one line to the grammar reference per ADR-696 §4a: a splat path addresses bundled keys by their names as TOML writes them unquoted (so a hyphenated or digit-leading key needs nothing special), and self is the key currently being written at any list depth. Positive statement only — the unaddressable quoted-key case is a constraint on our own bundled documents, which an adopter cannot reach, so it owes no page space.
- [2026-07-31T15:57:20Z] Catherine Manager:
  - Adopter doc obligation, verified by driving the engine: a value that BEGINS with an unescaped $( is in token territory and is refused as malformed — so a shell command line starting with a substitution ($(which python) -m pytest) must be written $$(which python) -m pytest. A value containing the sigil later is data and needs nothing (echo $(date) and git commit -m "$(cat msg)" both merge byte-identical). The grammar reference must carry that distinction with a shell example; it is the case an adopter meets first and the only one where they must know the escape.
- [2026-07-31T16:09:50Z] Catherine Manager:
  - Second adopter doc obligation (REV-722 F14): a value cannot begin with a literal $$( in any position, because a leading $$( always unescapes to $(. Worth one line alongside the leading-sigil escape rule, since the two are the same paragraph for a reader.
- [2026-08-01T19:01:18Z] Theo Writer:
  - Docs written and verified by driving the engine in throwaway squads (never this repo): docs/overrides.md (new '## The override grammar: shadow, append, and drop' — deep merge, arrays as leaves, splat-refs, the leading-sigil rule with the shell example + the $$( corollary, [selected], the reserved surface, a failure table, and drop/rename consequences; plus workflow-override drift folded into Staleness and drift), docs/stability.md (override contract rewritten: shadowing grammar, reserved surface = three roster type keys + fixed category, no reserved status name, failure mode), docs/workflow.md, README.md, docs/README.md, CHANGELOG.md.
  - Line 78 was wrong in a second way the flag did not name: the workflow override is stamped too, and sq check reports an unstamped SHADOWING workflow override as an error (add-only needs no stamp, and it is not a load-time refusal). Both stamp forms now documented — HTML comment for templates, '# squads:override-base:' for role and workflow TOML.
  - Three pre-existing false claims found and fixed while verifying: (1) the collections reference in BOTH overrides.md and workflow.md required a 'default_code' field that does not exist — the model is label (required) / ordered (optional, default false) / default / badges, and a spec using default_code fails extra_forbidden; (2) 'sq task <n> update --impact medium' and 'sq list --min-impact high' do not exist — a custom badge field is set with --set code=value and filtered with --badge / --min-badge / --sort; (3) ordered collections rank by declaration order STRONGEST FIRST, and the documented impact example declared low-first, which inverts every --min- filter.
  - Two behaviours contradict ST3's expected drop semantics and are documented as they actually are, not as stated: a dropped built-in type keeps its top-level entry in 'sq --help' (the built-in command table is static; invoking it is refused), and 'sq sync' does not retire the folder or the generated sq-<type> skill left behind by a drop. Verified in a fresh squad too: 'sq init' scaffolds folders and seeds roster items from the BUNDLED spec, ignoring a workflow override present at init time — so 'choose your vocabulary at adoption' is not reachable through init for the roster today. Flagged rather than documented; @tech-lead may want a ticket.
  - @manager sq check clean; nothing committed; TASK-719 left InProgress, ST1-ST3 Done.
- [2026-08-01T19:27:34Z] Theo Writer:
  - Follow-up on docs/overrides.md only, re-verified against current src in a fresh throwaway squad.
  - Dropped-type help behaviour corrected. A dropped built-in is now hidden from the top-level command listing AND from 'sq create' — my earlier sentence claiming the listing entry stays is gone. Confirmed the implementer's nuance and stated it plainly: 'sq guide --help' typed explicitly still prints that group's usage (the group is in the built-in command table), while every verb under it is refused. Also improved since my first pass: 'sq guide 1 show' now returns the [selected] provenance message rather than the generic 'no spec supplied' one, so the doc's single quoted refusal covers both create and address.
  - Re-checked the other two flagged behaviours — both UNCHANGED. 'sq sync' still does not sweep a dropped type's folder or its orphaned sq-<type> skill (skill item still Active, .claude/skills/sq-guide and squads/guides/ both survive a sync). Also re-confirmed the positive half: a type added by an override still appears in both the top-level listing and 'sq create', and the roster groups are unaffected.
  - Meta guard: 'sq ticket <n>' rephrased — the alias example now reads as vocabulary ('ticket joins t and tk as a way to address one') instead of a runnable invocation, so it no longer presents as a live command. tests/meta/test_documented_commands_resolve_against_cli.py is 6 passed. Note for whoever fixes the bare-flag gap: the docs no longer contain a bare 'sq --help', so that guard path is currently unexercised — the fix will need its own case rather than relying on this page.
  - @manager docs/ only; src/ and tests/ untouched; sq check clean; nothing committed.
<!-- sq:discussion:end -->
