"""``update`` on a skill, a role and an operator edits display fields and nothing that names the
entity.

One table: entity shape by option. Identity (slug, file name, id, the ``.claude`` file set) is
the same before and after; the new value is in the file, in ``show`` and ``show --json`` and in
the regenerated pointer or managed ``CLAUDE.md`` line. Then the pipeline invariants: ``sync``
after an update changes no file, a repair gives the same values, an unwritten body follows the
new title and a written one does not.
"""

import json
import re

import pytest

import _roster_squad
from _helpers import squad_tree
from squads._itemfile import read_frontmatter
from squads._sections import get_section

pytestmark = pytest.mark.anyio

#: shape -> option name -> (flag, new value, frontmatter key, show --json key)
SKILL = {
    "title": ("--title", "Ship Runbook", "title", "title"),
    "desc": ("--desc", "Ship it well.", "description", "description"),
    "when-to-use": ("--when-to-use", "At release time", "when_to_use", "when_to_use"),
}
NAME = {"title": ("--title", "Renamed Holder", "title", "full_name")}

#: shape -> (kind, slug, options)
ROWS = {
    "project skill": ("skill", "release-runbook", SKILL),
    "bundled role": ("role", "manager", NAME),
    "templated developer": ("role", "rust-dev", NAME),
    "project role": ("role", "security-analyst", NAME),
    "retired role": ("role", "devops", NAME),
    "operator": ("operator", "op-ada", {"title": NAME["title"]}),
    "retired operator": ("operator", "op-old", {"title": NAME["title"]}),
}
CELLS = [(shape, opt) for shape, (_k, _s, opts) in ROWS.items() for opt in opts]


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return _roster_squad.build(tmp_path_factory.mktemp("roster"))


@pytest.fixture
def squad(built, tmp_path, monkeypatch, frozen_time):
    dest = _roster_squad.restore(built, tmp_path / "squad")
    monkeypatch.chdir(dest)
    return dest


def _file(squad, kind: str, slug: str):
    root = squad / "squads"
    folder = root / ("operators" if kind == "operator" else f"agents/{kind}s")
    return next(folder.glob(f"*-{slug}.md"))


def _front(path):
    return read_frontmatter(text=path.read_text(encoding="utf-8"), source=path.name)


def _body(squad) -> str:
    text = _file(squad, "skill", "release-runbook").read_text(encoding="utf-8")
    return get_section(text, "body") or ""


def _claude_files(squad) -> list[str]:
    return sorted(
        p.relative_to(squad).as_posix() for p in (squad / ".claude").rglob("*") if p.is_file()
    )


@pytest.mark.parametrize(("shape", "option"), CELLS)
async def test_update_changes_the_value_and_nothing_that_names_the_entity(
    squad, invoke, shape, option
):
    kind, slug, options = ROWS[shape]
    flag, value, key, json_key = options[option]
    path = _file(squad, kind, slug)
    before = _front(path)
    claude = _claude_files(squad)

    result = await invoke([kind, slug, "update", flag, value])

    assert result.exit_code == 0, result.output
    after_path = _file(squad, kind, slug)
    assert after_path == path
    after = _front(after_path)
    assert {k: after[k] for k in ("id", "slug")} == {k: before[k] for k in ("id", "slug")}
    assert after[key] == value
    assert _claude_files(squad) == claude
    shown = json.loads((await invoke([kind, slug, "show", "--json"])).output)
    assert shown["slug"] == slug and shown["id"] == before["id"]
    assert shown[json_key] == value
    plain = await invoke([kind, slug, "show"])
    assert plain.exit_code == 0 and (value in plain.output or (kind == "skill" and key != "title"))
    if kind == "skill" and key == "description":
        pointer = (squad / ".claude" / "skills" / slug / "SKILL.md").read_text(encoding="utf-8")
        assert value in pointer
    if kind == "role" and shape != "retired role":
        pointer = (squad / ".claude" / "agents" / f"{slug}.md").read_text(encoding="utf-8")
        assert f"**{value}**" in pointer
    if kind in ("role", "operator") and shape not in ("retired role", "retired operator"):
        claude_md = (squad / "CLAUDE.md").read_text(encoding="utf-8")
        assert f"**{value}**" in claude_md and f"(`{slug}`)" in claude_md
    check = await invoke(["check"])
    assert check.exit_code == 0, check.output


