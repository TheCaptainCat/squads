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
updated_at: '2026-10-09T20:16:21Z'
---
<!-- sq:body -->
## The state, and why it currently has no exit

A squad's `.squads.toml` carries a `schema_version`. When it does not equal the installed
package's `SCHEMA_VERSION`, `require_current_schema` (`_cli/_common.py`) refuses every
subcommand but `migrate`, plus `--help`: behind the package it says "run `sq migrate up`",
ahead of it "upgrade the squads package".

Three places name `sq repair` as the remedy for a state that is only reachable while the
schema is behind (**read**):

- the 0.14 to 0.15 runner's three abort messages, and its module docstring twice — "`sq repair`
  before re-running `sq migrate up` is the recovery path, the same one every other single-item
  write seam already points at";
- `_index/_store.py`'s module docstring, whose entire skew-direction argument rests on it —
  a four-row table headed "`sq repair` outcome", and the closing sentence that `sq repair`
  remains the recovery path even out of the failure model;
- `_itemfile.skew_message`, the one shared refusal every single-item write seam raises:
  "run `sq repair` before mutating <id> again".

Behind the gate every one of those names a command that exits 1. The sentence in the runner's
docstring is load-bearing rather than decorative: it is the stated justification for choosing
abort-on-skew over skip-and-report, and it rests on a recovery path that does not exist in the
state it fires in.

> **Amended 2026-10-09 (A7):** two of the three sites are gone. No runner module contains a
> `raise` or imports `skew_message` or `ensure_no_skew`, and the sentence quoted from the runner's
> docstring is no longer there (**read**). The store docstring stands as described. The remedies
> that name a refused command behind the gate today are other ones, listed in A7.

The obvious repair — add `repair` to the exempt tuple — is refused below, and the reason it is
refused is the substance of this record. What replaces it is a rule about *operations*, so the
next migration inherits the answer instead of re-deriving it.

## What the gate is actually protecting

Two distinct costs, which the single word "staleness" runs together and which have to be
separated before anything can be exempted.

**1. Answering a question with the wrong vocabulary.** A command that resolves a type, a status,
a prefix, a folder, a ref kind, a view name or a badge off the installed spec, and applies that
answer to a corpus written against an older one, reports something untrue. This is a read
hazard: nothing is damaged, the operator is misled.

**2. Writing a corpus under a vocabulary it was not written in.** A command that rewrites item
content using the installed spec's answers converts the first hazard into a durable one. The
corpus stops being the thing the pending migration was written against, and the migration —
which is the only code that knows how to carry it forward — no longer has its documented input.

The gate as written stops both by stopping everything. That is why it is correct today and why
widening it is not a one-line change: the exempt set is currently justified by a property nobody
has had to write down, because it has only ever had one member.

## Why `sq repair` cannot be the exit

`sq repair` is not a read. It is a corpus-wide read-modify-write whose behaviour depends on the
installed vocabulary at six points, four of which write (**read**, all in
`_services/_maintenance.py` unless noted):

- `_iter_item_files` globs by the **active spec's** declared folder and prefix per type. A
  migration that re-folders or re-prefixes a type makes the pre-migration files invisible to
  this scan.
- `_corpus_alignment_refusals` then detects exactly that and refuses the whole rebuild — so on
  a corpus the pending migration is about to move, `repair` either misses files or refuses.
- `default_kind = self.spec.default_ref_kind()` is threaded into every
  `Item.from_frontmatter`, so the legacy-kind fold is resolved against the *installed*
  `[ref_kinds]` declaration.
- `_raise_unless_vocab_valid` rejects any item whose type, status or sub-entity status is not
  declared by the installed spec. A status a pending migration renames is refused here, and the
  refusal names `sq repair` as its own remedy.
- `_record_pending_rewrite` **writes**: the canonical ref re-encoding produced by that fold, the
  retired-region strip, the body-tag convergence (`_repair_body_tag` / `_converge_body_tag`,
  both gated on `self.spec.views`), and the removal of retired role `extra` keys from the file
  *and* from the indexed item.
