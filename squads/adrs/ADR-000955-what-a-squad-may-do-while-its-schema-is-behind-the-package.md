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
description: 'The reconcile licence: vocabulary-blind, content-neutral, convergent
  — and why the reconcile lives inside migrate up rather than as an exemption for
  sq repair'
created_at: '2026-09-15T08:58:16Z'
updated_at: '2026-09-15T09:17:00Z'
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

Because it strips nothing, `repair`'s ordering prohibition is satisfied vacuously rather than
weakened, and `repair`'s own "by construction" proof stays true verbatim, because nothing else
was exempted.

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

The obligation is enforceable rather than editorial: a meta-test asserting that no migration
runner module's text names a gate-refused `sq` subcommand is the cheap form, and it is the form
that survives the next migration being written by someone who has not read this record.

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
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-15T09:17:00Z] Pierre Chat:
  - Accepted. The reconcile licence stands as ruled: vocabulary-blind, content-neutral, convergent,
    with sq repair unexempted and the licensed reconcile running as migrate up's own pre-pass.
<!-- sq:discussion:end -->
