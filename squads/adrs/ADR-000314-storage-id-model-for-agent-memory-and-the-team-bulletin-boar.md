---
id: ADR-314
sequence_id: 314
type: decision
title: Storage & id model for agent memory and the team bulletin board
status: Accepted
author: architect
description: Slug-file-per-memory + own lighter board store, both off the global counter
  and outside .squads.json
created_at: '2026-07-06T16:03:50Z'
updated_at: '2026-07-15T12:36:47Z'
---
<!-- sq:body -->
# Context

Two complementary, lighter-than-item artifacts are being added to a squad:

- **Agent memory** — a per-role, committed notebook of small, agent-authored, *descriptive*
  facts ("what I learned"). Each role owns its own pool (scoped by ownership, not tagging).
  Being committed to the repo is the whole point: a fresh checkout or a new teammate's agent
  inherits the accumulated per-role memory — so it must merge cleanly across branches and
  across multiple concurrent devs. Retrieval is **pull, direct from the `.md` files**: an agent
  lists its own pool at the start of a run and fetches full content on demand.
- **Bulletin board** — a team-scoped, everyone-reads broadcast of *prescriptive* notices
  ("what we all need to know right now"), human/lead-posted and usually time-bound (they come
  down via an `--until` expiry). Cross-cutting facts live here once, not duplicated into every
  role's memory. The boundary: personal-learned -> memory; cross-cutting/announcement -> board.

This ADR fixes the **storage format and id model** for both. It does not design the CLI shape
(owned by product) beyond checking it for architectural implications.

# Decision drivers (settled at product level — recorded, not relitigated)

1. **These are a lighter tier than items and must NOT draw from the global sequence counter.**
   The counter is the crux of the pain we are avoiding: a counter-allocated id created on two
   branches collides on both the counter and the filename — the exact mess `sq renumber` and
   `repair --renumber` exist to clean up after. Memory is high-frequency and low-ceremony, so
   that collision would be near-constant. Ids must be human-meaningful (slug or short hash),
   never sequence numbers.
2. **Placement follows the existing layout.** `squads/agents/` already holds agent-scoped state
   (`roles/`, `skills/`), so memory nests there: `squads/agents/memory/<role-slug>/`. The board
   is team-scoped, so it is its own top-level folder, sibling to the item-type folders:
   `squads/board/`.
3. **The index invariant must stay clean.** `.squads.json` is a rebuildable index of
   counter-allocated items that `sq repair` reconstructs from item frontmatter. Nothing about
   these lighter tiers may weaken that guarantee.

# Options weighed — memory storage format

**Option A — one markdown file per memory, slug-named** (`squads/agents/memory/<role>/<slug>.md`).
Light frontmatter (title/one-line summary, created_at, optional tags) over a freeform,
agent-owned body.

- Merge: adds are independent files (never conflict); an edit conflicts only when the *same*
  memory is changed on both branches — rare, and exactly the case a human *should* resolve;
  deletes are file removals (merge cleanly). Git's own file-level merge does the right thing —
  no gitattribute dependency.
- Mirrors a pattern already proven in this very repo for Claude's own agent memory (a MEMORY.md
  index + one slug-named file per fact, no global ids, no lifecycle).
- The memory `.md` files stay greppable and human-editable — they are the source of truth;
  `search` is a plain content grep over them, no parsing/folding.

**Option B — one JSONL per role** (`squads/agents/memory/<role>.jsonl`) + a `merge=union`
gitattribute. Append-only with tombstone/retract records for deletion (never edit a line in
place), content-hash/uuid ids, dedup/collapse on read.

- Tighter on disk, trivially appendable.
- But `merge=union` is dumb: it concatenates both sides' added lines, so the same append on two
  branches yields a duplicate line, and an "edit" (a new line superseding an old one) needs the
  tombstone to hide the stale line. If the never-edit-in-place discipline slips, the union merge
  silently keeps both versions. Requires read-time collapse logic and a gitattribute that every
  checkout/tool must honor, or conflict markers / clobbering leak through.

# Options weighed — board storage

The board needs a **light reference id** so `clear <id>` works, and an **expiry** (`--until`).
It does *not* need the item model: a notice has text, author, posted-at, and an optional
until — no status lifecycle, sub-entities, refs, assignee, or workflow machine, and forcing it
through the item model would re-introduce the global-counter collision for a second
high-frequency artifact and drag in lifecycle that does not fit an ephemeral notice.