- `SquadsDB.schema_version` defaults to `SCHEMA_VERSION` (`_models/_index.py`), so any rebuild
  stamps the **installed** schema into `.squads.json` while `.squads.toml` still says the old
  one — a second, quieter version of the mismatch the gate exists to report.

There is also a structural dependency that an exemption would silently delete. `repair`'s own
docstring records an ordering prohibition — a strip must never run ahead of a surface
regeneration that reads what it removes — and states that the first half holds **by
construction**, citing `require_current_schema` by name: `sq repair` can only run against a
corpus already at the current schema, and the single call on a behind-schema corpus is the tail
of `run_pending_migrations`, after every runner. Exempting `repair` converts that construction
proof into a convention, and the thing it was protecting is not hypothetical: a runner's surface
step compiles the managed regions and every backend pointer from the roster projection it reads
off the corpus, and a strip landing first regenerates them from what it has just removed, with
nothing near the cause failing.

> **Amended 2026-10-09 (A1):** this construction did not hold. `sq migrate repad` ends in
> `repair()` and the gate exempts the whole `migrate` group, so the full sweep runs on a squad
> behind the package and on one ahead of it (**driven**). A1 is what makes the docstring's claim
> true.

So the candidate narrowing "exempt `repair` wholesale, because a rebuild answers from the
frontmatter and not from vocabulary" does not survive contact with the code. The rebuild answers
from the frontmatter *as read through the installed spec*, and it rewrites what it reads.

## Ruled: the reconcile licence

An operation may run on a squad whose stamped schema is not the installed package's if and only
if all three clauses hold, for every input corpus:

1. **Vocabulary-blind.** Its behaviour is not a function of any spec-resolved value — the type
   set, the status set, a type's folder or prefix, the declared ref kinds and their default, the
   view set, the sub-entity kinds, the badge collections, the validator catalog. It reads the
   corpus *structurally* (bytes, filenames, marker shape, frontmatter keys) and never
   *semantically*.
2. **Content-neutral.** It writes no item body and no frontmatter field value. The only squad
   artifacts it may write are ones that are derived and rebuildable in full from the markdown —
   in practice the index and the reflog — and it must write them stamped at the schema the
   corpus is stamped at, never at the installed one.
3. **Convergent.** It leaves the squad no further from a successful `sq migrate up` than it
   found it, and it never makes a later migration's input differ from what that migration was
   written against.

Anything that fails clause 1 or clause 2 is a **migration step**, not a maintenance command, and
its home is a versioned runner where the schema it assumes is written down and the transition it
performs is reviewable. That is the general rule, and it is what the next migration inherits:
the question to ask of any future remedy is not "is this command safe" but "does this operation
hold the three clauses".

Two things follow immediately.

- `sq repair` **does not hold the licence**, at four write points and six read points, and is
  not granted an exemption in any form — not wholesale, not behind a flag, not in a "skip the
  sweeps" mode (see the next section for why a mode is the wrong shape even where the subset is
  right).
- Emptiness of the exempt set is not the goal. A licensed operation is welcome. What is ruled
  out is granting the exemption to a *command* on the strength of its name, when the licence is
  a property of what the operation does.

## Ruled: the exempt set stays at one, and widening has a declared shape

The gate keys on a subcommand name because it runs in the root callback, before any command
body exists to ask. That is the right place for it — a gate that ran after command construction
would have to survive `open_service` first, which is itself vocabulary-dependent — and the
keying is not the problem. The problem is that a name in a tuple carries no proof.

Ruled: **`migrate` remains the only exempt subcommand.** It is the only command whose entire
contract is "assume nothing about the installed vocabulary matching this corpus; advance it",
and it is therefore the only member whose licence can be *proved* rather than asserted. Every
other command in the CLI resolves vocabulary somewhere on its path, most of them before their
own first statement.

> **Amended 2026-10-09 (A1):** this paragraph describes `sq migrate up`. `migrate` is a group of
> six commands, the gate exempts all of them, and three do not hold the licence. A1 grants the
> exemption command by command, in the declared-capability shape the next paragraph rules.

