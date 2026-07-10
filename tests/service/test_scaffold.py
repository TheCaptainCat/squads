"""Proves the service layer collects, runs, and can reach the `svc` fixture; delete once real
service tests land in Phase 2.
"""


async def test_service_directory_collects_and_reaches_svc_fixture(svc):
    assert svc.paths.root.exists()
