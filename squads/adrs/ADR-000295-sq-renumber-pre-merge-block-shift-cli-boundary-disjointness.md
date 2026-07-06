---
id: ADR-295
sequence_id: 295
type: decision
title: 'sq renumber pre-merge block-shift: CLI, boundary, disjointness, reflog'
status: Accepted
author: architect
refs:
- ADR-72
- ADR-117
- ADR-282
- FEAT-288
created_at: '2026-07-05T21:01:35Z'
updated_at: '2026-07-06T07:14:09Z'
---
<!-- sq:body -->
## Context

`squads` allocates IDs from a **single global monotonic counter** (ADR-72): `allocate_id` bumps
one `counter` inside `IndexStore.transaction()` and the number is globally unique. When two
collaborators diverge on separate git branches or clones, each branch bumps its own copy of that
counter, so both mint the same next number (both branch at `287` → both create item `288`). On
merge the tree holds two files claiming the same ID.

Today the only remedy is **post-merge** `sq repair --renumber`
(`src/squads/_services/_maintenance.py::_renumber`, line 601, planned by `_renumber_plan`, line
570). It scans for number collisions, mints fresh numbers for the losers, and drives
`_itemfile.py::rewrite_ids` (line 45) — a whole-word `\bOLD\b → NEW` substitution — across
frontmatter `id:`/refs and body prose, then renames files and resyncs `sequence_id`. It guarantees
uniqueness and no dangling refs, but its remap is **keyed by the shared old-ID string**: because
both collided items are literally `FEAT-000288`, `rewrite_ids` cannot tell which references meant
which item, and repoints **every** reference to the one renamed winner. Uniqueness is restored;
**referential intent is lost.**

FEAT-288 proposes the missing **pre-merge** path: on the branch that will yield, while every
reference is still unambiguous (the second `FEAT-288` does not yet exist in this tree), block-shift
this branch's newly-created IDs into a contiguous range reserved **above** the other branch's
counter. Intent is preserved because the rewrite happens *before* the ambiguity exists. FEAT-283
(Done, ADR-282) already unpadded display/refs/prose, so the prose rewrite is now a plain
whole-word integer swap with no leading-zero trap; padding survives only at the filename-rename
seam.

Five choices are not mechanical and must be ratified before implementation, because `sq renumber`
is a **new public CLI verb entering the frozen 1.0 grammar**, it operates on the identity system,
and it collides with two Accepted ADRs — ADR-72 (the global counter) and ADR-117 (the append-only,
not-a-source-of-truth reflog).

**Verified ground truth used below:** sq has **zero git dependency today** — a grep of `src/` for
`subprocess`/`import git`/`os.system` finds only prose mentions of `git` in templates and comments,
never an invocation. The reflog (`src/squads/_index/_reflog.py`) stores the affected item ID in
`target` (line 77) and, for `ref`/`link` ops, IDs *inside* `delta` too (e.g.
`_services/_refs.py:306` logs `{"add": to_id, "kind": kind}`; `_services/_items.py:159` logs link
endpoints). ADR-117 fixes the reflog as append-only (one `O_APPEND` newline-terminated line per op)
and **explicitly not a source of truth** — `sq repair` never reads it and a missing/truncated
reflog is never an error.

## Decision

### 1. CLI surface — a standalone `sq renumber`, not a mode of `sq repair`

`sq renumber` is its own top-level verb:

```
sq renumber --from <N> --onto <M>        # recommended: auto-computed minimal safe offset
sq renumber --from <N> --by <n>          # escape hatch: explicit offset, validated
```

- `--from <N>` (**required**): the lowest **branch-local** sequence number, inclusive. Items with
  `sequence_id >= N` are the block to shift. The operator derives it as `base_counter + 1` (the
  counter at the branch/merge-base point).
- `--onto <M>`: the **other branch's counter** (its high-water mark at merge time). sq computes the
  minimal offset that lands the whole block strictly above the merged tree's ranges (§3). This is
  the recommended form.
- `--by <n>`: an explicit offset (`seq → seq + n`). Mutually exclusive with `--onto`. sq validates
  what it can and refuses an unsafe value (§3); it cannot certify merge-disjointness without `M`
  and says so.

