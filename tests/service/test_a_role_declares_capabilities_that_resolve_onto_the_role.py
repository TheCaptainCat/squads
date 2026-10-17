"""A role declares ``capabilities`` in the catalog documents; the resolver computes them once
onto the role (``RoleDef``) and the roster view (``RoleView``), and nothing is stored on an item.

One table: where the capability list is declared, by the shape of the value declared there.
"""

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from squads import __version__
from squads._errors import SquadsError
from squads._roles._catalog import BUNDLES
from squads._roles._resolver import resolve_role_for_item
from squads._workflow import ROSTER_ROLE

pytestmark = pytest.mark.anyio

_NEW_ROLE = (
    'full_name = "Ava Auditor"\n'
    'title = "auditor"\n'
    'description = "Audits the work."\n'
    'mission = "Audit the work."\n'
)


def _overrides(squad_dir: Path) -> Path:
    path = squad_dir / ".overrides"
    (path / "roles").mkdir(parents=True, exist_ok=True)
    return path


@dataclass(frozen=True)
class _Site:
    """A place a capability list is declared: what the role's base holds, the file the
    declaration goes in, and how the file is written and the role brought onto the roster."""

    base: tuple[str, ...]
    file: str
    slug: str
    write: Callable[[Path, str], None]
    after: bool  # whether the role exists on the roster before the file is written


def _write_catalog_role(squad_dir: Path, line: str) -> None:
    everyone = [*BUNDLES["all"], "auditor"]
    body = f'[bundles]\nall = {everyone!r}\n\n[[roles]]\nslug = "auditor"\n{_NEW_ROLE}{line}'
    (_overrides(squad_dir) / "roles.toml").write_text(body, encoding="utf-8")


def _write_slug_file(slug: str, preamble: str = "") -> Callable[[Path, str], None]:
    def write(squad_dir: Path, line: str) -> None:
        (_overrides(squad_dir) / "roles" / f"{slug}.toml").write_text(
            f"# squads:override-base:{__version__}\n{preamble}{line}", encoding="utf-8"
        )

    return write


def _write_dev_table(squad_dir: Path, line: str) -> None:
    (_overrides(squad_dir) / "roles.toml").write_text(f"[dev]\n{line}", encoding="utf-8")


_SITES: dict[str, _Site] = {
    "catalog-roles-entry": _Site((), "roles.toml", "auditor", _write_catalog_role, False),
    "slug-file-new-role": _Site(
        (), "roles/auditor.toml", "auditor", _write_slug_file("auditor", _NEW_ROLE), False
    ),
    "slug-file-bundled-role": _Site(
        (), "roles/architect.toml", "architect", _write_slug_file("architect"), True
    ),
    "slug-file-templated-developer": _Site(
        ("dev",), "roles/rust-dev.toml", "rust-dev", _write_slug_file("rust-dev"), True
    ),
    "catalog-dev-table": _Site(("dev",), "roles.toml", "rust-dev", _write_dev_table, False),
}

#: shape -> (the declaration line, the resolved list given the site's base; ``None`` = refused)
_SHAPES: dict[str, tuple[str, Callable[[tuple[str, ...]], tuple[str, ...] | None]]] = {
    "absent": ("", lambda base: base),
    "empty": ("capabilities = []\n", lambda base: ()),
    "one": ('capabilities = ["audit"]\n', lambda base: ("audit",)),
    "two": ('capabilities = ["audit", "triage"]\n', lambda base: ("audit", "triage")),
    "repeated": ('capabilities = ["audit", "audit"]\n', lambda base: ("audit",)),
    "splat-append": ('capabilities = ["$(*self)", "audit"]\n', lambda base: (*base, "audit")),
    "uppercase": ('capabilities = ["Audit"]\n', lambda base: None),
    "leading-hyphen": ('capabilities = ["-audit"]\n', lambda base: None),
    "space": ('capabilities = ["au dit"]\n', lambda base: None),
    "empty-string": ('capabilities = [""]\n', lambda base: None),
    "non-string-element": ("capabilities = [1]\n", lambda base: None),
    "non-list": ('capabilities = "audit"\n', lambda base: None),
}

#: A new role has no base to splat against, so the append form is refused there.
_NO_BASE_REFUSES_SPLAT = {"catalog-roles-entry", "slug-file-new-role"}


async def _bring_onto_roster(svc, site: _Site):
    if site.slug == "rust-dev":
        return await svc.add_dev("rust")
    return await svc.activate_role(site.slug)


@pytest.mark.parametrize("shape", list(_SHAPES))
@pytest.mark.parametrize("site_name", list(_SITES))
async def test_the_declared_capabilities_resolve_onto_the_role_and_its_view(
    site_name: str, shape: str, project, svc
) -> None:
    site = _SITES[site_name]
    line, expected_for = _SHAPES[shape]
    expected = expected_for(site.base)
    if shape == "splat-append" and site_name in _NO_BASE_REFUSES_SPLAT:
        expected = None

    item = None
    if site.after:
        item = await _bring_onto_roster(svc, site)

    site.write(project.squad_dir, line)

    if expected is None:
        with pytest.raises(SquadsError) as excinfo:
            if item is None:
                item = await _bring_onto_roster(svc, site)
            resolve_role_for_item(item, project.squad_dir)
        assert site.file in str(excinfo.value).replace("\\", "/")
        return

    if item is None:
        item = await _bring_onto_roster(svc, site)
    role = resolve_role_for_item(item, project.squad_dir)
    assert role.capabilities == expected
    view = svc._role_view(item)
    assert view.capabilities == expected
    assert view.capabilities == resolve_role_for_item(item, project.squad_dir).capabilities


