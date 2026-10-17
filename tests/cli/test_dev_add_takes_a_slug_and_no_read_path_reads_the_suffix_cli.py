"""``sq dev add --slug`` stores a developer under the slug it is given; a slug that no source
declares resolves to nothing on every read path, however it is spelled.

Two tables: slug by ``dev add`` outcome, and slug by read path.
"""

import json

import pytest

from squads import __version__

pytestmark = pytest.mark.anyio


def _stamped(body: str) -> str:
    return f"# squads:override-base:{__version__}\n{body}"


@pytest.mark.parametrize(
    ("args", "slug"),
    [
        ([], "rust-dev"),
        (["--slug", "builder"], "builder"),
        (["--slug", "rust-builder"], "rust-builder"),
    ],
    ids=["default-slug", "free-slug", "free-slug-with-the-tech-in-it"],
)
async def test_dev_add_stores_the_developer_under_the_slug_it_was_given(
    args, slug, project, svc, invoke
) -> None:
    added = await invoke(["dev", "add", "--tech", "rust", *args])
    assert added.exit_code == 0, added.output

    item = await svc.roster_item("role", slug)
    assert item is not None and item.attribute("tech") == "rust"
    shown = await invoke(["role", slug, "show", "--json"])
    assert json.loads(shown.output)["capabilities"] == ["dev"]
    listed = await invoke(["dev", "list"])
    assert slug in listed.output.split()
    assert (await invoke(["sync"])).exit_code == 0
    assert (project.root / ".claude" / "agents" / f"{slug}.md").is_file()


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["--slug", "op-rusty"], "reserved for operators"),
        (["--slug", "Bad Slug"], "slug"),
        (["--slug", "manager"], "belongs to a role the catalog declares"),
        (["--slug", "reviewer"], "belongs to a role the catalog declares"),
        (["--slug", "operator"], "slug"),
        (["--slug", "squads"], "slug"),
    ],
    ids=[
        "operator-prefix",
        "outside-the-grammar",
        "taken-by-a-live-role",
        "bundled-role-not-on-the-roster",
        "reserved-operator",
        "reserved-squads",
    ],
)
async def test_dev_add_refuses_a_slug_a_role_cannot_have_and_writes_nothing(
    args, message, project, svc, invoke
) -> None:
    before = {i.slug for i in await svc.list_items(item_type="role")}
    refused = await invoke(["dev", "add", "--tech", "rust", *args])
    assert refused.exit_code == 1, refused.output
    assert message in refused.output
    assert {i.slug for i in await svc.list_items(item_type="role")} == before


async def test_a_per_slug_role_file_follows_the_slug_the_developer_was_stored_under(
    project, svc, invoke
) -> None:
    roles = project.squad_dir / ".overrides" / "roles"
    roles.mkdir(parents=True)
    (roles / "builder.toml").write_text(_stamped('color = "red"\n'), encoding="utf-8")
    assert (await invoke(["dev", "add", "--tech", "rust", "--slug", "builder"])).exit_code == 0
    assert (await invoke(["sync"])).exit_code == 0
    pointer = (project.root / ".claude" / "agents" / "builder.md").read_text(encoding="utf-8")
    assert "color: red" in pointer


@pytest.mark.parametrize("slug", ["rust-dev", "data-dev", "dev", "nobody"])
@pytest.mark.parametrize("surface", ["show", "show-json"])
async def test_a_slug_nothing_declares_resolves_to_nothing_however_it_is_spelled(
    slug: str, surface: str, project, invoke
) -> None:
    argv = ["role", slug, "show", *(["--json"] if surface == "show-json" else [])]
    result = await invoke(argv)
    assert result.exit_code == 1, result.output
    assert "no role" in result.output
    assert "Traceback" not in result.output


@pytest.mark.parametrize("slug", ["rust-dev", "data-dev"])
async def test_a_role_file_for_an_unadded_dev_slug_is_a_new_role_and_needs_its_fields(
    slug: str, project, invoke
) -> None:
    roles = project.squad_dir / ".overrides" / "roles"
    roles.mkdir(parents=True)
    (roles / f"{slug}.toml").write_text(_stamped('title = "Wrangler"\n'), encoding="utf-8")

    checked = await invoke(["check"])
    shown = await invoke(["role", slug, "show"])

    assert checked.exit_code != 0, checked.output
    assert "missing required fields" in " ".join(checked.output.split())
    assert shown.exit_code == 1, shown.output
    assert "missing required fields" in shown.output


async def test_dev_add_refuses_a_slug_the_project_catalog_declares(project, svc, invoke) -> None:
    from squads._roles._catalog import BUNDLES

    overrides = project.squad_dir / ".overrides"
    overrides.mkdir(exist_ok=True)
    (overrides / "roles.toml").write_text(
        _stamped(
            f'[bundles]\nall = {[*BUNDLES["all"], "lead"]!r}\n\n[[roles]]\nslug = "lead"\n'
            'full_name = "Lee Lead"\ntitle = "lead"\ndescription = "Leads."\nmission = "Lead."\n'
        ).replace("'", '"'),
        encoding="utf-8",
    )
    refused = await invoke(["dev", "add", "--tech", "go", "--slug", "lead"])
    assert refused.exit_code == 1, refused.output
    assert "belongs to a role the catalog declares" in refused.output
    assert await svc.roster_item("role", "lead") is None


async def test_a_collision_with_an_existing_entry_names_it_a_role(project, svc, invoke) -> None:
    assert (await invoke(["dev", "add", "--tech", "rust"])).exit_code == 0
    refused = await invoke(["dev", "add", "--tech", "go", "--slug", "rust-dev"])
    assert refused.exit_code == 1, refused.output
    assert "a role with slug 'rust-dev' already exists" in refused.output
