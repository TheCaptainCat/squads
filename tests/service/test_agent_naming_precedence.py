"""Agent naming precedence at the service layer: explicit name > TOML role-override
name > bundled default, flowing into the ROLE item's extra.full_name and CLAUDE.md.

CLI-surface naming (--name flag parsing, TTY prompting) lives in
tests/cli/test_init_naming_flags.py; the [init.names] config-model round-trip lives in
tests/unit/test_init_names_config.py.
"""

import pytest

from squads._models._extras import ExtraKey as X
from squads._roles._catalog import PREDEFINED
from squads._services import _service as service

pytestmark = pytest.mark.anyio


async def _role_item(svc, slug: str):
    for item in await svc.list_items(item_type="role"):
        if item.extra.get(X.SLUG) == slug:
            return item
    raise AssertionError(f"no ROLE item found for slug {slug!r}")


class TestActivateRoleName:
    async def test_explicit_name_wins_over_the_bundled_default(self, project, svc) -> None:
        item = await svc.activate_role("architect", name="Ada Lovelace")
        assert item.extra.get(X.FULL_NAME) == "Ada Lovelace"

    async def test_explicit_name_wins_over_a_toml_role_override_name(self, project, svc) -> None:
        overrides_dir = project.squad_dir / ".overrides" / "roles"
        overrides_dir.mkdir(parents=True, exist_ok=True)
        (overrides_dir / "qa.toml").write_text('full_name = "TOML QA"\n', encoding="utf-8")
        item = await svc.activate_role("qa", name="Grace Tester")
        assert item.extra.get(X.FULL_NAME) == "Grace Tester"

    async def test_no_name_falls_back_to_the_bundled_default(self, project, svc) -> None:
        item = await svc.activate_role("reviewer")
        bundled = next(r for r in PREDEFINED if r.slug == "reviewer")
        assert item.extra.get(X.FULL_NAME) == bundled.full_name

    async def test_no_name_falls_back_to_a_toml_role_override_name(self, project) -> None:
        overrides_dir = project.squad_dir / ".overrides" / "roles"
        overrides_dir.mkdir(parents=True, exist_ok=True)
        (overrides_dir / "devops.toml").write_text('full_name = "Ops Override"\n', encoding="utf-8")
        item = await service.Service(project).activate_role("devops")
        assert item.extra.get(X.FULL_NAME) == "Ops Override"


class TestInitNames:
    async def test_names_kwarg_writes_full_name_onto_each_role_item(
        self, tmp_path, monkeypatch, frozen_time
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = await service.init(
            root=tmp_path,
            roles_spec="core",
            no_claude=True,
            names={"architect": "Ada Lovelace", "manager": "Grace Hopper"},
        )
        svc = service.Service(result.paths)
        assert (await _role_item(svc, "architect")).extra.get(X.FULL_NAME) == "Ada Lovelace"
        assert (await _role_item(svc, "manager")).extra.get(X.FULL_NAME) == "Grace Hopper"

    async def test_a_role_absent_from_names_uses_the_bundled_default(
        self, tmp_path, monkeypatch, frozen_time
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = await service.init(
            root=tmp_path, roles_spec="core", no_claude=True, names={"architect": "Ada Lovelace"}
        )
        svc = service.Service(result.paths)
        mgr = await _role_item(svc, "manager")
        bundled = next(r for r in PREDEFINED if r.slug == "manager")
        assert mgr.extra.get(X.FULL_NAME) == bundled.full_name

    async def test_names_are_persisted_to_the_init_names_config_section(
        self, tmp_path, monkeypatch, frozen_time
    ) -> None:
        monkeypatch.chdir(tmp_path)
        await service.init(
            root=tmp_path, roles_spec="minimal", no_claude=True, names={"manager": "Grace Hopper"}
        )
        text = (tmp_path / ".squads.toml").read_text(encoding="utf-8")
        assert "[init.names]" in text
        assert 'manager = "Grace Hopper"' in text

    async def test_no_names_writes_no_init_names_section(
        self, tmp_path, monkeypatch, frozen_time
    ) -> None:
        monkeypatch.chdir(tmp_path)
        await service.init(root=tmp_path, roles_spec="minimal", no_claude=True)
        text = (tmp_path / ".squads.toml").read_text(encoding="utf-8")
        assert "[init.names]" not in text

    async def test_custom_names_reach_the_claude_md_agent_roster(
        self, tmp_path, monkeypatch, frozen_time
    ) -> None:
        monkeypatch.chdir(tmp_path)
        await service.init(
            root=tmp_path, roles_spec="minimal", no_claude=False, names={"manager": "Grace Hopper"}
        )
        assert "Grace Hopper" in (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
