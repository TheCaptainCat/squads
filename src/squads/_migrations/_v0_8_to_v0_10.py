"""Schema 0.8 → 0.10 runner: make ``sq-memory`` a tracked ``SKILL`` item like every other
bundled skill.

``sq-memory`` is the last bundled skill that predates the ``SKILL-<NNNNNN>-<slug>.md``
convention introduced by the 0.4→0.5 migration (see ``_v0_4_to_v0_5.py``): it shipped later,
as a plain ``write_managed``-written body file, never re-run through seeding.  Fresh
``sq init``/``sq sync`` already stamp it correctly (``MEMORY_SKILL`` is in
``bundled_skill_slugs()`` and ``seed_bundled_skills()`` handles it) — this runner exists only
for **existing squads** carrying the legacy untracked file.

Scoped to the single ``sq-memory`` slug (unlike the general 0.4→0.5 sweep, which walked every
bundled skill). Three-branch idempotency, identical in shape to ``_v0_4_to_v0_5``:

1. A convention file ``SKILL-<NNNNNN>-sq-memory.md`` already exists → no-op (already tracked,
   by fresh-init seeding or a prior run of this migration).

2. A legacy ``sq-memory.md`` with **no frontmatter id** exists → allocate a new ``SKILL-…`` id
   through ``IndexStore.transaction()``, stamp sq frontmatter, rename to the convention name,
   and rewrite the ``.claude/skills/sq-memory/SKILL.md`` pointer.

3. A legacy ``sq-memory.md`` that **already carries a frontmatter id** (partially migrated)
   exists → rename to the convention name and rewrite the pointer; no id is (re)allocated.

If neither file exists (the skill body was never written — e.g. a squad initialised before
``sq sync`` ran), this is a no-op; run ``sq sync`` first.

**Frozen vocabulary.** Like every other runner in this package, the type/prefix/folder/status
literals and the skill's description are pinned locally as of this schema version, never read
from the live spec/enum/registry — a migration is a point-in-time snapshot that must stay
immune to future drift. The ``.claude`` pointer is likewise rendered from a frozen point-in-time
template (``claude/pointer_skill.md.j2``, same as ``_v0_4_to_v0_5``), not via a call into the
live backend registry.

**What happens after this runner returns:** ``run_pending_migrations``
(``_services/_maintenance.py``) calls ``repair()``, which rebuilds ``.squads.json`` from
scratch — the counter high-water mark is recovered from ``max(sequence_id)``.

Invoked by ``sq migrate up`` via ``_migrations._registry`` — never run directly (this module is
private).
"""

from squads import _aio
from squads import _clock as clock
from squads import _sections as sections
from squads._backends._claude_code._frontmatter import oneline
from squads._index._store import IndexStore
from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._paths import SquadPaths, number_for_id
from squads._rendering._engine import render

# Frozen v0.8/v0.10 "skill" vocabulary — the type-name/prefix/folder/status literals and this
# skill's description, as they existed at this schema version. NEVER derive these from the live
# spec/enum/registry: a migration is a point-in-time snapshot — the live spec/enum must never be
# re-introduced here.
_SKILL_TYPE = "skill"
_SKILL_PREFIX = "SKILL"
_SKILL_FOLDER = "agents/skills"
_STATUS_ACTIVE = "Active"
_SLUG = "sq-memory"
_DESCRIPTION = (
    "Your role's committed memory notebook and the team bulletin board: check your "
    "index at the start of a run, jot one fact per memory, prune what's stale or wrong, "
    "post/clear board notices, and the memory-vs-board boundary. Use whenever you learn "
    "something worth remembering, or need to announce something to the whole team."
)

_CLAUDE_DIR = ".claude"
_SKILLS = "skills"
_SKILL_FILE = "SKILL.md"

MANUAL = """\
## Schema 0.8 → 0.10 — `sq-memory` becomes a tracked SKILL item

No manual steps are required. `sq migrate up` automatically:

1. Stamps `agents/skills/sq-memory.md` with a unique `SKILL-…` id (if not already stamped).
2. Renames it to the standard `SKILL-<NNNNNN>-sq-memory.md` convention (like every other
   bundled skill, e.g. `SKILL-000001-squads.md`).
3. Rewrites the `.claude/skills/sq-memory/SKILL.md` pointer to reference the renamed body path.
4. Runs `sq repair` to rebuild the index.

A fresh `sq init`/`sq sync` on a squad that never had `sq-memory` already writes it tracked —
this migration only matters for squads that predate that fix.

**Verify with:**

```
sq list -t skill          # sq-memory should appear with a SKILL-… id
sq skill <n> show         # check its frontmatter + body
sq check                  # should be clean
```
"""


