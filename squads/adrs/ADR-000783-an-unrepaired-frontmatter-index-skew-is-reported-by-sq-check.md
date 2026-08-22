---
id: ADR-783
sequence_id: 783
type: decision
title: An unrepaired frontmatter/index skew is reported by sq check
status: Accepted
author: architect
refs:
- BUG-779
- ADR-766
description: The projection refusal is correct and an improvement; sq check gains
  the value direction of its cross-source reconciliation
created_at: '2026-08-22T10:00:59Z'
updated_at: '2026-08-22T10:04:30Z'
---
<!-- sq:body -->
## Context

The role projection (ADR-766) writes a resolved `full_name`/`mission` onto the item's own
`title`/`description` (read: `_services/_maintenance.py:676`, `:684`). Those are ordinary
top-level frontmatter keys, so the skew guard compares them on every write — exactly as §5 of
that decision ruled it should. The observable consequence, filed as a regression: interrupt the
projection's write and `sq sync` now warns and refuses where it used to converge.

**Driven, twice, on fresh `--roles core` squads.** Two shapes, side by side.

*The shape the projection introduced* — markdown ahead on `title` and `extra.full_name` (an
interrupted rename to "Ada Lovelace"), index behind on both, plus a stale `extra.agreements` in
the index so the catalog refresh actually attempts a write:

    sq sync   warning: ROLE-2: on-disk frontmatter has diverged from the index (title)
                       — run `sq repair` before mutating ROLE-2 again      (printed twice)
              synced managed files to this squads version                  exit 0
    markdown  title 'Ada Lovelace'      full_name 'Ada Lovelace'      (both preserved)
    index     title 'Robert Architect'  agreements ['stale-agreement'] (write skipped whole)
    sq check  no issues                                                    exit 0
    sq repair index adopts 'Ada Lovelace'; the next sync is silent and leaves both sides equal

*The shape it replaced* — the same interruption confined to `extra.full_name`, the only mirror
that existed before the projection, with `title` identical on both sides so nothing non-exempt
is compared:

    sq sync   synced managed files to this squads version   exit 0, no warning
    markdown  full_name 'Robert Architect'   <- held 'Ada Lovelace' before this sync
    sq check  no issues                                     exit 0

That second drive is the load-bearing measurement, and it says the old behaviour was not a
self-heal. It converged by **writing the index's stale value over a value that existed only in
markdown**: a committed markdown mutation destroyed, silently, exit 0, `sq check` clean
throughout. The mechanism, read: `_refresh_catalog_extra` persists the whole
`to_frontmatter_dict()` of the item **as loaded from the index** (`_services/_maintenance.py:701`),
and `frontmatter_skew` (`_itemfile.py:182`) never compares the diverging key because
`_exempt_extra_keys` (`:96`) hands a non-dev role the whole of `PERMITTED_EXTRA_SKEW` (`:70`).
One exempt key is enough to lose data: any diff elsewhere fires the write, and the write carries
every field.

`_index/_store.py:18-38` states the direction and its reason in one breath — markdown is never
behind the index, because "an index ahead of the markdown would let repair silently revert a
committed mutation … a loud, repairable inconsistency beats a quiet rollback every time." The
old behaviour is that quiet rollback, reached through the exemption instead of through the
commit order.

## Decision

**1. The current behaviour is correct, and the change is an improvement, not a regression.**

The comparison that produced the regression verdict is "did the observable behaviour change"
(it did). The comparison that decides it is "did it change from correct to incorrect", and it
went the other way: from a silent index-wins rollback to a loud, lossless, markdown-wins
refusal that `sq repair` clears. Both drives above land on the same three surfaces — what
survives in markdown, what `sq sync` says, what `sq check` says — and the projection improves
the first two.

Two properties of the refusal are worth naming because they are not incidental. It preserves
markdown on the **exempt keys too**: the whole write is skipped, so the exemption never gets its
chance to clobber `extra.full_name` either (driven — `full_name 'Ada Lovelace'` survives in the
first drive and does not in the second). And `sq repair` resolves it in the sanctioned direction,
adopting the file's value, so the operator's extra step costs a command and loses nothing.

