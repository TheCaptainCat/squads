"""A daemon whose configuration changed since it started answers `retiring` to the next request,
runs nothing and exits; one whose configuration did not change keeps serving."""

import json

import pytest

from squads._daemon_link import daemon_identity
from tests._endpoint_client import command_body

pytestmark = pytest.mark.anyio


async def test_a_daemon_whose_configuration_was_edited_answers_retiring_and_exits(
    project, run_daemon, invoke
) -> None:
    running = run_daemon(project)
    config = project.config_path
    config.write_text(config.read_text(encoding="utf-8") + "\n# edited\n", encoding="utf-8")

    status, body = running.get_over_cli("/v1/items")

    assert (status, json.loads(body)) == (503, {"not_executed": "retiring"})
    running.wait_until_exited()
    assert daemon_identity(running.endpoint) is None


async def test_a_daemon_whose_overrides_gained_a_file_answers_retiring_and_exits(
    project, run_daemon, invoke
) -> None:
    running = run_daemon(project)
    assert (await invoke(["override", "scaffold", "playbook"])).exit_code == 0

    status, body = running.get_over_cli("/v1/items")

    assert (status, json.loads(body)) == (503, {"not_executed": "retiring"})
    running.wait_until_exited()


async def test_a_daemon_whose_configuration_did_not_change_keeps_serving(
    project, run_daemon
) -> None:
    running = run_daemon(project)

    first, _ = running.get_over_cli("/v1/items")
    second, _ = running.get_over_cli("/v1/items")

    assert (first, second) == (200, 200)


async def test_a_command_sent_to_a_daemon_whose_configuration_changed_is_declined_and_not_run(
    project, run_daemon
) -> None:
    running = run_daemon(project)
    config = project.config_path
    config.write_text(config.read_text(encoding="utf-8") + "\n# edited\n", encoding="utf-8")

    status, body = running.get_over_cli("/v1/commands", "POST", command_body(["--help"]))

    assert (status, json.loads(body)) == (503, {"not_executed": "retiring"})
    running.wait_until_exited()
