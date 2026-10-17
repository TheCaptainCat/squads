---
id: REV-975
sequence_id: 975
type: review
title: 'Engine fixes: versions, skill restamp, view tags, spec digest, slugs'
status: Approved
author: reviewer
refs:
- TASK-969
- ADR-970
- ADR-971
- MILE-934:targets
subentities:
- local_id: F1
  title: version_tuple fallback still concatenates digits
  status: Verified
  severity: medium
- local_id: F2
  title: 4+ segment versions and .post misorder
  status: Verified
  severity: low
- local_id: F3
  title: Restamp creates a silent duplicate id on a renamed file
  status: Verified
  severity: medium
- local_id: F4
  title: Restamp needs a carried-forward index entry
  status: Verified
  severity: medium
- local_id: F5
  title: Invalid-YAML managed skill still unrecoverable
  status: Verified
  severity: low
- local_id: F6
  title: Duplicate view tag remedy points at refusing verbs
  status: Verified
  severity: low
- local_id: F7
  title: Repair message gives two contradictory remedies
  status: Verified
  severity: low
- local_id: F8
  title: legacy_slugify is not frozen
  status: Verified
  severity: low
- local_id: F9
  title: Transliteration map misses þ ð ħ ŧ ı
  status: Verified
  severity: info
- local_id: F10
  title: Restamp leaves a timestamp drift warning in check
  status: Verified
  severity: medium
- local_id: F11
  title: Restamp mints a second skill item from a stray copy
  status: Verified
  severity: medium
- local_id: F12
  title: Sync now absorbs merge conflicts outside frontmatter
  status: Verified
  severity: medium
- local_id: F13
  title: Check names sync where the restamp refuses
  status: Verified
  severity: low
- local_id: F14
  title: Renumber keeps a misplaced copy, orphaning the id
  status: Verified
  severity: high
- local_id: F15
  title: Renumber misses references inside the renumbered copy
  status: Verified
  severity: medium
- local_id: F16
  title: Refused writes still change files first
  status: Verified
  severity: medium
- local_id: F17
  title: Remove and retype referrer rewrites are unguarded
  status: Verified
  severity: medium
- local_id: F18
  title: Write guard's name scan disagrees with the detector
  status: Verified
  severity: medium
- local_id: F19
  title: Restamp re-reads the skill folder per damaged file
  status: Verified
  severity: low
- local_id: F20
  title: Check names repair for a duplicate repair refuses
  status: Verified
  severity: low
- local_id: F21
  title: Roster show gives no duplicate-id warning
  status: Verified
  severity: low
- local_id: F22
  title: Duplicate-id and skill-file module cleanups
  status: Verified
  severity: low
- local_id: F23
  title: Write guard reads the whole corpus on every write
  status: Verified
  severity: medium
- local_id: F24
  title: Scan caches live as mutable Service state
  status: Verified
  severity: low
- local_id: F25
  title: Two strengthened tests prove less than they claim
  status: Verified
  severity: low
created_at: '2026-09-29T14:16:19Z'
updated_at: '2026-09-29T16:57:27Z'
---
<!-- sq:body -->
Review of the uncommitted `src/` and `tests/` changes for the five engine fixes: `version_tuple`, the managed-skill frontmatter restamp, out-of-region view tags, the self-view spec digest, and slug transliteration. I drove the new code with the dev tree's `sq --dir` on scratch squads under the scratchpad. The old-form data was seeded with the released 0.15.0 `sq`. I also read the diff and ran the targeted tests (152 passed) and `tests/meta` (303 passed). `ruff check` and `ruff format --check` are clean.

## What holds

- **ADR-970, digest (driven).** The canonical form matches the ADR exactly: `model_dump(mode="json")`, `ensure_ascii=False`, compact separators, keys not sorted, SHA-256 lowercase hex, computed from `Service.spec`. Override A and B give different digests. A comment or whitespace edit gives the same digest. Removing the override brings back the baseline. A rejected document refuses the command. Two squads in different directories with different rosters give identical digests, so the digest does not depend on a path or the roster. The spec models have no set-valued field (read).
- **ADR-971, stored slug (driven).** The released `sq` created `caf-dev`, `op-lodie` and `r-duire-latence`. After that, dev-tree `sync` then `check` left the tree byte-identical (`git status` empty): the pointer keeps its name and `role caf-dev show` resolves. Re-adding `--tech Café`, `" café "`, `Élodie Dupont` and `Réduire latence` is refused and names the stored slug. The legacy rule matches the pre-fix `slugify(tech.strip())` exactly (read).
- **ADR-971, no re-derivation (read).** The grep of every `slugify(`/`operator_slug(`/`dev_role(` call path finds derivation only at creation: `create`, `add_*`, memory `add` and retitle. `dev_base_from_item` now pins the stored slug. `dev_base_for_slug` still derives from a slug, but only as a preview for an override document that has no roster entry, so nothing stored is involved.
- **View tags (driven).** A tag before the body, after `sq:body:end`, in the discussion, at EOF with no newline, disabled, or written without spaces is warned by `check`. `view add` and `view disable` refuse it with exit 1 and leave the file unchanged. The in-body row keeps its old behaviour.
- **Restamp, the shapes in the brief (driven).** A deleted file, an empty file, stripped frontmatter, a missing `id` and an empty `id` all come back after one `sync`, byte-identical to the original.

## Invariant 1 (frontmatter is the source of truth)

The restamp is bounded to managed skills, whose content `sync` regenerates anyway. It never touches an authored item (read, and covered by a test). That keeps it from inverting the invariant. But it depends on something the invariant says it must not need: a carried-forward index entry. Every field it restores can be derived without the index. The id, sequence number, type and slug come from the filename. The title, author and description come from the bundled or declared skill catalog. The one field the index alone knows is `status`, and the projection guard keeps a managed skill live anyway (driven: archiving `sq-task` is refused). Once the index is rebuilt from the markdown, the restamp can no longer recover the file (F4). When an index entry is stale, the restamp writes those stale values back. For managed skills the next `sync` refresh converges the content fields, so the damage is limited (inferred). Rebuilding from filename plus catalog would make the path sound and remove F4.

