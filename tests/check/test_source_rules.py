"""The `sq check` rules over items a tracker feeds: duplicate holders of one issue, a source that is
undeclared, disabled or unreadable, an issue the pull lost, operator identities and comment
attribute lines. None can be selected or deselected, so each has a breach case only.

A sourced item is arranged by editing the file of an item the CLI created, since only a pull writes
the record.
"""

import re

import pytest

from tests.check._arrange import (
    activate,
    add_roster,
    address,
    create,
    edit_item_file,
    issue,
    ok,
    repair,
    write_override,
)

pytestmark = pytest.mark.anyio

SOURCES = (
    '[sources.platform]\nconnector = "gitlab"\nproject = "platform/api"\n'
    'base_url = "https://tracker.example"\n\n[sources.platform.maps.types.type]\nissue = "task"\n'
)


def _record(name: str, issue_id: str, state: str) -> str:
    return (
        f"source:\n  name: '{name}'\n  id: '{issue_id}'\n  key: 'platform/api#{issue_id}'\n"
        f"  state: '{state}'\n  updated_at: '2026-11-03T20:41:07Z'\n  author_id: '4567'\n"
        "  author_handle: 'pchat'\n"
    )


async def _mirror(
    invoke,
    project,
    title: str,
    *,
    name: str = "platform",
    issue_id: str = "12",
    state: str = "open",
) -> str:
    """A task whose file holds a source record for issue *issue_id* of source *name*."""
    task = await create(invoke, "task", title, "tech-lead", desc="d")
    edit_item_file(project, task, "\nstatus:", f"\n{_record(name, issue_id, state)}status:")
    await repair(invoke)
    return task


@pytest.fixture
async def squad(project, invoke):
    """The `minimal` squad with `tech-lead` live and the `platform` source declared."""
    await activate(invoke, "tech-lead")
    write_override(project, "sources.toml", SOURCES)
    return project


@pytest.mark.breaches("source_id_unique")
async def test_two_items_that_hold_one_issue_are_an_error(squad, invoke, check_json) -> None:
    first = await _mirror(invoke, squad, "First")
    assert await check_json() == ([], 0)

    second = await _mirror(invoke, squad, "Second")

    assert await check_json() == (
        [
            issue(
                "source_id_unique",
                "error",
                first,
                f"{first}, {second} all hold issue platform/api#12 of source 'platform'; "
                "the pull refreshes each, so keep one and run `source unlink` on the others",
            )
        ],
        3,
    )


@pytest.mark.breaches("source_declared")
async def test_an_item_whose_source_is_disabled_or_undeclared_is_a_warning(
    squad, invoke, check_json
) -> None:
    task = await _mirror(invoke, squad, "Mirror")
    assert await check_json() == ([], 0)

    write_override(squad, "sources.toml", SOURCES.replace("project", "enabled = false\nproject"))
    disabled = await check_json()
    write_override(squad, "sources.toml", SOURCES.replace("platform", "other"))
    undeclared = await check_json()

    assert (disabled, undeclared) == (
        (
            [
                issue(
                    "source_declared",
                    "warn",
                    task,
                    "source 'platform' is disabled (enabled = false); no pull refreshes "
                    "platform/api#12",
                )
            ],
            0,
        ),
        (
            [
                issue(
                    "source_declared",
                    "warn",
                    task,
                    "source 'platform' is not declared in sources.toml; no pull refreshes "
                    "platform/api#12",
                )
            ],
            0,
        ),
    )


