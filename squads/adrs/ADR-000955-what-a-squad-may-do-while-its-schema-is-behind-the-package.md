---
id: ADR-955
sequence_id: 955
type: decision
title: What a squad may do while its schema is behind the package
status: Accepted
author: architect
refs:
- REV-952:addresses
- TASK-954
- ADR-663
- ADR-76
description: 'The reconcile licence: vocabulary-blind, content-neutral, convergent
  — and why the reconcile lives inside migrate up rather than as an exemption for
  sq repair'
created_at: '2026-09-15T08:58:16Z'
updated_at: '2026-10-25T21:47:50Z'
---
<!-- sq:body -->
## The state

A squad's `.squads.toml` carries a `schema_version`. When it does not equal the installed
package's `SCHEMA_VERSION`, the schema gate (`require_current_schema` and `apply_gate`,
`_cli/_common.py`) refuses every command that has not declared it may run there (§4): behind the
package it says "run `sq migrate up`", ahead of it "upgrade the squads package".

When this was decided, several remedies printed in exactly that state named `sq repair`, a command
the gate refuses there: the store's skew-direction argument, the shared single-item skew refusal,
and a runner's abort messages. A remedy naming a refused command reads as an exit and is not one.
The obvious repair, exempting `repair` from the gate, is refused below, and the reason is the
substance of this record: what replaces it is a rule about **operations**, so the next migration
inherits the answer instead of re-deriving it.

## What the gate protects

Two distinct costs, which the single word "staleness" runs together:

1. **Answering a question with the wrong vocabulary.** A command that resolves a type, a status, a
   prefix, a folder, a ref kind, a view name or a badge off the installed spec, and applies that
   answer to a corpus written against an older one, reports something untrue. Nothing is damaged;
   the operator is misled.
2. **Writing a corpus under a vocabulary it was not written in.** A command that rewrites item
   content using the installed spec's answers makes the first hazard durable. The corpus stops
   being the thing the pending migration was written against, and the migration, the only code that
   knows how to carry it forward, no longer has its documented input.

## Why `sq repair` is not the exit

`sq repair` is a corpus-wide read-modify-write whose behaviour depends on the installed vocabulary:
it globs by the active spec's declared folder and prefix per type (and refuses the rebuild when the
corpus does not fit them); it threads the active spec's default ref kind into every
`Item.from_frontmatter`; it validates every item's type and status against the installed spec; it
writes (the canonical ref encoding, the retired-region strip, the body-tag convergence, the
retired-key removal); and it stamps the index at the installed schema. Its own docstring records an
ordering prohibition (a strip never runs ahead of a surface regeneration that reads what it
removes) that holds **by construction**, because `sq repair` only runs on a corpus at the current
schema, and the single call on a behind-schema corpus is the tail of `run_pending_migrations`,
after every runner. Exempting it would turn that proof into a convention.

## Ruled: the reconcile licence

An operation may run on a squad whose stamped schema is not the installed package's if and only if
all three clauses hold, for every input corpus:

1. **Vocabulary-blind.** Its behaviour is not a function of any spec-resolved value: the type set,
   the status set, a type's folder or prefix, the declared ref kinds and their default, the view
   set, the sub-entity kinds, the badge collections, the validator catalog. It reads the corpus
   *structurally* (bytes, filenames, marker shape, frontmatter keys), never *semantically*. Nothing
   declared is handed to it.
2. **Content-neutral.** It writes no item body and no frontmatter field value. The only squad
   artifacts it may write are derived and rebuildable in full from the markdown (the index and the
   reflog), stamped at the schema the corpus is stamped at, never at the installed one.
3. **Convergent.** It leaves the squad no further from a successful `sq migrate up` than it found
   it, and never makes a later migration's input differ from what that migration was written
   against.

Anything that fails clause 1 or clause 2 is a **migration step**, not a maintenance command: its
home is a versioned runner, where the schema it assumes is written down and the transition it
performs is reviewable. The question to ask of any future remedy is not "is this command safe" but
"does this operation hold the three clauses". `sq repair` does not hold the licence and is granted no
exemption in any form: not wholesale, not behind a flag, not in a "skip the sweeps" mode.

## Ruled: the reconcile is a routine of its own, run inside `migrate up`

**The structural scan is separable from the semantic sweep**, and the seam is not a flag on
`repair`. A `repair(sweeps=False)` would put two behaviours behind one verb, one of them correct only
in a state the other is never correct in. The licensed subset is a narrower routine of its own
(`_index/_reconcile.py`), with the licence as its contract:

