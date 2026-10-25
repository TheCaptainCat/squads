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
- ADR-955
description: The projection refusal is correct and an improvement; sq check gains
  the value direction of its cross-source reconciliation
created_at: '2026-08-22T10:00:59Z'
updated_at: '2026-10-25T21:42:19Z'
---
<!-- sq:body -->
## Context

The role projection (ADR-766) writes a resolved field onto the item's own `title`/`description`.
Those are ordinary top-level frontmatter keys, so the skew guard compares them on every write, as
§5 of that decision rules. The observable consequence was filed as a regression: interrupt the
projection's write and `sq sync` warns and refuses where it used to converge.

**Driven, twice, on fresh `--roles core` squads, when the role still mirrored its definition into
an `extra` mapping.** Two shapes, side by side.

*The shape the projection introduced*: markdown ahead on `title` and `extra.full_name` (an
interrupted rename to "Ada Lovelace"), index behind on both, plus a stale `extra.agreements` in
the index so the catalog refresh attempts a write:

    sq sync   warning: ROLE-2: on-disk frontmatter has diverged from the index (title)
                       — run `sq repair` before mutating ROLE-2 again      (printed twice)
              synced managed files to this squads version                  exit 0
    markdown  title 'Ada Lovelace'      full_name 'Ada Lovelace'      (both preserved)
    index     title 'Robert Architect'  agreements ['stale-agreement'] (write skipped whole)
    sq check  no issues                                                    exit 0
    sq repair index adopts 'Ada Lovelace'; the next sync is silent and leaves both sides equal

*The shape it replaced*: the same interruption confined to `extra.full_name`, the only mirror
that existed before the projection, with `title` identical on both sides so nothing non-exempt
was compared:

    sq sync   synced managed files to this squads version   exit 0, no warning
    markdown  full_name 'Robert Architect'   <- held 'Ada Lovelace' before this sync
    sq check  no issues                                     exit 0

That second drive is the load-bearing measurement: the old behaviour was not a self-heal. It
converged by **writing the index's stale value over a value that existed only in markdown**: a
committed markdown mutation destroyed, silently, exit 0, `sq check` clean throughout. The
mechanism: the catalog refresh persisted the whole frontmatter of the item **as loaded from the
index**, and `frontmatter_skew` never compared the diverging key because the skew exemption then
covered every mirrored key of a non-developer role. One exempt key was enough to lose data: any
diff elsewhere fired the write, and the write carried every field.

`_index/_store.py` states the direction and its reason in one breath: markdown is never behind
the index, because an index ahead of the markdown would let repair silently revert a committed
mutation, and a loud, repairable inconsistency beats a quiet rollback every time. The old
behaviour was that quiet rollback, reached through the exemption instead of through the commit
order.

## Decision

**1. The refusal is correct, and an improvement, not a regression.**

The comparison that decides it is "did the behaviour change from correct to incorrect", and it
went the other way: from a silent index-wins rollback to a loud, lossless, markdown-wins refusal
that the reconcile clears. Both drives land on the same three surfaces (what survives in
markdown, what `sq sync` says, what `sq check` says), and the projection improves the first two.

Two properties of the refusal are not incidental. It preserves markdown on the exempt keys too:
the whole write is skipped, so the exemption never gets its chance to clobber them. And the skew
is cleared in the sanctioned direction, adopting the file's value, so the operator's extra step
costs a command and loses nothing. On a squad at the package's schema that command is
`sq repair`, which the refusal and the `sq check` finding name; while the squad's schema is behind
the package the gate refuses `sq repair`, and the reconcile that `sq migrate up` runs before its
first runner clears it in the same direction (ADR-955). The refusal and the finding are printed
only by commands that run at the package's schema, so the remedy they name is available.

The collateral is real and accepted: while the skew stands, that role stops refreshing
altogether, since every refresh writer hits the same guard. That is the guard's uniform behaviour
for any unrepaired item and it is the conservative direction. It is acceptable **on condition of
decision 3**: a refusal nobody can observe except by attempting the next write is a silence of its
own.

**2. Re-deriving the projection is rejected, in both variants.**

Re-deriving from the item as loaded is rejected: the resolver's base takes the item's own stored
values, so a re-derivation reads the index's copy and writes it to markdown. That makes
index-ahead authoritative, the one direction `_index/_store.py` forbids, and the inverse of what
`sq repair` does.

A markdown-first re-derivation, building the base from `Item.from_frontmatter` on the file rather
than from the index-loaded item, is mechanically coherent and is still rejected, on scope. It
would make the reconciler perform `sq repair`'s job (derive the index from markdown) for one item
and one field family, without repair's whole-corpus discipline, and **partially**: it converges the
catalog-owned fields while every other diverging top-level field (`status`, `priority`,
`assignee`, `refs`, `parent`) stays skewed. The result is worse than either endpoint, because it
suppresses a true warning about an item that is still inconsistent on the fields the guard was
right about. One rule answers "which side wins" (markdown, via the reconcile); a second, weaker
rebuild path would make the answer depend on which writer ran last.

**3. `sq check` reports the divergence, as the general frontmatter-vs-index value divergence,
not as a projected-field rule.**

