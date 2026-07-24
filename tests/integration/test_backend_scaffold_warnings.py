"""WARN-only backend-scaffold notices on `init`/`adopt`: a candidate orphan pointer/skill
file this run did not generate (a hand-authored `.claude` corpus meeting `adopt`), and a
pre-existing hand-written CLAUDE.md/AGENTS.md with no squads markers yet. Both are advisory —
never delete/overwrite hand-written content, never abort the run.
"""

import pytest

from squads._cli import app
from squads._services import _service as service

pytestmark = pytest.mark.anyio


# ------------------------------------------------------------------ orphan pointers


async def test_adopt_warns_about_a_non_matching_pointer_but_not_a_slug_matched_one(
    tmp_path, monkeypatch, frozen_time
) -> None:
    """A hand-written pointer whose slug matches an activated role is squads-managed
    territory (overwritten, no warning); one that matches no role/skill is a candidate
    orphan — flagged, never deleted."""
    monkeypatch.chdir(tmp_path)
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "architect.md").write_text("HAND-WRITTEN ARCHITECT NOTES\n", encoding="utf-8")
    (agents_dir / "ux-ui-dev.md").write_text("hand-written ux notes\n", encoding="utf-8")

    result = await service.adopt(root=tmp_path, roles_spec="architect")

    orphan_warnings = [w for w in result.warnings if "ux-ui-dev.md" in w]
    assert len(orphan_warnings) == 1
    assert not any("architect.md" in w for w in result.warnings)

    # The slug-matched pointer WAS overwritten with the real definition (existing behaviour).
    architect_text = (agents_dir / "architect.md").read_text(encoding="utf-8")
    assert "HAND-WRITTEN ARCHITECT NOTES" not in architect_text
    assert "name: architect" in architect_text

    # The non-matching one is untouched — warned about, never deleted or modified.
    assert (agents_dir / "ux-ui-dev.md").read_text(encoding="utf-8") == "hand-written ux notes\n"


async def test_adopt_warns_about_an_orphan_skill_directory_and_never_deletes_it(
    tmp_path, monkeypatch, frozen_time
) -> None:
    monkeypatch.chdir(tmp_path)
    stale_skill = tmp_path / ".claude" / "skills" / "some-old-skill"
    stale_skill.mkdir(parents=True)
    (stale_skill / "SKILL.md").write_text("stale hand-written skill\n", encoding="utf-8")

    result = await service.adopt(root=tmp_path, roles_spec="minimal")

    assert any("some-old-skill" in w for w in result.warnings)
    assert (stale_skill / "SKILL.md").read_text(encoding="utf-8") == "stale hand-written skill\n"


async def test_a_fresh_init_reports_no_orphan_warnings(tmp_path, monkeypatch, frozen_time) -> None:
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    assert result.warnings == []


async def test_no_claude_skips_the_orphan_scan_entirely(tmp_path, monkeypatch, frozen_time) -> None:
    """With no backend scaffolding this run, there's nothing to compare against — no scan,
    no false warnings about a corpus this run never looked at."""
    monkeypatch.chdir(tmp_path)
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "whatever.md").write_text("pre-existing\n", encoding="utf-8")

    result = await service.init(root=tmp_path, roles_spec="minimal", no_claude=True)
    assert result.warnings == []


# ------------------------------------------------------------------ pre-existing CLAUDE.md


async def test_init_warns_and_leads_with_the_managed_block_over_pre_existing_claude_md(
    tmp_path, monkeypatch, frozen_time
) -> None:
    monkeypatch.chdir(tmp_path)
    handwritten = "# Our project\n\nSome real hand-written operating notes.\n"
    (tmp_path / "CLAUDE.md").write_text(handwritten, encoding="utf-8")

    result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)

    assert any("CLAUDE.md" in w for w in result.warnings)
    text = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert text.count("<!-- squads:start -->") == 1
    # The managed block leads; the hand-written prose survives intact, further down.
    assert text.index("<!-- squads:start -->") < text.index("Some real hand-written")
    assert handwritten in text


async def test_a_second_sync_over_an_already_managed_file_warns_only_once_and_never_moves_it(
    tmp_path, monkeypatch, frozen_time
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "CLAUDE.md").write_text("# Hand-written\n\nReal notes.\n", encoding="utf-8")
    result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    assert any("CLAUDE.md" in w for w in result.warnings)
    before = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")

    svc = service.Service(result.paths)
    warnings_again = await svc.refresh_managed()

    assert not any("CLAUDE.md" in w for w in warnings_again)
    after = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert after.count("<!-- squads:start -->") == 1
    assert before.index("Real notes.") == after.index("Real notes.")


async def test_a_missing_claude_md_is_created_with_no_warning(
    tmp_path, monkeypatch, frozen_time
) -> None:
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    assert not any("CLAUDE.md" in w for w in result.warnings)
    assert (tmp_path / "CLAUDE.md").exists()


async def test_agents_md_backend_shares_the_same_warn_and_lead_behaviour(
    tmp_path, monkeypatch, frozen_time
) -> None:
    monkeypatch.chdir(tmp_path)
    handwritten = "# Our project\n\nHand-authored AGENTS.md notes.\n"
    (tmp_path / "AGENTS.md").write_text(handwritten, encoding="utf-8")

    result = await service.init(
        root=tmp_path, roles_spec="minimal", backend=["agents_md"], _skip_skill_seed=True
    )

    assert any("AGENTS.md" in w for w in result.warnings)
    text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert text.count("<!-- squads:start -->") == 1
    assert text.index("<!-- squads:start -->") < text.index("Hand-authored AGENTS.md notes.")
    assert handwritten in text


# ------------------------------------------------------------------ CLI smoke


def test_sq_init_cli_prints_the_pre_existing_claude_md_warning(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "CLAUDE.md").write_text("# Real notes\n\nHand-written.\n", encoding="utf-8")
    result = runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    assert result.exit_code == 0, result.output
    assert "warning:" in result.output
    assert "CLAUDE.md" in result.output


def test_sq_adopt_cli_prints_the_orphan_pointer_warning(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "some-stranger.md").write_text("not ours\n", encoding="utf-8")
    result = runner.invoke(app, ["adopt", "--roles", "minimal"])
    assert result.exit_code == 0, result.output
    assert "warning:" in result.output
    assert "some-stranger.md" in result.output
    assert (agents_dir / "some-stranger.md").read_text(encoding="utf-8") == "not ours\n"
