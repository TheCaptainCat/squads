"""`sq check` reports a wrong-typed playbook or workflow override as an error finding, never a
traceback, whichever table or array in the document has the wrong type."""

import json

import pytest

pytestmark = pytest.mark.anyio

# (override file, body, fragment of the loader's own message)
_SHAPES = [
    ("playbook", "types = 3", "types must be a table (got int)"),
    ("playbook", "types = [1]", "types must be a table (got list)"),
    ("playbook", 'types = "x"', "types must be a table (got str)"),
    ("playbook", "[types]\nepic = 3", "types.epic must be a table (got int)"),
    ("playbook", "[types.epic]\nroles = 3", "types.epic.roles must be an array of tables"),
    ("playbook", "[types.epic]\nroles = [1]", "types.epic.roles[0] must be a table"),
    ("playbook", "[types.epic]\nroles = [[1]]", "types.epic.roles[0] must be a table"),
    ("workflow", "statuses = 3", "workflow config invalid"),
    ("workflow", "items = 3", "workflow config invalid"),
    ("workflow", "collections = 3", "workflow config invalid"),
    ("workflow", "lifecycles = 3", "workflow config invalid"),
    ("workflow", "items = [1]", "workflow config invalid"),
    ("workflow", "[statuses]\nx = 3", "workflow config invalid"),
]


@pytest.mark.parametrize(("document", "body", "fragment"), _SHAPES)
async def test_a_wrong_typed_override_is_an_error_not_a_traceback(
    project, invoke, document, body, fragment
) -> None:
    overrides = project.squad_dir / ".overrides"
    overrides.mkdir(parents=True, exist_ok=True)
    (overrides / f"{document}.toml").write_text(body + "\n", encoding="utf-8")

    r = await invoke(["check", "--json"])

    assert r.exit_code == 3, r.output
    assert isinstance(r.exception, SystemExit), repr(r.exception)
    issues = json.loads(r.stdout)
    found = [i for i in issues if i["item"] == document]
    assert len(found) == 1, issues
    assert found[0]["level"] == "error"
    assert fragment in found[0]["message"]
