"""A role or skill slug that equals a verb of its ``sq`` group cannot be addressed by slug, so
creation refuses it on every path and writes nothing."""

import json

import pytest

from _helpers import squad_tree
from squads._models._participants import ROLE_GROUP_VERBS, SKILL_GROUP_VERBS
from squads._roles._loader import load_role_catalog

pytestmark = pytest.mark.anyio

ROLE_FIELDS = (
    'full_name = "Sam {n}"\ntitle = "{n}"\ndescription = "Does {n} things."\n'
    'mission = "Do {n} well."\n'
)


def _project_role_file(project, slug: str) -> None:
    folder = project.squad_dir / ".overrides" / "roles"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{slug}.toml").write_text(ROLE_FIELDS.format(n=slug), encoding="utf-8")


def _catalog_entry(project, slug: str) -> None:
    (project.squad_dir / ".overrides").mkdir(parents=True, exist_ok=True)
    (project.squad_dir / ".overrides" / "roles.toml").write_text(
        f'[[roles]]\nslug = "{slug}"\n'
        + ROLE_FIELDS.format(n=slug)
        + f"\n[bundles]\nall = {[*load_role_catalog().bundles['all'], slug]!r}\n",
        encoding="utf-8",
    )


def _import(tmp_path, item_type: str, slug: str) -> list[str]:
    path = tmp_path / "events.jsonl"
    event = {"op": "create", "type": item_type, "title": f"Title {slug}", "slug": slug}
    path.write_text(json.dumps(event) + "\n", encoding="utf-8")
    return ["import", str(path), "--as", "manager"]


@pytest.mark.parametrize("verb", sorted(ROLE_GROUP_VERBS))
@pytest.mark.parametrize("path", ["project-role-file", "catalog-entry", "bulk-import"])
async def test_a_role_slug_equal_to_a_role_verb_is_refused_and_writes_nothing(
    project, invoke, tmp_path, verb, path
) -> None:
    if path == "bulk-import":
        argv = _import(tmp_path, "role", verb)
    elif path == "project-role-file":
        _project_role_file(project, verb)
        file = project.squad_dir / ".overrides" / "roles" / f"{verb}.toml"
        argv = ["role", "add", verb, "--file", str(file)]
    else:
        _catalog_entry(project, verb)
        argv = ["role", "activate", verb]
    before = squad_tree(project.root)

    r = await invoke(argv)

    assert r.exit_code == 1, r.output
    assert f"role slug '{verb}' is a verb of `sq role`" in r.output
    assert squad_tree(project.root) == before


@pytest.mark.parametrize("verb", sorted(SKILL_GROUP_VERBS))
@pytest.mark.parametrize("path", ["skill-add", "bulk-import"])
async def test_a_skill_slug_equal_to_a_skill_verb_is_refused_and_writes_nothing(
    project, invoke, tmp_path, verb, path
) -> None:
    argv = (
        ["skill", "add", verb.title()] if path == "skill-add" else _import(tmp_path, "skill", verb)
    )
    before = squad_tree(project.root)

    r = await invoke(argv)

    assert r.exit_code == 1, r.output
    assert f"skill slug '{verb}' is a verb of `sq skill`" in r.output
    assert squad_tree(project.root) == before


@pytest.mark.parametrize(
    ("item_type", "slug"),
    [
        pytest.param("role", "adds", id="role-near-a-verb"),
        pytest.param("role", "lister", id="role-near-another-verb"),
        pytest.param("skill", "list", id="skill-takes-the-role-verb"),
        pytest.param("skill", "adds", id="skill-near-a-verb"),
    ],
)
async def test_only_the_verbs_of_its_own_group_are_reserved(
    project, invoke, tmp_path, item_type, slug
) -> None:
    if item_type == "role":
        _project_role_file(project, slug)
        file = project.squad_dir / ".overrides" / "roles" / f"{slug}.toml"
        argv = ["role", "add", slug, "--file", str(file)]
    else:
        argv = ["skill", "add", slug]

    r = await invoke(argv)

    assert r.exit_code == 0, r.output
