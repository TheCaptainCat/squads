"""Proves the integration layer collects and can chain a service call with a CLI invocation;
delete once real integration tests land in Phase 2.
"""


async def test_integration_directory_collects_across_service_and_cli(svc, invoke):
    result = await invoke(["check"])
    assert result.exit_code == 0
    assert svc.paths.root.exists()