@pytest.mark.breaches("source_issue_reachable")
async def test_an_item_whose_issue_the_pull_lost_is_a_warning(squad, invoke, check_json) -> None:
    kept = await _mirror(invoke, squad, "Kept", issue_id="12")
    assert await check_json() == ([], 0)

    gone = await _mirror(invoke, squad, "Gone", issue_id="13", state="gone")
    moved = await _mirror(invoke, squad, "Moved", issue_id="14", state="out-of-filter")

    assert kept not in {i["item"] for i in (await check_json())[0]}
    assert await check_json() == (
        [
            issue(
                "source_issue_reachable",
                "warn",
                gone,
                "the tracker no longer answers for platform/api#13 (gone); keep the item, or "
                f"run `sq {' '.join(address(gone))} source unlink`",
            ),
            issue(
                "source_issue_reachable",
                "warn",
                moved,
                "platform/api#14 is out-of-filter: the filter rejects it or it left the scope; "
                "keep the "
                "item, or "
                f"run `sq {' '.join(address(moved))} source unlink`",
            ),
        ],
        0,
    )


@pytest.mark.breaches("sources_loads")
async def test_a_sources_document_that_does_not_load_is_an_error(squad, invoke, check_json) -> None:
    await _mirror(invoke, squad, "Mirror")
    assert await check_json() == ([], 0)

    write_override(squad, "sources.toml", SOURCES.replace('"task"', '"nowhere"'))

    path = squad.squad_dir / ".overrides" / "sources.toml"
    assert await check_json() == (
        [
            issue(
                "sources_loads",
                "error",
                "sources",
                f"sources config invalid: {path}: invalid sources after merge: source "
                "'platform': maps.types.type: 'issue' -> 'nowhere' is not an item type",
            )
        ],
        3,
    )


GITLAB = '[sources.platform]\nconnector = "gitlab"\nbase_url = "https://tracker.example"\n'
TYPES = '\n[sources.platform.maps.types.type]\nissue = "task"\n'
PROJECT = 'project = "platform/api"\n'
FILTER_HEAD = f"{PROJECT}\n[sources.platform.filter]\n"
GITLAB_SHAPE = (
    "a path of the shape group/subgroup/project (segments of letters, digits, _, - and . "
    "joined by /, no empty, . or .. segment, no whitespace)"
)
JIRA = '[sources.platform]\nconnector = "jira"\nbase_url = "https://tracker.example"\n'


async def _refused_at_load(squad, check_json, text: str, message: str) -> None:
    """The report is clean, then `sources.toml` is replaced by *text*: it names *message* as the
    one reason the document does not load."""
    assert await check_json() == ([], 0)

    write_override(squad, "sources.toml", text)

    path = squad.squad_dir / ".overrides" / "sources.toml"
    assert await check_json() == (
        [
            issue(
                "sources_loads",
                "error",
                "sources",
                f"sources config invalid: {path}: invalid sources after merge: "
                f"source 'platform': {message}",
            )
        ],
        3,
    )


async def _refused_filter(squad, check_json, expression: str, message: str) -> None:
    """*expression* is the `labels` side of the filter; *message* is what the load says of it."""
    await _refused_at_load(
        squad,
        check_json,
        GITLAB + FILTER_HEAD + expression + TYPES,
        f"sources.platform.filter.labels: {message}",
    )


@pytest.mark.breaches("sources_loads")
async def test_a_source_with_no_type_map_does_not_load(squad, check_json) -> None:
    await _refused_at_load(
        squad,
        check_json,
        GITLAB + PROJECT,
        "maps.types is empty; map at least one tracker type or label to an item type",
    )


@pytest.mark.breaches("sources_loads")
async def test_a_connector_version_it_does_not_register_does_not_load(squad, check_json) -> None:
    await _refused_at_load(
        squad,
        check_json,
        GITLAB + 'version = "v1"\n' + PROJECT + TYPES,
        "connector 'gitlab' has no version 'v1' (known: v4)",
    )


@pytest.mark.breaches("sources_loads")
async def test_a_connector_with_several_versions_needs_one_named(squad, check_json) -> None:
    await _refused_at_load(
        squad,
        check_json,
        JIRA + TYPES,
        "connector 'jira' has several versions, so `version` is required (known: cloud-v3, dc-v2)",
    )


