"""``sq migrate up`` from schema 0.16 moves each role onto the base that now defines it: a
developer stores its template, a custom role defined only by a per-slug file takes that
definition into its item (the file is left alone), a catalog or template role stores no
description, a role without ``tech`` stores no mirrored model, and a role whose file does not
load or that nothing backs is reported and never guessed. A ``[dev]`` table in the role catalog
override stops the run before it changes anything.

One table of role shapes; each row builds a role in the 0.17 shape, rewrites its item to the 0.16
shape, migrates, and compares.
"""

import hashlib
import json
import tomllib
from pathlib import Path

import pytest

from squads._itemfile import read_frontmatter
from squads._sections import replace_frontmatter

pytestmark = pytest.mark.anyio

_ADD = ["--name", "Sam Sre", "--job-title", "SRE", "--desc", "Keeps it up.", "--mission", "Run it."]
_DEFINITION_KEYS = (
    "job_title",
    "mission",
    "responsibilities",
    "agreements",
    "color",
    "can_spawn",
    "capabilities",
)
_FILE = (
    'full_name = "Sam Sre"\ntitle = "SRE"\ndescription = "Keeps it up."\nmission = "Run it."\n'
    'capabilities = ["ops"]\nmodel = "haiku"\n'
)


def _role_path(project, slug: str) -> Path:
    return next((project.squad_dir / "agents" / "roles").glob(f"*-{slug}.md"))


def _front(project, slug: str) -> dict[str, object]:
    return read_frontmatter(path=_role_path(project, slug))


def _rewrite(project, slug: str, *, drop=(), **put) -> None:
    """Put the role's item into the 0.16 shape: *drop* keys removed, *put* keys written."""
    path = _role_path(project, slug)
    text = path.read_text(encoding="utf-8")
    data = read_frontmatter(text=text, source=str(path))
    for key in drop:
        data.pop(key, None)
    data.update(put)
    path.write_text(replace_frontmatter(text, data, source=str(path)), encoding="utf-8")


def _stamp_back(project) -> None:
    config = project.root / ".squads.toml"
    config.write_text(
        config.read_text(encoding="utf-8").replace('"0.17"', '"0.16"'), encoding="utf-8"
    )


