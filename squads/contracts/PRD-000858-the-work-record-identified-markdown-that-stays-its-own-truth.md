---
id: PRD-858
sequence_id: 858
type: contract
title: 'The work record: identified markdown that stays its own truth'
status: Draft
author: product-owner
refs:
- PRD-862
- PRD-859
description: 'How work is stored: identified markdown files, durable IDs, per-type
  lifecycles, one-way links, and a rebuildable index.'
created_at: '2026-09-01T13:02:15Z'
updated_at: '2026-09-01T13:53:14Z'
---
<!-- sq:body -->
## What the product does

Every piece of work a squad tracks is one markdown file with YAML frontmatter, filed in a
folder per type and named `PREFIX-NNNNNN-slug.md`. Those files are the product's data. Nothing
squads keeps anywhere else can outlive them, and nothing has to be exported to read them: they
are plain text, they diff, they merge, and they travel in the project's own version control
alongside the code they describe.

### Identity that does not move

One monotonic counter numbers everything in a squad — work items and the roster alike, so a
number is unique across the whole corpus and never has to be qualified by type to be
unambiguous. An item's address is its type prefix plus that number (`TASK-<n>`). The number is
the durable half: reclassifying an item to another type keeps the number and changes only the
prefix, and every incoming reference, child parent-link and prose mention is rewritten to the
new address in the same operation.

Numbers are never reused. Deleting an item leaves its number permanently retired, so a gap in
the sequence is normal, expected state rather than a sign of damage — a reader can rely on a
missing number meaning "something was here and was deleted", and the corpus tools treat it that
way. On disk the filename zero-pads the number so files sort lexicographically; the padding
width is a property of the squad, raised in one step across the whole corpus, never lowered.

Two exits from a piece of work are kept distinct, because they answer different questions.
Cancelling records that the work was genuinely considered and dropped — the item stays on the
books, greppable and linkable. Deleting records that the item should never have existed; the
file and its index entry go, and the operation refuses while anything still points at the item
or hangs beneath it, listing every offender. Forcing the delete severs the incoming references
in the same transaction rather than leaving them dangling.

### A state machine per type, not one for everything

Each type carries its own lifecycle: a named initial state and a table of permitted moves. A
transition the machine does not allow is refused, so an item's status is always a state its own
type actually declares. Types with genuinely different rhythms get genuinely different
machines — a record that is proposed and accepted does not have to pretend it is work that is
started and finished.

Structure is declared the same way. A type states which types may parent it, and a parent link
outside that set is refused with a hint naming what is allowed.

### Links that point one way

A reference is stored on the item you add it to, and only there. The reverse direction is never
written down — it is computed by inverting the stored edges across the corpus, so the two
directions can never disagree and no operation has to remember to update a second copy. Asking
an item what points at it is a read, not a lookup in a maintained list.

A reference carries its kind inline. Kinds are declared vocabulary with declared meanings:
some are purely navigational, and some are read by the tooling — a dependency edge is what
makes an item show up as blocked by another still-open item. What binds behaviour is the kind's
declared semantic role rather than its spelling.

### Sub-entities

A type may declare one kind of sub-entity that lives inside its parent — a story under a
feature, a subtask under a task, a finding under a review. A sub-entity has its own title,
status, assignee and declared fields, and its own prose and discussion.

Its state lives in the parent's frontmatter. Only prose lives in the body. That split is what
lets a sub-entity be filtered, rolled up and assigned without parsing prose, and it is why the
roll-up a reader sees is computed at read time rather than written into the file and left to
rot.

### Prose is yours; regions are the product's

Body text, discussion and each sub-entity's prose sit inside named marker regions. Every write
the product makes goes to a region, and everything outside the regions is left exactly as
written. An item file can therefore carry hand-written headings, notes and structure around the
managed parts without the next write eating them.

### Integrity as a property of the record, not a service beside it

A squad keeps an index next to the files, and the index is a cache — it holds nothing that
cannot be reconstructed from the frontmatter. That is testable rather than aspirational:
deleting the index and rebuilding it from the markdown alone reproduces it entry for entry,
including the counter's high-water mark. Until it is rebuilt, commands refuse and say so rather
than guessing.