If a future command genuinely earns the licence, the widening is expressed as a **declared
capability on the command** — a marker the root callback consults, sitting beside the command
whose behaviour it claims — plus a meta-test asserting that the gate's exempt set equals the set
of commands carrying the marker. Never a second literal appended to a tuple. The reason is the
one this record is fixing: a name in a tuple is a claim with no home for its justification, and
the next person to widen it has nothing to read.

**One obligation this ruling creates immediately, because the exemption is currently nominal.**
`sq migrate up` builds its service through `get_service()` — the cross-checked path (**read**,
`_cli/_migrate.py`). For a squad carrying `.overrides/workflow.toml`, `open_service` runs
`validate_against_index_fail_closed` against the live index and raises when any indexed item's
type or status is not declared by the merged spec. So a behind-schema squad with an override can
be refused by the one command the gate exempts, for the same class of reason the gate exempted
it from. Ruled: **the exempt command builds through
`get_service_bypassing_index_cross_check()`**, the accessor whose docstring already states the
governing principle — "a validation gate that locks out its own recovery path is not a recovery
path". An exemption that the command's own construction can veto is not an exemption.

> **Amended 2026-10-09 (A5, A6):** the bypass is necessary and not sufficient, and its last
> fallback, the bundled spec, is refused for this caller. Built this way the same squad is refused
> one layer down, by the index store inside the first runner that opens a transaction (**read**).
> A5 rules the vocabulary `migrate up` runs under, and A6 where a conflict is refused.

## Ruled: the rebuild is separable from the sweeps, and the seam is not a flag

Yes, separable — and the separator is worth naming precisely, because it is the thing the three
candidate narrowings were all reaching for.

- The **structural scan** is a function of bytes: walk the item files, read frontmatter keys,
  derive `(id, sequence number, filename width)` and the indexed fields, commit an index. It can
  be made to hold all three clauses.
- The **semantic sweep** is a function of the installed spec: the legacy-kind fold and its
  canonical re-encoding, the vocab validation, the retired-region strip, the body-tag
  convergence, the retired-key removal, the folder/prefix alignment refusal. It cannot hold
  clause 1 or clause 2 and is not intended to.

`_rebuild_index_from_disk` interleaves them in one walk, deliberately and correctly, for the
one-pass property its docstring argues for. Ruled: **the separation is not expressed as a mode
on `repair`.** A `repair(sweeps=False)` puts two behaviours behind one verb, one of which is
only ever correct in a state the other is never correct in, and makes every future addition to
the sweep a decision about a flag nobody is looking at. It is also the shape that invites the
next person to "just also do the harmless one".

The licensed subset is a **narrower routine of its own**, with the licence as its contract and
the three clauses as its test. What it is obliged to do differently from the rebuild it
resembles, each following from a clause rather than from taste:

- glob the union of every folder the corpus actually contains, not the active spec's declared
  folders (clause 1, and the alignment refusal stops being reachable);
- parse frontmatter without the legacy-kind fold, and write no canonicalisation (clauses 1 and 2);
- perform no vocab validation and refuse nothing on vocabulary grounds — an item whose status a
  pending migration renames is exactly the input it exists to handle (clause 1);
- queue no rewrite of any kind: no strip, no convergence, no retired-key removal (clause 2);
- stamp the rebuilt index at the corpus's own `schema_version`, not `SCHEMA_VERSION` (clause 2);
- carry forward, never fabricate — the same posture the existing rebuild already takes for an
  unreadable file and for an absent timestamp (clause 3).

> **Amended 2026-10-09 (A2):** the folders are whatever the squad directory holds, and what makes
> a file an item there is structural. A2 states the recognition rule, the schemas the routine must
> read, and what it owes each state of the index.

Because it strips nothing, `repair`'s ordering prohibition is satisfied vacuously rather than
weakened, and `repair`'s own "by construction" proof stays true verbatim, because nothing else
was exempted.

> **Amended 2026-10-09 (A1):** true once A1 holds. See the note under "Why `sq repair` cannot be
> the exit".

## Ruled: the reconcile lives inside `migrate up`, as a pre-pass

The premise worth testing is "the index rebuild is the part actually needed after a partial
write". It is close, but it is one step short of the real need, and the step matters.

