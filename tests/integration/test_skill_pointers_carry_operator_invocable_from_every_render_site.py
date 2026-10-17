"""The Claude Code skill pointer carries ``user-invocable: false`` exactly when the skill resolves
not operator-invocable, and the three places that render one agree: the managed writer
(init and sync), the item entry (regen) and the pure render ``sq check`` compares with disk."""

from pathlib import Path

import pytest

from _helpers import plant_attribute
from _invocable_squad import SHAPES, build_squad, drifted, pointer, pointer_lines
from squads._models._attributes import AttributeKey
from squads._services import _service as service

pytestmark = pytest.mark.anyio

LINE = "user-invocable: false"

#: (id, stored value) — a stored value below, equal to and above each shape's default.
STORED = [("absent", None), ("true", True), ("false", False)]


def _expected(declared: bool, stored: bool | None) -> bool:
    return declared if stored is None else stored


@pytest.mark.parametrize("stored_id,stored", STORED, ids=[row[0] for row in STORED])
@pytest.mark.parametrize("shape", SHAPES)
async def test_every_site_renders_the_resolved_value_and_check_sees_no_drift(
    shape, stored_id, stored, tmp_path, monkeypatch, invoke
) -> None:
    slug, declared = SHAPES[shape]
    paths = await build_squad(tmp_path, monkeypatch, invoke)
    svc = service.Service(paths, spec=None)
    assert await drifted(invoke) == []
    item = await svc.roster_item("skill", slug)
    assert item is not None
    await plant_attribute(svc, item.id, AttributeKey.OPERATOR_INVOCABLE, stored)
    rel = f".claude/skills/{slug}/SKILL.md"
    hidden = not _expected(declared, stored)

    # The pure render reads the item: a stored value that moves the render shows as drift.
    assert (await drifted(invoke) == [rel]) is ((LINE in pointer_lines(paths, slug)) != hidden)

    r = await invoke(["sync"])  # the managed writer
    assert r.exit_code == 0, r.output
    after_sync = pointer(paths, slug)
    assert (LINE in after_sync.splitlines()) is hidden
    assert await drifted(invoke) == []

    r = await invoke(["skill", slug, "regen"])  # the item entry
    assert r.exit_code == 0, r.output
    assert pointer(paths, slug) == after_sync
    assert await drifted(invoke) == []


async def test_the_first_write_of_init_renders_every_bundled_pointer_at_its_declared_default(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = (await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)).paths
    skills = sorted((paths.root / ".claude" / "skills").iterdir())
    assert skills
    for skill in skills:
        assert LINE in (skill / "SKILL.md").read_text(encoding="utf-8").splitlines(), skill.name


async def test_init_then_sync_stores_no_operator_invocable_key_anywhere(
    tmp_path, monkeypatch, invoke
) -> None:
    paths = await build_squad(tmp_path, monkeypatch, invoke)
    for _ in range(2):
        r = await invoke(["sync"])
        assert r.exit_code == 0, r.output
    stored = [
        p
        for p in paths.squad_dir.rglob("*")
        if p.is_file() and "operator_invocable" in p.read_text(encoding="utf-8", errors="ignore")
    ]
    assert stored == []


async def test_sync_is_a_fixed_point_over_the_generated_pointers(
    tmp_path, monkeypatch, invoke
) -> None:
    paths = await build_squad(tmp_path, monkeypatch, invoke)
    snapshot = {p: p.read_bytes() for p in (paths.root / ".claude").rglob("*") if p.is_file()}
    r = await invoke(["sync"])
    assert r.exit_code == 0, r.output
    assert {p: p.read_bytes() for p in snapshot} == snapshot


async def test_role_pointers_never_carry_the_host_key(tmp_path, monkeypatch, invoke) -> None:
    paths = await build_squad(tmp_path, monkeypatch, invoke)
    roles = sorted((paths.root / ".claude" / "agents").glob("*.md"))
    assert roles
    for role in roles:
        assert "user-invocable" not in role.read_text(encoding="utf-8")


async def test_the_host_key_is_spelled_only_in_the_pointer_template() -> None:
    src = Path(__file__).parent.parent.parent / "src" / "squads"
    holders = sorted(
        p.relative_to(src).as_posix()
        for p in src.rglob("*")
        if p.is_file() and p.suffix in {".py", ".j2", ".toml", ".md"}
        if "user-invocable" in p.read_text(encoding="utf-8")
    )
    assert holders == ["_rendering/templates/claude/pointer_skill.md.j2"]