## Out of scope, for QA

On the released 0.15.0, `sq check` and `sq repair` do not report two files carrying the same `id` (driven by copying a task file). That gap existed before this change, and F3 depends on it.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 975 add-finding "…" --severity medium`; track with `sq review 975 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — version_tuple fallback still concatenates digits

<!-- sq:finding:F1:body -->
**Driven.** The fallback branch of `version_tuple` (`_util.py`) runs whenever `_VERSION_RE` does not match. It still concatenates every digit in a segment, which is the exact defect BUG-937 set out to remove:

```
'0.14.0-post1'   -> (0, 14, 1, 4, 0)      # equals 0.14.1
'0.14.0rc1.dev2' -> (0, 14, 1, 2, 4, 0)   # above 0.14.0 and 0.14.1
'0.14.0 rc1'     -> (0, 14, 1, 4, 0)
'0.14.0a1b2'     -> (0, 14, 12, 4, 0)
```

`0.14.0rc1.dev2` and `0.14.0.post1` are legal PEP 440 versions. A chlog bound or a stamp in one of these shapes moves the window, just as BUG-937 did. The subtask's "keeps today's fail-safe 0" was about a segment with **no** digits, not about concatenating the digits of a mixed segment.

**Fix direction:** in the fallback, take each segment's leading digit run, or 0, and never join digits across a suffix. Add these shapes as rows to the ordering table.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-09-29T14:33:41Z] `python-dev` Elias Python:
  - version_tuple fallback takes each segment's leading digits and never joins digits across a suffix
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — 4+ segment versions and .post misorder

<!-- sq:finding:F2:body -->
**Driven.** The tuple is `(*release, rank, n)`, and the release part is padded to at least 3 but can be longer. With 4 or more release segments, the prerelease rank lands in a slot that another version uses for a release number:

```
'1.2.3.1rc1'   -> (1, 2, 3, 1, 3, 1)  <  '1.2.3' -> (1, 2, 3, 4, 0)   # wrong
'0.14.0.post1' -> (0, 14, 0, 1, 4, 0) <  '0.14.0'                     # post below its release
```

The trailing-zero strip hides this for `X.Y.Z.0`. `.post` is not a recognised tag, so it falls through to the fallback and compares as a fourth release segment. squads ships only `X.Y.Z` today, so the impact is low.

**Fix direction:** return `(tuple(release), rank, n)` so the release part compares as its own element. Decide explicitly whether `.postN` sorts above its release, and add a row for it.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-09-29T14:33:49Z] `python-dev` Elias Python:
  - release numbers compare as their own tuple; post sorts above its release; rows added
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Restamp creates a silent duplicate id on a renamed file

<!-- sq:finding:F3:body -->
**Driven.** A managed skill file renamed away from its slug, with its frontmatter intact (`SKILL-000015-sq-task.md` renamed to `SKILL-000015-foo.md`):

- `sync` re-seeds `SKILL-000015-sq-task.md` from the index path.
- The restamp then writes `id: SKILL-15` into the re-seeded file.
- Both files now carry `id: SKILL-15` and `slug: sq-task`.
- `sq check` reports no issues and `sq repair` exits 0.

On the released 0.15.0, the same rename leaves the re-seeded file without an `id`, and `check` flags it. So the restamp turns a reported state into a silent duplicate identity. `check` does not report duplicate ids across files, a gap that already existed (see the review body).

**Fix direction:** before writing, the restamp refuses and reports when another file in the folder already carries that `id`. A row for this shape belongs in the table: a renamed file with frontmatter intact, and a renamed file with frontmatter stripped.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-09-29T14:34:01Z] `python-dev` Elias Python:
  - restamp refuses and reports when another file already carries the id
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Restamp needs a carried-forward index entry

<!-- sq:finding:F4:body -->
**Driven.** Strip `SKILL-000015-sq-task.md`'s frontmatter, delete `.squads.json`, run `sq repair`, then `sq sync`:

- `repair` rebuilds the index with no entry for SKILL-15, so `_restamp_managed_skill_frontmatter` never sees it.
- `seed_bundled_skills` finds no `sq-task` roster item and writes a stray unprefixed `agents/skills/sq-task.md`. `sync` then warns that nothing indexes it.
- `sq check` still says `file has no id -- sq sync restores a managed skill's frontmatter`. The `sync` that just ran did not restore it, so the remedy it names is false.

Invariant 1 says the index can always be rebuilt from the markdown. A recovery that works only while an older index is still around is incomplete. It fails for a lost or regenerated `.squads.json`, and for a repair that ran before the index existed. The id, sequence number, type and slug come from the filename, and the content fields come from the bundled or declared skill catalog. So a restamp built from the filename plus the catalog would not need the index at all.

**Fix direction:** derive the frontmatter from the filename plus the seeding catalog, not from the index entry. At minimum, `check` names `sync` only when the restamp can actually act.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-09-29T14:34:19Z] `python-dev` Elias Python:
  - frontmatter is rebuilt from file name plus skill catalog; sync rebuilds the index when it lacks the restored file
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Invalid-YAML managed skill still unrecoverable

<!-- sq:finding:F5:body -->
**Driven.** A managed skill file whose frontmatter is present but is not valid YAML (a `title: [unclosed` line) makes `sq sync` abort with exit 1 and a YAML traceback message, before the restamp runs. `sq check` reports "malformed frontmatter" and gives no remedy. No verb recovers the file, so BUG-938's "permanently unfixable managed skill" still holds for this shape. The brief named invalid YAML as a shape to attack, and the restamp's `except (OSError, SquadsError)` suggests it meant to report this case rather than never reach it.

**Fix direction:** for a managed-skill file only, let the restamp treat unparseable frontmatter like missing frontmatter and rewrite it, keeping the body. Otherwise, name the manual remedy.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-09-29T14:34:34Z] `python-dev` Elias Python:
  - unreadable YAML in a managed skill file is rebuilt like missing frontmatter; check names sync
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Duplicate view tag remedy points at refusing verbs

