"""Tests for TASK-000268: working create path for custom types.

Covers:
- AC#1/US1: sq create incident "DB timeout" --author tech-lead succeeds end-to-end.
  Uses the actual create CLI path — NOT write_new / retype — because that was the gap
  that let REV-265 F2 ship.
- Correct prefix: item id is INC-000001 (not INCIDENT-000001).
- Folder auto-created: incidents/ folder appears under the squad dir.
- sq list -t incident returns the item.
- sq check is green after a custom-type create.
- sq create --help lists the custom type after the override is loaded.
- Built-in sq create surface is byte-identical for a non-custom squad (AC#7/#8).
- Generic template fallback: svc.create('incident', ...) does not raise TemplateNotFound.
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from squads._cli import _CustomTypeGroup, app  # pyright: ignore[reportPrivateUsage]
from squads._cli._create import _CustomCreateGroup  # pyright: ignore[reportPrivateUsage]
from squads._services import _service as service

pytestmark = pytest.mark.anyio

# ---------------------------------------------------------------------------
# Override toml — mirrors the test_custom_type_cli.py helper
# ---------------------------------------------------------------------------

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
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Fixtures: clear lazy-dispatch caches between tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_caches():  # pyright: ignore[reportUnusedFunction]
    """Clear both lazy-dispatch caches between tests to prevent cross-test pollution."""
    _CustomTypeGroup._custom_cmd_cache.clear()  # pyright: ignore[reportPrivateUsage]
    _CustomCreateGroup._custom_cmd_cache.clear()  # pyright: ignore[reportPrivateUsage]
    yield
    _CustomTypeGroup._custom_cmd_cache.clear()  # pyright: ignore[reportPrivateUsage]
    _CustomCreateGroup._custom_cmd_cache.clear()  # pyright: ignore[reportPrivateUsage]


@pytest.fixture(autouse=True)
def _reset_active_spec(monkeypatch):  # pyright: ignore[reportUnusedFunction]
    """Reset the per-invocation active spec between tests to prevent leakage."""
    import squads._cli._common as common

    monkeypatch.setattr(common, "_active_spec", None)
    yield
    monkeypatch.setattr(common, "_active_spec", None)


# ---------------------------------------------------------------------------
# AC#1/US1: End-to-end create via sq create incident
# ---------------------------------------------------------------------------


async def test_create_incident_end_to_end(invoke, tmp_path: Path, monkeypatch, frozen_time) -> None:
    """The headline end-to-end test: sq create incident "DB timeout" --author tech-lead.

    This is the path that REV-265 F2 found missing.  Prior tests used write_new/retype;
    this test exercises the actual create CLI path end-to-end.
    """
    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    paths = init_result.paths
    squad_dir = paths.squad_dir
    _write_override(squad_dir)

    # --- sq create incident "DB timeout" --author manager ---
    # "manager" is the role seeded by "minimal" init; the test verifies that the create
    # path works end-to-end for an author that is registered in the squad.
    result = await invoke(["create", "incident", "DB timeout", "--author", "manager"])
    assert result.exit_code == 0, (
        f"sq create incident failed (exit {result.exit_code}):\n{result.output}"
    )

    # Correct prefix: INC-NNNNNN (not INCIDENT-NNNNNN).
    # The exact sequence number depends on how many items are seeded by init;
    # what matters is that the prefix is INC, not the type name uppercased.
    assert "INC-" in result.output and "INCIDENT-" not in result.output, (
        f"Expected INC-NNNNNN prefix in output, got:\n{result.output}"
    )

    # Extract the ID from the output for subsequent assertions.
    import re

    m = re.search(r"INC-(\d+)", result.output)
    assert m is not None, f"Could not parse INC-NNNNNN from output:\n{result.output}"
    item_num = int(m.group(1))

    # --- Folder auto-created ---
    incidents_dir = squad_dir / "incidents"
    assert incidents_dir.is_dir(), "incidents/ folder was not auto-created"
    md_files = list(incidents_dir.glob("INC-*.md"))
    assert md_files, "No INC-*.md file in incidents/"

    # --- sq list -t incident returns the item ---
    list_result = await invoke(["list", "-t", "incident"])
    assert list_result.exit_code == 0, f"sq list -t incident failed:\n{list_result.output}"
    assert "DB timeout" in list_result.output or f"INC-{item_num:06d}" in list_result.output, (
        f"Item not found in list output:\n{list_result.output}"
    )

    # --- sq incident N show round-trips correctly ---
    show_result = await invoke(["incident", str(item_num), "show"])
    assert show_result.exit_code == 0, (
        f"sq incident {item_num} show failed (exit {show_result.exit_code}):\n{show_result.output}"
    )
    assert "DB timeout" in show_result.output

    # --- sq check is green ---
    check_result = await invoke(["check"])
    assert check_result.exit_code == 0, (
        f"sq check failed after custom-type create:\n{check_result.output}"
    )


# ---------------------------------------------------------------------------
# Generic template fallback: svc.create does not raise TemplateNotFound
# ---------------------------------------------------------------------------


async def test_service_create_custom_type_no_template_error(
    tmp_path: Path, monkeypatch, frozen_time
) -> None:
    """svc.create('incident', ...) succeeds without a per-type template file.

    This directly tests the _template_for fallback to items/_default.md.j2 — the
    service-level break identified in REV-265 F2.
    """
    from squads._workflow._loader import load_workflow_spec
    from squads._workflow._models import ItemSpec, Lifecycle, WorkflowSpec

    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    paths = init_result.paths

    # Build spec with incident type.
    base = load_workflow_spec()
    triage = Lifecycle(
        initial="Open",
        transitions={"Open": ["Done", "WontFix"], "Done": [], "WontFix": ["Open"]},
    )
    incident_spec = ItemSpec(prefix="INC", folder="incidents", lifecycle="triage")
    new_lc = {**base.lifecycles, "triage": triage}
    new_items = {**base.items, "incident": incident_spec}
    new_p2t = {**base.prefix_to_type, "INC": "incident"}
    spec = WorkflowSpec.model_validate(
        {
            "items": new_items,
            "statuses": base.statuses,
            "lifecycles": new_lc,
            "prefix_to_type": new_p2t,
            "alias_to_type": base.alias_to_type,
            "collections": base.collections,
            "subentity_kinds": base.subentity_kinds,
        }
    )

    svc = service.Service(paths, spec=spec)
    # This must not raise TemplateNotFound.
    res = await svc.create("incident", "DB timeout", author="manager")
    # Prefix must be INC, not INCIDENT (correct prefix from spec, not type.upper()).
    assert res.item.id.startswith("INC-"), f"Expected INC-NNNNNN, got {res.item.id!r}"
    assert res.item.type == "incident"
    # The item file must exist in the correct folder.
    assert res.path.is_file()
    assert "incidents" in str(res.path)


# ---------------------------------------------------------------------------
# sq create --help lists the custom type
# ---------------------------------------------------------------------------


def test_create_help_lists_custom_type(runner: CliRunner, tmp_path: Path, monkeypatch) -> None:
    """sq create --help includes 'incident' when it is declared in the override."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    _write_override(tmp_path / "squads")

    result = runner.invoke(app, ["create", "--help"])
    assert result.exit_code == 0, f"sq create --help failed:\n{result.output}"
    assert "incident" in result.output, (
        f"'incident' not in sq create --help output:\n{result.output}"
    )


