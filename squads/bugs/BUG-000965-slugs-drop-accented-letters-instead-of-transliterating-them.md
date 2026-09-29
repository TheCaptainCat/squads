---
id: BUG-965
sequence_id: 965
type: bug
title: Slugs drop accented letters instead of transliterating them
status: Open
author: qa
priority: medium
severity: medium
refs:
- MILE-934:targets
created_at: '2026-09-25T13:39:46Z'
updated_at: '2026-09-25T13:40:13Z'
---
<!-- sq:body -->
## Reproduction

`slugify` (`src/squads/_util.py`) lowercases, then replaces every run of characters outside
`[a-z0-9]` with a single `-`. It does not transliterate accented/non-ASCII letters first, so
they are simply dropped as "not a-z0-9", collapsing surrounding text into extra hyphens or
eating whole syllables. Copied the function verbatim from `git show HEAD:src/squads/_util.py`
into a scratch script and ran it:

```
'Réduire la latence'  -> 'r-duire-la-latence'
'Größe prüfen'        -> 'gr-e-pr-fen'
'Ça marche'           -> 'a-marche'
'日本語のタイトル'      -> 'untitled'          # non-Latin script, see "Known limit" below
operator_slug('Élodie Martin') -> 'op-lodie'
```

`Ça marche` loses its first letter entirely (`Ç` -> nothing, not even a hyphen, because it sits
at the string boundary), and `Größe prüfen` loses enough letters that the result no longer
resembles the source words.

## Consumers (`rg -n "slugify\(" src`)

- `_util.py:26` `operator_slug` — **identity**. `op-<slug>` is the operator's handle, looked up
  by exact string (`sq ... --as op-<slug>`, `--author op-<slug>`, `--assignee op-<slug>`).
  `Élodie Martin` collides-by-mangling into `op-lodie`, which reads as if derived from "Lodie".
- `_roles/_catalog.py:332` `slug = f"{slugify(tech_label)}-dev"` — **identity**. The dev role
  slug (e.g. `dotnet-dev`) is how the role is addressed and resolved against the roster.
  An accented tech label mangles the role slug the same way.
- `_services/_roster.py:107` `add_skill`'s `slug = slugify(name)` — **identity**. Checked for
  collision via `roster_item(ROSTER_SKILL, slug)` and used as the skill's permanent lookup key
  (`sq skill <slug> show`, playbook wiring).
- `_memory/_store.py:76,115` (`_short_slug` / `add`'s `base_slug`) — **identity-ish**. A memory
  entry is addressed by its slug (`sq memory <role> show <slug>`), so a mangled slug is a worse
  address even though the summary/body text is unaffected.
- `_services/_base.py:689` `create`'s `slug = slug or slugify(title)` and
  `_services/_items.py:436` `_rename`'s `new_slug = slugify(new_title)` — **cosmetic**. This is
  the slug segment of a work item's filename (`PREFIX-NNNNNN-<slug>.md`); items are addressed by
  ID, never by this slug, so the only effect is an ugly/uninformative filename.

## Adopter impact

A French or German team titling their own features/tasks/bugs gets filenames like
`FEAT-000042-r-duire-la-latence.md` instead of `feat-000042-reduire-la-latence.md` — readable
but visibly broken in a file listing or `git log --stat`. Worse for the identity consumers: an
operator or dev-role slug derived from an accented name is actively misleading (`op-lodie` for
Élodie, `op-fmilie` for Émilie-ish inputs) rather than just ugly, since that string is what
gets typed and `@mentioned` going forward.

## Fix direction

Before the existing ASCII filter, transliterate:
1. Unicode NFKD-normalise the input.
2. Strip combining marks (`unicodedata.combining(ch)`) — turns `é` into `e`, `ü` into `u`, etc.
3. NFKD leaves some letters untouched because they are not composed of a base letter plus a
   combining mark (they need an explicit map, not decomposition): `ß`→`ss`, `æ`→`ae`, `ø`→`o`,
   `œ`→`oe`, `ł`→`l`, `đ`→`d`.
4. Then apply the existing `[^a-z0-9]+` → `-` filter as today.

## Open decision — existing slugs are not renamed

Fixing `slugify` only changes the slug a *new* item, skill, memory entry, or operator gets from
here on; nothing here proposes renaming files or slugs already on disk under the old buggy
form. Checked what re-derives a slug from a title after the fact, to see if the fix could then
disagree with an existing file:

- **Read** `_services/_items.py`'s `_rename` (used by a retitle) and `_services/_rename.py`
  (bulk type rename): a retitle recomputes `new_slug = slugify(new_title)` **and** moves the
  file to the new name in the same operation — self-consistent, not a source of disagreement.
- **Read** `_services/_retype.py:269`: a type-only rename (`PREFIX` change) reuses the item's
  existing `item.slug` verbatim; it does not call `slugify` again.
- **Read** `_models/_item.py`'s `_slug_from_path`/`from_frontmatter` (the load/repair path):
  the slug is parsed back out of the on-disk filename (`PREFIX-NNNNNN-<slug>.md` -> `<slug>`),
  never recomputed via `slugify(title)`. `sq repair` therefore never disagrees with what a file
  is already named.
- **Inferred, not directly read**: no code path re-derives a slug from a title on unrelated
  writes (body edits, status changes, comments) — `_rename` is only reached when the title
  itself changes.

So the only place old and new slugify behavior could ever meet is an explicit retitle of an
item created before the fix, and that path renames the file to match — it does not leave a
stale reference. No cross-check/migration is needed.

## Known limit (not in scope)

A title in a non-Latin script (CJK, Cyrillic, ...) still falls back to `'untitled'` after this
fix — there is no ASCII/Latin transliteration to fall back on for those scripts. Reproduced
above (`日本語のタイトル` -> `untitled`). Flagging as a known limit of the NFKD-plus-ASCII-filter
approach, not a defect to fix here.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
