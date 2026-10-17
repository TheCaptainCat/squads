"""Summaries the CLI generates from the spec read right for every declared name: the right
article, the kind's own labels instead of "sub-entity", and at most 72 characters.
"""

import pytest

from _help_tree import (
    CUSTOM_KIND,
    CUSTOM_TYPE,
    CUSTOM_VOCABULARY_OVERRIDE,
    command_nodes,
    find_node,
    help_source,
    write_workflow_override,
)

pytestmark = pytest.mark.anyio

BUNDLED_TYPES = ["epic", "feature", "task", "bug", "decision", "contract", "milestone", "review"]


def _article(word: str) -> str:
    return "an" if word[0] in "aeiou" else "a"


def _summary(nodes, *path: str) -> str:
    return help_source(find_node(nodes, *path)).splitlines()[0]


@pytest.mark.parametrize("item_type", [*BUNDLED_TYPES, CUSTOM_TYPE])
async def test_a_type_group_and_its_create_command_use_the_right_article(
    project, item_type: str
) -> None:
    write_workflow_override(project.squad_dir, CUSTOM_VOCABULARY_OVERRIDE)
    nodes = command_nodes()
    art = _article(item_type)
    assert _summary(nodes, item_type) == f"Operate on {art} {item_type} by number or ID."
    assert _summary(nodes, "create", item_type) == f"Create {art} {item_type}."


async def test_a_custom_kinds_verbs_use_its_own_labels(project) -> None:
    write_workflow_override(project.squad_dir, CUSTOM_VOCABULARY_OVERRIDE)
    nodes = command_nodes()
    base = (CUSTOM_TYPE,)
    assert _summary(nodes, *base, "analyses") == "List this item's analyses."
    assert _summary(nodes, *base, "add-analysis") == "Scaffold an analysis on this item."
    assert _summary(nodes, *base, CUSTOM_KIND) == "Operate on an analysis by number or local ID."
    for verb, summary in {
        "show": "Show the analysis's status, assignee, body and discussion.",
        "body": "Set or append to the analysis's body.",
        "remove": "Delete this analysis for good, with its body and discussion.",
    }.items():
        assert _summary(nodes, *base, CUSTOM_KIND, verb) == summary


@pytest.mark.parametrize(
    ("item_type", "kind"), [("feature", "story"), ("task", "subtask"), ("review", "finding")]
)
async def test_a_bundled_kinds_verbs_never_say_sub_entity(
    project, item_type: str, kind: str
) -> None:
    nodes = command_nodes()
    plural = {"story": "stories", "subtask": "subtasks", "finding": "findings"}[kind]
    own = [
        node
        for node in nodes
        if node.path[:2] == (item_type, kind)
        or node.path in {(item_type, plural), (item_type, f"add-{kind}")}
    ]
    assert own
    said = [node.label for node in own if "sub-entity" in (node.command.help or "")]
    assert said == []
    assert all("sub-entity" not in (p.help or "") for node in own for p in node.command.params)


async def test_generated_summaries_stay_within_72_characters(project) -> None:
    write_workflow_override(project.squad_dir, CUSTOM_VOCABULARY_OVERRIDE)
    long = [node.label for node in command_nodes() if len(help_source(node).splitlines()[0]) > 72]
    assert long == []