<!-- sq:finding:F6:body -->
**Driven.** With one copy of a view tag in `sq:body` and one outside it, `sq check` gives two remedies that disagree:

```
error ... duplicate sq:view:milestone_rollup tag (2 copies, counting both states) — collapse to one with `sq milestone 20 view add milestone_rollup` or `... view disable ...`
warn  ... view tag (sq:view:milestone_rollup) sits outside sq:body ... move it inside sq:body
```

Both verbs in the error's remedy now refuse in this state, because an out-of-region copy exists. The error-level line sends the operator to a verb that fails.

**Fix direction:** when any copy sits outside the region, the duplicate message defers to the move-it-inside remedy.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-09-29T14:34:50Z] `python-dev` Elias Python:
  - duplicate message defers to remove-or-move when a copy sits outside sq:body
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Repair message gives two contradictory remedies

<!-- sq:finding:F7:body -->
**Driven.** `sq repair` on a stripped managed skill prints:

```
file has no `id` in frontmatter -- `sq sync` restores a managed skill's frontmatter — its previous index entry, if any, was carried forward as-is; fix the file and repair again
```

`_missing_id_message` appends the `sync` remedy and keeps the generic "fix the file and repair again". That leaves two remedies in one line, one of them a hand edit the project forbids. It also mixes a `--` separator with a `—` one.

**Fix direction:** for a managed skill, replace the generic tail instead of appending to it.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-09-29T14:34:59Z] `python-dev` Elias Python:
  - repair/adopt/migrate print the sync remedy alone for a managed skill file
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — legacy_slugify is not frozen

<!-- sq:finding:F8:body -->
**Read.** ADR-971 decision 4 keeps the earlier rule as "one private, frozen function". `legacy_slugify` shares `_cut_slug` and `_slug_strip` with the live `slugify`. So any later change to the live cut (the strip pattern, the `max_len` trim, the `untitled` fallback) silently changes the "frozen" rule, and duplicate detection then stops matching slugs stored under the real old rule. The name is also public (`legacy_slugify`, `legacy_operator_slug`), so it can be imported to propose a slug.

**Fix direction:** give the legacy rule its own verbatim body, with its own regex, and a test that pins it to known old outputs (for example `Élodie` -> `lodie`, `Größe prüfen` -> `gr-e-pr-fen`).
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-09-29T14:35:09Z] `python-dev` Elias Python:
  - legacy_slugify is a verbatim self-contained copy pinned by tests
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Transliteration map misses þ ð ħ ŧ ı

<!-- sq:finding:F9:body -->
**Driven.** The transliteration gaps are the known limit, but they are narrower than "non-Latin scripts":

- Latin letters that NFKD does not split and the map does not cover are still dropped: `þ ð ħ ŧ ı`. For example, `Þór Ðað` -> `or-a`, and `ħ ŧ ŀ` -> `l`.
- The `max_len` cut can land inside an expansion, so `'a'*59 + 'ß'` ends `...as`.

Both are cosmetic for new slugs and harmless to stored ones. Recording them so the gap is named: extending the map with `þ→th, ð→d, ħ→h, ŧ→t, ı→i` costs nothing.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-09-29T14:35:15Z] `python-dev` Elias Python:
  - map extended with thorn, eth, h/t stroke, dotless i; the length cut never splits an expansion
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — Restamp leaves a timestamp drift warning in check

<!-- sq:finding:F10:body -->
**Driven.** On a real clock, every restamp shape leaves `sq check` with a warning: deleted, empty, stripped, no `id`, empty `id`, invalid YAML, and a frontmatter-only merge conflict.

```
warn SKILL-15: created_at, updated_at drift between frontmatter and index — markdown is ahead; run `sq repair` before this item is mutated again, or the fix is lost silently
```

`_catalog_skill_item` stamps `created_at`/`updated_at` with `clock.now()`. The early pass re-indexes only when the index lacks the number, so an index that already knows the item keeps its old timestamps. BUG-938's acceptance says `sq check` is clean after one `sync`.

The tests miss this because the `project` fixture freezes the clock, so seed time and restamp time are the same. I reproduced it on a scratch squad with the dev tree.

**Fix direction:** re-index after any restamp, not only for an unknown number. Alternatively, carry the timestamps over from the index entry when one exists; the index is then only a hint, not a requirement. Add a test with an unfrozen clock, or one that advances it between seeding and sync.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-09-29T15:16:45Z] `python-dev` Elias Python:
  - restamp keeps the index's timestamps when it knows the item; tested with a later clock
- [2026-09-29T15:55:04Z] `reviewer` Paul Reviewer:
  - Verified (driven, real clock, index older than the restamp): deleted, empty, stripped, empty id, missing id and invalid-YAML skill files all come back byte-identical after one sync, index unchanged, check clean.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — Restamp mints a second skill item from a stray copy

<!-- sq:finding:F11:body -->
**Driven.** The restamp now builds an item from any `SKILL-<n>-<managed-slug>.md` whose frontmatter lacks an `id`. So a stray copy with a new number becomes a second skill item for the same slug. Reproduction: copy `SKILL-000015-sq-task.md` without its frontmatter to `SKILL-000099-sq-task.md`, then run `sq sync`.

- The new file gets `id: SKILL-99`, and the early pass re-indexes it.
- The index now has two skill items with slug `sq-task` (SKILL-15 and SKILL-99).
- `sq check` is clean.

Before this round, the index-path guard (`_stamped_skill_slug == item.extra.slug` for an indexed item) kept this from happening. This is a duplicate slug, not a duplicate id, so the duplicate-id detection in ST6 will not catch it.

**Fix direction:** refuse to restamp a file when another file (or indexed item) already carries a managed skill with that slug. Report it the way the duplicate-id refusal does.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-09-29T15:16:54Z] `python-dev` Elias Python:
  - restamp refuses a file when another file or the index already holds the slug
