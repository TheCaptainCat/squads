import re

import pytest

from squads._index._resolver import item_file
from squads._models import _markers as markers

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("flags", [[], ["--append"]])
async def test_a_body_write_without_a_region_prints_one_error_line(project, svc, invoke, flags):
    created = await invoke(["create", "task", "t", "--author", "manager"])
    match = re.search(r"TASK-(\d+)", created.output)
    assert match
    item = await svc.get(f"TASK-{match.group(1)}")
    path = item_file(svc.paths, item)
    text = path.read_text(encoding="utf-8")
    text = text.replace(f"{markers.open_marker(markers.BODY)}\n", "")
    text = text.replace(f"{markers.close_marker(markers.BODY)}\n", "")
    path.write_text(text, encoding="utf-8")

    result = await invoke(["task", match.group(1), "body", *flags, "-m", "prose"])

    assert result.exit_code == 1, result.output
    assert "error:" in result.output
    assert path.name in result.output.replace("\n", "")
    assert "Traceback" not in result.output
    assert "KeyError" not in result.output
    assert path.read_text(encoding="utf-8") == text