@pytest.mark.breaches("sources_loads")
async def test_a_source_without_a_scope_key_does_not_load(squad, check_json) -> None:
    await _refused_at_load(
        squad,
        check_json,
        GITLAB + TYPES,
        "no scope key; name exactly one of: project, group",
    )


@pytest.mark.breaches("sources_loads")
async def test_a_source_with_two_scope_keys_does_not_load(squad, check_json) -> None:
    await _refused_at_load(
        squad,
        check_json,
        GITLAB + PROJECT + 'group = "platform"\n' + TYPES,
        "2 scope keys (project, group); name exactly one of: project, group",
    )


@pytest.mark.breaches("sources_loads")
async def test_a_scope_key_of_another_connector_does_not_load(squad, check_json) -> None:
    await _refused_at_load(
        squad,
        check_json,
        GITLAB + 'repository = "acme/api"\n' + TYPES,
        "'repository' is not a scope key of gitlab@v4 (scope keys: project, group)",
    )


@pytest.mark.breaches("sources_loads")
async def test_an_empty_scope_value_does_not_load(squad, check_json) -> None:
    await _refused_at_load(
        squad,
        check_json,
        GITLAB + 'group = "  "\n' + TYPES,
        "scope key 'group' must be a non-empty string",
    )


@pytest.mark.breaches("sources_loads")
async def test_a_gitlab_project_path_of_the_wrong_shape_does_not_load(squad, check_json) -> None:
    await _refused_at_load(
        squad,
        check_json,
        GITLAB + 'project = "platform/../x"\n' + TYPES,
        f"scope key 'project' is 'platform/../x', which is not {GITLAB_SHAPE}",
    )


@pytest.mark.breaches("sources_loads")
async def test_a_gitlab_group_path_of_the_wrong_shape_does_not_load(squad, check_json) -> None:
    await _refused_at_load(
        squad,
        check_json,
        GITLAB + 'group = "a//b"\n' + TYPES,
        "scope key 'group' is 'a//b', which is not "
        + GITLAB_SHAPE.replace("group/subgroup/project", "group/subgroup"),
    )


@pytest.mark.breaches("sources_loads")
async def test_a_github_repository_of_the_wrong_shape_does_not_load(squad, check_json) -> None:
    github = (
        '[sources.platform]\nconnector = "github"\nbase_url = "https://tracker.example"\n'
        'repository = "acme/../../orgs/acme"\n'
    )
    await _refused_at_load(
        squad,
        check_json,
        github + TYPES,
        "scope key 'repository' is 'acme/../../orgs/acme', which is not "
        + GITLAB_SHAPE.replace("group/subgroup/project", "owner/repo"),
    )


@pytest.mark.breaches("sources_loads")
async def test_a_jira_jql_with_an_order_by_clause_does_not_load(squad, check_json) -> None:
    await _refused_at_load(
        squad,
        check_json,
        JIRA + "version = \"cloud-v3\"\njql = 'labels = squads Order\tBy created'\n" + TYPES,
        "jql holds an ORDER BY clause; the pull lists the whole scope in no order, so remove "
        "the clause",
    )


@pytest.mark.breaches("sources_loads")
async def test_a_string_filter_does_not_load(squad, check_json) -> None:
    await _refused_at_load(
        squad,
        check_json,
        GITLAB + PROJECT + 'filter = "squads"\n' + TYPES,
        "sources.platform.filter is a table of one expression per side (sides: labels, type), "
        "not a string; the issues a source follows are named by its scope, one of: project, group",
    )


@pytest.mark.breaches("sources_loads")
async def test_a_filter_side_the_version_lacks_does_not_load(squad, check_json) -> None:
    await _refused_at_load(
        squad,
        check_json,
        GITLAB + FILTER_HEAD + 'priority = "high"\n' + TYPES,
        "sources.platform.filter.priority: the connector has no side 'priority' "
        "(sides: labels, type)",
    )