Its id semantics also differ from memory. A memory is referenced by a stable, meaningful slug
(`show scale-tests-slow`). A board notice is referenced by a small ordinal for a quick clear —
but a persisted monotonic board counter would collide across branches just like the global one.
So the board stores each notice under a **stable content id** (short hash) in its `.md` file, and
presents an **ephemeral positional ordinal** at list time. That ordinal is the notice's position
in the **freshly-computed live listing** — `list_notices` globs the board's `.md` files, drops
the expired ones, and sorts what remains, and `<n>` is the n-th entry in that live listing.
`clear <n>` resolves the n-th entry back to that notice's stable hash id and file. The ordinal is
a display affordance computed at list time, not persisted meaning.

# Decision

**Memory: Option A** — one slug-named markdown file per memory under
`squads/agents/memory/<role-slug>/`, light frontmatter + freeform body. Memory is **addressed by
its stable slug** (`show <slug>`); `list`/`search` read the `.md` files directly (glob +
frontmatter / content grep).

**Board: its own lighter store, not the item model** — one file per notice under
`squads/board/` (short-hash id in frontmatter alongside author / posted-at / `until` / body),
with expiry applied as a read-time filter. The board is **addressed by an ephemeral positional
ordinal** that is the entry's position in the freshly-computed live listing (`list_notices`,
sorted and unexpired, read straight from the `.md` files); `clear <n>` resolves the n-th entry to
the notice's stable hash.

The memory-vs-board difference is purely in *how the CLI addresses entries* — durable slug vs
ephemeral position in the live listing — matching each tier's semantics.

**The content is outside `.squads.json` and outside the global counter.** The memories and notices
are not items; `sq repair` ignores them; there is nothing about them for `.squads.json` to
reconstruct — the cleanest possible answer to driver 3 (rather than indexing them in `.squads.json`,
we keep them out of it altogether). Both use lightweight models of their own (a memory-entry /
board-notice type), *not* the `Item` model, so the "lighter tier" stays honest and no
schema-version / status machinery leaks in.

**The slug/hash-named `.md` files are the sole store — no committed derived index.** There is no
per-folder `.index.jsonl` roll-up, no generator, and nothing to regenerate on add / forget /
`sq sync` / `sq repair`. Every read (`memory list`, `search`, `show`, `board list`) computes what
it needs live from the `.md` files. This is "don't store what you can derive" followed to its
conclusion: a committed roll-up would be derived data kept in sync for readers that can just as
well read the source, and deriving it on read instead eliminates the index's entire merge-conflict
class at the root rather than handling it. (This reverses an earlier revision of this decision,
which committed a `.index.jsonl` roll-up and accepted a residual merge conflict on it — see the
discussion history.)

Rationale for A over B: A already satisfies driver 1 (slug filenames, no counter) exactly as B
does, but its merge behavior is both simpler and *more correct* — file-per-fact lets git resolve
adds/deletes automatically and turns a genuine concurrent same-fact edit into an honest,
human-resolved conflict, whereas B converts that same case into a silent duplicate or stale line
that read-time dedup must paper over. A carries no gitattribute dependency, and its `.md` content
files stay greppable and hand-editable as the source of truth, consistent with the repo's
"markdown + frontmatter is the source of truth" ethos and with the in-repo precedent for Claude's
own memory. B's only wins (disk tidiness, append ergonomics) do not outweigh its
tombstone-discipline footgun for a high-frequency, multi-writer, committed store. The board reuses
the same file-per-entry idiom for one storage mental model across both lighter tiers.

# Design notes (level, not full spec)

- **Content files are freeform / marker-free.** Markers exist to protect *regenerated* regions
  from agent edits; a memory or notice body is 100% agent/author-owned with nothing regenerated
  inside it, so it carries no `sq:` markers — only light frontmatter for listing and search.
  The `.md` content files remain the source of truth and stay greppable/hand-editable. There is
  no generated artifact alongside them — the folder holds only the `.md` files.

- **Surfacing is pull-at-startup, not push-into-managed-files.** The role sheet instructs every
  agent, at the start of a run, to run `sq memory <its-slug> list` and `sq board list` and apply
  anything relevant. Nothing is injected into the pointer / managed `CLAUDE.md` / `AGENTS.md`
  regions. The instruction is always valid — an empty pool or board simply lists nothing — so it
  never dangles on a fresh install, and the agent always sees live content rather than a
  `sq sync`-time snapshot. Memory/board content therefore stays out of the managed files entirely:
  nothing is duplicated and nothing can go stale. Consistent with pull-with-a-nudge — the role
  sheet is the nudge, and the `sq` list is the live pull.

- **Expiry hides; clear/prune deletes.** Expired notices are filtered out of listings at read
  time; physical removal happens on an explicit `clear`/prune, never as a side effect of a read
  (a read must not mutate git-tracked files and manufacture spurious diffs).

