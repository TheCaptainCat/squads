"""A source names one scope on its tracker and may narrow it with a filter expression per side;
both are checked when `sources.toml` loads."""

import json

import pytest

pytestmark = pytest.mark.anyio

BASE = 'base_url = "http://127.0.0.1:9"\n'
GITLAB = f'[sources.platform]\nconnector = "gitlab"\n{BASE}'
INVALID = "error: sources.toml: invalid sources after merge:\n  source 'platform': "
FILTER = "sources.platform.filter.labels: "


def _types(profile) -> str:
    return f'\n[sources.platform.maps.types.labels]\nbug = "{profile.ref}"\n'


async def _listed(invoke, project, text: str) -> tuple[int, str]:
    """Write `text` as the squad's sources override and load it through `sq source list`."""
    path = project.squad_dir / ".overrides" / "sources.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")
    result = await invoke(["source", "list", "--json"])
    return result.exit_code, result.output.replace(str(path), "sources.toml")


async def _refusals(
    invoke, project, profile, declared: list[tuple[str, str]]
) -> list[tuple[int, str]]:
    """The load result of each (filter text, expected refusal tail) in `declared`."""
    found: list[tuple[int, str]] = []
    for expression, _ in declared:
        source = f'{GITLAB}project = "platform/api"\n\n[sources.platform.filter]\n{expression}'
        found.append(await _listed(invoke, project, source + _types(profile)))
    return found


def _refused(declared: list[tuple[str, str]]) -> list[tuple[int, str]]:
    return [(1, f"{INVALID}{FILTER}{tail}\n") for _, tail in declared]


@pytest.mark.covers("source list", "--json")
async def test_a_source_without_a_scope_key_fails_at_load_listing_the_keys_its_version_takes(
    project, invoke, profile
) -> None:
    loaded = await _listed(invoke, project, GITLAB + _types(profile))

    assert loaded == (1, f"{INVALID}no scope key; name exactly one of: project, group\n")


@pytest.mark.covers("source list", "--json")
async def test_a_source_with_two_scope_keys_fails_at_load(project, invoke, profile) -> None:
    text = GITLAB + 'project = "platform/api"\ngroup = "platform"\n' + _types(profile)

    loaded = await _listed(invoke, project, text)

    assert loaded == (
        1,
        f"{INVALID}2 scope keys (project, group); name exactly one of: project, group\n",
    )


@pytest.mark.covers("source list", "--json")
async def test_a_scope_key_of_another_connector_fails_at_load(project, invoke, profile) -> None:
    loaded = await _listed(invoke, project, GITLAB + 'repository = "acme/api"\n' + _types(profile))

    assert loaded == (
        1,
        f"{INVALID}'repository' is not a scope key of gitlab@v4 (scope keys: project, group)\n",
    )


@pytest.mark.covers("source list", "--json")
async def test_an_empty_scope_value_fails_at_load(project, invoke, profile) -> None:
    loaded = await _listed(invoke, project, GITLAB + 'group = "  "\n' + _types(profile))

    assert loaded == (1, f"{INVALID}scope key 'group' must be a non-empty string\n")


@pytest.mark.covers("source list", "--json")
async def test_a_string_filter_fails_at_load_saying_filter_is_a_table_and_naming_the_scope_keys(
    project, invoke, profile
) -> None:
    loaded = await _listed(
        invoke, project, GITLAB + 'project = "a/b"\nfilter = "squads"\n' + _types(profile)
    )

    assert loaded == (
        1,
        f"{INVALID}sources.platform.filter is a table of one expression per side "
        "(sides: labels, type), not a string; the issues a source follows are named by its "
        "scope, one of: project, group\n",
    )


@pytest.mark.covers("source list", "--json")
async def test_a_filter_side_the_version_lacks_fails_at_load_listing_its_sides(
    project, invoke, profile
) -> None:
    text = (
        f'{GITLAB}project = "a/b"\n\n[sources.platform.filter]\npriority = "high"\n'
        f"{_types(profile)}"
    )

    loaded = await _listed(invoke, project, text)

    assert loaded == (
        1,
        f"{INVALID}sources.platform.filter.priority: the connector has no side 'priority' "
        "(sides: labels, type)\n",
    )


@pytest.mark.covers("source list", "--json")
async def test_an_empty_filter_table_or_expression_fails_at_load(project, invoke, profile) -> None:
    head = f'{GITLAB}project = "a/b"\n\n[sources.platform.filter]\n'

    empty_table = await _listed(invoke, project, head + _types(profile))
    blank = await _listed(invoke, project, head + "labels = '''  \n '''\n" + _types(profile))

    assert empty_table == (
        1,
        f"{INVALID}sources.platform.filter is an empty table; write a side (labels, type) "
        "or remove it\n",
    )
    assert blank == (1, f"{INVALID}{FILTER}the expression is empty\n")


@pytest.mark.covers("source list", "--json")
async def test_a_multi_line_expression_in_a_literal_string_loads(project, invoke, profile) -> None:
    text = (
        f'{GITLAB}project = "platform/api"\n\n[sources.platform.filter]\n'
        "labels = '''\n  (type::epic or type::story)\n  and not \"help wanted\"\n'''\n"
        "type = 'issue or incident'\n" + _types(profile)
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
    project, invoke, profile
) -> None:
    declared = [
        ("labels = 'a & b'", _outside("'&'", 1, 3)),
        ("labels = '''a and\n  b ?'''", _outside("'?'", 2, 5)),
        ('labels = "a and\\r\\n  b ?"', _outside("'?'", 2, 5)),
        ("labels = 'caf\u00e9'", _outside("'\u00e9'", 1, 4)),
    ]

    assert await _refusals(invoke, project, profile, declared) == _refused(declared)