@pytest.mark.breaches("sources_loads")
async def test_an_empty_filter_table_does_not_load(squad, check_json) -> None:
    await _refused_at_load(
        squad,
        check_json,
        GITLAB + FILTER_HEAD + TYPES,
        "sources.platform.filter is an empty table; write a side (labels, type) or remove it",
    )


@pytest.mark.breaches("sources_loads")
async def test_a_blank_filter_expression_does_not_load(squad, check_json) -> None:
    await _refused_filter(squad, check_json, "labels = '''  \n '''\n", "the expression is empty")


@pytest.mark.breaches("sources_loads")
async def test_a_character_outside_the_grammar_is_refused_with_its_line_and_column(
    squad, check_json
) -> None:
    await _refused_filter(
        squad,
        check_json,
        "labels = '''a and\n  b ?'''\n",
        "the character '?' is not allowed outside quotes; quote the value (line 2, column 5)",
    )


@pytest.mark.breaches("sources_loads")
async def test_a_control_character_outside_quotes_does_not_load(squad, check_json) -> None:
    await _refused_filter(
        squad,
        check_json,
        'labels = "a\\u0001b"\n',
        "the control character U+0001 is not allowed in an expression (line 1, column 2)",
    )


@pytest.mark.breaches("sources_loads")
async def test_an_uppercase_keyword_does_not_load(squad, check_json) -> None:
    await _refused_filter(
        squad,
        check_json,
        "labels = 'a OR b'\n",
        "keywords are lowercase: write 'or', or quote the value (\"OR\") to match it "
        "(line 1, column 3)",
    )


@pytest.mark.breaches("sources_loads")
async def test_an_unclosed_quoted_value_does_not_load(squad, check_json) -> None:
    await _refused_filter(
        squad,
        check_json,
        "labels = '\"open'\n",
        "a quoted value is not closed (line 1, column 1)",
    )


@pytest.mark.breaches("sources_loads")
async def test_a_backslash_that_escapes_nothing_in_a_quoted_value_does_not_load(
    squad, check_json
) -> None:
    await _refused_filter(
        squad,
        check_json,
        "labels = '\"a\\n\"'\n",
        'a backslash must be followed by " or \\ inside quotes (line 1, column 3)',
    )


@pytest.mark.breaches("sources_loads")
async def test_an_empty_quoted_value_does_not_load(squad, check_json) -> None:
    await _refused_filter(
        squad, check_json, "labels = '\"\"'\n", "a quoted value is empty (line 1, column 1)"
    )


@pytest.mark.breaches("sources_loads")
async def test_a_line_break_inside_a_quoted_value_does_not_load(squad, check_json) -> None:
    await _refused_filter(
        squad,
        check_json,
        "labels = '''\"a\nb\"'''\n",
        "a control character or line break inside a quoted value (line 1, column 3)",
    )


@pytest.mark.breaches("sources_loads")
async def test_two_values_with_no_operator_between_them_do_not_load(squad, check_json) -> None:
    await _refused_filter(
        squad,
        check_json,
        "labels = 'help wanted'\n",
        "expected 'and', 'or' or the end of the expression, found the value 'wanted'; quote a "
        "value that holds a space (line 1, column 6)",
    )


@pytest.mark.breaches("sources_loads")
async def test_an_operator_with_no_right_hand_side_does_not_load(squad, check_json) -> None:
    await _refused_filter(
        squad,
        check_json,
        "labels = 'a and'\n",
        "expected a value or '(', found the end of the expression (line 1, column 6)",
    )


@pytest.mark.breaches("sources_loads")
async def test_an_operator_where_a_value_belongs_does_not_load(squad, check_json) -> None:
    await _refused_filter(
        squad,
        check_json,
        "labels = 'or b'\n",
        "expected a value or '(', found 'or' (line 1, column 1)",
    )