- **Where it looks.** With a readable previous index, a file is the squad's item only where the
  index keeps items of its prefix: a *location* is the directory and file-name prefix of an
  entry's recorded path, matched literally, and nothing outside a location's directory is opened,
  indexed, reported, counted or written. With no readable previous index there are no locations,
  so the tree under the squad directory is walked and every file with an item's name (hyphen-joined
  segments of letters, digits and underscores, then the number) and a well-formed `id` is
  recognised.
- **What it owes each state of the index**, by "carry forward, never fabricate": with no readable
  previous index it builds from the files alone; it reads a previous index without vocabulary
  validation; a file's own frontmatter replaces its entry; a file with no entry gains one; an entry
  whose file is gone is dropped and named; a file it cannot index leaves its previous entry as it
  was.
- **What it reads.** Every schema this package can migrate from; the two oldest carry no
  `sequence_id`, which is read from the `id` (derivation, not fabrication).
- **What it never does.** No legacy-kind fold and no canonicalisation, no vocabulary validation and
  no refusal on vocabulary grounds, no strip, no convergence, no retired-key removal. It stamps the
  rebuilt index at the corpus's own `schema_version`. It refuses nothing and writes no markdown file;
  the caller decides whether the built index is kept.

**`sq migrate up` runs it unconditionally as its first step**, with no test of whether the index
looks stale, on every invocation that has a runner to apply. It does not run on a squad at the
current schema, where `sq migrate up` writes nothing and `sq repair` is the reconcile; nor on a squad
ahead of the package. The trailing `repair()` call stays where it is, after every runner, as the
corpus sweep and the rebuild on a corpus that is by then current. Each runner commits its own
transaction, so an interrupted chain leaves the index partly advanced and the markdown ahead; the
next `sq migrate up` reconciles first, so "re-run `sq migrate up`" is a true remedy. The reconcile
makes a re-run possible; it does not make a runner idempotent, which stays an obligation on every
runner.

**Before the first runner, in this order, every refusal that can be known in advance is made**, and
only the index has been written:

1. **The vocabulary resolves.** `sq migrate up` runs under the squad's declared vocabulary or not at
   all: the workflow override, and every other document a pending runner loads, resolve once before
   the first write, with no bundled-spec fallback (the last fallback of the bypass accessor suits
   `sq repair` at the current schema and is refused here). An override that does not load stops the
   run, naming the file and the loader's cause, with one remedy: correct the file, then re-run
   `sq migrate up`. Every step that validates against vocabulary uses that one resolution: the
   checks below, each runner's own access to the index, and the trailing repair. `sq migrate up`
   builds its service through the accessor that skips the index cross-check
   (`get_service_bypassing_index_cross_check(bundled_fallback=False)`), because an exemption that
   the command's own construction can veto is not an exemption.
2. **The reconcile runs.**
3. **Every item file has an entry of its own.** If a file at a location (or, with no index,
   recognised by the walk) cannot be given an entry (bytes that do not decode, frontmatter that does
   not parse, no usable `id`, an id two files carry, a number two different ids share), the run
   stops and names each file with what is wrong. The entry it had is carried forward. The remedy is
   outside `sq`: correct the file, or, when it is not one of the squad's items, move it out of the
   folder it sits in. For a number two ids share, the cause names the number, both ids, both paths,
   and that the index holds one item per number; the remedy is a renumber by hand, with its parts
   (a number above the counter, which it prints, then the file name, `id`, `sequence_id` and the
   references that name the old id), and it may say that the release the squad is stamped for can
   renumber it, without printing that release's command as one to run here. No renumber is reachable
   behind the gate: `sq repair --renumber` is `repair`, and `sq renumber` rewrites ids across files.
   Once a stamp is written no runner runs again, so a file passed over would keep its old shape in a
   squad every command treats as current.
4. **The reconciled corpus fits the resolved vocabulary** (`_services/_corpus_fit.py`). The check
   holds the vocabulary the reconcile was denied, and asks: does every indexed file sit where a
   declared type lives; does every file named for an item where a declared type lives (matched by
   each declared prefix exactly as declared) have an entry; and does every item's type, status,
   prefix, folder and badge code fit the declared vocabulary. It refuses only what the completed
   run would refuse: no shipped runner renames or retires a type, a status, a prefix, a folder or a
   badge code, and the first runner that does declares the names it consumes on its migration
   record, so the check is blind to them. Its remedies: restore the declaration in the override,
   correct the named frontmatter by hand, or move a stray file out of the folder, then re-run
   `sq migrate up`. With an index, the first item of a type left unindexed in a folder the index
   does not know is refused here, and the remedy names the stamped release's index rebuild. It does
   not retire the trailing refusals: what cannot be seen before the runners is still refused after
   them.

