"""`sq check` by roster body shape: shape by column.

A role or operator body may hold prose, with or without its tag, and `check` reports nothing for
it; a role that lost its tag and holds no prose is still reported, and a skill with prose beside a
missing tag reports exactly as before. `repair` leaves every body byte-identical (a tagless empty
role is re-seeded), and `show` prints what is stored.
"""

import hashlib
from pathlib import Path

import pytest

from squads._models import _markers as markers
from squads._sections import replace_section
from squads._services import _service as service

pytestmark = pytest.mark.anyio

_ROLE_TAG = markers.open_marker(markers.view_tag("role_definition"))
_PROSE = "Runbook prose for this entry."

#: shape -> (kind, slug, stored body region, whether `check` reports a missing seeded tag)
SHAPES = {
    "role-prose-no-tag": ("role", "manager", _PROSE, False),
    "role-prose-and-tag": ("role", "manager", f"{_PROSE}\n{_ROLE_TAG}", False),
    "role-neither": ("role", "manager", "", True),
    "role-only-tag": ("role", "manager", _ROLE_TAG, False),
    "role-prose-beside-a-truncated-tag": (
        "role",
        "manager",
        f"{_PROSE}\n<!-- sq:view:role_definition",
        True,
    ),
    "role-prose-beside-an-unspaced-truncated-tag": (
        "role",
        "manager",
        f"{_PROSE}\n<!--sq:view:role_definition",
        True,
    ),
    "operator-template": ("operator", "op-alice", None, False),
    "operator-prose": ("operator", "op-alice", _PROSE, False),
    "operator-empty-region": ("operator", "op-alice", "", False),
    "system-skill-prose-no-tag": ("skill", "squads", _PROSE, True),
    "generated-skill-prose-no-tag": ("skill", "sq-task", _PROSE, True),
}


def _file(paths, kind: str, slug: str) -> Path:
    folder = {"role": "roles", "skill": "skills", "operator": "operators"}[kind]
    return next((paths.squad_dir / "agents" / folder).glob(f"*{slug}.md"), None) or next(
        paths.squad_dir.rglob(f"{folder}/*{slug}.md")
    )


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("shape", list(SHAPES))
async def test_check_repair_and_show_by_body_shape(shape, tmp_path, monkeypatch, invoke) -> None:
    monkeypatch.chdir(tmp_path)
    paths = (await service.init(root=tmp_path, roles_spec="all")).paths
    kind, slug, region, reported = SHAPES[shape]
    if kind == "operator":
        assert (await invoke(["operator", "add", "Alice Tester"])).exit_code == 0
    path = _file(paths, kind, slug)
    if region is not None:
        path.write_text(
            replace_section(path.read_text(encoding="utf-8"), markers.BODY, region),
            encoding="utf-8",
        )
    before = _hash(path)

    checked = await invoke(["check"])
    repaired = await invoke(["repair"])
    shown = await invoke([kind, slug, "show", "--raw"])

    assert ("missing seeded view tag" in checked.output) is reported, checked.output
    assert checked.exit_code == (3 if reported else 0), checked.output
    assert repaired.exit_code == 0, repaired.output
    # Repair re-seeds the tag of a tagless, empty role body; every other body is left alone.
    if shape != "role-neither":
        assert _hash(path) == before
    assert shown.exit_code == 0, shown.output
    if region and region != _ROLE_TAG:
        assert _PROSE in shown.output


@pytest.mark.parametrize("opener", ["<!-- sq:", "<!--sq:"], ids=["spaced", "unspaced"])
async def test_a_damaged_role_tag_names_the_role_clear_command(
    opener, tmp_path, monkeypatch, invoke
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = (await service.init(root=tmp_path, roles_spec="all")).paths
    path = _file(paths, "role", "manager")
    path.write_text(
        replace_section(
            path.read_text(encoding="utf-8"),
            markers.BODY,
            f"{_PROSE}\n{opener}view:role_definition",
        ),
        encoding="utf-8",
    )

    checked = await invoke(["check"])

    assert 'sq role manager body -m "" --force' in " ".join(checked.output.split())
    assert "sq skill manager" not in checked.output