# Consequences & trade-offs

- **Two new id namespaces, both off the global counter** (memory: stable meaningful slug;
  board: stable hash, addressed as a position in the live listing). Deliberate: not everything in
  the system carries a counter-allocated, globally-unique id anymore. The conceptual cost of a
  second/third id scheme is accepted in exchange for escaping the counter-collision pain that is
  the entire premise of the lighter tier.
- **Merge correctness vs disk tidiness.** File-per-entry makes git the merge engine and surfaces
  concurrent same-fact edits as honest conflicts, at the cost of many small files and a `forget`
  being a real file deletion (history retained in git log). B would be tighter on disk but needs
  tombstone discipline and read-time dedup and silently duplicates when that discipline slips.
- **No derived-index merge surface.** Because nothing derived is committed, there is nothing
  derived to conflict on. The `.md` content files carry the whole merge story and merge cleanly:
  adds are independent files, deletes are file removals, and only a genuine concurrent same-fact
  edit conflicts — the one case a human should resolve. An earlier revision of this decision
  committed a `.index.jsonl` roll-up and accepted a residual conflict on it whenever two branches
  each added a distinct memory; dropping the index removes that surface entirely, along with the
  merge-handling it required.
- **Driver 1 fully satisfied.** Driver 1 built this lighter tier to escape the counter-collision
  merge pain of items, and that pain is gone: ids are human-meaningful slugs/hashes with no shared
  global counter, so the content files never collide on filename or counter and no `renumber`
  cleanup is ever needed. With no committed roll-up there is no residual derived-index conflict
  either — the `.md` files are the sole store and merge cleanly, so nothing derived needs
  reconciling.
- **Positional board clear has a mild list-then-act gap** — `clear <n>` resolves against the
  n-th entry of the current live listing (`list_notices`, sorted and unexpired, computed fresh from
  the `.md` files), so a concurrent post/clear/expiry between `list` and `clear` can shift
  positions; acceptable for a low-frequency, effectively single-writer board, and worth stating
  that resolution is against the live listing at the moment `clear` runs. Memory sidesteps this
  entirely by being slug-addressed, so its recall is stable across merges.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-13T08:49:13Z] Pierre Chat:
  - Change the index design: instead of a generated INDEX.md markdown digest, use a per-folder JSONL index file named `.index.json` with a standard schema — each line/entry carries {slug, filename, short description}. Each memory stays a `.md` file holding the memory prose. Apply the same index model to the board (`.index.json` in squads/board/). @architect please revise the decision accordingly.
- [2026-07-13T08:50:25Z] Pierre Chat:
  - Format refinement: use extension `.index.jsonl` (JSON Lines, one entry per line). The line position in the index file IS the ordinal <n> passed to the CLI (e.g. board `clear <n>` = the n-th line). @architect reconcile with the memory-slug vs board-ordinal addressing in the current draft.
- [2026-07-13T08:53:59Z] Robert Architect:
  - Revised per @op-pierre's directive + the format refinement: the generated index is now a per-folder `.index.jsonl` (JSON Lines, one object per line) replacing the `INDEX.md` markdown digest, identical format for memory and board. Memories/notices stay slug-named `.md` files (Option A unchanged) — the source of truth, greppable/hand-editable; the index is a regenerated-whole roll-up rebuilt from them (NOT a resurrection of the rejected Option-B content store).
  - Entry schema per line: {slug, filename, description}. First line is a header record {schema: "squads.index/1", generated: "<stamp>"}; the `generated` field is the JSON-native honoring of invariant #7 (a JSONL file can't carry an HTML sq: marker). Format version is its own tag, decoupled from item SCHEMA_VERSION.
  - Addressing reconciled: board is line-positional — `clear <n>` = the n-th ENTRY line of squads/board/.index.jsonl (header excluded), generator owns the line<->ordinal mapping. Memory stays slug-addressed (`show <slug>`); line position is not load-bearing for recall, so it survives regeneration/merge — the right call for a durable notebook vs the board's ephemeral ordinal. No real tension: one shared format, addressing differs by tier semantics. One wrinkle for your eye: the #7 header line offsets raw file line numbers by one, so 'position = ordinal' holds for entry lines specifically — flagging in case you'd prefer a headerless index + sibling stamp instead. Kept Proposed.
- [2026-07-13T09:08:12Z] Pierre Chat:
  - Header decision: keep the inline header line ({schema, generated-stamp}) as the first line of `.index.jsonl` — one self-describing file per folder. The board ordinal counts entry lines (header excluded), so entry line n = clear <n>; the raw-line +1 offset is CLI-internal and invisible to users. ADR-314 design is settled — approved to accept.
