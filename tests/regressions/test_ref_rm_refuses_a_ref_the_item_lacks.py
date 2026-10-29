import json

import pytest

from tests.cli._populated import REVIEW, TASK, init_populated

pytestmark = pytest.mark.anyio


@pytest.fixture
def populated_project(copy_squad):
    return copy_squad("populated", init_populated)


async def test_ref_rm_of_a_ref_the_item_lacks_is_refused_not_reported_removed(
    populated_project, invoke
) -> None:
    result = await invoke(["task", str(TASK), "ref", "rm", f"REV-{REVIEW}"])
    assert (result.exit_code, result.output) == (1, f"error: TASK-3 has no ref to REV-{REVIEW}\n")
    refs = json.loads((await invoke(["task", str(TASK), "show", "--json"])).output)["refs"]
    assert refs == []
