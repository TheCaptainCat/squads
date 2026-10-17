"""``comment <hash> show|edit|remove`` on a skill, a role and an operator work as on an item: the
hash is scoped to the entity's one discussion, and system skills and roles take edits and
removals too (a comment is not generated content)."""

import json
import re
from typing import Any

import pytest

import _roster_squad
from squads import _discussion as discussion

pytestmark = pytest.mark.anyio

AUTHOR = "architect"
REGION = re.compile(r"<!-- sq:discussion -->.*?<!-- sq:discussion:end -->", re.S)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return _roster_squad.build(tmp_path_factory.mktemp("roster"))


@pytest.fixture
def squad(built, tmp_path, monkeypatch, frozen_time):
    dest = _roster_squad.restore(built, tmp_path / "squad")
    monkeypatch.chdir(dest)
    return dest


def _rest(squad, kind: str, slug: str) -> str:
    folder = {"skill": "agents/skills", "role": "agents/roles", "operator": "operators"}[kind]
    path = next((squad / "squads" / folder).glob(f"*-{slug}.md"))
    return REGION.sub("<!-- region -->", path.read_text(encoding="utf-8").split("\n---\n", 1)[1])


async def _entries(invoke, kind: str, slug: str) -> list[dict[str, Any]]:
    return json.loads((await invoke([kind, slug, "comments", "--json"])).output)


@pytest.mark.parametrize("shape", list(_roster_squad.SHAPES))
async def test_a_roster_comment_is_shown_edited_and_removed_by_its_hash(squad, invoke, shape):
    kind, slug = _roster_squad.SHAPES[shape]
    seed = await invoke([kind, slug, "comment", "--as", AUTHOR, "-m", "first"])
    assert seed.exit_code == 0, seed.output
    outside = _rest(squad, kind, slug)
    (entry,) = await _entries(invoke, kind, slug)
    item_id = json.loads((await invoke([kind, slug, "show", "--json"])).output)["id"]
    seq = int(item_id.rsplit("-", 1)[1])
    assert entry["hash"] == discussion.comment_hash(seq, "", AUTHOR, entry["ts"], "  - first")

    shown = await invoke([kind, slug, "comment", entry["hash"][:6].upper(), "show", "--json"])
    assert shown.exit_code == 0, shown.output
    record = json.loads(shown.output)
    assert (record["scope"], record["copies"], record["item"]) == (None, 1, item_id)

    edited = await invoke(
        [kind, slug, "comment", entry["hash"][:7], "edit", "--as", AUTHOR, "-m", "second"]
    )
    assert edited.exit_code == 0, edited.output
    (now,) = await _entries(invoke, kind, slug)
    assert now["hash"] != entry["hash"] and now["edited_ts"] is not None
    assert edited.output.rstrip().endswith(now["short_hash"])
    assert _rest(squad, kind, slug) == outside

    stale = await invoke([kind, slug, "comment", entry["hash"][:7], "show"])
    assert stale.exit_code == 1

    gone = await invoke([kind, slug, "comment", now["hash"][:7], "remove", "--as", AUTHOR, "--yes"])
    assert gone.exit_code == 0, gone.output
    assert await _entries(invoke, kind, slug) == []
    assert _rest(squad, kind, slug) == outside
    assert (await invoke(["check"])).exit_code == 0


@pytest.mark.parametrize("shape", list(_roster_squad.SHAPES))
@pytest.mark.parametrize(
    ("args", "code", "text"),
    [
        pytest.param(["a1b2c3d"], 2, "missing verb after a1b2c3d", id="bare-hash"),
        pytest.param(["some text"], 2, "not a comment hash", id="bare-text"),
        pytest.param(["-m", "x", "a1b2c3d", "edit"], 2, "go after the verb", id="options-first"),
    ],
)
async def test_the_grammar_refuses_the_same_shapes_on_a_roster_entity(
    squad, invoke, shape, args, code, text
):
    kind, slug = _roster_squad.SHAPES[shape]

    r = await invoke([kind, slug, "comment", *args])

    assert r.exit_code == code, r.output
    assert text in " ".join(r.output.split())


async def test_another_authors_roster_comment_is_refused(squad, invoke):
    await invoke(["skill", "squads", "comment", "--as", AUTHOR, "-m", "mine"])
    (entry,) = await _entries(invoke, "skill", "squads")

    r = await invoke(
        ["skill", "squads", "comment", entry["hash"][:7], "remove", "--as", "manager", "--yes"]
    )

    assert r.exit_code == 1
    assert "written by architect; --as manager cannot change it" in " ".join(r.output.split())
