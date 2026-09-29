"""A ``self`` view's ``--json`` ``spec`` block carries a digest of the merged workflow spec:
it changes exactly when the merged spec changes, and stays put for edits that leave the merge
unchanged."""

import json
import re
from pathlib import Path
from typing import Any

import pytest

from squads import __version__
from squads._overrides._service import scaffold_playbook, scaffold_role
from squads._rendering._engine import invalidate_squad_dir

pytestmark = pytest.mark.anyio

_SELF_VIEW = '[views.self_card]\nsource = { kind = "self" }\n'


def _workflow(squad_dir: Path, body: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{_SELF_VIEW}{body}", encoding="utf-8"
    )
    invalidate_squad_dir(squad_dir)


async def _spec_block(project, invoke) -> dict[str, Any]:
    created = await invoke(["create", "task", "A task", "--author", "manager"])
    task_id = created.output.split("→")[0].removeprefix("created").strip()
    result = await invoke(["workflow", "view", "self_card", task_id, "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)["spec"]


def _badge(value: str) -> str:
    return f'[statuses.Draft]\nbadge = "{value}"\n'


async def test_block_shape_is_schema_version_override_and_a_sha256_digest(project, invoke):
    _workflow(project.squad_dir, "")

    block = await _spec_block(project, invoke)

    assert set(block) == {"schema_version", "override", "digest"}
    assert block["override"] is True
    assert re.fullmatch(r"[0-9a-f]{64}", block["digest"])


# (label_a, body_a, label_b, body_b, same_digest)
_PAIRS = [
    pytest.param(_badge("A"), _badge("Z"), False, id="same-keys-different-values"),
    pytest.param("", _badge("A"), False, id="none-vs-a-badge-override"),
    pytest.param(
        _badge("A"),
        "# a comment\n\n[statuses.Draft]\n\nbadge   =   'A'   # trailing\n",
        True,
        id="reformatted-same-merge",
    ),
]


@pytest.mark.parametrize(("body_a", "body_b", "same"), _PAIRS)
async def test_digest_follows_the_merged_spec(project, invoke, body_a, body_b, same):
    _workflow(project.squad_dir, body_a)
    first = await _spec_block(project, invoke)
    _workflow(project.squad_dir, body_b)
    second = await _spec_block(project, invoke)

    assert (first["digest"] == second["digest"]) is same


@pytest.mark.parametrize(
    "extra_override",
    [
        pytest.param(lambda d: scaffold_playbook(d), id="playbook-only"),
        pytest.param(lambda d: scaffold_role(d, "manager"), id="roles-only"),
    ],
)
async def test_playbook_and_role_overrides_leave_the_digest_alone(project, invoke, extra_override):
    _workflow(project.squad_dir, _badge("A"))
    before = await _spec_block(project, invoke)
    extra_override(project.squad_dir)
    invalidate_squad_dir(project.squad_dir)

    after = await _spec_block(project, invoke)

    assert after["digest"] == before["digest"]


async def test_two_runs_on_one_squad_give_identical_blocks(project, invoke):
    _workflow(project.squad_dir, _badge("A"))

    assert await _spec_block(project, invoke) == await _spec_block(project, invoke)


async def test_a_rejected_document_refuses_the_command_and_yields_no_digest(project, invoke):
    _workflow(project.squad_dir, "[statuses.Draft]\nnot_a_key = 1\n")

    result = await invoke(["workflow", "view", "self_card", "TASK-1", "--json"])

    assert result.exit_code != 0
    assert "digest" not in result.output
