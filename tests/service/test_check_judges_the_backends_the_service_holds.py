"""``sq check`` judges the backend instances the service was built with, not fresh ones: a backend
handed to the service that declares a managed file nobody wrote is reported by name."""

import pytest

from _helpers import make_service
from squads._backends._agents_md._backend import AgentsMdBackend
from squads._backends._base import AgentBackend, BackendContext
from squads._paths import SquadPaths

pytestmark = pytest.mark.anyio


class _OtherBackend(AgentsMdBackend):
    name = "other"

    def managed_paths(self, ctx: BackendContext) -> list[str]:
        return ["other-backend-file.md"]


async def test_check_reports_a_missing_file_of_a_backend_only_the_service_holds(
    project: SquadPaths,
) -> None:
    held: list[AgentBackend] = [_OtherBackend()]
    svc = make_service(project, backends=lambda: held)

    issues = await svc.check()

    assert any(
        "other-backend-file.md" in issue.item and "backend: other" in issue.message
        for issue in issues
    ), issues