What an interrupted `migrate up` leaves (**read**): the schema stamp is written only on success,
so the same runners are still pending; the index was never committed, so it is exactly as it was
before the run; the markdown is partially rewritten. The only thing that blocks a re-run is the
guard that compares on-disk frontmatter to the stale indexed item — `ensure_no_skew`, via
`frontmatter_skew`, which compares every frontmatter key including `updated_at` and excludes it
only when the disk side carries no value at all. So an aborted pass that wrote and bumped some
items leaves precisely those items unre-runnable by the next pass.

> **Amended 2026-10-09 (A2):** this premise is stale. No runner calls `ensure_no_skew`, and a
> frontmatter value ahead of the index migrates cleanly (**driven**). Nor is the index left
> exactly as it was: each runner commits its own transaction, so an interrupted chain leaves it
> partly advanced (**read**). What stops a run, or lets it stamp past a file, is the state of the
> index itself, set out in A2. The ruling below stands on those grounds.

The need is therefore not "a command that rebuilds the index" but "**`migrate up` able to read a
corpus whose markdown is ahead of the index**". And that need is satisfiable entirely inside the
one command that is already permitted.

Ruled: **`sq migrate up` reconciles before it runs, not after it fails.** The licensed
structural reconcile runs unconditionally as the first step of `migrate up`, before the first
runner, on every invocation. Three consequences, and they are the point:

- the state a partial pass leaves is healed by the next invocation of the only command an
  operator can reach, with no second command, no gate change, and nothing for the operator to
  know;
- "re-run `sq migrate up`" becomes a *true* remedy rather than an aspirational one, which is
  what makes the messaging rule below satisfiable rather than a wish;
- the existing `repair()` call stays exactly where it is — after every runner, as the corpus
  sweep and the rebuild, on a corpus that is by then at the current schema — and its placement
  argument is untouched.

The cost is one extra index rebuild per `migrate up` on a squad that has something to migrate.
That is a command an operator runs once per release on a corpus of hundreds of files, and it
buys the removal of an unrecoverable state. Accepted without further pricing.

> **Amended 2026-10-09 (A3):** "unconditionally" and "on every invocation" mean with no test of
> whether the index looks stale, on every invocation that has a runner to apply. See A3.

**Named, because this ruling does not remove it:** the reconcile makes the *re-run* possible; it
does not make a runner idempotent. A runner that is not idempotent still produces a wrong result
on the second pass. Idempotence is already an obligation on every runner (each is re-run from
the same stamp), and this ruling raises its importance rather than changing it.

## Ruled: what a remedy may name

**A message may only name a command that is permitted in the state the message fires in.**
Stated that way rather than as a list, because the list changes with every migration and the
obligation does not. A remedy naming a refused command is worse than no remedy: it reads as an
exit, and it costs the operator the time to discover it is not one.

Applied to the three sites (**read**):

- **A migration runner's abort, skip and refusal messages, and its module docstring.** These
  fire only behind the gate, by construction. They may name `sq migrate up` — which, after the
  ruling above, is the true answer — or an action outside `sq` entirely (fix the frontmatter,
  restore the file, edit the override). They may not name `sq repair`, `sq check` or
  `sq workflow views`. The 0.14 to 0.15 runner's docstring claim that `sq repair` is "the same
  recovery path every other single-item write seam already points at" is false in the state it
  describes and is withdrawn: every other seam points at a command the operator can run, because
  no other seam is behind a schema hard-stop.
- **`_index/_store.py`'s module docstring.** Its skew-direction argument is correct at the
  current schema and false behind the gate, and it currently states the correct half
  unconditionally. It must say which: markdown-ahead heals losslessly through `sq repair` at the
  current schema, and through `migrate up`'s own reconcile while the schema is behind. The
  table's column heading and the out-of-model sentence both inherit this.
- **`_itemfile.skew_message`.** The one shared refusal, raised from every single-item write seam
  *and* re-used by migration runners. It is correct for its ordinary callers and wrong for the
  migration ones, which is exactly the shape that produced this defect. A runner that reports a
  skew composes its own remedy clause rather than inheriting the seam's.

