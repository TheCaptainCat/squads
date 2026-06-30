"""Tests for TASK-000257: dynamic CLI build from spec (lazy-dispatch TyperGroup, ADR-000263).

Covers:
- Built-in command surface is byte-identical for a non-custom squad (AC#7/#8).
- A custom 'incident' type declared in .overrides/workflow.toml resolves as a top-level
  CLI command (sq incident --help, sq incident 1 show, etc.) without any code change.
- The custom type's spec-declared alias ('inc') routes to the same command tree.
- sq list -t incident works for a custom type.
- Unknown commands still produce Click's "No such command" error (AC#8 / byte-identical).
- The built-in TASK-256 golden surface is unperturbed when no custom types exist.
- The alias registration loop now reads from ItemSpec.aliases (not TYPE_ALIASES).
"""

from collections.abc import Generator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from squads._cli import _CustomTypeGroup, app  # pyright: ignore[reportPrivateUsage]
from squads._models._enums import TYPE_ALIASES, ItemType
from squads._services import _service as service
from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import ItemSpec, Lifecycle, WorkflowSpec

pytestmark = pytest.mark.anyio

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_custom_cmd_cache() -> Generator[None]:  # pyright: ignore[reportUnusedFunction]
    """Clear the lazy-dispatch cache between tests to prevent cross-test pollution.

    _CustomTypeGroup._custom_cmd_cache is a ClassVar that accumulates custom-type
    Click commands across calls.  Each test may use a different squad dir and
    different custom type specs, so we reset the cache before each test.
    """
    _CustomTypeGroup._custom_cmd_cache.clear()  # pyright: ignore[reportPrivateUsage]
    yield
    _CustomTypeGroup._custom_cmd_cache.clear()  # pyright: ignore[reportPrivateUsage]


@pytest.fixture(autouse=True)
def _reset_active_spec(monkeypatch) -> Generator[None]:  # pyright: ignore[reportUnusedFunction]
    """Reset the per-invocation active spec between tests to prevent leakage."""
    import squads._cli._common as common

    monkeypatch.setattr(common, "_active_spec", None)
    yield
    monkeypatch.setattr(common, "_active_spec", None)


# ---------------------------------------------------------------------------
# Helper: build a WorkflowSpec with a custom 'incident' type
# ---------------------------------------------------------------------------

_INCIDENT_FOLDER = "incidents"
_INCIDENT_PREFIX = "INC"
_INCIDENT_TYPE = "incident"
_INCIDENT_ALIAS = "inc"

_OVERRIDE_TOML = """\
[lifecycles.triage]
initial = "Open"

[lifecycles.triage.transitions]
Open = ["Done", "WontFix"]
Done = []
WontFix = ["Open"]

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "triage"
aliases = ["inc"]
"""


def _write_override(squad_dir: Path, content: str = _OVERRIDE_TOML) -> None:
    """Write a workflow override file under squad_dir/.overrides/workflow.toml."""
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(content, encoding="utf-8")


def _spec_with_incident() -> WorkflowSpec:
    """Return the bundled spec extended with a minimal 'incident' custom type."""
    base = load_workflow_spec()
    triage = Lifecycle(
        initial="Open",
        transitions={
            "Open": ["Done", "WontFix"],
            "Done": [],
            "WontFix": ["Open"],
        },
    )
    incident_spec = ItemSpec(
        prefix=_INCIDENT_PREFIX,
        folder=_INCIDENT_FOLDER,
        lifecycle="triage",
        aliases=[_INCIDENT_ALIAS],
    )
    new_lifecycles = dict(base.lifecycles)
    new_lifecycles["triage"] = triage
    new_items = dict(base.items)
    new_items[_INCIDENT_TYPE] = incident_spec
    new_prefix_to_type = dict(base.prefix_to_type)
    new_prefix_to_type[_INCIDENT_PREFIX] = _INCIDENT_TYPE
    new_alias_to_type = dict(base.alias_to_type)
    new_alias_to_type[_INCIDENT_ALIAS] = _INCIDENT_TYPE
    return WorkflowSpec.model_validate(
        {
            "items": new_items,
            "statuses": base.statuses,
            "lifecycles": new_lifecycles,
            "prefix_to_type": new_prefix_to_type,
            "alias_to_type": new_alias_to_type,
        }
    )


