from datetime import UTC, datetime

import pytest

from squads import _clock as clock
from squads import _service as service
from squads._cli import app
from squads._models._enums import ItemType

# --------------------------------------------------------------------------- clock override


def test_set_now_overrides_until_cleared():
    forged = datetime(2020, 1, 2, 3, 4, 5, tzinfo=UTC)
    clock.set_now(forged)
    assert clock.now() == forged
    clock.set_now(None)
    assert clock.now() != forged  # back to real wall clock


def test_parse_iso_variants():
    assert clock.parse_iso("2024-01-15") == datetime(2024, 1, 15, tzinfo=UTC)
    assert clock.parse_iso("2024-01-15T09:30:00Z") == datetime(2024, 1, 15, 9, 30, tzinfo=UTC)
    with pytest.raises(ValueError):
        clock.parse_iso("not-a-date")


# --------------------------------------------------------------------------- adopt


def test_adopt_imports_existing_and_is_idempotent(tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    # a pre-existing squad with one task, but no config/index (legacy/native files only)
    init = service.init(root=tmp_path, roles_spec="minimal")
    service.Service(init.paths).create(ItemType.TASK, "legacy")
    (tmp_path / ".squads.toml").unlink()
    (tmp_path / "squads" / ".squads.json").unlink()

    res = service.adopt(root=tmp_path, roles_spec="core")
    assert (tmp_path / ".squads.toml").exists()
    assert res.imported == 2  # manager role + the legacy task
    # manager already existed (imported) → not re-activated; the rest of core are
    activated = {r.extra["slug"] for r in res.roles}
    assert "manager" not in activated
    assert {"architect", "tech-lead", "reviewer"} <= activated

    # idempotent: a second adopt imports everything, activates nothing new
    again = service.adopt(root=tmp_path, roles_spec="core")
    assert again.roles == []


# --------------------------------------------------------------------------- --at (CLI)


def test_at_forges_timestamps(runner, tmp_path, monkeypatch):
    # deliberately NOT using frozen_time so clock honours the --at override
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    r = runner.invoke(app, ["--at", "2020-05-06", "create", "task", "old"])
    assert r.exit_code == 0, r.output
    text = next((tmp_path / "squads" / "tasks").glob("*.md")).read_text(encoding="utf-8")
    assert "created_at: '2020-05-06T00:00:00Z'" in text
    assert "updated_at: '2020-05-06T00:00:00Z'" in text


def test_at_forges_comment_timestamp(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "t"])
    runner.invoke(
        app,
        ["--at", "2019-12-31T23:00:00Z", "comment", "TASK-000002", "--as", "manager", "-m", "hi"],
    )
    text = next((tmp_path / "squads" / "tasks").glob("*.md")).read_text(encoding="utf-8")
    assert "- [2019-12-31T23:00:00Z] Catherine Manager:" in text


def test_at_invalid_is_rejected(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--roles", "minimal"])
    r = runner.invoke(app, ["--at", "nope", "list"])
    assert r.exit_code == 2
    assert "invalid --at" in r.output