> **Amended 2026-10-09 (A7):** the first and third bullets describe code that has gone, and "skip"
> does not belong in the first: a skip is reported by a run that completes, to an operator whose
> squad is by then current. A7 restates the rule's scope and lists the live sites.

The obligation is enforceable rather than editorial: a meta-test asserting that no migration
runner module's text names a gate-refused `sq` subcommand is the cheap form, and it is the form
that survives the next migration being written by someone who has not read this record.

> **Amended 2026-10-09 (A7):** as worded this test fails on correct code. Runner docstrings and
> `MANUAL` runbooks name `sq check` and `sq sync` dozens of times, as steps taken once the squad
> is current (**read**). A7 rules the two tests that carry the rule.

## Ruled: a squad ahead of the package is unchanged, and now for a stated reason

The gate also refuses a squad whose schema is newer than the installed package's. Nothing here
changes for it, and the reason is now derived from the licence rather than left incidental: an
ahead-schema corpus fails **clause 2**. This package's models cannot round-trip a corpus written
against a schema they have no model for, so committing a rebuilt index over the one a newer
package wrote is a lossy write of derived state, not a reconcile — and clause 3 has nothing to
converge toward, because there is no downgrade path and this package contains no runner that
targets that corpus.

The ahead-direction message also already names a remedy that exists and that the operator can
act on ("upgrade the squads package"), so it needs no change under the messaging rule. This is
worth recording precisely because it looks like an inconsistency: the two directions get
different answers because they are different states, not because one was overlooked.

> **Amended 2026-10-09 (A1):** "nothing here changes for it" was not the case. `sq migrate repad`
> and `sq migrate rename-status` rewrite a squad stamped ahead of the package (**driven**). Under
> A1 no command that touches the squad runs on one.

## What this obliges

- The gate's exempt set stays `migrate` alone; `sq repair` is not exempted in any form. Any
  future widening arrives as a declared capability on the command plus a meta-test binding the
  exempt set to it.
- `sq migrate up` builds its service through the bypass accessor, so the exemption is real for a
  squad carrying an override.
- A licensed structural reconcile exists as its own routine, contracted by the three clauses,
  and runs as `migrate up`'s unconditional pre-pass. It stamps the index at the corpus's own
  schema version.
- `repair()`'s trailing placement and its ordering prohibition are untouched, and its "by
  construction" paragraph stays true because nothing else was exempted.
- Every remedy reachable behind the gate names `sq migrate up` or a non-`sq` action. The three
  sites above are corrected, and a meta-test over the runner modules keeps the next one honest.
- The proof owed on landing is a behind-schema squad driven end to end, not a unit test: a clean
  one, one with markdown genuinely ahead of the index, one with a skewed item, one with an
  override that refuses the cross-check, and one *ahead* of the package which must still be
  refused. In each case what is asserted is the operator's position afterwards — that
  `migrate up` completes, that no body was rewritten under the old schema, and that the squad is
  usable from there — never only the exit code.

> **Amended 2026-10-09:** A1 to A7 correct and extend this list. The obligations as amended are
> the closing list under **Amendments**.

## What this record does not settle

- **Whether a licensed reconcile can be reached deliberately rather than only as a side effect.**
  This ruling gives it no verb of its own. An operator who wants to reconcile a behind-schema
  squad *without* migrating has no way to ask, and the answer today is that they should migrate.
  If a case appears where that is wrong, it arrives as the capability-marked command the second
  ruling describes, not as a flag on `migrate up`.
- **A corpus that is behind the schema and also cannot be migrated** — a runner that refuses for
  a reason no reconcile addresses. The reconcile removes the *partial-pass* dead end; it does not
  promise every behind-schema squad a path forward. Where a runner's own refusal is the wall, the
  fix is that runner's refusal, and the messaging rule above is what makes the wall legible.
- **Whether the licence should also govern reads.** The three clauses are written for operations
  that may write. A purely structural read behind the gate — "what is in this corpus" — would
  hold all three trivially, and there may be a case for one. No such command is proposed here,
  and adding one is a decision about the CLI surface, not about this gate.