The collateral is real and accepted: while the skew stands, that role stops refreshing
altogether — its resolved-skills cache and rendered body included, since both refresh writers
hit the same guard. That is the guard's uniform behaviour for any unrepaired item and it is the
conservative direction. It is acceptable **on condition of decision 3**: a refusal nobody can
observe except by attempting the next write is a silence of its own, and today the only command
that reveals this state is the one it blocks.

**2. Re-deriving the projection is rejected, in both variants.**

Re-deriving from the item as loaded is rejected for the reason the tech lead traced:
`role_base_from_item` (`_roles/_resolver.py:307`, `:340-343`) takes the item's own stored
`extra.full_name` as its base, so a re-derivation reads the index's copy and writes it to
markdown — index-ahead made authoritative, the one direction `_index/_store.py:18` forbids, and
the inverse of what `sq repair` does. The exempt-key drive above is what that path already does
when the guard is not looking.

A markdown-first re-derivation — building the base from `Item.from_frontmatter` on the file
rather than from the index-loaded item — is mechanically coherent and is still rejected, on
scope rather than on feasibility. It would make the reconciler perform `sq repair`'s job (derive
the index from markdown) for one item and one field family, without repair's whole-corpus
discipline, and **partially**: it converges the catalog-owned fields while every other diverging
top-level field — `status`, `priority`, `assignee`, `refs`, `parent` — stays skewed and still
needs repair. The result is worse than either endpoint, because it suppresses a true warning
about an item that is still inconsistent on the fields the guard was right about. One rule
answers "which side wins" (markdown, via repair); a second, weaker rebuild path makes the answer
depend on which writer ran last.

**3. `sq check` reports the divergence — as the general frontmatter-vs-index value divergence,
not a projected-field rule.**

`sq check` already performs cross-source value comparison, on exactly two hand-picked fields:
`_drift_issues` runs `_status_drift` and `_parent_drift` against the on-disk frontmatter
(`_services/_maintenance.py:224-246`), through the candidate/confirm round at `:1902`. So the
defect is not "check has no skew rule"; it is that check compares two fields of the two stored
homes and ignores the rest, while the write seam refuses on all of them. An interrupted write
that landed on `title`, `description`, `priority`, `assignee` or `refs` is invisible to the one
command whose job is to say whether the squad is healthy — driven above: `sq check` reports "no
issues" on a squad whose own `sq sync`, seconds earlier, said to run `sq repair`.

Scoping a rule to projected fields would be arbitrary for the same reason: the state is not
about projection, it is about an interrupted write, and the projection only made one instance of
it loud at the write seam.

**4. The predicate is `frontmatter_skew`, reused verbatim.**

