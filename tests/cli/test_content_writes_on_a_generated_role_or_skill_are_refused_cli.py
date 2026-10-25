"""Every content-changing write on a role or skill whose body is generated is refused, through
the classification the body refusal already uses; lifecycle and comment verbs stay open.

One table: shape by verb. A refusal is exit 1, an error naming the authoring surface, and the
file's bytes unchanged; `--force` changes nothing. A role is refused whatever its origin and keeps
its name (title) writable; a skill is refused exactly when its body is generated, so a system skill
whose view or type the project dropped is writable again and still shows origin system.
"""

import ast
import json
from collections.abc import Callable
from pathlib import Path

import pytest

from squads import __version__
from squads._services import _service as service

pytestmark = pytest.mark.anyio

_ROLE_FILE = (
    'full_name = "{name}"\ntitle = "{slug}"\n'
    'description = "A declared role."\nmission = "A declared role."\n'
)

#: Drops the guide type and the greeting skill's view.
_WORKFLOW = """\
[selected]
items = [
  "epic", "feature", "task", "bug", "decision", "contract", "milestone",
  "review", "role", "skill", "operator",
]
views = ["milestone_rollup", "role_definition", "squads_skill", "memory_skill", "item_skill"]

[items.role.attributes]
shift = { kind = "str" }

[items.skill.attributes]
shift = { kind = "str" }
"""

#: shape -> (kind, slug, view the host renders through, whether its body is generated)
SHAPES: dict[str, tuple[str, str, str, bool]] = {
    "bundled-role": ("role", "manager", "role_definition", True),
    "templated-developer": ("role", "rust-dev", "role_definition", True),
    "project-declared-role": ("role", "security-analyst", "role_definition", True),
    "bundled-skill": ("skill", "squads", "squads_skill", True),
    "generated-skill": ("skill", "sq-task", "item_skill", True),
    "skill-whose-view-is-dropped": ("skill", "greeting", "greeting_skill", False),
    "skill-of-a-dropped-type": ("skill", "sq-guide", "item_skill", False),
    "project-skill": ("skill", "release-runbook", "item_skill", False),
}

VERBS = [
    "update-title",
    "update-description",
    "update-field",
    "update-project-attribute",
    "update-project-and-pinned-attribute",
    "update-title-and-description",
    "body",
    "body-force",
    "body-append",
    "view-disable",
    "view-add",
    "view-add-foreign",
    "update-labels",
    "update-assignee",
    "update-priority",
    "comment",
    "status",
]


def _override(squad_dir: Path, name: str, text: str) -> None:
    path = squad_dir / ".overrides" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# squads:override-base:{__version__}\n{text}", encoding="utf-8")


@pytest.fixture
async def squad(tmp_path, monkeypatch, frozen_time, invoke):
    monkeypatch.chdir(tmp_path)
    paths = (await service.init(root=tmp_path, roles_spec="all")).paths
    squad_dir = paths.squad_dir
    _override(
        squad_dir,
        "roles/security-analyst.toml",
        _ROLE_FILE.format(name="Sentinel", slug="security-analyst"),
    )
    for args in (
        ["dev", "add", "--tech", "rust"],
        ["role", "activate", "security-analyst"],
        ["skill", "add", "Release Runbook", "--desc", "Ship it."],
    ):
        result = await invoke(args)
        assert result.exit_code == 0, result.output
    _override(squad_dir, "workflow.toml", _WORKFLOW)
    result = await invoke(["sync"])
    assert result.exit_code == 0, result.output
    return paths


def _file(squad, kind: str, slug: str) -> Path:
    folder = "roles" if kind == "role" else "skills"
    return next((squad.squad_dir / "agents" / folder).glob(f"*-{slug}.md"))


def _import(squad, event: dict[str, object]) -> list[str]:
    path = squad.root / "event.jsonl"
    path.write_text(json.dumps({"as": "manager", **event}) + "\n", encoding="utf-8")
    return ["import", str(path)]


async def _item_id(squad, kind: str, slug: str) -> str:
    text = _file(squad, kind, slug).read_text(encoding="utf-8")
    return next(line.split(": ")[1] for line in text.splitlines() if line.startswith("id: "))