- [2026-07-13T09:08:35Z] Robert Architect:
  - Accepted per @op-pierre's approval. Design settled across two refinements: index is a per-folder generated `.index.jsonl` (JSON Lines) with entry schema {slug, filename, description}; memory stays slug-addressed, board ordinal = entry-line position (inline header excluded); generated-file contract honored via the header's schema+generated stamp.
- [2026-07-15T09:26:39Z] Robert Architect:
  - Amended per REV-412 (findings F1/F2) and @op-pierre's option-B decision — a correction to this accepted ADR, not a re-proposal (status stays Accepted).
  - F1 (index conflicts on distinct concurrent adds): the .index.jsonl is now framed as a COMMITTED, rebuildable derived index — same posture as .squads.json (committed for convenience, .md frontmatter is source of truth), differing only in being per-folder and outside the global counter. Consequences now state plainly that two branches each adding a distinct memory DO conflict on the committed roll-up; the .md files still merge cleanly (no memory lost); resolution is mechanical — re-run sq sync/repair to regenerate. Explicitly NOT a merge-driver (union-merge stays rejected).
  - F2 (phantom 'edit' trigger + false sync claim): corrected the GENERATED_STAMP wording to 'regenerated by sq on add/forget and sq sync — do not hand-edit' (dropped 'edit' — there is no in-place edit path) and stated the stamp must name only real triggers. The generated-artifact bullet now says the add/forget path AND sq sync regenerate the index.
  - Reconciled with driver 1: the counter-collision pain is still gone (meaningful slug/hash ids, no shared counter, no renumber cleanup); what remains is a conflict on a derived, one-command-rebuildable index — a strictly smaller, qualitatively different problem — accepted in exchange for a committed, inspectable roll-up on fresh checkout. Trade is named, not claimed away.
  - Wiring sq sync to actually regenerate the memory AND board indexes, fixing the stamp string, and the merge test follow separately (tech-lead: TASK-406 et al.); this amendment is the ADR record only.
- [2026-07-15T12:36:47Z] Robert Architect:
  - Amended per REV-419 (findings F1/F2/F3, op-pierre-directed) — a correction to this accepted ADR, not a re-proposal (status stays Accepted). This REVERSES the earlier option-B / committed-index amendment recorded above.
  - Dropped the .index.jsonl entirely: no committed roll-up, no generator (_content_index.py), no add/forget/sync/repair regeneration. The slug-named memory .md files (agents/memory/<role>/) and hash-named board .md files (board/) are now the SOLE store — unchanged, off the global counter, outside .squads.json. This retracts the committed-derived-index decision and, with it, the merge-conflict trade-off and the BUG-414 fix that only existed to serve the index.
  - Retrieval is pull, direct from the .md files: sq memory <role> list/search/show and sq board list/clear already read the .md files (they never used the index). Reframed the board ordinal — <n> is the position in the freshly-computed live listing (list_notices, sorted+unexpired from the .md files), not a file line.
  - Surfacing is pull-at-startup, NOT push-into-managed-files: removed the boot-surfacing-through-the-backend design (no injection into the pointer / CLAUDE.md / AGENTS.md). Replaced with: the role sheet tells every agent to run 'sq memory <its-slug> list' and 'sq board list' at the start of a run and apply anything relevant — always fresh, works when empty, nothing duplicated into managed files, nothing to go stale.
  - Why: the index and the push-surfacing were coupled — the index's only reader was the boot-surfacing (read_index -> _memory_surface), so removing surfacing left the index readerless. Pulling at startup is simpler, always current, and kills the index merge-conflict class at the root. 'Don't store what you can derive' followed to its conclusion.
  - Revised sections: Context, Options-weighed (memory + board), Decision, Design notes (deleted the generated-artifact/.index.jsonl/#7-stamp bullet — there's no generated file now; rewrote the boot-surfacing note to pull-at-startup), Consequences (dropped the committed-index merge-conflict + committed-surface bullets; added that pull-at-startup + no roll-up removes that whole surface).
  - @product-owner FEAT-315 US2 / FEAT-317 US2 change from push-into-managed-files to pull-at-startup; @tech-lead the fix-tasks (drop _content_index.py + _memory_surface/_board_surface, the sync/repair regen pass, the pointer/section blocks, rewrite role.md.j2 to the pull directive) follow from here. Code/features/tasks untouched by this amendment — ADR record only.
<!-- sq:discussion:end -->
