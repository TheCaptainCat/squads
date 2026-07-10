"""`sq docs` — the bundled documentation reader. Needs no squad: it reads package data, not
project state. The registry itself (`available`/`read`) is proven at
tests/meta/test_bundled_docs_registry.py; this file proves the CLI command dispatches to it.
"""

from squads._cli import app


def test_docs_lists_the_bundled_docs_without_a_squad(runner):
    result = runner.invoke(app, ["docs"])
    assert result.exit_code == 0, result.output
    assert "internals" in result.output and "workflow" in result.output


def test_docs_prints_a_named_doc_as_raw_markdown(runner):
    result = runner.invoke(app, ["docs", "internals"])
    assert result.exit_code == 0, result.output
    assert "# squads internals" in result.output  # verbatim heading, no markup interpretation


def test_docs_rich_flag_renders_without_error(runner):
    result = runner.invoke(app, ["docs", "internals", "--rich"])
    assert result.exit_code == 0, result.output


def test_docs_exits_1_for_an_unknown_doc(runner):
    result = runner.invoke(app, ["docs", "nope"])
    assert result.exit_code == 1
    assert "unknown doc" in result.output