- [2026-09-29T15:55:20Z] `reviewer` Paul Reviewer:
  - Reopened (driven). With the index present, a stray `SKILL-000099-sq-task.md` is now refused. Two shapes still mint a second skill item for one slug, and `sq check` stays clean afterwards:
    
    1. **Slug in `extra.slug`.** Rename `SKILL-000019-sq-task.md` to `SKILL-000019-foo.md` with its frontmatter intact, add a frontmatter-less `SKILL-000099-sq-task.md`, delete `.squads.json`, then run `sync`. SKILL-99 is restamped, and the index then holds SKILL-19 and SKILL-99, both with slug `sq-task`. `SkillFolder.build` reads a top-level `slug`, but skill frontmatter carries it under `extra.slug`, so the renamed file is filed under its filename slug `foo`.
    2. **Two unstamped files.** Strip both `SKILL-000019-sq-task.md` and a copy `SKILL-000099-sq-task.md`, delete `.squads.json`, then run `sync`. Both are restamped, because the verdicts come from the folder as it stood before the restamp and neither file carried a slug yet.
    
    Both need the index gone. F4 made that a supported case: the restamp is meant to work without the index.
    
    **Fix direction:** read the slug from `extra.slug` (the same way `_file_slug` in `_duplicate_ids` does), and when several unstamped files claim one slug, restamp none of them and report the group. A check rule for two skill items sharing a slug would catch whatever the restamp still misses.
- [2026-09-29T16:21:30Z] `python-dev` Elias Python:
  - one file-slug helper (extra.slug first); several unstamped files for one slug are all left alone and reported
- [2026-09-29T16:33:51Z] `reviewer` Paul Reviewer:
  - Verified (driven, no index, then repair and sync): with the slug in extra.slug of a renamed file, and with two unstamped files for one slug, nothing is restamped, the index holds one sq-task item, and check names remove-or-rename.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — Sync now absorbs merge conflicts outside frontmatter

<!-- sq:finding:F12:body -->
**Driven.** The changed test (`test_sync_rebuilds_a_merge_conflicted_managed_skill_file`) covers only a conflict that sits wholly inside the frontmatter. For that shape, rebuilding is right: every field comes from the catalog. Two other conflict shapes now pass `sync` with exit 0, where 0.15.0 refused with a clean error:

- **Conflict spanning the frontmatter and the body:** the frontmatter is rebuilt and the other side's lines are dropped. The body keeps the stray `=======` and `>>>>>>> branch` lines, plus the other side's prose.
- **Conflict wrapping the whole file** (a hunk starting at line 1): `strip_frontmatter` finds no leading block, so the whole conflicted text becomes the body under a new frontmatter. The file keeps `<<<<<<<` and a second frontmatter. `check` then reports a duplicate `sq:body` and a duplicate view tag.

In both cases `sync` turns a merge a human must resolve into a file that looks resolved, keeping part of the conflict and dropping part of it. A managed skill body can also hold author prose (the check says so), so a body-side conflict is not safe to discard.

**Fix direction:** rebuild only when the text after the frontmatter carries no conflict markers and the file starts with a frontmatter block. Otherwise refuse as before. Keep the old refusal test for those shapes next to the new rebuild test.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-09-29T15:17:06Z] `python-dev` Elias Python:
  - only a conflict wholly inside the frontmatter is rebuilt; any other position refuses
- [2026-09-29T15:55:05Z] `reviewer` Paul Reviewer:
  - Verified (driven): a conflict wholly inside the frontmatter is rebuilt byte-identical; a conflict spanning frontmatter and body, and one wrapping the whole file, refuse sync with exit 1 and check names resolve-by-hand.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — Check names sync where the restamp refuses

<!-- sq:finding:F13:body -->
**Driven.** When the restamp refuses because another file already carries the id, `sync` warns "remove or rename one of the two files". `sq check` still says `file has no id in frontmatter; run sq sync to restore a managed skill's frontmatter`, but that `sync` has just refused. It is the same dead-end-remedy shape as F4 and F6.

**Fix direction:** `check` names `sync` only when the restamp would act. Otherwise it gives the same remove-or-rename remedy as `sync`.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
- [2026-09-29T15:17:14Z] `python-dev` Elias Python:
  - check names the working remedy: sync, remove-or-rename, or resolve-by-hand
- [2026-09-29T15:55:10Z] `reviewer` Paul Reviewer:
  - Verified (driven): for a stray copy and for the renamed-file shape, check names the same remove-or-rename remedy sync prints; a restampable file still names sync.
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — Renumber keeps a misplaced copy, orphaning the id

<!-- sq:finding:F14:body -->
**Driven.** Copy `tasks/TASK-000022-alpha.md` into the bugs folder as `bugs/TASK-000022-other.md` with a different title, then run `repair --renumber`:

```
TASK-22: 2 files, different slugs
  kept       bugs/TASK-000022-other.md
  renumbered tasks/TASK-000022-alpha.md -> TASK-25 (tasks/TASK-000025-alpha.md)
warn TASK-22: indexed but no markdown file found (deleted?)
```

The byte-order rule keeps whichever path sorts first, and `bugs/` sorts before `tasks/`. So the id stays with the misplaced copy, and no index scan reads that file (`_iter_item_files` globs `TASK-*.md` in `tasks/` only). The correctly placed original is renamed to TASK-25. TASK-22 drops out of `list`. Every reference to it now dangles. `check` exits 0 with dangling-ref warnings only, and it never mentions the orphaned `bugs/TASK-000022-other.md` again. This is the silent identity loss BUG-978 is meant to stop, and it ends on a board that looks almost clean.

The same rule also misfires within one folder. `TASK-000022-alpha-copy.md` sorts before `TASK-000022-alpha.md` (`-` < `.`). So a stray copy that differs from the original only by whitespace keeps the id, and the original is renumbered (driven).

**Fix direction:** refuse any group that has a file outside its type's folder, or at least never keep such a file. Within the eligible files, prefer the one the previous index entry points at, and fall back to byte order only when no index entry exists. Add a row: different slug, other type folder.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
- [2026-09-29T16:21:37Z] `python-dev` Elias Python:
  - renumber keeps the index's file, refuses a group with a file outside its type folder, and orders by name without the suffix
