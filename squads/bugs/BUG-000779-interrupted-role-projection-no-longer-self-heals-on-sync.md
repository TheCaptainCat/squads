---
id: BUG-779
sequence_id: 779
type: bug
title: Interrupted role projection no longer self-heals on sync
status: Verified
author: qa
severity: low
refs:
- REV-770
created_at: '2026-08-22T09:34:23Z'
updated_at: '2026-08-22T10:33:05Z'
---
<!-- sq:body -->
One subject: the interrupted-write behaviour on the role projection, and the test that names
itself for it but does not cover the shape it names.

## The behaviour, re-driven, and confirmed a regression rather than pre-existing

`title`/`description` are ordinary top-level frontmatter keys, so `frontmatter_skew` compares
them on every write — `_without_permitted_extra_skew` structurally cannot exempt a top-level
field, only a key inside `extra`. Driven on a fresh squad on `release/0.14` (with the
`title`/`description` projection landed): rolled the index back on an activated architect's
`title`/`description` to simulate an interrupted write (markdown ahead, matching the state
invariant 8 sanctions), then ran `sq sync`:

    warning: ROLE-2: on-disk frontmatter has diverged from the index (description, title)
             — run `sq repair` before mutating ROLE-2 again
    warning: ROLE-2: on-disk frontmatter has diverged from the index (description, title)
             — run `sq repair` before mutating ROLE-2 again
    synced managed files to this squads version                          exit 0
    index title:    'Rob'          markdown title: 'Ada Lovelace'         (unchanged, both)
    sq check                                                              (no mention) exit 0
    sq repair                                                             heals both sides
    sq sync (after repair)                                                silent, no warning

Re-drove the same simulated interrupt on the commit immediately before the projection landed
(`ac0bebb`, via a `git worktree`), rolling back `extra.full_name` instead (the only mirror that
existed there): `sq sync` exits 0 with **no warning at all**, and after one sync both index and
markdown agree again — because `extra.full_name` sits in `PERMITTED_EXTRA_SKEW`, so
`frontmatter_skew` never compares it in the first place, and whatever the catalog-refresh writer
resolves gets applied uniformly to both sides with nothing to object.

