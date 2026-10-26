"""``sq role <slug> body`` writes prose beside the definition on every role kind; the prose shows
in ``sq role <slug> show`` and ``sq show <id> --json`` and in no generated surface."""

import json

import pytest

from squads._services import _service as service

pytestmark = pytest.mark.anyio

LINE = "distinctive-prose-line-4711"


@pytest.fixture
async def squad(tmp_path, monkeypatch, frozen_time, invoke):
    monkeypatch.chdir(tmp_path)
    paths = (await service.init(root=tmp_path, roles_spec="all")).paths
    for args in (
        ["dev", "add", "--tech", "rust"],
        [
            "role",
            "add",
            "security-analyst",
            "--name",
            "Sentinel",
            "--job-title",
            "Security analyst",
            "--desc",
            "Reviews threats.",
            "--mission",
            "Keep it safe.",
        ],
    ):
        result = await invoke(args)
        assert result.exit_code == 0, result.output
    return paths


@pytest.mark.parametrize("slug", ["tech-lead", "rust-dev", "security-analyst"])
async def test_a_role_body_verb_writes_and_the_prose_follows_the_definition(
    squad, invoke, slug
) -> None:
    written = await invoke(["role", slug, "body", "-m", LINE])
    assert written.exit_code == 0, written.output
    again = await invoke(["role", slug, "body", "-m", "second"])
    assert again.exit_code == 1
    appended = await invoke(["role", slug, "body", "-m", "More.", "--append"])
    assert appended.exit_code == 0, appended.output
    forced = await invoke(["role", slug, "body", "-m", LINE, "--force"])
    assert forced.exit_code == 0, forced.output

    shown = await invoke(["role", slug, "show"])
    assert shown.exit_code == 0, shown.output
    assert shown.output.index("## Working agreements") < shown.output.index(LINE)
    assert shown.output.index("# ") < shown.output.index(LINE)

    card = await invoke(["role", slug, "show", "--json"])
    assert LINE not in card.output
    synced = await invoke(["sync"])
    assert synced.exit_code == 0, synced.output
    for name in [*squad.root.glob(".claude/agents/*.md"), squad.root / "CLAUDE.md"]:
        assert LINE not in name.read_text(encoding="utf-8")
    agents_md = squad.root / "AGENTS.md"
    assert not agents_md.exists() or LINE not in agents_md.read_text(encoding="utf-8")

    item = json.loads((await invoke(["role", slug, "show", "--json"])).output)
    assert item  # the card still renders
    raw = await invoke(["show", _role_id(squad, slug), "--json"])
    assert LINE in json.loads(raw.output)["body"]
    assert "<!-- sq:view:role_definition -->" in json.loads(raw.output)["body"]

    checked = await invoke(["check"])
    assert checked.exit_code == 0, checked.output


def _role_id(squad, slug: str) -> str:
    path = next((squad.squad_dir / "agents" / "roles").glob(f"*-{slug}.md"))
    text = path.read_text(encoding="utf-8")
    return next(line.split(": ")[1] for line in text.splitlines() if line.startswith("id: "))


async def test_clearing_a_roles_prose_keeps_its_tag(squad, invoke) -> None:
    await invoke(["role", "tech-lead", "body", "-m", LINE])
    refused = await invoke(["role", "tech-lead", "body", "-m", ""])
    assert refused.exit_code == 1
    cleared = await invoke(["role", "tech-lead", "body", "-m", "", "--force"])
    assert cleared.exit_code == 0, cleared.output

    shown = await invoke(["role", "tech-lead", "show"])
    assert LINE not in shown.output
    assert "## Working agreements" in shown.output
