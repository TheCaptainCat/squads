"""A role is named once, when it is created: ``--name`` when given, otherwise the most specific
configuration layer (the bundled catalog, ``.overrides/roles.toml``, the per-slug
``.overrides/roles/<slug>.toml``, and for a developer the pool). A later change to a layer renames
nothing.

One table crosses the creation inputs with a configuration change made afterwards, for a bundled
role and a developer role, and reads the name on every surface after ``sq sync``: ``sq role
<slug> show``, the title in the role's file, its ``.claude/`` pointer, the ``CLAUDE.md`` roster
and ``sq list --json``. ``sq check`` stays clean in every row.
"""

import json
from dataclasses import dataclass

import pytest

from _helpers import make_service
from squads import __version__
from squads._rendering._engine import invalidate_squad_dir
from squads._sections import split_frontmatter

pytestmark = pytest.mark.anyio

CATALOG_NAME = "Rita Catalog"
SLUG_NAME = "Pat Perslug"
LATER_NAME = "Lena Later"
GIVEN_NAME = "Ada Lovelace"


@dataclass(frozen=True)
class Row:
    id: str
    kind: str  # "bundled" | "developer"
    given: bool  # created with --name
    roles_toml: bool  # roles.toml names the role before creation
    per_slug: bool  # the per-slug file names the role before creation
    created_as: str | None  # None = the pool name the developer drew


ROWS = [
    Row("bundled-catalog", "bundled", False, False, False, "Robert Architect"),
    Row("bundled-roles-toml", "bundled", False, True, False, CATALOG_NAME),
    Row("bundled-per-slug", "bundled", False, False, True, SLUG_NAME),
    Row("bundled-both-files", "bundled", False, True, True, SLUG_NAME),
    Row("bundled-given", "bundled", True, True, True, GIVEN_NAME),
    Row("developer-pool", "developer", False, False, False, None),
    Row("developer-per-slug", "developer", False, False, True, SLUG_NAME),
    Row("developer-given", "developer", True, False, True, GIVEN_NAME),
]


def _write_layers(project, slug: str, *, roles_toml: str | None, per_slug: str | None) -> None:
    overrides = project.squad_dir / ".overrides"
    (overrides / "roles").mkdir(parents=True, exist_ok=True)
    stamp = f"# squads:override-base:{__version__}\n"
    if roles_toml:
        (overrides / "roles.toml").write_text(
            f'{stamp}[[roles]]\nslug = "{slug}"\nfull_name = "{roles_toml}"\n', encoding="utf-8"
        )
    if per_slug:
        (overrides / "roles" / f"{slug}.toml").write_text(
            f'{stamp}full_name = "{per_slug}"\n', encoding="utf-8"
        )
    invalidate_squad_dir(project.squad_dir)


async def _surfaces(project, invoke, slug: str) -> dict[str, str]:
    """The role's name as each surface states it."""
    shown = await invoke(["role", slug, "show", "--json"])
    assert shown.exit_code == 0, shown.output
    listed = await invoke(["list", "--type", "role", "--json"])
    assert listed.exit_code == 0, listed.output
    role_file = next(project.squad_dir.rglob(f"ROLE-*-{slug}.md"))
    claude_md = (project.root / "CLAUDE.md").read_text(encoding="utf-8")
    pointer = (project.root / ".claude" / "agents" / f"{slug}.md").read_text(encoding="utf-8")
    title = split_frontmatter(role_file.read_text(encoding="utf-8"))[0]["title"]
    return {
        "show": json.loads(shown.output)["full_name"],
        "file title": title,
        "list": next(r["title"] for r in json.loads(listed.output) if r["slug"] == slug),
        "pointer": title if title in pointer else "<name missing from the pointer>",
        "CLAUDE.md": title if f"**{title}**" in claude_md else "<name missing from CLAUDE.md>",
    }


@pytest.mark.parametrize("row", ROWS, ids=[r.id for r in ROWS])
async def test_a_role_is_named_at_creation_and_no_later_change_renames_it(
    project, invoke, row: Row
) -> None:
    slug = "architect" if row.kind == "bundled" else "python-dev"
    _write_layers(
        project,
        slug,
        roles_toml=CATALOG_NAME if row.roles_toml else None,
        per_slug=SLUG_NAME if row.per_slug else None,
    )
    svc = make_service(project)
    name = GIVEN_NAME if row.given else None
    if row.kind == "bundled":
        role = await svc.activate_role(slug, name=name)
    else:
        role = await svc.add_dev("python", name=name)
    expected = row.created_as or role.title
    assert role.title == expected

    _write_layers(
        project,
        slug,
        roles_toml=LATER_NAME if row.kind == "bundled" else None,
        per_slug=LATER_NAME,
    )
    for _ in range(2):
        synced = await invoke(["sync"])
        assert synced.exit_code == 0, synced.output
        surfaces = await _surfaces(project, invoke, slug)
        assert surfaces == dict.fromkeys(surfaces, expected)

    checked = await invoke(["check"])
    assert checked.exit_code == 0, checked.output