def _convention_name(item_id: str, padding: int) -> str:
    """Return the convention-correct filename: ``SKILL-<NNNNNN>-sq-memory.md``."""
    seq = number_for_id(item_id)
    return f"{_SKILL_PREFIX}-{seq:0{padding}d}-{_SLUG}.md"


async def _rewrite_pointer(paths: SquadPaths, new_body_rel: str) -> None:
    """Rewrite the ``.claude/skills/sq-memory/SKILL.md`` pointer to reference *new_body_rel*."""
    pointer = paths.root / _CLAUDE_DIR / _SKILLS / _SLUG / _SKILL_FILE
    if not pointer.parent.is_dir():
        return  # no .claude dir — nothing to rewrite
    await _aio.write_text(
        pointer,
        render(
            "claude/pointer_skill.md.j2",
            slug=_SLUG,
            description=oneline(_DESCRIPTION),
            squad_path=new_body_rel,
        ),
    )


async def migrate(paths: SquadPaths) -> int:
    """Stamp a SKILL id onto the legacy ``sq-memory.md`` body file and rename it to the
    ``SKILL-<NNNNNN>-sq-memory.md`` convention, if needed.

    Returns 1 if a stamping or rename happened, 0 otherwise (already tracked, or the skill
    body file doesn't exist yet).
    """
    skills_folder = paths.squad_dir / _SKILL_FOLDER
    if not skills_folder.is_dir():
        return 0

    # Branch 1: convention-named file already exists — already tracked, nothing to do.
    if list(skills_folder.glob(f"{_SKILL_PREFIX}-*-{_SLUG}.md")):
        return 0

    legacy_path = skills_folder / f"{_SLUG}.md"
    if not legacy_path.is_file():
        return 0  # skill body not written yet — run `sq sync` first

    squad_dir_rel = str(paths.squad_dir.relative_to(paths.root))
    existing_text = await _aio.read_text(legacy_path)
    fm, _ = sections.split_frontmatter(existing_text)

    if fm.get("id"):
        # Branch 3: already stamped but still slug-named — rename + rewrite pointer only.
        item_id = str(fm["id"])
        padding = int(fm.get("id_padding") or 6)
        new_name = _convention_name(item_id, padding)
        new_path = skills_folder / new_name
        await _aio.path_rename(legacy_path, new_path)
        squad_rel = f"{_SKILL_FOLDER}/{new_name}"
        fm["path"] = squad_rel
        if not fm.get("description"):  # fill-if-empty: don't clobber an operator edit
            fm["description"] = _DESCRIPTION
        new_text = await _aio.read_text(new_path)
        await _aio.write_text(new_path, sections.replace_frontmatter(new_text, fm))
        await _rewrite_pointer(paths, f"{squad_dir_rel}/{squad_rel}")
        return 1

    # Branch 2: unstamped legacy file — allocate id → stamp → rename → rewrite pointer.
    if not paths.index_path.is_file():
        return 0
    store = IndexStore(paths.index_path, paths.lock_path)
    now = clock.now()
    async with store.transaction() as db:
        # item_id is the padded filename stem (allocate_id formats at db.padding);
        # deliberately NOT the unpadded displayed Item.id.
        item_id = db.allocate_id(_SKILL_TYPE, prefix=_SKILL_PREFIX)
        new_name = _convention_name(item_id, db.padding)
        squad_rel = f"{_SKILL_FOLDER}/{new_name}"
        item = Item(
            sequence_id=db.counter,
            type=_SKILL_TYPE,
            prefix=_SKILL_PREFIX,
            title=_SLUG,
            slug=_SLUG,
            status=_STATUS_ACTIVE,
            description=_DESCRIPTION,
            author=_SLUG,
            path=squad_rel,
            created_at=now,
            updated_at=now,
            extra={X.SLUG: _SLUG},
        )
        stamped_text = sections.join_frontmatter(item.to_frontmatter_dict(), existing_text)
        new_path = skills_folder / new_name
        await _aio.write_text(new_path, stamped_text)
        db.add(item)
    await _aio.path_unlink(legacy_path)
    await _rewrite_pointer(paths, f"{squad_dir_rel}/{squad_rel}")
    return 1
