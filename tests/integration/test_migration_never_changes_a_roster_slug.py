"""Migrating any frozen corpus squad to the current schema leaves every roster entry that was
already there with the same slug and file name, and the slug is a top-level key afterwards."""

import re
import shutil
from pathlib import Path

import pytest

from squads._paths import SquadPaths
from squads._services._service import Service

_CORPUS_DIR = Path(__file__).parent.parent / "fixtures" / "corpus"
_ROSTER_FILE = re.compile(r"(ROLE|SKILL|OP)-\d+-")
_CORPUS_NAMES = sorted(p.name for p in _CORPUS_DIR.iterdir() if p.is_dir())


def _paths(root: Path) -> SquadPaths:
    import tomllib

    from squads._models._config import SquadsConfig

    cfg = SquadsConfig.from_toml_dict(tomllib.loads((root / ".squads.toml").read_text("utf-8")))
    return SquadPaths(root=root, squad_dir=root / cfg.squad_dir, config=cfg)


def _roster(root: Path) -> dict[str, tuple[str | None, bool]]:
    """Roster file name -> (the slug its frontmatter stores, whether it is a top-level key)."""
    out: dict[str, tuple[str | None, bool]] = {}
    for path in sorted(root.rglob("*.md")):
        if not _ROSTER_FILE.match(path.name):
            continue
        front = path.read_text(encoding="utf-8").split("---\n")[1]
        core = re.search(r"^slug: (.+)$", front, re.M)
        stored = re.search(r"^  slug: (.+)$", front, re.M)
        found = core or stored
        out[path.name] = (found.group(1) if found else None, core is not None)
    return out


@pytest.mark.parametrize("corpus", _CORPUS_NAMES)
async def test_every_existing_roster_entry_keeps_its_slugs_and_file_name(
    corpus: str, tmp_path: Path
) -> None:
    root = tmp_path / corpus
    shutil.copytree(_CORPUS_DIR / corpus, root)
    before = _roster(root)

    await Service(_paths(root)).run_pending_migrations()

    after = _roster(root)
    assert before, f"corpus {corpus!r} holds no roster entry to protect"
    assert {name: (after[name][0]) for name in before} == {n: b[0] for n, b in before.items()}
    assert all(after[name][1] for name in before), "a roster slug is not a top-level key"
