"""A playbook line whose `@*` is not followed by a well-formed capability name is a load error
naming the override file, the same refusal a malformed `*<name>` guide subject gets."""

import pytest

from squads import __version__
from squads._errors import SquadsError
from squads._interactions._loader import load_playbook
from squads._workflow import bundled_spec


@pytest.mark.parametrize("token", ["@*", "@*Audit", "@*-audit", "@*audit_work"])
async def test_a_malformed_token_is_refused_naming_the_file(token: str, project) -> None:
    override = project.squad_dir / ".overrides" / "playbook.toml"
    override.parent.mkdir(parents=True, exist_ok=True)
    override.write_text(
        f"# squads:override-base:{__version__}\n"
        '[types.task]\nroles = [\n    "$(*self)",\n'
        f'    {{ slug = "manager", do = ["ask `{token}` to look"] }},\n]\n',
        encoding="utf-8",
    )
    with pytest.raises(SquadsError) as excinfo:
        load_playbook(squad_dir=project.squad_dir, spec=bundled_spec())
    assert "playbook.toml" in str(excinfo.value).replace("\\", "/")
    assert "capability token" in str(excinfo.value)
    assert token in str(excinfo.value)