> **Amended 2026-10-09 (A5):** on the second point above, one such wall is known and it is a
> defect, not a design question: a runner that opens the index under the bundled vocabulary
> refuses a squad whose valid override declares a type of its own (**driven**). See A5.

## Amendments — 2026-10-09

The licence, the refusal to exempt `sq repair`, the pre-pass and the remedy rule stand as ruled.
What follows corrects premises the code has moved past and rules the cases the text above did not
have in front of it. The text above is unedited apart from the dated notes that point here.
Evidence is marked **driven** (run in scratch squads stamped behind or ahead of the package) or
**read**.

### A1 — The exemption belongs to commands, not to the `migrate` group

The root callback sees the group name only, so "`migrate` is exempt" exempts six commands.
Measured one by one against the licence:

| Command | Squad behind | Squad ahead | Ground |
|---|---|---|---|
| `sq migrate up` | runs | refused | It is the migration, the one command whose contract is to advance the corpus. Ahead, it holds no runner that targets the corpus. |
| `sq migrate help`, `sq migrate chlog` | run | run | They read the package's own registry and nothing in the squad (**read**). The licence governs operations on a squad, and these are not one. |
| `sq migrate repad` | refused | refused | Fails all three clauses: it globs by the active spec's folders and prefixes, renames every item file, and ends in `repair()`, the full sweep, ahead of every pending runner (**driven** in both directions: a `repair` reflog entry on a squad stamped behind). |
| `sq migrate rename-type` | refused | refused | Fails clauses 1 and 2: it resolves both types in the active spec, rewrites ids, file names and every referencing file through the installed model, and appends a comment to each body (**read**, and **driven** behind). |
| `sq migrate rename-status` | refused | refused | The same: it writes `status` and appends a comment (**driven** in both directions). |

The three refused commands are maintenance commands for a current squad that live under `migrate`
by name. Each assumes the installed schema without writing it down, which is what this record
says belongs in a versioned runner.

Three grounds let a command past the gate, and they are different grounds: being the migration
(behind only), holding the licence (no command today; the reconcile is a routine), and touching no
squad state (both directions). The capability a command declares names its ground and the
directions it covers. The gate consults it at the `migrate` group as well as at the root, through
one refusal with the same two messages. On a squad ahead of the package the gate refuses `up`
itself, before a service is built, so the answer is "upgrade the squads package" and never an
override refusal (**driven**: today the override refusal is printed instead).

What an adopter does instead. Behind: migrate first, then run the command. Where `migrate up` is
refused because the corpus uses vocabulary the override has dropped, restore the declaration,
migrate, rename at the current schema, then drop it; `rename-type` already requires both types to
be declared while it runs. Ahead: upgrade the package. A squad that has to be repadded or renamed
without being migrated is handled with the squads version it is stamped for.

Two things this makes true that were not: `repair`'s "by construction" claim, and the remedy rule
for `skew_message` and for the three commands' closing "run `sq check`", none of which is then
reachable on a squad whose schema differs from the package's.

### A2 — What the pre-pass is for

The pre-pass is needed for three states of the index, none of them the skew this record named
(each **driven** on a squad stamped behind):

- **No index, or one that does not parse.** `sq migrate up` stops with "run `sq repair`".
- **An entry carrying a type or status the spec does not declare, while the file's own value is
  declared.** The same stop, from the store's load.
- **A file with no entry.** Not a stop: the runners that enumerate items from the index (two
  today, **read**) never visit the file, the run exits 0 and stamps the new schema, and
  `sq check` then reports the item.

What the routine owes each, by "carry forward, never fabricate": with no readable previous index
it builds from the files alone; it reads a previous index without vocabulary validation; a file's
own frontmatter replaces its entry; a file with no entry gains one; an entry whose file is gone is
dropped and named.

Two precisions on the routine itself.

- **An item file is recognised structurally**, wherever under the squad directory it sits: by the
  shape of its file name and of the `id` in its frontmatter, never by a declared folder. A markdown
  file that is not an item is never reported. A squad directory may be the project root
  (`squad_dir = "."`), where the walk meets every markdown file in the repository, and that case is
  the test of the rule.