**With no readable previous index, a run refused before its first runner leaves no index behind**,
or leaves the unparseable one untouched. An index built from a tree walk and kept would make every
stray's directory a location for the next run and carry its number into the counter. The refusal
says why: there was no readable index, so every item-shaped file under the squad directory was taken
for an item, and these sit where no type of this squad lives. The remedy restores the first state:
restore the index, from version control or with the index rebuild of the release the squad is
stamped for, and re-run; or move the files out of the squad directory.

**The invariants.** A run that reaches its first runner is never refused by the trailing `repair`
for where a file sits, and no file that was on disk before the run reaches the trailing `repair`'s
unreadable report: when both questions of check 4 hold, the index the runners read is the corpus the
trailing `repair` will scan. One known limit: a copy of an item under a name that is not an item's,
in a declared folder the index has never held an item in, is seen by neither question and is left to
`repair`'s report after the stamp; no item is passed over by it.

## Ruled: the gate grants by command, on a declared ground

The gate keys on the command, and the exemption is a **declared capability on the command**
(`past_the_gate(ground, behind=..., ahead=...)`), which the root callback and the `sq migrate` and
`sq override` group callbacks consult through one refusal with the same two messages. A
`tests/meta` guard binds the set that gets past the gate to the set that declares a grant, and a
command added under one of those groups without a declaration is refused. Never a second literal
appended to a tuple: a name in a tuple is a claim with no home for its justification.

A command gets past on one of three grounds, each with its own directions:

- **It is the migration** (behind only): `sq migrate up`. On a squad ahead of the package the gate
  refuses `up` itself, before a service is built, so the answer is "upgrade the squads package",
  never an override refusal: this package can neither round-trip a corpus written against a schema
  it has no model for (clause 2) nor converge toward it (clause 3).
- **It touches no corpus state** (both directions, unless stated): `sq migrate help` and
  `sq migrate chlog`, which read the package's own registry; `--help`; and, behind only,
  `sq override list`, `sq override diff` and `sq override update`, which read the bundled documents
  and read or re-stamp files under `.overrides/`, never an item file or the index.
- **It holds the reconcile licence.** No command does: the reconcile is a routine.

Everything else is refused in both directions, `sq repair` included, and `sq migrate repad`,
`sq migrate rename-type` and `sq migrate rename-status` among them: each assumes the installed
vocabulary without writing it down, and each rewrites the corpus (repad ends in the full `repair()`
sweep). An adopter whose squad is behind migrates first and then runs them; where `migrate up` is
refused because the corpus uses vocabulary the override has dropped, they restore the declaration,
migrate, rename at the current schema, then drop it. Ahead, they upgrade the package. A squad that
has to be repadded or renamed without being migrated is handled with the squads version it is
stamped for.

## Ruled: what a remedy may name

**A message may only name a command that is permitted in the state the message fires in.** Its
subject is a **remedy**: what an operator is told to run to leave the state they are in, where the
state is the one the run leaves them in. A run that completes leaves a current squad, so its report
may name any command; a runner's `MANUAL` runbook and its docstring describe steps taken after that
and are outside the rule. A shared message stays worded for its ordinary callers; where the state is
known, `migrate up` composes the remedy, and a runner that reports a skew composes its own clause
instead of inheriting the write seam's.

Two tests carry the rule:

- **Behavioural, and the one that binds.** Over a table of `sq migrate up` runs that end with the
  schema stamp unchanged, every `sq` command the output names is one the gate lets past in that
  state. The permitted set is read from the declared grants, not written into the test.
- **Static, and narrower.** In a runner module no string that can leave through a `raise` names a
  refused command, and no runner imports the write seam's skew guard or its message.

The store's skew-direction docstring states both halves: markdown-ahead heals losslessly through
`sq repair` at the current schema, and through `migrate up`'s reconcile while the schema is behind.

## What this does not settle

- **Reconciling a behind-schema squad deliberately, without migrating.** There is no verb for it;
  the answer is to migrate. If a case appears where that is wrong, it arrives as a command declaring
  the licence ground, not as a flag on `migrate up`.