@pytest.mark.parametrize("shape", list(ROWS))
async def test_update_without_an_option_exits_1_and_writes_nothing(squad, invoke, shape):
    kind, slug, _options = ROWS[shape]
    before = squad_tree(squad)

    result = await invoke([kind, slug, "update"])

    assert result.exit_code == 1, result.output
    assert "nothing to update" in result.output
    expected = "pass --title)" if kind != "skill" else "pass at least one of --title, --desc"
    assert expected in " ".join(result.output.split())
    assert squad_tree(squad) == before


@pytest.mark.parametrize("shape", list(ROWS))
async def test_no_update_takes_a_slug_or_a_set_option(squad, invoke, shape):
    kind, slug, _options = ROWS[shape]
    for flag in ("--slug", "--set"):
        result = await invoke([kind, slug, "update", flag, "x=y"])
        assert result.exit_code == 2, result.output


@pytest.mark.parametrize(("shape", "option"), [c for c in CELLS if c[0] != "retired operator"])
async def test_sync_after_update_and_a_repair_keep_the_value(squad, invoke, shape, option):
    kind, slug, options = ROWS[shape]
    flag, value, key, _json_key = options[option]
    assert (await invoke([kind, slug, "update", flag, value])).exit_code == 0
    synced = await invoke(["sync"])
    assert synced.exit_code == 0, synced.output
    settled = squad_tree(squad)

    again = await invoke(["sync"])
    assert again.exit_code == 0, again.output
    assert squad_tree(squad) == settled
    (squad / "squads" / ".squads.json").unlink()
    rebuilt = await invoke(["repair"])
    assert rebuilt.exit_code == 0, rebuilt.output
    assert _front(_file(squad, kind, slug))[key] == value
    shown = json.loads((await invoke([kind, slug, "show", "--json"])).output)
    assert value in shown.values()


async def test_a_renamed_bundled_role_keeps_its_name_through_sync_and_an_override_name(
    squad, invoke
):
    assert (
        await invoke(["role", "architect", "update", "--title", "Chief Builder"])
    ).exit_code == 0
    override = squad / "squads" / ".overrides" / "roles" / "architect.toml"
    override.write_text(
        override.read_text(encoding="utf-8").replace("Renamed Architect", "Another Name"),
        encoding="utf-8",
    )

    synced = await invoke(["sync"])

    assert synced.exit_code == 0, synced.output
    shown = json.loads((await invoke(["role", "architect", "show", "--json"])).output)
    assert shown["full_name"] == "Chief Builder"
    assert "**Chief Builder**" in (squad / ".claude" / "agents" / "architect.md").read_text(
        encoding="utf-8"
    )


@pytest.mark.parametrize("slug", ["squads", "sq-task"])
async def test_update_on_a_system_skill_is_refused_naming_the_playbook(squad, invoke, slug):
    before = squad_tree(squad)

    result = await invoke(["skill", slug, "update", "--desc", "Mine."])

    assert result.exit_code == 1, result.output
    assert "authoring surface" in result.output and "playbook" in result.output
    assert squad_tree(squad) == before


async def test_an_unwritten_skill_body_follows_the_new_title_and_a_written_one_is_kept(
    squad, invoke
):
    assert (
        await invoke(
            [
                "skill",
                "release-runbook",
                "update",
                "--title",
                "Ship Runbook",
                "--desc",
                "New words.",
            ]
        )
    ).exit_code == 0
    body = _body(squad)
    assert "# Ship Runbook" in body and "New words." in body and "Release Runbook" not in body
    assert (
        await invoke(["skill", "release-runbook", "body", "-m", "Mine, by hand."])
    ).exit_code == 0
    assert (
        await invoke(["skill", "release-runbook", "update", "--title", "Third Name"])
    ).exit_code == 0
    kept = _body(squad)
    assert "Mine, by hand." in kept and "Third Name" not in kept
    assert re.search(
        r"title: Third Name", _file(squad, "skill", "release-runbook").read_text(encoding="utf-8")
    )


@pytest.mark.parametrize(
    ("flag", "value"),
    [("--title", "Ship Runbook"), ("--desc", "New words."), ("--when-to-use", "When shipping.")],
)
async def test_every_skill_option_keeps_an_unwritten_body_unwritten(squad, invoke, flag, value):
    assert (await invoke(["skill", "release-runbook", "update", flag, value])).exit_code == 0

    written = await invoke(["skill", "release-runbook", "body", "-m", "Authored now."])

    assert written.exit_code == 0, written.output
