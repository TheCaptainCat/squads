"""A restored region goes where the template puts it, at a line boundary, never inside authored
prose, reusing a surviving heading and keeping sub-entity blocks in id order."""

import re

import pytest

from squads._sections import get_section

pytestmark = pytest.mark.anyio


async def _task_with_subtasks(project, invoke, count=3):
    await invoke(["create", "task", "t", "--author", "manager"])
    for i in range(count):
        await invoke(["task", "2", "add-subtask", f"st{i + 1}"])
    (md,) = (project.squad_dir / "tasks").glob("TASK-*.md")
    return md


def _block(text: str, local: str) -> str:
    tag = f"subtask:{local}"
    start = text.index(f"<!-- sq:{tag} -->")
    return text[start : text.index(f"<!-- sq:{tag}:end -->", start)]


async def test_the_body_pair_goes_after_authored_lines_that_have_no_heading(project, invoke):
    md = await _task_with_subtasks(project, invoke, 1)
    text = md.read_text()
    bare = (
        "<!-- sq:subtask:ST1 -->\nAuthored line one\nauthored line two\n\n#### Discussion\n\n"
        "<!-- sq:subtask:ST1:discussion -->\n<!-- sq:subtask:ST1:discussion:end -->\n"
    )
    md.write_text(text.replace(_block(text, "ST1"), bare))

    result = await invoke(["task", "2", "subtask", "1", "comment", "--as", "manager", "-m", "x"])

    assert result.exit_code == 0, result.output
    after = _block(md.read_text(), "ST1")
    assert "Authored line one\nauthored line two\n" in after
    assert after.index("authored line two") < after.index("<!-- sq:subtask:ST1:body -->")
    assert after.index("<!-- sq:subtask:ST1:body:end -->") < after.index("#### Discussion")


@pytest.mark.parametrize("what", ["block-discussion", "item-discussion"])
async def test_a_surviving_discussion_heading_is_not_reused_and_the_pair_lands_outside_regions(
    project, invoke, what
):
    md = await _task_with_subtasks(project, invoke, 1)
    tag = "subtask:ST1:discussion" if what == "block-discussion" else "discussion"
    text = md.read_text()
    inner = re.search(rf"<!-- sq:{tag} -->.*?<!-- sq:{tag}:end -->\n?", text, re.S)
    assert inner
    md.write_text(text.replace(inner.group(), ""))
    args = (
        ["task", "2", "subtask", "1", "comment"]
        if what == "block-discussion"
        else ["task", "2", "comment"]
    )

    result = await invoke([*args, "--as", "manager", "-m", "x"])

    assert result.exit_code == 0, result.output
    final = md.read_text()
    assert f"<!-- sq:{tag} -->" in final
    assert final.count("Discussion\n") >= 2  # the surviving heading stays; a second is accepted
    assert "<!-- sq:discussion" not in (get_section(final, "body") or "")


async def _body_with_heading(project, invoke, heading, target):
    if target == "decision":
        await invoke(["create", "decision", "d", "--author", "manager"])
        (md,) = (project.squad_dir / "adrs").glob("ADR-*.md")
        number = "2"
        await invoke([target, number, "body", "-m", f"Context.\n\n{heading}\n\nmore"])
        write = [target, number]
    else:
        md = await _task_with_subtasks(project, invoke, 1)
        await invoke(["task", "2", "subtask", "1", "body", "-m", f"Text.\n\n{heading}\n\nmore"])
        write = ["task", "2", "subtask", "1"]
    return md, write


@pytest.mark.parametrize(
    ("target", "heading", "lost"),
    [
        pytest.param("decision", "## Discussion", "discussion", id="item-heading-in-body"),
        pytest.param("subtask", "#### Discussion", "subtask:ST1:discussion", id="block-heading"),
    ],
)
async def test_a_heading_inside_the_body_never_hosts_the_restored_discussion(
    project, invoke, target, heading, lost
):
    md, write = await _body_with_heading(project, invoke, heading, target)
    text = md.read_text()
    # The template's own heading goes with the pair; only the heading in the body is left.
    inner = re.search(
        rf"{re.escape(heading)}\n\n<!-- sq:{lost} -->.*?<!-- sq:{lost}:end -->\n?", text, re.S
    )
    assert inner
    md.write_text(text.replace(inner.group(), ""))
    body_tag = "body" if target == "decision" else "subtask:ST1:body"
    assert heading in (get_section(md.read_text(), body_tag) or "")

    result = await invoke([*write, "comment", "--as", "manager", "-m", "keep me"])

    assert result.exit_code == 0, result.output
    final = md.read_text()
    assert "<!-- sq:" + lost not in (get_section(final, body_tag) or "")
    forced = await invoke([*write, "body", "--force", "-m", "replaced"])
    assert forced.exit_code == 0, forced.output
    assert "keep me" in md.read_text()


async def test_a_restored_block_keeps_id_order(project, invoke):
    md = await _task_with_subtasks(project, invoke, 3)
    text = md.read_text()
    md.write_text(text.replace(_block(text, "ST2") + "<!-- sq:subtask:ST2:end -->\n", ""))
    assert "<!-- sq:subtask:ST2 -->" not in md.read_text()

    result = await invoke(["task", "2", "subtask", "2", "body", "-m", "second"])

    assert result.exit_code == 0, result.output
    final = md.read_text()
    order = [final.index(f"<!-- sq:subtask:ST{n} -->") for n in (1, 2, 3)]
    assert order == sorted(order)
    assert "second" in _block(final, "ST2")


@pytest.mark.parametrize(
    "args",
    [
        ["task", "2", "subtask", "1", "body", "-m", "text"],
        ["task", "2", "subtask", "1", "body", "--append", "-m", "text"],
        ["task", "2", "subtask", "1", "comment", "--as", "manager", "-m", "text"],
    ],
    ids=["body", "append", "comment"],
)
async def test_declared_sub_entities_with_no_container_get_container_and_block(
    project, invoke, args
):
    md = await _task_with_subtasks(project, invoke, 1)
    md.write_text(
        re.sub(r"\n## Subtasks.*?<!-- sq:subtasks:end -->\n", "\n", md.read_text(), flags=re.S)
    )
    assert "<!-- sq:subtasks -->" not in md.read_text()

    result = await invoke(args)

    assert result.exit_code == 0, result.output
    final = md.read_text()
    assert "<!-- sq:subtasks -->" in final
    assert "<!-- sq:subtask:ST1 -->" in final
    check = await invoke(["check"])
    assert check.exit_code == 0, check.output