- [2026-09-29T16:33:57Z] `reviewer` Paul Reviewer:
  - Verified (driven): a cross-folder different-slug copy is refused, and TASK-22 stays indexed with both files unchanged. A whitespace-only -copy renumbers the copy, not the original, with or without an index.
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->

<!-- sq:finding:F15 -->
### F15 — Renumber misses references inside the renumbered copy

<!-- sq:finding:F15:body -->
**Driven.** `BUG-000024-other.md` is a different-slug copy of BUG-24, and its body says "supersedes BUG-24". No other file mentions BUG-24. `repair --renumber` renames the copy to `BUG-000025-other.md`, prints `no references` and exits 0. The copy's own body still names BUG-24.

`renumber_same_id_groups` collects `item_files` before any rename, then scans `[p for p in item_files if p.exists()]`. The renumbered copy's new path is in neither list, so the copy's own references are never listed. The subtask says to scan every item file, the two copies included. For the same reason, when several groups are processed, a later group's scan also misses every file renamed by an earlier group.

**Fix direction:** rebuild the file list after the renames, or add each target path to it. Add a row with a reference inside the renumbered copy, and one where the only reference sits there (it must then exit 1).
<!-- sq:finding:F15:body:end -->

#### Discussion

<!-- sq:finding:F15:discussion -->
- [2026-09-29T16:21:44Z] `python-dev` Elias Python:
  - references are listed after every rename, so a renumbered file's own text and earlier groups' renames are scanned
- [2026-09-29T16:34:02Z] `reviewer` Paul Reviewer:
  - Verified (driven): the renumbered copy's own body reference is listed, and the command exits 1.
<!-- sq:finding:F15:discussion:end -->
<!-- sq:finding:F15:end -->

<!-- sq:finding:F16 -->
### F16 — Refused writes still change files first

<!-- sq:finding:F16:body -->
**Driven.** Two refused writes still change files on disk before they refuse:

- **Retitle.** `sq task 22 update --title "alpha renamed"` on a duplicated id renames `TASK-000022-alpha.md` to `TASK-000022-alpha-renamed.md`, and only then refuses. The index still points at the old path. `_items.py` renames the file (`path_rename`) before calling `_refuse_duplicated_id`. The refusal message names the renamed path.
- **`remove --force`.** `sq task 22 remove --yes --force`, where the referrer TASK-23 is duplicated: BUG-24 has its ref already severed and written, then the command refuses at TASK-23. Nothing is committed to the index, so BUG-24's markdown is now ahead of the index. The guard runs inside the per-referrer loop, not before it.

In both cases a command that exits 1 has still changed the corpus. The retitle case leaves the stale-path state that F18 then misreports as a duplicate.

**Fix direction:** check every file a command will touch, in one pass, before the first write: the subject and every referrer. Add the retitle and the multi-referrer `remove --force` rows to the write-seam test. Today it covers only `comment` and `body`.
<!-- sq:finding:F16:body:end -->

#### Discussion

<!-- sq:finding:F16:discussion -->
- [2026-09-29T16:21:56Z] `python-dev` Elias Python:
  - every write verb checks its subject and referrers before touching a file; a refused write leaves the tree byte-identical (hash rows)
- [2026-09-29T16:34:05Z] `reviewer` Paul Reviewer:
  - Verified (driven): a retitle and remove --force on a duplicated subject or referrer refuse with the tree unchanged.
<!-- sq:finding:F16:discussion:end -->
<!-- sq:finding:F16:end -->

<!-- sq:finding:F17 -->
### F17 — Remove and retype referrer rewrites are unguarded

<!-- sq:finding:F17:body -->
**Driven.** Two write paths are not guarded:

- **`remove`.** `sq task 23 remove --yes` succeeds on a duplicated id. It deletes the indexed copy, `TASK-000023-beta.md`, and keeps `TASK-000023-beta-copy.md`. The copy to delete is chosen by scan order, which is exactly the tie-break the subtask rules out.
- **Retype rewriting a referrer.** `sq task 22 retype bug`, where TASK-22 itself is not duplicated but its referrer TASK-23 is: the command rewrites `TASK-22:depends-on` to `BUG-22:depends-on` in `TASK-000023-beta.md` only. `TASK-000023-beta-copy.md` keeps the old ref. The guard protects writes whose *subject* is duplicated, but not writes that land on a duplicated *referrer*. The `remove --force` sever path does guard its referrers (F16), so the two paths disagree.

**Fix direction:** refuse `remove` on a duplicated id. Guard every file a referrer rewrite touches (retype, and any other ref-rewriting path), checking before the first write, as in F16.
<!-- sq:finding:F17:body:end -->

#### Discussion

<!-- sq:finding:F17:discussion -->
- [2026-09-29T16:22:03Z] `python-dev` Elias Python:
  - remove is guarded, and retype, status rename and default-role refuse while any id is duplicated
- [2026-09-29T16:34:11Z] `reviewer` Paul Reviewer:
  - Verified (driven): remove refuses on a duplicated id; retype refuses while any id is duplicated. Global refusal for retype, rename-status and set-default is judged proportionate: a duplicate is a check error cleared by one hand edit, and refusing more writes until then cannot lose data.
<!-- sq:finding:F17:discussion:end -->
<!-- sq:finding:F17:end -->

<!-- sq:finding:F18 -->
### F18 — Write guard's name scan disagrees with the detector

<!-- sq:finding:F18:body -->
**Driven.** `show` and every write use `duplicate_files` in `_base.py`, a filename scan (`<PREFIX>-<n>`). `check` and `repair` use the frontmatter-id detector. The two disagree in both directions:

- **Missed.** A copy named `tasks/alpha-copy.md`, or `tasks/TASK-000099-alpha.md` that carries `id: TASK-22`: `check` errors and `repair` exits 1, but `show` gives no warning and `sq task 22 comment` succeeds.
- **False.** After an interrupted rename (the only file is `TASK-000022-alpha2.md`, the index still says `alpha.md`), `show` warns "2 files carry this id (tasks/TASK-000022-alpha.md, tasks/TASK-000022-alpha2.md)", naming a file that does not exist. A write refuses with "merge the content ... delete the other by hand". At the checkpoint the same write gave the correct remedy: "file is missing from its indexed location ... run `sq repair`". `check` does not report a duplicate here. F16's refused retitle produces exactly this state.

The module docstring says one detector is shared by check, repair and the restamp. In fact the guard is a second detector with a different rule.

**Fix direction:** keep the cheap per-write scan, but make it answer the same question as the detector. Glob the candidates, then confirm each one by its frontmatter `id`, and drop the item's own file when it does not exist. At minimum, when the indexed path is missing, fall through to the existing missing-file error. Add both shapes as rows.
<!-- sq:finding:F18:body:end -->

#### Discussion

<!-- sq:finding:F18:discussion -->
- [2026-09-29T16:22:13Z] `python-dev` Elias Python:
  - the guard uses the detector's rule (frontmatter id, any name, any folder) via a stat-cached scan; a missing own file falls through to the missing-file error
- [2026-09-29T16:34:17Z] `reviewer` Paul Reviewer:
  - Verified (driven): unprefixed and other-number copies now warn on show and refuse writes; a stale index path gives the missing-file error again. Its cost is F23.
<!-- sq:finding:F18:discussion:end -->
<!-- sq:finding:F18:end -->

<!-- sq:finding:F19 -->
### F19 — Restamp re-reads the skill folder per damaged file

<!-- sq:finding:F19:body -->
**Driven** (a probe that counts `store.load` calls and `_aio.read_text` calls per path):

- **`check` with three stripped managed skill files:** 5 index loads, not 1, and every skill file read 4 times. Each report line calls `_skill_remedy`, which calls `_skill_folder_state`, which reads the whole skill folder and lists the index again. The cost is O(damaged files x skill files). On a clean board and on a duplicate-id board, `check` still loads once and reads each file once.
- **`sync` on a clean board:** 11 index parses, against 7 at checkpoint 48cf1444 (same squad, same probe). The restamp now runs `_indexed_skills` twice (folder state, then `known`), and the restamp runs twice per sync. `sync` did not parse the index once even at the checkpoint, so this is a regression of 4, not a broken contract.
- **`repair`:** reads every item file twice when duplicates are checked (`_id_carriers()` has no log, then the rebuild reads each file again). Inferred to be acceptable. Noted so the cost is named.

**Fix direction:** build the `SkillFolder` once per `check` and per restamp pass, and pass it to `_skill_remedy`. Reuse one indexed-skill list per restamp.
<!-- sq:finding:F19:body:end -->

#### Discussion

<!-- sq:finding:F19:discussion -->
- [2026-09-29T16:22:21Z] `python-dev` Elias Python:
  - skill folder built once per scan; index consulted only if a file could be restamped; check reads and parses match the earlier checkpoint
- [2026-09-29T16:34:21Z] `reviewer` Paul Reviewer:
  - Verified (driven, same probe on 48cf1444 and HEAD): sync clean 7/7 parses; check with three stripped skills 2/2 parses, 1 re-read file each; sync with them 8 vs 9.
<!-- sq:finding:F19:discussion:end -->
<!-- sq:finding:F19:end -->

<!-- sq:finding:F20 -->
### F20 — Check names repair for a duplicate repair refuses

<!-- sq:finding:F20:body -->
**Driven.** With `.squads.json` deleted, `repair` leaves the duplicated id out and exits 1, as specified. `check` then prints `TASK-22: on disk but not in index (run sq repair)` next to the duplicate error. That `repair` has just refused, so the line is the same dead-end-remedy shape as F4, F6 and F13.

Two smaller output issues from the same run:

- The check line is `error TASK-22: TASK-22: 2 files carry this id ...`. The message repeats the issue key.
- `repair` prints the whole group line once per file (two identical lines for a pair, differing only in the leading filename).

**Fix direction:** suppress the not-in-index line for an id the duplicate rule already reports. Drop the key from `_duplicate_id_message` for `check`, and print the group line once in `repair`.
<!-- sq:finding:F20:body:end -->

#### Discussion

<!-- sq:finding:F20:discussion -->
- [2026-09-29T16:22:32Z] `python-dev` Elias Python:
  - not-in-index line suppressed for a refused duplicate; key dropped from the check message; repair prints the group once
- [2026-09-29T16:34:27Z] `reviewer` Paul Reviewer:
  - Verified (driven): without an index, check no longer names repair; the key is not repeated; repair prints the group once.
<!-- sq:finding:F20:discussion:end -->
<!-- sq:finding:F20:end -->

<!-- sq:finding:F21 -->
### F21 — Roster show gives no duplicate-id warning

<!-- sq:finding:F21:body -->
**Driven.** With `SKILL-000019-sq-task.md` copied to `SKILL-000019-sq-task-copy.md`, `check` errors and `repair` exits 1. But `sq skill sq-task show` exits 0 and prints no warning to stderr. The warning is wired only into the work-item `show` in `_cli/_items.py`, and the roster `show` commands (skill, role, operator) do not call `duplicate_id_error`. Writes to the skill do refuse, since they go through the shared guard. The subtask says `show` warns, and it lists the skill shape as a row.

**Fix direction:** call the same warning from the roster `show` commands, and add a CLI row for the skill shape.
<!-- sq:finding:F21:body:end -->

#### Discussion

<!-- sq:finding:F21:discussion -->
- [2026-09-29T16:22:39Z] `python-dev` Elias Python:
  - skill, role, operator and any-item show warn on a duplicated id
- [2026-09-29T16:34:30Z] `reviewer` Paul Reviewer:
  - Verified (driven): sq skill sq-task show warns on stderr for a copied skill file.
<!-- sq:finding:F21:discussion:end -->
<!-- sq:finding:F21:end -->

