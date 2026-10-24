"""``working_language`` in ``.squads.toml`` through the commands: ``init`` and ``adopt`` write it,
every command validates it, the managed sections of both backends and the ``squads`` skill render
it, ``sq sync`` refreshes them and keeps the line as written, and ``sq check`` reports a value that
is not a language tag. A value that is not a language tag is never an error: one warning on
stderr, English applies, ``--json`` stdout stays parseable."""

import json
from typing import Any

import pytest

from squads._services import _service as service
from squads._services._service import Service

pytestmark = pytest.mark.anyio

ENGLISH = "**English** (`en`)"
# (id, text of the key's line or None for absent, rule rendered, whether it is not a tag)
CONTENTS: list[tuple[str, str | None, str, bool]] = [
    ("absent", None, ENGLISH, False),
    ("french", 'working_language = "fr"', "**French** (`fr`)", False),
    ("regional", 'working_language = "pt-br"', "**Portuguese (Brazil)** (`pt-br`)", False),
    ("underscore-form", 'working_language = "fr_FR"', ENGLISH, True),
    ("unknown-code", 'working_language = "tlh"', ENGLISH, True),
    ("number", "working_language = 5", ENGLISH, True),
]
_IDS = [c[0] for c in CONTENTS]


def _write_config(svc: Service, line: str | None) -> str:
    """The config with both backends and *line* as its key, or none; returns it."""
    path = svc.paths.config_path
    text = path.read_text(encoding="utf-8").replace('working_language = "en"\n', "")
    text = text.replace(
        'active_backends = ["claude_code"]', 'active_backends = ["claude_code", "agents_md"]'
    )
    if line is not None:
        text = text.replace('"agents_md"]\n', f'"agents_md"]\n{line}\n', 1)
    path.write_text(text, encoding="utf-8")
    return text


@pytest.mark.parametrize(("case", "line", "rule", "bad"), CONTENTS, ids=_IDS)
async def test_the_commands_validate_render_and_keep_the_working_language(
    svc: Service, invoke: Any, case: str, line: str | None, rule: str, bad: bool
) -> None:
    written = _write_config(svc, line)

    synced = await invoke(["sync"])
    listed = await invoke(["list"])
    as_json = await invoke(["list", "--json"])
    skill = await invoke(["skill", "squads", "show"])
    checked = await invoke(["check"])

    assert synced.exit_code == 0, synced.output
    config = svc.paths.config_path.read_text(encoding="utf-8")
    # A sync keeps the line as written, and never adds one.
    assert config == written
    root = svc.paths.root
    for managed in (root / "CLAUDE.md", root / "AGENTS.md"):
        assert rule in managed.read_text(encoding="utf-8")
    assert rule in skill.output
    # Only a value that is not a tag is reported: one warning per command, one check finding.
    assert listed.exit_code == 0
    assert (listed.stderr.count("warning:") == 1) is bad
    assert "working_language" not in listed.stdout
    assert json.loads(as_json.stdout) is not None
    assert checked.exit_code == 0, checked.output
    findings = [ln for ln in checked.stdout.splitlines() if "working_language" in ln]
    assert len(findings) == (1 if bad else 0)


async def test_changing_the_key_and_syncing_again_renders_the_new_language(
    svc: Service, invoke: Any
) -> None:
    _write_config(svc, 'working_language = "fr"')
    await invoke(["sync"])
    path = svc.paths.config_path
    path.write_text(path.read_text(encoding="utf-8").replace('"fr"', '"de"'), encoding="utf-8")

    await invoke(["sync"])
    skill = await invoke(["skill", "squads", "show"])

    assert "**German** (`de`)" in (svc.paths.root / "CLAUDE.md").read_text(encoding="utf-8")
    assert "**German** (`de`)" in skill.output


async def test_init_writes_english_and_adopt_writes_it_only_when_it_creates_the_config(
    tmp_path: Any, monkeypatch: Any, frozen_time: Any
) -> None:
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    await service.init(root=fresh, roles_spec="minimal", _skip_skill_seed=True)
    adopted = tmp_path / "adopted"
    adopted.mkdir()
    await service.adopt(root=adopted, roles_spec="minimal")
    existing = tmp_path / "existing"
    existing.mkdir()
    config = existing / ".squads.toml"
    config.write_text(
        'schema_version = "0.2"\nsquad_dir = "squads"\nactive_backends = ["claude_code"]\n',
        encoding="utf-8",
    )
    before = config.read_text(encoding="utf-8")
    await service.adopt(root=existing, roles_spec="minimal")

    assert 'working_language = "en"' in (fresh / ".squads.toml").read_text(encoding="utf-8")
    assert 'working_language = "en"' in (adopted / ".squads.toml").read_text(encoding="utf-8")
    assert config.read_text(encoding="utf-8") == before


async def test_outside_a_squad_the_startup_check_stays_out_of_the_way(invoke: Any) -> None:
    missing = await invoke(["list"])
    created = await invoke(["init", "--roles", "minimal"])

    assert missing.exit_code == 1
    assert "Traceback" not in missing.output
    assert created.exit_code == 0, created.output
