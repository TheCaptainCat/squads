"""The CLI half of the view-tag placement design's control: ``sq <type> <n> body -m``/
``--file`` refuses a well-formed view tag, while the same text with its HTML-comment wrapper
stripped goes through — driven at the CLI surface, not just the service.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.anyio

_WRAPPED = "<!-- sq:view:milestone_rollup -->"
_UNWRAPPED = "sq:view:milestone_rollup"


async def test_body_dash_m_refuses_the_wrapped_view_tag(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    r = await invoke(["task", "2", "body", "-m", f"see {_WRAPPED}"])
    assert r.exit_code == 1
    assert "marker" in r.output


async def test_body_dash_m_accepts_the_unwrapped_text_the_control(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    r = await invoke(["task", "2", "body", "-m", f"see {_UNWRAPPED}"])
    assert r.exit_code == 0, r.output
    shown = await invoke(["task", "2", "show", "--raw"])
    assert _UNWRAPPED in shown.output


async def test_body_file_refuses_the_wrapped_view_tag(project, invoke, tmp_path: Path) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    body_file = tmp_path / "body.md"
    body_file.write_text(f"see {_WRAPPED}\n", encoding="utf-8")

    r = await invoke(["task", "2", "body", "--file", str(body_file)])

    assert r.exit_code == 1
    assert "marker" in r.output


async def test_body_file_accepts_the_unwrapped_text_the_control(
    project, invoke, tmp_path: Path
) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    body_file = tmp_path / "body.md"
    body_file.write_text(f"see {_UNWRAPPED}\n", encoding="utf-8")

    r = await invoke(["task", "2", "body", "--file", str(body_file)])

    assert r.exit_code == 0, r.output
    shown = await invoke(["task", "2", "show", "--raw"])
    assert _UNWRAPPED in shown.output
