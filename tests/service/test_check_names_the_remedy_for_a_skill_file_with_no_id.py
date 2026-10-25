"""A stamped skill file with no `id` gets the remedy that works for its state: `sync` for the
canonical file, delete for a stray copy of a healthy skill, delete-and-sync when it was the only
copy, and nothing managed for a skill the user wrote."""

from pathlib import Path

import pytest

from _helpers import make_service
from squads._sections import split_frontmatter
from squads._services import _service as service

pytestmark = pytest.mark.anyio


@pytest.fixture
async def svc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal")
    return make_service(result.paths)


def _canonical(svc) -> Path:
    (found,) = (svc.paths.squad_dir / "agents" / "skills").glob("SKILL-*-sq-task.md")
    return found


def _stripped_canonical(svc, canonical: Path) -> Path:
    canonical.write_text(split_frontmatter(canonical.read_text())[1])
    return canonical


def _renamed_beside_a_healthy_canonical(svc, canonical: Path) -> Path:
    stray = canonical.with_name(canonical.stem + "-renamed.md")
    stray.write_text(split_frontmatter(canonical.read_text())[1])
    return stray


def _renamed_alone(svc, canonical: Path) -> Path:
    stray = canonical.with_name(canonical.stem + "-renamed.md")
    stray.write_text(split_frontmatter(canonical.read_text())[1])
    canonical.unlink()
    return stray


def _user_authored(svc, canonical: Path) -> Path:
    stray = canonical.with_name("SKILL-000900-my-own.md")
    stray.write_text(split_frontmatter(canonical.read_text())[1])
    return stray


_SHAPES = [
    pytest.param(_stripped_canonical, ["run `sq sync`"], [], id="canonical-name"),
    pytest.param(
        _renamed_beside_a_healthy_canonical,
        ["stray copy", "healthy in SKILL-", "delete this file"],
        ["fix the file"],
        id="renamed-canonical-healthy",
    ),
    pytest.param(
        _renamed_alone,
        ["no healthy file holds managed skill 'sq-task'", "delete this file", "`sq sync`"],
        ["fix the file"],
        id="renamed-no-canonical",
    ),
    pytest.param(
        _user_authored, [], ["sq sync", "stray copy", "managed skill"], id="user-authored"
    ),
]


@pytest.mark.parametrize(("shape", "expected", "absent"), _SHAPES)
async def test_the_remedy_matches_the_state_of_the_file(svc, shape, expected, absent):
    stray = shape(svc, _canonical(svc))

    messages = [i.message for i in await svc.check() if i.item == stray.name]

    (message,) = messages
    assert "no `id` in frontmatter" in message
    for part in expected:
        assert part in message
    for part in absent:
        assert part not in message
