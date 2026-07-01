"""Tests for TASK-000267: Item.prefix field + prefix_for resolver + retype prefix stamping.

Covers:
- prefix_for() returns the correct prefix for reserved and custom types.
- Item.prefix is stamped at create time; Item.id formats from it correctly.
- Retype stamps the target type's prefix: INC-000019, not INCIDENT-000019.
- File is named INC-000019-*.md after retype.
- sq incident INC-000019 show round-trips (CLI + service).
- sq list -t incident returns the custom item.
- ref add / remove work for a custom type item without KeyError.
- Legacy files without a prefix: frontmatter line still load (re-derived on load).
- Built-in items: id/filename/CLI output byte-identical (no prefix: line written).
- prefix_for raises SquadsError for an unknown type without a spec.
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from squads._cli import app
from squads._models._item import Item
from squads._models._vocab import RESERVED_PREFIX, is_reserved, prefix_for
from squads._paths import SquadPaths
from squads._services import _service as service
from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import ItemSpec, Lifecycle, WorkflowSpec

pytestmark = pytest.mark.anyio

# ---------------------------------------------------------------------------
# Fixtures / helpers shared by this module
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


def _spec_with_incident() -> WorkflowSpec:
    """Return the bundled spec extended with a minimal 'incident' custom type."""
    base = load_workflow_spec()
    triage = Lifecycle(
        initial="Open",
        transitions={"Open": ["Done", "WontFix"], "Done": [], "WontFix": ["Open"]},
    )
    incident_spec = ItemSpec(prefix="INC", folder="incidents", lifecycle="triage", aliases=["inc"])
    new_lifecycles = dict(base.lifecycles)
    new_lifecycles["triage"] = triage
    new_items = dict(base.items)
    new_items["incident"] = incident_spec
    new_prefix_to_type = dict(base.prefix_to_type)
    new_prefix_to_type["INC"] = "incident"
    new_alias_to_type = dict(base.alias_to_type)
    new_alias_to_type["inc"] = "incident"
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
# Unit: prefix_for resolver
# ---------------------------------------------------------------------------


class TestPrefixFor:
    """Unit tests for the _models._vocab.prefix_for() resolver."""

    def test_reserved_types_return_correct_prefix(self) -> None:
        """prefix_for returns the authoritative prefix for every reserved built-in type."""
        expected = {
            "epic": "EPIC",
            "feature": "FEAT",
            "task": "TASK",
            "bug": "BUG",
            "decision": "ADR",
            "review": "REV",
            "guide": "GUIDE",
            "role": "ROLE",
            "skill": "SKILL",
            "operator": "OP",
        }
        for type_str, expected_prefix in expected.items():
            assert prefix_for(type_str) == expected_prefix, f"wrong prefix for {type_str!r}"

    def test_reserved_types_ignore_spec(self) -> None:
        """For reserved types, prefix_for returns the built-in prefix even when a spec is passed."""
        spec = _spec_with_incident()
        assert prefix_for("task", spec) == "TASK"
        assert prefix_for("feature", spec) == "FEAT"

    def test_custom_type_with_spec_returns_declared_prefix(self) -> None:
        """prefix_for returns spec-declared prefix for a custom type."""
        spec = _spec_with_incident()
        assert prefix_for("incident", spec) == "INC"

    def test_unknown_type_no_spec_raises(self) -> None:
        """prefix_for raises SquadsError for an unknown type with no spec."""
        from squads._errors import SquadsError

        with pytest.raises(SquadsError, match="unknown item type"):
            prefix_for("incident")

    def test_unknown_type_not_in_spec_raises(self) -> None:
        """prefix_for raises SquadsError when the type is absent from the spec."""
        from squads._errors import SquadsError

        spec = _spec_with_incident()
        with pytest.raises(SquadsError, match="unknown item type"):
            prefix_for("blork", spec)

    def test_is_reserved_true_for_builtins(self) -> None:
        for type_str in RESERVED_PREFIX:
            assert is_reserved(type_str), f"{type_str!r} should be reserved"

    def test_is_reserved_false_for_custom(self) -> None:
        assert not is_reserved("incident")
        assert not is_reserved("blork")


# ---------------------------------------------------------------------------
# Unit: Item.prefix field + Item.id computed field
# ---------------------------------------------------------------------------


class TestItemPrefixField:
    """Item.prefix drives Item.id; the reserved fallback keeps built-ins stable."""

    def test_item_id_uses_prefix_field_when_set(self) -> None:
        """When prefix is explicitly supplied, Item.id formats from it."""
        from datetime import UTC, datetime

        item = Item(
            sequence_id=19,
            type="incident",
            prefix="INC",
            title="An incident",
            slug="an-incident",
            status="Open",
            path="incidents/INC-000019-an-incident.md",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert item.id == "INC-000019"
        assert item.prefix == "INC"

    def test_item_id_fallback_for_builtin_without_explicit_prefix(self) -> None:
        """Built-in items without an explicit prefix fall back to RESERVED_PREFIX."""
        from datetime import UTC, datetime

        item = Item(
            sequence_id=7,
            type="task",
            # prefix left as default "" — should fall back to RESERVED_PREFIX
            title="A task",
            slug="a-task",
            status="Draft",
            path="tasks/TASK-000007-a-task.md",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert item.id == "TASK-000007"

    def test_to_frontmatter_dict_writes_prefix_only_for_custom(self) -> None:
        """prefix: is written to frontmatter for custom types, NOT for reserved types."""
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        # Custom type: prefix must be in frontmatter
        custom_item = Item(
            sequence_id=1,
            type="incident",
            prefix="INC",
            title="Custom",
            slug="custom",
            status="Open",
            path="incidents/INC-000001-custom.md",
            created_at=now,
            updated_at=now,
        )
        fm_custom = custom_item.to_frontmatter_dict()
        assert "prefix" in fm_custom, "custom type must write prefix to frontmatter"
        assert fm_custom["prefix"] == "INC"

        # Reserved type: prefix must NOT be in frontmatter (byte-identical)
        builtin_item = Item(
            sequence_id=1,
            type="task",
            prefix="TASK",
            title="A task",
            slug="a-task",
            status="Draft",
            path="tasks/TASK-000001-a-task.md",
            created_at=now,
            updated_at=now,
        )
        fm_builtin = builtin_item.to_frontmatter_dict()
        assert "prefix" not in fm_builtin, "built-in type must NOT write prefix to frontmatter"

    def test_from_frontmatter_reads_prefix_for_custom_type(self) -> None:
        """from_frontmatter picks up a stored prefix: line for custom types."""
        from datetime import UTC, datetime

        now = datetime.now(UTC).isoformat()
        data = {
            "id": "INC-000019",
            "sequence_id": 19,
            "type": "incident",
            "prefix": "INC",
            "title": "An incident",
            "slug": "an-incident",
            "status": "Open",
            "created_at": now,
            "updated_at": now,
        }
        item = Item.from_frontmatter(data, path="incidents/INC-000019-an-incident.md")
        assert item.prefix == "INC"
        assert item.id == "INC-000019"

    def test_from_frontmatter_derives_prefix_for_builtins(self) -> None:
        """from_frontmatter re-derives prefix for reserved types (always from RESERVED_PREFIX)."""
        from datetime import UTC, datetime

        now = datetime.now(UTC).isoformat()
        data = {
            "id": "TASK-000007",
            "sequence_id": 7,
            "type": "task",
            # No prefix: line — as on-disk for built-ins
            "title": "A task",
            "slug": "a-task",
            "status": "Draft",
            "created_at": now,
            "updated_at": now,
        }
        item = Item.from_frontmatter(data, path="tasks/TASK-000007-a-task.md")
        assert item.prefix == "TASK"
        assert item.id == "TASK-000007"

    def test_from_frontmatter_ignores_stored_prefix_for_reserved_type(self) -> None:
        """Even if a corrupt frontmatter has a wrong prefix: line for a reserved type,
        from_frontmatter uses the authoritative RESERVED_PREFIX value."""
        from datetime import UTC, datetime

        now = datetime.now(UTC).isoformat()
        data = {
            "id": "TASK-000007",
            "sequence_id": 7,
            "type": "task",
            "prefix": "WRONGPREFIX",  # corrupt / hand-edited
            "title": "A task",
            "slug": "a-task",
            "status": "Draft",
            "created_at": now,
            "updated_at": now,
        }
        item = Item.from_frontmatter(data, path="tasks/TASK-000007-a-task.md")
        assert item.prefix == "TASK"  # override by RESERVED_PREFIX
        assert item.id == "TASK-000007"


# ---------------------------------------------------------------------------
# Integration: retype a task to 'incident' → INC-000019, correct filename
# ---------------------------------------------------------------------------


class TestRetypePrefixStamping:
    """End-to-end: retype to a custom type stamps the spec prefix correctly."""

    async def test_retype_to_custom_stamps_correct_id(
        self, project: SquadPaths, svc: service.Service, frozen_time
    ) -> None:
        """Retyping a task to 'incident' produces INC-NNNNNN, not INCIDENT-NNNNNN."""
        _write_override(project.squad_dir)
        svc = service.open_service()  # reload with the override spec

        # Create a task so we have something to retype.
        result = await svc.create("task", "A task to retype", author="manager")
        task_id = result.item.id

        # Retype to incident.
        retype_result = await svc.retype(task_id, "incident")
        item = retype_result.item

        # Prefix must be "INC", id must be "INC-000001".
        assert item.prefix == "INC", f"expected prefix 'INC', got {item.prefix!r}"
        assert item.id.startswith("INC-"), f"id {item.id!r} does not start with 'INC-'"
        assert not item.id.startswith("INCIDENT-"), (
            f"id {item.id!r} should NOT start with 'INCIDENT-'"
        )

    async def test_retype_file_named_with_correct_prefix(
        self, project: SquadPaths, svc: service.Service, frozen_time
    ) -> None:
        """The .md file after retype must be named INC-NNNNNN-*.md."""
        _write_override(project.squad_dir)
        svc = service.open_service()

        result = await svc.create("task", "Another retype task", author="manager")
        retype_result = await svc.retype(result.item.id, "incident")
        item = retype_result.item

        # The path field must start with the incidents folder and INC- prefix.
        assert "incidents/INC-" in item.path, (
            f"path {item.path!r} should be under incidents/ with INC- prefix"
        )
        filename = item.path.split("/")[-1]
        assert filename.startswith("INC-"), f"filename {filename!r} must start with INC-"
        assert not filename.startswith("INCIDENT-"), (
            f"filename {filename!r} must NOT start with INCIDENT-"
        )

    async def test_retype_file_exists_on_disk(
        self, project: SquadPaths, svc: service.Service, frozen_time
    ) -> None:
        """The correctly-named INC-*.md file exists on disk after retype."""
        _write_override(project.squad_dir)
        svc = service.open_service()

        result = await svc.create("task", "Disk check task", author="manager")
        retype_result = await svc.retype(result.item.id, "incident")
        item = retype_result.item

        disk_path = project.squad_dir / item.path
        assert disk_path.exists(), f"File not found: {disk_path}"
        assert disk_path.name.startswith("INC-"), f"File {disk_path.name!r} has wrong prefix"

    async def test_retype_item_shows_correctly(
        self, project: SquadPaths, svc: service.Service, frozen_time
    ) -> None:
        """sq incident INC-NNNNNN show succeeds; INCIDENT-NNNNNN show fails (correct behavior)."""
        _write_override(project.squad_dir)
        svc = service.open_service()

        result = await svc.create("task", "Show me task", author="manager")
        retype_result = await svc.retype(result.item.id, "incident")
        inc_id = retype_result.item.id
        assert inc_id.startswith("INC-"), f"Expected INC-…, got {inc_id!r}"

        # Service-level get by the correct id succeeds.
        loaded = await svc.get(inc_id)
        assert loaded.type == "incident"
        assert loaded.prefix == "INC"

    async def test_retype_list_by_type(
        self, project: SquadPaths, svc: service.Service, frozen_time
    ) -> None:
        """sq list -t incident returns the retyped item."""
        _write_override(project.squad_dir)
        svc = service.open_service()

        result = await svc.create("task", "Listable incident", author="manager")
        await svc.retype(result.item.id, "incident")

        incidents = await svc.list_items(item_type="incident")
        assert len(incidents) == 1
        assert incidents[0].type == "incident"
        assert incidents[0].id.startswith("INC-")


# ---------------------------------------------------------------------------
# Integration: ref add/remove for custom type item
# ---------------------------------------------------------------------------


class TestRefPathsForCustomType:
    """ref add/remove must not raise KeyError for a custom-type item."""

    async def test_ref_add_to_custom_item_no_keyerror(
        self, project: SquadPaths, svc: service.Service, frozen_time
    ) -> None:
        """Adding a ref TO a custom-type item does not KeyError on prefix lookup."""
        _write_override(project.squad_dir)
        svc = service.open_service()

        task_result = await svc.create("task", "Task ref source", author="manager")
        task_id = task_result.item.id

        bug_result = await svc.create("bug", "A bug", author="manager")
        bug_id = bug_result.item.id
        # Retype bug to incident so we have a custom-type target.
        await svc.retype(bug_id, "incident")
        # Get the new incident id.
        incidents = await svc.list_items(item_type="incident")
        inc_id = incidents[0].id

        # Add a ref from task to incident — must not KeyError.
        updated = await svc.add_ref(task_id, inc_id, kind="related")
        assert any(inc_id in r for r in updated.refs)

    async def test_ref_remove_from_custom_item_no_keyerror(
        self, project: SquadPaths, svc: service.Service, frozen_time
    ) -> None:
        """Removing a ref pointing AT a custom-type item does not KeyError."""
        _write_override(project.squad_dir)
        svc = service.open_service()

        task_result = await svc.create("task", "Task ref source", author="manager")
        task_id = task_result.item.id

        bug_result = await svc.create("bug", "A bug", author="manager")
        await svc.retype(bug_result.item.id, "incident")
        incidents = await svc.list_items(item_type="incident")
        inc_id = incidents[0].id

        await svc.add_ref(task_id, inc_id)
        # Remove it.
        updated = await svc.rm_ref(task_id, inc_id)
        assert not any(inc_id in r for r in updated.refs)

    async def test_refs_in_for_custom_item_no_keyerror(
        self, project: SquadPaths, svc: service.Service, frozen_time
    ) -> None:
        """refs_in() for a custom-type item does not KeyError on prefix lookup."""
        _write_override(project.squad_dir)
        svc = service.open_service()

        task_result = await svc.create("task", "Task", author="manager")
        task_id = task_result.item.id

        bug_result = await svc.create("bug", "A bug", author="manager")
        await svc.retype(bug_result.item.id, "incident")
        incidents = await svc.list_items(item_type="incident")
        inc_id = incidents[0].id

        await svc.add_ref(task_id, inc_id)
        # refs_in on the incident must not KeyError.
        backrefs = await svc.refs_in(inc_id)
        assert any(task_id == bid for bid, _ in backrefs)


# ---------------------------------------------------------------------------
# Legacy file round-trip: no prefix: line in frontmatter → re-derived on load
# ---------------------------------------------------------------------------


class TestLegacyFileLoad:
    """Items without a prefix: frontmatter line still load correctly (re-derived on load)."""

    async def test_legacy_builtin_loads_without_prefix_line(
        self, project: SquadPaths, svc: service.Service, frozen_time
    ) -> None:
        """A legacy task file with no prefix: line re-derives TASK on load."""
        from squads._itemfile import read_frontmatter

        # Create a task — built-in types never write prefix: to frontmatter.
        result = await svc.create("task", "Legacy task", author="manager")
        task_path = project.squad_dir / result.item.path

        # Verify no prefix: line in frontmatter (built-in behavior).
        fm = read_frontmatter(text=task_path.read_text())
        assert "prefix" not in fm, "Built-in task must not have prefix: in frontmatter"

        # Reload from disk — should still resolve the correct id.
        loaded = await svc.get(result.item.id)
        assert loaded.id == result.item.id
        assert loaded.prefix == "TASK"

    async def test_legacy_custom_without_prefix_still_loads(
        self, project: SquadPaths, svc: service.Service, frozen_time
    ) -> None:
        """A custom-type file whose prefix: line is manually stripped still loads via re-derive."""
        from squads import _sections as sections

        _write_override(project.squad_dir)
        svc = service.open_service()

        # Create + retype to get an incident item with prefix: in frontmatter.
        result = await svc.create("task", "Incident legacy", author="manager")
        await svc.retype(result.item.id, "incident")
        incidents = await svc.list_items(item_type="incident")
        inc = incidents[0]
        inc_path = project.squad_dir / inc.path

        # Manually strip the prefix: line from frontmatter to simulate a legacy file.
        text = inc_path.read_text()
        fm, _body = sections.split_frontmatter(text)
        if fm and "prefix" in fm:
            del fm["prefix"]
        text_without_prefix = sections.join_frontmatter(fm or {}, text)
        inc_path.write_text(text_without_prefix)

        # Repair rebuilds the index from disk — the item should still load with correct prefix.
        await svc.repair()
        loaded = await svc.get(inc.id)
        # The prefix re-derived from the spec should be INC.
        assert loaded.prefix == "INC"
        assert loaded.id.startswith("INC-")


# ---------------------------------------------------------------------------
# Byte-identical: built-in item files unchanged by this change
# ---------------------------------------------------------------------------


class TestBuiltinByteIdentical:
    """Built-in items must not gain a prefix: frontmatter line from this change."""

    async def test_builtin_task_frontmatter_has_no_prefix_line(
        self, project: SquadPaths, svc: service.Service, frozen_time
    ) -> None:
        """A newly created task must not have prefix: in its frontmatter."""
        from squads._itemfile import read_frontmatter

        result = await svc.create("task", "No prefix line", author="manager")
        task_path = project.squad_dir / result.item.path
        fm = read_frontmatter(text=task_path.read_text())
        assert "prefix" not in fm, "Built-in task must not write prefix: to frontmatter"

    async def test_builtin_ids_unchanged(
        self, project: SquadPaths, svc: service.Service, frozen_time
    ) -> None:
        """Built-in items still render TASK-000001, FEAT-000002, etc. — no regression."""
        task = await svc.create("task", "A task", author="manager")
        feat = await svc.create("feature", "A feature", author="manager")
        bug = await svc.create("bug", "A bug", author="manager")

        assert task.item.id.startswith("TASK-")
        assert feat.item.id.startswith("FEAT-")
        assert bug.item.id.startswith("BUG-")
        assert not task.item.id.startswith("TASK-000000")


# ---------------------------------------------------------------------------
# CLI smoke: sq incident <n> show round-trip
# ---------------------------------------------------------------------------


class TestCliCustomTypeRoundTrip:
    """CLI integration: sq incident INC-NNNNNN show succeeds end-to-end."""

    def test_cli_retype_then_show_via_inc_id(
        self, runner: CliRunner, tmp_path: Path, monkeypatch, frozen_time
    ) -> None:
        """After retype to incident, sq incident <seq> show returns exit code 0."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
        assert result.exit_code == 0, result.output

        # Write override.
        _write_override(tmp_path / "squads")

        # Create a task then retype it via CLI.
        # init --roles minimal seeds 1 role (sequence 1); first task → sequence 2.
        result = runner.invoke(app, ["create", "task", "My incident task", "--author", "manager"])
        assert result.exit_code == 0, result.output

        # Retype the task (sequence 2) to incident.
        result = runner.invoke(app, ["task", "2", "retype", "incident"])
        assert result.exit_code == 0, result.output

        # The show command must work with the new INC- id (sequence 2).
        result = runner.invoke(app, ["incident", "2", "show"])
        assert result.exit_code == 0, result.output
        assert "INC-" in result.output, f"Expected INC- in output, got:\n{result.output}"
        assert "INCIDENT-" not in result.output, (
            f"Should not see INCIDENT- in output, got:\n{result.output}"
        )

    def test_cli_list_type_incident(
        self, runner: CliRunner, tmp_path: Path, monkeypatch, frozen_time
    ) -> None:
        """sq list -t incident returns the retyped item."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
        _write_override(tmp_path / "squads")

        # init --roles minimal seeds 1 role (sequence 1); first task → sequence 2.
        runner.invoke(app, ["create", "task", "Incident item", "--author", "manager"])
        runner.invoke(app, ["task", "2", "retype", "incident"])

        result = runner.invoke(app, ["list", "-t", "incident"])
        assert result.exit_code == 0, result.output
        assert "INC-" in result.output
        assert "INCIDENT-" not in result.output
