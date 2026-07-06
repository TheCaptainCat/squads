---
id: ADR-314
sequence_id: 314
type: decision
title: Storage & id model for agent memory and the team bulletin board
status: Proposed
author: architect
description: Slug-file-per-memory + own lighter board store, both off the global counter
  and outside .squads.json
created_at: '2026-07-06T16:03:50Z'
updated_at: '2026-07-06T16:03:50Z'
---
<!-- sq:body -->
# Context

Two complementary, lighter-than-item artifacts are being added to a squad:

- **Agent memory** — a per-role, committed notebook of small, agent-authored, *descriptive*
  facts ("what I learned"). Each role owns its own pool (scoped by ownership, not tagging).
  Being committed to the repo is the whole point: a fresh checkout or a new teammate's agent
  inherits the accumulated per-role memory — so it must merge cleanly across branches and
  across multiple concurrent devs. Retrieval is pull-with-a-nudge: a per-role **index** is
  surfaced at role-boot (one line per memory), full content fetched on demand.
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
plus a generated per-role `INDEX.md`. Light frontmatter (title/one-line summary, created_at,
optional tags) over a freeform, agent-owned body.

- Merge: adds are independent files (never conflict); an edit conflicts only when the *same*
  memory is changed on both branches — rare, and exactly the case a human *should* resolve;
  deletes are file removals (merge cleanly). Git's own file-level merge does the right thing —
  no gitattribute dependency.
- Mirrors a pattern already proven in this very repo for Claude's own agent memory (a MEMORY.md
  index + one slug-named file per fact, no global ids, no lifecycle).
- Greppable and human-editable; `search` is a plain content grep, no parsing/folding.

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
So the board stores each notice under a **stable content id** (short hash) and presents an
**ephemeral positional ordinal** at list time; `clear <n>` resolves the n-th currently-listed
(unexpired, sorted) notice to its stable id. The ordinal is a display affordance, not persisted
meaning.

# Decision

**Memory: Option A** — one slug-named markdown file per memory under
`squads/agents/memory/<role-slug>/`, light frontmatter + freeform body, with a generated
per-role `INDEX.md`.

**Board: its own lighter store, not the item model** — one file per notice under
`squads/board/` (short-hash id in frontmatter alongside author / posted-at / `until` / body),
listed and cleared by an ephemeral positional ordinal, with expiry applied as a read-time filter.

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
that read-time dedup must paper over. A carries no gitattribute dependency and stays greppable
and hand-editable, consistent with the repo's "markdown + frontmatter is the source of truth"
ethos and with the in-repo precedent for Claude's own memory. B's only wins (disk tidiness,
append ergonomics) do not outweigh its tombstone-discipline footgun for a high-frequency,
multi-writer, committed store. The board reuses the same file-per-entry idiom for one storage
mental model across both lighter tiers.

# Design notes (level, not full spec)

- **Content files are freeform / marker-free.** Markers exist to protect *regenerated* regions
  from agent edits; a memory or notice body is 100% agent/author-owned with nothing regenerated
  inside it, so it carries no `sq:` markers — only light frontmatter for the roll-up and search.
- **The derived digests are the generated artifacts.** The per-role `INDEX.md` (one line per
  memory) is regenerated from that role's files on every add/forget/edit and on `sq sync`,
  mirroring how the sub-entity summary roll-up is re-rendered on every mutation. The board digest
  (current unexpired notices) is generated the same way. Both carry the "regenerated by `sq`"
  managed-region stamp so an agent editing them in-session knows they will be overwritten. This
  introduces a new class of generated file distinct from `.squads.json`, kept fresh by the
  mutation path and by sync.
- **Boot surfacing goes through the backend, not hard-coded.** At role-boot the agent's own
  memory index and the team board digest are surfaced into its context — the Claude Code backend
  includes them in its pointer / managed CLAUDE.md region; an AGENTS.md backend does the
  equivalent — so the pluggable-backend invariant holds. Consistent with pull-with-a-nudge:
  memory surfaces the *index* and fetches content on recall (potentially large, descriptive);
  the board, being short and prescriptive, can surface content directly — with `--until` expiry
  doing real load-bearing work to keep that boot payload bounded, not just tidiness.
- **Expiry hides; clear/prune deletes.** Expired notices are filtered out of listings and boot
  surfacing at read time; physical removal happens on an explicit `clear`/prune, never as a
  side effect of a read (a read must not mutate git-tracked files and manufacture spurious diffs).

# Consequences & trade-offs

- **Two new id namespaces, both off the global counter** (memory: stable meaningful slug;
  board: stable hash shown as an ephemeral positional ordinal). Deliberate: not everything in
  the system carries a counter-allocated, globally-unique id anymore. The conceptual cost of a
  second/third id scheme is accepted in exchange for escaping the counter-collision pain that is
  the entire premise of the lighter tier.
- **Merge correctness vs disk tidiness.** File-per-entry makes git the merge engine and surfaces
  concurrent same-fact edits as honest conflicts, at the cost of many small files and a `forget`
  being a real file deletion (history retained in git log). B would be tighter on disk but needs
  tombstone discipline and read-time dedup and silently duplicates when that discipline slips.
- **A new generated-artifact surface.** Keeping memory/board out of `.squads.json` gives a clean
  invariant story (nothing for `sq repair` to rebuild), but the per-role INDEX and board digest
  become derived files that the mutation path and `sq sync` must keep fresh and stamped — a second
  regeneration surface to keep honest, separate from the index.
- **Positional board clear has a mild list-then-act gap** — `clear <n>` resolves against the
  current sorted, unexpired listing, so a concurrent change can shift positions; acceptable for a
  low-frequency, effectively single-writer board, and worth stating that resolution is against the
  live listing.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