- **A corpus that is behind and also cannot be migrated** because a runner refuses for a reason no
  reconcile addresses. The reconcile removes the partial-pass dead end; it does not promise every
  behind-schema squad a path forward. The messaging rule is what makes such a wall legible.
- **Whether the licence also governs reads.** A purely structural read behind the gate would hold
  all three clauses trivially; no such command is proposed.
- **A load-time grammar for a type's prefix.** The workflow spec gives a prefix no grammar beyond
  uniqueness, so no name pattern covers every squad; the invariants above do not rest on one. Whether
  a spec should refuse such a prefix at load belongs with what a spec must satisfy (ADR-696).

## Consequences

- On a squad whose schema differs from the package's, only the commands that declare a grant run:
  `migrate up` (behind), `migrate help`, `migrate chlog` and `--help` (both), and `override list`,
  `diff` and `update` (behind).
- On a behind squad every refusal that can be known in advance precedes the first runner, and only
  the index is written before it.
- `sq migrate up` never stamps past an item file it cannot index.
- A run that leaves the squad behind names, as remedies, only commands the gate lets past and
  actions outside `sq`.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-15T09:17:00Z] `op-pierre` Pierre Chat:
  - Accepted. The reconcile licence stands as ruled: vocabulary-blind, content-neutral, convergent,
    with sq repair unexempted and the licensed reconcile running as migrate up's own pre-pass.
- [2026-10-09T19:36:36Z] `architect` Robert Architect:
  - 2026-10-09: amended in place, on the operator's direction recorded on TASK-954. Thirteen dated notes at the passages concerned and a closing **Amendments** section (A1 to A7). The diff against HEAD is additions only in the body; `related` refs to ADR-663 and ADR-76 added; status untouched.
    
    **Amendment, not a new decision.** Every ruling's headline survives: the licence, no exemption for `sq repair`, the pre-pass inside `migrate up`, the remedy rule. What moved is two stale premises, the reach of one ruling, and obligations derived from the record's own clauses. A superseding decision would restate the licence to change nothing in it, and a supersedes edge for clause-level corrections is what board notice 7 rules out.
    
    **What changed**
    - A1: the exemption is per command. `migrate up` when the squad is behind; `migrate help`, `migrate chlog` and `--help` in both directions; `repad`, `rename-type` and `rename-status` refused in both. Each of the three fails the licence, and `repad` ends in the full `repair()` sweep on a behind squad, which `repair`'s own docstring says cannot happen.
    - A2: the pre-pass is needed for states of the index (missing, corrupt, a stale entry, a file with no entry), not for the `ensure_no_skew` premise, which the code no longer has. Item files are recognised structurally, and the two oldest schemas carry no `sequence_id`.
    - A3: "unconditional" means whenever a runner applies, with no staleness test. A current squad stays a no-op.
    - A4: when an item file cannot be given an index entry of its own, the run stops before the first runner instead of stamping past it.
    - A5: no bundled-spec fallback for `migrate up`, and one vocabulary resolution used by every step, each runner's index access included.
    - A6: a vocabulary conflict is refused on the reconciled index before the first runner, bounded to what the completed run would refuse anyway.
    - A7: the remedy rule's scope, its live sites, and two tests in place of the one that fails on legitimate text (64 mentions by the tech lead's count, 95 by a wider pattern of mine).
    
    **For op-pierre to weigh.** These go past correcting the accepted text:
    1. A1 changes a documented contract. `docs/migration.md` says every `sq migrate` command runs on an out-of-date squad; three stop doing so. The adopter migrates first and then runs them, or upgrades the package when the squad is ahead.
    2. A4 changes what `migrate up` does with an unreadable item file. Today undecodable bytes are skipped, the schema is stamped and the exit is 1. Under A4 the run refuses until the file is fixed, because once the stamp is written no runner ever visits that file. Malformed frontmatter already refuses this way today. The alternative is to keep stamp-and-report for both.
    3. A5 surfaced a defect outside TASK-954 as drafted: a squad stamped 0.11 or older whose valid override declares a type of its own, with one item of it, cannot migrate at all, because three runners open the index store under the bundled vocabulary. It needs a home, in TASK-954 or as a bug. I filed nothing.
    4. ADR-663 states `sq repair` as the recovery path without condition, and this record qualifies that behind the gate. ADR-663 owes a reciprocal dated note; I left it alone under this run's scope.
    
    **Evidence.** Driven by me in scratch squads (dev build at 9a00ddb4; corpora made by the current package and hand-stamped 0.14, 0.11, 0.8 or 0.99): every index-state stop, the file the index lacks, a value ahead of the index, a hand-edited status, the three writing verbs behind, `repad` and `rename-status` ahead, both override refusals, malformed frontmatter against undecodable bytes, the ahead squad with an override conflict, the custom-type override with its two controls. Read-only over the eleven corpus fixtures: no `sequence_id` in `v0_1` or `v0_2`, and no fixture index refused by the cross-check under the bundled spec. Read: the gate, the `migrate` commands, `run_pending_migrations`, `repair`, `repad`, the rename services, the store, every runner module. Taken from the tech lead and not re-driven: the bypass-built service failing one layer down (I read the mechanism), an index that is JSON but fails the model, an entry whose file is gone.
    
    @manager for the operator's read before TASK-954 is promoted. What the subtasks must change is on TASK-954.
