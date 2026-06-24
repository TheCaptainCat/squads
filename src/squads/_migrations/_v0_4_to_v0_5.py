"""Schema 0.4 → 0.5 runner: stamp SKILL ids onto existing ``agents/skills/`` body files
and rename them to the ``SKILL-<NNNNNN>-<slug>.md`` convention (ADR-000181, decision #3).

This migration retrofits squads that were created before FEAT-000178 landed.  For each
bundled skill slug, in lexical order (ADR-000181 decision #5):

1. If a **convention-correct** file ``agents/skills/SKILL-<NNNNNN>-<slug>.md`` already
   exists, it is completely skipped (idempotent — re-running after a successful migration
   is a no-op).

2. If a **legacy slug-named** file ``agents/skills/<slug>.md`` exists:

   - If it **has no frontmatter id** (unstamped pre-178 file): allocate a new ``SKILL-…``
     id through ``IndexStore.transaction()`` (invariant #2), stamp sq frontmatter, rename
     the file to the convention name, and rewrite the ``.claude/skills/<slug>/SKILL.md``
     pointer to reference the renamed path.

   - If it **already carries a frontmatter id** (stamped but still slug-named — i.e. our
     own repo's state after a partial migration): extract the id from frontmatter, rename
     to the convention name, and rewrite the pointer.  No new id is allocated.

3. If neither file exists, skip (skill body not written yet; run ``sq sync`` first).

**Ordering parity** (ADR-000181 decision #5): skills are processed in the same
lexical-by-slug order as ``seed_bundled_skills()`` (used by ``sq init``).

**Idempotent** (ADR-000181 decision #4): ids are never reallocated; re-running is a no-op.

**What happens after this runner returns:**
``run_pending_migrations`` (``_services/_maintenance.py``) calls ``repair()`` which
re-reads all ``.md`` files and rebuilds ``.squads.json`` from scratch — the counter
high-water mark is recovered from ``max(sequence_id)`` across all items.

Invoked by ``sq migrate up`` via ``_migrations._registry`` — never run directly
(this module is private).
"""

from pathlib import Path
from typing import Any

from squads import _aio
from squads import _clock as clock
from squads import _sections as sections
from squads._backends._claude_code._frontmatter import oneline
from squads._index._store import IndexStore
from squads._interactions import bundled_skill_slugs, skill_description
from squads._models._enums import ItemType, Status
from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._paths import SquadPaths
from squads._rendering._engine import render

_CLAUDE_DIR = ".claude"
_SKILLS = "skills"
_SKILL_FILE = "SKILL.md"

MANUAL = """\
## Schema 0.4 → 0.5 — SKILL ids and filename convention for existing squads
## (FEAT-000178, ADR-000181)

No manual steps are required.  ``sq migrate up`` automatically:

1. Stamps every bundled skill body file under ``agents/skills/`` with a unique
   ``SKILL-…`` id (if not already stamped).
2. Renames legacy ``<slug>.md`` files to the standard
   ``SKILL-<NNNNNN>-<slug>.md`` convention (like ``ROLE-000001-manager.md``).
3. Rewrites each ``.claude/skills/<slug>/SKILL.md`` pointer to reference the
   renamed body path.
4. Runs ``sq repair`` to rebuild the index.

**Verify with:**

```
sq list -t skill          # all bundled skills should appear with SKILL-… ids
sq skill <n> show         # check a specific skill's frontmatter + body
sq check                  # should be clean
```

**If any skill body file is missing** (e.g. the squad was initialised before
``sq sync`` wrote the skill files), run ``sq sync`` first and then
``sq migrate up`` again.
"""


def _convention_name(slug: str, item_id: str, padding: int) -> str:
    """Return the convention-correct filename for a skill: ``SKILL-<NNNNNN>-<slug>.md``."""
    from squads._paths import number_for_id

    seq = number_for_id(item_id)
    return f"{ItemType.SKILL.prefix}-{seq:0{padding}d}-{slug}.md"


async def _rewrite_pointer(
    root: SquadPaths,
    slug: str,
    description: str,
    new_body_rel: str,
) -> None:
    """Rewrite the ``.claude/skills/<slug>/SKILL.md`` pointer to reference ``new_body_rel``."""
    pointer = root.root / _CLAUDE_DIR / _SKILLS / slug / _SKILL_FILE
    if not pointer.parent.is_dir():
        return  # no .claude dir — nothing to rewrite
    await _aio.write_text(
        pointer,
        render(
            "claude/pointer_skill.md.j2",
            slug=slug,
            description=oneline(description),
            squad_path=new_body_rel,
        ),
    )


