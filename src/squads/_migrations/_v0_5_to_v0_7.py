"""Schema 0.5 → 0.7 runner: unpad every human-facing ID.

Display padding is fixed at 0 (:data:`squads._models._item.DISPLAY_ID_PADDING`) — every
human-facing surface (frontmatter ``id:``, ``refs:``, ``parent:``, and ID mentions in body
prose) should read ``PREFIX-nnn`` rather than ``PREFIX-000nnn``. Filenames are unaffected:
they stay padded at the squad's stored (filename) width and are never renamed by this runner.

Two passes over the corpus:

1. **Discovery.** Read every item file once and build a single ``{old literal id → new unpadded
   id}`` map from each item's *own* current frontmatter ``id:`` string — the "old form" this
   migration already knows, whatever width it happens to be on disk (repad may have widened it
   past the historical default of 6).

2. **Rewrite.**
   - *Structural* (deterministic): reformat each file's own frontmatter ``id:`` from
     ``(item_type.prefix, sequence_id)`` and unpad every ``refs:`` entry / ``parent:`` field by
     re-parsing the trailing digits of the stored ref string — the same width-tolerant identity
     ``ref_id_matches`` already relies on, so no cross-file lookup is needed for refs.
   - *Prose* (bounded, best-effort): substitute occurrences of the exact old-form literals from
     the discovery map, whole-word (``\\bOLD\\b``), across the body **and** sub-entity
     (``subentities[*].title``) frontmatter fields — never a blind zero-collapsing regex.
     Fenced code blocks and inline code spans are left untouched (an ID inside one may be a
     literal example, not a real mention), matching how the renumber path scopes its own
     mention rewrites (:func:`squads._itemfile.rewrite_ids`). A padded id immediately followed
     by a filename tail (``-slug.md``) is also left alone — it is the stem of an on-disk
     filename reference, which stays padded; unpadding it would corrupt a valid path into
     one that doesn't exist.

Filenames are untouched (already width-padded and stay so — no renames, no path-index churn
beyond what the trailing ``sq repair`` already does after every migration batch runs).

Custom (spec-declared) item types are **not** covered — :func:`_iter_files` only walks the
built-in type folders (frozen local constants, not the live spec), matching every other
runner in this package (none of them thread the active spec). See ``MANUAL`` below.

Idempotent: once every id/ref/parent/mention is unpadded, the discovery map is empty and the
second pass is a no-op.

Invoked by ``sq migrate up`` via ``_migrations._registry`` — never run directly (this module is
private).
"""

import re
from pathlib import Path
from typing import Any, cast

from squads._models._item import (
    DISPLAY_ID_PADDING,
    format_item_id,
    make_ref,
    split_ref,
)
from squads._paths import SquadPaths
from squads._sections import join_frontmatter, split_frontmatter

#: Fenced code blocks (```…```, DOTALL so they can span lines) or inline code spans (`…`,
#: single line). Tried in this order so a fenced block is not mistaken for two inline spans.
_CODE_SPAN_RE = re.compile(r"(```.*?```|`[^`\n]*`)", re.DOTALL)

# Frozen v0.5/v0.7 built-in type vocabulary — the prefix/folder literals as they existed at
# this schema version. NEVER derive this from the live spec/enum: a migration is a
# point-in-time snapshot — the live spec/enum must never be re-introduced here.
_TYPES: tuple[tuple[str, str], ...] = (
    ("EPIC", "epics"),
    ("FEAT", "features"),
    ("TASK", "tasks"),
    ("BUG", "bugs"),
    ("ADR", "adrs"),
    ("REV", "reviews"),
    ("GUIDE", "guides"),
    ("ROLE", "agents/roles"),
    ("SKILL", "agents/skills"),
    ("OP", "operators"),
)

MANUAL = """\
## Schema 0.5 → 0.7 — unpadded display IDs

No manual steps are required for the structural rewrite — `sq migrate up` automatically:

1. Reformats every item's frontmatter `id:` to the unpadded form (`PREFIX-nnn` rather than
   `PREFIX-000nnn`), driven by its stored `sequence_id`.
2. Unpads every `refs:` entry and `parent:` field.
3. Rewrites padded-ID mentions in body prose and sub-entity titles to their unpadded form,
   skipping fenced code blocks and inline code (a literal example ID there is left as written)
   and skipping a padded id that is the stem of an on-disk filename reference (`PREFIX-000nnn-
   slug.md` stays exactly as written — filenames are never unpadded).
4. Runs `sq repair` to rebuild the index.

**Filenames are not touched** — they stay padded on disk; only content changes.

**The prose rewrite is best-effort.** It only catches the exact padded strings this migration
already knows about (each item's own prior frontmatter `id:`), whole-word matched. A body that
mentions an ID some other unusual way, or a mention-heavy body, is worth an eyeball after
migrating — run `sq <type> <n> show --full` on a few high-traffic items and confirm the prose
reads as expected.

**Custom (spec-declared) item types are not covered.** This runner only walks the built-in
item-type folders (role/skill/operator/epic/feature/task/bug/decision/review/guide) — a squad
with config-driven custom types (`.squads.toml` item specs) has those files, their refs, and
any prose mentions of their ids left entirely untouched by this migration. If your squad
declares custom types, give them a manual eyeball/pass after `sq migrate up`: unpad their
frontmatter `id`/`refs`/`parent` by hand (or re-`sq create`/re-derive as appropriate) and check
any built-in item's prose that mentions one of their (now stale-padded) ids.

**Verify with:**

```
sq check                  # should be clean
sq list                   # ids render unpadded
sq tree PREFIX-n           # resolves and renders unpadded (any valid epic id works)
```
"""


