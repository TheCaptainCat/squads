"""A role item is an identity over one base chosen from its stored facts (``template``, then
``mission``, then the catalog); the per-slug file merges over it; the item's stored name,
default designation and model win over every layer. Driven at the CLI, reading ``role show
--json``, the generated pointer and the listings.

One table per behaviour: the base kind by the layer that touches it, the stored default
designation, the stored model, the JSON surfaces, and the origin of each base.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.anyio

_ADD = ["--name", "Sam Sre", "--job-title", "SRE", "--desc", "Keeps it up.", "--mission", "Run it."]
_CATALOG_SRE = (
    '[bundles]\nall = ["manager", "architect", "tech-lead", "reviewer", "qa", "devops", '
    '"product-owner", "tech-writer", "sre"]\n\n[[roles]]\nslug = "sre"\nfull_name = "Catalog Sre"\n'
    'title = "catalog sre"\ndescription = "From the catalog."\nmission = "The catalog mission."\n'
)


def _write(project, relative: str, body: str) -> None:
    path = project.squad_dir / ".overrides" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _pointer(project, slug: str) -> str:
    return (project.root / ".claude" / "agents" / f"{slug}.md").read_text(encoding="utf-8")


async def _show(invoke, slug: str) -> dict[str, object]:
    result = await invoke(["role", slug, "show", "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


async def _make(invoke, kind: str) -> str:
    """Create a role of *kind* and return its slug."""
    if kind == "catalog":
        argv, slug = ["role", "activate", "architect"], "architect"
    elif kind == "template":
        argv, slug = ["dev", "add", "--tech", "rust"], "rust-dev"
    else:
        argv, slug = ["role", "add", "sre", *_ADD], "sre"
    result = await invoke(argv)
    assert result.exit_code == 0, result.output
    return slug


# ------------------------------------------------------------------------------ kind x layer

#: (id, kind, per-slug file body, stored change, expected json fields)
LAYERS = [
    ("catalog-bare", "catalog", None, None, {"title": "architect", "model": "opus"}),
    (
        "catalog-file",
        "catalog",
        'title = "chief architect"\nmodel = "haiku"\n',
        None,
        {"title": "chief architect", "model": "haiku"},
    ),
    (
        "catalog-file-and-stored-model",
        "catalog",
        'model = "haiku"\n',
        ["--model", "sonnet"],
        {"title": "architect", "model": "sonnet"},
    ),
    ("template-bare", "template", None, None, {"title": "Rust developer", "model": "sonnet"}),
    (
        "template-file",
        "template",
        'title = "Staff Rust developer"\nmodel = "inherit"\n',
        None,
        {"title": "Staff Rust developer", "model": "inherit"},
    ),
    (
        "template-file-and-stored-model",
        "template",
        'model = "inherit"\n',
        ["--model", "opus"],
        {"title": "Rust developer", "model": "opus"},
    ),
    ("item-bare", "item", None, None, {"title": "SRE", "model": None}),
    (
        "item-file",
        "item",
        'title = "Staff SRE"\nmodel = "haiku"\n',
        None,
        {"title": "Staff SRE", "model": "haiku"},
    ),
    (
        "item-file-and-stored-model",
        "item",
        'model = "haiku"\n',
        ["--model", "opus"],
        {"title": "SRE", "model": "opus"},
    ),
]


@pytest.mark.parametrize(
    ("kind", "file_body", "stored", "expected"),
    [r[1:] for r in LAYERS],
    ids=[r[0] for r in LAYERS],
)
async def test_each_kind_resolves_base_then_file_then_stored_values(
    project,
    invoke,
    kind: str,
    file_body: str | None,
    stored: list[str] | None,
    expected: dict[str, object],
) -> None:
    slug = await _make(invoke, kind)
    if file_body is not None:
        _write(project, f"roles/{slug}.toml", file_body)
    if stored is not None:
        result = await invoke(["role", slug, "update", *stored])
        assert result.exit_code == 0, result.output
    assert (await invoke(["sync"])).exit_code == 0

    shown = await _show(invoke, slug)

    for key, value in expected.items():
        assert shown[key] == value, (key, shown)
    model = expected["model"]
    if model is not None and model != "inherit":
        assert f"model: {model}" in _pointer(project, slug)


async def test_the_kind_is_stored_not_looked_up_for_the_show_card_and_the_pointer(
    project, invoke
) -> None:
    """An item-defined ``sre``, then a catalog entry ``sre`` with another mission: ``sq role sre
    show`` and the pointer keep the item's mission."""
    await _make(invoke, "item")
    _write(project, "roles.toml", _CATALOG_SRE)

    shown = await _show(invoke, "sre")
    synced = await invoke(["sync"])

    assert synced.exit_code == 0, synced.output
    assert shown["mission"] == "Run it."
    assert shown["full_name"] == "Sam Sre"
    assert "Keeps it up." in _pointer(project, "sre")
    assert "From the catalog." not in _pointer(project, "sre")


# ---------------------------------------------------------------- stored default designation

