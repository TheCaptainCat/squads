"""At the CLI: a create under a parent of the wrong type exits 1 while the type leaves
`parent_in` at its default level or raises it, and exits 0 once the type lowers it to `@warn`,
where `sq check` still reports it.
"""

import pytest

from _helpers import create_item
from _selection_table import service_with

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize(
    ("entry", "create_exit"),
    [("parent_in", 1), ("parent_in@error", 1), ("parent_in@warn", 0)],
)
async def test_create_exit_follows_the_level_the_type_selects(
    project, invoke, entry, create_exit
) -> None:
    svc = service_with(project.squad_dir, f'[items.task]\nvalidators = ["{entry}"]\n')
    parent = (await create_item(svc, "task", "parent")).item
    created = await invoke(
        ["create", "task", "t", "--author", "manager", "--parent", str(parent.id)]
    )
    assert created.exit_code == create_exit, created.output
    checked = await invoke(["check"])
    assert checked.exit_code == 0, checked.output
    assert ("got task" in checked.output) is (create_exit == 0)
