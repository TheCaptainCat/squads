"""The `roles` override kind's scaffold/scan/diff/update lifecycle — mirrors
`TestWorkflowOverride`/`TestPlaybookOverride` in
`test_override_scaffold_scan_diff_update_and_check.py` (same stamp-only-until-content-gated
drift contract, same scaffold/diff/update verb shape), the fifth override kind alongside
workflow/playbook/roles(per-slug)/templates.

`sq check`'s stamp-obligation finding for this kind (shadowing-vs-add-only severity,
`_check_roles_catalog_override_issues`/`_roles_catalog_stamp_finding_gated`) is exercised in
`TestCheckDrift` below, on the same shadowing-unstamped-is-an-error contract every other
override kind carries. Scaffold, stamp, the drift classifier, and both diff panes are
exercised by the classes above it.

This file drives the service functions directly, exactly as the sibling classes in the file
above do for workflow/playbook. `sq override scaffold roles`/`diff roles`/`update roles` (the
CLI verbs over this same service layer) are exercised through the real CLI in
`tests/cli/test_override_commands_cli.py`.
"""

import pytest

from squads import __version__
from squads._errors import SquadsError
from squads._overrides._service import (
    STATE_CURRENT,
    STATE_DRIFTED,
    check_override_issues,
    diff_override,
    scaffold_roles_catalog,
    scan_overrides,
    update_stamp,
)
from squads._overrides._stamp import read_toml_stamp, stamp_toml_file
from squads._roles._loader import ROLES_OVERRIDE_FILENAME

pytestmark = pytest.mark.anyio


class TestScaffold:
    async def test_scaffold_creates_a_stamped_file_containing_the_worked_example(
        self, project
    ) -> None:
        dest = scaffold_roles_catalog(project.squad_dir)
        text = dest.read_text(encoding="utf-8")
        assert read_toml_stamp(text) == __version__
        assert "[[roles]]" in text  # the commented worked example

        with pytest.raises(SquadsError, match="already exists"):
            scaffold_roles_catalog(project.squad_dir)

        dest.write_text("custom content", encoding="utf-8")
        scaffold_roles_catalog(project.squad_dir, force=True)
        assert "[[roles]]" in dest.read_text(encoding="utf-8")


class TestScanOverrides:
    async def test_scan_reports_a_roles_entry_current_when_freshly_scaffolded(
        self, project
    ) -> None:
        scaffold_roles_catalog(project.squad_dir)
        entries = scan_overrides(project.squad_dir)
        assert len(entries) == 1
        assert entries[0].name == "roles"
        assert entries[0].kind == "roles"
        assert entries[0].base_version == __version__
        assert entries[0].state == STATE_CURRENT

    async def test_scan_reports_drifted_for_an_unstamped_file(self, project) -> None:
        path = scaffold_roles_catalog(project.squad_dir)
        path.write_text(path.read_text(encoding="utf-8").split("\n", 1)[1], encoding="utf-8")
        assert scan_overrides(project.squad_dir)[0].state == STATE_DRIFTED

    async def test_scan_reports_an_uncarried_old_stamp_current_when_content_is_unchanged(
        self, project
    ) -> None:
        """Content-gated drift, mirroring the workflow/playbook kinds' equivalent test: a
        stamp squads carries no per-release history for reports current, not drifted, on
        stamp age alone."""
        path = scaffold_roles_catalog(project.squad_dir)
        stamp_toml_file(path, "0.1.0")
        assert scan_overrides(project.squad_dir)[0].state == STATE_CURRENT


