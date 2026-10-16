"""``comment`` and ``comments`` on a skill, a role and an operator behave as they do on an item.

One table: roster shape by verb. A comment needs ``--as``, is stored under the permanent-slug
header, changes nothing outside the discussion region, reaches ``sq inbox`` through an
``@mention`` and reads back with ``author_slug``. System skills and roles take comments too.
"""

import json
import re

import pytest

import _roster_squad
from _helpers import squad_tree

pytestmark = pytest.mark.anyio

HEADER = re.compile(r"^- \[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\] `([a-z0-9-]+)` (.+):$", re.M)
REGION = re.compile(r"<!-- sq:discussion -->.*?<!-- sq:discussion:end -->", re.S)
#: Shapes the inbox leaves out, as it leaves out any entry in a terminal status.
RETIRED = {"retired role", "retired operator"}
AUTHOR = "architect"
MENTIONED = "manager"


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return _roster_squad.build(tmp_path_factory.mktemp("roster"))


@pytest.fixture
def squad(built, tmp_path, monkeypatch, frozen_time):
    dest = _roster_squad.restore(built, tmp_path / "squad")
    monkeypatch.chdir(dest)
    return dest


def _file(squad, kind: str, slug: str):
    folder = {"skill": "skills", "role": "roles", "operator": "operators"}[kind]
    root = squad / "squads"
    pattern = f"*-{slug}.md"
    return next((root / ("agents/" + folder if kind != "operator" else folder)).glob(pattern))


def _outside_region(text: str) -> str:
    body = text.split("\n---\n", 1)[1]
    return REGION.sub("<!-- region -->", body)


@pytest.mark.parametrize("via", ["-m", "--file"])
@pytest.mark.parametrize("shape", list(_roster_squad.SHAPES))
async def test_a_comment_is_stored_read_back_and_mentioned(squad, invoke, tmp_path, shape, via):
    kind, slug = _roster_squad.SHAPES[shape]
    path = _file(squad, kind, slug)
    before = path.read_text(encoding="utf-8")
    text = f"checked, over to @{MENTIONED}"
    if via == "-m":
        args = ["-m", text]
    else:
        note = tmp_path / "note.md"
        note.write_text(text + "\n", encoding="utf-8")
        args = ["--file", str(note)]

    result = await invoke([kind, slug, "comment", "--as", AUTHOR, *args])

    assert result.exit_code == 0, result.output
    after = path.read_text(encoding="utf-8")
    headers = HEADER.findall(after)
    assert [h[0] for h in headers] == [AUTHOR]
    assert _outside_region(after) == _outside_region(before)
    assert text in after

    as_json = await invoke([kind, slug, "comments", "--json"])
    assert as_json.exit_code == 0, as_json.output
    rows = json.loads(as_json.output)
    assert [r["author_slug"] for r in rows] == [AUTHOR]
    assert text in rows[0]["body"]
    plain = await invoke([kind, slug, "comments"])
    assert plain.exit_code == 0, plain.output
    assert text.split(",")[0] in plain.output

    shown = await invoke([kind, slug, "show", "--comments"])
    assert shown.exit_code == 0, shown.output
    assert text.split(",")[0] in shown.output
    item_id = json.loads((await invoke([kind, slug, "show", "--json"])).output)["id"]
    inbox = await invoke(["inbox", MENTIONED, "--json"])
    assert inbox.exit_code == 0, inbox.output
    assert (item_id in {row["id"] for row in json.loads(inbox.output)}) is (shape not in RETIRED)
    check = await invoke(["check"])
    assert check.exit_code == 0, check.output


@pytest.mark.parametrize("shape", list(_roster_squad.SHAPES))
async def test_a_comment_without_as_exits_1_and_writes_nothing(squad, invoke, shape):
    kind, slug = _roster_squad.SHAPES[shape]
    before = squad_tree(squad)

    result = await invoke([kind, slug, "comment", "-m", "no author"])

    assert result.exit_code == 1, result.output
    assert "--as is required" in result.output
    assert squad_tree(squad) == before


@pytest.mark.parametrize("shape", list(_roster_squad.SHAPES))
async def test_comments_of_an_uncommented_entity_is_empty(squad, invoke, shape):
    kind, slug = _roster_squad.SHAPES[shape]
    result = await invoke([kind, slug, "comments", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == []
