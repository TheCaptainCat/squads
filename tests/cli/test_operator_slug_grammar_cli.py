"""An operator's slug is ``op-`` plus the slug grammar: operator creation refuses anything else,
typed or derived, through ``sq operator add --slug`` and through the bulk importer, and writes
nothing when it refuses."""

import json

import pytest

from _helpers import squad_tree
from squads._models._participants import operator_slug_suggestion

pytestmark = pytest.mark.anyio

REFUSED = [
    pytest.param("squads", "'op-squads'", id="reserved-system"),
    pytest.param("operator", "'op-operator'", id="reserved-anonymous"),
    pytest.param("qa", "'op-qa'", id="a-live-roles-slug"),
    pytest.param("Bad Slug", "'op-bad-slug'", id="space-and-capitals"),
    pytest.param("OP-UP", "'op-up'", id="prefix-in-capitals"),
    pytest.param("op-", None, id="empty-tail"),
    pytest.param("op--x", "'op-x'", id="double-hyphen-after-prefix"),
    pytest.param("Op-anna", "'op-anna'", id="mixed-case-prefix"),
    pytest.param("op-anna ", "'op-anna'", id="trailing-space"),
    pytest.param("op_anna", "'op-anna'", id="underscore-for-hyphen"),
    pytest.param("anna", "'op-anna'", id="no-prefix"),
    pytest.param("-op-anna", "'op-anna'", id="leading-hyphen"),
]
ACCEPTED = ["op-anna", "op-a1", "op-1", "op-ann-lee", "op-x"]


def _import_create(tmp_path, slug: str):
    path = tmp_path / "events.jsonl"
    event = {"op": "create", "type": "operator", "title": "Anna Lee", "slug": slug}
    path.write_text(json.dumps(event) + "\n", encoding="utf-8")
    return ["import", str(path), "--as", "manager"]


def _argv(entry: str, tmp_path, slug: str) -> list[str]:
    if entry == "operator-add":
        return ["operator", "add", "Anna Lee", "--slug", slug]
    return _import_create(tmp_path, slug)


@pytest.mark.parametrize("entry", ["operator-add", "bulk-import"])
@pytest.mark.parametrize(("slug", "example"), REFUSED)
async def test_operator_creation_refuses_a_slug_outside_its_grammar_and_writes_nothing(
    project, invoke, tmp_path, entry, slug, example
) -> None:
    argv = _argv(entry, tmp_path, slug)
    before = squad_tree(project.root)

    r = await invoke(argv)

    assert r.exit_code == 1, r.output
    rule = "must be 'op-' followed by" if slug.startswith("op-") else "must start with 'op-' and be"
    assert f"operator slug {slug!r} {rule} lowercase letters, digits and hyphens" in r.output
    assert (f"(e.g. {example})" in r.output) if example else "(e.g." not in r.output
    assert squad_tree(project.root) == before


@pytest.mark.parametrize("entry", ["operator-add", "bulk-import"])
@pytest.mark.parametrize("slug", ACCEPTED)
async def test_operator_creation_stores_the_slug_exactly_as_typed(
    project, invoke, tmp_path, entry, slug
) -> None:
    r = await invoke(_argv(entry, tmp_path, slug))

    assert r.exit_code == 0, r.output
    assert any(p.name.endswith(f"-{slug}.md") for p in (project.squad_dir / "operators").iterdir())


@pytest.mark.parametrize(
    ("name", "slug"),
    [
        pytest.param("Anna Lee", "op-anna", id="ascii"),
        pytest.param("Élodie Roux", "op-elodie", id="accented"),
        pytest.param("日本語", "op-untitled", id="non-latin"),
        pytest.param("!!!", "op-untitled", id="punctuation-only"),
        pytest.param("  Anna  ", "op-anna", id="padded"),
    ],
)
async def test_the_derived_operator_slug_is_accepted(project, invoke, name, slug) -> None:
    r = await invoke(["operator", "add", name])

    assert r.exit_code == 0, r.output
    assert f"`{slug}`" in r.output


