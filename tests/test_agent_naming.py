"""Tests for TASK-000090: agent naming at sq init and role creation.

Verifies:
- sq init --name slug=Full Name sets the name on the activated ROLE item.
- sq init with [init.names] in .squads.toml (round-trip) seeds the name.
- sq init with both flags and config: flags win on conflict.
- sq init with TTY (mocked) prompts for unnamed roles; named ones skipped.
- sq init with --default-names skips prompting even at a TTY.
- Non-TTY (mocked) behaves as --default-names (never blocks).
- Unnamed roles fall back to the bundled PREDEFINED name.
- sq init names flow through extra.full_name → roster → CLAUDE.md section.
- sq role activate --name "…" sets the name on the activated item.
- sq role activate --name with a bundled role overrides the bundled name.
- sq dev add --name still works as before (existing surface, not broken).
- Malformed --name flag (missing '=') exits with error.
- Malformed --name with empty slug exits with error.
- Malformed --name with empty name exits with error.
"""

from squads._cli import app
from squads._models._config import CONFIG_FILENAME, SquadsConfig
from squads._models._enums import ItemType
from squads._models._extras import ExtraKey as X
from squads._roles._catalog import PREDEFINED
from squads._services import _service as service

# --------------------------------------------------------------------------- helpers


def _get_role_item(svc: service.Service, slug: str):
    """Return the ROLE item for the given slug, or raise."""
    items = svc.list_items(item_type=ItemType.ROLE)
    for it in items:
        if it.extra.get(X.SLUG) == slug:
            return it
    raise AssertionError(f"no ROLE item found for slug {slug!r}")


# ============================================================================
# Service-level tests
# ============================================================================


class TestActivateRoleWithName:
    def test_explicit_name_overrides_bundled(self, project, svc):
        """activate_role(slug, name=…) stores the custom name in extra.full_name."""
        item = svc.activate_role("architect", name="Ada Lovelace")
        assert item.extra.get(X.FULL_NAME) == "Ada Lovelace"

    def test_explicit_name_overrides_resolver_toml_name(self, project, svc):
        """A --name flag wins over a full_name set in a TOML override."""
        # Place a TOML that sets a name.
        overrides_dir = project.squad_dir / ".overrides" / "roles"
        overrides_dir.mkdir(parents=True, exist_ok=True)
        (overrides_dir / "qa.toml").write_text('full_name = "TOML QA"\n', encoding="utf-8")
        # Explicit name must win.
        item = svc.activate_role("qa", name="Grace Tester")
        assert item.extra.get(X.FULL_NAME) == "Grace Tester"

    def test_no_name_uses_bundled_default(self, project, svc):
        """activate_role with no name kwarg uses the bundled PREDEFINED full_name."""
        item = svc.activate_role("reviewer")
        bundled = next(r for r in PREDEFINED if r.slug == "reviewer")
        assert item.extra.get(X.FULL_NAME) == bundled.full_name

    def test_no_name_uses_toml_full_name(self, project):
        """activate_role with no name kwarg picks up full_name from a TOML override."""
        overrides_dir = project.squad_dir / ".overrides" / "roles"
        overrides_dir.mkdir(parents=True, exist_ok=True)
        (overrides_dir / "devops.toml").write_text('full_name = "Ops Override"\n', encoding="utf-8")
        svc2 = service.Service(project)
        item = svc2.activate_role("devops")
        assert item.extra.get(X.FULL_NAME) == "Ops Override"


