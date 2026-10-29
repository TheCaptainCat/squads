"""Schema 0.17 → 0.19 runner. A sub-entity entry is flat: its mapping is stored under ``maps_to``
and every other key beside the core ones is an attribute, so the runner renames each entry's
``story`` to ``maps_to``, lifts each key of its ``extra`` block to the entry's top level and drops
an empty ``severity`` or ``maps_to``. It also puts each item's top-level keys in the order the item
writer emits them, values untouched. Bodies and markers are untouched, and a file that is already
flat and in order is not written, so applying the step again changes nothing. It plans every file
first and refuses the whole run, writing nothing, when an entry holds both ``story`` and a
non-empty ``maps_to``, or an ``extra`` key that is a core key or already sits at the entry's top
level. It runs only through ``sq migrate up`` via ``_migrations._registry``.
"""

from typing import Any, cast

from squads import _aio
from squads._index._store import IndexStore
from squads._itemfile import read_frontmatter, write_text
from squads._migrations._context import MigrationContext
from squads._migrations._outcome import EntriesRefused, MigrationOutcome
from squads._models._attributes import CORE_KEYS
from squads._models._subentity import SUBENTITY_CORE_KEYS
from squads._sections import replace_frontmatter

SUMMARY = (
    "Sub-entity entries are flat: story becomes maps_to, the keys of extra move up beside the "
    "others, and an empty severity is dropped. Item keys keep their values and follow the "
    "writer's order."
)
MANUAL = (
    "Edit what `sq migrate up` does not rewrite. "
    "(1) An override that spells `maps_parent_story`, `subtask_story_mapping` or the transform "
    "`milestone_rollup` is refused at load, so `sq migrate up` stops before any step and changes "
    "nothing until you rename them to `maps_to_parent`, `subentity_mapping` and `status_rollup`. "
    "(2) An override template that reads a name this release removes fails to render: the "
    "sub-entity head no longer receives `severity`, `severity_label` or `story` but `fields` (a "
    "list of `code`, `label` and `badge`) and `mapping` (a `label` and a `value`, or none); an "
    "item's `.priority` and `.severity` are read like any other stored value, with "
    "`item.badge_value('<code>')`; a sub-entity's `.story` is `.maps_to` and its `.extra` is "
    "`.attributes`. "
    "(3) Reflog entries keep the keys they recorded: they are history and are not rewritten."
)

_STORY = "story"
_MAPS_TO = "maps_to"
_EXTRA = "extra"
_SEVERITY = "severity"


def _empty(value: object) -> bool:
    return value is None or value == ""


def _flat_entry(entry: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """*entry* in the flat shape, with the problems that stop it being migrated; the same mapping
    comes back when it needs no change."""
    problems: list[str] = []
    if _STORY in entry and not _empty(entry[_STORY]) and not _empty(entry.get(_MAPS_TO)):
        problems.append(f"holds both {_STORY!r} and a non-empty {_MAPS_TO!r}")
    extra = entry.get(_EXTRA)
    if _EXTRA in entry and not _empty(extra) and not isinstance(extra, dict):
        problems.append(f"has an {_EXTRA!r} that is not a mapping")
    moved = cast("dict[str, Any]", extra) if isinstance(extra, dict) else {}
    top = {k for k in entry if k != _EXTRA}
    problems.extend(
        f"has an {_EXTRA!r} key {key!r} that is a core key"
        if key in SUBENTITY_CORE_KEYS
        else f"has an {_EXTRA!r} key {key!r} that is also a key of the entry"
        for key in moved
        if key in SUBENTITY_CORE_KEYS or key in top
    )
    if problems:
        return entry, problems
    flat: dict[str, Any] = {}
    for key, value in entry.items():
        if key == _STORY:
            if not _empty(value):
                flat[_MAPS_TO] = value
        elif key == _EXTRA:
            flat.update(moved)
        elif key in (_SEVERITY, _MAPS_TO) and _empty(value):
            continue
        else:
            flat[key] = value
    return (entry, []) if flat == entry and list(flat) == list(entry) else (flat, [])


def _flat_entries(
    item_id: str, data: dict[str, Any]
) -> tuple[list[dict[str, Any]] | None, list[str]]:
    """The item's ``subentities`` in the flat shape, ``None`` when none needs a change, and the
    problems found, each naming the item and the sub-entity."""
    raw = data.get("subentities")
    if not isinstance(raw, list):
        return None, []
    entries: list[dict[str, Any]] = []
    problems: list[str] = []
    changed = False
    for position, entry in enumerate(cast("list[Any]", raw), start=1):
        if not isinstance(entry, dict):
            entries.append(cast("dict[str, Any]", entry))
            continue
        old = cast("dict[str, Any]", entry)
        new, found = _flat_entry(old)
        name = old.get("local_id", f"#{position}")
        problems.extend(f"{item_id} {name}: {problem}" for problem in found)
        changed = changed or new is not old
        entries.append(new)
    return (entries if changed else None), problems


def _writer_order(data: dict[str, Any], written: list[str]) -> dict[str, Any]:
    """*data* with its core keys in the order the item writer emits them (*written*) and every
    other key after them in the order the file has them, which is where the writer puts them. A
    core key the writer leaves out when empty keeps its place after the key before it."""
    rank = {key: position for position, key in enumerate(written)}
    last = -1
    ranked: list[tuple[int, str]] = []
    for key in (k for k in data if k in CORE_KEYS):
        last = rank.get(key, last)
        ranked.append((last, key))
    ordered = [key for _, key in sorted(ranked, key=lambda pair: pair[0])]
    ordered.extend(k for k in data if k not in CORE_KEYS)
    return {key: data[key] for key in ordered}


async def migrate(ctx: MigrationContext) -> MigrationOutcome:
    """Plan every item file, refuse on any problem, then rewrite the changed files."""
    store = IndexStore(ctx.paths.index_path, ctx.paths.lock_path, spec=ctx.spec)
    async with store.transaction() as db:
        plans: list[tuple[str, str, dict[str, Any]]] = []
        problems: list[str] = []
        for item in sorted(db.items.values(), key=lambda i: i.sequence_id):
            text = (await _aio.read_bytes(ctx.paths.abspath(item.path))).decode("utf-8")
            data = read_frontmatter(text=text, source=item.path)
            entries, found = _flat_entries(item.id, data)
            problems.extend(found)
            ordered = _writer_order(data, list(item.to_frontmatter_dict()))
            if entries is not None:
                ordered["subentities"] = entries
            if entries is not None or list(ordered) != list(data):
                plans.append((item.path, text, ordered))
        if problems:
            raise EntriesRefused(
                "\n".join(
                    [
                        *problems,
                        f"{len(problems)} problem(s) found; fix the entries by hand.",
                        "This step wrote nothing and the schema stamp is unchanged.",
                    ]
                )
            )
        for path, text, ordered in plans:
            await write_text(
                ctx.paths.abspath(path), replace_frontmatter(text, ordered, source=path)
            )
    return MigrationOutcome(count=len(plans))
