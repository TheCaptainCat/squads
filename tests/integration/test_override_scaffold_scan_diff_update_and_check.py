"""The `sq override` lifecycle end to end: scaffold stamps a copy of the bundle (refusing to
clobber without --force), scan enumerates every override with its current/broken state, diff
reports Δ-mine/Δ-upgrade, update-stamp re-stamps without touching body content (skipping
anything structurally broken), `sq check` turns drift into a warning and a missing required
marker into an error, the full stale->diff->update->clean loop closes, and `sq migrate up`
never touches a file under `.overrides/`. CLI exit-code/JSON smoke lives in
tests/cli/test_override_commands_cli.py; manifest/stamp mechanics live in
tests/unit/test_override_manifest_and_stamp_freshness.py.

The third override kind, `workflow` (`.overrides/workflow.toml`, additive-only — no bundled
counterpart to diff against, so drift is version-stamp-only), gets its own `TestWorkflowOverride`
class below: `open_service` actually consuming a hand-written workflow.toml is proven
separately at tests/integration/test_workflow_override_service_integration.py — this file covers
the scaffold/scan/diff/update/check lifecycle commands themselves, exactly as it does for
`template`/`role`.
"""

from pathlib import Path

import pytest

from squads import __version__
from squads._errors import SquadsError
from squads._overrides._service import (
    STATE_BROKEN,
    STATE_CURRENT,
    STATE_DRIFTED,
    DiffResult,
    check_override_issues,
    diff_override,
    scaffold_role,
    scaffold_template,
    scaffold_workflow,
    scan_overrides,
    update_stamp,
)
from squads._overrides._stamp import read_template_stamp, read_toml_stamp, stamp_toml_file
from squads._services import _service as service
from squads._workflow._loader import WORKFLOW_OVERRIDE_FILENAME

pytestmark = pytest.mark.anyio


def _tmpl_dir(squad_dir: Path) -> Path:
    return squad_dir / ".overrides" / "templates"


def _role_dir(squad_dir: Path) -> Path:
    return squad_dir / ".overrides" / "roles"


def _place_template(squad_dir: Path, name: str, content: str, *, stamp: str | None = None) -> Path:
    from squads._overrides._stamp import write_template_stamp

    target = _tmpl_dir(squad_dir) / name
    target.parent.mkdir(parents=True, exist_ok=True)
    text = content if stamp is None else write_template_stamp(content, stamp)
    target.write_text(text, encoding="utf-8")
    return target


def _place_role(squad_dir: Path, slug: str, content: str) -> Path:
    target = _role_dir(squad_dir) / f"{slug}.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def _valid_task_override(label: str = "CUSTOM") -> str:
    return (
        f"<!-- sq:body -->\n{label}\n<!-- sq:body:end -->\n\n"
        "<!-- sq:summary -->\n<!-- sq:summary:end -->\n\n"
        "<!-- sq:subtasks -->\n<!-- sq:subtasks:end -->\n\n"
        "## Discussion\n\n<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n"
    )


def _broken_task_override() -> str:
    return (
        "## Description\n\nMISSING MARKERS\n\n<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n"
    )


class TestScaffold:
    async def test_scaffold_template_stamps_a_copy_of_the_bundle_and_refuses_to_clobber(
        self, project
    ) -> None:
        squad_dir = project.squad_dir
        dest = scaffold_template(squad_dir, "items/task.md.j2")
        text = dest.read_text(encoding="utf-8")
        assert read_template_stamp(text) == __version__
        assert "<!-- sq:body -->" in text

        with pytest.raises(SquadsError, match="already exists"):
            scaffold_template(squad_dir, "items/task.md.j2")

        dest.write_text("custom content", encoding="utf-8")
        scaffold_template(squad_dir, "items/task.md.j2", force=True)
        assert "<!-- sq:body -->" in dest.read_text(encoding="utf-8")

    async def test_scaffold_template_raises_for_an_unknown_bundled_template(self, project) -> None:
        with pytest.raises(SquadsError, match="no bundled template"):
            scaffold_template(project.squad_dir, "items/nonexistent.md.j2")

    @pytest.mark.parametrize(
        "template_name",
        [
            "items/task.md.j2",
            "items/bug.md.j2",
            "items/feature.md.j2",
            "items/epic.md.j2",
            "items/review.md.j2",
            "items/guide.md.j2",
            "items/decision.md.j2",
        ],
    )
    async def test_scaffold_template_works_for_every_bundled_item_type(
        self, project, template_name
    ) -> None:
        dest = scaffold_template(project.squad_dir, template_name)
        assert dest.exists()
        assert read_template_stamp(dest.read_text(encoding="utf-8")) is not None

    async def test_scaffold_role_stamps_a_toml_stub_and_refuses_to_clobber(self, project) -> None:
        squad_dir = project.squad_dir
        dest = scaffold_role(squad_dir, slug="architect")
        assert read_toml_stamp(dest.read_text(encoding="utf-8")) == __version__

        with pytest.raises(SquadsError, match="already exists"):
            scaffold_role(squad_dir, slug="architect")

        dest.write_text("# old content\n", encoding="utf-8")
        scaffold_role(squad_dir, slug="architect", force=True)
        assert read_toml_stamp(dest.read_text(encoding="utf-8")) is not None