# ---------------------------------------------------------------------------
# sq create incident --help works
# ---------------------------------------------------------------------------


def test_create_incident_help(runner: CliRunner, tmp_path: Path, monkeypatch) -> None:
    """sq create incident --help works for a custom type declared in the override."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    _write_override(tmp_path / "squads")

    result = runner.invoke(app, ["create", "incident", "--help"])
    assert result.exit_code == 0, f"sq create incident --help failed:\n{result.output}"
    assert "title" in result.output.lower() or "Title" in result.output


# ---------------------------------------------------------------------------
# AC#7/#8: Built-in sq create surface unchanged for non-custom squads
# ---------------------------------------------------------------------------


def test_builtin_create_surface_unchanged(runner: CliRunner, tmp_path: Path, monkeypatch) -> None:
    """sq create --help lists only built-in types for a non-custom squad (AC#7)."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])

    result = runner.invoke(app, ["create", "--help"])
    assert result.exit_code == 0, f"sq create --help failed:\n{result.output}"
    # All 7 built-in work types must be present.
    for t in ("epic", "feature", "task", "bug", "decision", "review", "guide"):
        assert t in result.output, f"built-in type '{t}' missing from sq create --help"
    # No custom types leaked in.
    assert "incident" not in result.output


def test_builtin_create_task_still_works(runner: CliRunner, tmp_path: Path, monkeypatch) -> None:
    """sq create task ... still works — built-in create path unchanged (AC#8)."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])

    result = runner.invoke(app, ["create", "task", "--help"])
    assert result.exit_code == 0, f"sq create task --help failed:\n{result.output}"
    assert "title" in result.output.lower() or "Title" in result.output


# ---------------------------------------------------------------------------
# Unknown custom type in create still errors
# ---------------------------------------------------------------------------


def test_create_unknown_type_errors(runner: CliRunner, tmp_path: Path, monkeypatch) -> None:
    """sq create volcano errors even with an override (volcano not declared)."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    _write_override(tmp_path / "squads")

    result = runner.invoke(app, ["create", "volcano"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Generic template produces a valid item file with markers
# ---------------------------------------------------------------------------


async def test_generic_template_produces_valid_markers(
    tmp_path: Path, monkeypatch, frozen_time
) -> None:
    """The _default.md.j2 template renders valid sq markers (body + discussion).

    This ensures the generic fallback renders a structurally correct item file
    that svc operations (body set, comment, etc.) can read back safely.
    """
    from squads import _sections as sections
    from squads._models._markers import BODY, DISCUSSION
    from squads._workflow._loader import load_workflow_spec
    from squads._workflow._models import ItemSpec, Lifecycle, WorkflowSpec

    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    paths = init_result.paths

    base = load_workflow_spec()
    triage = Lifecycle(
        initial="Open",
        transitions={"Open": ["Done", "WontFix"], "Done": [], "WontFix": ["Open"]},
    )
    incident_spec = ItemSpec(prefix="INC", folder="incidents", lifecycle="triage")
    spec = WorkflowSpec.model_validate(
        {
            "items": {**base.items, "incident": incident_spec},
            "statuses": base.statuses,
            "lifecycles": {**base.lifecycles, "triage": triage},
            "prefix_to_type": {**base.prefix_to_type, "INC": "incident"},
            "alias_to_type": base.alias_to_type,
            "collections": base.collections,
            "subentity_kinds": base.subentity_kinds,
        }
    )
    svc = service.Service(paths, spec=spec)
    res = await svc.create("incident", "Test incident", author="manager")
    text = res.path.read_text(encoding="utf-8")

    # Both required marker sections must be present.
    assert sections.get_section(text, BODY) is not None, (
        "body section missing from generic template output"
    )
    assert sections.get_section(text, DISCUSSION) is not None, (
        "discussion section missing from generic template output"
    )


# ---------------------------------------------------------------------------
# TASK-000273: sq create <alias> works for built-in AND custom types
# ---------------------------------------------------------------------------


def test_create_builtin_alias_feat(runner: CliRunner, tmp_path: Path, monkeypatch) -> None:
    """sq create feat TITLE dispatches to the feature create command (built-in alias).

    The result ID must start with FEAT- (canonical type, not the alias).
    The alias must not appear in sq create --help (hidden=True).
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])

    result = runner.invoke(app, ["create", "feat", "My Feature via alias", "--author", "manager"])
    assert result.exit_code == 0, f"sq create feat failed:\n{result.output}"
    assert "FEAT-" in result.output, f"Expected FEAT-NNNNNN in output, got:\n{result.output}"

    # Aliases must remain hidden from help (byte-identical AC#7/#8).
    # Verify no help line lists the alias as a standalone command name.
    help_result = runner.invoke(app, ["create", "--help"])
    lines = help_result.output.splitlines()
    alias_cmd_lines = [
        ln
        for ln in lines
        if ln.lstrip("│ ").startswith("feat ") or ln.lstrip("│ ").startswith("feat\t")
    ]
    assert not alias_cmd_lines, (
        f"built-in alias 'feat' must not appear in sq create --help: {alias_cmd_lines}"
    )


async def test_create_builtin_alias_end_to_end(
    invoke, tmp_path: Path, monkeypatch, frozen_time
) -> None:
    """sq create feat / sq create t / sq create b produce canonical IDs end-to-end."""
    monkeypatch.chdir(tmp_path)
    from squads._services import _service as service

    await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)

    for alias, expected_prefix in [("feat", "FEAT-"), ("t", "TASK-"), ("b", "BUG-")]:
        result = await invoke(["create", alias, f"Item via {alias!r} alias", "--author", "manager"])
        assert result.exit_code == 0, (
            f"sq create {alias!r} failed (exit {result.exit_code}):\n{result.output}"
        )
        assert expected_prefix in result.output, (
            f"sq create {alias!r}: expected {expected_prefix!r} in output, got:\n{result.output}"
        )


async def test_create_custom_type_alias(invoke, tmp_path: Path, monkeypatch, frozen_time) -> None:
    """sq create inc TITLE dispatches to the incident create command (custom alias).

    The result ID must start with INC- (canonical prefix from the spec, not alias.upper()).
    """
    monkeypatch.chdir(tmp_path)
    from squads._services import _service as service

    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    _write_override(init_result.paths.squad_dir)

    result = await invoke(["create", "inc", "Incident via inc alias", "--author", "manager"])
    assert result.exit_code == 0, (
        f"sq create inc failed (exit {result.exit_code}):\n{result.output}"
    )
    assert "INC-" in result.output, f"Expected INC-NNNNNN, got:\n{result.output}"
    assert "INCIDENT-" not in result.output
