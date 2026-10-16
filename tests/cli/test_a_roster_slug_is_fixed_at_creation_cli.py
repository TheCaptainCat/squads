"""A roster entry's slug is fixed when it is created and nothing writes a different one: role
creation refuses the slugs reserved for other kinds of author, and every other path that touches an
existing role, developer role, skill or operator leaves its slug, stored slug, file name and index
entry as they were."""

import hashlib
import json
import re
from pathlib import Path

import pytest
import typer.main

from squads._cli import app
from squads._models._participants import reserved_role_slug_reason
from squads._roles._loader import load_role_catalog

pytestmark = pytest.mark.anyio

ROLE_FIELDS = (
    'full_name = "Sam {n}"\ntitle = "{n}"\ndescription = "Does {n} things."\n'
    'mission = "Do {n} well."\n'
)


def _tree(root: Path) -> dict[str, str]:
    """Every file under the project root, keyed by relative path, valued by content hash."""
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and ".git" not in p.parts
    }


def _identities(project) -> dict[str, tuple[str, str | None, str]]:
    """Per roster item: its core slug, its stored slug and its file name, read from the files."""
    out: dict[str, tuple[str, str | None, str]] = {}
    for path in sorted(project.squad_dir.rglob("*.md")):
        if not re.match(r"(ROLE|SKILL|OP)-\d+-", path.name):
            continue
        text = path.read_text(encoding="utf-8")
        front = text.split("---\n")[1]
        slug = re.search(r"^slug: (.+)$", front, re.M)
        stored = re.search(r"^  slug: (.+)$", front, re.M)
        out[path.name.split("-")[0] + "-" + path.name.split("-")[1]] = (
            slug.group(1) if slug else "",
            stored.group(1) if stored else None,
            path.name,
        )
    return out


@pytest.fixture
async def roster(project, invoke):
    """One of each roster kind beside the minimal squad's role: a developer role, a skill and an
    operator."""
    for argv in (
        ["dev", "add", "--tech", "python"],
        ["skill", "add", "Pairing"],
        ["operator", "add", "Pierre Chat"],
    ):
        r = await invoke(argv)
        assert r.exit_code == 0, r.output
    return _identities(project)


# --------------------------------------------------------------------------- creation

RESERVED = [
    pytest.param("operator", "reserved for the anonymous author", id="operator"),
    pytest.param("squads", "reserved for system entries", id="squads"),
    pytest.param("op-anna", "reserved for operators", id="op-prefix"),
    pytest.param("Squads", "cannot create this role as 'Squads'", id="reserved-in-other-case"),
    pytest.param("OP-anna", "cannot create this role as 'OP-anna'", id="op-prefix-in-other-case"),
    pytest.param("has space", "cannot create this role as 'has space'", id="outside-the-grammar"),
]


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


@pytest.mark.parametrize(("slug", "reason"), RESERVED)
@pytest.mark.parametrize("source", ["project-role-file", "catalog-entry", "bulk-import"])
async def test_role_creation_refuses_a_reserved_slug_and_writes_nothing(
    project, invoke, tmp_path_factory, source, slug, reason
) -> None:
    before = _tree(project.root)
    if source == "bulk-import":
        events = tmp_path_factory.mktemp("events") / "events.jsonl"
        events.write_text(
            json.dumps({"op": "create", "type": "role", "title": "Imposter", "slug": slug}) + "\n",
            encoding="utf-8",
        )
        argv = ["import", str(events), "--as", slug]
    else:
        (_project_role_file if source == "project-role-file" else _catalog_entry)(project, slug)
        before = _tree(project.root)
        argv = ["role", "activate", slug]

    r = await invoke(argv)

    assert r.exit_code == 1, r.output
    assert reason in r.output
    assert _tree(project.root) == before


async def test_operator_creation_refuses_a_slug_outside_the_grammar(project, invoke) -> None:
    before = _tree(project.root)

    r = await invoke(["operator", "add", "Bad Slug", "--slug", "Bad Slug"])

    assert r.exit_code == 1, r.output
    assert "operator slug 'Bad Slug' must start with 'op-'" in r.output
    assert _tree(project.root) == before


def test_the_reserved_check_ignores_case() -> None:
    assert reserved_role_slug_reason("SQUADS") is not None
    assert reserved_role_slug_reason("Operator") is not None
    assert reserved_role_slug_reason("OP-x") is not None
    assert reserved_role_slug_reason("squad") is None


async def test_a_developer_role_whose_slug_starts_with_the_operator_prefix_is_refused(
    project, invoke
) -> None:
    before = _tree(project.root)

    r = await invoke(["dev", "add", "--tech", "op"])

    assert r.exit_code == 1, r.output
    assert "reserved for operators" in r.output and "a role needs another slug" in r.output
    assert _tree(project.root) == before


