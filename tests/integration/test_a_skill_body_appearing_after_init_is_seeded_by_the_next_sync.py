"""Every managed skill body ``sq sync`` writes ends the same run with a ``SKILL`` item
indexing it — whatever the slug, bundled or project-declared.

``sync`` seeded only the *custom* half, and the custom vocabulary is defined by exclusion from
the bundled playbook. So a slug the bundled playbook does name, whose body file first appears
*after* init, fell between the two: the backend wrote
``agents/skills/sq-<type>.md`` with no frontmatter, nothing stamped it, and nothing healed it
either — ``sq repair`` rebuilds the index *from* frontmatter, and this file has none. Meanwhile
the generated ``.claude`` pointer referenced it and live roles preloaded its slug, so the squad
looked complete from every direction except ``sq skill <slug> show``, which exited 1.

Reachable today by removing a workflow override that had dropped the type; reachable by
construction on any future release that adds a bundled type, which would otherwise owe a
hand-written migration per type. The end state is asserted here rather than the mechanism, so
seeding may be reorganised freely as long as nothing is left bare.
"""

import pytest

from squads import __version__
from squads._services import _service as service
from squads._workflow import ROSTER_SKILL

pytestmark = pytest.mark.anyio

#: Every bundled type except ``guide`` — a `[selected]` list, which is the only way to *drop*
#: a type (deep-merge alone never deletes). Written with the version stamp the override lint
#: expects so the squad under test is a clean one.
_KEPT = [
    "epic",
    "feature",
    "task",
    "bug",
    "decision",
    "review",
    "role",
    "skill",
    "operator",
]


def _drop_guide(squad_dir) -> None:
    path = squad_dir / ".overrides" / "workflow.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# squads:override-base:{__version__}\n[selected]\nitems = {_KEPT!r}\n", encoding="utf-8"
    )


def _skill_files(paths) -> list[str]:
    return sorted(p.name for p in (paths.squad_dir / "agents" / "skills").glob("*.md"))


async def test_a_type_restored_after_init_gets_its_skill_indexed_on_the_next_sync(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    _drop_guide(tmp_path / "squads")
    result = await service.init(root=tmp_path, backend=["claude_code"], roles_spec="minimal")
    paths = result.paths
    # Eagerly prove the setup did what it claims: a broken/ignored override falls back to the
    # bundled spec fail-soft, which would make everything below pass for the wrong reason.
    # ``open_service`` (not ``Service(paths)``) is what resolves the override, exactly as the
    # CLI does -- a bare ``Service`` is handed the bundled spec and would never see the drop.
    assert "guide" not in service.open_service().spec.items
    assert not any(name.endswith("sq-guide.md") for name in _skill_files(paths))

    (tmp_path / "squads" / ".overrides" / "workflow.toml").unlink()
    svc = service.open_service()
    assert "guide" in svc.spec.items  # the type is back

    assert await svc.sync() == []

    skill = await service.open_service().roster_item(ROSTER_SKILL, "sq-guide")
    assert skill is not None, "the restored type's skill body was written but never indexed"
    assert skill.path.split("/")[-1].startswith("SKILL-")  # convention-named, not the bare slug
    assert skill.path.endswith("-sq-guide.md")
    # No bare slug-named residue left behind, and the body the pointer names is the indexed one.
    assert "sq-guide.md" not in _skill_files(paths)
    pointer = (tmp_path / ".claude" / "skills" / "sq-guide" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert skill.path in pointer


async def test_seeding_on_sync_is_idempotent_and_allocates_nothing_the_second_time(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, backend=["claude_code"], roles_spec="minimal")
    paths = result.paths

    await service.Service(paths).sync()
    first = _skill_files(paths)
    counter_after_first = (await service.Service(paths).store.load()).counter

    await service.Service(paths).sync()

    assert _skill_files(paths) == first
    assert (await service.Service(paths).store.load()).counter == counter_after_first


async def test_a_skill_body_no_seeding_vocabulary_claims_is_reported_by_sync(tmp_path, monkeypatch):
    """The variant seeding cannot close, and the reason it is reported here rather than by
    ``sq check``: a bare body under the skills folder whose slug no seeder names. ``check``
    tolerates that shape by design (it cannot tell it from a corpus that has genuinely never
    been stamped), so ``sync`` — which is what writes these files — names it instead."""
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, backend=["claude_code"], roles_spec="minimal")
    paths = result.paths
    stray = paths.squad_dir / "agents" / "skills" / "sq-nothing-declares-this.md"
    stray.write_text("<!-- sq:body -->\nbody\n<!-- sq:body:end -->\n", encoding="utf-8")

    reported = await service.Service(paths).sync()

    assert any(stray.name in line for line in reported), reported
    assert await service.Service(paths).check() == []  # check stays quiet, as documented

    stray.unlink()
    assert await service.Service(paths).sync() == []