- **It reads every schema this package can migrate from.** The two oldest carry no `sequence_id`
  in any item file (**driven** over the corpus fixtures); the number is read from the `id`, which
  is derivation and not fabrication. A shape an older schema wrote legitimately is never damage.

### A3 — "Unconditional" means no staleness test

The reconcile runs whenever at least one runner applies, with no test of whether the index looks
stale. It does not run on a squad at the current schema, where `sq migrate up` writes nothing
(**driven**): there `sq repair` is the reconcile, and a second, narrower rebuild of a current
index would put two behaviours behind one state, the shape this record refuses for `repair`. It
does not run on a squad ahead of the package (clause 2).

### A4 — `migrate up` stamps only a corpus every runner could see

The stamp claims that every item file has been through every pending runner. Once it is written
no runner runs again, so a file that was passed over keeps its old shape for good, in a squad
every command now treats as current.

Ruled: after the reconcile, if any item file could not be given an index entry of its own (bytes
that do not decode, frontmatter that does not parse, an identity that cannot be established, an
id two files claim), the run stops before the first runner and names each file with what is wrong
with it. The entry such a file already had is carried forward, not dropped. The remedy is outside
`sq`: correct the file, or take it out of the squad directory, then re-run `sq migrate up`.

This gives one disposition to shapes that get two today (**driven**): frontmatter that does not
parse already stops the run with the schema unchanged, and a re-run after the fix completes,
while undecodable bytes are skipped, stamped past and reported with exit 1. A runner's own skips
are untouched: a runner that visits an item and declines to act on it reports it by id, on a run
that completes.

### A5 — `migrate up` runs under the squad's declared vocabulary, or not at all

A migration run under the bundled vocabulary, on a squad that declared its own, is the second
cost this record names, reached from the other side. Ruled:

- **No bundled substitute.** The last fallback of the bypass accessor suits `sq repair` at the
  current schema and is refused for `migrate up`. An override that does not load stops the run
  before the first runner.
- **One resolution.** The vocabulary is resolved once, before the first write, together with every
  other document a pending runner loads (the playbook override is one). Every step that validates
  against vocabulary uses that resolution: the check in A6, each runner's own access to the index,
  and the trailing repair.

The second clause does not hold today (**driven**). A runner that opens the index store without a
spec validates under the bundled vocabulary (**read**), so a squad stamped 0.11 or 0.8 whose valid override
declares a type of its own, with one item of that type, is refused by `sq migrate up` as carrying
a type "the active spec no longer declares". The same squad stamped 0.14 migrates, and so does a
squad without the override stamped 0.11. Nothing is wrong with the refused squad, and no reconcile
helps it.

The refusal for an override that does not load names the file and the loader's own cause, and as a
remedy only this: correct the file, then re-run `sq migrate up`.

### A6 — A vocabulary conflict is refused before the first runner

A corpus carrying a type, status, prefix, folder or badge code that the resolved vocabulary does
not declare cannot complete a migration. A runner's index transaction refuses it (**read**), or
the trailing repair does once every runner has written (**driven**: both milestone files
rewritten, then the refusal, schema unchanged). Ruled: that refusal is made once, on the
reconciled index, before the first runner. Nothing but the index has been written by then, and
because the index mirrors the files, what it reports is a fact about the corpus and not about a
stale entry.

The check is not part of the reconcile, which stays blind and refuses nothing on vocabulary
grounds. It writes nothing, so it needs no licence. Its bound is its own:

- **It refuses only what the completed run would refuse**: the families the load boundary refuses
  at the current schema, and no more. It is measured against the corpus as the pending runners
  leave it. No shipped runner renames or retires a type, a status, a prefix, a folder or a badge
  code on an existing item (**read**), so today that is the plain cross-check. The first runner
  that does one declares the names it consumes on its migration record, and the check is blind to
  them. Otherwise the check refuses exactly the corpus that runner exists to carry forward.
- **It does not retire the trailing refusals.** What cannot be seen before the runners (state a
  runner lifts out of a body) is still refused after them, with a remedy composed for a squad that
  is still behind.

