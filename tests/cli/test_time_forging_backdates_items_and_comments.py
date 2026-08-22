"""The root `--at` flag forges the clock for a single CLI invocation — an operator-facing
escape hatch for backdating an import: a created item's `created_at`/`updated_at` and a
comment's timestamp both carry the forged value, and an unparseable `--at` is rejected before
anything runs.

Deliberately does NOT use the `project`/`frozen_time` fixtures: `frozen_time` monkeypatches
`clock.now` directly, which would shadow the `set_now`-based override `--at` relies on.
"""

from squads._cli import app


def test_at_forges_an_items_created_and_updated_timestamps(runner, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    r = runner.invoke(app, ["--at", "2020-05-06", "create", "task", "old", "--author", "manager"])
    assert r.exit_code == 0, r.output
    text = next((tmp_path / "squads" / "tasks").glob("*.md")).read_text(encoding="utf-8")
    assert "created_at: '2020-05-06T00:00:00Z'" in text
    assert "updated_at: '2020-05-06T00:00:00Z'" in text


def test_at_forges_a_comments_timestamp(runner, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "t", "--author", "manager"])
    runner.invoke(
        app,
        ["--at", "2019-12-31T23:00:00Z", "task", "2", "comment", "--as", "manager", "-m", "hi"],
    )
    text = next((tmp_path / "squads" / "tasks").glob("*.md")).read_text(encoding="utf-8")
    assert "- [2019-12-31T23:00:00Z] Catherine Manager:" in text


def test_an_unparseable_at_value_is_rejected(runner, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    r = runner.invoke(app, ["--at", "nope", "list"])
    assert r.exit_code == 2
    assert "invalid --at" in r.output


def test_an_unparseable_at_values_iso_example_stays_on_one_line(
    runner, tmp_path, monkeypatch
) -> None:
    """The regression this guards: at the suite's pinned `COLUMNS=80` (`tests/conftest.py`),
    an unwrapped render used to insert a real newline inside the copy-pasteable ISO example --
    asserted here as "no embedded newline", the same shape the soft-wrap class guard checks,
    rather than a one-off match on this one message's exact text. Exit code stays 2: this
    parser refuses differently from `sq reflog --since`'s (which exits 1, see
    `test_reflog_cli.test_an_invalid_since_value_is_rejected`, unaffected by this fix)."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    r = runner.invoke(app, ["--at", "nope", "list"])
    assert r.exit_code == 2
    assert r.output.count("2024-01-15T09:30:00Z") == 1
    assert "\n" not in r.output.strip("\n")
