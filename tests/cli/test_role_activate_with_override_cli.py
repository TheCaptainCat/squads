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


async def test_activate_a_brand_new_project_defined_slug(project, invoke):
    override_dir = project.squad_dir / ".overrides" / "roles"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "security-expert.toml").write_text(
        'full_name = "Sam Security"\ntitle = "security expert"\n'
        'description = "Keeps the system secure."\nmission = "Find and fix security issues."\n',
        encoding="utf-8",
    )
    result = await invoke(["role", "activate", "security-expert"])
    assert result.exit_code == 0
    assert "Sam Security" in result.output