@pytest.mark.covers("source list", "--json")
async def test_a_badly_written_keyword_or_quoted_value_is_refused_with_its_line_and_column(
    project, invoke, profile
) -> None:
    declared = [
        (
            "labels = 'a OR b'",
            "keywords are lowercase: write 'or', or quote the value (\"OR\") to match it "
            "(line 1, column 3)",
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

    assert await _refusals(invoke, project, profile, declared) == _refused(declared)


@pytest.mark.covers("source list", "--json")
async def test_a_value_or_operator_out_of_place_is_refused_with_its_line_and_column(
    project, invoke, profile
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

    assert await _refusals(invoke, project, profile, declared) == _refused(declared)


@pytest.mark.covers("source list", "--json")
async def test_an_unbalanced_parenthesis_is_refused_at_the_column_it_stands_on(
    project, invoke, profile
) -> None:
    declared = [
        ("labels = '(a or b'", "'(' is not closed (line 1, column 1)"),
        ("labels = 'x and (a and (b)'", "'(' is not closed (line 1, column 7)"),
        ("labels = 'a)'", "')' closes no '(' (line 1, column 2)"),
    ]

    assert await _refusals(invoke, project, profile, declared) == _refused(declared)


@pytest.mark.covers("source list", "--json")
async def test_a_deeply_nested_expression_is_refused_at_load_and_a_long_blank_run_loads(
    project, invoke, profile
) -> None:
    deep = "the nesting is too deep"
    declared = [
        (f"labels = '{'not ' * 65}a'", deep),
        (f"labels = '{'(' * 65}a{')' * 65}'", deep),
    ]
    found = await _refusals(invoke, project, profile, declared)
    blanks = await _refusals(
        invoke, project, profile, [(f'labels = "a and{"\\r\\n" * 1500}b"', "")]
    )

    assert [(code, text.split(FILTER)[-1]) for code, text in found] == [
        (1, "nested more than 64 levels deep with 'not' or '(' (line 1, column 257)\n"),
        (1, "nested more than 64 levels deep with 'not' or '(' (line 1, column 65)\n"),
    ]
    assert [code for code, _ in blanks] == [0]


@pytest.mark.covers("check", "--json")
async def test_sq_check_reports_a_too_deep_filter_as_a_failed_sources_load(
    project, invoke, profile
) -> None:
    await _refusals(invoke, project, profile, [(f"labels = '{'not ' * 65}a'", "")])

    checked = await invoke(["check", "--json"])

    assert "sources_loads" in checked.output
    assert "Traceback" not in checked.output


@pytest.mark.covers("source list", "--json")
async def test_a_scope_value_of_the_wrong_shape_fails_at_load_naming_the_key_and_the_shape(
    project, invoke, profile
) -> None:
    github = '[sources.platform]\nconnector = "github"\nbase_url = "http://127.0.0.1:9"\n'
    gitlab_shape = (
        "a path of the shape group/subgroup/project (segments of letters, digits, _, - and . "
        "joined by /, no empty, . or .. segment, no whitespace)"
    )
    cases = [
        (f'{GITLAB}project = "platform"\n', "project", "platform", gitlab_shape),
        (f'{GITLAB}project = "platform/../x"\n', "project", "platform/../x", gitlab_shape),
        (f'{GITLAB}project = "platform/api/"\n', "project", "platform/api/", gitlab_shape),
        (f'{GITLAB}project = "plat form/api"\n', "project", "plat form/api", gitlab_shape),
        (
            f'{GITLAB}group = "a//b"\n',
            "group",
            "a//b",
            gitlab_shape.replace("group/subgroup/project", "group/subgroup"),
        ),
        (
            f'{github}repository = "acme/../../orgs/acme"\n',
            "repository",
            "acme/../../orgs/acme",
            gitlab_shape.replace("group/subgroup/project", "owner/repo"),
        ),
    ]

    found = [await _listed(invoke, project, text + _types(profile)) for text, *_ in cases]

    assert found == [
        (1, f"{INVALID}scope key {key!r} is {value!r}, which is not {shape}\n")
        for _, key, value, shape in cases
    ]


@pytest.mark.covers("source list", "--json")
async def test_a_jira_jql_with_an_order_by_clause_fails_at_load_and_a_quoted_one_loads(
    project, invoke, profile
) -> None:
    jira = (
        '[sources.platform]\nconnector = "jira"\nversion = "cloud-v3"\n'
        'base_url = "http://127.0.0.1:9"\n'
    )
    maps = f'\n[sources.platform.maps.types.type]\nStory = "{profile.ref}"\n'

    refused = await _listed(
        invoke, project, f"{jira}jql = 'labels = squads Order\tBy created'\n" + maps
    )
    loaded = await _listed(
        invoke, project, f"{jira}jql = 'text ~ \"order by\" AND labels = x'\n" + maps
    )

    assert refused == (
        1,
        f"{INVALID}jql holds an ORDER BY clause; the pull lists the whole scope in no order, "
        "so remove the clause\n",
    )
    assert loaded[0] == 0, loaded


@pytest.mark.covers("source list", "--json")
async def test_a_quoted_value_takes_any_character_but_a_control_one(
    project, invoke, profile
) -> None:
    head = f'{GITLAB}project = "platform/api"\n\n[sources.platform.filter]\n'
    quoted = head + 'labels = "\\"a\u00a0b\\""\n'
    outside = [
        (
            'labels = "a\\u0001b"',
            "the control character U+0001 is not allowed in an expression (line 1, column 2)",
        )
    ]

    loaded = await _listed(invoke, project, quoted + _types(profile))

    assert loaded[0] == 0, loaded
    assert await _refusals(invoke, project, profile, outside) == _refused(outside)
