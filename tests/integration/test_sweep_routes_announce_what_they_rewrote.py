"""Every command that reaches the corpus sweep announces the content it rewrote.

The sweep that strips retired regions is reached by four commands, none of which advertises
rewriting content: ``repair`` and ``renumber`` advertise the index, ``migrate up`` advertises
the schema, ``adopt`` advertises an import. The mitigation the design was accepted on is that
the rewrite is *announced*, not prevented — so an unannounced route is the whole defect, and
the property is one every route has to hold rather than a line in one command.

This is a family assertion, deliberately: the first fix here covered the route that had been
looked at, and two of the four still said nothing afterwards because the reasoning ran from
the shared core outwards instead of from each door inwards. A new door added to the table
below fails until it is wired to the shared sentence.

Each case is asserted against a real rewrite — the corpus's own bytes before and after — so a
route that announced a strip it did not perform, or stopped performing one, fails here too.
"""

import json
import re
import shutil
import tomllib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from squads._models import _markers as markers
from squads._models._config import SquadsConfig
from squads._paths import SquadPaths
from squads._services import _service as service

_CORPUS_DIR = Path(__file__).parent.parent / "fixtures" / "corpus"

#: The one sentence every sweep-reaching command prints, as an operator reads it off stdout.
#: Matched as a pattern rather than compared to the constructor's own output so a route that
#: silently grew its own phrasing fails instead of agreeing with itself.
_NOTICE = re.compile(r"stripped retired regions from (\d+) item files? — review the diff")

#: How many item files a staged corpus must hold before its "the sweep rewrote something"
#: precondition means anything. A staging step that produced an empty (or nearly empty) tree
#: would let the strip assertions below pass over a corpus with nothing in it to strip.
_MIN_CORPUS = 4

#: How the two retired region families read on disk: the stored roll-up table, and a
#: sub-entity's stored badge line. Matched on the file's own bytes rather than by asking the
#: sweep what it considers retired — a test that reads its subject's list would keep passing if
#: that list emptied.
_RETIRED_REGION = re.compile(r"<!-- sq:(?:summary|[^>]*:head) -->")


@dataclass(frozen=True)
class _Route:
    """One door onto the corpus sweep: how to stage a corpus it will rewrite, and the argv."""

    name: str
    stage: Callable[[Path], Awaitable[tuple[Path, Path]]]  # tmp_path -> (cwd, squad_dir)
    argv: list[str]


def _paths_of(root: Path) -> SquadPaths:
    with (root / ".squads.toml").open("rb") as fh:
        cfg = SquadsConfig.from_toml_dict(tomllib.load(fh))
    return SquadPaths(root=root, squad_dir=root / cfg.squad_dir, config=cfg)


#: An item file's name, the only markdown the corpus sweep visits: ``<PREFIX>-<digits>[-slug].md``.
#: Generated skill bodies (``greeting.md``) sit in the same tree and carry marker regions of
#: their own, so a bare ``rglob("*.md")`` both plants regions the sweep will never reach and
#: then reports them as survivors.
_ITEM_FILE = re.compile(r"^[A-Z][A-Z0-9-]*-\d+(?:-[^/]*)?\.md$")


def _md_files(squad_dir: Path) -> list[Path]:
    return sorted(p for p in squad_dir.rglob("*.md") if p.is_file() and _ITEM_FILE.match(p.name))


def _plant_retired_region(squad_dir: Path, *, count: int = 2) -> int:
    """Give *count* item files a stored ``sq:summary`` region — the retired shape a corpus
    written before the roll-up became a computed rendering still carries on disk.

    Written here as raw marker text rather than through a writer, because the point is a shape
    no live writer produces any more: there is nothing left in the product that could plant it.
    """
    region = (
        f"{markers.open_marker(markers.SUMMARY)}\n\n"
        "| # | Title |\n| - | - |\n| S1 | a stale rendering |\n\n"
        f"{markers.close_marker(markers.SUMMARY)}\n\n"
    )
    planted = 0
    for md in _md_files(squad_dir):
        text = md.read_text()
        anchor = markers.open_marker(markers.BODY)
        if anchor not in text:
            continue
        md.write_text(text.replace(anchor, region + anchor, 1))
        planted += 1
        if planted == count:
            break
    return planted


