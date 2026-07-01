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
- F5 (REV-265): a real build error on a resolved custom type propagates rather than
  silently becoming "No such command".
- F6 (REV-265): every non-meta built-in work type declares at least one alias so it
  appears in the alias cheatsheet.
"""

from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from squads._cli import _CustomTypeGroup, app  # pyright: ignore[reportPrivateUsage]
from squads._models._enums import ItemType
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
        """Alias registration reads ItemSpec.aliases from the bundled spec.

        The authoritative alias values live in default_workflow.toml (ItemSpec.aliases).
        TYPE_ALIASES has been retired (TASK-267); this test verifies that the spec's
        aliases are non-empty for every work type (the actual values are locked by
        test_golden_aliases in test_workflow_spec.py).
        """
        from squads._workflow import bundled_spec

        spec = bundled_spec()
        for item_type in ItemType:
            if item_type.value not in spec.work_types():
                continue  # meta types have no aliases
            spec_aliases = spec.items[item_type.value].aliases
            assert spec_aliases, (
                f"{item_type.value}: spec declares no aliases — did default_workflow.toml change?"
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


# ---------------------------------------------------------------------------
# F5 (REV-000265) — broad except must NOT swallow real build errors for a
# resolved custom type (only spec-resolution failures are fail-soft).
# ---------------------------------------------------------------------------


class TestF5ExceptNarrowing:
    """REV-000265 F5: a genuine build error for a declared custom type must propagate.

    Once ``_CustomTypeGroup.get_command`` confirms ``canonical`` is a declared custom
    type, errors in ``build_item_app`` or ``typer.main.get_command`` are real failures
    for a visible, user-declared type.  They must not be silently swallowed into Click's
    "No such command" response.

    Same contract for ``_CustomCreateGroup.get_command``.
    """

    def test_resource_group_build_error_propagates(
        self, runner: CliRunner, tmp_path: Path, monkeypatch
    ) -> None:
        """A RuntimeError from build_item_app propagates instead of becoming 'No such command'.

        We monkey-patch ``build_item_app`` to raise after ``canonical`` is confirmed as
        a declared custom type.  The old broad-except swallowed this into ``None``
        (→ "No such command").  After F5 the exception must escape the handler so the
        CliRunner catches it (exit_code != 0 and NOT the "No such command" message).
        """
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
        _write_override(tmp_path / "squads")

        # Inject a build failure: after canonical is resolved, raise before caching.
        with patch(
            "squads._cli._items.build_item_app",
            side_effect=RuntimeError("injected build failure"),
        ):
            result = runner.invoke(app, ["incident", "--help"])

        # The error must NOT have been swallowed into "No such command".
        assert "No such command" not in result.output, (
            "Build error was silently swallowed into 'No such command' — F5 not fixed"
        )
        # The injected RuntimeError must have surfaced (non-zero exit or exception).
        assert result.exit_code != 0 or result.exception is not None, (
            "Expected a non-zero exit or exception when build_item_app raises"
        )

    def test_create_group_build_error_propagates(
        self, runner: CliRunner, tmp_path: Path, monkeypatch
    ) -> None:
        """Same contract for _CustomCreateGroup: build error propagates, not 'No such command'.

        Monkey-patch ``_build_create_cmd`` to raise after the spec confirms the type.
        """
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
        _write_override(tmp_path / "squads")

        with patch(
            "squads._cli._create._build_create_cmd",
            side_effect=RuntimeError("injected create-build failure"),
        ):
            result = runner.invoke(app, ["create", "incident", "--help"])

        assert "No such command" not in result.output, (
            "Create-group build error was silently swallowed into 'No such command' — F5 not fixed"
        )
        assert result.exit_code != 0 or result.exception is not None, (
            "Expected a non-zero exit or exception when _build_create_cmd raises"
        )

    def test_spec_resolution_error_still_degrades_gracefully(
        self, runner: CliRunner, tmp_path: Path, monkeypatch
    ) -> None:
        """Errors during spec resolution (before canonical is confirmed) still degrade gracefully.

        An invalid/unresolvable spec must never crash ``sq --help``.  This is the
        fail-soft guarantee preserved by the narrow except in the resolution region.
        """
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])

        # Corrupt the override so spec resolution raises.
        override_dir = tmp_path / "squads" / ".overrides"
        override_dir.mkdir(parents=True, exist_ok=True)
        (override_dir / "workflow.toml").write_text("[[invalid toml", encoding="utf-8")

        # sq --help must still succeed (fail-soft on spec resolution errors).
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0, (
            f"sq --help crashed with an invalid override:\n{result.output}"
        )


# ---------------------------------------------------------------------------
# F6 (REV-000265) — defence: every non-meta built-in work type must declare
# at least one alias so it appears in the workflow alias cheatsheet.
# ---------------------------------------------------------------------------


def test_f6_all_builtin_work_types_have_aliases() -> None:
    """REV-000265 F6: every non-meta work type in the bundled spec declares an alias.

    The alias cheatsheet in workflow.md.j2 only renders a row when
    ``item_spec.aliases`` is truthy.  This test catches a future built-in work
    type added with no alias — it would silently vanish from the cheatsheet with
    no other signal.

    Constraint: this is a *defence* test.  It must not change when new aliases are
    added to existing types (it only asserts non-empty, not specific values).
    """
    from squads._workflow import bundled_spec

    spec = bundled_spec()
    alias_less: list[str] = []
    for type_name in spec.work_types():
        item_spec = spec.items[type_name]
        if item_spec.is_meta:
            continue  # meta types are excluded from the alias table by the template guard
        if not item_spec.aliases:
            alias_less.append(type_name)

    assert not alias_less, (
        f"Non-meta work type(s) declared no aliases and would be silently dropped from "
        f"the alias cheatsheet: {alias_less!r}.  Add at least one alias to the spec "
        f"(default_workflow.toml) or the workflow.md.j2 guard needs updating."
    )