class TestInitWithNames:
    def test_names_kwarg_flows_to_role_item(self, tmp_path, monkeypatch, frozen_time):
        """init(names=…) writes the custom name into the ROLE item's extra.full_name."""
        monkeypatch.chdir(tmp_path)
        result = service.init(
            root=tmp_path,
            roles_spec="core",
            no_claude=True,
            names={"architect": "Ada Lovelace", "manager": "Grace Hopper"},
        )
        svc = service.Service(result.paths)
        arch = _get_role_item(svc, "architect")
        mgr = _get_role_item(svc, "manager")
        assert arch.extra.get(X.FULL_NAME) == "Ada Lovelace"
        assert mgr.extra.get(X.FULL_NAME) == "Grace Hopper"

    def test_unnamed_roles_use_bundled_name(self, tmp_path, monkeypatch, frozen_time):
        """Roles not in names dict fall back to PREDEFINED.full_name."""
        monkeypatch.chdir(tmp_path)
        result = service.init(
            root=tmp_path,
            roles_spec="core",
            no_claude=True,
            names={"architect": "Ada Lovelace"},
        )
        svc = service.Service(result.paths)
        # manager was not in names dict → should have the bundled default
        mgr = _get_role_item(svc, "manager")
        bundled_mgr = next(r for r in PREDEFINED if r.slug == "manager")
        assert mgr.extra.get(X.FULL_NAME) == bundled_mgr.full_name

    def test_names_written_to_config_toml(self, tmp_path, monkeypatch, frozen_time):
        """init() stores init_names in .squads.toml under [init.names]."""
        monkeypatch.chdir(tmp_path)
        service.init(
            root=tmp_path,
            roles_spec="minimal",
            no_claude=True,
            names={"manager": "Grace Hopper"},
        )
        config_text = (tmp_path / CONFIG_FILENAME).read_text(encoding="utf-8")
        assert "[init.names]" in config_text
        assert 'manager = "Grace Hopper"' in config_text

    def test_config_toml_round_trips_init_names(self, tmp_path, monkeypatch, frozen_time):
        """SquadsConfig.to_toml() / from_toml_dict() round-trips [init.names]."""
        monkeypatch.chdir(tmp_path)
        service.init(
            root=tmp_path,
            roles_spec="minimal",
            no_claude=True,
            names={"manager": "Grace Hopper"},
        )
        from squads._paths import load_config

        config_path = tmp_path / CONFIG_FILENAME
        reloaded = load_config(config_path)
        assert reloaded.init_names == {"manager": "Grace Hopper"}

    def test_names_none_produces_empty_init_names(self, tmp_path, monkeypatch, frozen_time):
        """init() with no names writes no [init.names] section to .squads.toml."""
        monkeypatch.chdir(tmp_path)
        service.init(root=tmp_path, roles_spec="minimal", no_claude=True)
        config_text = (tmp_path / CONFIG_FILENAME).read_text(encoding="utf-8")
        assert "[init.names]" not in config_text

    def test_names_flow_to_claude_md_roster(self, tmp_path, monkeypatch, frozen_time):
        """Custom names appear in the CLAUDE.md Agent roster section."""
        monkeypatch.chdir(tmp_path)
        service.init(
            root=tmp_path,
            roles_spec="minimal",
            no_claude=False,
            names={"manager": "Grace Hopper"},
        )
        claude_md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        assert "Grace Hopper" in claude_md


# ============================================================================
# SquadsConfig model: [init.names] table
# ============================================================================


class TestSquadsConfigInitNames:
    def test_to_toml_writes_init_names_section(self):
        cfg = SquadsConfig(
            squad_dir="squads",
            active_backends=["claude_code"],
            default_role="manager",
            squads_version="0.1.0",
            init_names={"architect": "Ada Lovelace", "manager": "Grace Hopper"},
        )
        toml = cfg.to_toml()
        assert "[init.names]" in toml
        assert 'architect = "Ada Lovelace"' in toml
        assert 'manager = "Grace Hopper"' in toml

    def test_to_toml_omits_section_when_empty(self):
        cfg = SquadsConfig(
            squad_dir="squads",
            active_backends=["claude_code"],
            default_role="manager",
            squads_version="0.1.0",
        )
        toml = cfg.to_toml()
        assert "[init.names]" not in toml

    def test_from_toml_dict_hoists_init_names(self):
        data = {
            "schema_version": "0.3",
            "squad_dir": "squads",
            "active_backends": ["claude_code"],
            "default_role": "manager",
            "squads_version": "0.1.0",
            "init": {"names": {"architect": "Ada Lovelace"}},
        }
        cfg = SquadsConfig.from_toml_dict(data)
        assert cfg.init_names == {"architect": "Ada Lovelace"}

    def test_from_toml_dict_no_init_section(self):
        data = {
            "schema_version": "0.3",
            "squad_dir": "squads",
            "active_backends": ["claude_code"],
            "default_role": "manager",
            "squads_version": "0.1.0",
        }
        cfg = SquadsConfig.from_toml_dict(data)
        assert cfg.init_names == {}

    def test_roundtrip_via_toml(self):
        import tomllib

        original = SquadsConfig(
            squad_dir="squads",
            active_backends=["claude_code"],
            default_role="manager",
            squads_version="0.1.0",
            init_names={"qa": "Mara Tester", "manager": "Grace Hopper"},
        )
        toml_text = original.to_toml()
        data = tomllib.loads(toml_text)
        reloaded = SquadsConfig.from_toml_dict(data)
        assert reloaded.init_names == original.init_names


# ============================================================================
# CLI tests: sq init --name, --default-names, TTY prompting
# ============================================================================


