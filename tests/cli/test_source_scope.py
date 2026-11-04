"""A source names one scope on its tracker and may narrow it with a filter expression per side;
both are checked when `sources.toml` loads."""

import json

import pytest

pytestmark = pytest.mark.anyio

BASE = 'base_url = "http://127.0.0.1:9"\n'
GITLAB = f'[sources.platform]\nconnector = "gitlab"\n{BASE}'
TYPES = '\n[sources.platform.maps.types.labels]\nbug = "task"\n'
INVALID = "error: sources.toml: invalid sources after merge:\n  source 'platform': "
FILTER = "sources.platform.filter.labels: "


async def _listed(invoke, project, text: str) -> tuple[int, str]:
    """Write `text` as the squad's sources override and load it through `sq source list`."""
    path = project.squad_dir / ".overrides" / "sources.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")
    result = await invoke(["source", "list", "--json"])
    return result.exit_code, result.output.replace(str(path), "sources.toml")


async def _refusals(invoke, project, declared: list[tuple[str, str]]) -> list[tuple[int, str]]:
    """The load result of each (filter text, expected refusal tail) in `declared`."""
    found: list[tuple[int, str]] = []
    for expression, _ in declared:
        source = f'{GITLAB}project = "platform/api"\n\n[sources.platform.filter]\n{expression}'
        found.append(await _listed(invoke, project, source + TYPES))
    return found


def _refused(declared: list[tuple[str, str]]) -> list[tuple[int, str]]:
    return [(1, f"{INVALID}{FILTER}{tail}\n") for _, tail in declared]


@pytest.mark.covers("source list", "--json")
async def test_a_source_without_a_scope_key_fails_at_load_listing_the_keys_its_version_takes(
    project, invoke
) -> None:
    loaded = await _listed(invoke, project, GITLAB + TYPES)

    assert loaded == (1, f"{INVALID}no scope key; name exactly one of: project, group\n")


@pytest.mark.covers("source list", "--json")
async def test_a_source_with_two_scope_keys_fails_at_load(project, invoke) -> None:
    text = GITLAB + 'project = "platform/api"\ngroup = "platform"\n' + TYPES

    loaded = await _listed(invoke, project, text)

    assert loaded == (
        1,
        f"{INVALID}2 scope keys (project, group); name exactly one of: project, group\n",
    )


@pytest.mark.covers("source list", "--json")
async def test_a_scope_key_of_another_connector_fails_at_load(project, invoke) -> None:
    loaded = await _listed(invoke, project, GITLAB + 'repository = "acme/api"\n' + TYPES)

    assert loaded == (
        1,
        f"{INVALID}'repository' is not a scope key of gitlab@v4 (scope keys: project, group)\n",
    )


@pytest.mark.covers("source list", "--json")
async def test_an_empty_scope_value_fails_at_load(project, invoke) -> None:
    loaded = await _listed(invoke, project, GITLAB + 'group = "  "\n' + TYPES)

    assert loaded == (1, f"{INVALID}scope key 'group' must be a non-empty string\n")


@pytest.mark.covers("source list", "--json")
async def test_a_string_filter_fails_at_load_saying_filter_is_a_table_and_naming_the_scope_keys(
    project, invoke
) -> None:
    loaded = await _listed(invoke, project, GITLAB + 'project = "a/b"\nfilter = "squads"\n' + TYPES)

    assert loaded == (
        1,
        f"{INVALID}sources.platform.filter is a table of one expression per side "
        "(sides: labels, type), not a string; the issues a source follows are named by its "
        "scope, one of: project, group\n",
    )


@pytest.mark.covers("source list", "--json")
async def test_a_filter_side_the_version_lacks_fails_at_load_listing_its_sides(
    project, invoke
) -> None:
    text = f'{GITLAB}project = "a/b"\n\n[sources.platform.filter]\npriority = "high"\n{TYPES}'

    loaded = await _listed(invoke, project, text)

    assert loaded == (
        1,
        f"{INVALID}sources.platform.filter.priority: the connector has no side 'priority' "
        "(sides: labels, type)\n",
    )


