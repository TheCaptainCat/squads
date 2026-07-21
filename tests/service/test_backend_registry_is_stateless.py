"""The backend registry (`_backends/_registry.py`) is a CODE cache — backend *classes*,
instantiated fresh per call — never a place squad DATA can accumulate across requests.
Guards against the registry drifting into a data cache: every `get_backend()` call must
return an instance holding no attributes at all, so there is nothing for one squad's request
to leave behind for the next, and the same instance can be reused across two different
squads' `BackendContext`s with no cross-contamination.
"""

from pathlib import Path

import pytest

from squads._backends._base import BackendContext
from squads._backends._registry import get_backend
from squads._services import _service as service

pytestmark = pytest.mark.anyio


def test_get_backend_returns_a_new_instance_every_call() -> None:
    first = get_backend("claude_code")
    second = get_backend("claude_code")
    assert first is not second


def test_a_backend_instance_holds_no_instance_state() -> None:
    for name in ("claude_code", "agents_md"):
        backend = get_backend(name)
        assert vars(backend) == {}


async def test_one_backend_instance_scaffolds_two_squads_with_no_cross_contamination(
    tmp_path: Path,
) -> None:
    root_a, root_b = tmp_path / "a", tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()
    result_a = await service.init(root=root_a, roles_spec="minimal", no_claude=True)
    result_b = await service.init(root=root_b, roles_spec="minimal", no_claude=True)

    backend = get_backend("claude_code")
    assert vars(backend) == {}

    await backend.ensure_scaffold(BackendContext(paths=result_a.paths))
    assert vars(backend) == {}  # still holds nothing after scaffolding squad A

    await backend.ensure_scaffold(BackendContext(paths=result_b.paths))
    assert vars(backend) == {}  # still holds nothing after scaffolding squad B too

    assert (root_a / ".claude" / "settings.json").is_file()
    assert (root_b / ".claude" / "settings.json").is_file()
