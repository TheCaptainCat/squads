"""The 0.16 step lifts the nested ``extra`` block of every item file to top-level keys.

Three tables. The first drives the per-file transform, a pure function over a frontmatter
mapping, with a row per key shape and per exception. The second runs the step over a squad written
in the 0.15 shape and reads every operator row and every role-name row off the migrated files.
The third drives what a run does around the transform: refusing with one combined report,
composing with the comment-header rewrite, and changing nothing the second time.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from _helpers import squad_tree
from _legacy_squad import (
    TS,
    add_legacy_operator,
    inject,
    legacy_shape,
    read,
    reopen,
    roster,
    stamp_behind,
    task,
)
from squads._errors import SquadsError
from squads._index._resolver import item_file
from squads._migrations._v0_15_to_v0_16 import flatten_frontmatter
from squads._models._item import Item
from squads._rendering._engine import invalidate_squad_dir as invalidate
from squads._sections import replace_frontmatter, split_frontmatter

pytestmark = pytest.mark.anyio

# --------------------------------------------------------------------------- the transform


def _front(item_type: str, **fields: Any) -> dict[str, Any]:
    return {
        "id": f"{item_type.upper()}-1",
        "sequence_id": 1,
        "type": item_type,
        "title": "Example",
        "status": "Active",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        **fields,
    }


@dataclass(frozen=True)
class Row:
    id: str
    given: dict[str, Any]
    expected: dict[str, Any] | None  # None: the input comes back untouched
    lifted: tuple[str, ...] = ()
    flags: dict[str, bool] = field(default_factory=dict[str, bool])


ROWS = [
    Row("nothing-to-do", _front("guide"), None),
    Row(
        "declared-and-undeclared-keys-are-lifted-in-order",
        _front("guide", extra={"tags": ["a"], "tech": "go", "hand_key": "keep"}),
        _front("guide", tags=["a"], tech="go", hand_key="keep"),
        ("tags", "tech", "hand_key"),
    ),
    Row("an-empty-extra-is-removed", _front("guide", extra={}), _front("guide")),
    Row("a-null-extra-is-removed", _front("guide", extra=None), _front("guide")),
    Row(
        "a-top-level-unknown-key-precedes-the-lifted-ones",
        _front("guide", hand_key="x", extra={"tags": ["a"]}),
        _front("guide", hand_key="x", tags=["a"]),
        ("tags",),
    ),
    Row(
        "a-lifted-key-equal-to-the-top-level-one-is-not-repeated",
        _front("guide", tech="go", extra={"tech": "go"}),
        _front("guide", tech="go"),
    ),
    Row(
        "a-role-keeps-its-operator-settings-and-loses-the-mirror",
        _front(
            "role",
            extra={
                "slug": "a-slug",
                "is_default": False,
                "model": "opus",
                "is_dev": True,
                "tech": "go",
                "mission": "M",
                "full_name": "X",
                "title": "T",
                "description": "D",
                "skills": ["a"],
            },
        ),
        _front("role", slug="a-slug", is_default=False, model="opus", is_dev=True, tech="go"),
        ("is_default", "model", "is_dev", "tech"),
    ),
    Row(
        "a-roster-file-without-a-slug-gets-the-file-names",
        _front("role"),
        _front("role", slug="a-slug"),
    ),
    Row(
        "an-operator-whose-full-name-equals-its-title",
        _front("operator", extra={"slug": "a-slug", "full_name": "Example"}),
        _front("operator", slug="a-slug"),
    ),
    Row(
        "an-operator-whose-full-name-differs-takes-it-as-the-title",
        _front("operator", extra={"slug": "a-slug", "full_name": "Real Name"}),
        {**_front("operator", slug="a-slug"), "title": "Real Name"},
        flags={"retitled": True},
    ),
    Row(
        "an-operator-the-importer-wrote",
        _front("operator", extra={}),
        _front("operator", slug="a-slug"),
    ),
    Row(
        "a-skill-description-is-dropped-when-the-top-level-one-is-set",
        _front("skill", description="Top", extra={"slug": "a-slug", "description": "Stale"}),
        _front("skill", slug="a-slug", description="Top"),
        flags={"description_dropped": True, "description_differed": True},
    ),
    Row(
        "a-skill-description-equal-to-the-kept-one-is-dropped-unlisted",
        _front("skill", description="Same", extra={"slug": "a-slug", "description": "Same"}),
        _front("skill", slug="a-slug", description="Same"),
        flags={"description_dropped": True},
    ),
    Row(
        "a-skill-description-becomes-the-top-level-one-when-that-is-empty",
        _front("skill", extra={"slug": "a-slug", "description": "Kept"}),
        _front("skill", slug="a-slug", description="Kept"),
    ),
    Row(
        "a-skill-description-equal-to-the-title-is-dropped",
        _front("skill", extra={"slug": "a-slug", "description": "Example"}),
        _front("skill", slug="a-slug"),
        flags={"description_dropped": True},
    ),
    Row(
        "the-stray-path-on-a-skill-is-removed",
        _front("skill", path="agents/skills/x.md", extra={"slug": "a-slug"}),
        _front("skill", slug="a-slug"),
        flags={"path_removed": True},
    ),
    Row(
        "the-legacy-severity-becomes-the-top-level-one",
        _front("bug", extra={"severity": "high"}),
        _front("bug", severity="high"),
    ),
    Row(
        "a-top-level-severity-wins-over-the-legacy-one",
        _front("bug", severity="low", extra={"severity": "high"}),
        _front("bug", severity="low"),
    ),
    Row(
        "the-legacy-ref-kind-map-is-folded-into-the-refs",
        _front("task", refs=["A-1", "B-2"], extra={"ref_kinds": {"B-2": "fixes"}}),
        _front("task", refs=["A-1", "B-2:fixes"]),
    ),
]

#: Rows the transform refuses: (id, input, fragment of the problem).
REFUSED = [
    ("extra-is-a-string", _front("guide", extra="oops"), "extra is not a mapping"),
    ("extra-is-a-list", _front("guide", extra=[1, 2]), "extra is not a mapping"),
    (
        "a-lifted-key-collides-with-a-different-top-level-value",
        _front("guide", tech="go", extra={"tech": "rust"}),
        "extra.tech and the top-level tech hold different values",
    ),
    (
        "a-roster-slug-differs-from-the-file-name",
        _front("role", extra={"slug": "other"}),
        "extra.slug 'other' differs from the file name's slug 'a-slug'",
    ),
    (
        "a-non-roster-slug-differs-from-the-file-name",
        _front("guide", extra={"slug": "other"}),
        "extra.slug 'other' differs from the file name's slug 'a-slug'",
    ),
    *[
        (
            f"extra-holds-the-core-key-{key}",
            _front("task", extra={key: value}),
            f"extra.{key} would become the item's own '{key}'",
        )
        for key, value in (("assignee", "qa"), ("parent", "FEAT-9"), ("labels", ["x"]))
    ],
    *[
        (
            f"extra-holds-the-name-{key}",
            _front("guide", extra={key: {"a": 1} if key == "extra" else "x"}),
            f"extra.{key} would become the item's own '{key}'",
        )
        for key in ("extra", "path", "prefix")
    ],
    (
        "a-skills-extra-path",
        _front("skill", extra={"slug": "a-slug", "path": "x.md"}),
        "extra.path would become the item's own 'path'",
    ),
]


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r.id)
def test_the_per_file_transform(row: Row) -> None:
    flat = flatten_frontmatter(row.given, file_slug="a-slug", default_kind="related", source="f.md")

    assert flat.problems == ()
    if row.expected is None:
        assert flat.data is row.given
        assert flat.changed is False
        return
    assert flat.changed is True
    assert flat.data == row.expected
    reloaded = Item.from_frontmatter(
        flat.data, path="guides/GUIDE-000001-example.md", default_kind="related"
    ).to_frontmatter_dict()
    assert list(flat.data) == list(reloaded)
    assert flat.lifted == row.lifted
    for flag in ("retitled", "description_dropped", "description_differed", "path_removed"):
        assert getattr(flat, flag) is row.flags.get(flag, False), flag


@pytest.mark.parametrize(
    ("given", "fragment"), [r[1:] for r in REFUSED], ids=[r[0] for r in REFUSED]
)
def test_a_file_that_cannot_be_flattened_comes_back_untouched_with_its_problem(
    given: dict[str, Any], fragment: str
) -> None:
    flat = flatten_frontmatter(given, file_slug="a-slug", default_kind="related", source="f.md")

    assert flat.data is given
    assert flat.changed is False
    assert len([p for p in flat.problems if p.startswith(f"f.md: {fragment}")]) == 1


# --------------------------------------------------------------------------- over a squad


def _front_of(text: str) -> dict[str, Any]:
    return split_frontmatter(text)[0]


#: (id, name, slug, shape of the 0.15 file, stored full name, expected title, retitled)
OPERATORS = [
    ("name-and-title-equal", "Imp Orted", "op-imp", {}, None, "Imp Orted", False),
    ("full-name-differs", "Imp Orted", "op-imp", {}, "Real Name", "Real Name", True),
    (
        "importer-shape",
        "Imp Orted",
        "op-imp",
        {"stored_slug": False, "stored_full_name": False},
        None,
        "Imp Orted",
        False,
    ),
]


@pytest.mark.parametrize(
    ("name", "slug", "shape", "stored_name", "title", "retitled"),
    [r[1:] for r in OPERATORS],
    ids=[r[0] for r in OPERATORS],
)
async def test_an_operator_ends_with_a_slug_and_one_name_and_a_changed_one_is_reported(
    project, svc, name, slug, shape, stored_name, title, retitled
) -> None:
    path = await add_legacy_operator(svc, name, slug, stored_name=stored_name, **shape)
    before = await read(path)
    stamp_behind(project.root)

    run = await reopen(project.root).run_pending_migrations()

    after = await read(path)
    front = _front_of(after)
    assert front["slug"] == slug and front["title"] == title
    assert "extra" not in front and "full_name" not in front
    assert after.split("---\n", 2)[2] == before.split("---\n", 2)[2]  # the body is untouched
    report = [line for lines in run.reports.values() for line in lines]
    assert f"{int(retitled)} operator title(s) set from the stored full name" in report
    assert (f"  {path.relative_to(project.squad_dir).as_posix()}" in report) is retitled
    migrated = reopen(project.root)
    created = (await migrated.create("task", "T", author="manager", assignee=slug)).item
    assert created.assignee == slug
    assert await migrated.author(slug) == title


# --------------------------------------------------------------------------- the name of a role

#: (id, how the role is made)
ROLE_ROWS = [
    ("bundled-with-the-catalog-name", "bundled"),
    ("bundled-with-another-name", "chosen-bundled"),
    ("developer-with-a-pool-name", "developer"),
    ("developer-with-another-name", "chosen-developer"),
    ("developer-named-from-the-squads-own-pool", "own-pool"),
    ("project-defined-role", "project"),
]


async def _own_pool_developer(project):
    (project.squad_dir / ".overrides").mkdir(exist_ok=True)
    (project.squad_dir / ".overrides" / "roles.toml").write_text(
        '[dev]\nname_pool = ["Zed", "Yan"]\n', encoding="utf-8"
    )
    return await reopen(project.root).add_dev("rust")


async def _project_defined_role(svc, project):
    override = project.squad_dir / ".overrides" / "roles"
    override.mkdir(parents=True, exist_ok=True)
    (override / "compliance.toml").write_text(
        'full_name = "Sam Security"\ntitle = "security"\ndescription = "Keeps it safe."\n'
        'mission = "Find issues."\n',
        encoding="utf-8",
    )
    return await svc.activate_role("compliance")


async def _role(svc, project, how: str):
    makers = {
        "bundled": lambda: svc.activate_role("architect"),
        "chosen-bundled": lambda: svc.activate_role("qa", name="Sam Lee"),
        "developer": lambda: svc.add_dev("python"),
        "chosen-developer": lambda: svc.add_dev("go", name="Ada Gopher"),
        "own-pool": lambda: _own_pool_developer(project),
        "project": lambda: _project_defined_role(svc, project),
    }
    return await makers[how]()


@pytest.mark.parametrize("how", [r[1] for r in ROLE_ROWS], ids=[r[0] for r in ROLE_ROWS])
async def test_the_step_keeps_every_stored_role_name_whatever_the_configuration_says(
    project, svc, how: str
) -> None:
    role = await _role(svc, project, how)
    if how != "project":  # a per-slug file naming the role differently, added after creation
        per_slug = project.squad_dir / ".overrides" / "roles" / f"{role.slug}.toml"
        per_slug.parent.mkdir(parents=True, exist_ok=True)
        per_slug.write_text('full_name = "Changed By Config"\n', encoding="utf-8")
        invalidate(project.squad_dir)
    path = item_file(svc.paths, role)
    legacy_shape(path, move=("slug", "is_dev", "tech", "model", "is_default"))
    stamp_behind(project.root)

    await reopen(project.root).run_pending_migrations()

    front = _front_of(await read(path))
    assert front["title"] == role.title
    assert "extra" not in front and front["slug"] == role.slug
    assert "name_chosen" not in front and "pool_name" not in front
    await reopen(project.root).sync()
    assert (await reopen(project.root).get(role.id)).title == role.title


# --------------------------------------------------------------------------- around the transform


async def test_a_refusal_lists_the_flat_problems_with_the_header_ones_and_writes_nothing(
    project, svc
) -> None:
    guide = (await svc.create("guide", "Notes", author="manager")).item
    legacy_shape(item_file(svc.paths, guide), move=(), extra={"tech": "go"})
    path = item_file(svc.paths, guide)
    text = await read(path)
    data = _front_of(text)
    data["tech"] = "rust"  # a top-level value the extra block disagrees with
    path.write_text(replace_frontmatter(text, data), encoding="utf-8")
    await inject(svc, await task(svc), f"- [{TS}] Nobody Known:\n  - hi\n")
    stamp_behind(project.root)
    settled_before = squad_tree(project.root)

    with pytest.raises(SquadsError) as raised:
        await reopen(project.root).run_pending_migrations()

    message = str(raised.value)
    assert "extra.tech and the top-level tech hold different values" in message
    assert "'Nobody Known' matches no roster entry" in message
    assert "2 problem(s) found." in message
    index = "squads/.squads.json"
    after = squad_tree(project.root)
    assert {k: v for k, v in after.items() if k != index} == {
        k: v for k, v in settled_before.items() if k != index
    }


async def test_the_header_rewrite_and_the_flattening_compose_on_one_file(project, svc) -> None:
    op = await add_legacy_operator(svc, "Zoë Müller", "op-zo", stored_name="Zoe Mueller")
    item = await svc.roster_item("operator", "op-zo")
    assert item is not None
    await inject(svc, await task(svc), f"- [{TS}] Zoe Mueller:\n  - hi\n")
    stamp_behind(project.root)

    await reopen(project.root).run_pending_migrations()

    front = _front_of(await read(op))
    assert front["title"] == "Zoe Mueller" and "extra" not in front
    found = [
        p.read_text(encoding="utf-8") for p in project.squad_dir.rglob("TASK-*.md") if p.is_file()
    ]
    assert any(re.search(rf"- \[{TS}\] `op-zo` Zoe Mueller:", text) for text in found)


async def test_a_migrated_file_round_trips_through_the_model_and_a_second_run_changes_nothing(
    project, svc
) -> None:
    await svc.activate_role("architect")
    await svc.add_dev("python")
    await add_legacy_operator(svc, "Imp Orted", "op-imp", stored_name="Real Name")
    guide = (await svc.create("guide", "Notes", author="manager")).item
    legacy_shape(item_file(svc.paths, guide), extra={"tags": ["a"], "tech": "go"})
    for role in await svc.list_items(item_type="role"):
        legacy_shape(
            item_file(svc.paths, role),
            move=("slug", "is_dev", "tech", "model", "is_default"),
        )
    stamp_behind(project.root)
    migrated = reopen(project.root)
    await migrated.run_pending_migrations()

    default_kind = migrated.spec.default_ref_kind()
    for path in sorted(project.squad_dir.rglob("*.md")):
        text = await read(path)
        front, _ = split_frontmatter(text)
        if not front.get("type"):
            continue
        item = Item.from_frontmatter(
            front, path=path.relative_to(project.squad_dir).as_posix(), default_kind=default_kind
        )
        assert replace_frontmatter(text, item.to_frontmatter_dict()) == text, path.name

    settled = squad_tree(project.root)
    stamp_behind(project.root)
    await reopen(project.root).run_pending_migrations()
    index = {"squads/.squads.json", "squads/.reflog.jsonl", ".squads.toml"}
    assert {k: v for k, v in squad_tree(project.root).items() if k not in index} == {
        k: v for k, v in settled.items() if k not in index
    }


# --------------------------------------------------------------------------- line endings

#: (id, what is written in the 0.15 shape, line terminator of the whole file)
KINDS = ["role", "developer", "operator", "skill", "guide"]


async def _legacy_file(svc, kind: str) -> Path:
    if kind == "role":
        role = await svc.activate_role("qa", name="Hank Chosen")
        path = item_file(svc.paths, role)
        legacy_shape(path, move=("slug", "is_dev", "tech", "model", "is_default"))
    elif kind == "developer":
        role = await svc.add_dev("python")
        path = item_file(svc.paths, role)
        legacy_shape(path, move=("slug", "is_dev", "tech", "model", "is_default"))
    elif kind == "operator":
        path = await add_legacy_operator(svc, "Imp Orted", "op-imp", stored_name="Real Name")
    elif kind == "skill":
        skill = await svc.add_skill("Runbook", description="Top", when_to_use="Before a release")
        path = item_file(svc.paths, skill)
        legacy_shape(
            path, move=("when_to_use", "allowed_tools"), extra={"slug": skill.slug}, drop=("slug",)
        )
    else:
        guide = (await svc.create("guide", "Notes", author="manager")).item
        path = item_file(svc.paths, guide)
        legacy_shape(path, extra={"tags": ["a", "b"], "tech": "python"})
    return path


@pytest.mark.parametrize("eol", ["\n", "\r\n"], ids=["LF", "CRLF"])
@pytest.mark.parametrize("kind", KINDS)
async def test_the_step_flattens_a_file_whatever_its_line_endings_and_keeps_them(
    project, svc, kind: str, eol: str
) -> None:
    path = await _legacy_file(svc, kind)
    text = (await read(path)).replace("\r\n", "\n").replace("\n", eol)
    path.write_bytes(text.encode())
    stamp_behind(project.root)

    run = await reopen(project.root).run_pending_migrations()

    after = await read(path)
    front = _front_of(after)
    assert "extra" not in front, "the file was not flattened"
    assert kind == "guide" or front.get("slug"), "a roster file carries no slug"
    assert after.count("\n") == after.count(eol if eol == "\r\n" else "\n")
    if eol == "\r\n":
        assert "\n" not in after.replace("\r\n", ""), "a bare line feed was written"
    if kind == "guide":
        assert front["tags"] == ["a", "b"] and front["tech"] == "python"
    migrated = reopen(project.root)
    assert not [i for i in await migrated.check() if i.level == "error"]
    report = [line for lines in run.reports.values() for line in lines]
    assert any(
        line.startswith("1 file(s) flattened") or "file(s) flattened" in line for line in report
    )


async def test_a_role_with_crlf_line_endings_keeps_its_name(project, svc) -> None:
    role = await svc.activate_role("devops", name="Hank Chosen")
    path = item_file(svc.paths, role)
    legacy_shape(path, move=("slug", "is_dev", "tech", "model", "is_default"))
    path.write_bytes((await read(path)).replace("\n", "\r\n").encode())
    stamp_behind(project.root)

    await reopen(project.root).run_pending_migrations()

    migrated = reopen(project.root)
    assert (await migrated.get(role.id)).title == "Hank Chosen"
    assert (await migrated.roster_item("role", "devops")) is not None
    await migrated.sync()
    assert (await migrated.get(role.id)).title == "Hank Chosen"


# --------------------------------------------------------------------------- reporting and refusal


async def test_a_dropped_skill_description_that_differed_is_listed_by_file(project, svc) -> None:
    same = await svc.add_skill("Same Text", description="One")
    differs = await svc.add_skill("Other Text", description="Top")
    for skill, stale in ((same, "One"), (differs, "Stale")):
        legacy_shape(
            item_file(svc.paths, skill),
            extra={"slug": skill.slug, "description": stale},
            drop=("slug",),
        )
    stamp_behind(project.root)

    run = await reopen(project.root).run_pending_migrations()

    report = [line for lines in run.reports.values() for line in lines]
    assert "2 skill description(s) dropped" in " ".join(report)
    assert "1 dropped skill description(s) differed from the one kept" in report
    listed = report[report.index("1 dropped skill description(s) differed from the one kept") + 1]
    assert listed == f"  {item_file(svc.paths, differs).relative_to(project.squad_dir).as_posix()}"


async def test_a_refused_run_leaves_the_index_as_the_earlier_release_wrote_it(project, svc) -> None:
    await roster(svc)
    await inject(svc, await task(svc), f"- [{TS}] Nobody Known:\n  - hi\n")
    stamp_behind(project.root)
    index = project.squad_dir / ".squads.json"
    before = index.read_bytes()

    with pytest.raises(SquadsError):
        await reopen(project.root).run_pending_migrations()

    assert index.read_bytes() == before