@pytest.mark.breaches("sources_loads")
async def test_a_parenthesis_that_is_never_closed_does_not_load(squad, check_json) -> None:
    await _refused_filter(
        squad, check_json, "labels = '(a or b'\n", "'(' is not closed (line 1, column 1)"
    )


@pytest.mark.breaches("sources_loads")
async def test_a_parenthesis_that_closes_nothing_does_not_load(squad, check_json) -> None:
    await _refused_filter(
        squad, check_json, "labels = 'a)'\n", "')' closes no '(' (line 1, column 2)"
    )


@pytest.mark.breaches("sources_loads")
async def test_an_expression_nested_past_the_limit_does_not_load(squad, check_json) -> None:
    await _refused_filter(
        squad,
        check_json,
        f"labels = '{'not ' * 65}a'\n",
        "nested more than 64 levels deep with 'not' or '(' (line 1, column 257)",
    )


@pytest.mark.breaches("sources_loads")
async def test_a_map_naming_a_value_where_a_side_belongs_does_not_load(squad, check_json) -> None:
    await _refused_at_load(
        squad,
        check_json,
        GITLAB + PROJECT + '\n[sources.platform.maps.types]\nsquads = "task"\n',
        "maps.types.squads is a value, not a side: write it under maps.types.<side>, one of: "
        "labels, type",
    )


@pytest.mark.breaches("sources_loads")
async def test_a_field_map_naming_a_side_the_connector_lacks_does_not_load(
    squad, check_json
) -> None:
    await _refused_at_load(
        squad,
        check_json,
        GITLAB
        + PROJECT
        + TYPES
        + '\n[sources.platform.maps.fields.priority.priority]\n"high" = "high"\n',
        "maps name the side 'priority', which the connector does not have (known: labels, type)",
    )


@pytest.mark.breaches("sources_loads")
async def test_a_sources_document_that_is_not_toml_does_not_load(squad, check_json) -> None:
    assert await check_json() == ([], 0)

    write_override(squad, "sources.toml", "[sources.platform\n", stamp=None)

    path = squad.squad_dir / ".overrides" / "sources.toml"
    assert await check_json() == (
        [
            issue(
                "sources_loads",
                "error",
                "sources",
                f"sources config invalid: malformed sources override {path}: "
                "Expected ']' at the end of a table declaration (at line 1, column 18)",
            )
        ],
        3,
    )


@pytest.mark.breaches("source_author_declared")
async def test_an_author_naming_no_declared_source_is_a_warning(squad, invoke, check_json) -> None:
    task = await create(invoke, "task", "Mirror", "tech-lead", desc="d")
    await ok(invoke, *address(task), "comment", "--as", "tech-lead", "-m", "Noted.")
    assert await check_json() == ([], 0)

    edit_item_file(squad, task, "author: tech-lead", "author: source:phantom")
    edit_item_file(squad, task, "] `tech-lead` ", "] `source:ghost` ")
    await repair(invoke)

    assert await check_json() == (
        [
            issue(
                "source_author_declared",
                "warn",
                task,
                f"an author `source:{name}` names no source declared in sources.toml",
            )
            for name in ("ghost", "phantom")
        ],
        0,
    )


@pytest.fixture
async def operators(invoke) -> tuple[str, str]:
    """Two operators, `op-alice` and `op-bob`, and the ids their rows carry."""
    return (
        await add_roster(invoke, "operator", "Alice Tester"),
        await add_roster(invoke, "operator", "Bob Tester"),
    )


@pytest.mark.breaches("identity_source_declared")
async def test_an_identity_naming_no_declared_source_is_a_warning(
    squad, invoke, check_json, operators
) -> None:
    alice, _bob = operators
    await ok(invoke, "operator", "op-alice", "update", "--identities", "platform=4567")
    assert await check_json() == ([], 0)

    await ok(invoke, "operator", "op-alice", "update", "--identities", "ghost=4567")

    assert await check_json() == (
        [
            issue(
                "identity_source_declared",
                "warn",
                alice,
                "identity 'ghost' names no source declared in sources.toml",
            )
        ],
        0,
    )