<!-- sq:finding:F22 -->
### F22 — Duplicate-id and skill-file module cleanups

<!-- sq:finding:F22:body -->
**Read**, except where noted.

- **Cohesion.** `has_conflict_markers` and `RESTAMP_BLOCKED_REMEDY` are restamp concerns, but they live in `_duplicate_ids.py`. `_skill_files.py` then imports them back from there. A merge-conflict test has nothing to do with duplicate ids. Both belong in `_skill_files.py`.
- **Two definitions of a file's slug.** `_duplicate_ids._file_slug` reads `extra.slug`, then `slug`, then the filename. `SkillFolder.build` reads `slug`, then the filename. The second one is the root of the F11 residual. Keep one helper.
- **Stringly-typed verdict.** `Verdict.kind: str` takes `"act"`, `"blocked"` or `"conflict"`, and callers compare against literals. Use `Literal[...]` or an enum.
- **Convention.** `_duplicate_ids.py` lines 138 and 169 use the parenthesis-less `except OSError, SquadsError:`. That is valid Python 3.14, but CLAUDE.md makes the parenthesized form plus `# fmt: skip` the project convention, and these are the only two paren-less sites in `src` (driven grep).
- **Sync I/O in async code.** `renumber_same_id_groups` calls `md.read_bytes()` directly, while the rest of the module goes through `_aio`.
- **Fragile dispatch.** `unreadable_report` picks its output form by substring-matching four remedy constants inside the message. A structured flag on the result would not break when someone rewords a constant.

**What holds:** no bare type aliases, no module-level mutable state (tests/meta 303 passed), no gratuitous private-import aliases (`_sections as sections` is the documented namespace form), no ticket ids or versions in new comments (grep checked against a known positive), and the docstrings stay at 1 to 2 sentences. pyright shows 0 errors, and ruff check and format are clean.
<!-- sq:finding:F22:body:end -->

#### Discussion

<!-- sq:finding:F22:discussion -->
- [2026-09-29T16:22:50Z] `python-dev` Elias Python:
  - constants moved, one file_slug, Literal verdict kind, parenthesised excepts, async reads, SelfRemedied replaces remedy-text matching
- [2026-09-29T16:34:38Z] `reviewer` Paul Reviewer:
  - Verified (read): constants moved to _skill_files, one file_slug, Literal verdict kind, parenthesised excepts with fmt: skip, _aio.read_bytes, SelfRemedied replaces substring matching.
<!-- sq:finding:F22:discussion:end -->
<!-- sq:finding:F22:end -->

<!-- sq:finding:F23 -->
### F23 — Write guard reads the whole corpus on every write

<!-- sq:finding:F23:body -->
**Driven.** The write guard and the `show` warning now call `IdCarrierCache.groups(self._all_item_files())`, which reads every markdown file in every type folder. The cache lives on the `Service`, and each CLI invocation builds a new `Service`, so a CLI command always starts with an empty cache and reads the whole corpus.

Measured with one interpreter, on a copy of this repo's squad (1029 files):

| command | 48cf1444 | HEAD |
|---|---|---|
| `sq task 969 show` | 0.76-0.80 s | 1.75-1.84 s |
| `sq task 969 comment` | 0.79 s | 1.89 s |
| `sq task 969 show --json` | 0.75 s | 0.75 s |

On the base scratch squad, a probe counted a single `comment` reading 25 files (every item file, the target twice), against 2 at 48cf1444. The ST6 body asked for this check to stay cheap: glob for the sequence number's files and do not rescan the corpus. Cost grows with the size of the corpus, so it lands on every adopter write and on every human `show`.

**Fix direction:** keep the guard proportional to one item. Glob candidates by the sequence number across the type folders, and confirm each by its frontmatter `id`. For a copy whose name does not carry the number (the unprefixed shape), either accept that `check` and `repair` catch it, or read only the frontmatter block of each file. Add a test that bounds the files a single write reads.
<!-- sq:finding:F23:body:end -->

#### Discussion

<!-- sq:finding:F23:discussion -->
- [2026-09-29T16:51:25Z] `python-dev` Elias Python:
  - the guard and show read only files whose name carries the item number or no number; a well-formed name for another number is check and repair territory; timings within noise of the checkpoint
- [2026-09-29T16:57:15Z] `reviewer` Paul Reviewer:
  - Verified (driven, repo-squad copy of 1029 files, 3 runs each, same interpreter): show 0.81-0.93s against 0.75-0.81s at 48cf1444, comment 0.87-0.92s against 0.83-0.85s. A comment reads 2 files. Trade-off accepted: a copy named for another number is caught by check and repair, and writes meanwhile land on the indexed file.
<!-- sq:finding:F23:discussion:end -->
<!-- sq:finding:F23:end -->

<!-- sq:finding:F24 -->
### F24 — Scan caches live as mutable Service state

<!-- sq:finding:F24:body -->
**Read / inferred.** `check` now stores what it has read on the `Service` itself: `_skill_state`, `_skill_texts` and `_skill_items` are set at the start of `check` and cleared at the end, while restamp and repair reset only some of them. Three consequences follow:

- **No `try/finally`.** If `check` raises part-way, the caches stay set. A later `repair` or `sync` on the same `Service` then reads a stale skill folder through `_read_skill_texts` and `_indexed_skills` (inferred).
- **Shared between coroutines.** Coroutines on one `Service` share this state. The existing race tests run a mutation on the same `svc` in the middle of `check`, and a restamp or repair in that window resets `_skill_texts` or `_skill_state` under `check` (inferred).
- **Misplaced comment.** In `_roster.py`, `set_default_role` still has "Resolved once for the whole pass ..." above the new `_refuse_any_duplicated_id()` line. That comment describes `default_kind`, one line below.

This is scan-scoped state kept on a long-lived object, where the project prefers a context passed through the calls.

**Fix direction:** pass one scan context through `check`, `repair` and the restamp, holding the skill texts, the skill items and the `SkillFolder`. Failing that, wrap the set and clear in `try/finally`. Move the comment back onto `default_kind`.
<!-- sq:finding:F24:body:end -->