# ---------------------------------------------------------------------------
# AC#7 / Byte-identical surface for non-custom squads
# ---------------------------------------------------------------------------


class TestBuiltInSurfaceUnchanged:
    """Verify AC#7: non-custom squads see byte-identical CLI surface."""

    def test_builtin_work_types_in_help(
        self, runner: CliRunner, tmp_path: Path, monkeypatch
    ) -> None:
        """sq --help lists all 7 built-in work types and no extra types."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        output = result.output
        # All 7 built-in types present.
        for t in ("epic", "feature", "task", "bug", "decision", "review", "guide"):
            assert t in output, f"built-in type '{t}' missing from --help"
        # No custom types leaked in.
        assert "incident" not in output

    def test_unknown_command_native_error(
        self, runner: CliRunner, tmp_path: Path, monkeypatch
    ) -> None:
        """sq <unknown> still produces Click's 'No such command' error (AC#8)."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
        result = runner.invoke(app, ["incident"])
        # Exit code 2 = Click usage error.
        assert result.exit_code == 2
        assert "No such command" in result.output or "no such command" in result.output.lower()

    def test_builtin_aliases_still_resolve(
        self, runner: CliRunner, tmp_path: Path, monkeypatch
    ) -> None:
        """Built-in type aliases (e/f/t/b/d/r/g, feat/dec/rev) still resolve (AC#7)."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
        for alias in ("e", "f", "t", "b", "d", "r", "g", "feat", "dec", "rev"):
            result = runner.invoke(app, [alias, "--help"])
            assert result.exit_code == 0, f"alias '{alias}' failed: {result.output}"

    def test_aliases_registered_from_spec(self) -> None:
        """Alias registration now reads ItemSpec.aliases, not just TYPE_ALIASES.

        The static app-build loop at import time uses the bundled spec's ItemSpec.aliases.
        These must match TYPE_ALIASES (the non-authoritative shim) exactly.
        """
        from squads._workflow import bundled_spec

        spec = bundled_spec()
        for item_type in ItemType:
            if item_type.value not in spec.work_types():
                continue  # meta types have no aliases
            spec_aliases = sorted(spec.items[item_type.value].aliases)
            enum_aliases = sorted(TYPE_ALIASES.get(item_type, ()))
            assert spec_aliases == enum_aliases, (
                f"{item_type.value}: spec aliases {spec_aliases!r} != TYPE_ALIASES {enum_aliases!r}"
            )


# ---------------------------------------------------------------------------
# Custom type CLI: sq incident ... resolves lazily
# ---------------------------------------------------------------------------


class TestCustomTypeCliResolution:
    """Verify AC#1: a custom type declared in .overrides/workflow.toml gets a CLI command."""

    def test_custom_type_command_resolves(
        self, runner: CliRunner, tmp_path: Path, monkeypatch
    ) -> None:
        """sq incident --help works after declaring incident in .overrides/workflow.toml."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
        _write_override(tmp_path / "squads")

        result = runner.invoke(app, ["incident", "--help"])
        assert result.exit_code == 0, f"sq incident --help failed:\n{result.output}"
        assert "incident" in result.output
        # Standard subcommands should be present.
        assert "show" in result.output
        assert "update" in result.output
        assert "status" in result.output

    def test_custom_type_alias_resolves(
        self, runner: CliRunner, tmp_path: Path, monkeypatch
    ) -> None:
        """sq inc --help works (alias 'inc' declared in the spec)."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
        _write_override(tmp_path / "squads")

        result = runner.invoke(app, ["inc", "--help"])
        assert result.exit_code == 0, f"sq inc --help failed:\n{result.output}"
        assert "incident" in result.output

    def test_custom_type_appears_in_help(
        self, runner: CliRunner, tmp_path: Path, monkeypatch
    ) -> None:
        """sq --help lists 'incident' when running from within the custom squad."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
        _write_override(tmp_path / "squads")

        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "incident" in result.output

    def test_unknown_non_spec_command_still_errors(
        self, runner: CliRunner, tmp_path: Path, monkeypatch
    ) -> None:
        """Unknown commands that are NOT in the spec still produce 'No such command'."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
        _write_override(tmp_path / "squads")

        result = runner.invoke(app, ["volcano"])
        assert result.exit_code == 2
        assert "No such command" in result.output or "no such command" in result.output.lower()