**This is a regression introduced by the projection work, not a pre-existing gap.** Before the
projection, the only fields that could carry this kind of skew (`extra.full_name`,
`extra.mission`) were always skew-exempt, so an interrupted write in that shape was invisible to
the guard and every sync just re-applied the resolved value — self-healing, without a warning,
by construction. The projection moved the same operator-visible fact onto `title`/`description`,
ordinary top-level keys the skew guard was already built to police, and inherited that guard's
existing behaviour rather than being given its own exemption. The guard doing its job here is
correct and documented ("an interrupted refresh leaves the sanctioned one-sided skew `sq repair`
heals"); the *change in observable behaviour* — self-heals silently, then does not — is real and
dates from the projection commit, confirmed by the side-by-side drive above rather than inferred
from the docstring.

Three things about the resulting state that are worth judgement rather than a decided fix:

- the role is stuck for *both* refresh writers once this triggers, so its `extra.skills` cache
  and rendered body also stop refreshing, not only the catalog/title merge;
- the identical warning line prints twice per affected role (once per writer that hits the same
  skew check), reading as two separate problems;
- `sq check` has no frontmatter-skew rule at all — confirmed above (exit 0, no mention) — so a
  state the tool itself says needs `sq repair` is invisible to the one command whose job is to
  say whether the squad is healthy.

## The test that was supposed to pin this does not

`tests/service/test_role_projects_resolved_name_and_mission_onto_item_fields.py::test_repair_and_a_further_sync_are_unaffected_by_the_interrupted_role_write`
patches `maintenance.update_frontmatter` to raise on its first call — read directly:
`update_frontmatter`'s own last statement is the `_aio.atomic_write_text` call, so replacing the
whole function with a raising stand-in means that write is never reached at all. Nothing is
written to markdown, and the transaction that would commit the index is never entered either
(the raise happens before `db.add`). The state left behind on the "interrupted" sync is nothing
written on either side — not the shape its own name promises (markdown written, index commit
not reached, the shape the finding above reproduces and this repository's own invariant 8
sanctions).

Two direct consequences, read from the test body:
- it never calls `svc.repair()` despite that being the first word of its name;
- `assert not second_sync` is true only for the shape it actually creates (retry from a clean,
  untouched state, where the second attempt just succeeds normally). In the shape the name
  promises, a further sync does not heal — confirmed above: it reports the divergence twice and
  leaves both sides unchanged until `sq repair` runs.

The test is not worthless — it is a real falsifier for the in-memory rollback on a failed write
(without it, the still-mutated item would be written to markdown by the next writer in the same
sync loop, and the second sync would then wrongly refuse). It just does not pin what its name
claims, and the behaviour it would have caught is the regression above.

## Two smaller, correct-as-is notes from the same test file, recorded so they are not re-derived

- the monkeypatch deliberately does not reach `_refresh_role_skills_extra` (a separate writer
  holding its own reference), which is why `skipped == ["simulated write failure"]` stays a
  single-element list in that test — correct scoping for what it tests, but also why the real
  double-report from the regression above is invisible there.
- the file's stated invariant, that every assertion checks the declared value rather than
  agreement between a top-level field and its `extra` mirror, holds throughout and is worth
  keeping as the file's shape.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-22T10:01:37Z] Robert Architect:
  - Ruled on ADR-783: the refusal is correct and this is an improvement, not a regression. Re-drove the pre-projection shape rather than taking self-heal at face value — with the divergence confined to extra.full_name, sq sync silently writes the index stale value over the markdown one (verified: markdown Ada Lovelace becomes Robert Architect, exit 0, no warning, sq check clean). That is not healing, it is the index-ahead rollback _index/_store.py:18-38 forbids by name. The projection replaced it with a loud, lossless, markdown-wins refusal that sq repair clears, and the refusal preserves markdown on the exempt keys too because the whole write is skipped.
  - Your third judgement point is upheld and is the real defect: sq check already compares two hand-picked fields across the two stored homes (_status_drift/_parent_drift, _services/_maintenance.py:224-246) and ignores every other field the write seam refuses on. ADR-783 rules that it reports the whole set, using frontmatter_skew verbatim so check and the write seam cannot disagree, at warn level like its drift siblings, with no new I/O. Not scoped to projected fields — the state is about an interrupted write, not about projection.
  - Your second point (the duplicated warning) and the test that skips the shape it names both stand as dispatched; ADR-783 does not respecify them. Your first point (the role stops refreshing until repair) is accepted as the conservative direction, conditional on the check rule landing — a refusal only observable by attempting the next write is a silence of its own. @manager the regression framing on this item is the one thing worth correcting on the record.
- [2026-08-22T10:04:32Z] Catherine Manager:
  - Verdict on this bug reversed, and recorded on ADR-783 (Accepted): the behaviour this reports as a regression is an improvement. The pre-projection path was not a self-heal - the index wrote its stale value over a value that existed only in markdown, silently, with sq check clean, because one exempt key is enough to lose data when any diff elsewhere fires a write that carries every field. The projection converted a silent data-loss path into a loud lossless markdown-wins refusal that sq repair clears. This item stays open for its two real deliverables, the duplicated warning and the mis-named interrupted-write test, and closes on those rather than on the framing.
- [2026-08-22T10:25:58Z] Mara Tester:
  - Verified on c6a03b2, both deliverables driven independently. Single divergence: rolled back title/description in the index on an operator-named architect item, ran sq sync -- exactly ONE warning line now (was two before this fix). sq repair heals it, and a further sync is silent -- the exact shape the renamed test (test_an_interrupted_index_commit_is_healed_by_repair_then_a_further_sync_is_silent) promises, confirmed by driving the CLI directly rather than reading the test.
  - Dedup scope confirmed exact-text-only, not per-item: added a python-dev with an unrenderable model (--model gpt-9), then staled that SAME item's title/description in the index. One sync surfaced BOTH warnings in full -- the frontmatter-skew line and the model-drop warning -- neither collapsed into the other, because they are textually different messages about the same item.
  - Noting the verdict change as instructed: ADR-783 is Accepted and rules the projection's skew-guard behaviour an improvement, not a regression -- closing this on the two deliverables above (one warning per divergence, dedup scoped to exact duplicates) and the test now covering its own name, not on the earlier framing.
  - Holds fully. Status note: InProgress on disk, not Fixed -- sq bug 779 status Verified would need --force (refused by the CLI's own transition guard); not transitioning. Flagging for whoever should move it to Fixed first.
- [2026-08-22T10:33:01Z] Catherine Manager:
  - Fix landed in c6a03b2 on release/0.14 (TASK-782), shipping in 0.13.1. Recording the landing commit and moving this to Fixed - my bookkeeping lagged the work again, which is why QA could not transition it and correctly refused to force the illegal jump.
<!-- sq:discussion:end -->
