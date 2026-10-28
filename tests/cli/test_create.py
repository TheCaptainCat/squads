"""`sq create <type>`: the title, the author, the parent, the attributes an item is created
with, the body, and the options only some types carry."""

import json
from typing import Any

import pytest

pytestmark = pytest.mark.anyio

USAGE = "Usage: sq create task [OPTIONS] TITLE\nTry 'sq create task --help' for help.\n"


async def _shown(invoke, item_type: str, number: int) -> dict[str, Any]:
    """The `show --json` object of the item *item_type* *number*."""
    result = await invoke([item_type, str(number), "show", "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


@pytest.mark.covers("create <type>", "TITLE")
@pytest.mark.covers("create <type>", "--author")
async def test_create_makes_a_draft_task_and_prints_its_id_and_path(
    populated_project, invoke
) -> None:
    result = await invoke(["create", "task", "Index the corpus", "--author", "manager"])
    path = populated_project.squad_dir / "tasks" / "TASK-000005-index-the-corpus.md"
    assert result.exit_code == 0
    assert "".join(result.output.split()) == f"createdTASK-5→{path}"
    item = await _shown(invoke, "task", 5)
    assert (item["title"], item["status"], item["author"], item["parent"]) == (
        "Index the corpus",
        "Draft",
        "manager",
        None,
    )


@pytest.mark.covers("create <type>", "--author")
async def test_author_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    result = await invoke(["create", "task", "Index", "--author", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: manager\n",
    )


async def test_author_is_required(project, invoke) -> None:
    result = await invoke(["create", "task", "Index"])
    assert (result.exit_code, result.output) == (
        2,
        USAGE + "╭─ Error ──────────────────────────────────────────────────────────────────────╮\n"
        "│ Missing option '--author'.                                                   │\n"
        "╰──────────────────────────────────────────────────────────────────────────────╯\n",
    )


async def test_title_is_required(project, invoke) -> None:
    result = await invoke(["create", "task", "--author", "manager"])
    assert (result.exit_code, result.output) == (
        2,
        USAGE + "╭─ Error ──────────────────────────────────────────────────────────────────────╮\n"
        "│ Missing argument 'TITLE'.                                                    │\n"
        "╰──────────────────────────────────────────────────────────────────────────────╯\n",
    )


@pytest.mark.covers("create <type>", "--parent")
async def test_parent_sets_the_parent_the_type_allows(populated_project, invoke) -> None:
    result = await invoke(["create", "task", "Child", "--author", "manager", "--parent", "2"])
    assert result.exit_code == 0, result.output
    assert (await _shown(invoke, "task", 5))["parent"] == "FEAT-2"


@pytest.mark.covers("create <type>", "--parent")
async def test_parent_refuses_a_type_the_parent_rule_does_not_allow(
    populated_project, invoke
) -> None:
    result = await invoke(["create", "task", "Child", "--author", "manager", "--parent", "4"])
    assert (result.exit_code, result.output) == (
        1,
        "error: a task's parent must be of type feature; link a bug or review with "
        "`sq task <n> ref add <id> --kind fixes|addresses` (got review)\n",
    )


@pytest.mark.covers("create <type>", "--parent")
async def test_parent_refuses_a_number_no_item_has(populated_project, invoke) -> None:
    result = await invoke(["create", "task", "Child", "--author", "manager", "--parent", "99"])
    assert (result.exit_code, result.output) == (
        1,
        "error: no item with number 99 (use a full ID like TYPE-99 or bare 99)\n",
    )


@pytest.mark.covers("create <type>", "--parent")
async def test_parent_refuses_an_empty_value_instead_of_creating_a_parentless_item(
    populated_project, invoke
) -> None:
    result = await invoke(["create", "task", "Child", "--author", "manager", "--parent", ""])
    assert (result.exit_code, result.output) == (
        1,
        "error: --parent needs an item ID; omit --parent to create without a parent\n",
    )


@pytest.mark.covers("create <type>", "--desc")
async def test_desc_sets_the_summary(project, invoke) -> None:
    result = await invoke(
        ["create", "task", "Index", "--author", "manager", "--desc", "Build the index"]
    )
    assert result.exit_code == 0, result.output
    assert (await _shown(invoke, "task", 2))["description"] == "Build the index"


@pytest.mark.covers("create <type>", "--label")
async def test_label_repeated_adds_each_label_in_order(project, invoke) -> None:
    result = await invoke(
        ["create", "task", "Index", "--author", "manager", "--label", "urgent", "--label", "infra"]
    )
    assert result.exit_code == 0, result.output
    assert (await _shown(invoke, "task", 2))["labels"] == ["urgent", "infra"]


@pytest.mark.covers("create <type>", "--ref")
async def test_ref_with_and_without_a_kind_is_stored_as_given(populated_project, invoke) -> None:
    result = await invoke(
        ["create", "task", "Index", "--author", "manager", "--ref", "2:implements", "--ref", "4"]
    )
    assert result.exit_code == 0, result.output
    assert (await _shown(invoke, "task", 5))["refs"] == ["FEAT-2:implements", "REV-4"]


@pytest.mark.covers("create <type>", "--ref")
async def test_ref_refuses_a_kind_the_workflow_does_not_declare(populated_project, invoke) -> None:
    result = await invoke(["create", "task", "Index", "--author", "manager", "--ref", "2:bogus"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown ref kind 'bogus'. Valid kinds: addresses, blocks, depends-on, "
        "duplicates, fixes, implements, related, scopes, supersedes, targets\n",
    )


@pytest.mark.covers("create <type>", "--ref")
async def test_ref_refuses_an_item_that_does_not_exist(populated_project, invoke) -> None:
    result = await invoke(["create", "task", "Index", "--author", "manager", "--ref", "99"])
    assert (result.exit_code, result.output) == (
        1,
        "error: no item with number 99 (use a full ID like TYPE-99 or bare 99)\n",
    )


@pytest.mark.covers("create <type>", "--assignee")
async def test_assignee_sets_the_assignee(project, invoke) -> None:
    result = await invoke(
        ["create", "task", "Index", "--author", "manager", "--assignee", "manager"]
    )
    assert result.exit_code == 0, result.output
    assert (await _shown(invoke, "task", 2))["assignee"] == "manager"


@pytest.mark.covers("create <type>", "--assignee")
async def test_assignee_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    result = await invoke(
        ["create", "task", "Index", "--author", "manager", "--assignee", "nobody"]
    )
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: manager\n",
    )


@pytest.mark.covers("create <type>", "--priority")
async def test_priority_sets_the_priority(project, invoke) -> None:
    result = await invoke(["create", "task", "Index", "--author", "manager", "--priority", "high"])
    assert result.exit_code == 0, result.output
    assert (await _shown(invoke, "task", 2))["priority"] == "high"


@pytest.mark.covers("create <type>", "--priority")
async def test_priority_refuses_a_code_the_collection_does_not_declare(project, invoke) -> None:
    result = await invoke(["create", "task", "Index", "--author", "manager", "--priority", "nope"])
    assert (result.exit_code, result.output) == (
        1,
        "error: invalid priority 'nope' (one of: urgent, high, medium, low)\n",
    )


@pytest.mark.covers("create <type>", "--message")
async def test_message_repeated_becomes_one_paragraph_each_in_the_body(project, invoke) -> None:
    result = await invoke(
        ["create", "task", "Index", "--author", "manager", "-m", "First.", "-m", "Second."]
    )
    assert result.exit_code == 0, result.output
    assert (await _shown(invoke, "task", 2))["body"] == "First.\n\nSecond."


@pytest.mark.covers("create <type>", "--file")
async def test_file_reads_the_body_from_the_file(project, invoke, tmp_path) -> None:
    source = tmp_path / "body.md"
    source.write_text("From a file.\n\nTwo paragraphs.\n", encoding="utf-8")
    result = await invoke(["create", "task", "Index", "--author", "manager", "--file", str(source)])
    assert result.exit_code == 0, result.output
    assert (await _shown(invoke, "task", 2))["body"] == "From a file.\n\nTwo paragraphs."


@pytest.mark.covers("create <type>", "--message", "--file")
async def test_message_excludes_file(project, invoke, tmp_path) -> None:
    source = tmp_path / "body.md"
    source.write_text("From a file.\n", encoding="utf-8")
    result = await invoke(
        ["create", "task", "Index", "--author", "manager", "-m", "Inline.", "--file", str(source)]
    )
    assert (result.exit_code, result.output) == (
        1,
        "error: provide the body via -m or --file, not both\n",
    )
    listed = await invoke(["list", "--json"])
    assert [item["id"] for item in json.loads(listed.output)] == ["ROLE-1"]


@pytest.mark.covers("create <type>", "--json")
async def test_json_prints_the_created_item_as_show_does(project, invoke) -> None:
    result = await invoke(["create", "task", "Index", "--author", "manager", "--json"])
    assert result.exit_code == 0, result.output
    created = json.loads(result.output)
    shown = await _shown(invoke, "task", 2)
    assert created == {key: shown[key] for key in created}
    assert (created["id"], created["title"], created["status"]) == ("TASK-2", "Index", "Draft")


@pytest.mark.covers("create guide", "TITLE")
@pytest.mark.covers("create guide", "--author")
async def test_create_guide_makes_a_draft_guide_and_prints_its_id_and_path(project, invoke) -> None:
    await invoke(["role", "activate", "architect"])
    result = await invoke(["create", "guide", "Setup", "--author", "architect"])
    path = project.squad_dir / "guides" / "GUIDE-000003-setup.md"
    assert result.exit_code == 0
    assert "".join(result.output.split()) == f"createdGUIDE-3→{path}"
    item = await _shown(invoke, "guide", 3)
    assert (item["title"], item["status"], item["author"], item["parent"]) == (
        "Setup",
        "Draft",
        "architect",
        None,
    )


@pytest.mark.covers("create guide", "--author")
async def test_create_guide_refuses_an_author_that_is_not_registered(project, invoke) -> None:
    result = await invoke(["create", "guide", "Setup", "--author", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: manager\n",
    )


@pytest.mark.covers("create guide", "--tag")
@pytest.mark.covers("create guide", "--tech")
async def test_create_guide_stores_each_tag_in_order_and_the_tech(project, invoke) -> None:
    result = await invoke(
        [
            "create",
            "guide",
            "Setup",
            "--author",
            "manager",
            "--tag",
            "ops",
            "--tag",
            "dev",
            "--tech",
            "python",
        ]
    )
    assert result.exit_code == 0, result.output
    shown = await _shown(invoke, "guide", 2)
    assert (shown["tags"], shown["tech"]) == (["ops", "dev"], "python")


@pytest.mark.covers("create guide", "--desc")
async def test_create_guide_desc_sets_the_summary(project, invoke) -> None:
    result = await invoke(
        ["create", "guide", "Setup", "--author", "manager", "--desc", "How to set up"]
    )
    assert result.exit_code == 0, result.output
    assert (await _shown(invoke, "guide", 2))["description"] == "How to set up"


@pytest.mark.covers("create guide", "--assignee")
async def test_create_guide_assignee_sets_the_assignee(project, invoke) -> None:
    result = await invoke(
        ["create", "guide", "Setup", "--author", "manager", "--assignee", "manager"]
    )
    assert result.exit_code == 0, result.output
    assert (await _shown(invoke, "guide", 2))["assignee"] == "manager"


@pytest.mark.covers("create guide", "--assignee")
async def test_create_guide_assignee_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    result = await invoke(
        ["create", "guide", "Setup", "--author", "manager", "--assignee", "nobody"]
    )
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: manager\n",
    )


@pytest.mark.covers("create guide", "--parent")
async def test_create_guide_parent_refuses_a_parent_because_a_guide_takes_none(
    populated_project, invoke
) -> None:
    """No guide parent is accepted under the bundled spec; the refusal is the case."""
    result = await invoke(["create", "guide", "Setup", "--author", "manager", "--parent", "2"])
    assert (result.exit_code, result.output) == (1, "error: guide takes no parent (got FEAT-2)\n")


@pytest.mark.covers("create guide", "--parent")
async def test_create_guide_parent_refuses_a_number_no_item_has(populated_project, invoke) -> None:
    result = await invoke(["create", "guide", "Setup", "--author", "manager", "--parent", "99"])
    assert (result.exit_code, result.output) == (
        1,
        "error: no item with number 99 (use a full ID like TYPE-99 or bare 99)\n",
    )


@pytest.mark.covers("create guide", "--parent")
async def test_create_guide_parent_refuses_an_empty_value_instead_of_creating_a_parentless_guide(
    populated_project, invoke
) -> None:
    result = await invoke(["create", "guide", "Setup", "--author", "manager", "--parent", ""])
    assert (result.exit_code, result.output) == (
        1,
        "error: --parent needs an item ID; omit --parent to create without a parent\n",
    )


@pytest.mark.covers("create guide", "--message")
async def test_create_guide_message_repeated_becomes_one_paragraph_each_in_the_body(
    project, invoke
) -> None:
    result = await invoke(
        ["create", "guide", "Setup", "--author", "manager", "-m", "First.", "-m", "Second."]
    )
    assert result.exit_code == 0, result.output
    assert (await _shown(invoke, "guide", 2))["body"] == "First.\n\nSecond."


@pytest.mark.covers("create guide", "--file")
async def test_create_guide_file_reads_the_body_from_the_file(project, invoke, tmp_path) -> None:
    source = tmp_path / "body.md"
    source.write_text("From a file.\n\nTwo paragraphs.\n", encoding="utf-8")
    result = await invoke(
        ["create", "guide", "Setup", "--author", "manager", "--file", str(source)]
    )
    assert result.exit_code == 0, result.output
    assert (await _shown(invoke, "guide", 2))["body"] == "From a file.\n\nTwo paragraphs."


@pytest.mark.covers("create guide", "--message", "--file")
async def test_create_guide_message_excludes_file(project, invoke, tmp_path) -> None:
    source = tmp_path / "body.md"
    source.write_text("From a file.\n", encoding="utf-8")
    result = await invoke(
        ["create", "guide", "Setup", "--author", "manager", "-m", "Inline.", "--file", str(source)]
    )
    assert (result.exit_code, result.output) == (
        1,
        "error: provide the body via -m or --file, not both\n",
    )
    listed = await invoke(["list", "--json"])
    assert [item["id"] for item in json.loads(listed.output)] == ["ROLE-1"]


@pytest.mark.covers("create guide", "--json")
async def test_create_guide_json_prints_the_created_guide_as_show_does(project, invoke) -> None:
    result = await invoke(["create", "guide", "Setup", "--author", "manager", "--json"])
    assert result.exit_code == 0, result.output
    created = json.loads(result.output)
    shown = await _shown(invoke, "guide", 2)
    assert created == {key: shown[key] for key in created}
    assert (created["id"], created["title"], created["status"]) == ("GUIDE-2", "Setup", "Draft")


@pytest.mark.covers("create <type>", "--severity")
async def test_bug_severity_sets_the_severity(project, invoke) -> None:
    result = await invoke(["create", "bug", "Crash", "--author", "manager", "--severity", "high"])
    assert result.exit_code == 0, result.output
    assert (await _shown(invoke, "bug", 2))["severity"] == "high"


@pytest.mark.covers("create <type>", "--severity")
async def test_bug_severity_refuses_a_code_the_collection_does_not_declare(project, invoke) -> None:
    result = await invoke(["create", "bug", "Crash", "--author", "manager", "--severity", "zzz"])
    assert (result.exit_code, result.output) == (
        1,
        "error: invalid severity 'zzz' (one of: critical, high, medium, low, info)\n",
    )
