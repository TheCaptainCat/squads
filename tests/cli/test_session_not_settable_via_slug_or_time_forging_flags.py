"""Session attribution is settable ONLY via explicit seeding (`_actor.seed_session`, read from
the environment at the CLI root callback) — never implicitly via the ``--as``/``--author``
slug flags, and never via the ``--at`` time-forging flag. A deliberate anti-footgun guard
against two unrelated mechanisms silently composing (the unit-layer half of this same
guarantee — ``set_actor`` never touches the session pair — lives in
tests/unit/test_session_seeding.py).
"""

import json

import pytest

from squads._cli import app
from squads._index._reflog import read_lines, reflog_path

pytestmark = pytest.mark.anyio


async def test_the_as_flag_never_sets_a_session_on_the_reflog_line(project, invoke, monkeypatch):
    monkeypatch.delenv("SQUADS_SESSION_ID", raising=False)
    monkeypatch.delenv("SQUADS_PARENT_SESSION_ID", raising=False)
    await invoke(["create", "task", "Test", "--author", "manager"])
    result = await invoke(["task", "2", "comment", "--as", "manager", "-m", "A note"])
    assert result.exit_code == 0

    lines = await read_lines(reflog_path(project.squad_dir))
    comment_lines = [ln for ln in lines if ln.op == "comment"]
    assert comment_lines
    assert all(ln.session_id is None for ln in comment_lines)


def test_the_at_time_forging_flag_never_sets_a_session_on_the_created_item(
    runner, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SQUADS_SESSION_ID", raising=False)
    monkeypatch.delenv("SQUADS_PARENT_SESSION_ID", raising=False)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    r = runner.invoke(app, ["--at", "2020-05-06", "create", "task", "old", "--author", "manager"])
    assert r.exit_code == 0, r.output

    result = runner.invoke(app, ["reflog", "--json"])
    data = json.loads(result.output)
    create_entries = [e for e in data if e["op"] == "create"]
    assert create_entries
    assert all(e.get("session_id") is None for e in create_entries)
