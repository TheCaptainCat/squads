"""File I/O for agent memory: one slug-named ``.md`` per memory under
``squads/agents/memory/<role-slug>/``, plus the shared ``.index.jsonl`` roll-up
(:mod:`squads._content_index`).

Memory is **off the global counter and outside ``.squads.json``**: nothing here allocates a
counter id, opens ``IndexStore``, or touches the index — ``sq repair`` has nothing to rebuild
because there is nothing here for it to know about. Content files are marker-free (freeform,
agent-owned body — see :mod:`squads._memory._model`).
"""

from pathlib import Path

from squads import _aio
from squads import _clock as clock
from squads._content_index import INDEX_FILENAME, IndexEntry, parse_index, regenerate
from squads._errors import SquadsError
from squads._memory._model import MemoryEntry
from squads._paths import SquadPaths
from squads._sections import join_frontmatter, split_frontmatter
from squads._util import slugify

#: Squad-relative root for every role's memory pool: ``<squad_dir>/agents/memory/<role-slug>/``.
MEMORY_ROOT = "agents/memory"


class MemoryNotFoundError(SquadsError):
    """Raised when a memory slug does not exist in a role's pool."""


def role_folder(paths: SquadPaths, role_slug: str) -> Path:
    """The folder holding one role's memory pool + its ``.index.jsonl``."""
    return paths.abspath(f"{MEMORY_ROOT}/{role_slug}")


def memory_path(paths: SquadPaths, role_slug: str, slug: str) -> Path:
    """The ``.md`` file for one memory, addressed by its stable slug."""
    return paths.abspath(f"{MEMORY_ROOT}/{role_slug}/{slug}.md")


async def _content_files(folder: Path) -> list[Path]:
    """Every memory ``.md`` in *folder*, sorted by filename. Empty if the folder is absent."""
    if not await _aio.path_exists(folder):
        return []
    return await _aio.to_thread(lambda: sorted(folder.glob("*.md")))


async def _unique_slug(folder: Path, base_slug: str) -> str:
    """*base_slug* if free, else the first ``<base_slug>-2``, ``-3``, ... not already on disk.

    A memory file is addressed purely by its slug (no counter prefix disambiguates it the way
    an item's ``<ID>-<slug>.md`` does), so a same-slug second fact gets a numeric suffix rather
    than clobbering or hard-erroring — still a human-meaningful id, never a sequence number.
    """
    if not await _aio.path_exists(folder / f"{base_slug}.md"):
        return base_slug
    n = 2
    while await _aio.path_exists(folder / f"{base_slug}-{n}.md"):
        n += 1
    return f"{base_slug}-{n}"


async def _regenerate_index(folder: Path) -> None:
    """Rebuild *folder*'s ``.index.jsonl`` whole from its current ``.md`` files."""
    entries: list[IndexEntry] = []
    for path in await _content_files(folder):
        text = await _aio.read_text(path)
        frontmatter, _ = split_frontmatter(text)
        entries.append(
            IndexEntry(
                slug=path.stem,
                filename=path.name,
                description=str(frontmatter.get("summary", "")),
            )
        )
    await regenerate(folder, entries)


async def add(
    paths: SquadPaths,
    role_slug: str,
    fact: str,
    *,
    body: str | None = None,
    tags: list[str] | None = None,
) -> MemoryEntry:
    """Write a new memory: ``<slug>.md`` (slug derived from *fact*) + regenerate the index.

    *fact* is both the source of the slug and the frontmatter one-line ``summary``. *body*
    supplies the freeform markdown body (``--file`` content at the CLI edge); it defaults to
    *fact* itself so a bare ``add "<fact>"`` still yields a readable memory. No counter id is
    allocated and ``.squads.json`` is never touched.
    """
    fact = fact.strip()
    if not fact:
        raise SquadsError("a memory needs a non-empty fact/summary")
    folder = role_folder(paths, role_slug)
    slug = await _unique_slug(folder, slugify(fact))
    entry = MemoryEntry(
        slug=slug,
        summary=fact,
        created_at=clock.iso(clock.now()),
        body=(body if body is not None else fact).strip(),
        tags=tuple(tags or ()),
    )
    text = join_frontmatter(entry.to_frontmatter_dict(), entry.body)
    await _aio.mkdir(folder, parents=True, exist_ok=True)
    await _aio.write_text(folder / f"{slug}.md", text)
    await _regenerate_index(folder)
    return entry


async def read(paths: SquadPaths, role_slug: str, slug: str) -> MemoryEntry:
    """Read one memory back by slug. A read never mutates anything."""
    path = memory_path(paths, role_slug, slug)
    if not await _aio.path_exists(path):
        raise MemoryNotFoundError(f"no memory {slug!r} for role {role_slug!r}")
    text = await _aio.read_text(path)
    frontmatter, body = split_frontmatter(text)
    return MemoryEntry.from_frontmatter(slug, frontmatter, body.strip("\n"))


async def list_entries(paths: SquadPaths, role_slug: str) -> list[MemoryEntry]:
    """All memories in a role's pool, in filename (slug) order. Empty pool -> ``[]``, no error."""
    folder = role_folder(paths, role_slug)
    out: list[MemoryEntry] = []
    for path in await _content_files(folder):
        text = await _aio.read_text(path)
        frontmatter, body = split_frontmatter(text)
        out.append(MemoryEntry.from_frontmatter(path.stem, frontmatter, body.strip("\n")))
    return out


async def search(
    paths: SquadPaths, role_slug: str, query: str
) -> list[tuple[MemoryEntry, list[str]]]:
    """Memories whose summary or body contains *query* (case-insensitive substring).

    A plain content grep over the role's ``.md`` files — mirrors
    :meth:`squads._services._collab.CollabMixin.search`'s shape (entry, matching lines).
    An unknown/empty role pool simply yields no matches, consistent with :func:`list_entries`.
    """
    needle = query.strip().lower()
    if not needle:
        raise SquadsError("search needs a non-empty query")
    out: list[tuple[MemoryEntry, list[str]]] = []
    for entry in await list_entries(paths, role_slug):
        candidates = [entry.summary, *entry.body.splitlines()]
        hits = [ln.strip() for ln in candidates if ln and needle in ln.lower()]
        if hits:
            out.append((entry, hits))
    return out


async def read_index(paths: SquadPaths, role_slug: str) -> list[IndexEntry]:
    """Read back *role_slug*'s generated ``.index.jsonl`` (entry lines only, header dropped).

    Boot surfacing reads this directly rather than :func:`list_entries` — the index already
    holds exactly what gets surfaced (slug + one-line description), so there's no need to
    reopen every memory's ``.md`` file just to re-read a summary already rolled up. Missing
    folder/index -> ``[]`` (an empty pool surfaces nothing), never an error.
    """
    index_path = role_folder(paths, role_slug) / INDEX_FILENAME
    if not await _aio.path_exists(index_path):
        return []
    _, entries = parse_index(await _aio.read_text(index_path))
    return entries


async def forget(paths: SquadPaths, role_slug: str, slug: str) -> None:
    """Delete a memory's file for real (history retained in git) + regenerate the index.

    Raises :class:`MemoryNotFoundError` if *slug* doesn't exist — forgetting is not a silent
    no-op on an already-gone memory.
    """
    path = memory_path(paths, role_slug, slug)
    if not await _aio.path_exists(path):
        raise MemoryNotFoundError(f"no memory {slug!r} for role {role_slug!r}")
    await _aio.path_unlink(path)
    await _regenerate_index(role_folder(paths, role_slug))