A corpus lint reads the whole squad and reports what has gone wrong against the declared rules:
damaged or missing marker regions, references to items that do not exist, reference kinds the
vocabulary does not declare, statuses invalid for their type, parent links the type rules
forbid, sub-entities left at their placeholder prose, sub-entity titles carrying prose that
belongs in a body, workflow state written into a body as prose, and drift between the files and
the index. It reports every problem in one pass with a fix hint for each.

The on-disk shape is versioned. A squad on an older schema is stopped at the door and told to
upgrade rather than being read with the wrong assumptions, and the upgrade applies ordered
migrations, rebuilds the index and stamps the new version. Corpus-wide relabelling is separate
from schema upgrade and explicit: moving every item of one type to another type, moving every
item of a type off one status onto another, raising the filename padding.

A branch that filed its own items can be block-shifted onto a number range that does not
collide with another branch's before the two are merged; parent links and references follow the
items to their new addresses, and the mapping is printed.

Every mutating command appends to a chronological operation log, so the sequence of changes to a
squad is readable after the fact — including the deletions that explain a gap.

### Bulk entry

A whole history can be replayed into a squad from one event stream in a single process: items,
bodies, comments, references and sub-entities, with symbolic handles standing in for IDs that do
not exist yet and resolving to the numbers actually allocated. Validation is fail-closed and
runs first — a stream with any invalid event writes nothing at all and reports every problem,
and a dry run prints the projected handle-to-ID plan without touching the squad. Timestamps can
be forged deliberately when the point is to migrate history rather than to record now.

An existing folder that already looks like a squad can be adopted in place rather than
recreated: existing items are imported keeping their numbers, and nothing already on disk is
overwritten.

## Scope

The storage format and the guarantees that hold over it: item files and their frontmatter,
identity and numbering, per-type lifecycles and parent rules, references and their computed
inverse, sub-entities, marker regions, the rebuildable index, the corpus lint, schema versioning
and corpus-wide relabelling, the operation log, bulk import and adoption.

What a squad's types, statuses, lifecycles, reference kinds and sub-entity kinds actually *are*
is declared vocabulary and belongs to the vocabulary contract; this contract covers the
machinery that holds whatever is declared. How the record is read belongs to the read-surface
contract.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-01T13:11:36Z] Nina Product:
  - The contract set is six documents; the seams and what changed from the proposal are recorded on each one's Scope section. Every capability claim in these bodies was driven against the shipped CLI in a throwaway squad — a fresh init, a custom item type declared end to end, an index deleted and rebuilt, an import replayed, a corpus renumbered, both agent backends, and the terminal browser run headlessly. Claims that could not be driven were left out rather than softened.
    
    Two boundaries are stated in the bodies as limits rather than omitted: a type's prefix and folder cannot be changed once items are filed under it (refused, offending IDs named, no realignment command), and the skills and developer listings answer only in the human rendering, not in JSON.
- [2026-09-01T13:11:38Z] Nina Product:
  - Creating the first contracts made the advisory currency check fire for the first time. It is inert while no contract exists; with one on disk it warns on every feature that has settled without an `implements` ref to a contract.
    
    Measured on this corpus: `sq check` goes from clean to 92 warnings, 0 errors, exit 0 — all one rule, all on Done features, none on the contracts themselves. Verbatim: "settled with no implements ref to a contract — its functional contract slice may be stale".
    
    The check is correct, not noisy: none of those features updated a contract, because there were none to update. Clearing it means deciding which contract slice each delivered feature shaped and adding the ref — a judgement call per feature, and one that should wait until the set is no longer Draft. Backfilling 92 refs quickly would put unearned claims on the record, which is the opposite of what a contract is for.
