"""`sq import --json` lists its issues in the order `sq check` prints them, with the validator
list of the touched types in either order."""

import json

import pytest

from squads import __version__

pytestmark = pytest.mark.anyio

_LONG = "q" * 121

_EVENTS = (
    '{"op":"create","type":"feature","title":"Imp F","handle":"f1","as":"manager",'
    '"body":"## Status\\n\\nx"}\n'
    f'{{"op":"add-story","target":"f1","title":"{_LONG}"}}\n'
)

_SELECTIONS = [
    pytest.param('["no_status_banner", "subentity_title_max:120"]', id="banner-first"),
    pytest.param('["subentity_title_max:120", "no_status_banner"]', id="banner-last"),
]


@pytest.mark.parametrize("selection", _SELECTIONS)
async def test_the_json_issues_are_in_check_order_whatever_the_selection(
    project, invoke, tmp_path, selection
):
    (project.squad_dir / ".overrides").mkdir(exist_ok=True)
    (project.squad_dir / ".overrides" / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n[items.feature]\nvalidators = {selection}\n",
        encoding="utf-8",
    )
    events = tmp_path / "events.jsonl"
    events.write_text(_EVENTS, encoding="utf-8")

    result = await invoke(["import", "--json", str(events)])

    issues = json.loads(result.output)["issues"]
    assert [i["message"].split(" ")[0] for i in issues] == ["US1", "advisory:", "body"]