async def _args(squad, verb: str, kind: str, slug: str, view: str) -> list[str]:
    target = await _item_id(squad, kind, slug)

    def event(**fields: object) -> list[str]:
        return _import(squad, {"target": target, **fields})

    table: dict[str, Callable[[], list[str]]] = {
        "update-title": lambda: event(op="update", title="A New Name"),
        "update-description": lambda: event(op="update", description="New words."),
        "update-field": lambda: event(op="update", fields={"model": "opus"}),
        "update-project-attribute": lambda: event(op="update", fields={"shift": "night"}),
        "update-project-and-pinned-attribute": lambda: event(
            op="update", fields={"shift": "night", "model": "opus"}
        ),
        "update-title-and-description": lambda: event(
            op="update", title="A New Name", description="New words."
        ),
        "body": lambda: event(op="body", body="Hand written."),
        "body-force": lambda: (
            ["skill", slug, "body", "-m", "Hand written.", "--force"]
            if kind == "skill"
            else event(op="body", body="Forced.")
        ),
        "body-append": lambda: event(op="body", body="More.", append=True),
        "view-disable": lambda: [kind, slug, "view", "disable", view],
        "view-add": lambda: [kind, slug, "view", "add", view],
        "view-add-foreign": lambda: [kind, slug, "view", "add", "milestone_rollup"],
        "update-labels": lambda: event(op="update", add_labels=["oncall"]),
        "update-assignee": lambda: event(op="update", assignee="manager"),
        "update-priority": lambda: event(op="update", priority="high"),
        "comment": lambda: event(op="comment", messages=["A note."]),
        "status": lambda: [kind, slug, "status", "Archived"],
    }
    return table[verb]()


def _body(raw: bytes) -> bytes:
    """The bytes of the file's body region."""
    text = raw.decode("utf-8")
    return text[text.index("<!-- sq:body -->") : text.index("<!-- sq:body:end -->")].encode()


def _refused(verb: str, kind: str, generated: bool) -> bool:
    """Whether the table expects the verb refused on a host of this kind."""
    if not generated:
        return False
    if verb == "update-title":
        return kind == "skill"
    return verb in {
        "update-description",
        "update-field",
        "update-project-and-pinned-attribute",
        "update-title-and-description",
        "body",
        "body-force",
        "body-append",
        "view-disable",
        "view-add-foreign",
    }


@pytest.mark.parametrize("verb", VERBS)
@pytest.mark.parametrize("shape", list(SHAPES))
async def test_a_generated_host_refuses_content_verbs_and_keeps_the_open_ones(
    shape, verb, squad, invoke
) -> None:
    kind, slug, view, generated = SHAPES[shape]
    path = _file(squad, kind, slug)
    before = path.read_bytes()
    args = await _args(squad, verb, kind, slug, view)

    result = await invoke(args)

    if _refused(verb, kind, generated):
        assert result.exit_code == 1, result.output
        assert "authoring surface" in result.output
        assert path.read_bytes() == before
    else:
        assert "authoring surface" not in result.output, result.output
        tag_only = verb == "update-title" and shape in (
            "skill-whose-view-is-dropped",
            "skill-of-a-dropped-type",
        )
        if tag_only or verb in ("update-labels", "update-assignee", "update-project-attribute"):
            assert result.exit_code == 0, result.output
            assert _body(path.read_bytes()) == _body(before)
        if verb in (
            "update-title",
            "update-description",
            "update-project-attribute",
            "body",
            "update-labels",
            "update-assignee",
        ):
            assert result.exit_code == 0, result.output


@pytest.mark.parametrize("shape", [s for s, row in SHAPES.items() if row[0] == "skill"])
async def test_a_skills_origin_and_refusal_agree_except_where_the_view_or_type_is_dropped(
    shape, squad, invoke
) -> None:
    kind, slug, _view, generated = SHAPES[shape]
    shown = await invoke([kind, slug, "show", "--json"])
    origin = json.loads(shown.output)["origin"]
    dropped = shape in ("skill-whose-view-is-dropped", "skill-of-a-dropped-type")

    assert (origin == "system") == (generated or dropped)


def test_the_exempt_fields_are_the_declared_set_and_nothing_broader() -> None:
    from squads._services._base import ROSTER_UPDATE_EXEMPT

    assert {k: set(v) for k, v in ROSTER_UPDATE_EXEMPT.items()} == {
        "role": {"title"},
        "skill": set(),
    }


def test_only_the_gate_asks_the_classification_for_a_write() -> None:
    """No verb carries its own membership test: the classification is asked in the shared gate
    and in the places that read it for the file checks, the view mechanics and the migration."""
    root = Path(__file__).parents[2] / "src" / "squads"
    callers: dict[str, int] = {}
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        count = sum(
            1
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and (
                getattr(node.func, "attr", None) == "roster_body_view_name"
                or getattr(node.func, "id", None) == "roster_body_view_name"
            )
        )
        if count:
            callers[path.relative_to(root).as_posix()] = count

    assert callers == {
        "_views.py": 1,
        "_services/_base.py": 1,
        "_services/_maintenance.py": 2,
        "_migrations/_v0_14_to_v0_15.py": 1,
    }