Check must not invent its own comparison. Reusing `frontmatter_skew(text, item)` guarantees that
check reports **exactly** the set the write seam would refuse on — no more (an operator told to
repair a state nothing objects to) and no less (today's gap). It also inherits the exemptions and
the round-trip normalisation for free (`_itemfile.py:182-200`), so the legacy-corpus case
`PERMITTED_EXTRA_SKEW` exists for stays silent here as well, and folding the two existing drift
predicates into it removes their raw-value comparison in favour of the normalised one.

**5. Warn level, folded into the existing drift family, keeping direction in the message.**

Both existing drift predicates are `warn` (`:234`, `:241`); both existence directions of
`_index_reconciled` are `error` (`_services/_validators.py:477`, `:485`). A value divergence is
the drift family's class, not the reconciliation family's — the entry exists on both sides and
one side is simply older — so it takes `warn`, and `sq check`'s exit code is unchanged. In this
repo a warning is a defect to fix, which is enough to make it actionable. `_drift_message`'s
existing habit of naming the skew direction when the two `updated_at` values order it should
carry over.

**6. No new I/O, and no new race.**

`_scan_for_check` already keeps each file's full raw text in `bodies[seq]` and its parsed
frontmatter in `on_disk[seq]` (`_services/_maintenance.py:2078-2079`), and `check` already holds
the index snapshot (`:1804`). The rule is a cross-source claim, so it is a candidate confirmed by
the existing single re-read round (`:1902`) exactly like its siblings — a sync committing between
the scan and the check resolves the candidate instead of producing a false warning, and a clean
board still pays for no second load.

## Consequences

- An interrupted write becomes visible from the command an operator actually runs to ask whether
  the squad is healthy, rather than only from the next write that happens to touch the item.
  That is what makes decision 1's refusal acceptable rather than merely defensible.
- `sq check` and the item-file write seam agree, by construction, on what "diverged" means.
- Two hand-picked drift fields become all of them, which is a widening: a corpus carrying an
  interrupted write on any field starts reporting where it was silent. It is not a widening onto
  pre-existing legitimate states — driven on a pre-fix corpus (a `full_name`/`mission` override
  declared and never synced), `frontmatter_skew` returns `[]` for every item, because both
  stored homes carry the same stale value; every write persists the whole frontmatter dict from
  one item, so the two sides can only differ where a write was interrupted. Driven on the same
  squad after `sq sync`: still `[]`, both sides now carrying the declared name.
- The exemption's own loss window is narrowed, not closed. A divergence confined to
  `PERMITTED_EXTRA_SKEW` keys still resolves index-wins and silently, as the second drive above
  shows, and this decision
  does not change that: the exemption is deliberate and ADR-766 §6 owns the trade. What the
  projection did was move the realistic instance of that window — a rename — out of the exempt
  set, since `full_name` and `title` now ride one `update_frontmatter` call and an interruption
  leaves both ahead.
- Nothing in the skew guard, `PERMITTED_EXTRA_SKEW`, or the projection changes. ADR-766 §5 stands
  as written; this decision adds the reporting half that its own consequences deferred as a
  separate policy call.

## Falsification the implementation owes

- The interrupted-write shape, driven end to end on one item: markdown ahead on a top-level
  field, index behind, then `sq check` names the item and the diverging key. Delete the rule and
  that test goes red on a clean report.
- The same assertion for a field with no bespoke predicate today (`title` and `priority`, say) —
  a rule that only generalises `status`/`parent` in name passes a test written against those two.
- A pre-fix corpus asserted clean: an override declaring `full_name` and `mission`, never synced,
  reports nothing. This is the test that keeps the widening honest, and the one that would have
  caught a rule built on "stored title vs resolved name" instead of on the two stored homes.
- Equivalence with the write seam, stated as one property rather than two lists: for a given
  `(text, item)` pair, check reports precisely when `ensure_no_skew` (`_itemfile.py:253`) raises.
  A test asserting the message text on both sides is not the same test and does not replace it.
- The confirm round: a candidate whose skew is resolved between the scan and the confirm (by a
  concurrent `sq repair`) is not reported.
- `sq check` exit code unchanged on a squad whose only issue is a value divergence.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-22T10:04:27Z] Pierre Chat:
  - Add the check rule at warn level. The distinction from my earlier refusal holds: that one was declined because the projection repairs itself on the next sync, and here sync refuses and leaves it. The zero-fire evidence on a pre-fix corpus answers the noise objection, and generalizing the existing drift family beats a third hand-picked field.
- [2026-08-22T10:04:28Z] Catherine Manager:
  - Verified the load-bearing mechanism before accepting rather than taking the drives on trust: _refresh_catalog_extra mutates and persists the item as loaded from the index, and _exempt_extra_keys hands a non-dev role the whole permitted-skew set, so a value living only in markdown was overwritten by the index copy with nothing comparing it. The store module docstring states the principle in its own words - an index ahead of the markdown would let repair silently revert a committed mutation, and a loud repairable inconsistency beats a quiet rollback. This ruling is that principle applied.
<!-- sq:discussion:end -->
