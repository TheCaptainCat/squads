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
updated_at: '2026-07-13T09:08:35Z'
---
<!-- sq:body -->
# Context

Two complementary, lighter-than-item artifacts are being added to a squad:

- **Agent memory** — a per-role, committed notebook of small, agent-authored, *descriptive*
  facts ("what I learned"). Each role owns its own pool (scoped by ownership, not tagging).
  Being committed to the repo is the whole point: a fresh checkout or a new teammate's agent
  inherits the accumulated per-role memory — so it must merge cleanly across branches and
  across multiple concurrent devs. Retrieval is pull-with-a-nudge: a per-role **index**
  (`.index.jsonl`, one line per memory) is surfaced at role-boot, full content fetched on demand.
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
   (`roles/`, `skills/`), so memory nests there: `squads/agents/memory/<role-slug>/` with a
   per-role index. The board is team-scoped, so it is its own top-level folder, sibling to the
   item-type folders: `squads/board/`.
3. **The index invariant must stay clean.** `.squads.json` is a rebuildable index of
   counter-allocated items that `sq repair` reconstructs from item frontmatter. Nothing about
   these lighter tiers may weaken that guarantee.

# Options weighed — memory storage format

**Option A — one markdown file per memory, slug-named** (`squads/agents/memory/<role>/<slug>.md`),
plus a generated per-folder `.index.jsonl` roll-up. Light frontmatter (title/one-line summary,
created_at, optional tags) over a freeform, agent-owned body.

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

