"""Driven end to end, across every surface a role override reaches: a blank ``full_name``/
``title``/``mission`` override used to sail through ``sq sync`` and land broken in the human and
``--json`` role-show output, both backends' generated roster lines, and the Claude Code
pointer's own identity sentence -- ``sq check`` said nothing. The fix refuses it once, upstream
of all of them, so none of the four ever sees the blank value; this file proves that by
asserting the generated files are untouched, not by asserting anything about a renderer.

``sq check``'s coverage is the one acceptance criterion that needs no new reporter:
``_check_role_override_resolves`` already resolves every role override through the same seam
``sq sync``/``sq role <slug> show`` use, specifically so it reports whatever they refuse. This
file's ``check`` assertions are therefore a verification, not a new implementation.
"""

import json

import pytest

from squads._itemfile import read_frontmatter
from squads._services import _service as service
from squads._services._service import Service

pytestmark = pytest.mark.anyio


def _place_blank_override(project, slug: str) -> None:
    target = project.squad_dir / ".overrides" / "roles" / f"{slug}.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('full_name = ""\ntitle = ""\nmission = ""\n', encoding="utf-8")


async def test_sync_refuses_naming_the_file_and_every_blank_field(tmp_path, monkeypatch, invoke):
    monkeypatch.chdir(tmp_path)
    result = await service.init(
        root=tmp_path, backend=["claude_code", "agents_md"], roles_spec="minimal"
    )
    project = result.paths
    svc = Service(project)
    await svc.add_dev("python")

    claude_md_before = (project.root / "CLAUDE.md").read_text(encoding="utf-8")
    agents_md_before = (project.root / "AGENTS.md").read_text(encoding="utf-8")
    pointer_before = (project.root / ".claude" / "agents" / "python-dev.md").read_text(
        encoding="utf-8"
    )

    _place_blank_override(project, "python-dev")

    synced = await invoke(["sync"])
    assert synced.exit_code != 0, synced.output
    assert "python-dev.toml" in synced.output
    assert "full_name" in synced.output
    assert "title" in synced.output
    assert "mission" in synced.output
    # The message an adopter actually reads on their terminal, not just a non-zero exit code:
    # one clean sentence, and none of pydantic's own default rendering leaked through it.
    assert "field(s) blank or whitespace-only" in synced.output
    assert "omit the key instead to inherit" in synced.output
    for leak_marker in ("validation error for", "input_value=", "errors.pydantic.dev"):
        assert leak_marker not in synced.output.lower(), synced.output

    shown = await invoke(["role", "python-dev", "show"])
    shown_json = await invoke(["role", "python-dev", "show", "--json"])
    assert shown.exit_code != 0, shown.output
    assert shown_json.exit_code != 0, shown_json.output
    assert "field(s) blank or whitespace-only" in shown.output

    checked = await invoke(["check"])
    assert checked.exit_code != 0, checked.output
    assert "python-dev.toml" in checked.output

    # None of the four generated surfaces ever saw the blank value -- the refused sync wrote
    # nothing, so each is exactly what it was before the override was placed.
    assert (project.root / "CLAUDE.md").read_text(encoding="utf-8") == claude_md_before
    assert (project.root / "AGENTS.md").read_text(encoding="utf-8") == agents_md_before
    assert (project.root / ".claude" / "agents" / "python-dev.md").read_text(
        encoding="utf-8"
    ) == pointer_before
    for surface_name, text in (
        ("CLAUDE.md", claude_md_before),
        ("AGENTS.md", agents_md_before),
        (".claude pointer", pointer_before),
    ):
        assert "****" not in text, f"{surface_name} carries a broken empty-bold roster line"
        assert "You are , the " not in text, f"{surface_name} carries a broken identity sentence"


async def test_dev_add_itself_refuses_a_pre_existing_blank_override(project, svc):
    from squads._errors import SquadsError

    target = project.squad_dir / ".overrides" / "roles" / "rust-dev.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('full_name = ""\n', encoding="utf-8")

    with pytest.raises(SquadsError, match="full_name"):
        await svc.add_dev("rust")


async def test_check_json_carries_the_blank_field_error(project, svc, invoke) -> None:
    """The free-coverage claim, pinned precisely: ``check --json`` (the CI-facing surface, not
    just the human table) names the file among its error-level issues, with no dedicated
    blank-field reporter added anywhere."""
    await svc.add_dev("python")
    _place_blank_override(project, "python-dev")

    result = await invoke(["check", "--json"])
    issues = json.loads(result.output)
    errors = [i for i in issues if i["level"] == "error"]

    assert any("python-dev.toml" in i["item"] for i in errors), errors
    assert any("full_name" in i["message"] for i in errors), errors


async def test_removing_the_override_and_resyncing_restores_the_real_values(
    project, svc, invoke
) -> None:
    """The bug's own closing note: this is a validation gap, not a corruption one. Confirmed
    here rather than only asserted -- the role's real, pre-override values survive untouched."""
    dev = await svc.add_dev("python")
    real_full_name = dev.extra["full_name"]

    _place_blank_override(project, "python-dev")
    refused = await invoke(["sync"])
    assert refused.exit_code != 0

    (project.squad_dir / ".overrides" / "roles" / "python-dev.toml").unlink()
    recovered = await invoke(["sync"])
    assert recovered.exit_code == 0, recovered.output

    fm = read_frontmatter(path=project.abspath(dev.path))
    assert fm["extra"]["full_name"] == real_full_name