The refusal names the items, the override when there is one, and as remedies only these: restore
the declaration in the override, or correct the named frontmatter by hand, then re-run
`sq migrate up`.

### A7 — The remedy rule: its scope, its live sites, its tests

The rule stands: a message may only name a command permitted in the state it fires in. Its subject
is a **remedy**, what an operator is told to run to leave the state they are in, and the state is
the one the run leaves them in. A run that completes leaves a current squad, so its report may
name any command. A `MANUAL` runbook and a runner's docstring describe steps taken after that and
are outside the rule.

The sites that name a refused command to an operator left behind the gate (**driven** unless
marked):

- the store's load refusals for a missing index, a corrupt index and an undeclared type or status
  ("run `sq repair`");
- the trailing repair's vocabulary refusals ("before running `sq repair`");
- the override refusal, in its closing line and in the cross-check cause it quotes
  ("`sq workflow lint`");
- the capacity refusal of `SquadsDB.allocate_id` ("`sq migrate repad`"), which the three runners
  that allocate ids can raise and which A1 makes a refused command behind the gate (**read**);
- two docstrings (**read**): the store's, as this record already says, and the paragraph in the
  0.14 to 0.15 runner stating that it cannot raise and that a raised run has no command to
  reconcile with. It can raise, through what it calls, and with the pre-pass `sq migrate up` is
  that command.

A shared message stays worded for its ordinary callers. The remedy is composed where the state is
known, by `migrate up`, and not by rewording the seam.

Two tests carry the rule, in place of the one this record named:

- **Behavioural, and the one that binds.** Over a table of `sq migrate up` runs that end with the
  schema stamp unchanged, every `sq` command the output names is one the gate lets past in that
  state. The permitted set is read from the declared capability and is not written into the test.
- **Static, and narrower.** In a runner module no string that can leave through a `raise` names a
  refused command, and none imports the write seam's skew guard or its message. It is scoped to
  `raise` because the rest of a runner's text is description.

### What the amendments oblige

- On a squad whose schema differs from the package's, the gate lets past `sq migrate up` when the
  squad is behind, and `sq migrate help`, `sq migrate chlog` and `--help` in both directions.
  Nothing else. Each declares its ground and its directions, a meta-test binds the set that gets
  past the gate to the set that declares one, and a command added under `sq migrate` without a
  declaration is refused.
- On a behind squad every refusal that can be known in advance precedes the first runner: the
  declared vocabulary resolves (A5), the reconcile runs (A2, A3), every item file has an entry of
  its own (A4), and the reconciled corpus fits the vocabulary (A6). Only the index is written
  before the first runner.
- Every runner reaches the index under the vocabulary the run resolved (A5).
- A run that leaves the squad behind names, as remedies, only commands the gate lets past and
  actions outside `sq` (A7).
- The proof owed on landing adds to the shapes this record lists: the index states of A2, the
  unreadable-file shapes of A4, a valid override declaring a type of its own on a squad several
  schemas behind (A5), an override conflict and a hand-edited value (A6), a squad whose directory
  is the project root (A2), and the gate rows of A1 in both directions. Markdown ahead of the
  index and a skewed item both complete without the pre-pass, so alone they prove nothing about
  it.
- Two changes an adopter can observe: `repad`, `rename-type` and `rename-status` no longer run on
  a squad whose schema differs from the package's, and `sq migrate up` no longer stamps past an
  item file it cannot read.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-15T09:17:00Z] Pierre Chat:
  - Accepted. The reconcile licence stands as ruled: vocabulary-blind, content-neutral, convergent,
    with sq repair unexempted and the licensed reconcile running as migrate up's own pre-pass.
- [2026-10-09T19:36:36Z] Robert Architect:
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
- [2026-10-09T20:16:20Z] Pierre Chat:
  - 2026-10-09: the amendments of this date are confirmed, including the two that change what an adopter can do: A1 (only migrate up, help and chlog run on a squad whose schema differs from the package) and A4 (migrate up refuses rather than stamps past an item file it cannot index).
<!-- sq:discussion:end -->
