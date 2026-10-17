"""``capabilities`` is readable on every role surface a tool or a person uses: always present as
an array in the four ``--json`` payloads, and shown in the two text outputs.

One table: surface by role shape. Each cell states the value and, for ``--json``, that it is a
list.
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from squads import __version__
from squads._cli._common import console
from squads._rendering._engine import invalidate_squad_dir

pytestmark = pytest.mark.anyio

_NEW_ROLE = (
    'full_name = "{name}"\n'
    'title = "{slug}"\n'
    'description = "A declared role."\n'
    'mission = "A declared role."\n'
)

#: shape -> (slug, expected capabilities)
_SHAPES: dict[str, tuple[str, list[str]]] = {
    "bundled": ("architect", []),
    "templated-developer": ("rust-dev", ["dev"]),
    "declared-one": ("auditor", ["review-work"]),
    "declared-two": ("inspector", ["review-work", "triage"]),
    "definition-gone": ("ghost", []),
}


def _write_role_file(squad_dir: Path, slug: str, capabilities: list[str]) -> Path:
    path = squad_dir / ".overrides" / "roles" / f"{slug}.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    body = _NEW_ROLE.format(name=slug.title(), slug=slug) + f"capabilities = {capabilities!r}\n"
    path.write_text(f"# squads:override-base:{__version__}\n{body}".replace("'", '"'), "utf-8")
    return path


async def _build_roster(project, svc) -> None:
    await svc.activate_role("architect")
    await svc.add_dev("rust")
    _write_role_file(project.squad_dir, "auditor", ["review-work"])
    await svc.activate_role("auditor")
    _write_role_file(project.squad_dir, "inspector", ["review-work", "triage"])
    await svc.activate_role("inspector")
    gone = _write_role_file(project.squad_dir, "ghost", ["vanishing"])
    await svc.activate_role("ghost")
    gone.unlink()
    invalidate_squad_dir(project.squad_dir)


async def _json(invoke, args: list[str]):
    result = await invoke([*args, "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


async def _catalog_row(invoke, slug: str) -> object:
    rows = await _json(invoke, ["role", "catalog"])
    return next((r for r in rows if r["slug"] == slug), None)


async def _list_row(invoke, slug: str) -> object:
    rows = await _json(invoke, ["role", "list"])
    return next(r for r in rows if r["slug"] == slug)


async def _show(invoke, slug: str) -> object:
    return await _json(invoke, ["role", slug, "show"])


async def _playbook_row(invoke, project, slug: str) -> object:
    squad_dir = project.squad_dir
    (squad_dir / ".overrides").mkdir(exist_ok=True)
    (squad_dir / ".overrides" / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n"
        '[views.lane_card]\nsource = { kind = "playbook" }\n',
        encoding="utf-8",
    )
    invalidate_squad_dir(squad_dir)
    created = await invoke(["create", "task", "A task", "--author", "manager"])
    assert created.exit_code == 0, created.output
    item_id = created.output.split("→")[0].removeprefix("created").strip()
    payload = await _json(invoke, ["workflow", "view", "lane_card", item_id])
    return next(r for r in payload["roster"] if r["slug"] == slug)


_JSON_SURFACES: dict[str, Callable[..., Any]] = {
    "role-list": lambda invoke, project, slug: _list_row(invoke, slug),
    "role-show": lambda invoke, project, slug: _show(invoke, slug),
    "playbook-roster": _playbook_row,
}


@pytest.mark.parametrize("shape", list(_SHAPES))
@pytest.mark.parametrize("surface", list(_JSON_SURFACES))
async def test_every_json_surface_carries_capabilities_as_a_list(
    surface: str, shape: str, project, svc, invoke
) -> None:
    slug, expected = _SHAPES[shape]
    await _build_roster(project, svc)
    row = await _JSON_SURFACES[surface](invoke, project, slug)
    assert isinstance(row, dict)
    assert isinstance(row["capabilities"], list)
    assert row["capabilities"] == expected


@pytest.mark.parametrize("shape", ["bundled", "declared-one", "declared-two"])
async def test_the_catalog_json_carries_capabilities_as_a_list(
    shape: str, project, svc, invoke
) -> None:
    slug, expected = _SHAPES[shape]
    if slug != "architect":
        overrides = project.squad_dir / ".overrides"
        overrides.mkdir(exist_ok=True)
        entry = (
            f'[[roles]]\nslug = "{slug}"\n'
            + _NEW_ROLE.format(name=slug.title(), slug=slug)
            + f"capabilities = {json.dumps(expected)}\n"
        )
        bundled_all = json.loads((await invoke(["role", "catalog", "--json"])).output)
        everyone = [r["slug"] for r in bundled_all] + [slug]
        (overrides / "roles.toml").write_text(
            f"# squads:override-base:{__version__}\n[bundles]\nall = {json.dumps(everyone)}\n\n"
            + entry,
            encoding="utf-8",
        )
        invalidate_squad_dir(project.squad_dir)
    row = await _catalog_row(invoke, slug)
    assert isinstance(row, dict)
    assert isinstance(row["capabilities"], list)
    assert row["capabilities"] == expected


async def test_the_catalog_json_outside_any_squad_carries_capabilities_for_a_bundled_role(
    tmp_path, monkeypatch, invoke
) -> None:
    monkeypatch.chdir(tmp_path)
    rows = await _json(invoke, ["role", "catalog"])
    assert rows
    assert all(r["capabilities"] == [] for r in rows)


async def test_a_role_with_no_definition_left_answers_an_empty_list_in_the_show_fallback(
    project, svc, invoke
) -> None:
    """The fallback branch of the show payload (no catalog entry, no dev base, no file)."""
    await _build_roster(project, svc)
    payload = await _show(invoke, "ghost")
    assert isinstance(payload, dict)
    assert payload["title"] == ""  # the fallback branch, not the resolved one
    assert payload["capabilities"] == []


@pytest.mark.parametrize("shape", list(_SHAPES))
async def test_the_text_outputs_show_capabilities(
    shape: str, project, svc, invoke, monkeypatch
) -> None:
    slug, expected = _SHAPES[shape]
    # Wide enough that no cell of the listing wraps.
    monkeypatch.setattr(console, "width", 140)
    await _build_roster(project, svc)
    listing = await invoke(["role", "list"])
    assert listing.exit_code == 0, listing.output
    assert "Capabilities" in listing.output
    lines = listing.output.splitlines()
    header = next(line for line in lines if "Capabilities" in line)
    start, end = header.index("Capabilities"), header.index("Default")
    row = next(line for line in lines if line.split()[:1] == [slug])
    assert row[start:end].strip() == ", ".join(expected)

    card = await invoke(["role", slug, "show"])
    assert card.exit_code == 0, card.output
    if shape == "definition-gone":
        assert "capabilities:" not in card.output
    else:
        line = next(ln for ln in card.output.splitlines() if "capabilities:" in ln)
        assert line.strip("│ ").strip() == f"capabilities: {', '.join(expected) or '—'}"


async def test_the_catalog_lists_the_document_value_and_the_roster_surfaces_the_resolved_one(
    project, svc, invoke
) -> None:
    """A per-slug file's capabilities reach ``role list`` and ``role show``, not the catalog."""
    await svc.activate_role("reviewer")
    _write_role_file(project.squad_dir, "reviewer", ["rev-work"])
    # The file is a partial override of a bundled role, so only the key under test is checked.
    assert (await _catalog_row(invoke, "reviewer"))["capabilities"] == []  # type: ignore[index]
    assert (await _list_row(invoke, "reviewer"))["capabilities"] == ["rev-work"]  # type: ignore[index]
    assert (await _show(invoke, "reviewer"))["capabilities"] == ["rev-work"]  # type: ignore[index]
