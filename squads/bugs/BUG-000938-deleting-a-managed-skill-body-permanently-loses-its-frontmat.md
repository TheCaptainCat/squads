---
id: BUG-938
sequence_id: 938
type: bug
title: Deleting a managed skill body permanently loses its frontmatter
status: Verified
author: qa
priority: low
refs:
- MILE-934:targets
- REV-926:addresses
created_at: '2026-09-10T08:37:34Z'
updated_at: '2026-10-09T15:38:04Z'
---
<!-- sq:body -->
## Problem

Deleting a managed skill's item `.md` file and re-syncing restores the file, but with no
frontmatter at all — no `id`, `type`, `sequence_id`, `title`, `status` — and this loss is
permanent: neither `sq sync` nor `sq repair` ever re-stamps it, across repeated cycles of
either.

Driven, in a throwaway squad (not the live corpus):

```
$ rm squads/agents/skills/SKILL-000012-sq-task.md
$ sq sync
synced managed files to this squads version
$ cat squads/agents/skills/SKILL-000012-sq-task.md
sq:body (open)
sq:view:item_skill
sq:body (close)
```

The file is back — same view tag, same path — but with no frontmatter block whatsoever.
Repeating `sq sync` / `sq repair` three more cycles each leaves the file byte-identical; nothing
recovers it. `sq repair` reports it every time:

```
$ sq repair
rebuilt index: 13 items, counter=13
error: SKILL-000012-sq-task.md: file has no `id` in frontmatter — its previous index entry, if
  any, was carried forward as-is; fix the file and repair again
```

There is no `sq` command that can put the frontmatter back — recovering it requires hand-editing
the file to reconstruct `id`/`sequence_id`/`type`/`title`/`status`, which is itself against this
project's own convention against hand-editing `.md` files under `squads/`.

Reproduced on both a permanently-system skill (`squads`) and a per-item-type skill (`sq-task`) —
same result both times.

## Correction against the original description

This was surfaced by the reviewer as an aside on REV-926 (deliberately not filed there), who
characterized the combination as "`sq repair` exits 1 on it forever while `sq check` reports
clean." **Driven on the current tree, that second half does not hold**: `sq check` reports the
same error and exits 3 on every cycle, immediately after the corrupting `sq sync`:

```
$ sq check
error SKILL-000012-sq-task.md: file has no `id` in frontmatter
```

(`_is_legacy_skill_body` in `_services/_maintenance.py` exempts a missing `id` only for a
skill file whose *name* lacks the `SKILL-` prefix — the genuinely pre-stamping shape. A file
that already carries the `SKILL-` prefix but lost its `id`, which is exactly this state, is not
exempt and is flagged like any other type.) So the failure mode is not silent — `sq check` does
catch it — but it is still permanently unfixable by any `sq` command: `sq check` names the file
as broken forever, and `sq repair` refuses to guess at it forever, with no verb that repairs it.

## Why file it anyway

The reviewer's own reason for not filing was that this is only reachable via a hand-edit under
`squads/` that project convention already forbids. That reach is thinner than it sounds — this
project's own memory notes record agents making forbidden edits under `squads/` more than once
(a breakdown agent ran `sq remove` on a committed review; an agent purged fixtures with a
`/tmp/tmp.*` glob). A permanently-unrecoverable item file reachable by one accidental `rm` or
edit is worth a name and a home even though `sq check` does flag the corpus state going forward.

## Verification performed

- Drove the full delete → sync → check → repair (×3 cycles) → sync sequence in two fresh
  throwaway squads, not the live corpus, on both a permanently-system skill and a per-type
  skill.
- Confirmed the file content is byte-identical (frontmatter-less) after every cycle.
- Confirmed `sq skill <slug> show` still renders correctly (via the carried-forward index entry)
  even while the on-disk file itself is permanently broken — so the break is invisible unless an
  operator runs `sq check` or `sq repair` directly.
- Read `_is_legacy_skill_body` (`_services/_maintenance.py`) to explain why `sq check` currently
  catches this rather than staying clean, and confirmed by reading the check code path
  (`_scan_for_check`) that a `SKILL-`-prefixed file with a missing `id` is not exempted.

## Closure suggestion

