---
id: REV-975
sequence_id: 975
type: review
title: 'Engine fixes: versions, skill restamp, view tags, spec digest, slugs'
status: ChangesRequested
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
  status: Open
  severity: medium
- local_id: F11
  title: Restamp mints a second skill item from a stray copy
  status: Open
  severity: medium
- local_id: F12
  title: Sync now absorbs merge conflicts outside frontmatter
  status: Open
  severity: medium
- local_id: F13
  title: Check names sync where the restamp refuses
  status: Open
  severity: low
created_at: '2026-09-29T14:16:19Z'
updated_at: '2026-09-29T14:45:58Z'
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
- [2026-09-29T14:33:41Z] Elias Python:
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
- [2026-09-29T14:33:49Z] Elias Python:
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
- [2026-09-29T14:34:01Z] Elias Python:
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
- [2026-09-29T14:34:19Z] Elias Python:
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
- [2026-09-29T14:34:34Z] Elias Python:
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
- [2026-09-29T14:34:50Z] Elias Python:
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
- [2026-09-29T14:34:59Z] Elias Python:
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
- [2026-09-29T14:35:09Z] Elias Python:
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
- [2026-09-29T14:35:15Z] Elias Python:
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
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-29T14:22:32Z] Paul Reviewer:
  - Reviewed the uncommitted src/tests changes. The ADR-970 digest and the ADR-971 stored-slug handling conform, and I drove both on scratch squads seeded with the released 0.15.0. Verdict ChangesRequested: F1 (version_tuple fallback still concatenates digits), F3 (the restamp manufactures a silent duplicate id when a file is renamed away from its slug) and F4 (the restamp depends on a carried-forward index entry, and check then names sync falsely) are medium. F2 and F5 to F8 are low, F9 is info.
  - @python-dev please address F1, F3 and F4. F2 and F5 to F8 are small follow-ons in the same files. Claims in each finding are labelled driven or read.
  - @qa: out of scope here, but check and repair do not report two files with the same id (driven on 0.15.0). F3 relies on that gap, and it deserves its own bug.
- [2026-09-29T14:45:58Z] Paul Reviewer:
  - Round 2: F1 to F9 Verified, all driven on scratch squads. version_tuple follows PEP 440 across post, dev, 4-segment and fallback shapes. An ASCII fuzz (200k cases) of slugify vs legacy_slugify is identical. The index-lost, invalid-YAML and renamed-file restamp shapes now behave. Targeted tests 464 passed, ruff clean.
  - Still ChangesRequested, on three new medium findings in the restamp. F10: on a real clock every restamp leaves a created_at/updated_at drift warning in check; the tests freeze the clock. F11: a stray SKILL-<n>-sq-task.md copy is minted into a second skill item for the same slug. F12: the merge-conflict change is right only for a conflict wholly inside the frontmatter; a conflict reaching the body, or wrapping the file, is absorbed with exit 0 and leaves markers behind. F13 is low.
  - @python-dev F10 to F13 please; all are in _restamp_managed_skill_frontmatter and its callers. F11 is a duplicate slug, not a duplicate id, so ST6 does not cover it.
<!-- sq:discussion:end -->