async def _backfill_description(
    paths: SquadPaths,
    slug: str,
    convention_path: Path,
    desc: str,
    squad_dir_rel: str,
) -> bool:
    """Backfill description onto an already-convention-named but description-less file.

    Returns True if the file was updated (description was empty/missing), False if it
    already had a description (idempotent skip).
    """
    convention_text = await _aio.read_text(convention_path)
    cfm, _ = sections.split_frontmatter(convention_text)
    if cfm.get("description"):
        return False  # already populated — no-op
    cfm["description"] = desc
    updated = sections.replace_frontmatter(convention_text, cfm)
    await _aio.write_text(convention_path, updated)
    squad_rel = str(cfm.get("path", ""))
    if squad_rel:
        await _rewrite_pointer(paths, slug, desc, f"{squad_dir_rel}/{squad_rel}")
    return True


async def _rename_stamped_legacy(
    paths: SquadPaths,
    slug: str,
    legacy_path: Path,
    skills_folder: Path,
    fm: dict[str, Any],
    desc: str,
    squad_dir_rel: str,
) -> None:
    """Rename an already-stamped but slug-named file to the convention name."""
    item_id = str(fm["id"])
    padding = int(fm.get("id_padding") or 6)
    new_name = _convention_name(slug, item_id, padding)
    new_path = skills_folder / new_name
    await _aio.path_rename(legacy_path, new_path)
    squad_rel = paths.squad_relative(ItemType.SKILL, new_name)
    fm["path"] = squad_rel
    if not fm.get("description"):  # fill-if-empty: don't clobber an operator edit
        fm["description"] = desc
    new_text = await _aio.read_text(new_path)
    await _aio.write_text(new_path, sections.replace_frontmatter(new_text, fm))
    await _rewrite_pointer(paths, slug, desc, f"{squad_dir_rel}/{squad_rel}")


async def migrate(paths: SquadPaths) -> int:
    """Stamp SKILL ids and rename legacy slug-named files to the convention.

    Walks ``agents/skills/`` in lexical-by-slug order (shared ordering primitive,
    ADR-000181 decision #5), allocates a new ``SKILL-…`` id per unstamped file through
    ``IndexStore.transaction()`` (invariant #2), stamps sq frontmatter, renames the file
    to ``SKILL-<NNNNNN>-<slug>.md``, and rewrites the ``.claude`` pointer.

    If a convention file already exists but has an empty description (our own repo state
    before TASK-204 landed), backfills the description from the registry.

    Returns the count of files acted on (stampings + renames + backfills).
    """
    skills_folder = paths.folder_for(ItemType.SKILL)
    if not skills_folder.is_dir():
        return 0

    if not paths.index_path.is_file():
        return 0

    store = IndexStore(paths.index_path, paths.lock_path)
    now = clock.now()
    acted = 0

    for slug in bundled_skill_slugs():
        legacy_path = skills_folder / f"{slug}.md"
        desc = skill_description(slug)
        squad_dir_rel = str(paths.squad_dir.relative_to(paths.root))

        # Check for an already-convention-named file (normal post-migration state).
        existing_convention = list(skills_folder.glob(f"{ItemType.SKILL.prefix}-*-{slug}.md"))
        if existing_convention:
            updated = await _backfill_description(
                paths, slug, existing_convention[0], desc, squad_dir_rel
            )
            if updated:
                acted += 1
            continue

        if not legacy_path.is_file():
            continue  # skill body file not written yet — skip (needs sq sync first)

        existing_text = await _aio.read_text(legacy_path)
        fm, _ = sections.split_frontmatter(existing_text)

        if fm.get("id"):
            # Already stamped but still slug-named: rename + update frontmatter + rewrite pointer.
            await _rename_stamped_legacy(
                paths, slug, legacy_path, skills_folder, fm, desc, squad_dir_rel
            )
            acted += 1
        else:
            # Unstamped: allocate id → stamp → rename → rewrite pointer.
            async with store.transaction() as db:
                item_id = db.allocate_id(ItemType.SKILL)
                new_name = _convention_name(slug, item_id, db.padding)
                squad_rel = paths.squad_relative(ItemType.SKILL, new_name)
                item = Item(
                    sequence_id=db.counter,
                    type=ItemType.SKILL,
                    title=slug,
                    slug=slug,
                    status=Status.ACTIVE,
                    description=desc,
                    author=slug,
                    path=squad_rel,
                    created_at=now,
                    updated_at=now,
                    extra={X.SLUG: slug},
                    id_padding=db.padding,
                )
                stamped_text = sections.join_frontmatter(item.to_frontmatter_dict(), existing_text)
                new_path = skills_folder / new_name
                await _aio.write_text(new_path, stamped_text)
                db.add(item)
            await _aio.path_unlink(legacy_path)
            await _rewrite_pointer(paths, slug, desc, f"{squad_dir_rel}/{squad_rel}")
            acted += 1

    return acted
