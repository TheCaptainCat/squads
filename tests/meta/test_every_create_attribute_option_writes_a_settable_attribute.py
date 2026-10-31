"""`sq create <type>` derives an option for each settable attribute of kind str, list or date a
type declares, and none for an attribute `update --set` could not write."""

import pytest

from tests._help_tree import write_workflow_override

pytestmark = pytest.mark.anyio

OVERRIDE = """\
[items.guide.attributes]
audience = { kind = "str" }
secret = { kind = "str", settable = false }
flags = { kind = "bool" }
"""


async def test_a_create_option_is_derived_only_for_a_settable_attribute(project, invoke) -> None:
    write_workflow_override(project.squad_dir, OVERRIDE)
    result = await invoke(["create", "guide", "--help"])
    assert result.exit_code == 0, result.output
    options = {word for word in result.output.split() if word.startswith("--")}
    assert {"--tags", "--tech", "--audience"} <= options
    assert not {"--secret", "--flags"} & options
