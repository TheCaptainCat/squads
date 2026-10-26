"""The `body` verb on roles and operators: shape by verb.

Rows are the shapes a roster entry can be in; columns are the four ways to supply a body, each
with and without `--force`. A cell is judged on the bare exit code, the printed text, the file's
bytes on refusal and the body read back through `show`. A role whose view is in `[selected]` is
refused whatever the flag; a role whose view the project dropped and an operator are writable,
with a written body asking for `--force` on a replace only.
"""

import hashlib
from pathlib import Path

import pytest

from squads import __version__
from squads._models import _markers as markers
from squads._sections import replace_section
from squads._services import _service as service

pytestmark = pytest.mark.anyio

_DROPPED = """\
[selected]
items = [
  "epic", "feature", "task", "bug", "decision", "contract", "milestone",
  "review", "role", "skill", "operator",
]
views = ["milestone_rollup", "squads_skill", "memory_skill", "item_skill", "greeting_skill"]
"""

_ROLE_FILE = (
    'full_name = "Sentinel"\ntitle = "security-analyst"\n'
    'description = "A declared role."\nmission = "A declared role."\n'
)

#: how the body is supplied -> (arguments, stdin)
SOURCES = {
    "message": (["-m", "Staff engineer; reviews."], None),
    "file": (["--file", "{file}"], None),
    "stdin": (["--file", "-"], "Staff engineer; reviews.\n"),
    "append": (["-m", "Staff engineer; reviews.", "--append"], None),
}

#: shape -> (kind, slug, what the body is before the write)
SHAPES = {
    "role-in-selected": ("role", "manager", "refused"),
    "role-view-dropped": ("role", "manager", "unwritten"),
    "declared-role-view-dropped": ("role", "security-analyst", "unwritten"),
    "bundled-role-not-activated": ("role", "qa", "inactive"),
    "operator-template": ("operator", "op-alice", "unwritten"),
    "operator-written": ("operator", "op-alice", "written"),
    "operator-renamed-before-first-write": ("operator", "op-alice", "unwritten"),
    "operator-retired": ("operator", "op-alice", "unwritten"),
}

#: shape -> setup commands, run after the squad exists
SETUP = {
    "role-view-dropped": [],
    "operator-written": [["operator", "op-alice", "body", "-m", "Tech lead."]],
    "operator-renamed-before-first-write": [["operator", "op-alice", "update", "--title", "Al"]],
    "operator-retired": [["operator", "op-alice", "status", "Archived"]],
}

DROP_VIEW = {"role-view-dropped", "declared-role-view-dropped"}


def _override(squad_dir: Path, name: str, text: str) -> None:
    path = squad_dir / ".overrides" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# squads:override-base:{__version__}\n{text}", encoding="utf-8")


def _file(paths, kind: str, slug: str) -> Path:
    folder = "roles" if kind == "role" else "operators"
    return next((paths.squad_dir / "agents" / folder).glob(f"*{slug}.md"), None) or next(
        paths.squad_dir.rglob(f"{folder}/*{slug}.md")
    )


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def _build(shape, tmp_path, monkeypatch, frozen_time, invoke):
    monkeypatch.chdir(tmp_path)
    roles = "minimal" if shape == "bundled-role-not-activated" else "all"
    paths = (await service.init(root=tmp_path, roles_spec=roles)).paths
    kind = SHAPES[shape][0]
    if shape.startswith("declared"):
        _override(paths.squad_dir, "roles/security-analyst.toml", _ROLE_FILE)
        role_file = paths.squad_dir / ".overrides" / "roles" / "security-analyst.toml"
        added = await invoke(["role", "add", "security-analyst", "--file", str(role_file)])
        assert added.exit_code == 0
        role_file.unlink()
    if kind == "operator":
        assert (await invoke(["operator", "add", "Alice Tester"])).exit_code == 0
    if shape in DROP_VIEW:
        _override(paths.squad_dir, "workflow.toml", _DROPPED)
        assert (await invoke(["sync"])).exit_code == 0
    for args in SETUP.get(shape, []):
        assert (await invoke(args)).exit_code == 0
    return paths


