"""``sq role activate`` CLI surface: a TOML override's ``full_name`` reaches the printed output
for both a bundled slug and a brand-new project-defined slug — the same override-pickup
mechanism proven at the service layer (tests/service/test_role_and_dev_override_pickup_at_
instantiation.py), reached through the actual command wiring.
"""

import pytest

pytestmark = pytest.mark.anyio


async def test_activate_a_bundled_slug_reports_the_toml_override_name(project, invoke):
    override_dir = project.squad_dir / ".overrides" / "roles"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "reviewer.toml").write_text('full_name = "Helen Reviewer"\n', encoding="utf-8")
    result = await invoke(["role", "activate", "reviewer"])
    assert result.exit_code == 0
    assert "Helen Reviewer" in result.output


async def test_activate_refuses_a_slug_only_a_role_file_declares_and_add_creates_it(
    project, invoke
):
    override_dir = project.squad_dir / ".overrides" / "roles"
    override_dir.mkdir(parents=True, exist_ok=True)
    file = override_dir / "security-expert.toml"
    file.write_text(
        'full_name = "Sam Security"\ntitle = "security expert"\n'
        'description = "Keeps the system secure."\nmission = "Find and fix security issues."\n',
        encoding="utf-8",
    )
    refused = await invoke(["role", "activate", "security-expert"])
    assert refused.exit_code == 1
    assert "sq role add security-expert --file" in " ".join(refused.output.split())

    added = await invoke(["role", "add", "security-expert", "--file", str(file)])
    assert added.exit_code == 0, added.output
    assert "Sam Security" in added.output