async def test_every_live_role_view_carries_what_the_resolver_computes(project, svc) -> None:
    await svc.activate_role("architect")
    await svc.add_dev("rust")
    for item in await svc.list_items(item_type=ROSTER_ROLE):
        assert (
            svc._role_view(item).capabilities
            == resolve_role_for_item(item, project.squad_dir).capabilities
        )


def _snapshot(project) -> dict[str, str]:
    """A hash of every item file and the index, which is everything the squad stores."""
    out = {}
    for path in sorted(project.squad_dir.rglob("*.md")):
        if ".overrides" in path.parts:
            continue
        out[str(path.relative_to(project.squad_dir))] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
    index = json.loads((project.squad_dir / ".squads.json").read_text(encoding="utf-8"))
    out[".squads.json"] = json.dumps(index, sort_keys=True)
    return out


async def test_declaring_a_capability_stores_nothing_on_any_item_or_in_the_index(
    project, svc, invoke
) -> None:
    await svc.add_dev("rust")
    await svc.activate_role("architect")
    first = await invoke(["sync"])
    assert first.exit_code == 0, first.output
    before = _snapshot(project)

    (project.squad_dir / ".overrides").mkdir(exist_ok=True)
    (project.squad_dir / ".overrides" / "roles.toml").write_text(
        '[dev]\ncapabilities = ["dev", "extra"]\n', encoding="utf-8"
    )
    (project.squad_dir / ".overrides" / "roles").mkdir(exist_ok=True)
    (project.squad_dir / ".overrides" / "roles" / "architect.toml").write_text(
        'capabilities = ["design"]\n', encoding="utf-8"
    )
    synced = await invoke(["sync"])
    assert synced.exit_code == 0, synced.output
    assert _snapshot(project) == before

    (project.squad_dir / ".squads.json").unlink()
    repaired = await invoke(["repair"])
    assert repaired.exit_code == 0, repaired.output
    assert _snapshot(project) == before


@pytest.mark.parametrize(("command", "expected_exit"), [(["check"], 3), (["sync"], 1)])
async def test_a_malformed_capability_name_is_refused_and_names_the_file(
    command: list[str], expected_exit: int, project, svc, invoke
) -> None:
    await svc.activate_role("architect")
    (project.squad_dir / ".overrides" / "roles").mkdir(parents=True, exist_ok=True)
    (project.squad_dir / ".overrides" / "roles" / "architect.toml").write_text(
        f'# squads:override-base:{__version__}\ncapabilities = ["Not Valid"]\n', encoding="utf-8"
    )
    result = await invoke(command)
    assert result.exit_code == expected_exit, result.output
    assert "architect.toml" in result.output.replace("\n", "")


#: [dev] capabilities declared after the developer exists -> what the developer resolves to.
_DEV_TABLE_CHANGES = {
    "emptied": ("[]", ()),
    "replaced": ('["builder"]', ("builder",)),
    "repeated": ('["builder", "builder"]', ("builder",)),
    "appended": ('["$(*self)", "builder"]', ("dev", "builder")),
}


@pytest.mark.parametrize("change", list(_DEV_TABLE_CHANGES))
async def test_an_existing_developer_follows_a_later_change_to_the_dev_table_capabilities(
    change: str, project, svc, invoke
) -> None:
    value, expected = _DEV_TABLE_CHANGES[change]
    item = await svc.add_dev("rust")
    assert resolve_role_for_item(item, project.squad_dir).capabilities == ("dev",)
    _write_dev_table(project.squad_dir, f"capabilities = {value}\n")

    assert resolve_role_for_item(item, project.squad_dir).capabilities == expected
    assert svc._role_view(item).capabilities == expected
    shown = await invoke(["role", "rust-dev", "show", "--json"])
    assert shown.exit_code == 0, shown.output
    assert json.loads(shown.output)["capabilities"] == list(expected)


async def test_a_catalog_entry_error_names_the_entry_by_slug_not_by_a_merged_index(
    project, svc
) -> None:
    (_overrides(project.squad_dir) / "roles.toml").write_text(
        '[[roles]]\nslug = "reviewer"\ncapabilities = "dev"\n', encoding="utf-8"
    )
    with pytest.raises(SquadsError) as excinfo:
        await svc.activate_role("reviewer")
    message = str(excinfo.value)
    assert "roles.toml" in message
    assert "slug 'reviewer'" in message
    assert "roles[" not in message


async def test_the_two_malformed_name_messages_read_alike(project, svc) -> None:
    architect = await svc.activate_role("architect")
    _write_dev_table(project.squad_dir, 'capabilities = ["Bad"]\n')
    with pytest.raises(SquadsError) as catalog_error:
        await svc.add_dev("rust")
    (project.squad_dir / ".overrides" / "roles.toml").unlink()
    _write_slug_file("architect")(project.squad_dir, 'capabilities = ["Bad"]\n')
    with pytest.raises(SquadsError) as file_error:
        resolve_role_for_item(architect, project.squad_dir)
    assert "capabilities entry 'Bad' must match" in str(catalog_error.value)
    assert "capabilities entry 'Bad' must match" in str(file_error.value)