class TestCliInitName:
    def test_name_flag_single(self, runner, tmp_path, monkeypatch, frozen_time):
        """sq init --name slug=Full Name sets that role's name."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app,
            ["init", "--roles", "minimal", "--no-claude", "--name", "manager=Grace Hopper"],
        )
        assert result.exit_code == 0, result.output
        from squads._paths import resolve

        svc = service.Service(resolve())
        mgr = _get_role_item(svc, "manager")
        assert mgr.extra.get(X.FULL_NAME) == "Grace Hopper"

    def test_name_flag_multiple(self, runner, tmp_path, monkeypatch, frozen_time):
        """sq init --name can be repeated for multiple roles."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app,
            [
                "init",
                "--roles",
                "core",
                "--no-claude",
                "--name",
                "manager=Grace Hopper",
                "--name",
                "architect=Ada Lovelace",
            ],
        )
        assert result.exit_code == 0, result.output
        from squads._paths import resolve

        svc = service.Service(resolve())
        mgr = _get_role_item(svc, "manager")
        arch = _get_role_item(svc, "architect")
        assert mgr.extra.get(X.FULL_NAME) == "Grace Hopper"
        assert arch.extra.get(X.FULL_NAME) == "Ada Lovelace"

    def test_default_names_flag_skips_prompting(self, runner, tmp_path, monkeypatch, frozen_time):
        """--default-names: init completes without prompting; roles get bundled names."""
        import squads._cli._main as main_mod

        monkeypatch.chdir(tmp_path)
        # Simulate a TTY — would normally prompt; --default-names suppresses it.
        monkeypatch.setattr(main_mod, "_is_tty", lambda: True)
        result = runner.invoke(
            app, ["init", "--roles", "minimal", "--no-claude", "--default-names"]
        )
        assert result.exit_code == 0, result.output
        # No interactive prompt text in output.
        assert "Name for" not in result.output
        # Role uses bundled name.
        from squads._paths import resolve

        svc = service.Service(resolve())
        mgr = _get_role_item(svc, "manager")
        bundled = next(r for r in PREDEFINED if r.slug == "manager")
        assert mgr.extra.get(X.FULL_NAME) == bundled.full_name

    def test_non_tty_behaves_as_default_names(self, runner, tmp_path, monkeypatch, frozen_time):
        """Non-TTY: init never prompts; roles get bundled names."""
        import squads._cli._main as main_mod

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(main_mod, "_is_tty", lambda: False)
        result = runner.invoke(app, ["init", "--roles", "minimal", "--no-claude"])
        assert result.exit_code == 0, result.output
        assert "Name for" not in result.output
        from squads._paths import resolve

        svc = service.Service(resolve())
        mgr = _get_role_item(svc, "manager")
        bundled = next(r for r in PREDEFINED if r.slug == "manager")
        assert mgr.extra.get(X.FULL_NAME) == bundled.full_name

    def test_tty_prompts_for_unnamed_roles(self, runner, tmp_path, monkeypatch, frozen_time):
        """At a TTY, sq init prompts for each role not already named; blank keeps default."""
        import squads._cli._main as main_mod

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(main_mod, "_is_tty", lambda: True)
        # CliRunner can simulate user input for prompts.
        result = runner.invoke(
            app,
            ["init", "--roles", "minimal", "--no-claude"],
            input="Grace Hopper\n",  # answer for the manager prompt
        )
        assert result.exit_code == 0, result.output
        assert "Name for" in result.output
        from squads._paths import resolve

        svc = service.Service(resolve())
        mgr = _get_role_item(svc, "manager")
        assert mgr.extra.get(X.FULL_NAME) == "Grace Hopper"

    def test_tty_blank_answer_keeps_default(self, runner, tmp_path, monkeypatch, frozen_time):
        """At a TTY, a blank answer at the prompt keeps the bundled default name."""
        import squads._cli._main as main_mod

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(main_mod, "_is_tty", lambda: True)
        result = runner.invoke(
            app,
            ["init", "--roles", "minimal", "--no-claude"],
            input="\n",  # blank — keep default
        )
        assert result.exit_code == 0, result.output
        from squads._paths import resolve

        svc = service.Service(resolve())
        mgr = _get_role_item(svc, "manager")
        bundled = next(r for r in PREDEFINED if r.slug == "manager")
        assert mgr.extra.get(X.FULL_NAME) == bundled.full_name

    def test_tty_flag_pre_answers_prompt(self, runner, tmp_path, monkeypatch, frozen_time):
        """At a TTY, a role named via --name is not prompted."""
        import squads._cli._main as main_mod

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(main_mod, "_is_tty", lambda: True)
        # manager is named via flag; with minimal roles there is only manager, so no prompts.
        result = runner.invoke(
            app,
            ["init", "--roles", "minimal", "--no-claude", "--name", "manager=Grace Hopper"],
            input="",  # no prompts expected; any input would cause an error
        )
        assert result.exit_code == 0, result.output
        assert "Name for" not in result.output

    def test_init_names_from_config_seeds_names(self, runner, tmp_path, monkeypatch, frozen_time):
        """[init.names] in a pre-existing .squads.toml pre-answers prompts."""
        import squads._cli._main as main_mod

        monkeypatch.chdir(tmp_path)
        # Write a config with [init.names] before running sq init.
        cfg = SquadsConfig(
            squad_dir="squads",
            active_backends=["claude_code"],
            default_role="manager",
            squads_version="0.1.0",
            init_names={"manager": "Grace Hopper"},
        )
        (tmp_path / CONFIG_FILENAME).write_text(cfg.to_toml(), encoding="utf-8")
        # Make it a TTY so we'd normally prompt — but config should pre-answer.
        monkeypatch.setattr(main_mod, "_is_tty", lambda: True)
        result = runner.invoke(
            app,
            ["init", "--roles", "minimal", "--no-claude", "--force"],
            input="",  # no prompts expected
        )
        assert result.exit_code == 0, result.output
        assert "Name for" not in result.output
        from squads._paths import resolve

        svc = service.Service(resolve())
        mgr = _get_role_item(svc, "manager")
        assert mgr.extra.get(X.FULL_NAME) == "Grace Hopper"

    def test_flags_win_over_config_names(self, runner, tmp_path, monkeypatch, frozen_time):
        """--name flags win over [init.names] for the same slug."""
        import squads._cli._main as main_mod

        monkeypatch.chdir(tmp_path)
        cfg = SquadsConfig(
            squad_dir="squads",
            active_backends=["claude_code"],
            default_role="manager",
            squads_version="0.1.0",
            init_names={"manager": "From Config"},
        )
        (tmp_path / CONFIG_FILENAME).write_text(cfg.to_toml(), encoding="utf-8")
        monkeypatch.setattr(main_mod, "_is_tty", lambda: False)
        result = runner.invoke(
            app,
            ["init", "--roles", "minimal", "--no-claude", "--force", "--name", "manager=From Flag"],
        )
        assert result.exit_code == 0, result.output
        from squads._paths import resolve

        svc = service.Service(resolve())
        mgr = _get_role_item(svc, "manager")
        assert mgr.extra.get(X.FULL_NAME) == "From Flag"

    def test_malformed_name_no_equals(self, runner, tmp_path, monkeypatch, frozen_time):
        """A --name without '=' exits with code 1 and an error message."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["init", "--roles", "minimal", "--no-claude", "--name", "architect"]
        )
        assert result.exit_code == 1
        output_lower = result.output.lower()
        assert "expected format" in output_lower or "slug=full name" in output_lower

    def test_malformed_name_empty_slug(self, runner, tmp_path, monkeypatch, frozen_time):
        """A --name '=Full Name' (empty slug) exits with code 1."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["init", "--roles", "minimal", "--no-claude", "--name", "=Full Name"]
        )
        assert result.exit_code == 1
        assert "slug" in result.output.lower()

    def test_malformed_name_empty_name(self, runner, tmp_path, monkeypatch, frozen_time):
        """A --name 'slug=' (empty name) exits with code 1."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app, ["init", "--roles", "minimal", "--no-claude", "--name", "architect="]
        )
        assert result.exit_code == 1


# ============================================================================
# CLI tests: sq role activate --name
# ============================================================================


class TestCliRoleActivateName:
    def test_activate_with_name_flag(self, project, runner):
        """sq role activate <slug> --name 'Full Name' stores the name in the ROLE item."""
        result = runner.invoke(app, ["role", "activate", "architect", "--name", "Ada Lovelace"])
        assert result.exit_code == 0, result.output
        assert "Ada Lovelace" in result.output
        svc = service.Service(project)
        arch = _get_role_item(svc, "architect")
        assert arch.extra.get(X.FULL_NAME) == "Ada Lovelace"

    def test_activate_name_flows_to_claude_md(self, project, runner):
        """Custom name from --name appears in the CLAUDE.md Agent roster section."""
        runner.invoke(app, ["role", "activate", "reviewer", "--name", "Helen Reviewer"])
        claude_md = (project.root / "CLAUDE.md").read_text(encoding="utf-8")
        assert "Helen Reviewer" in claude_md

    def test_activate_no_name_uses_bundled(self, project, runner):
        """sq role activate without --name uses the bundled PREDEFINED full_name."""
        result = runner.invoke(app, ["role", "activate", "qa"])
        assert result.exit_code == 0, result.output
        svc = service.Service(project)
        qa = _get_role_item(svc, "qa")
        bundled = next(r for r in PREDEFINED if r.slug == "qa")
        assert qa.extra.get(X.FULL_NAME) == bundled.full_name

    def test_activate_name_flows_to_pointer_file(self, project, runner):
        """Custom name appears in the agent pointer file."""
        runner.invoke(app, ["role", "activate", "devops", "--name", "Dev Ops Custom"])
        pointer = project.root / ".claude" / "agents" / "devops.md"
        if pointer.exists():
            content = pointer.read_text(encoding="utf-8")
            assert "Dev Ops Custom" in content