class TestDiffOverride:
    async def test_diff_raises_when_absent_and_reflects_the_stamp_state_once_present(
        self, project
    ) -> None:
        with pytest.raises(SquadsError, match="no role catalog override found"):
            diff_override(project.squad_dir, "roles", "roles")

        path = scaffold_roles_catalog(project.squad_dir)
        current = diff_override(project.squad_dir, "roles", "roles")
        assert current.kind == "roles"
        assert current.name == "roles"
        # A purely-commented scaffold's Δ-mine shows every real bundled entry as "removed"
        # relative to the scaffold, against the real bundled document (not an empty reference).
        assert "bundled/roles.toml" in current.delta_mine
        assert "-[bundles]" in current.delta_mine
        assert current.base_available is True
        assert current.delta_upgrade == ""  # stamp == running version: real diff, no delta

        stamp_toml_file(path, "0.1.0")
        stale = diff_override(project.squad_dir, "roles", "roles")
        assert stale.base_version == "0.1.0"

        path.write_text(path.read_text(encoding="utf-8").split("\n", 1)[1], encoding="utf-8")
        unstamped = diff_override(project.squad_dir, "roles", "roles")
        assert unstamped.base_available is False
        assert "no stamp" in unstamped.delta_upgrade

    async def test_diff_shows_the_customisation_against_the_bundled_document(self, project) -> None:
        path = scaffold_roles_catalog(project.squad_dir)
        path.write_text(
            f'# squads:override-base:{__version__}\n[dev]\ncolor = "magenta"\n',
            encoding="utf-8",
        )
        result = diff_override(project.squad_dir, "roles", "roles")
        # "magenta" names no bundled colour anywhere in roles.toml, so it can only ever show
        # up as an added line — unlike a value (e.g. "opus") difflib might match against an
        # unrelated existing occurrence deeper in the bundled document and render as context.
        assert '+color = "magenta"' in result.delta_mine


class TestUpdateStamp:
    async def test_update_stamp_restamps_and_raises_when_absent(self, project) -> None:
        with pytest.raises(SquadsError, match="no role catalog override found"):
            update_stamp(project.squad_dir, "roles", "roles")

        path = scaffold_roles_catalog(project.squad_dir)
        stamp_toml_file(path, "0.1.0")
        stamped = update_stamp(project.squad_dir, "roles", "roles")
        assert stamped == ["roles"]
        assert read_toml_stamp(path.read_text(encoding="utf-8")) == __version__

    async def test_bulk_update_stamp_includes_the_roles_catalog_override(self, project) -> None:
        path = scaffold_roles_catalog(project.squad_dir)
        stamp_toml_file(path, "0.1.0")
        stamped = update_stamp(project.squad_dir, None, None)
        assert "roles" in stamped
        assert read_toml_stamp(path.read_text(encoding="utf-8")) == __version__