async def test_an_imported_operator_without_a_slug_gets_the_derived_operator_slug(
    project, invoke, tmp_path
) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text(
        json.dumps({"op": "create", "type": "operator", "title": "Anna Lee"}) + "\n",
        encoding="utf-8",
    )

    r = await invoke(["import", str(path), "--as", "manager"])

    assert r.exit_code == 0, r.output
    assert any(p.name.endswith("-op-anna.md") for p in (project.squad_dir / "operators").iterdir())


@pytest.mark.parametrize(
    ("slug", "expected"),
    [
        ("Anna", "op-anna"),
        ("op-", None),
        ("!!", None),
        ("OP-A_B", "op-a-b"),
        ("squads", "op-squads"),
    ],
)
def test_the_suggested_operator_slug_is_compliant_or_absent(slug, expected) -> None:
    assert operator_slug_suggestion(slug) == expected


async def test_a_skill_slug_is_not_held_to_the_operator_rule(project, invoke) -> None:
    r = await invoke(["skill", "add", "Pairing"])

    assert r.exit_code == 0, r.output
    assert (await invoke(["skill", "pairing", "show"])).exit_code == 0


# --------------------------------------------------------------------------- importer-shaped


def _import_operators(tmp_path, *names: str) -> list[str]:
    path = tmp_path / "events.jsonl"
    path.write_text(
        "".join(json.dumps({"op": "create", "type": "operator", "title": n}) + "\n" for n in names),
        encoding="utf-8",
    )
    return ["import", str(path), "--as", "manager"]


async def test_an_imported_operator_stores_its_slug_and_name_the_way_operator_add_does(
    project, invoke, tmp_path
) -> None:
    assert (await invoke(_import_operators(tmp_path, "Anna Lee"))).exit_code == 0
    assert (await invoke(["operator", "add", "Bob Ray"])).exit_code == 0

    stored = {
        p.name.split("-", 2)[2]: p.read_text(encoding="utf-8")
        for p in (project.squad_dir / "operators").iterdir()
    }
    for name, text in stored.items():
        slug = name.removesuffix(".md")
        assert f"\n  slug: {slug}\n" in text and "\n  full_name: " in text


@pytest.mark.parametrize(
    ("first", "second"),
    [
        pytest.param("add", ["Ann Smith"], id="add-then-import"),
        pytest.param("import", ["Ann Smith"], id="import-then-import"),
        pytest.param("import", ["Ann Smith", "Ann Jones"], id="one-batch"),
        pytest.param("add-untitled", ["日本語"], id="untitled-after-add"),
        pytest.param("import-untitled", ["!!!"], id="untitled-after-import"),
        pytest.param("none", ["!!!", "Ζωή Ελ"], id="untitled-twice-in-one-batch"),
    ],
)
async def test_a_second_operator_with_the_same_slug_is_refused_by_every_entry_path(
    project, invoke, tmp_path, first, second
) -> None:
    argv = _import_operators(tmp_path, *second)
    if first == "add":
        assert (await invoke(["operator", "add", "Ann Lee"])).exit_code == 0
    elif first == "add-untitled":
        assert (await invoke(["operator", "add", "!!!"])).exit_code == 0
    elif first == "import":
        assert (await invoke(_import_operators(tmp_path, "Ann Lee"))).exit_code == 0
    elif first == "import-untitled":
        assert (await invoke(_import_operators(tmp_path, "Ζωή Ελ"))).exit_code == 0
    before = squad_tree(project.root)

    r = await invoke(argv)

    assert r.exit_code == 1, r.output
    assert "already exists" in r.output
    assert squad_tree(project.root) == before


@pytest.mark.parametrize("first", ["import", "add"])
async def test_operator_add_is_refused_when_an_imported_operator_holds_the_slug(
    project, invoke, tmp_path, first
) -> None:
    if first == "import":
        assert (await invoke(_import_operators(tmp_path, "Ann Smith"))).exit_code == 0
        before = squad_tree(project.root)

        r = await invoke(["operator", "add", "Ann Lee"])

        assert r.exit_code == 1 and "already exists" in r.output
        assert squad_tree(project.root) == before
    else:
        assert (await invoke(["operator", "add", "Ann Lee"])).exit_code == 0
        assert (await invoke(["operator", "add", "Ann Smith"])).exit_code == 1
