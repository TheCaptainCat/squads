"""A source's `converter`: tracker description and comment text reach the squad as markdown."""

import json
from pathlib import Path
from typing import Any

import pytest

from tests import _tracker_harness as harness

pytestmark = pytest.mark.anyio

SECRET = "glpat-not-a-real-token"
SAMPLES = Path(__file__).parents[1] / "fixtures" / "converters"
TYPES = '\n[sources.platform.maps.types]\nissue = "task"\n'


@pytest.mark.covers("source pull", "source")
@pytest.mark.parametrize("converter", ["adf", "jira-wiki", "github-md"])
async def test_a_description_and_a_comment_in_the_converters_format_show_as_markdown(
    project, invoke, credentials_home, converter
) -> None:
    written = (SAMPLES / converter / "input.txt").read_text(encoding="utf-8").rstrip("\n")
    expected = (SAMPLES / converter / "expected.md").read_text(encoding="utf-8").rstrip("\n")
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        for route in tracker.routes:
            body: Any = route.get("body")
            if route["path"] == "/api/v4/issues":
                body[0]["description"] = written
            elif route["path"] == "/api/v4/projects/platform%2Fapi/issues/12":
                body["description"] = written
            elif route["path"] == "/api/v4/projects/77/issues/12/notes":
                body[1]["body"] = written
        path = project.squad_dir / ".overrides" / "sources.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f'[sources.platform]\nconnector = "gitlab"\nfilter = "squads"\n'
            f'base_url = "{tracker.base_url}"\nconverter = "{converter}"\n{TYPES}',
            encoding="utf-8",
        )
        stored = await invoke(["source", "credential", "set", "platform"], input=f"{SECRET}\n")
        assert stored.exit_code == 0, stored.output
        pulled = await invoke(["source", "pull", "platform"])
        assert pulled.exit_code == 0, pulled.output
        shown = await invoke(["task", "2", "show", "--json"])
        base = tracker.base_url

    assert shown.exit_code == 0, shown.output
    item = json.loads(shown.output.replace(base, "http://tracker"))
    assert item["views"]["source_description"]["body"] == expected
    # A comment shows as one list entry, its lines indented under the marker.
    assert [c["body"] for c in item["discussion"]] == ["- " + expected.replace("\n", "\n  ")]


@pytest.mark.covers("source pull", "--json")
async def test_a_hostile_description_drops_only_its_issue_and_the_report_names_it(
    project, invoke, credentials_home
) -> None:
    nested: dict[str, Any] = {"type": "paragraph"}
    for _ in range(400):
        nested = {"type": "blockquote", "content": [nested]}
    hostile = json.dumps({"type": "doc", "content": [nested]})
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        for route in tracker.routes:
            if route["path"] == "/api/v4/issues":
                route["body"][0]["description"] = hostile
        path = project.squad_dir / ".overrides" / "sources.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            '[sources.platform]\nconnector = "gitlab"\nfilter = "squads"\n'
            f'base_url = "{tracker.base_url}"\nconverter = "adf"\n{TYPES}',
            encoding="utf-8",
        )
        stored = await invoke(["source", "credential", "set", "platform"], input=f"{SECRET}\n")
        assert stored.exit_code == 0, stored.output
        pulled = await invoke(["source", "pull", "platform", "--json"])

    assert pulled.exit_code == 0, pulled.output
    report = json.loads(pulled.stdout)["sources"][0]
    assert (report["created"], report["lines"]) == (
        ["TASK-2"],
        ["platform/api#12: dropped, its text cannot be converted (ValueError)"],
    )
