"""The generated greeting skill reads a registered operator's profile and records one for a new
person through `operator add` then `operator <slug> body --file`; a second sync is a fixed point."""

import hashlib
import re
from pathlib import Path

import pytest

from squads._services import _service as service

pytestmark = pytest.mark.anyio


@pytest.fixture
async def squad(tmp_path, monkeypatch, invoke):
    monkeypatch.chdir(tmp_path)
    await service.init(root=tmp_path, roles_spec="all")
    assert (await invoke(["sync"])).exit_code == 0
    return tmp_path


async def _skill_text(invoke) -> str:
    shown = await invoke(["skill", "greeting", "show", "--raw"])
    assert shown.exit_code == 0, shown.output
    return re.sub(r"\s+", " ", shown.output)


@pytest.mark.parametrize(
    "phrase",
    [
        "sq list -t operator --all",
        "`sq operator <slug> status Active`",
        "Never `operator add` them again",
        "sq operator <slug> show",
        "Its body is their profile",
        "still the default operator text",
        "offer to record one with `sq operator <slug> body`",
        "**ask first** whether to register them",
        "on a no, change nothing",
        'sq operator add "<their name>"',
        "their role on the project, their level of expertise, and what they come to do",
        "sq operator <slug> body --file <path>",
        "`operator add` takes no answers",
        "can't tell who it is, ask",
        "never read the profile back to them",
        "Skip it entirely when you've been spawned as a subagent",
    ],
)
async def test_the_greeting_skill_states_each_profile_step(phrase, squad, invoke) -> None:
    assert phrase in await _skill_text(invoke)


async def test_the_greeting_skill_names_no_profile_option(squad, invoke) -> None:
    assert "--profile" not in await _skill_text(invoke)


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts):
        digest.update(path.relative_to(root).as_posix().encode() + path.read_bytes())
    return digest.hexdigest()


async def test_a_second_sync_changes_no_file_after_a_profile_is_recorded(
    tmp_path, monkeypatch, invoke
) -> None:
    monkeypatch.chdir(tmp_path)
    await service.init(root=tmp_path, roles_spec="all")
    assert (await invoke(["operator", "add", "Alice Tester"])).exit_code == 0
    assert (await invoke(["operator", "op-alice", "body", "-m", "Tech lead."])).exit_code == 0

    assert (await invoke(["sync"])).exit_code == 0
    first = _tree_hash(tmp_path)
    assert (await invoke(["sync"])).exit_code == 0

    assert _tree_hash(tmp_path) == first


@pytest.mark.parametrize(
    ("group", "slug"), [("role", "manager"), ("skill", "greeting"), ("operator", "op-alice")]
)
async def test_the_body_help_states_the_rule_for_every_kind(group, slug, squad, invoke) -> None:
    assert (await invoke(["operator", "add", "Alice Tester"])).exit_code == 0

    helped = await invoke([group, slug, "body", "--help"])

    text = " ".join(helped.output.split())
    assert "a role, a system or per-type skill" in text
    assert "an operator body is never refused" in text
