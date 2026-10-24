"""An item type may not declare a field whose code is also a built-in `sq create` option, and the
reserved set matches the options the command really has."""

import pytest

import squads._cli._create as create_cli
from squads._workflow._loader import CREATE_OPTION_NAMES

pytestmark = pytest.mark.anyio


def _override(code: str) -> str:
    return f"""\
[collections.level]
label = "Level"
badges = [{{ code = "high", label = "High", emoji = "H" }}]

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "work"
fields = [{{ code = "{code}", label = "Clash", collection = "level" }}]
"""


@pytest.mark.parametrize("code", sorted(CREATE_OPTION_NAMES))
async def test_a_colliding_field_code_is_refused_naming_the_code_and_the_type(
    project, invoke, code
) -> None:
    (project.squad_dir / ".overrides").mkdir(parents=True, exist_ok=True)
    (project.squad_dir / ".overrides" / "workflow.toml").write_text(
        _override(code), encoding="utf-8"
    )

    result = await invoke(["create", "incident", "T", "--author", "manager"])

    assert result.exit_code != 0
    assert f"'{code}'" in result.output
    assert "items.incident" in result.output


async def test_the_bundled_spec_declares_no_colliding_field(project, invoke) -> None:
    assert (await invoke(["create", "bug", "T", "--author", "manager"])).exit_code == 0


async def test_the_reserved_set_is_the_create_commands_own_long_options() -> None:
    import typer.main

    command = typer.main.get_command(create_cli.create_app).commands["task"]  # type: ignore[attr-defined]
    options = {
        opt.removeprefix("--")
        for param in command.params
        for opt in (*param.opts, *param.secondary_opts)
        if opt.startswith("--")
    }
    assert options - {"priority"} | {"help"} == CREATE_OPTION_NAMES
