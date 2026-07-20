"""Both backends read a role's resolved preload-skill list from ``BackendContext``, not by
calling ``interactions.skills_for_role`` themselves.

Parametrized over the backend registry (mirrors ``test_backend_lifecycle_contract.py``): the
same ``BackendContext.role_skills`` entry — standing in for the service-layer resolver's
output once a skill is scoped to a role — must reach both the Claude Code pointer YAML and the
AGENTS.md staging entry identically. Proves the resolved list, not an independent per-backend
lookup, is the single source for every backend.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest

from squads import _interactions as interactions
from squads._backends._agents_md._backend import AgentsMdBackend
from squads._backends._base import AgentBackend, BackendContext
from squads._backends._claude_code._backend import ClaudeCodeBackend
from squads._models._config import SquadsConfig
from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._paths import SquadPaths
from squads._roles._catalog import RoleDef

pytestmark = pytest.mark.anyio

BackendFactory = Callable[[], AgentBackend]

_BACKEND_FACTORIES: list[tuple[str, BackendFactory]] = [
    ("claude_code", ClaudeCodeBackend),
    ("agents_md", AgentsMdBackend),
]


@pytest.fixture(
    params=[name for name, _ in _BACKEND_FACTORIES], ids=[name for name, _ in _BACKEND_FACTORIES]
)
def backend(request: pytest.FixtureRequest) -> AgentBackend:
    name: str = request.param
    return dict(_BACKEND_FACTORIES)[name]()


@pytest.fixture
def squad_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def paths(squad_root: Path) -> SquadPaths:
    config = SquadsConfig(squad_dir="squads", active_backends=["claude_code"])
    squad_dir = squad_root / "squads"
    squad_dir.mkdir()
    return SquadPaths(root=squad_root, squad_dir=squad_dir, config=config)


@pytest.fixture
def role_def() -> RoleDef:
    return RoleDef(
        slug="architect",
        full_name="Robert Architect",
        title="Architect",
        description="Owns decisions.",
        mission="Design the system.",
    )


_FIXED_TS = datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC)


def _make_role_item(squad_dir: Path, slug: str) -> Item:
    folder = squad_dir / "roles"
    folder.mkdir(exist_ok=True)
    filename = f"ROLE-000001-{slug}.md"
    (folder / filename).write_text("---\nid: ROLE-1\n---\n", encoding="utf-8")
    return Item(
        sequence_id=1,
        type="role",
        title=slug,
        slug=slug,
        status="Active",
        path=f"roles/{filename}",
        created_at=_FIXED_TS,
        updated_at=_FIXED_TS,
        extra={X.SLUG: slug, X.FULL_NAME: "Robert Architect", X.TITLE: "Architect"},
    )


#: The scoped resolved list a service-layer resolver would compute — system membership plus
#: one custom skill scoped in via a ``scopes`` ref edge. Deliberately NOT what
#: ``interactions.skills_for_role`` returns on its own, so any backend that bypassed
#: ``BackendContext`` in favour of a direct call would fail the assertions below.
_RESOLVED_SKILLS = [*interactions.skills_for_role("architect"), "release-runbook"]


async def test_the_resolved_list_differs_from_the_pure_system_only_mapping() -> None:
    """Sanity: the fixture actually exercises the scoped path, not a no-op equal to the pure
    function's own output."""
    assert interactions.skills_for_role("architect") != _RESOLVED_SKILLS


async def test_each_backends_role_entry_carries_the_context_resolved_list_verbatim(
    backend: AgentBackend, paths: SquadPaths, role_def: RoleDef
) -> None:
    ctx = BackendContext(paths=paths, role_skills={"architect": _RESOLVED_SKILLS})
    await backend.ensure_scaffold(ctx)
    item = _make_role_item(paths.squad_dir, role_def.slug)
    artifact = await backend.generate_role_entry(ctx, item, role_def)
    content = (ctx.root / artifact.path).read_text(encoding="utf-8")
    assert "release-runbook" in content
    for system_skill in interactions.skills_for_role("architect"):
        assert system_skill in content


async def test_absent_from_role_skills_falls_back_to_the_pure_mapping_for_every_backend(
    backend: AgentBackend, paths: SquadPaths, role_def: RoleDef
) -> None:
    """No ``role_skills`` entry (pre-resolver call sites, e.g. brand-new role creation) —
    every backend must still fall back to the pure system-only list, not omit skills."""
    ctx = BackendContext(paths=paths)  # role_skills defaults to {}
    await backend.ensure_scaffold(ctx)
    item = _make_role_item(paths.squad_dir, role_def.slug)
    artifact = await backend.generate_role_entry(ctx, item, role_def)
    content = (ctx.root / artifact.path).read_text(encoding="utf-8")
    assert "release-runbook" not in content
    for system_skill in interactions.skills_for_role("architect"):
        assert system_skill in content