_CLAUDE_LINE = "default to **{name}** (`{slug}`)"


async def _default_holders(invoke) -> set[str]:
    result = await invoke(["role", "list", "--json"])
    assert result.exit_code == 0, result.output
    return {row["slug"] for row in json.loads(result.output) if row["is_default"]}


async def _setup_default(invoke, row: str) -> tuple[str, str]:
    """Bring the squad to *row*'s state and return the expected holder's (slug, name)."""
    if row == "item-defined-role":
        assert (
            await invoke(["role", "add", "lead", "--name", "Lee Lead", *_ADD[2:]])
        ).exit_code == 0
        assert (await invoke(["role", "lead", "set-default"])).exit_code == 0
        return "lead", "Lee Lead"
    if row == "previous-default-archived":
        assert (
            await invoke(["role", "add", "lead", "--name", "Lee Lead", *_ADD[2:]])
        ).exit_code == 0
        assert (await invoke(["role", "lead", "set-default"])).exit_code == 0
        assert (await invoke(["role", "manager", "status", "Archived"])).exit_code == 0
        return "lead", "Lee Lead"
    if row == "bundled-role":
        assert (await invoke(["role", "activate", "qa"])).exit_code == 0
        assert (await invoke(["role", "qa", "set-default"])).exit_code == 0
        return "qa", "Mara Tester"
    assert row == "moved-away"
    assert (await invoke(["role", "add", "lead", "--name", "Lee Lead", *_ADD[2:]])).exit_code == 0
    assert (await invoke(["role", "activate", "qa"])).exit_code == 0
    assert (await invoke(["role", "lead", "set-default"])).exit_code == 0
    assert (await invoke(["role", "qa", "set-default"])).exit_code == 0
    return "qa", "Mara Tester"


@pytest.mark.parametrize(
    "row", ["item-defined-role", "previous-default-archived", "bundled-role", "moved-away"]
)
async def test_the_stored_default_designation_survives_every_reader(
    project, invoke, row: str
) -> None:
    slug, name = await _setup_default(invoke, row)

    for maintenance in ([], ["sync"], ["repair"]):
        if maintenance:
            assert (await invoke(maintenance)).exit_code == 0
        assert await _default_holders(invoke) == {slug}
        assert (await _show(invoke, slug))["is_default"] is True
        claude = (project.root / "CLAUDE.md").read_text(encoding="utf-8")
        assert _CLAUDE_LINE.format(name=name, slug=slug) in claude
    plain = await invoke(["role", "list"])
    assert next(ln for ln in plain.output.splitlines() if ln.split()[:1] == [slug]).count("✓") >= 1


# ------------------------------------------------------------------------- stored model

#: (id, setup, slug, per-slug file body, expected model)
MODELS = [
    (
        "bundled-role",
        ["role", "activate", "reviewer", "--model", "haiku"],
        "reviewer",
        None,
        "haiku",
    ),
    ("developer", ["dev", "add", "--tech", "go", "--model", "haiku"], "go-dev", None, "haiku"),
    (
        "item-defined-role-over-a-file-saying-sonnet",
        ["role", "add", "sre", *_ADD, "--model", "haiku"],
        "sre",
        'model = "sonnet"\n',
        "haiku",
    ),
    (
        "catalog-role-over-a-file-saying-sonnet",
        ["role", "activate", "reviewer", "--model", "haiku"],
        "reviewer",
        'model = "sonnet"\n',
        "haiku",
    ),
    (
        "no-stored-model-follows-the-catalog",
        ["role", "activate", "reviewer"],
        "reviewer",
        None,
        "opus",
    ),
    (
        "no-stored-model-follows-the-template",
        ["dev", "add", "--tech", "go"],
        "go-dev",
        None,
        "sonnet",
    ),
    (
        "no-stored-model-follows-the-file",
        ["role", "activate", "reviewer"],
        "reviewer",
        'model = "sonnet"\n',
        "sonnet",
    ),
]


@pytest.mark.parametrize(
    ("setup", "slug", "file_body", "model"), [r[1:] for r in MODELS], ids=[r[0] for r in MODELS]
)
async def test_a_stored_model_wins_on_every_kind_and_an_absent_one_follows_the_base(
    project, invoke, setup: list[str], slug: str, file_body: str | None, model: str
) -> None:
    assert (await invoke(setup)).exit_code == 0
    if file_body is not None:
        _write(project, f"roles/{slug}.toml", file_body)
    assert (await invoke(["sync"])).exit_code == 0

    assert (await _show(invoke, slug))["model"] == model
    assert f"model: {model}" in _pointer(project, slug)