`sq check` compares the on-disk frontmatter with the index for every item. An interrupted write
that landed on `title`, `description`, `priority`, `assignee` or `refs` is visible to the one
command whose job is to say whether the squad is healthy, not only to the next write that touches
the item. Scoping a rule to projected fields would be arbitrary: the state is about an
interrupted write, and the projection only made one instance of it loud at the write seam.

**4. The predicate is `frontmatter_skew`, reused verbatim.**

Check does not invent its own comparison. Reusing `frontmatter_skew(text, item, ...)` guarantees
that check reports **exactly** the set the write seam would refuse on: no more (an operator told
to repair a state nothing objects to) and no less. It also inherits the exemptions
(`PERMITTED_ATTRIBUTE_SKEW`) and the round-trip normalisation, so the legacy-corpus case the
exemption exists for stays silent here as well. The former status and parent drift predicates
are the two-field special case of it and fold into it.

**5. Warn level, in the drift family, keeping direction in the message.**

A value divergence is the drift family's class, not the reconciliation family's: the entry exists
on both sides and one side is older. It takes `warn`, and `sq check`'s exit code is unchanged. In
this repo a warning is a defect to fix, which is enough to make it actionable. The message names
the skew direction when the two `updated_at` values order it.

**6. No new I/O, and no new race.**

The check scan already keeps each file's raw text and parsed frontmatter, and `check` already
holds the index snapshot. The rule is a cross-source claim, so it is a candidate confirmed by the
existing single re-read round like its siblings: a sync committing between the scan and the check
resolves the candidate instead of producing a false warning, and a clean board pays for no second
load.

## Consequences

- An interrupted write is visible from the command an operator runs to ask whether the squad is
  healthy. That is what makes decision 1's refusal acceptable rather than merely defensible.
- `sq check` and the item-file write seam agree, by construction, on what "diverged" means.
- Every frontmatter field is compared, not two hand-picked ones. It fires on no legitimate state:
  every write persists the whole frontmatter from one item, so the two sides differ only where a
  write was interrupted (driven on a corpus with a `full_name`/`mission` override declared and
  never synced, before and after `sq sync`: `frontmatter_skew` returned `[]` for every item).
- The exemption's loss window is as small as its membership. A divergence confined to
  `PERMITTED_ATTRIBUTE_SKEW` keys (today `model` on a non-developer role, which nothing writes
  there) resolves index-wins and silently; ADR-766 §5 owns that trade. The realistic instance of
  the window, a name or mission change, sits outside the exempt set, since the projected fields
  ride one `update_frontmatter` call and an interruption leaves both ahead.

## Falsification the implementation owes

- The interrupted-write shape, driven end to end on one item: markdown ahead on a top-level
  field, index behind, then `sq check` names the item and the diverging key. Delete the rule and
  that test goes red on a clean report.
- The same assertion for a field with no bespoke predicate (`title` and `priority`, say): a rule
  that only generalises `status`/`parent` in name passes a test written against those two.
- A corpus carrying an override that declares `mission`, never synced, reports nothing. This keeps
  the widening honest.
- Equivalence with the write seam, stated as one property: for a given `(text, item)` pair, check
  reports precisely when `ensure_no_skew` raises.
- The confirm round: a candidate whose skew is resolved between the scan and the confirm (by a
  concurrent `sq repair`) is not reported.
- `sq check` exit code unchanged on a squad whose only issue is a value divergence.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-22T10:04:27Z] `op-pierre` Pierre Chat:
  - Add the check rule at warn level. The distinction from my earlier refusal holds: that one was declined because the projection repairs itself on the next sync, and here sync refuses and leaves it. The zero-fire evidence on a pre-fix corpus answers the noise objection, and generalizing the existing drift family beats a third hand-picked field.
- [2026-08-22T10:04:28Z] `manager` Catherine Manager:
  - Verified the load-bearing mechanism before accepting rather than taking the drives on trust: _refresh_catalog_extra mutates and persists the item as loaded from the index, and _exempt_extra_keys hands a non-dev role the whole permitted-skew set, so a value living only in markdown was overwritten by the index copy with nothing comparing it. The store module docstring states the principle in its own words - an index ahead of the markdown would let repair silently revert a committed mutation, and a loud repairable inconsistency beats a quiet rollback. This ruling is that principle applied.
- [2026-10-11T20:20:01Z] `architect` Robert Architect:
  - 2026-10-11: narrowed in place, on the operator's ruling of this date recorded on MILE-934. One dated note, under decision 1, after the two paragraphs stating that `sq repair` clears the refusal and resolves the skew in the sanctioned direction. It says the claim holds at the package's schema, and that while a squad's schema is behind the package the gate refuses `sq repair` and the reconcile inside `sq migrate up` is the recovery path (ADR-955 and its amendments of 2026-10-09). Nothing else in the body changed; `related` ref to ADR-955 added.
- [2026-10-25T21:42:19Z] `architect` Robert Architect:
  - 2026-10-25 audit: body rewritten in present tense; decision unchanged. Context framed as the state measured then; the ADR-955 note folded into decision 1; PERMITTED_EXTRA_SKEW references replaced by PERMITTED_ATTRIBUTE_SKEW (model only) and the stale extra mechanics removed.
<!-- sq:discussion:end -->
