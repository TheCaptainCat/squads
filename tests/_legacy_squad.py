"""A squad whose comments carry pre-0.16 headers, built for the header migration's tests: the
roster the current code can create, items with discussions, text injected into any discussion region
the way the released writer would have left it, and a stamp put back to 0.15."""

import tomllib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from _helpers import create_item
from squads import _aio
from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._models._config import SquadsConfig
from squads._paths import SquadPaths
from squads._sections import append_to_section, replace_frontmatter, split_frontmatter
from squads._services._service import Service

TS = "2025-05-20T11:00:00Z"


async def roster(svc: Service) -> None:
    """A role of each kind (bundled, developer, retired, renamed after a comment), an operator
    with an accent, a retired operator, and two entries that share the name ``Sam Lee``."""
    await svc.activate_role("reviewer")
    await svc.add_dev("python")
    await svc.activate_role("devops")
    await _retire(svc, "role", "devops")
    await svc.activate_role("qa", name="Sam Lee")
    await svc.activate_role("architect", name="Mara: the Tester")
    ops = [
        await svc.add_operator("Zoë Müller"),
        await svc.add_operator("Sam Lee"),
        await svc.add_operator("Gone Person"),
    ]
    await _retire(svc, "operator", "op-gone")
    for op in ops:
        legacy_operator_shape(item_file(svc.paths, op), op.title, op.slug)
    for role in await svc.list_items(item_type="role"):
        legacy_shape(
            item_file(svc.paths, role),
            move=("slug", "is_dev", "tech", "model", "is_default"),
        )


async def _retire(svc: Service, item_type: str, slug: str) -> None:
    item = await svc.roster_item(item_type, slug)
    assert item is not None
    await svc.set_roster_status(item.id, "Archived")


async def inject(svc: Service, item_id: str, text: str, tag: str = markers.DISCUSSION) -> Path:
    """Append *text* to the item's discussion region *tag*, byte for byte."""
    item = await svc.get(item_id)
    path = item_file(svc.paths, item)
    updated = append_to_section(path.read_text(encoding="utf-8", newline=""), tag, text)
    path.write_bytes(updated.encode("utf-8"))
    return path


def stamp_behind(root: Path, schema: str = "0.15") -> None:
    config = root / ".squads.toml"
    text = config.read_text(encoding="utf-8")
    current = tomllib.loads(text)["schema_version"]
    config.write_text(
        text.replace(f'schema_version = "{current}"', f'schema_version = "{schema}"'),
        encoding="utf-8",
    )


def reopen(root: Path) -> Service:
    """A service over *root* as its config now reads (after :func:`stamp_behind`)."""
    cfg = SquadsConfig.from_toml_dict(tomllib.loads((root / ".squads.toml").read_text("utf-8")))
    return Service(SquadPaths(root=root, squad_dir=root / cfg.squad_dir, config=cfg))


async def task(svc: Service, title: str = "Target") -> str:
    return (await create_item(svc, "task", title)).item.id


async def read(path: Path) -> str:
    return (await _aio.read_bytes(path)).decode("utf-8")


def legacy_shape(
    path: Path,
    *,
    move: Iterable[str] = (),
    extra: dict[str, Any] | None = None,
    drop: Iterable[str] = (),
) -> None:
    """Rewrite one item file's frontmatter into the nested shape a 0.15 file has: the keys in
    *move* go under ``extra:``, *extra* is added to that block, and *drop* is removed."""
    text = path.read_text(encoding="utf-8")
    data, _ = split_frontmatter(text)
    block: dict[str, Any] = {key: data.pop(key) for key in move if key in data}
    for key in drop:
        data.pop(key, None)
    block.update(extra or {})
    if block:
        data["extra"] = block
    path.write_text(replace_frontmatter(text, data), encoding="utf-8", newline="")


def legacy_operator_shape(
    path: Path,
    name: str,
    slug: str,
    *,
    stored_name: str | None = None,
    stored_slug: bool = True,
    stored_full_name: bool = True,
) -> None:
    """Rewrite an operator file as the released 0.15 tool wrote it: the name and the slug under
    ``extra:`` (``stored_name`` is the ``full_name`` there when it differs from the title)."""
    block: dict[str, Any] = {}
    if stored_slug:
        block["slug"] = slug
    if stored_full_name:
        block["full_name"] = stored_name or name
    legacy_shape(path, drop=("slug",), extra=block)


async def add_legacy_operator(svc: Service, name: str, slug: str, **shape: Any) -> Path:
    """Add an operator and leave its file in the nested 0.15 shape."""
    item = await svc.add_operator(name, slug=slug)
    path = item_file(svc.paths, item)
    legacy_operator_shape(path, name, slug, **shape)
    return path
