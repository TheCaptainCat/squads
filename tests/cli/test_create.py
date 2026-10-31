"""`sq create <type>`: the title, the author, the parent, the attributes an item is created
with, the body, and the options only some types carry."""

import json
import re
from typing import Any

import pytest

from tests._profile import selected
from tests.cli._output import unknown_option

P = selected()

pytestmark = pytest.mark.anyio

USAGE = f"Usage: sq create {P.ref} [OPTIONS] {{title}}\nTry 'sq create {P.ref} --help' for help.\n"


async def _shown(invoke, item_type: str, number: int) -> dict[str, Any]:
    """The `show --json` object of the item *item_type* *number*."""
    result = await invoke([item_type, str(number), "show", "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


@pytest.mark.covers("create <type>", "title")
@pytest.mark.covers("create <type>", "--author")
@pytest.mark.bundled_only(
    "the case creates or reads a bundled type's own options, defaults or messages"
)
async def test_create_makes_a_draft_task_and_prints_its_id_and_path(
    populated_project, invoke
) -> None:
    result = await invoke(["create", P.ref, "Index the corpus", "--author", "manager"])
    path = populated_project.squad_dir / P.ref_folder / f"{P.ref_prefix}-000005-index-the-corpus.md"
    assert result.exit_code == 0
    assert "".join(result.output.split()) == f"createdTASK-5→{path}"
    item = await _shown(invoke, P.ref, 5)
    assert (item["title"], item["status"], item["author"], item["parent"]) == (
        "Index the corpus",
        "Draft",
        "manager",
        None,
    )


@pytest.mark.covers("create <type>", "--author")
async def test_author_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    result = await invoke(["create", P.ref, "Index", "--author", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: manager\n",
    )


@pytest.mark.covers("create <type>", "--author")
async def test_author_is_required(project, invoke) -> None:
    result = await invoke(["create", P.ref, "Index"])
    assert (result.exit_code, result.output) == (
        2,
        USAGE + "╭─ Error ──────────────────────────────────────────────────────────────────────╮\n"
        "│ Missing option '--author'.                                                   │\n"
        "╰──────────────────────────────────────────────────────────────────────────────╯\n",
    )


@pytest.mark.covers("create <type>", "title")
async def test_title_is_required(project, invoke) -> None:
    result = await invoke(["create", P.ref, "--author", "manager"])
    assert (result.exit_code, result.output) == (
        2,
        USAGE + "╭─ Error ──────────────────────────────────────────────────────────────────────╮\n"
        "│ Missing argument 'title'.                                                    │\n"
        "╰──────────────────────────────────────────────────────────────────────────────╯\n",
    )


@pytest.mark.covers("create <type>", "--parent")
async def test_parent_sets_the_parent_the_type_allows(populated_project, invoke) -> None:
    result = await invoke(["create", P.ref, "Child", "--author", "manager", "--parent", "2"])
    assert result.exit_code == 0, result.output
    assert (await _shown(invoke, P.ref, 5))["parent"] == f"{P.host_prefix}-2"


@pytest.mark.covers("create <type>", "--parent")
@pytest.mark.bundled_only(
    "the case creates or reads a bundled type's own options, defaults or messages"
)
async def test_parent_refuses_a_type_the_parent_rule_does_not_allow(
    populated_project, invoke
) -> None:
    result = await invoke(["create", P.ref, "Child", "--author", "manager", "--parent", "4"])
    assert (result.exit_code, result.output) == (
        1,
        f"error: the parent of {P.ref} items must be of type {P.host}; link a bug or {P.third} "
        f"with "
        f"`sq {P.ref} <n> ref add <id> --kind fixes|addresses` (got {P.third})\n",
    )


@pytest.mark.covers("create <type>", "--parent")
async def test_parent_refuses_a_number_no_item_has(populated_project, invoke) -> None:
    result = await invoke(["create", P.ref, "Child", "--author", "manager", "--parent", "99"])
    assert (result.exit_code, result.output) == (
        1,
        "error: no item with number 99 (use a full ID like TYPE-99 or bare 99)\n",
    )


@pytest.mark.covers("create <type>", "--parent")
async def test_parent_refuses_an_empty_value_instead_of_creating_a_parentless_item(
    populated_project, invoke
) -> None:
    result = await invoke(["create", P.ref, "Child", "--author", "manager", "--parent", ""])
    assert (result.exit_code, result.output) == (
        1,
        "error: --parent needs an item ID; omit --parent to create without a parent\n",
    )


@pytest.mark.covers("create <type>", "--desc")
async def test_desc_sets_the_summary(project, invoke) -> None:
    result = await invoke(
        ["create", P.ref, "Index", "--author", "manager", "--desc", "Build the index"]
    )
    assert result.exit_code == 0, result.output
    assert (await _shown(invoke, P.ref, 2))["description"] == "Build the index"


@pytest.mark.covers("create <type>", "--label")
async def test_label_repeated_adds_each_label_in_order(project, invoke) -> None:
    result = await invoke(
        ["create", P.ref, "Index", "--author", "manager", "--label", "urgent", "--label", "infra"]
    )
    assert result.exit_code == 0, result.output
    assert (await _shown(invoke, P.ref, 2))["labels"] == ["urgent", "infra"]


@pytest.mark.covers("create <type>", "--ref")
@pytest.mark.bundled_only(
    "the case creates or reads a bundled type's own options, defaults or messages"
)
async def test_ref_with_and_without_a_kind_is_stored_as_given(populated_project, invoke) -> None:
    result = await invoke(
        ["create", P.ref, "Index", "--author", "manager", "--ref", "2:implements", "--ref", "4"]
    )
    assert result.exit_code == 0, result.output
    assert (await _shown(invoke, P.ref, 5))["refs"] == [
        f"{P.host_prefix}-2:implements",
        f"{P.third_prefix}-4",
    ]


@pytest.mark.covers("create <type>", "--ref")
@pytest.mark.bundled_only(
    "the case creates or reads a bundled type's own options, defaults or messages"
)
async def test_ref_refuses_a_kind_the_workflow_does_not_declare(populated_project, invoke) -> None:
    result = await invoke(["create", P.ref, "Index", "--author", "manager", "--ref", "2:bogus"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown ref kind 'bogus'. Valid kinds: addresses, blocks, depends-on, "
        "duplicates, fixes, implements, related, scopes, supersedes, targets\n",
    )


@pytest.mark.covers("create <type>", "--ref")
async def test_ref_refuses_an_item_that_does_not_exist(populated_project, invoke) -> None:
    result = await invoke(["create", P.ref, "Index", "--author", "manager", "--ref", "99"])
    assert (result.exit_code, result.output) == (
        1,
        "error: no item with number 99 (use a full ID like TYPE-99 or bare 99)\n",
    )


@pytest.mark.covers("create <type>", "--assignee")
async def test_assignee_sets_the_assignee(project, invoke) -> None:
    result = await invoke(
        ["create", P.ref, "Index", "--author", "manager", "--assignee", "manager"]
    )
    assert result.exit_code == 0, result.output
    assert (await _shown(invoke, P.ref, 2))["assignee"] == "manager"


@pytest.mark.covers("create <type>", "--assignee")
async def test_assignee_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    result = await invoke(["create", P.ref, "Index", "--author", "manager", "--assignee", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: manager\n",
    )


@pytest.mark.covers("create <type>", "--<field>")
async def test_a_field_flag_sets_the_value_of_the_squads_field(populated_project, invoke) -> None:
    args = ["create", P.ref, "Index", "--author", "manager", *P.parent_args(P.ref)]
    result = await invoke([*args, P.badge_flag, P.badge_value])
    assert result.exit_code == 0, result.output
    assert (await _shown(invoke, P.ref, 5))[P.badge] == P.badge_value


@pytest.mark.covers("create <type>", "--<field>")
async def test_a_field_flag_refuses_a_code_the_collection_does_not_declare(
    populated_project, invoke
) -> None:
    args = ["create", P.ref, "Index", "--author", "manager", *P.parent_args(P.ref)]
    result = await invoke([*args, P.badge_flag, "nope"])
    assert (result.exit_code, result.output) == (
        1,
        f"error: invalid {P.badge} 'nope' (one of: {P.badge_codes})\n",
    )


@pytest.mark.covers("create <type>", "--<field>")
async def test_a_field_code_with_an_underscore_gets_a_dashed_flag(override_project, invoke) -> None:
    result = await invoke(
        ["create", "job", "Wire it", "--author", "manager", "--parent", "8", "--work-size", "m"]
    )
    assert result.exit_code == 0, result.output
    assert (await _shown(invoke, "job", 11))["badges"] == {"work_size": "m"}


@pytest.mark.covers("create <type>", "--<field>")
async def test_a_declared_field_flag_sets_the_value_the_squad_names(
    override_project, invoke
) -> None:
    result = await invoke(
        ["create", "initiative", "Open the doors", "--author", "manager", "--urgency", "later"]
    )
    assert result.exit_code == 0, result.output
    assert (await _shown(invoke, "initiative", 11))["badges"] == {"urgency": "later"}
    refused = await invoke(
        ["create", "initiative", "Open more", "--author", "manager", "--priority", "high"]
    )
    assert (refused.exit_code, refused.output) == (
        2,
        unknown_option("create initiative [OPTIONS] {title}", "create initiative", "--priority"),
    )


@pytest.mark.covers("create <type>", "--<field>")
async def test_a_field_flag_refuses_an_empty_value(populated_project, invoke) -> None:
    args = ["create", P.ref, "Index", "--author", "manager", *P.parent_args(P.ref)]
    result = await invoke([*args, P.badge_flag, ""])
    assert (result.exit_code, result.output) == (
        1,
        f"error: invalid {P.badge} '' (one of: {P.badge_codes})\n",
    )


@pytest.mark.covers("create <type>", "--message")
async def test_message_repeated_becomes_one_paragraph_each_in_the_body(project, invoke) -> None:
    result = await invoke(
        ["create", P.ref, "Index", "--author", "manager", "-m", "First.", "-m", "Second."]
    )
    assert result.exit_code == 0, result.output
    assert (await _shown(invoke, P.ref, 2))["body"] == "First.\n\nSecond."


@pytest.mark.covers("create <type>", "--file")
async def test_file_reads_the_body_from_the_file(project, invoke, tmp_path) -> None:
    source = tmp_path / "body.md"
    source.write_text("From a file.\n\nTwo paragraphs.\n", encoding="utf-8")
    result = await invoke(["create", P.ref, "Index", "--author", "manager", "--file", str(source)])
    assert result.exit_code == 0, result.output
    assert (await _shown(invoke, P.ref, 2))["body"] == "From a file.\n\nTwo paragraphs."


@pytest.mark.covers("create <type>", "--message", "--file")
async def test_message_excludes_file(project, invoke, tmp_path) -> None:
    source = tmp_path / "body.md"
    source.write_text("From a file.\n", encoding="utf-8")
    result = await invoke(
        ["create", P.ref, "Index", "--author", "manager", "-m", "Inline.", "--file", str(source)]
    )
    assert (result.exit_code, result.output) == (
        1,
        "error: provide the body via -m or --file, not both\n",
    )
    listed = await invoke(["list", "--json"])
    assert [item["id"] for item in json.loads(listed.output)] == ["ROLE-1"]


@pytest.mark.covers("create <type>", "--<attribute:list>", "--<attribute:str>")
async def test_create_stores_each_list_value_in_order_and_the_string(
    populated_project, invoke
) -> None:
    list_args = [P.attr_flag(P.list_attr), "ops", P.attr_flag(P.list_attr), "dev"]
    result = await invoke(
        [
            "create",
            P.list_type,
            "Setup",
            "--author",
            "manager",
            *P.parent_args(P.list_type),
            *list_args,
            *([P.attr_flag(P.str_attr), "python"] if P.str_type == P.list_type else []),
        ]
    )
    assert result.exit_code == 0, result.output
    shown = await _shown(invoke, P.list_type, 5)
    assert shown[P.list_attr] == ["ops", "dev"]
    if P.str_type == P.list_type:
        assert shown[P.str_attr] == "python"
    else:
        other = await invoke(
            [
                "create",
                P.str_type,
                "Owned",
                "--author",
                "manager",
                *P.parent_args(P.str_type),
                P.attr_flag(P.str_attr),
                "python",
            ]
        )
        assert other.exit_code == 0, other.output
        assert (await _shown(invoke, P.str_type, 6))[P.str_attr] == "python"


@pytest.mark.covers("create <type>", "--<field>")
@pytest.mark.bundled_only(
    "the case creates or reads a bundled type's own options, defaults or messages"
)
async def test_bug_severity_sets_the_severity(project, invoke) -> None:
    result = await invoke(["create", "bug", "Crash", "--author", "manager", "--severity", "high"])
    assert result.exit_code == 0, result.output
    assert (await _shown(invoke, "bug", 2))["severity"] == "high"


@pytest.mark.covers("create <type>", "--<field>")
@pytest.mark.bundled_only(
    "the case creates or reads a bundled type's own options, defaults or messages"
)
async def test_bug_severity_refuses_a_code_the_collection_does_not_declare(project, invoke) -> None:
    result = await invoke(["create", "bug", "Crash", "--author", "manager", "--severity", "zzz"])
    assert (result.exit_code, result.output) == (
        1,
        "error: invalid severity 'zzz' (one of: critical, high, medium, low, info)\n",
    )


@pytest.mark.covers("create <type>", "--<attribute:str>")
@pytest.mark.bundled_only(
    "the case creates or reads a bundled type's own options, defaults or messages"
)
async def test_review_target_ref_sets_the_reviewed_ref(populated_project, invoke) -> None:
    result = await invoke(
        ["create", P.third, "Audit", "--author", "manager", "--target-ref", "v1.2.0"]
    )
    assert result.exit_code == 0, result.output
    shown = await invoke([P.third, "5", "show", "--json"])
    assert json.loads(shown.output)["target_ref"] == "v1.2.0"


@pytest.mark.covers("create <type>", "--<attribute:date>")
async def test_a_date_attribute_flag_stores_the_date(populated_project, invoke) -> None:
    result = await invoke(
        [
            "create",
            P.date_type,
            "Ship",
            "--author",
            "manager",
            *P.parent_args(P.date_type),
            P.attr_flag(P.date_attr),
            "2026-12-01",
        ]
    )
    assert result.exit_code == 0, result.output
    assert (await _shown(invoke, P.date_type, 5))[P.date_attr] == "2026-12-01"


@pytest.mark.covers("create <type>", "--<attribute:date>")
async def test_a_date_attribute_flag_refuses_a_value_that_is_not_a_date(
    populated_project, invoke
) -> None:
    result = await invoke(
        [
            "create",
            P.date_type,
            "Ship",
            "--author",
            "manager",
            *P.parent_args(P.date_type),
            P.attr_flag(P.date_attr),
            "soon",
        ]
    )
    assert (result.exit_code, result.output) == (
        1,
        f"error: '{P.date_attr}' expects an ISO date (YYYY-MM-DD); got 'soon'\n",
    )


@pytest.mark.covers("create <type>", "--<attribute:list>")
async def test_list_attribute_values_split_on_commas_and_drop_blanks(
    populated_project, invoke
) -> None:
    flag = P.attr_flag(P.list_attr)
    result = await invoke(
        [
            "create",
            P.list_type,
            "Setup",
            "--author",
            "manager",
            *P.parent_args(P.list_type),
            *[flag, "a,b", flag, " ", flag, "c"],
        ]
    )
    assert result.exit_code == 0, result.output
    assert (await _shown(invoke, P.list_type, 5))[P.list_attr] == ["a", "b", "c"]


@pytest.mark.covers("create <type>", "title")
@pytest.mark.covers("create <type>", "--author")
async def test_create_help_lists_the_declared_options_before_help(override_project, invoke) -> None:
    result = await invoke(["create", "job", "--help"])
    assert result.exit_code == 0, result.output
    assert re.findall(r"^│ [* ] +(--[\w-]+)", result.output, flags=re.M) == [
        "--author",
        "--parent",
        "--desc",
        "--label",
        "--ref",
        "--assignee",
        "--message",
        "--file",
        "--json",
        "--install-completion",
        "--show-completion",
        "--work-size",
        "--owner-team",
        "--help",
    ]
    created = await invoke(["create", "job", "Ship it", "--author", "manager", "--parent", "8"])
    assert created.exit_code == 0, created.output
