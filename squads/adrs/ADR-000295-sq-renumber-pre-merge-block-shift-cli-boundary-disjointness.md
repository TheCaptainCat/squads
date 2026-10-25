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
updated_at: '2026-10-25T21:19:28Z'
---
<!-- sq:body -->
## Context

`squads` allocates ids from a single global monotonic counter (ADR-72). When two collaborators
diverge on separate branches or clones, each bumps its own copy of the counter, so both mint the
same next number, and the merged tree holds two files claiming it.

`sq repair --renumber` is the post-merge remedy: it gives fresh numbers to files that share a
number and rewrites every reference to them. It cannot recover referential intent when the
colliding files carry the **same** id (both `FEAT-288`): nothing tells which reference meant which
file, so references to that id are listed for checking by hand instead of rewritten.

The missing piece is a **pre-merge** path: on the branch that will yield, while every reference is
still unambiguous, shift this branch's new numbers into a block above the other branch's counter.
Ids are unpadded in content (ADR-282), so the prose rewrite is a plain whole-word swap; padding
matters only at the file-rename seam.

The verb enters the frozen CLI grammar, operates on the identity system, and has to agree with
ADR-72 (the global counter) and ADR-117 (the append-only reflog that is not a source of truth).

## Decision

### 1. A standalone `sq renumber`, not a mode of `sq repair`

```
sq renumber --from <N> --onto <M>     # auto-computed minimal safe offset (recommended)
sq renumber --from <N> --by <n>       # explicit offset, validated
```

- `--from <N>` (required): the lowest branch-local number, inclusive; every item numbered `>= N`
  moves.
- `--onto <M>`: the other branch's counter; sq computes the offset (§3).
- `--by <n>`: an explicit offset. Exactly one of `--onto` and `--by` is required.

`repair` is an idempotent, argument-free reconstruction of the index from frontmatter, and its
`--renumber` needs no operator input. `renumber` is an intentional identity transform with a
boundary only the operator knows. The two keep separate verbs and share an executor (§5).

### 2. sq stays git-agnostic; the operator supplies integers

The boundary and the landing target cross into sq as plain integers. sq does not shell out to git,
read another ref's `.squads.json` or compute a merge base: its contract is a folder of markdown and
a JSON index, and its tests run in a bare `tmp_path`. The `--help` text gives the recipe for the
other branch's counter:

```
git show <mainref>:squads/.squads.json | jq .counter
```

A git-assisted convenience, if one is ever added, is an isolated opt-in layer that only computes
the integers and feeds this same core, degrading gracefully when git is absent. The identity core
never assumes git.

### 3. A disjoint block, or a refusal

Let `C` be this branch's counter, read from its index. Every local item `seq >= N` maps to
`seq + delta`, preserving order and gaps.

- **`--onto M`:** `delta = max(M, C) + 1 - N`, so the block lands strictly above both the other
  branch's counter and this branch's own maximum. Always computable, always safe.
- **`--by n`:** valid only if `N + n > C`. An unsafe value is refused with a `SquadsError` (no file
  touched) that reports the minimum safe offset. Even a safe `--by` warns that without `--onto` sq
  cannot certify the block clears the other branch's counter. A too-small offset is never silently
  corrected.

Because the new range sits strictly above the old local range, no new id string equals an old one,
so the single-pass whole-word substitution cannot chain and its order is irrelevant. Files are
renamed at the filename width while content takes the unpadded id (ADR-282).

### 4. The reflog keeps its history; one `renumber` line records the shift

Historical reflog lines are never rewritten. After the index commit, the transaction appends one
`renumber` line whose delta summarises the shift: the boundary, whichever of `onto`/`by` the
operator gave, the full `{old → new}` remap, and the items the shared index rebuild rewrote
(ADR-117: a summary, not a replayable diff). Nothing is appended when nothing moved.

Rewriting old lines would break the one-op-one-appended-line model and make the history lie about
which id an event named at the time. Identity is the integer `sequence_id` and the reflog is not
authoritative, so an old line naming a pre-shift id is a truthful record, and the appended line
lets a reader follow it forward. This is the posture of git's own reflog, which history rewriting
never touches. The source-of-truth surfaces (frontmatter `id:` and refs, body prose, filenames,
`sequence_id`, the counter) are fully rewritten.

### 5. Complementary with `repair --renumber`, one executor

- **`sq renumber` (pre-merge)** is the preferred path: it preserves referential intent.
- **`sq repair --renumber` (post-merge)** fixes collisions that already landed: it guarantees
  uniqueness and no dangling refs, and lists the references to a same-id pair it cannot attribute.

Both planners produce a `{old → new}` remap and padded renames, and both drive the same
counter-neutral executor (`_apply_remap`: `rewrite_ids` over every file, rename at filename
padding, `sequence_id` resync). Each caller reconciles the counter itself through the index
rebuild. `sq renumber` uses that rebuild directly rather than `repair`, whose missing-file detector
would read every moved number as a deletion.

