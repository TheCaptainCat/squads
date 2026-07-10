"""sq init --name / --default-names / TTY prompting, and sq role activate --name, at the
CLI surface. Naming precedence itself (the service-level facts) lives in
tests/service/test_agent_naming_precedence.py.
"""

import pytest

from squads._cli import app
from squads._models._config import CONFIG_FILENAME, SquadsConfig
from squads._models._extras import ExtraKey as X
from squads._roles._catalog import PREDEFINED
from squads._services import _service as service

pytestmark = pytest.mark.anyio


def _role_item_sync(svc, slug: str):
    import anyio

    async def _get():
        for item in await svc.list_items(item_type="role"):
            if item.extra.get(X.SLUG) == slug:
                return item
        raise AssertionError(f"no ROLE item found for slug {slug!r}")

    return anyio.run(_get)


class TestNameFlag:
    def test_single_name_flag_sets_that_roles_name(
        self, runner, tmp_path, monkeypatch, frozen_time
    ):
        monkeypatch.chdir(tmp_path)
        r = runner.invoke(
            app,
            [
                "init",
                "--no-seed-skills",
                "--roles",
                "minimal",
                "--no-claude",
                "--name",
                "manager=Grace Hopper",
            ],
        )
        assert r.exit_code == 0, r.output
        from squads._paths import resolve

        svc = service.Service(resolve())
        assert _role_item_sync(svc, "manager").extra.get(X.FULL_NAME) == "Grace Hopper"

    def test_name_flag_can_be_repeated_for_multiple_roles(
        self, runner, tmp_path, monkeypatch, frozen_time
    ):
        monkeypatch.chdir(tmp_path)
        r = runner.invoke(
            app,
            [
                "init",
                "--no-seed-skills",
                "--roles",
                "core",
                "--no-claude",
                "--name",
                "manager=Grace Hopper",
                "--name",
                "architect=Ada Lovelace",
            ],
        )
        assert r.exit_code == 0, r.output
        from squads._paths import resolve

        svc = service.Service(resolve())
        assert _role_item_sync(svc, "manager").extra.get(X.FULL_NAME) == "Grace Hopper"
        assert _role_item_sync(svc, "architect").extra.get(X.FULL_NAME) == "Ada Lovelace"

    def test_malformed_name_missing_equals_sign_exits_1(
        self, runner, tmp_path, monkeypatch, frozen_time
    ):
        monkeypatch.chdir(tmp_path)
        r = runner.invoke(
            app,
            [
                "init",
                "--no-seed-skills",
                "--roles",
                "minimal",
                "--no-claude",
                "--name",
                "architect",
            ],
        )
        assert r.exit_code == 1
        out = r.output.lower()
        assert "expected format" in out or "slug=full name" in out

    def test_malformed_name_empty_slug_exits_1(self, runner, tmp_path, monkeypatch, frozen_time):
        monkeypatch.chdir(tmp_path)
        r = runner.invoke(
            app,
            [
                "init",
                "--no-seed-skills",
                "--roles",
                "minimal",
                "--no-claude",
                "--name",
                "=Full Name",
            ],
        )
        assert r.exit_code == 1
        assert "slug" in r.output.lower()

    def test_malformed_name_empty_name_exits_1(self, runner, tmp_path, monkeypatch, frozen_time):
        monkeypatch.chdir(tmp_path)
        r = runner.invoke(
            app,
            [
                "init",
                "--no-seed-skills",
                "--roles",
                "minimal",
                "--no-claude",
                "--name",
                "architect=",
            ],
        )
        assert r.exit_code == 1


class TestTtyAndDefaultNamesPrompting:
    def test_default_names_flag_never_prompts(self, runner, tmp_path, monkeypatch, frozen_time):
        import squads._cli._main as main_mod

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(main_mod, "_is_tty", lambda: True)  # would prompt without the flag
        r = runner.invoke(
            app,
            ["init", "--no-seed-skills", "--roles", "minimal", "--no-claude", "--default-names"],
        )
        assert r.exit_code == 0, r.output
        assert "Name for" not in r.output
        from squads._paths import resolve

        svc = service.Service(resolve())
        bundled = next(role for role in PREDEFINED if role.slug == "manager")
        assert _role_item_sync(svc, "manager").extra.get(X.FULL_NAME) == bundled.full_name

    def test_non_tty_behaves_as_default_names(self, runner, tmp_path, monkeypatch, frozen_time):
        import squads._cli._main as main_mod

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(main_mod, "_is_tty", lambda: False)
        r = runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal", "--no-claude"])
        assert r.exit_code == 0, r.output
        assert "Name for" not in r.output

    def test_tty_prompts_for_a_role_not_already_named(
        self, runner, tmp_path, monkeypatch, frozen_time
    ):
        import squads._cli._main as main_mod

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(main_mod, "_is_tty", lambda: True)
        r = runner.invoke(
            app,
            ["init", "--no-seed-skills", "--roles", "minimal", "--no-claude"],
            input="Grace Hopper\n",
        )
        assert r.exit_code == 0, r.output
        assert "Name for" in r.output
        from squads._paths import resolve

        svc = service.Service(resolve())
        assert _role_item_sync(svc, "manager").extra.get(X.FULL_NAME) == "Grace Hopper"

    def test_tty_blank_answer_keeps_the_bundled_default(
        self, runner, tmp_path, monkeypatch, frozen_time
    ):
        import squads._cli._main as main_mod

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(main_mod, "_is_tty", lambda: True)
        r = runner.invoke(
            app, ["init", "--no-seed-skills", "--roles", "minimal", "--no-claude"], input="\n"
        )
        assert r.exit_code == 0, r.output
        from squads._paths import resolve

        svc = service.Service(resolve())
        bundled = next(role for role in PREDEFINED if role.slug == "manager")
        assert _role_item_sync(svc, "manager").extra.get(X.FULL_NAME) == bundled.full_name

    def test_a_role_already_named_via_flag_is_not_prompted(
        self, runner, tmp_path, monkeypatch, frozen_time
    ):
        import squads._cli._main as main_mod

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(main_mod, "_is_tty", lambda: True)
        r = runner.invoke(
            app,
            [
                "init",
                "--no-seed-skills",
                "--roles",
                "minimal",
                "--no-claude",
                "--name",
                "manager=Grace Hopper",
            ],
            input="",
        )
        assert r.exit_code == 0, r.output
        assert "Name for" not in r.output

    def test_init_names_in_an_existing_config_pre_answers_the_prompt(
        self, runner, tmp_path, monkeypatch, frozen_time
    ):
        import squads._cli._main as main_mod

        monkeypatch.chdir(tmp_path)
        cfg = SquadsConfig(
            squad_dir="squads",
            active_backends=["claude_code"],
            default_role="manager",
            squads_version="0.1.0",
            init_names={"manager": "Grace Hopper"},
        )
        (tmp_path / CONFIG_FILENAME).write_text(cfg.to_toml(), encoding="utf-8")
        monkeypatch.setattr(main_mod, "_is_tty", lambda: True)
        r = runner.invoke(
            app,
            ["init", "--no-seed-skills", "--roles", "minimal", "--no-claude", "--force"],
            input="",
        )
        assert r.exit_code == 0, r.output
        assert "Name for" not in r.output
        from squads._paths import resolve

        svc = service.Service(resolve())
        assert _role_item_sync(svc, "manager").extra.get(X.FULL_NAME) == "Grace Hopper"

    def test_name_flag_wins_over_a_config_name_for_the_same_slug(
        self, runner, tmp_path, monkeypatch, frozen_time
    ):
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
        r = runner.invoke(
            app,
            [
                "init",
                "--no-seed-skills",
                "--roles",
                "minimal",
                "--no-claude",
                "--force",
                "--name",
                "manager=From Flag",
            ],
        )
        assert r.exit_code == 0, r.output
        from squads._paths import resolve

        svc = service.Service(resolve())
        assert _role_item_sync(svc, "manager").extra.get(X.FULL_NAME) == "From Flag"


class TestRoleActivateNameFlag:
    async def test_activate_with_name_stores_it_on_the_role_item(self, project, invoke) -> None:
        r = await invoke(["role", "activate", "architect", "--name", "Ada Lovelace"])
        assert r.exit_code == 0, r.output
        assert "Ada Lovelace" in r.output
        svc = service.Service(project)
        item = next(
            i for i in await svc.list_items(item_type="role") if i.extra.get(X.SLUG) == "architect"
        )
        assert item.extra.get(X.FULL_NAME) == "Ada Lovelace"

    async def test_activate_name_reaches_claude_md(self, project, invoke) -> None:
        await invoke(["role", "activate", "reviewer", "--name", "Helen Reviewer"])
        assert "Helen Reviewer" in (project.root / "CLAUDE.md").read_text(encoding="utf-8")

    async def test_activate_without_name_uses_the_bundled_default(self, project, invoke) -> None:
        r = await invoke(["role", "activate", "qa"])
        assert r.exit_code == 0, r.output
        svc = service.Service(project)
        item = next(
            i for i in await svc.list_items(item_type="role") if i.extra.get(X.SLUG) == "qa"
        )
        bundled = next(role for role in PREDEFINED if role.slug == "qa")
        assert item.extra.get(X.FULL_NAME) == bundled.full_name

    async def test_activate_name_reaches_the_agent_pointer_file(self, project, invoke) -> None:
        await invoke(["role", "activate", "devops", "--name", "Dev Ops Custom"])
        pointer = project.root / ".claude" / "agents" / "devops.md"
        if pointer.exists():
            assert "Dev Ops Custom" in pointer.read_text(encoding="utf-8")