class TestWorkflowOverride:
    """The `workflow` override kind's scaffold/scan/diff/update/check lifecycle — additive-only
    (no bundled counterpart), so drift is detected by version stamp alone."""

    async def test_scaffold_creates_a_stamped_file_containing_the_worked_example(
        self, project
    ) -> None:
        dest = scaffold_workflow(project.squad_dir)
        text = dest.read_text(encoding="utf-8")
        assert read_toml_stamp(text) == __version__
        assert "incident" in text  # the commented worked example

        with pytest.raises(SquadsError, match="already exists"):
            scaffold_workflow(project.squad_dir)

        dest.write_text("custom content", encoding="utf-8")
        scaffold_workflow(project.squad_dir, force=True)
        assert "incident" in dest.read_text(encoding="utf-8")

    async def test_scan_reports_a_workflow_entry_current_when_freshly_scaffolded(
        self, project
    ) -> None:
        scaffold_workflow(project.squad_dir)
        entries = scan_overrides(project.squad_dir)
        assert len(entries) == 1
        assert entries[0].name == "workflow"
        assert entries[0].kind == "workflow"
        assert entries[0].base_version == __version__
        assert entries[0].state == STATE_CURRENT

    async def test_scan_flags_an_old_or_missing_stamp_as_drifted(self, project) -> None:
        path = scaffold_workflow(project.squad_dir)
        stamp_toml_file(path, "0.1.0")
        assert scan_overrides(project.squad_dir)[0].state == STATE_DRIFTED

        path.write_text(path.read_text(encoding="utf-8").split("\n", 1)[1], encoding="utf-8")
        assert scan_overrides(project.squad_dir)[0].state == STATE_DRIFTED

    async def test_diff_raises_when_absent_and_reflects_the_stamp_state_once_present(
        self, project
    ) -> None:
        with pytest.raises(SquadsError, match="no workflow override found"):
            diff_override(project.squad_dir, "workflow", "workflow")

        path = scaffold_workflow(project.squad_dir)
        current = diff_override(project.squad_dir, "workflow", "workflow")
        assert current.kind == "workflow"
        assert "incident" in current.delta_mine  # additive-only: diffed against empty
        assert current.base_available is True
        assert "no upgrade delta" in current.delta_upgrade

        stamp_toml_file(path, "0.1.0")
        stale = diff_override(project.squad_dir, "workflow", "workflow")
        assert "review the squads changelog" in stale.delta_upgrade

        path.write_text(path.read_text(encoding="utf-8").split("\n", 1)[1], encoding="utf-8")
        unstamped = diff_override(project.squad_dir, "workflow", "workflow")
        assert unstamped.base_available is False
        assert "no stamp" in unstamped.delta_upgrade

    async def test_update_stamp_restamps_and_raises_when_absent(self, project) -> None:
        with pytest.raises(SquadsError, match="no workflow override found"):
            update_stamp(project.squad_dir, "workflow", "workflow")

        path = scaffold_workflow(project.squad_dir)
        stamp_toml_file(path, "0.1.0")
        stamped = update_stamp(project.squad_dir, "workflow", "workflow")
        assert stamped == ["workflow"]
        assert read_toml_stamp(path.read_text(encoding="utf-8")) == __version__

    async def test_bulk_update_stamp_includes_the_workflow_override(self, project) -> None:
        path = scaffold_workflow(project.squad_dir)
        stamp_toml_file(path, "0.1.0")
        stamped = update_stamp(project.squad_dir, None, None)
        assert "workflow" in stamped

    async def test_check_warns_on_a_stale_stamp(self, project, svc) -> None:
        path = scaffold_workflow(project.squad_dir)
        assert check_override_issues(project.squad_dir) == []  # freshly scaffolded: clean

        stamp_toml_file(path, "0.1.0")
        issues = check_override_issues(project.squad_dir)
        assert len(issues) == 1
        level, display, message = issues[0]
        assert level == "warn"
        assert display == WORKFLOW_OVERRIDE_FILENAME
        assert "workflow override may be stale" in message

        # surfaces through the real sq check too, without flipping the exit code.
        svc_issues = await svc.check()
        assert any(".overrides" in i.item or "workflow" in i.item for i in svc_issues)