def _unpad_ref(ref: str) -> str:
    """Unpad a ``refs:``/``parent:`` entry (``"ID"`` or ``"ID:kind"``) from its own digits.

    Refs are width-tolerant identity strings (mirrors ``ref_id_matches``): the trailing digit
    run already carries the sequence number, so no cross-file lookup is needed — just reparse
    and reformat at :data:`DISPLAY_ID_PADDING`.
    """
    rid, kind = split_ref(ref)
    prefix, _, digits = rid.rpartition("-")
    if not (prefix and digits.isdigit()):
        return ref  # malformed — leave untouched rather than guess
    return make_ref(format_item_id(prefix, int(digits), DISPLAY_ID_PADDING), kind)


#: A padded id immediately followed by a filename tail (``-slug.md``) is the stem of an
#: on-disk filename reference, not a bare mention — filenames stay padded, so unpadding
#: here would rewrite a valid path into one that doesn't exist. Skip those: a missed bare
#: mention is a harmless best-effort miss, but corrupting a valid filename reference is
#: active, silent, one-way damage — skipping is the safe direction.
_FILENAME_TAIL = r"(?!-[a-z0-9][a-z0-9-]*\.md)"


def _rewrite_mentions(body: str, id_map: dict[str, str]) -> str:
    """Whole-word substitute every ``old → new`` literal in *body*, skipping code spans.

    A bare mention (``PREFIX-nnn``) is rewritten; the same literal as the stem of a filename
    reference (``PREFIX-000nnn-slug.md``) is left alone (:data:`_FILENAME_TAIL`).
    """
    if not id_map:
        return body
    mention_re = re.compile(
        "|".join(
            rf"\b{re.escape(old)}\b{_FILENAME_TAIL}"
            for old in sorted(id_map, key=len, reverse=True)
        )
    )
    parts = _CODE_SPAN_RE.split(body)
    for i, part in enumerate(parts):
        if i % 2 == 0:  # even indices are prose; odd indices are the captured code spans
            parts[i] = mention_re.sub(lambda m: id_map[m.group(0)], part)
    return "".join(parts)


def _iter_files(paths: SquadPaths) -> list[tuple[Path, str]]:
    """Every item file across the built-in type folders, as (path, prefix) pairs."""
    files: list[tuple[Path, str]] = []
    for prefix, folder_name in _TYPES:
        folder = paths.squad_dir / folder_name
        if not folder.is_dir():
            continue
        files.extend((md, prefix) for md in sorted(folder.glob(f"{prefix}-*.md")))
    return files


def migrate(paths: SquadPaths) -> int:
    """Unpad every item's frontmatter id/refs/parent and body-prose ID mentions.

    Returns the count of files whose content changed. Filenames are never touched.
    """
    files = _iter_files(paths)

    # Pass 1 — discovery: read everything once, build the {old id literal -> new unpadded id}
    # map from each item's own current frontmatter id, before anything is rewritten.
    raw: dict[Path, str] = {}
    id_map: dict[str, str] = {}
    for md, prefix in files:
        text = md.read_text(encoding="utf-8")
        raw[md] = text
        fm, _ = split_frontmatter(text)
        old_id = fm.get("id")
        seq = fm.get("sequence_id")
        if not old_id or seq is None:
            continue
        new_id = format_item_id(prefix, int(seq), DISPLAY_ID_PADDING)
        if new_id != old_id:
            id_map[str(old_id)] = new_id

    # Pass 2 — rewrite: structural frontmatter fields, then bounded/fence-skipping prose.
    changed = 0
    for md, prefix in files:
        text = raw[md]
        fm, body = split_frontmatter(text)
        if "id" not in fm or "sequence_id" not in fm:
            continue  # unstamped file — nothing to unpad

        fm["id"] = format_item_id(prefix, int(fm["sequence_id"]), DISPLAY_ID_PADDING)
        if fm.get("parent"):
            fm["parent"] = _unpad_ref(str(fm["parent"]))
        if fm.get("refs"):
            fm["refs"] = [_unpad_ref(str(r)) for r in fm["refs"]]
        # Sub-entity titles live in frontmatter too — same bounded/guarded rewrite as body
        # prose, so a mention like "tie into FEAT-n contract" in a story/subtask/finding
        # title unpads just like it does in the surrounding body.
        for sub in cast("list[dict[str, Any]]", fm.get("subentities") or []):
            if sub.get("title"):
                sub["title"] = _rewrite_mentions(str(sub["title"]), id_map)

        new_body = _rewrite_mentions(body, id_map)
        new_text = join_frontmatter(fm, new_body)
        if new_text != text:
            md.write_text(new_text, encoding="utf-8")
            changed += 1

    return changed