- [2026-10-09T20:16:20Z] `op-pierre` Pierre Chat:
  - 2026-10-09: the amendments of this date are confirmed, including the two that change what an adopter can do: A1 (only migrate up, help and chlog run on a squad whose schema differs from the package) and A4 (migrate up refuses rather than stamps past an item file it cannot index).
- [2026-10-11T22:18:54Z] `architect` Robert Architect:
  - 2026-10-12: amended in place a second time, on REV-995 findings 7, 9 and 12. Five dated notes (at clause 1 of the licence, at the reconcile's obligations, under A2, under A4, under the 2026-10-09 obligations) and a closing section **Amendments — 2026-10-12** with A8 to A10. The diff is additions only in the body; status untouched.
    
    **The rule (A8).** A file is the squad's item only where the squad keeps items of that prefix. A location is a directory and a prefix, known from the previous index (the path each entry records) or declared by the run's resolved vocabulary. Nothing outside a location's directory is opened, indexed, reported, counted or written to, and the tree is no longer walked. The measure is the trailing `repair`: the reconcile's idea of the squad's files is `repair`'s, with the previous index standing in for what the vocabulary does not declare.
    
    **A9.** Whether an unreadable file is the squad's is decided by where it sits, never by its content. At a location it stops the run, with or without a previous entry; anywhere else it is never opened. The remedy becomes "correct the file, or, when it is not one of the squad's items, move it out of the folder it sits in".
    
    **A10.** A number shared by two different ids still stops the run (it is A4's case), with a true cause and a hand renumber spelled out. No renumber is made reachable behind the gate.
    
    **For op-pierre to weigh.** I see one defensible rule and two real choices inside it:
    1. A8 narrows clause 1 of the licence he accepted: the routine is handed each type's declared folder and prefix as plain pairs. Without that, a squad with no readable index has no record of where its corpus lives. The strictly blind alternative is to recognise every item-shaped file in the tree in that state, which brings back findings 7 and 9 there. I ruled the hand-in.
    2. A10 keeps the refusal. The state is routine after a merge and `sq check` is clean in it today (BUG-994), so the refusal can be its first sign, and the way out is a hand renumber or the renumbering repair of the release the squad is stamped for. The alternative is to migrate and leave it to `sq repair --renumber`, which stamps past the file left out of the index. I ruled refusal, as A4 does.
    
    Two smaller effects he should know of: a copy of an item in an archive or backup folder is now ignored where the built routine refused it; and a never-indexed, id-less file named for an item inside a type's folder now stops the run, where `repair` reported it after the stamp.
    
    **Evidence.** Nothing was driven for this ruling. My probe script ran in the repository instead of a scratch squad and was stopped; the coordinator repaired the board. Every claim is marked read (the routine, its call site, `repair`'s scan, alignment refusal and duplicate-id reader) or taken from REV-995, and the amendment names each row the developer still owes as proof: the no-index state beside a stray file, a file with another type's prefix inside a type's folder, the id-less file, a same-id copy under any name in a type's folder, and the two pipeline invariants.
    
    @manager for the operator's confirmation. What the code and tests must change is on TASK-954.
- [2026-10-12T05:16:13Z] `op-pierre` Pierre Chat:
  - 2026-10-12, on the amendments of this date:
    
    - A8: not confirmed as written. The routine stays strictly blind: its locations come from the previous index only, and no declared folder or prefix is handed to it. With no readable index it recognises every item-shaped file in the tree.
    - A9 follows A8 as corrected.
    - A10: confirmed. Two ids sharing one number stop the run, with the number, both ids and both paths named and the renumber by hand spelled out.
- [2026-10-12T05:21:58Z] `architect` Robert Architect:
  - 2026-10-12: corrected in place to carry the operator's decision of this date. A8's second source (declared folder and prefix handed to the routine) is withdrawn; clause 1 of the licence stands as first written. Eight dated notes mark the sentences that no longer hold (two at the licence and the reconcile's obligations, one under A2, three in A8, one in A9, one at the obligations list) and a new section A11 states what replaces them. The original A8 and A9 text is left readable; A10 is untouched. Additions only in the body.
    
    **The rule now.** With a readable previous index, a location is the directory and file-name prefix of an entry's recorded path, and nothing else. With no readable index the tree is walked and every file with an item's name and a well-formed `id` is recognised.
    
    **What the check before the first runner (A6) carries.** It holds the vocabulary, so it asks two questions the routine cannot: does every indexed file sit where a declared type lives, and does every file named for an item where a declared type lives have an entry. A run that fails either is refused before any item file is written. With both, the invariant of A8 still holds: no run that reaches its first runner is refused by the trailing `repair` for where a file sits.
    
    **The cost in the no-index state, for op-pierre.**
    - A squad with no readable index and any item-shaped file outside its type folders (an archive, a backup, a fixture, another tool's numbered record) is refused before the first runner, where the first version of A8 migrated it. A look-alike document that cannot be read stops it too. The cause is true and no runner has written, so it is a refusal and not the half-migrated state REV-995 found.
    - The remedy is to restore the index, from version control or with the index rebuild of the release the squad is stamped for. Moving the files out is the other way, and at a project-root squad that means out of the repository.
    - A refused run in this state must leave no index behind. One built from a tree walk and kept would turn every stray's directory into a location for the next run and raise the counter. This is a new obligation born of the decision.
    - With an index, the first item of a type left unindexed in a folder the index does not know is no longer found by the routine. A6 refuses it rather than let the run stamp past it, and the remedy is again the stamped release's index rebuild.
    
    **One point to reconsider, stated once.** The vocabulary still decides both cases, one step later and by refusing instead of by looking: A6 uses the same declared folders and prefixes the routine was denied. So strict blindness buys the licence its purity and costs two refusals with remedies outside this package, plus the no-index-left-behind rule, in states the declared pairs handled in one run. If that trade is the intended one, nothing here needs to change.
    
    **Evidence.** All of A11 is read, none driven; the rows owed are listed at its end and on TASK-954.
    
    @manager for the operator. What flips in the built code and rows is on TASK-954.
- [2026-10-12T06:23:28Z] `architect` Robert Architect:
  - 2026-10-12: one dated note added at A11, on REV-995 finding 17 (a type prefix the routine's name pattern does not match). Additions only in the body.
    
    **Ruled.** With an index the routine uses the spelling each entry records, so any prefix a squad actually used is recognised and no pattern is involved. With no index the tree walk keeps one shape, widened to letters, digits and underscores. The invariant of A11 does not rest on that shape: the check before the first runner lists files by each declared prefix exactly as declared, so an item the walk misses is refused before any runner and never stamped past.
    
    **For op-pierre to weigh, two things.**
    1. The wider walk shape takes a few more file names for items when there is no index. It only matters in that state, and a file that parses without a well-formed id is still passed over.
    2. The workflow spec has no grammar for a type's prefix: any string loads, checked for uniqueness only (read). Four readers in the code each assume a different one. I did not rule a load-time grammar, because it is a hard stop for a squad already using a prefix it would refuse, and it belongs with ADR-696. It is worth its own decision: a prefix holding a slash or a glob character would reach `repair`'s scan as declared (inferred from reading the glob, not driven).
    
    @manager for the operator; the code and rows are on TASK-954.
- [2026-10-25T21:42:24Z] `architect` Robert Architect:
  - 2026-10-25 audit: body rewritten in present tense; decision unchanged. A1-A11 and the REV-995 F17 note folded (per-command grants, locations from the previous index only, no-index walk, checks before the first runner). Added as fact: sq override list/diff/update pass the gate behind the package (BUG-1060, ground "touches no squad state"). @manager op-pierre may want to confirm that override update re-stamping .overrides files fits that ground.
- [2026-10-25T21:47:50Z] `manager` Catherine Manager:
  - Confirmed: sq override list/diff/update run behind the schema (BUG-1060); the stamp rewrite touches no squad state.
<!-- sq:discussion:end -->