async def _fresh_squad(tmp_path: Path) -> tuple[Path, Path]:
    """A current-schema squad whose corpus carries retired regions."""
    result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    svc = service.Service(result.paths)
    await svc.create("task", "Wire the importer", author="manager")
    await svc.create("feature", "Importer", author="manager")
    await svc.create("bug", "Importer drops the last row", author="manager")
    assert _plant_retired_region(result.paths.squad_dir) == 2
    return tmp_path, result.paths.squad_dir


async def _unindexed_squad(tmp_path: Path) -> tuple[Path, Path]:
    """The same corpus with its index removed — a folder of squads-native markdown meeting sq
    for the first time, which is the population ``adopt`` exists for."""
    root, squad_dir = await _fresh_squad(tmp_path)
    (squad_dir / ".squads.json").unlink()
    (squad_dir / ".reflog.jsonl").unlink(missing_ok=True)
    return root, squad_dir


async def _legacy_corpus(tmp_path: Path) -> tuple[Path, Path]:
    """A frozen pre-current-schema squad — the only corpus ``migrate up`` will act on."""
    dst = tmp_path / "v0_11"
    shutil.copytree(_CORPUS_DIR / "v0_11", dst)
    return dst, _paths_of(dst).squad_dir


_ROUTES: list[_Route] = [
    _Route("repair", _fresh_squad, ["repair"]),
    _Route("renumber", _fresh_squad, ["renumber", "--from", "1", "--by", "100"]),
    _Route("adopt", _unindexed_squad, ["adopt", "--no-claude"]),
    _Route("migrate-up", _legacy_corpus, ["migrate", "up"]),
]


def _stripped_in_reflog(squad_dir: Path) -> list[str]:
    """Every item id any reflog line of this run records as content-rewritten."""
    log = squad_dir / ".reflog.jsonl"
    if not log.exists():
        return []
    out: list[str] = []
    for line in log.read_text().splitlines():
        if not line.strip():
            continue
        delta = json.loads(line).get("delta") or {}
        out.extend(delta.get("stripped") or [])
    return out


@pytest.mark.parametrize("route", _ROUTES, ids=lambda r: r.name)
async def test_a_sweep_route_states_the_content_diff_it_produced(
    route: _Route, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invoke
) -> None:
    cwd, squad_dir = await route.stage(tmp_path)
    corpus = _md_files(squad_dir)
    assert len(corpus) >= _MIN_CORPUS, (
        f"staging for {route.name!r} produced {len(corpus)} item file(s) — too small for the "
        "rewrite assertions below to mean anything"
    )
    # Carried content, not file identity: `renumber` renames every file it shifts, so a
    # before/after comparison keyed by path sees an empty intersection and would report "no
    # rewrite" on the very route that rewrote the most.
    carriers = [path.name for path in corpus if _RETIRED_REGION.search(path.read_text())]
    assert len(carriers) >= 2, (
        f"precondition: staging for {route.name!r} left {len(carriers)} file(s) carrying a "
        "retired region, so there is nothing for the sweep to strip"
    )
    monkeypatch.chdir(cwd)

    result = await invoke(route.argv)

    assert result.exit_code == 0, result.output
    survivors = [p.name for p in _md_files(squad_dir) if _RETIRED_REGION.search(p.read_text())]
    assert not survivors, f"precondition: {route.name!r} stripped nothing — {survivors}"
    match = _NOTICE.search(result.output)
    assert match, f"{route.name!r} rewrote content and said nothing:\n{result.output}"
    assert int(match.group(1)) > 0
    assert _stripped_in_reflog(squad_dir), (
        f"{route.name!r} left no record of the rewrite in the reflog either"
    )
