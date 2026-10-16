"""A stored attribute value that fails its declared kind is reported by ``sq check`` and left
exactly as written; ``--set`` and ``sq import`` refuse an invalid value before writing. One table
over the value shapes crosses load, ``sq check`` with and without the opt-in undeclared-key check,
``sq update --set`` and ``sq import``, and every cell asserts that the file is byte-identical
afterwards."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from _helpers import create_item
from squads import __version__
from squads._rendering._engine import invalidate_squad_dir
from squads._sections import replace_frontmatter, split_frontmatter
from squads._services._service import Service
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio

_OVERRIDE = """\
[items.guide.attributes]
weight = { kind = "bool" }
owner = { kind = "str", required = true }
"""

_OPT_IN = """
[items.guide]
validators = ["frontmatter_key_undeclared"]
"""


@dataclass(frozen=True)
class Shape:
    """One value shape: the frontmatter keys it sets, what each surface must answer for it."""

    id: str
    stored: dict[str, Any]
    reported: str | None  # the sq check error fragment (default bundle), None = silent
    reported_with_opt_in: str | None  # the extra warn fragment the opt-in adds
    refused_input: tuple[str, str] | None  # (key, raw value) --set and import must refuse


_OWNED = {"owner": "pat"}

SHAPES = [
    Shape("valid", {**_OWNED, "tech": "go", "tags": ["a"], "weight": True}, None, None, None),
    Shape("str-kind-holds-a-list", {**_OWNED, "tech": ["go"]}, "attribute 'tech'", None, None),
    Shape("list-kind-holds-a-string", {**_OWNED, "tags": "a,b"}, "attribute 'tags'", None, None),
    Shape(
        "bool-kind-holds-a-string",
        {**_OWNED, "weight": "heavy"},
        "attribute 'weight'",
        None,
        ("weight", "heavy"),
    ),
    Shape(
        "list-kind-holds-a-mapping", {**_OWNED, "tags": {"a": 1}}, "attribute 'tags'", None, None
    ),
    Shape("missing-required", {"tech": "go"}, "missing required attribute 'owner'", None, None),
    Shape("undeclared-typo", {**_OWNED, "tagz": ["a"]}, None, "frontmatter key 'tagz'", None),
]


def _guide_file(svc: Service, item: Any) -> Path:
    return svc.paths.abspath(item.path)


async def _prepared(
    project: Any, shape: Shape, *, opt_in: bool
) -> tuple[Service, Any, Path, bytes]:
    overrides = project.squad_dir / ".overrides"
    overrides.mkdir(exist_ok=True)
    (overrides / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n" + _OVERRIDE + (_OPT_IN if opt_in else ""),
        encoding="utf-8",
    )
    invalidate_squad_dir(project.squad_dir)
    svc = Service(project, spec=load_workflow_spec(squad_dir=project.squad_dir))
    item = (await create_item(svc, "guide", "A guide")).item
    path = _guide_file(svc, item)
    text = path.read_text(encoding="utf-8")
    data, _ = split_frontmatter(text)
    for key in ("owner", "tech", "tags", "weight"):
        data.pop(key, None)
    data.update(shape.stored)
    path.write_text(replace_frontmatter(text, data), encoding="utf-8")
    await svc.repair()
    return svc, item, path, path.read_bytes()


@pytest.mark.parametrize("shape", SHAPES, ids=[s.id for s in SHAPES])
async def test_load_keeps_the_value_and_check_reports_it_without_changing_the_file(
    project, shape: Shape
) -> None:
    svc, item, path, before = await _prepared(project, shape, opt_in=False)

    loaded = await svc.get(item.id)
    issues = [i for i in await svc.check() if i.item == item.id]

    for key, value in shape.stored.items():
        assert loaded.attributes[key] == value
    errors = [i for i in issues if i.level == "error"]
    if shape.reported is None:
        assert errors == []
        assert [i for i in issues if "frontmatter key" in i.message] == []
    else:
        assert len(errors) == 1
        assert shape.reported in errors[0].message
    assert path.read_bytes() == before


@pytest.mark.parametrize("shape", SHAPES, ids=[s.id for s in SHAPES])
async def test_the_opt_in_check_reports_an_undeclared_key_at_warn_and_never_rewrites(
    project, shape: Shape
) -> None:
    svc, item, path, before = await _prepared(project, shape, opt_in=True)

    issues = [i for i in await svc.check() if i.item == item.id]

    warned = [i for i in issues if "frontmatter key" in i.message]
    if shape.reported_with_opt_in is None:
        assert warned == []
    else:
        assert [w.level for w in warned] == ["warn"]
        assert shape.reported_with_opt_in in warned[0].message
    assert path.read_bytes() == before


@pytest.mark.parametrize("shape", [s for s in SHAPES if s.refused_input], ids=lambda s: s.id)
async def test_set_and_import_refuse_an_invalid_value_before_writing(
    project, invoke, tmp_path: Path, shape: Shape
) -> None:
    _svc, item, path, before = await _prepared(project, shape, opt_in=False)
    assert shape.refused_input is not None
    key, raw = shape.refused_input

    via_set = await invoke(["guide", str(item.sequence_id), "update", "--set", f"{key}={raw}"])
    events = tmp_path / "update.jsonl"
    events.write_text(
        json.dumps({"op": "update", "target": item.id, "as": "manager", "fields": {key: raw}})
        + "\n",
        encoding="utf-8",
    )
    via_import = await invoke(["import", str(events)])

    assert via_set.exit_code == 1
    assert key in via_set.output
    assert via_import.exit_code == 1
    assert key in via_import.output
    assert path.read_bytes() == before


#: (kind, valid raw value, the value stored): the same two doors accept a valid value of each kind.
VALID_INPUTS = [
    ("str", "tech", "rust", "rust"),
    ("list", "tags", "x, y", ["x", "y"]),
    ("bool", "weight", "true", True),
]


@pytest.mark.parametrize(
    ("key", "raw", "stored"), [v[1:] for v in VALID_INPUTS], ids=[v[0] for v in VALID_INPUTS]
)
async def test_set_and_import_write_a_valid_value_of_every_kind(
    project, invoke, tmp_path: Path, key: str, raw: str, stored: Any
) -> None:
    svc, item, _path, _ = await _prepared(project, SHAPES[0], opt_in=False)

    via_set = await invoke(["guide", str(item.sequence_id), "update", "--set", f"{key}={raw}"])
    assert via_set.exit_code == 0, via_set.output
    assert (await svc.get(item.id)).attributes[key] == stored

    await invoke(["guide", str(item.sequence_id), "update", "--unset", key])
    events = tmp_path / "update.jsonl"
    events.write_text(
        json.dumps({"op": "update", "target": item.id, "as": "manager", "fields": {key: raw}})
        + "\n",
        encoding="utf-8",
    )
    via_import = await invoke(["import", str(events)])
    assert via_import.exit_code == 0, via_import.output
    assert (await svc.get(item.id)).attributes[key] == stored
