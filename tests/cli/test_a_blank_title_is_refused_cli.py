"""A blank `--title` or title argument fails with exit 1, naming the field, on item `update` and
`create`, and leaves the item file as it was. A blank subtask title clears the title."""

import pytest

from _helpers import create_item

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("title", ["", "   ", "\u200b"], ids=["empty", "whitespace", "zwsp"])
@pytest.mark.parametrize("verb", ["update", "create"])
async def test_a_blank_title_fails_cleanly(svc, invoke, verb, title) -> None:
    task = (await create_item(svc, "task", "t")).item
    await svc.add_block(task.id, "subtask", "s")
    n = str(task.sequence_id)
    args = {
        "update": ["task", n, "update", "--title", title],
        "create": ["create", "task", title, "--author", "manager"],
    }[verb]
    before = sorted(p.read_text(encoding="utf-8") for p in svc.paths.squad_dir.rglob("TASK-*.md"))

    result = await invoke(args)

    assert result.exit_code == 1, result.output
    assert "title must not be empty" in result.output
    assert before == sorted(
        p.read_text(encoding="utf-8") for p in svc.paths.squad_dir.rglob("TASK-*.md")
    )


@pytest.mark.parametrize("title", ["", "   "], ids=["empty", "whitespace"])
async def test_a_blank_subtask_title_clears_it_and_the_views_render(svc, invoke, title) -> None:
    task = (await create_item(svc, "task", "t")).item
    await svc.add_block(task.id, "subtask", "s")
    n = str(task.sequence_id)

    updated = await invoke(["task", n, "subtask", "1", "update", "--title", title])
    shown = await invoke(["task", n, "show", "--full"])

    assert updated.exit_code == 0, updated.output
    assert shown.exit_code == 0, shown.output
    assert (await svc.get(task.id)).subentities[0].title == ""
