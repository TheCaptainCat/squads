"""A role definition renders a Responsibilities section only when the role has responsibilities,
so an empty list leaves no heading and no placeholder, on every role kind."""

import pytest

from squads import __version__
from squads._services import _service as service

pytestmark = pytest.mark.anyio

_HEAD = f"# squads:override-base:{__version__}\n"
_DEFINED = (
    'full_name = "Sentinel"\ntitle = "Security analyst"\ndescription = "Reviews threats."\n'
    'mission = "Keep it safe."\n'
)


@pytest.fixture
async def squad(tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    return (await service.init(root=tmp_path, roles_spec="all")).paths


def _override(squad, name: str, text: str) -> None:
    path = squad.squad_dir / ".overrides" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_HEAD + text, encoding="utf-8")


async def _show(invoke, slug: str) -> str:
    result = await invoke(["role", slug, "show"])
    assert result.exit_code == 0, result.output
    return result.output


def _assert_definition(out: str, *, responsibilities: bool) -> None:
    assert ("## Responsibilities" in out) is responsibilities
    assert "## Mission" in out
    assert "## Working agreements" in out
    assert "_TODO" not in out
    assert "\n- \n" not in out


async def test_a_catalog_role_with_bundled_responsibilities_shows_the_section(
    squad, invoke
) -> None:
    out = await _show(invoke, "tech-lead")
    _assert_definition(out, responsibilities=True)
    assert "## Responsibilities\n\n- " in out


async def test_a_catalog_role_whose_override_empties_the_list_shows_no_section(
    squad, invoke
) -> None:
    _override(squad, "roles.toml", '[[roles]]\nslug = "tech-lead"\nresponsibilities = []\n')
    _assert_definition(await _show(invoke, "tech-lead"), responsibilities=False)


async def test_a_template_role_shows_the_section_then_none_once_its_list_is_emptied(
    squad, invoke
) -> None:
    assert (await invoke(["dev", "add", "--tech", "rust"])).exit_code == 0
    _assert_definition(await _show(invoke, "rust-dev"), responsibilities=True)

    _override(squad, "roles.toml", "[templates.dev]\nresponsibilities = []\n")
    _assert_definition(await _show(invoke, "rust-dev"), responsibilities=False)


async def test_an_item_defined_role_from_flags_has_no_responsibilities_section(
    squad, invoke
) -> None:
    result = await invoke(
        [
            *("role", "add", "sec", "--name", "Sentinel", "--job-title", "Analyst"),
            *("--desc", "Reviews.", "--mission", "Keep it safe."),
        ]
    )
    assert result.exit_code == 0, result.output
    _assert_definition(await _show(invoke, "sec"), responsibilities=False)


async def test_an_item_defined_role_follows_its_file_lists_through_update(
    squad, invoke, tmp_path
) -> None:
    file = tmp_path / "def.toml"
    file.write_text(_DEFINED + 'responsibilities = ["Audit"]\n', encoding="utf-8")
    assert (await invoke(["role", "add", "sec", "--file", str(file)])).exit_code == 0
    out = await _show(invoke, "sec")
    _assert_definition(out, responsibilities=True)
    assert "- Audit" in out

    delta = tmp_path / "delta.toml"
    delta.write_text('responsibilities = ["$(*self)", "Triage"]\n', encoding="utf-8")
    assert (await invoke(["role", "sec", "update", "--file", str(delta)])).exit_code == 0
    out = await _show(invoke, "sec")
    assert "- Audit\n- Triage" in out

    delta.write_text("responsibilities = []\n", encoding="utf-8")
    assert (await invoke(["role", "sec", "update", "--file", str(delta)])).exit_code == 0
    _assert_definition(await _show(invoke, "sec"), responsibilities=False)


async def test_an_agreements_list_empty_or_not_adds_no_empty_bullet(squad, invoke) -> None:
    out = await _show(invoke, "tech-lead")
    assert "\n- \n" not in out
    assert "Operate as" in out


@pytest.mark.parametrize(
    "command", [["role", "add", "--help"], ["role", "tech-lead", "update", "--help"]]
)
async def test_the_file_help_names_the_list_keys(squad, command, invoke) -> None:
    result = await invoke(command)
    assert result.exit_code == 0, result.output
    flat = " ".join(result.output.split())
    assert "responsibilities" in flat
    assert "agreements" in flat
