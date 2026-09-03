"""The ``comment`` command's content-source resolution, at both the item level and the
sub-entity level: ``-m``/``--file`` are mutually exclusive, ``--file`` reads a real file,
``--file -`` reads stdin, an empty or whitespace-only file is refused, and file content is
guarded against sq marker tags the same way an inline message is. Mirrors the ``body``
coverage in ``test_body_content_source_and_mutual_exclusion_cli.py`` and
``test_subentity_body_input_parity_cli.py``, plus the fenced-block round trip that motivated
the flag in the first place.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.anyio

_FENCED = (
    "Repro steps:\n"
    "\n"
    "```python\n"
    "def check():\n"
    "    return True\n"
    "\n"
    "    # note the blank line above, inside the fence\n"
    "```\n"
    "\n"
    "That reproduces it.\n"
)


async def _make_task_with_subtask(invoke) -> str:
    await invoke(["create", "task", "T", "--author", "manager"])
    r = await invoke(["task", "2", "add-subtask", "a subtask"])
    assert r.exit_code == 0, r.output
    return "2"


# ─── item level ─────────────────────────────────────────────────────────────


async def test_item_comment_rejects_both_a_message_and_a_file(
    project, invoke, tmp_path: Path
) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    f = tmp_path / "c.md"
    f.write_text("from file", encoding="utf-8")
    r = await invoke(["task", "2", "comment", "--as", "manager", "-m", "inline", "--file", str(f)])
    assert r.exit_code == 1
    assert "not both" in r.output


async def test_item_comment_reads_its_content_from_a_file(project, invoke, tmp_path: Path) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    f = tmp_path / "c.md"
    f.write_text("comment from a file\n", encoding="utf-8")
    r = await invoke(["task", "2", "comment", "--as", "manager", "--file", str(f)])
    assert r.exit_code == 0, r.output

    shown = await invoke(["task", "2", "show", "--full", "--comments"])
    assert "comment from a file" in shown.output


async def test_item_comment_reads_its_content_from_stdin_when_file_is_a_dash(
    project, invoke
) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    r = await invoke(
        ["task", "2", "comment", "--as", "manager", "--file", "-"],
        input="comment from stdin\n",
    )
    assert r.exit_code == 0, r.output

    shown = await invoke(["task", "2", "show", "--full", "--comments"])
    assert "comment from stdin" in shown.output


async def test_item_comment_with_neither_source_exits_one_naming_both_flags(
    project, invoke
) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    r = await invoke(["task", "2", "comment", "--as", "manager"])
    assert r.exit_code == 1
    assert "-m" in r.output
    assert "--file" in r.output


async def test_item_comment_with_an_empty_file_is_refused_and_discussion_unchanged(
    project, invoke, tmp_path: Path
) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    f = tmp_path / "empty.md"
    f.write_text("   \n\n", encoding="utf-8")
    r = await invoke(["task", "2", "comment", "--as", "manager", "--file", str(f)])
    assert r.exit_code == 1

    comments = await invoke(["task", "2", "comments"])
    assert "no comments" in comments.output


async def test_item_comment_file_with_a_marker_tag_is_refused_like_an_inline_message(
    project, invoke, tmp_path: Path
) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    tag = "<!-- sq:body -->"
    f = tmp_path / "bad.md"
    f.write_text(f"see the {tag} region\n", encoding="utf-8")
    r = await invoke(["task", "2", "comment", "--as", "manager", "--file", str(f)])
    assert r.exit_code == 1
    assert "marker" in r.output


async def test_item_comment_repeated_m_yields_one_bullet_per_message_file_yields_one(
    project, invoke, tmp_path: Path
) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    r = await invoke(
        ["task", "2", "comment", "--as", "manager", "-m", "first point", "-m", "second point"]
    )
    assert r.exit_code == 0, r.output

    f = tmp_path / "c.md"
    f.write_text("a single file comment\n", encoding="utf-8")
    r2 = await invoke(["task", "2", "comment", "--as", "manager", "--file", str(f)])
    assert r2.exit_code == 0, r2.output

    shown = await invoke(["task", "2", "show", "--full", "--json"])
    import json

    discussion = json.loads(shown.output)["discussion"]
    assert len(discussion) == 2
    assert discussion[0]["body"].count("- ") == 2  # two bullets, one per -m message
    assert discussion[1]["body"].strip().startswith("-")
    assert discussion[1]["body"].count("\n- ") == 0  # single bullet


async def test_item_comment_fenced_code_block_with_blank_lines_round_trips_verbatim(
    project, invoke, tmp_path: Path
) -> None:
    await invoke(["create", "bug", "B", "--author", "manager"])
    f = tmp_path / "repro.md"
    f.write_text(_FENCED, encoding="utf-8")
    r = await invoke(["bug", "2", "comment", "--as", "manager", "--file", str(f)])
    assert r.exit_code == 0, r.output

    shown = await invoke(["bug", "2", "show", "--full", "--comments"])
    assert "def check():" in shown.output
    assert "return True" in shown.output
    assert "# note the blank line above, inside the fence" in shown.output
    assert "That reproduces it." in shown.output


# ─── sub-entity level ───────────────────────────────────────────────────────


async def test_subentity_comment_rejects_both_a_message_and_a_file(
    project, invoke, tmp_path: Path
) -> None:
    num = await _make_task_with_subtask(invoke)
    f = tmp_path / "c.md"
    f.write_text("from file", encoding="utf-8")
    r = await invoke(
        [
            "task",
            num,
            "subtask",
            "1",
            "comment",
            "--as",
            "manager",
            "-m",
            "inline",
            "--file",
            str(f),
        ]
    )
    assert r.exit_code == 1
    assert "not both" in r.output


async def test_subentity_comment_reads_its_content_from_a_file(
    project, invoke, tmp_path: Path
) -> None:
    num = await _make_task_with_subtask(invoke)
    f = tmp_path / "c.md"
    f.write_text("subentity comment from a file\n", encoding="utf-8")
    r = await invoke(["task", num, "subtask", "1", "comment", "--as", "manager", "--file", str(f)])
    assert r.exit_code == 0, r.output

    shown = await invoke(["task", num, "subtask", "1", "show"])
    assert "subentity comment from a file" in shown.output


async def test_subentity_comment_reads_its_content_from_stdin_when_file_is_a_dash(
    project, invoke
) -> None:
    num = await _make_task_with_subtask(invoke)
    r = await invoke(
        ["task", num, "subtask", "1", "comment", "--as", "manager", "--file", "-"],
        input="subentity comment from stdin\n",
    )
    assert r.exit_code == 0, r.output

    shown = await invoke(["task", num, "subtask", "1", "show"])
    assert "subentity comment from stdin" in shown.output


async def test_subentity_comment_with_neither_source_exits_one_naming_both_flags(
    project, invoke
) -> None:
    num = await _make_task_with_subtask(invoke)
    r = await invoke(["task", num, "subtask", "1", "comment", "--as", "manager"])
    assert r.exit_code == 1
    assert "-m" in r.output
    assert "--file" in r.output


async def test_subentity_comment_with_an_empty_file_is_refused_and_discussion_unchanged(
    project, invoke, tmp_path: Path
) -> None:
    num = await _make_task_with_subtask(invoke)
    f = tmp_path / "empty.md"
    f.write_text("\n\n   \n", encoding="utf-8")
    r = await invoke(["task", num, "subtask", "1", "comment", "--as", "manager", "--file", str(f)])
    assert r.exit_code == 1

    shown = await invoke(["task", num, "subtask", "1", "show"])
    assert "(none)" in shown.output


async def test_subentity_comment_file_with_a_marker_tag_is_refused_like_an_inline_message(
    project, invoke, tmp_path: Path
) -> None:
    num = await _make_task_with_subtask(invoke)
    tag = "<!-- sq:body -->"
    f = tmp_path / "bad.md"
    f.write_text(f"see the {tag} region\n", encoding="utf-8")
    r = await invoke(["task", num, "subtask", "1", "comment", "--as", "manager", "--file", str(f)])
    assert r.exit_code == 1
    assert "marker" in r.output


async def test_subentity_comment_repeated_m_yields_one_bullet_per_message_file_yields_one(
    project, invoke, tmp_path: Path
) -> None:
    num = await _make_task_with_subtask(invoke)
    r = await invoke(
        [
            "task",
            num,
            "subtask",
            "1",
            "comment",
            "--as",
            "manager",
            "-m",
            "first point",
            "-m",
            "second point",
        ]
    )
    assert r.exit_code == 0, r.output

    f = tmp_path / "c.md"
    f.write_text("a single file comment\n", encoding="utf-8")
    r2 = await invoke(["task", num, "subtask", "1", "comment", "--as", "manager", "--file", str(f)])
    assert r2.exit_code == 0, r2.output

    shown = await invoke(["task", num, "show", "--json"])
    import json

    subentity = json.loads(shown.output)["subentities"][0]
    discussion = subentity["discussion"]
    assert len(discussion) == 2
    assert discussion[0]["body"].count("- ") == 2  # two bullets, one per -m message
    assert discussion[1]["body"].count("\n- ") == 0  # single bullet


async def test_subentity_comment_fenced_code_block_with_blank_lines_round_trips_verbatim(
    project, invoke, tmp_path: Path
) -> None:
    num = await _make_task_with_subtask(invoke)
    f = tmp_path / "repro.md"
    f.write_text(_FENCED, encoding="utf-8")
    r = await invoke(["task", num, "subtask", "1", "comment", "--as", "manager", "--file", str(f)])
    assert r.exit_code == 0, r.output

    shown = await invoke(["task", num, "subtask", "1", "show"])
    assert "def check():" in shown.output
    assert "return True" in shown.output
    assert "# note the blank line above, inside the fence" in shown.output
    assert "That reproduces it." in shown.output