(Note: choosing JSONL for the *derived index* below does **not** resurrect Option B. Option B
proposed JSONL as the **content store** — an append-only, hand/merge-edited log of facts, which
is where the tombstone/merge-union hazards live. The Option-A index is a **regenerated-whole**
roll-up rebuilt from the `.md` files; it is never appended in place, never hand-edited, and never
the merge battleground, so none of B's hazards apply to it.)

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
presents an **ephemeral positional ordinal** at list time. That ordinal is made concrete by the
generated index: it is the **line position of the notice's entry in `squads/board/.index.jsonl`**,
generated in the same sorted, unexpired order the CLI lists in. `clear <n>` resolves the n-th
entry line back to that notice's stable hash id and file. The ordinal is a display affordance
derived from the generated index, not persisted meaning.

# Decision

**Memory: Option A** — one slug-named markdown file per memory under
`squads/agents/memory/<role-slug>/`, light frontmatter + freeform body, with a generated
per-role `.index.jsonl` roll-up. Memory is **addressed by its stable slug**
(`show <slug>`); line position in the index is not load-bearing for recall.

**Board: its own lighter store, not the item model** — one file per notice under
`squads/board/` (short-hash id in frontmatter alongside author / posted-at / `until` / body),
with a generated `squads/board/.index.jsonl` roll-up, and expiry applied as a read-time filter.
The board is **addressed by an ephemeral positional ordinal** that *is* the entry's line position
in that generated index; `clear <n>` resolves the n-th line to the notice's stable hash.

Both indexes use the **identical `.index.jsonl` format** (see Design notes) for one storage mental
model; the memory-vs-board difference is purely in *how the CLI addresses entries* (durable slug
vs ephemeral line-ordinal), matching each tier's semantics, not a divergence in the file format.

**Both live entirely outside `.squads.json` and outside the global counter.** They are not
items; `sq repair` ignores them; there is nothing about them for the index to reconstruct — which
is the cleanest possible answer to driver 3 (rather than indexing them and making them
rebuildable, we keep them out of the index altogether). Both use lightweight models of their own
(a memory-entry / board-notice type), *not* the `Item` model, so the "lighter tier" stays honest
and no schema-version / status machinery leaks in.

Rationale for A over B: A already satisfies driver 1 (slug filenames, no counter) exactly as B
does, but its merge behavior is both simpler and *more correct* — file-per-fact lets git resolve
adds/deletes automatically and turns a genuine concurrent same-fact edit into an honest,
human-resolved conflict, whereas B converts that same case into a silent duplicate or stale line
that read-time dedup must paper over. A carries no gitattribute dependency, and its `.md` content
files stay greppable and hand-editable as the source of truth, consistent with the repo's
"markdown + frontmatter is the source of truth" ethos and with the in-repo precedent for Claude's
own memory. B's only wins (disk tidiness, append ergonomics) do not outweigh its
tombstone-discipline footgun for a high-frequency, multi-writer, committed store. The board reuses
the same file-per-entry idiom, and the same generated `.index.jsonl`, for one storage mental model
across both lighter tiers.

# Design notes (level, not full spec)

- **Content files are freeform / marker-free.** Markers exist to protect *regenerated* regions
  from agent edits; a memory or notice body is 100% agent/author-owned with nothing regenerated
  inside it, so it carries no `sq:` markers — only light frontmatter for the roll-up and search.
  The `.md` content files remain the source of truth and stay greppable/hand-editable.

- **The generated artifact is the per-folder `.index.jsonl`.** Every folder that holds content
  files — each `squads/agents/memory/<role>/` and `squads/board/` — carries one `.index.jsonl`,
  a machine-readable roll-up regenerated *whole* from that folder's `.md` files on every
  add/forget/edit and on `sq sync` (mirroring how the sub-entity summary roll-up is re-rendered on
  every mutation). One identical format serves both tiers.

  - **Format: JSON Lines (`.index.jsonl`) — one JSON object per line.** Chosen over a single
    JSON array/object because (a) the file is regenerated whole and streamed line-by-line, so a
    line is a natural unit; (b) it lets **line position carry meaning** — the board's positional
    ordinal `<n>` is literally the n-th entry line — which a nested array would not express as
    directly; and (c) it stays diff-friendly (one entry changes one line). This is *not* the
    rejected Option-B content store: the index is rebuilt from the `.md` files, never appended or
    merged in place, so JSONL's append/merge hazards do not apply here.

  - **Entry schema (per line):** `{"slug": "...", "filename": "...", "description": "..."}`.
    For memory, `slug` is the memory slug and `filename` its `<slug>.md`. For the board, the same
    `slug` field carries the notice's stable short-hash id and `filename` its notice file — one
    schema covers both. `description` is the one-line summary drawn from the content file's
    frontmatter.

  - **Header + format version.** The **first line** is a header record,
    `{"schema": "squads.index/1", "generated": "<stamp>"}`, distinct from the entry records that
    follow. `schema` is a format tag with its own small version (`/1`), independent of the item
    `SCHEMA_VERSION` and its migration chain, since these tiers sit outside `.squads.json`. The
    board's positional ordinal counts **entry** lines (header excluded): entry line *n* is
    ordinal *n*, a mapping the generator owns because it writes the file and the `list` output in
    the same ordered pass.

  - **Generated-file contract for JSON (invariant #7).** A JSONL file cannot carry the HTML
    `<!-- sq:... -->` marker the managed-region wrapper stamps on markdown, so the contract is
    honored by a JSON-native equivalent: the header line's `generated` field is a plain-text
    stamp ("regenerated by `sq` on add/forget/edit and `sq sync` — do not hand-edit") that plays
    the role the managed-region warning plays in `CLAUDE.md`/`AGENTS.md`. The file is regenerable
    and never migrated; the `schema` + `generated` header makes that visible in place, satisfying
    #7 without a marker comment. Backends surface these indexes; the index-writer is
    backend-neutral, the same way `_managed_region.py` is.

- **Boot surfacing goes through the backend, not hard-coded.** At role-boot the agent's own
  memory `.index.jsonl` and the current board notices are surfaced into its context — the Claude
  Code backend includes them in its pointer / managed CLAUDE.md region; an AGENTS.md backend does
  the equivalent — so the pluggable-backend invariant holds. Consistent with pull-with-a-nudge:
  memory surfaces the *index* and fetches content on recall (potentially large, descriptive);
  the board, being short and prescriptive, can surface content directly — with `--until` expiry
  doing real load-bearing work to keep that boot payload bounded, not just tidiness.

- **Expiry hides; clear/prune deletes.** Expired notices are filtered out of listings and boot
  surfacing at read time; physical removal happens on an explicit `clear`/prune, never as a
  side effect of a read (a read must not mutate git-tracked files and manufacture spurious diffs).

# Consequences & trade-offs

- **Two new id namespaces, both off the global counter** (memory: stable meaningful slug;
  board: stable hash, addressed as a line-positional ordinal in the generated `.index.jsonl`).
  Deliberate: not everything in the system carries a counter-allocated, globally-unique id
  anymore. The conceptual cost of a second/third id scheme is accepted in exchange for escaping
  the counter-collision pain that is the entire premise of the lighter tier.
- **Merge correctness vs disk tidiness.** File-per-entry makes git the merge engine and surfaces
  concurrent same-fact edits as honest conflicts, at the cost of many small files and a `forget`
  being a real file deletion (history retained in git log). B would be tighter on disk but needs
  tombstone discipline and read-time dedup and silently duplicates when that discipline slips.
- **A new generated-artifact surface.** Keeping memory/board out of `.squads.json` gives a clean
  invariant story (nothing for `sq repair` to rebuild), but each folder's `.index.jsonl` becomes a
  derived file that the mutation path and `sq sync` must keep fresh and stamped — a second
  regeneration surface to keep honest, separate from the index. Because it is derived, a merge
  conflict on an `.index.jsonl` is resolved by **regeneration** (`sq sync`), never by hand — the
  `.md` files remain the merge battleground and source of truth.
- **Positional board clear has a mild list-then-act gap** — `clear <n>` resolves against the
  n-th entry line of the current `squads/board/.index.jsonl` (the live sorted, unexpired listing),
  so a concurrent post/clear/expiry that regenerates the index between `list` and `clear` can
  shift positions; acceptable for a low-frequency, effectively single-writer board, and worth
  stating that resolution is against the live index at the moment `clear` runs. Memory sidesteps
  this entirely by being slug-addressed, so its recall is stable across regeneration and merges.
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
<!-- sq:discussion:end -->