#### Discussion

<!-- sq:finding:F24:discussion -->
- [2026-09-29T16:51:35Z] `python-dev` Elias Python:
  - scan state moved to a ScanContext made per call and passed down; nothing kept on the service; comment moved back onto default_kind
- [2026-09-29T16:57:19Z] `reviewer` Paul Reviewer:
  - Verified (read, driven tests): scan state is carried in a ScanContext/SkillScan made per check, repair or restamp; nothing remains on the service. The set_default_role comment sits on default_kind again.
<!-- sq:finding:F24:discussion:end -->
<!-- sq:finding:F24:end -->

<!-- sq:finding:F25 -->
### F25 — Two strengthened tests prove less than they claim

<!-- sq:finding:F25:body -->
**Read.** Two of the tests prove less than their names claim:

- **`test_with_no_index_the_first_name_is_kept_whatever_the_scan_order`.** The test reverses `fresh._iter_item_files`, but the choice of the kept file never reads that order. The groups come from `_id_carriers`, which sorts, and `renumber_same_id_groups` sorts again by stem. So the reversal changes nothing the test observes, and it would pass with any iteration order. The explicit sort is what gives the order-independence (read). Either reverse the order `_id_carriers` sees, or drop the claim from the name.
- **`test_check_on_damaged_skills_parses_the_index_and_reads_files_no_more_than_needed`.** The test asserts `parses <= 2` and at most 3 re-read files. The measured values are 2 parses and 1 re-read file (driven), so up to two more files could be re-read without the test going red. Pin the exact counts, or derive them from the fixture.
<!-- sq:finding:F25:body:end -->

#### Discussion

<!-- sq:finding:F25:discussion -->
- [2026-09-29T16:51:44Z] `python-dev` Elias Python:
  - scan-order test reverses what the kept-file choice reads; parse and re-read counts pinned to the measured 2 and 1
- [2026-09-29T16:57:21Z] `reviewer` Paul Reviewer:
  - Verified (read): the parse test pins 2 parses and 1 re-read; the scan-order test now reverses the _id_carriers result that the renumber consumes.
<!-- sq:finding:F25:discussion:end -->
<!-- sq:finding:F25:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-29T14:22:32Z] `reviewer` Paul Reviewer:
  - Reviewed the uncommitted src/tests changes. The ADR-970 digest and the ADR-971 stored-slug handling conform, and I drove both on scratch squads seeded with the released 0.15.0. Verdict ChangesRequested: F1 (version_tuple fallback still concatenates digits), F3 (the restamp manufactures a silent duplicate id when a file is renamed away from its slug) and F4 (the restamp depends on a carried-forward index entry, and check then names sync falsely) are medium. F2 and F5 to F8 are low, F9 is info.
  - @python-dev please address F1, F3 and F4. F2 and F5 to F8 are small follow-ons in the same files. Claims in each finding are labelled driven or read.
  - @qa: out of scope here, but check and repair do not report two files with the same id (driven on 0.15.0). F3 relies on that gap, and it deserves its own bug.
- [2026-09-29T14:45:58Z] `reviewer` Paul Reviewer:
  - Round 2: F1 to F9 Verified, all driven on scratch squads. version_tuple follows PEP 440 across post, dev, 4-segment and fallback shapes. An ASCII fuzz (200k cases) of slugify vs legacy_slugify is identical. The index-lost, invalid-YAML and renamed-file restamp shapes now behave. Targeted tests 464 passed, ruff clean.
  - Still ChangesRequested, on three new medium findings in the restamp. F10: on a real clock every restamp leaves a created_at/updated_at drift warning in check; the tests freeze the clock. F11: a stray SKILL-<n>-sq-task.md copy is minted into a second skill item for the same slug. F12: the merge-conflict change is right only for a conflict wholly inside the frontmatter; a conflict reaching the body, or wrapping the file, is absorbed with exit 0 and leaves markers behind. F13 is low.
  - @python-dev F10 to F13 please; all are in _restamp_managed_skill_frontmatter and its callers. F11 is a duplicate slug, not a duplicate id, so ST6 does not cover it.
- [2026-09-29T15:57:18Z] `reviewer` Paul Reviewer:
  - Round 3 (F10-F13 plus ST6): F10, F12 and F13 are Verified (driven). F11 is reopened: a slug stored in extra.slug is not seen, and two unstamped files that share a slug are both minted when the index is gone.
  - ST6: check, repair, list and show behave on every BUG-978 shape, the padded spelling and the three-file group. The identical-copy refusal holds. New: F14 (high) renumber keeps a copy from the wrong type folder, so the original is renumbered and the id drops out of the index. F15 to F18 (medium): the renumbered copy's own references are not listed; retitle and remove --force change files before refusing; remove and retype referrer rewrites are unguarded; the write guard's filename scan disagrees with the detector. F19 to F22 are low.
  - Whitespace-only copies: renumbering loses no data, but byte order keeps the -copy file and renumbers the original. That is folded into F14's kept-file rule.
  - @python-dev please address F11 and F14 to F22. Every claim in them is labelled driven or read.
- [2026-09-29T16:35:12Z] `reviewer` Paul Reviewer:
  - Round 4: F11 and F14-F22 Verified, all driven except F22 (read). Global refusal for retype, rename-status and set-default is judged proportionate.
  - Still ChangesRequested on F23 (medium): the write guard and show now read every item file per CLI invocation, about 2.3x on this repo's 1029-file squad (show 0.78s to 1.8s, comment 0.79s to 1.89s). F24 (low): scan caches kept as mutable Service state. F25 (low): two tests prove less than their names claim.
  - @python-dev F23 to F25 please.
- [2026-09-29T16:57:26Z] `reviewer` Paul Reviewer:
  - Round 5: F23-F25 Verified. Every finding F1-F25 is Verified. The narrowed guard is accepted: show and comment are back within about 0.1s of 48cf1444, and the one shape it no longer sees (a copy named for another number) is reported by check and repair.
<!-- sq:discussion:end -->
