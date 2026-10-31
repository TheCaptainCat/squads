"""The squads the surface tests start from are the ones their fixtures promise."""

import json
from typing import Any

import pytest

from tests._populated import FEATURE, REVIEW, TASK, init_populated

pytestmark = pytest.mark.anyio


@pytest.fixture
def populated_project(copy_squad):
    """The squad the CLI tests' `populated_project` fixture copies."""
    return copy_squad("populated", init_populated)


async def _show(invoke, item_type: str, number: int) -> dict[str, Any]:
    result = await invoke([item_type, str(number), "show", "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


async def test_the_populated_squad_holds_a_feature_with_stories(populated_project, invoke) -> None:
    feature = await _show(invoke, "feature", FEATURE)
    assert [(s["local_id"], s["title"]) for s in feature["subentities"]] == [
        ("US1", "Query the index"),
        ("US2", "Rank the results"),
    ]


async def test_the_populated_squad_holds_a_task_under_the_feature(
    populated_project, invoke
) -> None:
    task = await _show(invoke, "task", TASK)
    assert task["parent"] == f"FEAT-{FEATURE}"
    assert [(s["local_id"], s["maps_to"]) for s in task["subentities"]] == [
        ("ST1", "US1"),
        ("ST2", None),
    ]


async def test_the_populated_squad_holds_a_review_with_findings(populated_project, invoke) -> None:
    review = await _show(invoke, "review", REVIEW)
    assert [s["local_id"] for s in review["subentities"]] == ["F1", "F2"]


async def test_the_minimal_squad_holds_only_its_role(project, invoke) -> None:
    result = await invoke(["list", "--json"])
    assert (result.exit_code, [i["id"] for i in json.loads(result.output)]) == (0, ["ROLE-1"])


async def test_the_seeded_squad_holds_the_bundled_skills(seeded_project, invoke) -> None:
    result = await invoke(["skill", "greeting", "show", "--json"])
    assert (result.exit_code, json.loads(result.output)["title"]) == (0, "greeting")
