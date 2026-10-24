"""The `deferred` status-role flag is read from the role a status resolves to. An override that
redeclares the finding `Open` list keeps its own machine, and a spec whose item lifecycle reaches
a status of a deferred role does not load.
"""

import pytest

from _selection_table import service_with
from squads._errors import SquadsError

pytestmark = pytest.mark.anyio

_POSTPONED_ON_TASKS = """
[statuses.Postponed]
role = "deferred"

[lifecycles.work.transitions]
InProgress = ["$(*lifecycles.work.transitions.InProgress)", "Postponed"]
"""


async def test_an_override_redeclaring_open_keeps_its_machine_without_the_new_states(
    project,
) -> None:
    svc = service_with(
        project.squad_dir, '[lifecycles.finding.transitions]\nOpen = ["Fixed", "WontFix"]\n'
    )
    assert svc.spec.subentity_workflow("finding").states == {"Open", "Fixed", "WontFix", "Verified"}
    review = (await svc.create("review", "r", author="manager")).item
    await svc.add_finding(review.id, "f")
    with pytest.raises(SquadsError, match="not a valid finding status"):
        await svc.update_finding(review.id, "F1", status="Noted")


async def test_an_item_lifecycle_reaching_a_deferred_role_status_is_refused_at_load(
    project,
) -> None:
    with pytest.raises(SquadsError, match="deferred = true"):
        service_with(project.squad_dir, _POSTPONED_ON_TASKS)