async def test_an_ordinary_project_role_and_an_operator_slug_are_still_created(
    project, invoke
) -> None:
    _project_role_file(project, "security-expert")

    role = await invoke(["role", "activate", "security-expert"])
    operator = await invoke(["operator", "add", "Anna Lee", "--slug", "op-anna"])

    assert role.exit_code == 0, role.output
    assert operator.exit_code == 0, operator.output


# --------------------------------------------------------------------------- permanence

ROSTER_ADDR = {
    "role": "ROLE-1",
    "developer-role": "ROLE-2",
    "skill": "SKILL-3",
    "operator": "OP-4",
}


def _update_event(target: str, **fields) -> str:
    return json.dumps({"op": "update", "target": target, "as": "manager", **fields}) + "\n"


@pytest.mark.parametrize("kind", ROSTER_ADDR)
async def test_a_display_update_changes_the_title_and_never_the_identity(
    project, invoke, roster, tmp_path, kind
) -> None:
    before = _identities(project)
    events = tmp_path / "u.jsonl"
    # A role's definition lives in its role document, so only its name changes here.
    fields = {} if kind.endswith("role") else {"description": "New words."}
    events.write_text(
        _update_event(ROSTER_ADDR[kind], title="A Completely New Title", **fields),
        encoding="utf-8",
    )

    r = await invoke(["import", str(events)])

    assert r.exit_code == 0, r.output
    assert _identities(project) == before
    path = next(project.squad_dir.rglob(f"{ROSTER_ADDR[kind].replace('-', '-00000')}-*.md"))
    assert "title: A Completely New Title" in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("kind", ROSTER_ADDR)
@pytest.mark.parametrize("how", ["set", "unset", "unset-unknown-key", "unset-other-case"])
async def test_an_import_cannot_set_or_clear_a_stored_slug_through_the_extra_fields(
    project, invoke, roster, tmp_path, kind, how
) -> None:
    before = _identities(project)
    events = tmp_path / "u.jsonl"
    change = {
        "set": {"fields": {"slug": "hijacked"}},
        "unset": {"unset_fields": ["slug"]},
        "unset-unknown-key": {"unset_fields": ["no_such_field"]},
        "unset-other-case": {"unset_fields": ["SLUG"]},
    }[how]
    events.write_text(_update_event(ROSTER_ADDR[kind], **change), encoding="utf-8")

    r = await invoke(["import", str(events)])

    assert r.exit_code == 1, r.output
    named = how in ("set", "unset")  # a key the role document supplies is gated by name
    refusal = "authoring surface" if kind.endswith("role") and named else "is not a settable field"
    assert refusal in r.output
    assert _identities(project) == before, r.output


# --------------------------------------------------------------------------- overrides


async def test_an_override_document_whose_slug_differs_from_its_file_name_is_refused(
    project, invoke
) -> None:
    folder = project.squad_dir / ".overrides" / "roles"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "reviewer.toml").write_text('slug = "other"\n', encoding="utf-8")
    before = _tree(project.root)

    r = await invoke(["role", "activate", "reviewer"])

    assert r.exit_code == 1, r.output
    assert "reviewer.toml" in r.output and "'other'" in r.output
    assert _tree(project.root) == before


async def test_a_catalog_override_that_stops_declaring_a_role_leaves_its_item_alone(
    project, invoke
) -> None:
    _catalog_entry(project, "security-expert")
    assert (await invoke(["role", "activate", "security-expert"])).exit_code == 0
    before = _identities(project)

    (project.squad_dir / ".overrides" / "roles.toml").unlink()
    _project_role_file(project, "security-expert")
    sync = await invoke(["sync"])

    assert sync.exit_code == 0, sync.output
    after = _identities(project)
    assert {key: after[key] for key in before} == before


# --------------------------------------------------------------------------- retype / rename


@pytest.mark.parametrize("roster_type", ["role", "skill", "operator"])
async def test_the_bulk_renames_refuse_every_roster_type_both_ways(
    project, invoke, roster, roster_type
) -> None:
    before = _tree(project.root)
    for argv in (
        ["migrate", "rename-type", roster_type, "task"],
        ["migrate", "rename-type", "task", roster_type],
        ["migrate", "rename-status", roster_type, "Active", "Gone"],
    ):
        r = await invoke(argv)
        assert r.exit_code == 1, (argv, r.output)
        assert "reserved roster type" in r.output
    assert _tree(project.root) == before


@pytest.mark.parametrize("roster_id", ["ROLE-1", "ROLE-2", "SKILL-3", "OP-4"])
async def test_retype_refuses_a_roster_item_and_a_roster_target(
    project, svc, roster, roster_id
) -> None:
    from _helpers import create_item
    from squads._errors import SquadsError

    task = (await create_item(svc, "task", "A task")).item
    before = _tree(project.root)

    with pytest.raises(SquadsError):
        await svc.retype(roster_id, "task")
    with pytest.raises(SquadsError):
        await svc.retype(
            task.id, {"ROLE": "role", "SKILL": "skill", "OP": "operator"}[roster_id.split("-")[0]]
        )

    assert _tree(project.root) == before