## Consequences

- `sq renumber --from/--onto/--by` is part of the CLI grammar, and `renumber` is a reflog
  operation with the delta shape of §4.
- sq stays a markdown-folder tool: no git binary, no work-tree assumption.
- The single-pass rewrite is provably safe because overlap is forbidden; an unsafe `--by` is
  refused.
- The reflog stays append-only and honest; nothing about the index depends on it.
- Trade-off accepted: the operator reads the other branch's counter by hand, in exchange for
  keeping git out of the identity core.

## Alternatives considered

- **A flagged mode of `sq repair --renumber`.** Rejected: opposite risk profile and argument shape.
- **Derive the boundary from `git merge-base` inside sq.** Rejected (§2); left open only as an
  isolated optional layer.
- **Rewrite reflog `target`/`delta` in place.** Rejected (§4): it violates ADR-117 and falsifies
  history.
- **No marker event in the reflog.** Rejected: a reader could not map an old reference forward.
- **`--by` only.** Rejected as the sole surface: it pushes the disjointness arithmetic onto the
  operator. Kept as the escape hatch.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-05T21:02:05Z] `architect` Robert Architect:
  - Recommending acceptance. This pins the five load-bearing choices Olivia flagged as ADR-gated before any FEAT-288 impl task is dispatched. @manager @op-pierre please review and accept if you concur; I have left it Proposed and have not self-accepted.
  - (1) CLI: standalone `sq renumber --from <N> --onto <M>` (recommended, auto-computes the minimal safe offset) with `--by <n>` as a validated escape hatch — NOT a mode of `sq repair` (opposite risk profile; repair is idempotent/argument-free, renumber needs an operator boundary).
  - (2) Boundary/git: sq stays git-agnostic — the operator passes integers; sq never shells out to git / reads another ref / computes merge-base. Documented recipe is 'git show <ref>:squads/.squads.json | jq .counter' run OUTSIDE sq. Any future git assist must be an isolated, optional, gracefully-degrading layer feeding the same integer core; git is a convenience, never required.
  - (3) Disjointness: sq reads its own counter C; with --onto M it computes delta = max(M,C)+1-N so the block lands strictly above BOTH the other branch's counter and this branch's own max. With --by it validates N+n>C and REFUSES (no mutation) if unsafe, reporting the minimum. Disjoint old/new ranges => no remap key equals a remap value => single-pass rewrite_ids is order-independent (no chaining), so no high-to-low pass is needed.
  - (4) Reflog (the sharp one): historical target/delta ID fields are NOT rewritten in place — that would break ADR-117's append-only, not-a-source-of-truth contract and make history lie. Instead append one 'renumber' event carrying the {old->new} remap as the forward-resolution bridge. filter-branch analogy rejected (git commits ARE the source of truth; the reflog is not); the right analogy is git's own reflog, which is append-only and never rewritten. Frontmatter/refs/prose/filenames/counter ARE rewritten (they are the source of truth).
  - (5) Coexistence: pre-merge `sq renumber` is the preferred, intent-preserving path; post-merge `sq repair --renumber` stays the 'too late, make it valid' fallback (uniqueness only, intent lost). They share one extracted executor (rewrite_ids -> rename at filename padding -> sequence_id resync -> counter bump); only the planner differs (offset vs collision-detection).
  - Refs set: ADR-295 related-> ADR-72/ADR-117/ADR-282/FEAT-288; FEAT-288 implements-> ADR-295. FEAT-288 status left untouched (Ready). Deferral owed to FEAT-13: the new verb grammar and the 'renumber' reflog op/delta shape.
- [2026-07-06T07:14:08Z] `op-pierre` Pierre Chat:
  - Accepted. sq stays git-agnostic for now — plain integers in, no git calls; we may add a convenience 'util merge' command later, and per this ADR it would be an optional, isolated layer feeding the same integer core. Reflog is append-only: one renumber event carries the old->new remap, historical lines are never rewritten (right call — and realistically most people will ignore the reflog anyway). Standalone verb, refuse-on-unsafe offset, and coexistence with repair --renumber as the fallback all look good. Approved for implementation.
- [2026-10-25T21:19:28Z] `architect` Robert Architect:
  - 2026-10-25 audit: partly stale, body rewritten in the present tense; the five choices are unchanged. Corrected the post-merge description: repair --renumber no longer repoints every reference to one winner, it renumbers number collisions and lists references to a same-id pair for checking by hand (sq repair --help, _renumber). Restated §4 with the delta sq writes (from, onto, by as given, remap, stripped), §5 with the counter-neutral _apply_remap and the rebuild sq renumber uses instead of repair. Removed the line-number citations, the verified-ground-truth paragraph and the FEAT-13 deferral notes.
<!-- sq:discussion:end -->