- [2026-09-01T13:53:14Z] Nina Product:
  - Seeding pass: `implements` refs from settled features to the contract slice each one delivered. No contract created, nothing retyped, nothing force-fitted.
    
    **Population.** The 92 features `sq check --json` warned on, read from the check output itself, not from a hand-copied list.
    
    **Method.** For each feature I read title, summary, stories and — where those were not decisive — the body, then matched against the six contracts' own **Scope** paragraphs. Test applied: a contract earns the ref when its prose or scope *states the promise the feature delivers*, not when the subject matter is merely adjacent. A second ref only where two acceptance criteria land in two different contracts (e.g. a mechanism plus its rendering into host files). Where nothing stated the promise, the feature was left unreffed rather than filed under the nearest contract.
    
    **Result.** 75 features seeded, 85 refs. Warnings 92 → 17, drop exactly 75, zero errors. Distribution: 858/17, 859/24, 860/11, 861/8, 862/14, 863/11.
    
    **Homeless — 17.** (a) = internal/dev-process, should never have warned; (b) = adopter-facing capability none of the six covers.
    
    - FEAT-13 Stability contract documentation — (b) *the compatibility promise*: which surfaces are SemVer-stable, the 0.x→1.0 migration promise, what is explicitly not public. The biggest real gap.
    - FEAT-17 1.0 hardening — (a) CI fixture corpus, scale test, Python-floor decision. Two adopter-facing crumbs ride along (shell completion, the supported-Python floor) that also belong to a compatibility/install slice if one is ever written.
    - FEAT-18 Backfill architecture documentation into squads — (a) dogfood: this repo's own guides and ADRs.
    - FEAT-34 Async to the core — (a) refactor, explicitly "byte-identical outputs, the CLI user sees zero change".
    - FEAT-125 Best-effort spawn-lineage recording — (b) *attribution and forensics*: which agent session did what, recorded-not-signed. The operation log's existence is in this contract; who performed an operation, and the lineage above them, is stated nowhere.
    - FEAT-231 Ground-up test battery — (a).
    - FEAT-237 Strip squad-item refs from non-item content + hygiene guard — (a).
    - FEAT-250 De-globalize workflow spec, threaded context — (a) refactor, no adopter-visible promise.
    - FEAT-336 Audit agent/user-facing surfaces for vocab-hardcoding — (a) survey, produced a matrix, no shipped behaviour.
    - FEAT-533 Statelessness: one process, many squads — (a) today: explicitly "does not build the server, makes the engine safe to run inside one". Becomes (b) *embedding* the day a daemon or server ships.
    - FEAT-572 Migrate 5 parented ADRs to related refs — (a) this repo's own corpus data fix.
    - FEAT-573 Consumer audit: is_meta sites reclassified to category — (a).
    - FEAT-574 Docs accuracy + drift guard for CLI verbs — (a) doc maintenance plus a CI guard.
    - FEAT-644 Recommend a manager-run init interview — (a) adopter-facing docs guidance with no mechanism behind it; it deliberately ships nothing sq prompts for or checks.
    - FEAT-652 Consolidate bundled TOML into _bundled — (a).
    - FEAT-660 Release version-bump script — (a).
    - FEAT-715 Consolidate bundled specs under _specs/ — (a) pure relocation, byte-identical behaviour.
    
    Fourteen of the seventeen are (a). Two are (b) outright, one conditionally.
    
    **Corpus evolution is not a gap.** Retype, sanctioned removal, repad, renumber, rename-type/rename-status, unpadded IDs, bulk import and adoption are all stated in this contract already — identity that survives reclassification, retired numbers, padding raised in one step, block-shift before a merge, corpus-wide relabelling as a move separate from schema upgrade, bulk entry and adopt-in-place. All eight of those features seeded here cleanly. What is true is that this contract carries two jobs — the format and its guarantees, plus the machinery that reshapes a corpus without losing it. If a seventh is ever wanted it is a **split of this one**, not a hole being filled, and the drift check reads the same either way.
    
    **Auditability is half a gap.** The log itself is covered (this contract for its existence, the read-surface contract for reading it), so the reflog feature seeded. The layer above it — actor identity, session, spawn lineage, and the honest "recorded, not signed" guarantee — is described nowhere. That is the second (b).
    
    **Tempted and refused.** The compatibility promise into this contract's schema-versioning paragraph (versioning the on-disk shape is not promising a stable CLI). Spawn lineage into the operation-log sentence (the log records changes, not who is behind them). One-process-many-squads into the read surface's "no session, no daemon" line (that line describes today's absence of a daemon, not a promise to host one). The docs features into the read surface's offline-documentation clause (that covers `sq docs` existing, not the shipped docs being accurate). Filing any of these would have hidden exactly the drift this exercise exists to expose.
    
    **One prose gap, not a homeless feature.** The contract-currency check that produced these warnings is not named in this contract's list of what the corpus lint reports. Worth adding when this slice is next rewritten.
    
    @product-owner
<!-- sq:discussion:end -->