@pytest.mark.parametrize("model", ["opuss", "Sonnet", "claude-opus-4-5"])
async def test_an_import_naming_an_unknown_model_is_refused_and_writes_nothing(
    project, invoke, tmp_path: Path, model: str
) -> None:
    assert (await invoke(["role", "activate", "reviewer"])).exit_code == 0
    target = str((await _show(invoke, "reviewer"))["id"])
    before = {p: p.read_bytes() for p in sorted(project.squad_dir.rglob("*.md"))}
    events = tmp_path / "events.jsonl"
    events.write_text(
        json.dumps({"op": "update", "target": target, "as": "manager", "fields": {"model": model}})
        + "\n",
        encoding="utf-8",
    )

    result = await invoke(["import", str(events)])

    assert result.exit_code == 1, result.output
    assert "is not one of" in result.output
    assert {p: p.read_bytes() for p in sorted(project.squad_dir.rglob("*.md"))} == before


async def test_an_import_naming_a_valid_model_sets_it_on_a_catalog_role(
    project, invoke, tmp_path: Path
) -> None:
    assert (await invoke(["role", "activate", "reviewer"])).exit_code == 0
    target = str((await _show(invoke, "reviewer"))["id"])
    events = tmp_path / "events.jsonl"
    events.write_text(
        json.dumps(
            {"op": "update", "target": target, "as": "manager", "fields": {"model": "haiku"}}
        )
        + "\n",
        encoding="utf-8",
    )

    result = await invoke(["import", str(events)])

    assert result.exit_code == 0, result.output
    assert (await _show(invoke, "reviewer"))["model"] == "haiku"


# ---------------------------------------------------------------------------- JSON surfaces


async def test_generic_listings_carry_a_description_only_where_the_item_stores_one(
    project, invoke
) -> None:
    for kind in ("catalog", "template", "item"):
        await _make(invoke, kind)

    listed = await invoke(["list", "-t", "role", "--json"])
    assert listed.exit_code == 0, listed.output
    stored = {row["slug"]: row["description"] for row in json.loads(listed.output)}

    assert stored["architect"] == ""
    assert stored["rust-dev"] == ""
    assert stored["sre"] == "Keeps it up."


async def test_the_role_listing_carries_the_resolved_one_line_description_for_every_kind(
    project, invoke
) -> None:
    for kind in ("catalog", "template", "item"):
        await _make(invoke, kind)

    listed = await invoke(["role", "list", "--json"])
    assert listed.exit_code == 0, listed.output
    resolved = {row["slug"]: row["description"] for row in json.loads(listed.output)}

    assert resolved["architect"] == "System design and architecture decisions (ADRs)."
    assert (
        resolved["rust-dev"] == "Implements Rust code following the project's guides and standards."
    )
    assert resolved["sre"] == "Keeps it up."


# ---------------------------------------------------------------------------------- origin


async def test_origin_follows_the_base_each_role_is_built_from(project, invoke) -> None:
    _write(
        project,
        "roles.toml",
        _CATALOG_SRE.replace('"sre"]', '"sre", "ops"]').replace(
            '[[roles]]\nslug = "sre"',
            '[[roles]]\nslug = "ops"\nfull_name = "Olga Ops"\ntitle = "ops"\ndescription = "d"\n'
            'mission = "m"\n\n[[roles]]\nslug = "sre"',
        )
        + '\n[templates.auditor]\ntitle = "{Tech} auditor"\ndescription = "d"\nmission = "m"\n'
        'slug = "{tech}-aud"\nname = "Ann {Tech}"\n',
    )
    _write(project, "roles/devops.toml", 'full_name = "Renamed Ops"\n')
    commands = [
        ["role", "activate", "devops"],  # a bundled entry the project overrides
        ["role", "activate", "architect"],  # a bundled entry
        ["dev", "add", "--tech", "go"],  # a bundled template
        ["role", "activate", "ops"],  # a project [[roles]] entry
        ["role", "activate", "--from", "auditor", "--tech", "go"],  # a project template
        ["role", "add", "scout", "--name", "Sid Scout", *_ADD[2:]],  # defined in its item
    ]
    for argv in commands:
        result = await invoke(argv)
        assert result.exit_code == 0, (argv, result.output)

    origins = {
        slug: (await _show(invoke, slug))["origin"]
        for slug in ("devops", "architect", "go-dev", "ops", "go-aud", "scout")
    }

    assert origins == {
        "devops": "system",
        "architect": "system",
        "go-dev": "system",
        "ops": "project",
        "go-aud": "project",
        "scout": "project",
    }


# --------------------------------------------------------- template text is data (existing roles)


async def test_a_template_override_reaches_an_existing_developer_on_the_next_sync(
    project, invoke
) -> None:
    assert (await invoke(["dev", "add", "--tech", "rust"])).exit_code == 0
    assert "Implement assigned tasks in Rust" in str((await _show(invoke, "rust-dev"))["mission"])

    _write(
        project,
        "roles.toml",
        '[templates.dev]\nmission = "Own the {Tech} surface."\n'
        'description = "Writes {Tech} well."\n',
    )
    synced = await invoke(["sync"])

    assert synced.exit_code == 0, synced.output
    assert (await _show(invoke, "rust-dev"))["mission"] == "Own the Rust surface."
    assert "Writes Rust well." in _pointer(project, "rust-dev")
