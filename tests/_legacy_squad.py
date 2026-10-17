"""A squad whose comments carry pre-0.16 headers, built for the header migration's tests: the
roster the current code can create, items with discussions, text injected into any discussion region
the way the released writer would have left it, and a stamp put back to 0.15."""

import tomllib
from pathlib import Path

from _helpers import create_item
from squads import _aio
from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._models._config import SquadsConfig
from squads._paths import SquadPaths
from squads._sections import append_to_section
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
    await svc.add_operator("Zoë Müller")
    await svc.add_operator("Sam Lee")
    await svc.add_operator("Gone Person")
    await _retire(svc, "operator", "op-gone")


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
