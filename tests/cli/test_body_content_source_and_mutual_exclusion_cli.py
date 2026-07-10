"""The ``body`` command's content-source resolution: ``-m``/``--file`` are mutually exclusive,
``--file`` reads a real file, and ``--file -`` reads stdin. Shared by every item type's
``body`` verb (``resolve_body``/``resolve_body_optional`` in ``_cli/_common.py``).
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.anyio


async def test_body_rejects_both_a_message_and_a_file(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    r = await invoke(["task", "2", "body", "-m", "inline", "--file", "whatever.md"])
    assert r.exit_code == 1
    assert "not both" in r.output


async def test_body_reads_its_content_from_a_file(project, invoke, tmp_path: Path) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    body_file = tmp_path / "body.md"
    body_file.write_text("Content read from a file.\n", encoding="utf-8")

    r = await invoke(["task", "2", "body", "--file", str(body_file)])
    assert r.exit_code == 0, r.output

    shown = await invoke(["task", "2", "show", "--raw"])
    assert "Content read from a file." in shown.output


async def test_body_reads_its_content_from_stdin_when_file_is_a_dash(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])

    r = await invoke(["task", "2", "body", "--file", "-"], input="Piped in from stdin.\n")
    assert r.exit_code == 0, r.output

    shown = await invoke(["task", "2", "show", "--raw"])
    assert "Piped in from stdin." in shown.output