@pytest.mark.covers("source list", "--json")
async def test_an_empty_filter_table_or_expression_fails_at_load(project, invoke) -> None:
    head = f'{GITLAB}project = "a/b"\n\n[sources.platform.filter]\n'

    empty_table = await _listed(invoke, project, head + TYPES)
    blank = await _listed(invoke, project, head + "labels = '''  \n '''\n" + TYPES)

    assert empty_table == (
        1,
        f"{INVALID}sources.platform.filter is an empty table; write a side (labels, type) "
        "or remove it\n",
    )
    assert blank == (1, f"{INVALID}{FILTER}the expression is empty\n")


@pytest.mark.covers("source list", "--json")
async def test_a_multi_line_expression_in_a_literal_string_loads(project, invoke) -> None:
    text = (
        f'{GITLAB}project = "platform/api"\n\n[sources.platform.filter]\n'
        "labels = '''\n  (type::epic or type::story)\n  and not \"help wanted\"\n'''\n"
        "type = 'issue or incident'\n" + TYPES
    )

    exit_code, output = await _listed(invoke, project, text)

    assert exit_code == 0, output
    assert [s["name"] for s in json.loads(output)["sources"]] == ["platform"]


def _outside(char: str, line: int, column: int) -> str:
    return (
        f"the character {char} is not allowed outside quotes; quote the value "
        f"(line {line}, column {column})"
    )


@pytest.mark.covers("source list", "--json")
async def test_a_character_outside_the_grammar_is_refused_with_its_line_and_column(
    project, invoke
) -> None:
    declared = [
        ("labels = 'a & b'", _outside("'&'", 1, 3)),
        ("labels = '''a and\n  b ?'''", _outside("'?'", 2, 5)),
        ('labels = "a and\\r\\n  b ?"', _outside("'?'", 2, 5)),
        ("labels = 'caf\u00e9'", _outside("'\u00e9'", 1, 4)),
    ]

    assert await _refusals(invoke, project, declared) == _refused(declared)


@pytest.mark.covers("source list", "--json")
async def test_a_badly_written_keyword_or_quoted_value_is_refused_with_its_line_and_column(
    project, invoke
) -> None:
    declared = [
        (
            "labels = 'a OR b'",
            "the keyword 'or' is written in lowercase; quote the value (\"OR\") to use it as a "
            "label (line 1, column 3)",
        ),
        ("labels = '\"open'", "a quoted value is not closed (line 1, column 1)"),
        (
            "labels = '\"a\\n\"'",
            'a backslash must be followed by " or \\ inside quotes (line 1, column 3)',
        ),
        ("labels = '\"\"'", "a quoted value is empty (line 1, column 1)"),
        (
            "labels = '''\"a\nb\"'''",
            "a control character or line break inside a quoted value (line 1, column 3)",
        ),
    ]

    assert await _refusals(invoke, project, declared) == _refused(declared)


@pytest.mark.covers("source list", "--json")
async def test_a_value_or_operator_out_of_place_is_refused_with_its_line_and_column(
    project, invoke
) -> None:
    due = "expected 'and', 'or' or "
    quote = "; quote a value that holds a space"
    declared = [
        (
            "labels = 'help wanted'",
            f"{due}the end of the expression, found the value 'wanted'{quote} (line 1, column 6)",
        ),
        (
            "labels = 'a and'",
            "expected a value or '(', found the end of the expression (line 1, column 6)",
        ),
        ("labels = 'or b'", "expected a value or '(', found 'or' (line 1, column 1)"),
        ("labels = '()'", "expected a value or '(', found ')' (line 1, column 2)"),
        ("labels = '(a b)'", f"{due}')', found the value 'b'{quote} (line 1, column 4)"),
    ]

    assert await _refusals(invoke, project, declared) == _refused(declared)


@pytest.mark.covers("source list", "--json")
async def test_an_unbalanced_parenthesis_is_refused_at_the_column_it_stands_on(
    project, invoke
) -> None:
    declared = [
        ("labels = '(a or b'", "'(' is not closed (line 1, column 1)"),
        ("labels = 'x and (a and (b)'", "'(' is not closed (line 1, column 7)"),
        ("labels = 'a)'", "')' closes no '(' (line 1, column 2)"),
    ]

    assert await _refusals(invoke, project, declared) == _refused(declared)