class TestCheckDrift:
    """The stamp obligation (the uniform severity contract): unstamped-and-shadowing is an
    error, unstamped-and-add-only is silent, and a stale-but-content-unchanged stamp
    stays clean. Mirrors
    `TestPlaybookOverride`'s equivalent tests in
    `test_override_scaffold_scan_diff_update_and_check.py` exactly — same three-outcome
    contract, now wired for this kind too."""

    async def test_check_reports_an_error_for_a_shadowing_override_with_no_stamp(
        self, project
    ) -> None:
        """Redeclaring a bundled role slug shadows — an unstamped shadowing override is an
        error, never a load-time refusal."""
        override_path = project.squad_dir / ROLES_OVERRIDE_FILENAME
        override_path.parent.mkdir(parents=True, exist_ok=True)
        override_path.write_text(
            '[[roles]]\nslug = "architect"\ntitle = "Chief Architect"\n', encoding="utf-8"
        )

        issues = check_override_issues(project.squad_dir)
        assert len(issues) == 1
        level, display, message = issues[0]
        assert level == "error"
        assert display == ROLES_OVERRIDE_FILENAME
        assert "no squads:override-base stamp" in message
        # Names its own object, like every sibling kind — not the bulk form.
        assert "`sq override update roles`" in message

    async def test_check_reports_an_error_for_an_unstamped_bundle_shadow(self, project) -> None:
        """Shadowing is not limited to `roles` — redeclaring a bundled bundle name is a
        shadow too."""
        override_path = project.squad_dir / ROLES_OVERRIDE_FILENAME
        override_path.parent.mkdir(parents=True, exist_ok=True)
        override_path.write_text('[bundles]\nall = ["architect"]\n', encoding="utf-8")

        issues = check_override_issues(project.squad_dir)
        assert len(issues) == 1
        assert issues[0][0] == "error"

    async def test_check_reports_an_error_for_an_unstamped_dev_shadow(self, project) -> None:
        """`[dev]` is one object, not a keyed collection — declaring it at all redeclares the
        bundled dev pool, so it shadows even with no slug or bundle name in common."""
        override_path = project.squad_dir / ROLES_OVERRIDE_FILENAME
        override_path.parent.mkdir(parents=True, exist_ok=True)
        override_path.write_text('[dev]\nmodel = "opus"\n', encoding="utf-8")

        issues = check_override_issues(project.squad_dir)
        assert len(issues) == 1
        assert issues[0][0] == "error"

    async def test_check_reports_nothing_for_an_add_only_override_with_no_stamp(
        self, project
    ) -> None:
        """A brand-new, non-bundled role slug — no shadowed slug, bundle, or `[dev]` — has
        nothing to have drifted from yet."""
        override_path = project.squad_dir / ROLES_OVERRIDE_FILENAME
        override_path.parent.mkdir(parents=True, exist_ok=True)
        override_path.write_text(
            '[[roles]]\nslug = "security-analyst"\nfull_name = "Sam Analyst"\n'
            'title = "Security Analyst"\ndescription = "Reviews for security issues."\n'
            'mission = "Keep the codebase secure."\n',
            encoding="utf-8",
        )

        assert check_override_issues(project.squad_dir) == []

    async def test_check_warns_when_the_bundled_catalog_actually_changed(
        self, project, monkeypatch
    ) -> None:
        """Content-gated drift's warn branch, driven the same way the playbook kind's
        equivalent test is (real history has not moved this document either): make
        `artifact_changed_since` say so, exercising the real wiring
        (`_check_roles_catalog_override_issues` -> `_roles_catalog_stamp_finding_gated`)."""
        from squads._overrides import _service as override_service

        path = scaffold_roles_catalog(project.squad_dir)
        stamp_toml_file(path, "0.13.1")
        monkeypatch.setattr(override_service, "artifact_changed_since", lambda key, v: True)

        issues = check_override_issues(project.squad_dir)
        assert len(issues) == 1
        level, display, message = issues[0]
        assert level == "warn"
        assert display == ROLES_OVERRIDE_FILENAME
        assert "role catalog override may be stale" in message
        # Names its own object, like every sibling kind — not the bulk form.
        assert "`sq override diff roles`" in message
        assert "`sq override update roles`" in message

    async def test_check_reports_clean_for_a_stamp_squads_carries_no_provenance_for(
        self, project
    ) -> None:
        path = scaffold_roles_catalog(project.squad_dir)
        assert check_override_issues(project.squad_dir) == []  # freshly scaffolded: clean

        stamp_toml_file(path, "0.1.0")
        assert check_override_issues(project.squad_dir) == []  # uncarried base: silent


async def test_roles_catalog_override_coexists_with_the_per_slug_roles_directory(
    project,
) -> None:
    """`.overrides/roles.toml` (this document) and `.overrides/roles/<slug>.toml` (the
    per-slug files) are siblings on disk with distinct names — scaffolding one must not
    disturb the other, and both show up in `sq override list`."""
    from squads._overrides._service import scaffold_role

    scaffold_roles_catalog(project.squad_dir)
    scaffold_role(project.squad_dir, "architect")

    entries = scan_overrides(project.squad_dir)
    kinds = {e.kind for e in entries}
    assert kinds == {"roles", "role"}
    assert (project.squad_dir / ROLES_OVERRIDE_FILENAME).is_file()
    assert (project.squad_dir / ".overrides" / "roles" / "architect.toml").is_file()
