"""Squad resolution (``_paths.resolve``/``open_service``) takes the requesting client's
working directory as an explicit input rather than reading the process cwd — proves the
one process/many squads acceptance: two requests naming two different squad roots resolve
fully independently, and neither is remembered for a later request that supplies none.
"""

from pathlib import Path

import pytest

from squads._paths import resolve
from squads._services import _service as service
from squads._services._service import open_service

pytestmark = pytest.mark.anyio


def _ensure_dir(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)


async def _init_squad(root: Path) -> Path:
    _ensure_dir(root)
    result = await service.init(root=root, roles_spec="", no_claude=True)
    return result.paths.squad_dir


async def test_resolve_independently_resolves_two_client_cwds_in_one_process(tmp_path):
    root_a, root_b = tmp_path / "squad-a", tmp_path / "squad-b"
    squad_dir_a = await _init_squad(root_a)
    squad_dir_b = await _init_squad(root_b)

    paths_a = resolve(client_cwd=root_a)
    paths_b = resolve(client_cwd=root_b)

    assert paths_a.squad_dir == squad_dir_a
    assert paths_b.squad_dir == squad_dir_b
    assert paths_a.squad_dir != paths_b.squad_dir


async def test_a_client_cwd_resolution_is_not_remembered_for_the_next_call(tmp_path):
    root_a, root_b = tmp_path / "squad-a", tmp_path / "squad-b"
    await _init_squad(root_a)
    squad_dir_b = await _init_squad(root_b)

    resolve(client_cwd=root_a)  # a prior "request" resolving a different squad
    again = resolve(client_cwd=root_b)

    assert again.squad_dir == squad_dir_b  # unaffected by the previous call's client_cwd


async def test_open_service_threads_an_explicit_client_cwd_to_two_independent_services(tmp_path):
    root_a, root_b = tmp_path / "squad-a", tmp_path / "squad-b"
    squad_dir_a = await _init_squad(root_a)
    squad_dir_b = await _init_squad(root_b)

    svc_a = open_service(client_cwd=root_a)
    svc_b = open_service(client_cwd=root_b)

    assert svc_a.paths.squad_dir == squad_dir_a
    assert svc_b.paths.squad_dir == squad_dir_b


async def test_resolve_falls_back_to_the_process_cwd_when_no_client_cwd_is_given(
    tmp_path, monkeypatch
):
    """One-shot CLI behaviour: an absent client_cwd resolves exactly like today."""
    squad_dir = await _init_squad(tmp_path)
    monkeypatch.chdir(tmp_path)

    assert resolve().squad_dir == squad_dir