def _hashes(project) -> dict[str, str]:
    return {
        str(p.relative_to(project.root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(project.root.rglob("*"))
        if p.is_file() and ".git" not in p.parts and p.name != ".reflog.jsonl"
    }


def _write(project, relative: str, body: str) -> Path:
    path = project.squad_dir / ".overrides" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


async def _show(invoke, slug: str) -> dict[str, object]:
    result = await invoke(["role", slug, "show", "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


async def _migrate(project, invoke):
    _stamp_back(project)
    result = await invoke(["migrate", "up"])
    assert result.exit_code == 0, result.output
    return result


async def test_a_file_only_custom_role_takes_the_files_definition_into_its_item(
    project, invoke
) -> None:
    assert (await invoke(["role", "add", "sre", *_ADD, "--capabilities", "ops"])).exit_code == 0
    file = _write(project, "roles/sre.toml", _FILE)
    before = await _show(invoke, "sre")
    _rewrite(project, "sre", drop=(*_DEFINITION_KEYS, "model"), model="opus", description="old")
    file_hash = hashlib.sha256(file.read_bytes()).hexdigest()

    await _migrate(project, invoke)

    front = _front(project, "sre")
    assert (front["job_title"], front["mission"], front["description"]) == (
        "SRE",
        "Run it.",
        "Keeps it up.",
    )
    assert front["capabilities"] == ["ops"] and front["model"] == "haiku"
    assert front["title"] == "Sam Sre"
    assert hashlib.sha256(file.read_bytes()).hexdigest() == file_hash
    after = await _show(invoke, "sre")
    assert {k: after[k] for k in before if k != "skills"} == {
        k: before[k] for k in before if k != "skills"
    } | {"model": "haiku"}


async def test_a_developer_stores_its_template_keeps_its_model_and_loses_its_description(
    project, invoke
) -> None:
    assert (await invoke(["dev", "add", "--tech", "go", "--model", "opus"])).exit_code == 0
    _rewrite(project, "go-dev", drop=("template",), description="Implement tasks in Go.")

    await _migrate(project, invoke)

    front = _front(project, "go-dev")
    assert front["template"] == "dev" and front["tech"] == "go" and front["model"] == "opus"
    assert "description" not in front
    assert (await _show(invoke, "go-dev"))["capabilities"] == ["dev"]


async def test_a_catalog_role_loses_its_description_and_its_mirrored_model(project, invoke) -> None:
    assert (await invoke(["role", "activate", "reviewer"])).exit_code == 0
    _rewrite(project, "reviewer", description="Guard quality.", model="opus")

    await _migrate(project, invoke)

    front = _front(project, "reviewer")
    assert "description" not in front and "model" not in front and "mission" not in front


#: (id, how the role is made, the slug)
OPERATOR_MODELS = [
    ("a-catalog-role", ["role", "activate", "reviewer"], "reviewer"),
    ("an-orphan", ["role", "add", "ghost", *_ADD], "ghost"),
]


@pytest.mark.parametrize(
    ("setup", "slug"), [r[1:] for r in OPERATOR_MODELS], ids=[r[0] for r in OPERATOR_MODELS]
)
async def test_applying_the_step_again_keeps_a_model_the_operator_set_at_the_current_schema(
    project, invoke, setup: list[str], slug: str
) -> None:
    assert (await invoke(setup)).exit_code == 0
    if slug == "ghost":
        _rewrite(project, slug, drop=_DEFINITION_KEYS)
        assert (await invoke(["repair"])).exit_code == 0
    assert (await invoke(["role", slug, "update", "--model", "haiku"])).exit_code == 0
    before = _front(project, slug)

    result = await _migrate(project, invoke)

    assert _front(project, slug)["model"] == "haiku"
    assert "kept" in " ".join(result.output.split()) and "haiku" in result.output
    if slug == "reviewer":
        assert _front(project, slug).get("description") == before.get("description")


async def test_a_role_from_the_project_catalog_is_a_catalog_base_and_is_not_migrated(
    project, invoke
) -> None:
    _write(
        project,
        "roles.toml",
        '[bundles]\nall = ["manager", "architect", "tech-lead", "reviewer", "qa", "devops", '
        '"product-owner", "tech-writer", "ops"]\n\n[[roles]]\nslug = "ops"\n'
        'full_name = "Olga Ops"\ntitle = "ops"\ndescription = "Ops."\nmission = "Run ops."\n',
    )
    assert (await invoke(["role", "activate", "ops"])).exit_code == 0
    _rewrite(project, "ops", description="Run ops.")

    await _migrate(project, invoke)

    front = _front(project, "ops")
    assert "mission" not in front and "job_title" not in front and "description" not in front


@pytest.mark.parametrize(
    ("file_body", "fragment"),
    [
        (
            'full_name = "Gwen"\n',
            "does not load as a complete role (the file for 'ghost' is a layer with no base",
        ),
        (None, "no catalog entry and no role file"),
    ],
    ids=["a-broken-file", "an-orphan"],
)
async def test_a_broken_file_and_an_orphan_are_reported_and_left_as_they_were(
    project, invoke, file_body: str | None, fragment: str
) -> None:
    assert (await invoke(["role", "add", "ghost", *_ADD])).exit_code == 0
    file = _write(project, "roles/ghost.toml", file_body) if file_body else None
    _rewrite(project, "ghost", drop=(*_DEFINITION_KEYS, "model"), description="Old words.")
    file_hash = hashlib.sha256(file.read_bytes()).hexdigest() if file else None

    result = await _migrate(project, invoke)

    front = _front(project, "ghost")
    flat = " ".join(result.output.split())
    assert fragment in flat
    assert "new slug" not in flat
    assert "ghost:" in result.output
    assert "mission" not in front and front["description"] == "Old words."
    if file:
        assert hashlib.sha256(file.read_bytes()).hexdigest() == file_hash


@pytest.mark.parametrize(
    "setup",
    ["file-only", "developer", "catalog", "orphan"],
)
async def test_a_repair_after_the_run_rebuilds_the_same_index_and_a_second_run_changes_nothing(
    project, invoke, setup: str
) -> None:
    if setup == "file-only":
        assert (await invoke(["role", "add", "sre", *_ADD])).exit_code == 0
        _write(project, "roles/sre.toml", _FILE)
        _rewrite(project, "sre", drop=_DEFINITION_KEYS)
    elif setup == "developer":
        assert (await invoke(["dev", "add", "--tech", "go"])).exit_code == 0
        _rewrite(project, "go-dev", drop=("template",), description="Old.")
    elif setup == "catalog":
        assert (await invoke(["role", "activate", "qa"])).exit_code == 0
        _rewrite(project, "qa", description="Old.", model="haiku")
    else:
        assert (await invoke(["role", "add", "ghost", *_ADD])).exit_code == 0
        _rewrite(project, "ghost", drop=_DEFINITION_KEYS)
    await _migrate(project, invoke)
    index = (project.squad_dir / ".squads.json").read_text(encoding="utf-8")
    migrated = _hashes(project)

    assert (await invoke(["repair"])).exit_code == 0
    _stamp_back(project)
    again = await invoke(["migrate", "up"])

    assert again.exit_code == 0, again.output
    after = _hashes(project)
    assert {k: v for k, v in after.items() if k != ".squads.toml"} == {
        k: v for k, v in migrated.items() if k != ".squads.toml"
    }
    assert json.loads((project.squad_dir / ".squads.json").read_text(encoding="utf-8")) == (
        json.loads(index)
    )


async def test_a_legacy_dev_table_stops_the_run_before_it_changes_anything(project, invoke) -> None:
    assert (await invoke(["dev", "add", "--tech", "go"])).exit_code == 0
    _rewrite(project, "go-dev", drop=("template",), description="Old.")
    _write(project, "roles.toml", '[dev]\nmodel = "opus"\n')
    _stamp_back(project)
    before = _hashes(project)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 1, result.output
    message = " ".join(result.output.split())
    assert "[dev] is not a key of the role catalog; rename it to [templates.dev]" in message
    assert "Nothing was changed" in message
    assert _hashes(project) == before
    assert (
        tomllib.loads((project.root / ".squads.toml").read_text(encoding="utf-8"))["schema_version"]
        == "0.16"
    )