# --------------------------------------------------------------------------- repair / sync

ROSTER_FILE = {"role": "ROLE-1", "developer-role": "ROLE-2", "skill": "SKILL-3", "operator": "OP-4"}


def _roster_file(project, prefix: str) -> Path:
    kind, number = prefix.split("-")
    return next(project.squad_dir.rglob(f"{kind}-{int(number):06d}-*.md"))


@pytest.mark.parametrize("kind", ROSTER_FILE)
@pytest.mark.parametrize("damage", ["title-differs-from-slug", "file-renamed-by-hand"])
@pytest.mark.parametrize("index", ["kept", "deleted"])
async def test_repair_and_sync_never_derive_or_write_a_slug(
    project, invoke, roster, kind, damage, index
) -> None:
    before_index = _index_slugs(project)
    path = _roster_file(project, ROSTER_FILE[kind])
    if damage == "title-differs-from-slug":
        text = path.read_text(encoding="utf-8")
        retitled = re.sub(r"^title: .*$", "title: Something Else Entirely", text, flags=re.M)
        path.write_text(retitled, encoding="utf-8")
    else:
        renamed = re.sub(r"^([A-Z]+-\d+)-.*$", r"\1-renamed-by-hand.md", path.name)
        path = path.rename(path.with_name(renamed))
    if index == "deleted":
        (project.squad_dir / ".squads.json").unlink()
    slugs_before = re.findall(r"^\s*slug: .*$", _frontmatter(path), flags=re.M)

    await invoke(["repair"])
    await invoke(["sync"])

    assert re.findall(r"^\s*slug: .*$", _frontmatter(path), flags=re.M) == slugs_before
    after_index = _index_slugs(project)
    assert {k: after_index[k][1] for k in before_index} == {
        k: v[1] for k, v in before_index.items()
    }
    if damage == "title-differs-from-slug":
        assert {k: after_index[k] for k in before_index} == before_index


def _frontmatter(path: Path) -> str:
    return path.read_text(encoding="utf-8").split("---\n")[1]


def _index_slugs(project) -> dict[str, tuple[str, str | None]]:
    """Per roster item in the index: its core slug and its stored slug."""
    items = json.loads((project.squad_dir / ".squads.json").read_text(encoding="utf-8"))["items"]
    return {
        key: (item["slug"], item["slug"] if item["slug_in_file"] else None)
        for key, item in items.items()
        if item["type"] in ("role", "skill", "operator")
    }


# --------------------------------------------------------------------------- no slug option

#: The only roster verbs that may declare a ``--slug`` option: the ones that create an entity.
SLUG_OPTION_ALLOWLIST = frozenset({("operator", "add"), ("dev", "add")})
ROSTER_GROUPS = ("role", "dev", "skill", "operator")


def _walk(command, path: tuple[str, ...]):
    """Every command under ``command`` with its path; duck-typed over Typer's Click commands."""
    yield path, command
    for name, child in getattr(command, "commands", {}).items():
        yield from _walk(child, (*path, name))


def test_no_roster_verb_but_a_creation_verb_declares_a_slug_option() -> None:
    root = typer.main.get_command(app)
    offenders: set[tuple[str, ...]] = set()
    for group in ROSTER_GROUPS:
        for path, command in _walk(root.commands[group], (group,)):  # type: ignore[attr-defined]
            if any("--slug" in getattr(p, "opts", ()) for p in command.params):
                offenders.add(path)

    assert offenders - SLUG_OPTION_ALLOWLIST == set()
    assert (
        offenders & SLUG_OPTION_ALLOWLIST == SLUG_OPTION_ALLOWLIST
    )  # the walk does see the option


# --------------------------------------------------------------------------- reuse after purge


async def test_a_purged_slug_may_be_taken_again_and_old_headers_then_read_as_the_new_entity(
    project, invoke
) -> None:
    """Accepted by ruling: creation does not consult comment history, so reuse after a purge
    succeeds and the earlier header names the newcomer. Do not add that check as a fix."""
    await invoke(["operator", "add", "Anna Lee", "--slug", "op-anna"])
    await invoke(["create", "task", "Target", "--author", "manager"])
    await invoke(["task", "3", "comment", "--as", "op-anna", "-m", "from the first Anna"])
    assert (await invoke(["operator", "op-anna", "rm", "--purge"])).exit_code == 0

    again = await invoke(["operator", "add", "Anna Other", "--slug", "op-anna"])

    assert again.exit_code == 0, again.output
    comments = json.loads((await invoke(["task", "3", "comments", "--json"])).output)
    assert [c["author_slug"] for c in comments] == ["op-anna"]