@pytest.mark.breaches("identity_id_unique")
async def test_two_operators_holding_one_tracker_user_are_an_error(
    squad, invoke, check_json, operators
) -> None:
    alice, _bob = operators
    await ok(invoke, "operator", "op-alice", "update", "--identities", "platform=4567")
    await ok(invoke, "operator", "op-bob", "update", "--identities", "platform=4568")
    assert await check_json() == ([], 0)

    await ok(invoke, "operator", "op-bob", "update", "--identities", "platform=4567")

    assert await check_json() == (
        [
            issue(
                "identity_id_unique",
                "error",
                alice,
                "operators op-alice, op-bob all hold user '4567' of source 'platform'; "
                "a tracker user is one operator",
            )
        ],
        3,
    )


@pytest.mark.breaches("comment_attributes_valid")
async def test_a_comment_whose_attribute_line_is_not_a_json_object_of_strings_is_an_error(
    squad, invoke, check_json
) -> None:
    task = await create(invoke, "task", "Mirror", "tech-lead", desc="d")
    await ok(invoke, *address(task), "comment", "--as", "tech-lead", "-m", "Noted.")
    assert await check_json() == ([], 0)

    edit_item_file(squad, task, ":\n  - Noted.", ':\n  <!-- sq:attrs {"n":1} -->\n  - Noted.')

    found, code = await check_json()
    assert (code, len(found), found[0]["rule"], found[0]["level"], found[0]["item"]) == (
        3,
        1,
        "comment_attributes_valid",
        "error",
        task,
    )
    assert re.fullmatch(
        r"the comment by `tech-lead` at \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ has an sq:attrs line "
        r"that is not one JSON object of strings; it reads as comment text",
        found[0]["message"],
    )


async def test_prose_that_names_the_attribute_tag_is_not_an_attribute_line(
    squad, invoke, check_json
) -> None:
    task = await create(invoke, "task", "Mirror", "tech-lead", desc="d")
    await ok(
        invoke,
        *address(task),
        "comment",
        "--as",
        "tech-lead",
        "-m",
        "The sq:attrs line is the payload under a header.",
    )
    body = (
        "Example of a comment:\n\n```\n"
        "- [2026-11-02T09:14:00Z] `tech-lead` Olivia Lead:\n"
        "  sq:attrs not-json\n```"
    )
    await ok(invoke, *address(task), "body", "-m", body)
    # The marker guard refuses the wrapped form through the CLI, so the file is edited directly.
    edit_item_file(squad, task, "  sq:attrs not-json", "  <!-- sq:attrs not-json -->")

    assert await check_json() == ([], 0)


async def test_a_body_example_naming_an_undeclared_source_author_is_not_a_comment(
    squad, invoke, check_json
) -> None:
    task = await create(invoke, "task", "Mirror", "tech-lead", desc="d")
    body = "Example of a comment:\n\n```\n- [2026-11-02T09:14:00Z] `source:nowhere` Ghost:\n```"
    await ok(invoke, *address(task), "body", "-m", body)

    assert await check_json() == ([], 0)


@pytest.mark.breaches("source_id_unique")
async def test_two_items_of_two_sources_on_one_tracker_that_hold_one_issue_are_an_error(
    squad, invoke, check_json
) -> None:
    write_override(squad, "sources.toml", SOURCES + "\n" + SOURCES.replace("platform", "mirror"))
    first = await _mirror(invoke, squad, "First")
    assert await check_json() == ([], 0)

    second = await _mirror(invoke, squad, "Second", name="mirror")

    assert await check_json() == (
        [
            issue(
                "source_id_unique",
                "error",
                first,
                f"{first}, {second} all hold issue platform/api#12 of sources 'mirror', "
                "'platform'; the pull refreshes each, so keep one and run `source unlink` on "
                "the others",
            )
        ],
        3,
    )
