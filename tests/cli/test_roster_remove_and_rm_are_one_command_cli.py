"""`remove` and `rm` are one command on a skill, a role and an operator.

One table: roster shape by verb (`remove`, `rm`) by `--purge`. Each cell pins the bare exit
code, the printed text and the resulting tree; the invariant is that both names leave
byte-identical trees and print the same text from the same start.
"""

import json
import re

import pytest

import _roster_squad
from _helpers import squad_tree

pytestmark = pytest.mark.anyio

KINDS = ("skill", "role", "operator")

#: Shapes the roster's own dependencies keep in place whatever the flags (the text they print).
HELD = {
    "bundled skill": "permanent floor",
    "generated skill": "implied by declared type(s)",
    "system skill with its view dropped": "permanent floor",
}


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return _roster_squad.build(tmp_path_factory.mktemp("roster"))


@pytest.fixture
def squad(built, tmp_path, monkeypatch, frozen_time):
    dest = _roster_squad.restore(built, tmp_path / "squad")
    monkeypatch.chdir(dest)
    return dest


async def _address(invoke, kind: str, slug: str) -> str:
    shown = await invoke([kind, slug, "show", "--json"])
    assert shown.exit_code == 0, shown.output
    return json.loads(shown.output)["id"]


@pytest.mark.parametrize("purge", [False, True], ids=["bare", "purge"])
@pytest.mark.parametrize("verb", ["remove", "rm"])
@pytest.mark.parametrize("shape", list(_roster_squad.SHAPES))
async def test_every_shape_answers_remove_and_rm_the_same_way(squad, invoke, shape, verb, purge):
    kind, slug = _roster_squad.SHAPES[shape]
    item_id = await _address(invoke, kind, slug)
    before = squad_tree(squad)

    result = await invoke([kind, slug, verb, *(["--purge"] if purge else [])])

    flat = " ".join(result.output.split())
    if shape in HELD:
        assert result.exit_code == 1, result.output
        assert f"cannot remove {item_id}" in flat
        assert HELD[shape] in flat
        assert squad_tree(squad) == before
    elif purge:
        assert result.exit_code == 0, result.output
        assert flat.startswith(f"removed {item_id}"), flat
        listed = await invoke(["list", "-t", kind, "-a", "--json"])
        assert item_id not in {row["id"] for row in json.loads(listed.output)}
        claude_md = (squad / "CLAUDE.md").read_text(encoding="utf-8")
        assert f"`{slug}`" not in claude_md and f"({slug})" not in claude_md
    else:
        assert result.exit_code == 1, result.output
        assert f"cannot remove {item_id} without --purge" in flat
        assert f"sq {kind} {item_id} remove --purge" in flat
        assert squad_tree(squad) == before
    check = await invoke(["check"])
    assert check.exit_code == 0, check.output


@pytest.mark.parametrize("purge", [False, True], ids=["bare", "purge"])
@pytest.mark.parametrize("shape", list(_roster_squad.SHAPES))
async def test_remove_and_rm_leave_byte_identical_trees(
    built, tmp_path, monkeypatch, frozen_time, invoke, shape, purge
):
    kind, slug = _roster_squad.SHAPES[shape]
    outcomes = {}
    for verb in ("remove", "rm"):
        dest = _roster_squad.restore(built, tmp_path / verb)
        monkeypatch.chdir(dest)
        result = await invoke([kind, slug, verb, *(["--purge"] if purge else [])])
        outcomes[verb] = (result.exit_code, " ".join(result.output.split()), squad_tree(dest))
    assert outcomes["remove"][0] == outcomes["rm"][0]
    assert re.sub(r"sq (\w+) (\S+) rm", r"sq \1 \2 X", outcomes["remove"][1]) == re.sub(
        r"sq (\w+) (\S+) rm", r"sq \1 \2 X", outcomes["rm"][1]
    )
    assert outcomes["remove"][2] == outcomes["rm"][2]


@pytest.mark.parametrize("kind", KINDS)
async def test_help_lists_remove_and_hides_rm(squad, invoke, kind):
    slug = next(s for k, s in _roster_squad.SHAPES.values() if k == kind)
    result = await invoke([kind, slug, "--help"])
    assert result.exit_code == 0, result.output
    commands = re.findall(r"^│ (\S+)", result.output, re.M)
    assert "remove" in commands
    assert "rm" not in commands
