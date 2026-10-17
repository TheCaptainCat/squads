"""The verbs a roster group names in its missing-verb error and its help come from the commands
registered on the addressed subgroup: every visible verb, and no hidden alias."""

import re

import pytest

import _roster_squad

pytestmark = pytest.mark.anyio

GROUPS = {"skill": "squads", "role": "manager", "operator": "op-ada"}
VERBS = {"show", "remove", "comment", "comments", "status"}


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return _roster_squad.build(tmp_path_factory.mktemp("roster"))


@pytest.fixture
def squad(built, tmp_path, monkeypatch, frozen_time):
    dest = _roster_squad.restore(built, tmp_path / "squad")
    monkeypatch.chdir(dest)
    return dest


@pytest.mark.parametrize("group", list(GROUPS))
async def test_the_missing_verb_error_lists_the_visible_verbs(squad, invoke, group):
    result = await invoke([group, GROUPS[group]])
    assert result.exit_code == 1, result.output
    listed = set(" ".join(result.output.split()).split("<slug|id|n> ")[1].split("|"))
    assert listed >= VERBS
    assert "rm" not in listed
    assert "_addr" not in result.output


@pytest.mark.parametrize("group", list(GROUPS))
async def test_the_help_epilog_lists_the_same_verbs(squad, invoke, group):
    result = await invoke([group, "--help"])
    assert result.exit_code == 0, result.output
    flat = " ".join(result.output.split())
    line = re.search(r"VERB is one of ([\w,\s-]+?)\. Examples", flat)
    assert line, flat
    listed = set(line.group(1).replace(" ", "").split(","))
    assert listed >= VERBS
    assert "rm" not in listed
    assert "{verbs}" not in flat