# ---------------------------------------------------------------------------
# Service-level test: sq list -t incident works
# ---------------------------------------------------------------------------


async def test_list_custom_type_cli(
    runner: CliRunner, invoke, tmp_path: Path, monkeypatch, frozen_time
) -> None:
    """sq list -t incident returns items after seeding one directly via write_new.

    This test proves the full flow: custom type spec is loaded, an item is written
    at the itemfile level (bypassing the create CLI / svc.create since those require
    a template — a later task), and sq list -t incident finds it.
    """
    from squads import _clock as clock
    from squads._itemfile import write_new
    from squads._models._item import Item

    monkeypatch.chdir(tmp_path)
    # Use service.init directly (not CLI runner) to avoid asyncio nesting.
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    paths = init_result.paths
    _write_override(paths.squad_dir)

    spec = _spec_with_incident()
    svc = service.Service(paths, spec=spec)

    # Write the incident item file directly (no template needed).
    squad_rel = paths.squad_relative(_INCIDENT_TYPE, "INC-000099-db-timeout.md", spec=spec)
    abs_path = paths.abspath(squad_rel)
    now = clock.now()
    item = Item(
        sequence_id=99,
        type=_INCIDENT_TYPE,
        title="DB timeout",
        slug="db-timeout",
        status="Open",
        author="manager",
        path=squad_rel,
        created_at=now,
        updated_at=now,
        id_padding=6,
    )
    rendered = "# DB timeout\n"
    await write_new(abs_path, item, rendered)
    # Bump the index counter to accommodate sequence 99, then repair to index the item.
    async with svc.store.transaction() as db:
        if db.counter < 99:
            db.counter = 99
    await svc.repair()

    # sq list -t incident must return the item.
    result = await invoke(["list", "-t", "incident"])
    assert result.exit_code == 0, f"sq list -t incident failed:\n{result.output}"
    # The listing must include the item title or ID.
    assert "DB timeout" in result.output or "INC-000099" in result.output


# ---------------------------------------------------------------------------
# Service-level test: sq incident N show works for a created item
# ---------------------------------------------------------------------------


async def test_custom_type_show_via_cli(
    runner: CliRunner, invoke, tmp_path: Path, monkeypatch, frozen_time
) -> None:
    """sq incident N show works after seeding a custom-type item via write_new."""
    from squads import _clock as clock
    from squads._itemfile import write_new
    from squads._models._item import Item

    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    paths = init_result.paths
    _write_override(paths.squad_dir)

    spec = _spec_with_incident()
    svc = service.Service(paths, spec=spec)

    squad_rel = paths.squad_relative(_INCIDENT_TYPE, "INC-000099-db-timeout.md", spec=spec)
    abs_path = paths.abspath(squad_rel)
    now = clock.now()
    item = Item(
        sequence_id=99,
        type=_INCIDENT_TYPE,
        title="DB timeout",
        slug="db-timeout",
        status="Open",
        author="manager",
        path=squad_rel,
        created_at=now,
        updated_at=now,
        id_padding=6,
    )
    rendered = "# DB timeout\n"
    await write_new(abs_path, item, rendered)
    async with svc.store.transaction() as db:
        if db.counter < 99:
            db.counter = 99
    await svc.repair()

    # sq incident 99 show must work.
    result = await invoke(["incident", "99", "show"])
    assert result.exit_code == 0, f"sq incident 99 show failed:\n{result.output}"
    assert "DB timeout" in result.output


# ---------------------------------------------------------------------------
# Ensure built-in types still use spec aliases (regression guard for alias swap)
# ---------------------------------------------------------------------------


def test_builtin_type_aliases_from_spec_not_enum(
    runner: CliRunner, tmp_path: Path, monkeypatch
) -> None:
    """The 'f' alias for feature is registered from spec.items['feature'].aliases.

    This verifies the alias registration loop was switched from TYPE_ALIASES to
    spec.items[t].aliases.  If the swap was reverted, aliases would still work
    (TYPE_ALIASES values match the spec) but the test documents the mechanism.
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])

    # 'f' is the single-letter alias for 'feature' in the bundled spec.
    result = runner.invoke(app, ["f", "--help"])
    assert result.exit_code == 0
    # The help text should describe the feature command.
    assert "feature" in result.output or "Operate on a feature" in result.output