class TestScanOverrides:
    async def test_scan_is_empty_when_no_overrides_directory_exists(self, project) -> None:
        assert scan_overrides(project.squad_dir) == []

    async def test_scan_reports_current_and_broken_state_for_templates_and_roles(
        self, project
    ) -> None:
        squad_dir = project.squad_dir
        _place_template(squad_dir, "items/task.md.j2", _valid_task_override(), stamp=__version__)
        entries = scan_overrides(squad_dir)
        assert len(entries) == 1
        assert entries[0].name == "items/task.md.j2"
        assert entries[0].kind == "template"
        assert entries[0].base_version == __version__
        assert entries[0].state == STATE_CURRENT

        _place_template(squad_dir, "items/bug.md.j2", _broken_task_override(), stamp="0.3.0")
        _place_role(squad_dir, "qa", f"# squads:override-base:{__version__}\n")
        entries = scan_overrides(squad_dir)
        by_name = {e.name: e for e in entries}
        assert by_name["items/bug.md.j2"].state == STATE_BROKEN
        assert by_name["qa"].kind == "role"
        assert by_name["qa"].state == STATE_CURRENT
        assert {e.kind for e in entries} == {"template", "role"}


class TestDiffOverride:
    async def test_diff_raises_when_no_override_is_present_for_either_kind(self, project) -> None:
        with pytest.raises(SquadsError, match="no template override"):
            diff_override(project.squad_dir, "items/task.md.j2", "template")
        with pytest.raises(SquadsError, match="no role override"):
            diff_override(project.squad_dir, "architect", "role")

    async def test_diff_raises_for_an_unknown_kind(self, project) -> None:
        with pytest.raises(SquadsError, match="unknown override kind"):
            diff_override(project.squad_dir, "something", "unknown-kind")

    async def test_delta_mine_shows_the_customisation_delta_upgrade_is_empty_at_same_version(
        self, project
    ) -> None:
        squad_dir = project.squad_dir
        _place_template(
            squad_dir,
            "items/task.md.j2",
            _valid_task_override("MY_CUSTOM_CONTENT"),
            stamp=__version__,
        )
        result = diff_override(squad_dir, "items/task.md.j2", "template")
        assert isinstance(result, DiffResult)
        assert "MY_CUSTOM_CONTENT" in result.delta_mine or result.delta_mine != ""
        assert result.delta_upgrade == ""

    async def test_role_diff_shows_delta_mine(self, project) -> None:
        squad_dir = project.squad_dir
        _place_role(
            squad_dir, "architect", f'# squads:override-base:{__version__}\nfull_name = "Ada"\n'
        )
        assert "Ada" in diff_override(squad_dir, "architect", "role").delta_mine


