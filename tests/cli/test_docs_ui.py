"""`sq docs` (the bundled documentation) and `sq ui` (the terminal browser, never run
interactively here)."""

import json
from typing import TYPE_CHECKING

import pytest

from squads import _docfiles
from tests.cli._readable import lines

if TYPE_CHECKING:
    from squads._tui._app import SquadsApp

pytestmark = pytest.mark.anyio

FAQ_HEAD = [
    "# FAQ & troubleshooting",
    "",
    "### `pip install squads` fails / wrong Python",
    "squads requires **Python ≥ 3.14** (it uses PEP 649 deferred annotations and PEP 695 "
    "generics).",
]
FAQ_RICH_HEAD = [
    "                             FAQ & troubleshooting",
    "",
    "pip install squads fails / wrong Python",
    "",
    "squads requires Python ≥ 3.14 (it uses PEP 649 deferred annotations and PEP 695",
]


async def _docs(invoke, *args: str) -> tuple[int, list[str]]:
    result = await invoke(["docs", *args])
    return result.exit_code, lines(result.output)


def _cells(row: str) -> list[str]:
    return [cell.strip() for cell in row.strip("│").split("│")]


async def test_docs_lists_the_bundled_documents_by_name_and_title(invoke) -> None:
    code, out = await _docs(invoke)
    assert code == 0
    assert out[0].strip() == "squads docs — read with `sq docs <name>`"
    assert _cells(out[2].strip("┃").replace("┃", "│")) == ["name", "title"]
    rows = [_cells(line) for line in out if line.startswith("│")]
    assert ["faq", "FAQ & troubleshooting"] in rows
    assert [name for name, _ in rows] == [stem for stem, _ in _docfiles.available()]


@pytest.mark.covers("docs", "NAME")
async def test_docs_name_prints_the_document_as_raw_markdown(invoke) -> None:
    result = await invoke(["docs", "faq"])
    assert result.exit_code == 0, result.output
    assert lines(result.output)[:4] == FAQ_HEAD
    assert result.output == _docfiles.read("faq") + "\n"


async def test_docs_name_ignores_case_and_a_markdown_suffix(invoke) -> None:
    assert await _docs(invoke, "FAQ.md") == await _docs(invoke, "faq")


async def test_docs_name_refuses_a_document_the_bundle_lacks(invoke) -> None:
    names = ", ".join(stem for stem, _ in _docfiles.available())
    assert await _docs(invoke, "ghost") == (1, [f"error: unknown doc 'ghost' (one of: {names})"])


@pytest.mark.covers("docs", "--rich")
async def test_rich_pretty_prints_the_document_instead_of_raw_markdown(invoke) -> None:
    code, out = await _docs(invoke, "faq", "--rich")
    assert (code, out[:5]) == (0, FAQ_RICH_HEAD)


# --- ui -------------------------------------------------------------------------------------


@pytest.fixture
def squads_app() -> type[SquadsApp]:
    """The terminal app class, or a skip when the `tui` extra is not installed."""
    pytest.importorskip("textual")
    from squads._tui._app import SquadsApp

    return SquadsApp


@pytest.mark.covers("ui")
async def test_ui_runs_the_terminal_browser_over_the_squad(
    squads_app, project, invoke, monkeypatch
) -> None:
    runs: list[SquadsApp] = []
    monkeypatch.setattr(squads_app, "run", lambda self, *a, **k: runs.append(self))
    result = await invoke(["ui"])
    assert (result.exit_code, result.output, len(runs)) == (0, "", 1)


async def test_ui_refuses_to_start_outside_a_squad(squads_app, invoke, monkeypatch) -> None:
    monkeypatch.setattr(squads_app, "run", lambda self, *a, **k: pytest.fail("the app started"))
    result = await invoke(["ui"])
    assert (result.exit_code, lines(result.output)) == (
        1,
        ["error: no .squads.toml found in this or any parent directory — run `sq init`"],
    )


@pytest.mark.covers("docs", "--json")
async def test_docs_json_prints_the_named_document_under_its_own_name(invoke) -> None:
    result = await invoke(["docs", "FAQ.md", "--json"])
    assert result.exit_code == 0, result.output
    assert (
        result.output
        == json.dumps({"name": "faq", "markdown": _docfiles.read("faq")}, indent=2) + "\n"
    )