It is **not** folded into `sq repair`. `repair` is an idempotent, argument-free reconstruction of
the index from frontmatter (Invariant 1) whose `--renumber` is a *post-hoc collision fixer needing
no operator input*. `renumber` is the opposite risk profile: an intentional, operator-parameterized
identity transform with a **required boundary** that only the operator knows. Different mental
model, different argument shape, different blast radius — they stay distinct verbs even though they
share the executor (§5).

### 2. Boundary derivation — sq stays git-agnostic; the operator supplies integers

**sq does not take on a git dependency.** The boundary (`--from`) and the landing target
(`--onto`) cross into sq only as **plain integers**. sq does not shell out to git, does not read
`.squads.json` from another ref, and does not compute `merge-base`.

Rationale, treated as the architectural boundary Olivia flagged: sq has *no* subprocess/git call in
`src/` today, and its contract is "operates on a folder of markdown + a JSON index." A merge-base
derivation would add an implicit runtime dependency on a git binary **and** on being inside a git
work tree, couple the identity core to one VCS, and break the test model (every test runs in a bare
`tmp_path` with no repo). The convenience of auto-deriving the counter does not justify that
coupling for a command an operator runs deliberately, once, at merge time.

The operator reads the other branch's counter **outside sq** and passes it in — the documented
recipe is:

```
git show <mainref>:squads/.squads.json | jq .counter     # → the value for --onto
```

If a git-assisted convenience is ever wanted, it must be an **isolated, optional** layer: a thin
helper behind an explicit opt-in flag (e.g. a future `--from-merge-base <ref>`) that merely
*computes the integers* and feeds this same core, degrades gracefully when git is absent, and lives
outside the `_index`/`_services` identity path. The core never assumes git. Git is a convenience,
**never a requirement.**

### 3. Disjoint-block guarantee — auto-compute the minimal safe offset; refuse when unsafe

Let `C` be **this branch's own counter** (sq reads it from the index — the max local
`sequence_id`). Two ranges could collide with the shifted block in the merged tree: the other
branch's `[N .. M]` and, for substitution safety, this branch's *own* old local range `[N .. C]`.
The shift maps `seq → seq + delta` for every local item (`seq >= N`), preserving relative order and
gaps.

- **With `--onto M`:** `delta = max(M, C) + 1 - N`, so the block lands at `max(M, C) + 1` — strictly
  above **both** the other branch's counter *and* this branch's own maximum. This is always
  computable and always safe; sq never emits an unsafe offset on this path.
