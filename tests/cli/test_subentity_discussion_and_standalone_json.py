"""Every ``subentities`` entry in ``sq show --json`` carries a ``discussion`` array (additive,
mirroring the item-level shape), across every built-in sub-entity kind — and the standalone
``sq <type> <n> <kind> <k> show --json`` emits exactly that same object shape from one shared
construction path.
"""

import json

import pytest

pytestmark = pytest.mark.anyio

# (kind, parent type, create-item args, add-verb args, sub-entity local id)
_KINDS = [
    ("story", "feature", "add-story", "US1"),
    ("subtask", "task", "add-subtask", "ST1"),
    ("finding", "review", "add-finding", "F1"),
]


@pytest.mark.parametrize(("kind", "parent_type", "add_verb", "local_id"), _KINDS)
async def test_subentity_entry_carries_discussion_matching_the_human_render(
    project, invoke, kind, parent_type, add_verb, local_id
) -> None:
    await invoke(["create", parent_type, "Parent", "--author", "manager"])
    await invoke(["role", "activate", "reviewer"])
    await invoke([parent_type, "2", add_verb, "Child sub-entity"])
    c1 = await invoke(
        [parent_type, "2", kind, local_id, "comment", "--as", "manager", "-m", "First."]
    )
    c2 = await invoke(
        [parent_type, "2", kind, local_id, "comment", "--as", "reviewer", "-m", "Second."]
    )
    assert c1.exit_code == 0, c1.output
    assert c2.exit_code == 0, c2.output

    shown = await invoke([parent_type, "2", "show", "--json"])
    assert shown.exit_code == 0, shown.output
    payload = json.loads(shown.output)
    entry = payload["subentities"][0]
    assert [c["body"] for c in entry["discussion"]] == ["- First.", "- Second."]
    # the author resolves to the role's display name, exactly like the item-level discussion.
    assert entry["discussion"][0]["author"] != entry["discussion"][1]["author"]

    human = await invoke([parent_type, "2", kind, local_id, "show"])
    assert "First." in human.output and "Second." in human.output


@pytest.mark.parametrize(("kind", "parent_type", "add_verb", "local_id"), _KINDS)
async def test_subentity_entry_discussion_is_an_empty_array_with_no_comments(
    project, invoke, kind, parent_type, add_verb, local_id
) -> None:
    await invoke(["create", parent_type, "Parent", "--author", "manager"])
    await invoke([parent_type, "2", add_verb, "Child sub-entity"])

    shown = await invoke([parent_type, "2", "show", "--json"])
    payload = json.loads(shown.output)
    assert payload["subentities"][0]["discussion"] == []


@pytest.mark.parametrize(("kind", "parent_type", "add_verb", "local_id"), _KINDS)
async def test_standalone_subentity_show_json_matches_the_item_payload_entry_exactly(
    project, invoke, kind, parent_type, add_verb, local_id
) -> None:
    await invoke(["create", parent_type, "Parent", "--author", "manager"])
    await invoke([parent_type, "2", add_verb, "Child sub-entity"])
    await invoke([parent_type, "2", kind, local_id, "comment", "--as", "manager", "-m", "Note."])

    item_shown = await invoke([parent_type, "2", "show", "--json"])
    from_item = json.loads(item_shown.output)["subentities"][0]

    standalone = await invoke([parent_type, "2", kind, local_id, "show", "--json"])
    assert standalone.exit_code == 0, standalone.output
    assert json.loads(standalone.output) == from_item


@pytest.mark.parametrize(("kind", "parent_type", "add_verb", "local_id"), _KINDS)
async def test_standalone_subentity_show_json_fails_cleanly_on_a_nonexistent_local_id(
    project, invoke, kind, parent_type, add_verb, local_id
) -> None:
    await invoke(["create", parent_type, "Parent", "--author", "manager"])

    result = await invoke([parent_type, "2", kind, local_id, "show", "--json"])
    assert result.exit_code != 0
    assert result.output.strip()
