"""`sq create guide` takes the priority, label and ref options the other types take."""

import json
from typing import Any

import pytest

from tests._populated import TASK

pytestmark = pytest.mark.anyio


async def test_create_guide_takes_a_priority_labels_and_refs(populated_project, invoke) -> None:
    result = await invoke(
        [
            "create",
            "guide",
            "Setup",
            "--author",
            "manager",
            "--priority",
            "high",
            "--label",
            "ops",
            "--ref",
            f"{TASK}:implements",
        ]
    )
    assert result.exit_code == 0, result.output
    shown = await invoke(["guide", "5", "show", "--json"])
    doc: dict[str, Any] = json.loads(shown.output)
    assert (doc["priority"], doc["labels"], doc["refs"]) == (
        "high",
        ["ops"],
        [f"TASK-{TASK}:implements"],
    )
