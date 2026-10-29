"""An operation's `json_field` names a field of its response type, and only the operations of
the commands whose frozen `--json` document is an array (or `workflow view`) set one."""

from squads._api._ops import OPERATIONS

#: The operations allowed a `json_field`: those of the closed set of array commands, added as
#: each of them moves onto its operation.
ALLOWED = frozenset(
    {
        "blocked",
        "board.list",
        "check",
        "inbox",
        "items.comments",
        "items.comments.remove",
        "items.list",
        "items.subentities.comments.remove",
        "items.subentities.list",
        "memory.list",
        "memory.search",
        "mine",
        "operators.comments",
        "operators.comments.remove",
        "operators.list",
        "overrides.diff",
        "overrides.list",
        "reflog",
        "roles.catalog",
        "roles.comments",
        "roles.comments.remove",
        "roles.list",
        "search",
        "skills.comments",
        "skills.comments.remove",
        "tree",
        "workflow.collections",
        "workflow.lifecycles",
        "workflow.ref-kinds",
        "workflow.roles",
        "workflow.statuses",
        "workflow.subentity-kinds",
        "workflow.types",
        "workflow.view",
        "workflow.views",
        "workload",
    }
)


def test_every_json_field_names_a_field_of_the_response() -> None:
    wrong = {
        op.name: op.json_field
        for op in OPERATIONS
        if op.json_field is not None and op.json_field not in op.response.model_fields
    }
    assert not wrong, f"json_field names no field of the response type: {wrong}"


def test_only_the_array_commands_set_a_json_field() -> None:
    setting = {op.name for op in OPERATIONS if op.json_field is not None}
    assert setting <= ALLOWED, (
        f"a shape without a frozen array document is an object: {sorted(setting - ALLOWED)}"
    )
    assert "items.list" in setting
