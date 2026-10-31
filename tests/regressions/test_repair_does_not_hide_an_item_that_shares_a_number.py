"""`sq repair` over two files that share a number reports them instead of dropping one."""

import pytest

from tests._squadwide import listed

pytestmark = pytest.mark.anyio


async def test_repair_refuses_instead_of_dropping_one_of_two_files_sharing_a_number(
    populated, invoke
) -> None:
    squad = populated.squad_dir
    original = (squad / "tasks/TASK-000003-build-the-query-parser.md").read_text(encoding="utf-8")
    twin = original.replace("id: TASK-3", "id: FEAT-3")
    (squad / "features/FEAT-000003-twin.md").write_text(twin, encoding="utf-8")
    before = await listed(invoke)
    result = await invoke(["repair"])
    assert (result.exit_code, result.output) == (
        1,
        "error: refusing to rebuild the index: it keys items by number:\n"
        "  - 2 files carry number 3 under different ids "
        "(features/FEAT-000003-twin.md, tasks/TASK-000003-build-the-query-parser.md); "
        "run `sq repair --renumber` to give one of them a new number\n",
    )
    assert await listed(invoke) == before
