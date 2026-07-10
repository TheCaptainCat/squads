"""End to end: ``sq sync`` regenerates both CLAUDE.md and AGENTS.md to include a custom type
declared in ``.overrides/workflow.toml`` — the alias table row and its custom alias appear in
each file — while the static Retype/Remove-vs-Cancel/Ref-kinds sections survive byte-identical
apart from the one deliberately spec-derived "Valid targets" line.
"""

import pytest

from squads._services import _service as service
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio

_STATIC_SECTIONS = ["## Retype", "## Remove vs. Cancel", "## Ref kinds"]
_OVERRIDE_TOML = """\
[lifecycles.triage]
initial = "Open"
[lifecycles.triage.transitions]
Open = ["Done", "WontFix"]
Done = []
WontFix = ["Open"]

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "triage"
aliases = ["inc"]
"""


def _write_override(squad_dir) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(_OVERRIDE_TOML, encoding="utf-8")


async def test_sync_writes_the_custom_type_into_agents_md_and_keeps_static_sections(
    tmp_path, monkeypatch, frozen_time
):
    monkeypatch.chdir(tmp_path)
    init_result = await service.init(
        root=tmp_path, roles_spec="minimal", backend=["agents_md"], _skip_skill_seed=True
    )
    paths = init_result.paths
    _write_override(paths.squad_dir)
    spec = load_workflow_spec(squad_dir=paths.squad_dir)
    await service.Service(paths, spec=spec).sync()

    text = (paths.root / "AGENTS.md").read_text(encoding="utf-8")
    assert "incident" in text and "`inc`" in text
    for header in _STATIC_SECTIONS:
        assert header in text


async def test_sync_writes_the_custom_type_into_claude_md_via_the_squads_skill(
    tmp_path, monkeypatch, frozen_time
):
    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    paths = init_result.paths
    _write_override(paths.squad_dir)
    spec = load_workflow_spec(squad_dir=paths.squad_dir)
    await service.Service(paths, spec=spec).sync()

    skills_folder = paths.squad_dir / "agents" / "skills"
    convention_files = list(skills_folder.glob("SKILL-*-squads.md"))
    skill_file = convention_files[0] if convention_files else skills_folder / "squads.md"
    text = skill_file.read_text(encoding="utf-8")
    assert "incident" in text and "`inc`" in text


async def test_static_sections_stay_byte_identical_after_a_custom_type_is_added_and_synced(
    tmp_path, monkeypatch, frozen_time
):
    monkeypatch.chdir(tmp_path)
    init_result = await service.init(
        root=tmp_path, roles_spec="minimal", backend=["agents_md"], _skip_skill_seed=True
    )
    paths = init_result.paths

    await service.Service(paths).sync()
    before = (paths.root / "AGENTS.md").read_text(encoding="utf-8")

    _write_override(paths.squad_dir)
    spec = load_workflow_spec(squad_dir=paths.squad_dir)
    await service.Service(paths, spec=spec).sync()
    after = (paths.root / "AGENTS.md").read_text(encoding="utf-8")

    def _static_tail(text: str) -> str:
        idx = text.find("**Status behaviour:**")
        end = text.find("<!-- squads:end -->", idx)
        return text[idx:end] if end != -1 else text[idx:]

    assert "`incident`" not in before
    assert "incident" in after.split("Valid targets:")[1].splitlines()[0]
    assert _static_tail(before) == _static_tail(after)
