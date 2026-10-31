"""`HttpApi.declined` says whether the last call was declined by a daemon whose configuration had
changed, so a session reloads what it read after a retirement and not on every call after."""

import pytest

from squads._api import _ops as ops
from squads._api._dto._workflow import CatalogRequest
from squads._cli._calls import local_api
from squads._cli._remote import build_http_api

pytestmark = pytest.mark.anyio


async def test_the_flag_is_set_by_a_retirement_and_clear_again_on_the_next_daemon(
    project, run_daemon
) -> None:
    running = run_daemon(project)
    api = build_http_api(running.endpoint, local=local_api)
    await api.call(ops.WORKFLOW_TYPES, CatalogRequest())
    assert api.declined is False

    config = project.config_path
    config.write_text(config.read_text(encoding="utf-8") + "\n# edited\n", encoding="utf-8")
    await api.call(ops.WORKFLOW_TYPES, CatalogRequest())
    assert api.declined is True

    running.wait_until_exited()
    run_daemon(project)
    await api.call(ops.WORKFLOW_TYPES, CatalogRequest())
    assert api.declined is False