@pytest.mark.parametrize("force", [False, True], ids=["plain", "force"])
@pytest.mark.parametrize("source", list(SOURCES))
@pytest.mark.parametrize("shape", list(SHAPES))
async def test_the_body_verb_by_shape_source_and_force(
    shape, source, force, tmp_path, monkeypatch, frozen_time, invoke
) -> None:
    paths = await _build(shape, tmp_path, monkeypatch, frozen_time, invoke)
    kind, slug, state = SHAPES[shape]
    body_file = tmp_path / "profile.md"
    body_file.write_text("Staff engineer; reviews.\n", encoding="utf-8")
    source_args, stdin = SOURCES[source]
    args = [kind, slug, "body", *(a.replace("{file}", str(body_file)) for a in source_args)]
    if force:
        args.append("--force")
    path = _file(paths, kind, slug) if state != "inactive" else None
    before = _hash(path) if path else None

    result = await invoke(args, input=stdin)

    append = source == "append"
    refused = state in ("refused", "inactive") or (state == "written" and not append and not force)
    if refused:
        assert result.exit_code == 1, result.output
        if state == "refused":
            assert ".overrides/roles.toml" in result.output
            assert "--force" in result.output and "does not lift" in result.output
            assert f"sq role {slug} view disable role_definition" in " ".join(result.output.split())
        elif state == "inactive":
            assert "activate it first" in result.output
        else:
            assert "already has a body" in result.output
        if path:
            assert _hash(path) == before
        return
    assert result.exit_code == 0, result.output
    assert "body appended" in result.output if append else "body set" in result.output
    shown = await invoke([kind, slug, "show", "--raw"])
    assert "Staff engineer; reviews." in shown.output
    if shape in DROP_VIEW:
        assert path is not None
        # The documented escape converges: disabling the leftover tag leaves a clean squad.
        assert "sq:view:role_definition" in path.read_text(encoding="utf-8")
        assert path.name in (await invoke(["check"])).output
        disabled = await invoke([kind, slug, "view", "disable", "role_definition"])
        assert disabled.exit_code == 0, disabled.output
        assert path.name not in (await invoke(["check"])).output
        reshown = await invoke([kind, slug, "show", "--raw"])
        assert "<!--" not in reshown.output
        assert "Staff engineer; reviews." in reshown.output
        return
    if state == "written":
        assert "Tech lead." in shown.output if append else "Tech lead." not in shown.output


async def test_an_operator_profile_round_trips_and_a_second_write_is_refused(
    project, invoke
) -> None:
    assert (await invoke(["operator", "add", "Alice Tester"])).exit_code == 0
    profile = project.root / "profile.md"
    profile.write_text("Role: tech lead.\nExpertise: senior.\n", encoding="utf-8")

    first = await invoke(["operator", "op-alice", "body", "--file", str(profile)])
    shown = await invoke(["operator", "op-alice", "show"])
    path = _file(project, "operator", "op-alice")
    before = _hash(path)
    second = await invoke(["operator", "op-alice", "body", "-m", "Replacement."])

    assert first.exit_code == 0 and "body set" in first.output
    assert "Role: tech lead." in shown.output and "Expertise: senior." in shown.output
    assert second.exit_code == 1 and "--force" in second.output
    assert _hash(path) == before


async def test_a_prose_role_and_a_profile_pass_check_with_exit_zero(project, invoke) -> None:
    assert (await invoke(["role", "activate", "manager"])).exit_code in (0, 1)
    assert (await invoke(["operator", "add", "Alice Tester"])).exit_code == 0
    assert (await invoke(["operator", "op-alice", "body", "-m", "Tech lead."])).exit_code == 0
    role_path = _file(project, "role", "manager")
    text = role_path.read_text(encoding="utf-8")
    role_path.write_text(
        replace_section(text, markers.BODY, "Runbook prose, no tag."), encoding="utf-8"
    )
    before = _hash(role_path)

    checked = await invoke(["check"])
    repaired = await invoke(["repair"])

    assert checked.exit_code == 0, checked.output
    assert "seeded view tag" not in checked.output
    assert repaired.exit_code == 0 and _hash(role_path) == before