- **With `--by n`:** sq validates `N + n > C` (new block strictly above this branch's own max). If
  it fails, sq **refuses** with `SquadsError` (exit 1, no files touched) and reports the minimum
  safe offset. It additionally warns that, without `--onto`, it cannot certify the block clears the
  *other* branch's counter — that guarantee is the operator's on this path.

**Refuse, never silently auto-fix a too-small `--by`.** Auto-computation happens only where the
operator asked for it (`--onto`).

Why a guaranteed-disjoint block makes the single-pass substitution safe: because the new range is
strictly above the old local range, **no new ID string equals any old ID string in the remap.**
`rewrite_ids`' successive `\bOLD\b → NEW` edits therefore cannot chain — no substitution's output
re-matches a later substitution's input — so iteration order over the remap is irrelevant. The
high-to-low ordering an *in-place* (overlapping) shift would require is unnecessary here precisely
because we forbid overlap. Filenames still reformat at the **filename width** via
`format_item_id(prefix, seq, db.padding)` while frontmatter/refs/prose take the unpadded
`DISPLAY_ID_PADDING` form (ADR-282) — the same padded-disk / unpadded-content split `_renumber_plan`
already threads (lines 594–597).

### 4. Reflog — leave historical lines literal; append one `renumber` event. No in-place rewrite.

The reflog's historical `target`/`delta` ID fields are **not rewritten**. Instead the renumber
transaction appends a single `renumber` op line whose `delta` records the shift — the range and the
`{old → new}` remap (e.g. `{"from": N, "onto": M, "by": delta, "remap": {...}}`, a compact summary,
consistent with ADR-117 §4's "summary, not a replayable diff").

Reconciliation with ADR-117/114, stated explicitly because this is the sharp one:

- The reflog is **append-only and explicitly not a source of truth.** In-place rewrite of historical
  lines violates that contract head-on: it would rewrite the whole file (breaking the "one op = one
  `O_APPEND` newline-terminated line" atomicity model), and it would make the history **lie** — an
  event that at time *T* genuinely referenced `FEAT-210` would be retroactively fabricated to say it
  referenced `FEAT-220`. ADR-117's load-bearing principle is *"never make the history lie"* (it is
  why the append is ordered strictly after the index commit). That same principle forbids editing
  `target` after the fact.
- The feature's worry — "history stops resolving" — is answered without rewriting: because identity
  is the integer `sequence_id` and the reflog is **not** authoritative, an old line naming a
  pre-shift *formatted* ID is a truthful record of the ID *as it existed then*, not a dangling
  pointer that corrupts state. The appended `renumber` event is the **bridge**: a forensic reader
  (or `sq reflog`'s best-effort resolver) walking the log sees "block `[N..X]` shifted by `delta`"
  and can map any earlier reference forward to the live item. Resolvability is preserved; honesty is
  preserved; the append-only contract is preserved.
- The **git-filter-branch analogy is rejected.** filter-branch rewrites history *because in git the
  commit graph IS the source of truth.* Here the reflog is explicitly *not* the source of truth, so
  the analogy inverts. The correct analogy is git's **own reflog**, which is append-only and is
  never rewritten by filter-branch — exactly the posture adopted here.

The **source-of-truth surfaces are still fully rewritten** — frontmatter `id:`/refs, body prose,
inline mentions, filenames, `sequence_id`, and the counter — because those must stay internally
consistent (Invariant 1). The reflog is the single non-authoritative, append-only stream, and it is
the single thing left literal. That is a clean, principled line, not an omission.

The new `renumber` op joins the reflog op vocabulary; its delta shape is a **FEAT-13 deferral**
touchpoint (FEAT-13 owns the frozen reflog-schema tier per ADR-117 §4).

### 5. Coexistence with `repair --renumber` — complementary, shared executor

The two are documented as a **pair, not a replacement**:

- **`sq renumber` (pre-merge) is the preferred path** when the operator controls the yielding branch
  before merge. It preserves referential intent because it runs while refs are unambiguous.
- **`sq repair --renumber` (post-merge) remains the "too late, make it valid" fallback** for
  collisions that already landed. It guarantees uniqueness and no dangling refs but *cannot* preserve
  intent (its remap is keyed by the shared old-ID string).

They **share the core executor.** Both produce a `{old → new}` remap and drive the identical
apply-path: `rewrite_ids` over all files → file rename at filename padding → `sequence_id` resync →
counter bump. Implementation should **extract that apply-path** from `_renumber` (lines 610–625) so
both verbs call one executor. What differs is only the *planner* feeding the remap: `repair
--renumber` uses `_renumber_plan`'s collision detection; `sq renumber` uses the offset planner of §3.
`sq renumber` additionally (a) bumps the counter to the new max and (b) appends the `renumber` reflog
event of §4.

## Consequences

- **A new 1.0-grammar verb.** `sq renumber --from/--onto/--by` enters the frozen CLI surface
  deliberately. It owes FEAT-13 (stability-contract capstone) a deferral note — both the verb's
  grammar and the new `renumber` reflog op/delta shape.
- **sq stays a markdown-folder tool.** No git binary, no work-tree assumption, no new runtime
  dependency; the test model (bare `tmp_path`) is unaffected. The one-liner recipe lives in help/docs.
- **Single-pass `rewrite_ids` is provably safe here** because the offset planner forbids old/new
  range overlap; no high-to-low ordering machinery is needed. An unsafe `--by` is refused, not
  silently corrected.
- **The reflog stays append-only and honest.** Old lines keep their pre-shift IDs (truthful history);
  one appended event lets readers follow the shift forward. Invariant 1 is untouched — nothing about
  the index now depends on the reflog.
- **Referential intent is preserved on the preferred path** and the lossy post-merge fallback is
  retained for collisions that slipped through; both share one executor, so the machinery does not
  fork.
- **Trade-off accepted:** the operator must supply two integers (and read the other branch's counter
  by hand). We take that small manual step over embedding git in the identity core. A git-assisted
  convenience remains open as a strictly optional, isolated future addition.

## Alternatives considered

- **Fold renumber into `sq repair --renumber` as a flagged mode.** Rejected: opposite risk profiles
  and argument shapes; a required operator-supplied boundary does not belong on the idempotent,
  argument-free repair verb. They share the executor internally instead.
- **Derive the boundary from `git merge-base` inside sq.** Rejected in §2: it crosses sq's
  no-git-dependency boundary for a deliberate, once-per-merge command. Left open only as an isolated,
  optional, gracefully-degrading future layer that feeds the same integer core.
- **In-place rewrite of reflog `target`/`delta` (git-filter-branch style).** Rejected in §4: violates
  ADR-117's append-only, not-a-source-of-truth contract and makes history lie. The append-a-`renumber`-
  event approach preserves both resolvability and honesty.
- **Leave the reflog entirely untouched with no marker event.** Rejected as insufficient: without the
  bridging `renumber` event a reader cannot map an old reference forward. Literal history *plus* one
  appended event is the honest, resolvable middle.
- **Manual `--by` offset only (no `--onto` auto-compute).** Rejected as the sole surface: it pushes
  the disjointness arithmetic onto the operator and invites off-by-one collisions. Kept as the escape
  hatch, with `--onto` as the safe default.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-05T21:02:05Z] Robert Architect:
  - Recommending acceptance. This pins the five load-bearing choices Olivia flagged as ADR-gated before any FEAT-288 impl task is dispatched. @manager @op-pierre please review and accept if you concur; I have left it Proposed and have not self-accepted.
  - (1) CLI: standalone `sq renumber --from <N> --onto <M>` (recommended, auto-computes the minimal safe offset) with `--by <n>` as a validated escape hatch — NOT a mode of `sq repair` (opposite risk profile; repair is idempotent/argument-free, renumber needs an operator boundary).
  - (2) Boundary/git: sq stays git-agnostic — the operator passes integers; sq never shells out to git / reads another ref / computes merge-base. Documented recipe is 'git show <ref>:squads/.squads.json | jq .counter' run OUTSIDE sq. Any future git assist must be an isolated, optional, gracefully-degrading layer feeding the same integer core; git is a convenience, never required.
  - (3) Disjointness: sq reads its own counter C; with --onto M it computes delta = max(M,C)+1-N so the block lands strictly above BOTH the other branch's counter and this branch's own max. With --by it validates N+n>C and REFUSES (no mutation) if unsafe, reporting the minimum. Disjoint old/new ranges => no remap key equals a remap value => single-pass rewrite_ids is order-independent (no chaining), so no high-to-low pass is needed.
  - (4) Reflog (the sharp one): historical target/delta ID fields are NOT rewritten in place — that would break ADR-117's append-only, not-a-source-of-truth contract and make history lie. Instead append one 'renumber' event carrying the {old->new} remap as the forward-resolution bridge. filter-branch analogy rejected (git commits ARE the source of truth; the reflog is not); the right analogy is git's own reflog, which is append-only and never rewritten. Frontmatter/refs/prose/filenames/counter ARE rewritten (they are the source of truth).
  - (5) Coexistence: pre-merge `sq renumber` is the preferred, intent-preserving path; post-merge `sq repair --renumber` stays the 'too late, make it valid' fallback (uniqueness only, intent lost). They share one extracted executor (rewrite_ids -> rename at filename padding -> sequence_id resync -> counter bump); only the planner differs (offset vs collision-detection).
  - Refs set: ADR-295 related-> ADR-72/ADR-117/ADR-282/FEAT-288; FEAT-288 implements-> ADR-295. FEAT-288 status left untouched (Ready). Deferral owed to FEAT-13: the new verb grammar and the 'renumber' reflog op/delta shape.
- [2026-07-06T07:14:08Z] Pierre Chat:
  - Accepted. sq stays git-agnostic for now — plain integers in, no git calls; we may add a convenience 'util merge' command later, and per this ADR it would be an optional, isolated layer feeding the same integer core. Reflog is append-only: one renumber event carries the old->new remap, historical lines are never rewritten (right call — and realistically most people will ignore the reflog anyway). Standalone verb, refuse-on-unsafe offset, and coexistence with repair --renumber as the fallback all look good. Approved for implementation.
<!-- sq:discussion:end -->
