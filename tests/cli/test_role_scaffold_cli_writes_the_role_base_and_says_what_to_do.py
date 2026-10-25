"""`sq override scaffold --role` writes the fields of the role's base, bundled or templated, and
its closing message says to uncomment them; a role with no base is told to add fields."""

import re

import pytest

from squads._roles._models import RoleSpec
from squads._roles._resolver import resolve_role_with_base, role_base_from_item
from squads._workflow import ROSTER_ROLE

pytestmark = pytest.mark.anyio

_FIELD = re.compile(r"^# (\w+) = ", re.MULTILINE)


async def test_a_templated_developer_gets_its_template_fields_commented_out(
    project, svc, invoke
) -> None:
    await svc.add_dev("python")
    result = await invoke(["override", "scaffold", "--role", "python-dev"])
    assert result.exit_code == 0, result.output
    path = project.squad_dir / ".overrides" / "roles" / "python-dev.toml"
    text = path.read_text(encoding="utf-8")
    assert set(_FIELD.findall(text)) == set(RoleSpec.model_fields) - {"slug", "is_default"}
    assert '# capabilities = ["dev"]' in text
    # Every line uncommented still resolves to the developer's own base.
    seen: set[str] = set()
    lines = []
    for line in text.splitlines():
        key = _FIELD.match(line)
        if key and key.group(1) not in seen:
            seen.add(key.group(1))
            line = line.removeprefix("# ")
        lines.append(line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    item = await svc.roster_item(ROSTER_ROLE, "python-dev")
    base = role_base_from_item(item, project.squad_dir)
    assert resolve_role_with_base("python-dev", project.squad_dir, base=base) == base


@pytest.mark.parametrize(
    ("slug", "expected"),
    [
        ("reviewer", "uncomment the fields to override"),
        ("auditor", "add fields to override"),
    ],
)
async def test_the_closing_message_matches_what_the_file_holds(
    slug: str, expected: str, project, invoke
) -> None:
    result = await invoke(["override", "scaffold", "--role", slug])
    assert result.exit_code == 0, result.output
    assert expected in " ".join(result.output.split())
