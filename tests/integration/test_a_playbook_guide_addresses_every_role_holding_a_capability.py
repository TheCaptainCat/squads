"""A playbook guide whose subject is ``*<name>`` addresses every live role that holds capability
``<name>``: those roles preload the type's skill, appear under the guide's section heading and,
when the guide declares ``authors``, gain the type in their create lane.

One table: guide subject by holder state by ``authors``. Each cell compares four surfaces that
must name the same roles.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

from squads import __version__
from squads._errors import SquadsError
from squads._interactions._loader import load_playbook
from squads._roles._catalog import get_catalog
from squads._services._service import open_service
from squads._workflow import bundled_spec

pytestmark = pytest.mark.anyio

_HOLDERS = ("devops", "qa")
_TYPE = "contract"
_SKILL = f"sq-{_TYPE}"


def _write(squad_dir: Path, relative: str, body: str) -> None:
    path = squad_dir / ".overrides" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# squads:override-base:{__version__}\n{body}", encoding="utf-8")


def _guide(subject: str, authors: bool) -> str:
    return (
        f'[types.{_TYPE}]\nroles = [\n    "$(*self)",\n'
        f'    {{ slug = "{subject}", enter = ["read the contract"], do = ["check it"], '
        f"authors = {str(authors).lower()} }},\n]\n"
    )


@dataclass(frozen=True)
class _Cell:
    subject: str
    live: int  # holders left live: 2, 1 or 0 (the rest retired); -1 = nobody declares it
    authors: bool


_SUBJECTS = ["*audit", "*dev", "*reviewer"]
_CELLS = [
    pytest.param(_Cell(s, live, authors), id=f"{s}-live{live}-authors{authors}")
    for s in _SUBJECTS
    for live in (2, 1, 0, -1)
    for authors in (False, True)
    if not (s == "*dev" and authors)  # the bundled guide cannot be restated beside itself
]


async def _roles_listed_under(svc, heading: str) -> list[str]:
    from squads._interactions._skills import item_skill_name
    from squads._workflow import ROSTER_SKILL

    item = await svc.roster_item(ROSTER_SKILL, item_skill_name(_TYPE))
    assert item is not None
    body = await svc.read_body(item.id)
    line = next((ln for ln in body.splitlines() if ln.startswith("## For `" + heading)), "")
    return re.findall(r"\(`([a-z0-9-]+)`\)", line)


async def _arrange(cell: _Cell, project, svc) -> list[str]:
    """Bring the roster and the playbook override into the cell's state; return the live holders."""
    capability = cell.subject[1:]
    roles = {}
    if cell.live != -1:
        for slug in _HOLDERS:
            roles[slug] = await svc.activate_role(slug)
            if capability != "dev":
                _write(
                    project.squad_dir, f"roles/{slug}.toml", f'capabilities = ["{capability}"]\n'
                )
    if capability == "dev":
        # The bundled guide: templated developers hold the capability the [dev] table declares.
        roles = {}
        if cell.live != -1:
            for tech in ("rust", "go"):
                roles[f"{tech}-dev"] = await svc.add_dev(tech)
    holders = list(roles)
    live_holders = holders[: max(cell.live, 0)] if cell.live >= 0 else []
    for slug in holders[len(live_holders) :]:
        await svc.set_status(roles[slug].id, "Archived")

    if capability != "dev":
        _write(project.squad_dir, "playbook.toml", _guide(cell.subject, cell.authors))
    return live_holders


@pytest.mark.parametrize("cell", _CELLS)
async def test_a_capability_guide_reaches_exactly_the_live_holders_on_every_surface(
    cell: _Cell, project, svc, invoke
) -> None:
    live_holders = await _arrange(cell, project, svc)
    capability = cell.subject[1:]

    synced = await invoke(["sync"])
    assert synced.exit_code == 0, synced.output

    # surface 1: the pointer preloads the type's skill
    preloaders = []
    for slug in live_holders:
        pointer = (Path(project.root) / ".claude" / "agents" / f"{slug}.md").read_text("utf-8")
        if f"- {_SKILL}\n" in pointer:
            preloaders.append(slug)
    # surface 2: the section heading lists the holders
    listed = await _roles_listed_under(open_service(), cell.subject)
    # surface 3: the create lane
    lane_members = []
    for slug in live_holders:
        shown = await invoke(["role", slug, "show", "--json"])
        assert shown.exit_code == 0, shown.output
        if _TYPE in json.loads(shown.output)["create_lane"]:
            lane_members.append(slug)

    assert preloaders == live_holders
    assert listed == live_holders
    assert lane_members == (live_holders if cell.authors else [])

    # surface 4: sq check reports an override-declared guide no live role holds, and only that
    checked = await invoke(["check"])
    assert checked.exit_code == 0, checked.output
    reported = "names no live role" in " ".join(checked.output.split())
    declared_by_override = capability != "dev"
    assert reported is (declared_by_override and not live_holders), checked.output


@pytest.mark.parametrize("subject", ["*", "*Audit", "* audit", "*-audit"])
async def test_a_malformed_capability_subject_is_refused_naming_the_file(
    subject: str, project
) -> None:
    _write(project.squad_dir, "playbook.toml", _guide(subject, False))
    with pytest.raises(SquadsError) as excinfo:
        load_playbook(get_catalog(), squad_dir=project.squad_dir, spec=bundled_spec())
    assert "playbook.toml" in str(excinfo.value).replace("\\", "/")
    assert subject in str(excinfo.value)


async def test_the_bundled_dev_guides_are_silent_in_a_squad_with_no_developer(
    project, invoke
) -> None:
    checked = await invoke(["check"])
    assert checked.exit_code == 0, checked.output
    assert "names no live role" not in " ".join(checked.output.split())


@pytest.mark.parametrize("subject", ["*Dev", "nobody"])
async def test_a_refused_playbook_names_its_file_once(subject: str, project, invoke) -> None:
    _write(project.squad_dir, "playbook.toml", _guide(subject, False))
    checked = await invoke(["check"])
    assert checked.exit_code != 0
    assert " ".join(checked.output.split()).count("playbook.toml") == 1, checked.output
