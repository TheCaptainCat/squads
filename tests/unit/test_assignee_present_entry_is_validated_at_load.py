"""`assignee_present` at spec load: it takes no parameter, and a type whose lifecycle holds no
status of a role declaring `live = true` cannot select it. The refusal names the type, the entry
and the declaration that is missing; the check is accepted once a status of a live role exists.
"""

import pytest

from squads._errors import SquadsError
from squads._workflow import bundled_spec
from squads._workflow._models import ItemSpec, WorkflowSpec


def _load(item_type: str, entries: list[str], *, lifecycle: str | None = None) -> WorkflowSpec:
    base = bundled_spec()
    update: dict[str, object] = {"validators": entries}
    if lifecycle is not None:
        update["lifecycle"] = lifecycle
    items: dict[str, ItemSpec] = {
        **base.items,
        item_type: base.items[item_type].model_copy(update=update),
    }
    return WorkflowSpec.model_validate(
        {
            "items": items,
            "statuses": dict(base.statuses),
            "lifecycles": dict(base.lifecycles),
            "prefix_to_type": dict(base.prefix_to_type),
            "alias_to_type": dict(base.alias_to_type),
            "collections": dict(base.collections),
            "subentity_kinds": dict(base.subentity_kinds),
            "roles": dict(base.roles),
            "ref_kinds": dict(base.ref_kinds),
            "views": dict(base.views),
        }
    )


def test_the_entry_takes_no_parameter() -> None:
    with pytest.raises(SquadsError, match="takes no param"):
        _load("task", ["assignee_present:manager"])


@pytest.mark.parametrize("item_type", ["decision", "guide"])
def test_a_type_whose_lifecycle_has_no_live_status_is_refused(item_type: str) -> None:
    with pytest.raises(SquadsError) as raised:
        _load(item_type, ["assignee_present"])
    text = str(raised.value)
    assert f"item {item_type!r}" in text
    assert "'assignee_present'" in text
    assert "live = true" in text


@pytest.mark.parametrize("item_type", ["decision", "guide"])
def test_the_same_type_is_accepted_once_its_lifecycle_has_a_live_status(item_type: str) -> None:
    _load(item_type, ["assignee_present"], lifecycle="work")


@pytest.mark.parametrize("item_type", ["epic", "feature", "task", "bug", "review", "contract"])
def test_a_type_with_a_live_status_is_accepted(item_type: str) -> None:
    _load(item_type, ["assignee_present"])