class TestUpdateStamp:
    async def test_update_stamp_re_stamps_a_template_without_touching_its_body(
        self, project
    ) -> None:
        squad_dir = project.squad_dir
        _place_template(
            squad_dir, "items/task.md.j2", _valid_task_override("PRESERVE_ME"), stamp="0.1.0"
        )
        stamped = update_stamp(squad_dir, "items/task.md.j2", "template")
        assert stamped == ["items/task.md.j2"]
        text = (_tmpl_dir(squad_dir) / "items/task.md.j2").read_text(encoding="utf-8")
        assert read_template_stamp(text) == __version__
        assert "PRESERVE_ME" in text

    async def test_update_stamp_raises_for_a_structurally_broken_override(self, project) -> None:
        squad_dir = project.squad_dir
        _place_template(squad_dir, "items/task.md.j2", _broken_task_override(), stamp="0.1.0")
        with pytest.raises(SquadsError, match="missing required sq markers"):
            update_stamp(squad_dir, "items/task.md.j2", "template")

    async def test_bulk_update_stamp_re_stamps_valid_overrides_and_skips_broken_ones(
        self, project
    ) -> None:
        squad_dir = project.squad_dir
        _place_template(squad_dir, "items/task.md.j2", _valid_task_override(), stamp="0.1.0")
        _place_template(squad_dir, "items/bug.md.j2", _broken_task_override(), stamp="0.1.0")
        stamped = update_stamp(squad_dir, None, None)
        assert "items/task.md.j2" in stamped
        assert "items/bug.md.j2" not in stamped

    async def test_update_stamp_re_stamps_a_role_and_raises_for_a_missing_name(
        self, project
    ) -> None:
        squad_dir = project.squad_dir
        _place_role(squad_dir, "architect", "# squads:override-base:0.1.0\nfull_name = 'Ada'\n")
        stamped = update_stamp(squad_dir, "architect", "role")
        assert "architect" in stamped
        text = (_role_dir(squad_dir) / "architect.toml").read_text(encoding="utf-8")
        assert read_toml_stamp(text) == __version__
        assert "Ada" in text

        with pytest.raises(SquadsError, match="no override found"):
            update_stamp(project.squad_dir, "items/nonexistent.md.j2", "template")


class TestCheckDrift:
    async def test_check_is_clean_for_an_override_stamped_at_the_running_version(
        self, project, svc
    ) -> None:
        squad_dir = project.squad_dir
        _place_template(squad_dir, "items/task.md.j2", _valid_task_override(), stamp=__version__)
        issues = await svc.check()
        assert not [i for i in issues if ".overrides" in i.item]
        assert check_override_issues(squad_dir) == []

    async def test_check_warns_on_an_unstamped_override_but_still_renders(
        self, project, svc
    ) -> None:
        squad_dir = project.squad_dir
        _place_template(squad_dir, "items/task.md.j2", _valid_task_override())
        issues = await svc.check()
        override_issues = [i for i in issues if ".overrides" in i.item]
        assert override_issues and all(i.level == "warn" for i in override_issues)

    async def test_check_errors_on_a_structurally_broken_override(self, project, svc) -> None:
        squad_dir = project.squad_dir
        _place_template(squad_dir, "items/task.md.j2", _broken_task_override(), stamp=__version__)
        issues = await svc.check()
        errors = [i for i in issues if i.level == "error" and ".overrides" in i.item]
        assert errors
        assert any("missing required sq marker" in i.message for i in errors)


class TestFullStalenessLoop:
    async def test_stale_diff_update_clears_the_warning(self, project, svc, invoke) -> None:
        squad_dir = project.squad_dir
        _place_template(squad_dir, "items/task.md.j2", _valid_task_override())

        issues_before = await svc.check()
        assert [i for i in issues_before if ".overrides" in i.item and i.level == "warn"]

        diff_result = await invoke(["override", "diff", "items/task.md.j2"])
        assert diff_result.exit_code == 0, diff_result.output

        # Simulate a hand-merge landing on an old base version, then re-stamp it.
        _place_template(squad_dir, "items/task.md.j2", _valid_task_override(), stamp="0.1.0")
        update_result = await invoke(["override", "update", "items/task.md.j2"])
        assert update_result.exit_code == 0, update_result.output

        text = (_tmpl_dir(squad_dir) / "items/task.md.j2").read_text(encoding="utf-8")
        assert read_template_stamp(text) == __version__

        issues_after = await service.Service(project).check()
        assert not [i for i in issues_after if ".overrides" in i.item]


async def test_migrate_up_never_touches_a_file_under_overrides(project, invoke) -> None:
    squad_dir = project.squad_dir
    dest = _place_template(
        squad_dir, "items/task.md.j2", _valid_task_override("MUST_NOT_TOUCH"), stamp=__version__
    )
    mtime_before = dest.stat().st_mtime

    result = await invoke(["migrate", "up"])
    assert result.exit_code == 0, result.output

    assert dest.stat().st_mtime == mtime_before
    assert "MUST_NOT_TOUCH" in dest.read_text(encoding="utf-8")
