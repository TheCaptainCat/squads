"""The roles catalog document reaching every surface that reads the catalog, driven through the
real CLI: an already-activated role (``sq role <slug> show``), the listing of what could be
activated (``sq role catalog``), and the not-yet-activated path staying unchanged. Complements
the service-level sync proof in
``tests/service/test_roles_catalog_document_reaches_an_activated_role.py``.
"""

import json

import pytest

from squads import __version__

pytestmark = pytest.mark.anyio


def _write_catalog_document(squad_dir, content: str) -> None:
    (squad_dir / ".overrides").mkdir(parents=True, exist_ok=True)
    (squad_dir / ".overrides" / "roles.toml").write_text(
        f"# squads:override-base:{__version__}\n{content}", encoding="utf-8"
    )


async def test_role_show_reaches_the_document_only_after_activation(project, invoke) -> None:
    """The exact contrast this task fixes: before activation the document already applied
    (unchanged, proven here too); after activation it previously did not."""
    _write_catalog_document(
        project.squad_dir, '[[roles]]\nslug = "reviewer"\ntitle = "Chief Reviewer"\n'
    )

    before = await invoke(["role", "reviewer", "show", "--json"])
    assert before.exit_code == 0, before.output
    assert json.loads(before.output)["title"] == "Chief Reviewer"

    activated = await invoke(["role", "activate", "reviewer"])
    assert activated.exit_code == 0, activated.output

    after = await invoke(["role", "reviewer", "show", "--json"])
    assert after.exit_code == 0, after.output
    assert json.loads(after.output)["title"] == "Chief Reviewer"  # still the document's value


async def test_role_catalog_shows_a_document_declared_slug_and_an_overridden_bundled_one(
    project, invoke
) -> None:
    from squads._roles._loader import load_role_catalog

    all_bundle = load_role_catalog().bundles["all"]
    _write_catalog_document(
        project.squad_dir,
        '[[roles]]\nslug = "reviewer"\ntitle = "Chief Reviewer"\n\n'
        "[[roles]]\n"
        'slug = "security-analyst"\n'
        'full_name = "Sylvie Sentinel"\n'
        'title = "security analyst"\n'
        'description = "Reviews changes for security implications."\n'
        'mission = "Find and flag security risks before they ship."\n\n'
        f"[bundles]\nall = {[*all_bundle, 'security-analyst']!r}\n",
    )

    r = await invoke(["role", "catalog", "--json"])
    assert r.exit_code == 0, r.output
    rows = {row["slug"]: row for row in json.loads(r.output)}

    assert rows["reviewer"]["title"] == "Chief Reviewer"
    assert rows["reviewer"]["origin"] == "bundled"
    assert "security-analyst" in rows
    assert rows["security-analyst"]["origin"] == "project"
    assert rows["security-analyst"]["full_name"] == "Sylvie Sentinel"

    plain = await invoke(["role", "catalog"])
    assert plain.exit_code == 0, plain.output
    assert "security-analyst" in plain.output
    assert "Chief Reviewer" in plain.output


async def test_role_catalog_with_no_document_is_unaffected(project, invoke) -> None:
    r = await invoke(["role", "catalog", "--json"])
    assert r.exit_code == 0, r.output
    assert all(row["origin"] == "bundled" for row in json.loads(r.output))
