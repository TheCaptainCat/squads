"""A role's name resolves through the bundled catalog, ``.overrides/roles.toml`` and the per-slug
``.overrides/roles/<slug>.toml``, lowest to highest, unless it was chosen explicitly
(``name_chosen``), in which case no layer changes it.

One table crosses ``name_chosen`` with the layer that sets ``full_name``, for a bundled role and
a developer role, and reads the name on every surface after one ``sq sync`` and again after a
second that writes nothing: ``sq role <slug> show``, the title in the role's file, its
``.claude/`` pointer, the ``CLAUDE.md`` roster and ``sq list --json``. ``sq check`` stays clean in
every row.
"""

import json
from dataclasses import dataclass, replace
from datetime import timedelta

import pytest

from _helpers import squad_tree
from squads import __version__
from squads._context import bind_context, get_context
from squads._rendering._engine import invalidate_squad_dir
from squads._sections import split_frontmatter
from squads._services._service import Service

pytestmark = pytest.mark.anyio

CATALOG_NAME = "Rita Catalog"
SLUG_NAME = "Pat Perslug"
CHOSEN_BUNDLED = "Ada Lovelace"
CHOSEN_DEV = "Hank Python"


@dataclass(frozen=True)
class Row:
    id: str
    kind: str  # "bundled" | "developer"
    chosen: bool
    roles_toml: bool
    per_slug: bool
    expected: str | None  # None = the name the role was created with


ROWS = [
    Row("bundled-never-named-catalog-only", "bundled", False, False, False, "Robert Architect"),
    Row("bundled-never-named-roles-toml", "bundled", False, True, False, CATALOG_NAME),
    Row("bundled-never-named-per-slug", "bundled", False, False, True, SLUG_NAME),
    Row("bundled-never-named-both-files", "bundled", False, True, True, SLUG_NAME),
    Row("bundled-chosen-catalog-only", "bundled", True, False, False, CHOSEN_BUNDLED),
    Row("bundled-chosen-roles-toml", "bundled", True, True, False, CHOSEN_BUNDLED),
    Row("bundled-chosen-per-slug", "bundled", True, False, True, CHOSEN_BUNDLED),
    Row("bundled-chosen-both-files", "bundled", True, True, True, CHOSEN_BUNDLED),
    Row("developer-never-named-no-file", "developer", False, False, False, None),
    Row("developer-never-named-per-slug", "developer", False, False, True, SLUG_NAME),
    Row("developer-chosen-no-file", "developer", True, False, False, CHOSEN_DEV),
    Row("developer-chosen-per-slug", "developer", True, False, True, CHOSEN_DEV),
]


def _write_layers(project, row: Row, slug: str) -> None:
    overrides = project.squad_dir / ".overrides"
    (overrides / "roles").mkdir(parents=True, exist_ok=True)
    stamp = f"# squads:override-base:{__version__}\n"
    if row.roles_toml:
        (overrides / "roles.toml").write_text(
            f'{stamp}[[roles]]\nslug = "{slug}"\nfull_name = "{CATALOG_NAME}"\n', encoding="utf-8"
        )
    if row.per_slug:
        (overrides / "roles" / f"{slug}.toml").write_text(
            f'{stamp}full_name = "{SLUG_NAME}"\n', encoding="utf-8"
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
async def test_a_role_takes_the_most_specific_layer_unless_its_name_was_chosen(
    project, invoke, row: Row
) -> None:
    svc = Service(project)
    if row.kind == "bundled":
        slug = "architect"
        role = await svc.activate_role(slug, name=CHOSEN_BUNDLED if row.chosen else None)
    else:
        slug = "python-dev"
        role = await svc.add_dev("python", name=CHOSEN_DEV if row.chosen else None)
    created_with = role.title
    expected = row.expected or created_with
    _write_layers(project, row, slug)

    first = await invoke(["sync"])
    assert first.exit_code == 0, first.output
    after_first = squad_tree(project.root)
    surfaces_first = await _surfaces(project, invoke, slug)

    second = await invoke(["sync"])
    assert second.exit_code == 0, second.output
    assert squad_tree(project.root) == after_first
    assert await _surfaces(project, invoke, slug) == surfaces_first

    assert surfaces_first == dict.fromkeys(surfaces_first, expected)
    checked = await invoke(["check"])
    assert checked.exit_code == 0, checked.output


async def test_a_rename_moves_updated_at_and_is_recorded_in_the_reflog(
    project, invoke, frozen_time
) -> None:
    svc = Service(project)
    role = await svc.activate_role("architect")
    _write_layers(project, Row("x", "bundled", False, True, False, CATALOG_NAME), "architect")
    later = frozen_time + timedelta(hours=1)
    bind_context(replace(get_context(), clock_override=later))

    await invoke(["sync"])

    renamed = await Service(project).get(role.id)
    assert renamed.title == CATALOG_NAME
    assert renamed.updated_at == later != role.updated_at
    reflog = (project.squad_dir / ".reflog.jsonl").read_text(encoding="utf-8")
    assert any(
        json.loads(line)["op"] == "update" and json.loads(line)["target"] == role.id
        for line in reflog.splitlines()
    )