Either `sq sync`/`sq repair` re-stamp a frontmatter-less managed-skill body from its known slug
and the index's carried-forward entry (the information to reconstruct `id`/`type`/`sequence_id`
is already available — the index still has the prior entry), or `sq check`'s message names the
concrete recovery instead of the generic "fix the file and repair again", since there is
currently no supported command that performs that fix.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-10T08:38:20Z] `qa` Mara Tester:
  - Drove delete -> sync -> check -> repair (x3 cycles) -> sync on both a permanently-system skill (squads) and a per-type skill (sq-task) in two throwaway squads. Frontmatter loss is real and permanent; no sq command recovers it.
  - Correction against the reviewer's aside: on the current tree sq check does NOT report clean -- it flags the missing id every cycle, exit 3 (_is_legacy_skill_body only exempts a non-SKILL-prefixed filename). The unrecoverable-without-a-forbidden-hand-edit half of the finding stands; the silent-clean-check half does not reproduce today. Body has the full detail.
  - Priority: low, per op-pierre's reasoning -- pre-existing, orthogonal, and only reachable through a hand-edit under squads/ that project convention forbids. Filed anyway since agents have made forbidden edits before, and the failure is a permanently unfixable file even though sq check now does catch it.
  - Targeted 0.16 (MILE-934), addresses REV-926.
- [2026-09-29T13:49:28Z] `python-dev` Elias Python:
  - Fixed: sq sync re-stamps a managed skill file that lost its id from the index entry, body kept; sq check and repair name sq sync for it.
- [2026-09-29T14:23:53Z] `manager` Catherine Manager:
  - Reopened for REV-975 findings.
- [2026-09-29T14:36:16Z] `python-dev` Elias Python:
  - Review fixes: frontmatter rebuilt from file name plus catalog (no index needed), duplicate-id guard, invalid YAML rebuilt, single remedy in repair.
- [2026-09-29T15:17:34Z] `python-dev` Elias Python:
  - Review fixes: timestamps carried over, duplicate slug guard, conflict-only-in-frontmatter rebuild, check names the right remedy.
- [2026-09-29T16:23:09Z] `python-dev` Elias Python:
  - Review round 3: slug identity is one helper, unstamped rivals are left alone, the skill folder is read once per scan.
- [2026-10-09T15:38:01Z] `qa` Mara Tester:
  - Verified at HEAD 7cd45323. Driven (real CLI, dev build, one scratch squad per row, bare exit codes): `sq sync` restores frontmatter on every shape, then `sq check` is clean (exit 0), `sq repair` exits 0, a second `sync` leaves the file byte-identical, and the result is byte-identical to the original file.
    
    Rows, on both a permanently-system skill (`squads`) and a per-type skill (`sq-task`):
    - file deleted: check exit 3 ("in index but no markdown file"); after sync restored whole, frontmatter and timestamps included.
    - frontmatter stripped whole, body kept: check exit 3, message names `sq sync`; after sync restored; a body with an extra line inside the body region keeps that line.
    - `id` line removed only: same as above.
    - empty file: check exit 3 (no id, missing body region); after sync restored.
    - invalid YAML frontmatter: check exit 3 (malformed frontmatter); after sync restored.
    - two files claiming SKILL-19 (a `-copy` plus a stripped original): sync warns "not restamped", leaves both files byte-identical; check exit 3 and repair exit 1, both naming the other file.
    - a managed skill renamed away from its slug: frontmatter intact then sync writes a body-only canonical file and warns; stripped then sync writes a fully stamped canonical file; after deleting the stray file, check exit 0 and repair exit 0 in both.
    - user-authored skill (`sq skill add my-custom`) stripped: sync leaves it byte-identical, check exit 3, repair exit 1 (not re-stamped, as intended); a deleted user skill file is not recreated.
    - a stripped task (non-managed): not re-stamped by sync, check exit 3, repair exit 1.
    - no index (`.squads.json` deleted) plus stripped managed skill: sync restores it, check exit 0 (only the created_at/updated_at differ from the original, as nothing carries them).
    
    Targeted tests: 114 passed (4 files, run once).
    Not covered: a hand-edited non-default frontmatter field on a managed skill beyond the fields above; Windows paths.
<!-- sq:discussion:end -->
