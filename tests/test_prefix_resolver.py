"""Tests for TASK-000267 / ADR-322 (TASK-000328, revised by TASK-000338): Item.prefix +
prefix_for resolver + retype prefix stamping.

Covers:
- prefix_for() resolves solely from the spec, for every type (built-in or custom); an
  unknown type or a missing spec raises SquadsError (no reserved-map / type.upper() guess).
  Used at create/retype time, when a spec is in hand.
- No item, built-in or custom, writes a prefix: frontmatter line — Item.prefix is instead
  re-derived from the durable id string on every read path (rsplit on the last "-"), so
  there is nothing redundant left to persist or backfill.
- Retype stamps the target type's prefix: INC-000019, not INCIDENT-000019.
- File is named INC-000019-*.md after retype.
- sq incident INC-000019 show round-trips (CLI + service).
- sq list -t incident returns the custom item.
- ref add / remove work for a custom type item without KeyError.
- A stray prefix: key left over in frontmatter (from an earlier build) is tolerated on read
  and never trusted — the derived-from-id value always wins.
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from squads._cli import app
from squads._models._item import UNRESOLVED_PREFIX, Item
from squads._models._vocab import prefix_for
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
            "collections": base.collections,
            "subentity_kinds": base.subentity_kinds,
        }
    )


# ---------------------------------------------------------------------------
# Unit: prefix_for resolver
# ---------------------------------------------------------------------------


class TestPrefixFor:
    """Unit tests for the _models._vocab.prefix_for() resolver (ADR-322: spec-only, no
    reserved-map fast path — every type, built-in or custom, resolves the same way)."""

    def test_builtin_types_resolve_via_spec(self) -> None:
        """prefix_for returns the spec-declared prefix for every built-in type."""
        spec = _spec_with_incident()
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
            assert prefix_for(type_str, spec) == expected_prefix, f"wrong prefix for {type_str!r}"

    def test_builtin_type_no_spec_raises(self) -> None:
        """A built-in type with no spec supplied raises — there is no reserved-map fallback."""
        from squads._errors import SquadsError

        with pytest.raises(SquadsError, match="unknown item type"):
            prefix_for("task")

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


# ---------------------------------------------------------------------------
# Unit: effective_prefix() — the shared acyclic-formatter fallback helper
# ---------------------------------------------------------------------------


class TestEffectivePrefix:
    """effective_prefix() is the ONE shared stand-in used by every acyclic formatter/matcher
    that cannot call prefix_for (no spec in hand) and cannot raise (Item.id, format_id, the
    ref-matching helpers). It never guesses type.upper() — architect ruling on the residual
    type.upper() idiom, folded into TASK-000328."""

    def test_returns_prefix_when_set(self) -> None:
        from squads._models._item import effective_prefix

        assert effective_prefix("INC", "incident") == "INC"
        assert effective_prefix("TASK", "task") == "TASK"

    def test_degrades_to_sentinel_when_unset_regardless_of_type(self) -> None:
        """Never a type.upper() guess — not even for a type where that would coincide."""
        from squads._models._item import UNRESOLVED_PREFIX, effective_prefix

        assert effective_prefix("", "task") == UNRESOLVED_PREFIX
        assert effective_prefix("", "decision") == UNRESOLVED_PREFIX
        assert effective_prefix("", "review") == UNRESOLVED_PREFIX


# ---------------------------------------------------------------------------
# Unit: Item.prefix field + Item.id computed field
# ---------------------------------------------------------------------------


class TestItemPrefixField:
    """Item.prefix drives Item.id; the model formats purely from the stored string
    (ADR-322 §3 — no reserved-map fallback lives in the model any more)."""

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
        assert item.id == "INC-19"
        assert item.prefix == "INC"

    def test_item_id_fallback_for_missing_prefix_is_unresolved_sentinel(self) -> None:
        """With no prefix set at all, Item.id degrades to the UNRESOLVED_PREFIX sentinel —
        never a type.upper() guess (which used to coincidentally look right for 'task' but
        silently mis-renders e.g. 'decision' as DECISION-N instead of ADR-N). A leaked
        pre-resolution id reads loud and test-visible: UNRESOLVED-N, never a
        plausible-but-wrong id — _models must stay spec-decoupled and never import
        _workflow, so this can never be a real vocabulary lookup."""
        from datetime import UTC, datetime

        item = Item(
            sequence_id=7,
            type="task",
            # prefix left as default "" — degrades to the UNRESOLVED_PREFIX sentinel,
            # regardless of type (never a type.upper() guess, even one that would coincide).
            title="A task",
            slug="a-task",
            status="Draft",
            path="tasks/TASK-000007-a-task.md",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert item.prefix == ""
        assert item.id == f"{UNRESOLVED_PREFIX}-7"

    def test_to_frontmatter_dict_never_writes_prefix(self) -> None:
        """No prefix: line is written for ANY type — built-in or custom (TASK-338: the
        prefix is recoverable from the written id: line alone, so there is nothing left to
        persist redundantly)."""
        from datetime import UTC, datetime

        now = datetime.now(UTC)
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
        assert "prefix" not in fm_custom
        assert fm_custom["id"] == "INC-1"

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
        assert "prefix" not in fm_builtin
        assert fm_builtin["id"] == "TASK-1"

    def test_to_frontmatter_dict_omits_prefix_when_unset(self) -> None:
        """An Item constructed with no prefix at all (e.g. a bare test fixture) writes no
        prefix: line — there's nothing to persist."""
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        item = Item(
            sequence_id=1,
            type="task",
            title="A task",
            slug="a-task",
            status="Draft",
            path="tasks/TASK-000001-a-task.md",
            created_at=now,
            updated_at=now,
        )
        fm = item.to_frontmatter_dict()
        assert "prefix" not in fm

    def test_from_frontmatter_derives_prefix_for_custom_type(self) -> None:
        """from_frontmatter derives the prefix from the id: line for custom types — no
        stored prefix: key involved at all."""
        from datetime import UTC, datetime

        now = datetime.now(UTC).isoformat()
        data = {
            "id": "INC-000019",
            "sequence_id": 19,
            "type": "incident",
            "title": "An incident",
            "slug": "an-incident",
            "status": "Open",
            "created_at": now,
            "updated_at": now,
        }
        item = Item.from_frontmatter(data, path="incidents/INC-000019-an-incident.md")
        assert item.prefix == "INC"
        assert item.id == "INC-19"

    def test_from_frontmatter_derives_prefix_for_builtins_too(self) -> None:
        """from_frontmatter derives the prefix from id: for built-in types the same way as
        custom types — there is no separate built-in code path."""
        from datetime import UTC, datetime

        now = datetime.now(UTC).isoformat()
        data = {
            "id": "TASK-000007",
            "sequence_id": 7,
            "type": "task",
            "title": "A task",
            "slug": "a-task",
            "status": "Draft",
            "created_at": now,
            "updated_at": now,
        }
        item = Item.from_frontmatter(data, path="tasks/TASK-000007-a-task.md")
        assert item.prefix == "TASK"
        assert item.id == "TASK-7"

    def test_from_frontmatter_degrades_to_unresolved_when_id_absent(self) -> None:
        """With no id: line at all (a bare/malformed record), Item.prefix stays empty and
        the id degrades to the loud UNRESOLVED_PREFIX sentinel — never a silent guess. In
        practice every item's frontmatter has always carried id:, so this is a
        never-should-happen guard, not a real legacy-file scenario."""
        from datetime import UTC, datetime

        now = datetime.now(UTC).isoformat()
        data = {
            "sequence_id": 7,
            "type": "task",
            "title": "A task",
            "slug": "a-task",
            "status": "Draft",
            "created_at": now,
            "updated_at": now,
        }
        item = Item.from_frontmatter(data, path="tasks/TASK-000007-a-task.md")
        assert item.prefix == ""
        assert item.id == f"{UNRESOLVED_PREFIX}-7"

    def test_from_frontmatter_ignores_stray_prefix_key(self) -> None:
        """A stray prefix: key left in frontmatter by an earlier build (TASK-328's now-
        reverted mechanism) is tolerated — it never errors, and it is never trusted: the
        prefix re-derived from id: always wins, even when the stray value disagrees."""
        from datetime import UTC, datetime

        now = datetime.now(UTC).isoformat()
        data = {
            "id": "TASK-000007",
            "sequence_id": 7,
            "type": "task",
            "prefix": "WRONGPREFIX",  # stray legacy key — must be ignored, not trusted
            "title": "A task",
            "slug": "a-task",
            "status": "Draft",
            "created_at": now,
            "updated_at": now,
        }
        item = Item.from_frontmatter(data, path="tasks/TASK-000007-a-task.md")
        assert item.prefix == "TASK"
        assert item.id == "TASK-7"

    def test_full_round_trip_with_no_spec_loaded(self) -> None:
        """Explicit spec-free round-trip (FEAT-326 AC#3 / done-criteria, revised by
        TASK-338): to_frontmatter_dict() -> from_frontmatter() reproduces the same id for
        BOTH a built-in and a custom type, with no WorkflowSpec constructed or imported
        anywhere in this test and no prefix: key ever written — proving _models never needs
        a spec to round-trip an item's own id."""
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        for item_type, prefix, path in (
            ("task", "TASK", "tasks/TASK-000007-a-task.md"),
            ("incident", "INC", "incidents/INC-000019-an-incident.md"),
        ):
            original = Item(
                sequence_id=7,
                type=item_type,
                prefix=prefix,
                title="Round trip",
                slug="round-trip",
                status="Draft",
                path=path,
                created_at=now,
                updated_at=now,
            )
            fm = original.to_frontmatter_dict()
            assert "prefix" not in fm, f"{item_type}: prefix: must not be written"

            reloaded = Item.from_frontmatter(fm, path=path)
            assert reloaded.prefix == prefix, f"{item_type}: prefix did not re-derive from id"
            assert reloaded.id == original.id, f"{item_type}: id did not round-trip"


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

        # Prefix must be "INC", id must be "INC-1".
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
# A stray prefix: key surviving on disk (from an earlier, reverted build) still loads
# ---------------------------------------------------------------------------


class TestLegacyFileLoad:
    """A file that happens to carry a stray prefix: frontmatter key (written by an
    earlier, since-reverted build) still loads correctly — the key is tolerated, and the
    prefix re-derived from id: is used regardless of what it says.
    """

    async def test_stray_prefix_key_ignored_on_reload(
        self, project: SquadPaths, svc: service.Service, frozen_time
    ) -> None:
        """A hand-inserted stray prefix: line (disagreeing with the real prefix) does not
        change what gets loaded — the id: line is always the source of truth."""
        from squads import _sections as sections

        result = await svc.create("task", "Legacy task", author="manager")
        task_path = project.squad_dir / result.item.path

        # create() never writes a prefix: line; hand-insert a disagreeing stray one to
        # simulate a file left over from an earlier, since-reverted build.
        text = task_path.read_text()
        fm, _body = sections.split_frontmatter(text)
        assert "prefix" not in fm, "sanity: create() must not stamp a prefix: line"
        fm["prefix"] = "WRONGPREFIX"
        task_path.write_text(sections.join_frontmatter(fm, text))

        # Reload from disk — the stray key must not surface as an error or as the id.
        loaded = await svc.get(result.item.id)
        assert loaded.id == result.item.id
        assert loaded.prefix == "TASK"

    async def test_stray_prefix_key_ignored_for_custom_type(
        self, project: SquadPaths, svc: service.Service, frozen_time
    ) -> None:
        """Same tolerance for a custom type: a stray prefix: key is ignored on repair."""
        from squads import _sections as sections

        _write_override(project.squad_dir)
        svc = service.open_service()

        result = await svc.create("task", "Incident legacy", author="manager")
        await svc.retype(result.item.id, "incident")
        incidents = await svc.list_items(item_type="incident")
        inc = incidents[0]
        inc_path = project.squad_dir / inc.path

        text = inc_path.read_text()
        fm, _body = sections.split_frontmatter(text)
        fm["prefix"] = "WRONGPREFIX"
        inc_path.write_text(sections.join_frontmatter(fm, text))

        # Repair rebuilds the index from disk — the stray key must not survive the reload.
        await svc.repair()
        loaded = await svc.get(inc.id)
        assert loaded.prefix == "INC"
        assert loaded.id.startswith("INC-")


# ---------------------------------------------------------------------------
# Built-in item IDs: no prefix: frontmatter line, id: alone carries the identity
# ---------------------------------------------------------------------------


class TestBuiltinByteIdentical:
    """Built-in item IDs/folders round-trip correctly with no prefix: line at all."""

    async def test_builtin_task_frontmatter_carries_no_prefix_line(
        self, project: SquadPaths, svc: service.Service, frozen_time
    ) -> None:
        """A newly created task's frontmatter has no prefix: key — TASK-338 dropped it."""
        from squads._itemfile import read_frontmatter

        result = await svc.create("task", "No prefix line", author="manager")
        task_path = project.squad_dir / result.item.path
        fm = read_frontmatter(text=task_path.read_text())
        assert "prefix" not in fm
        assert fm.get("id") == result.item.id

    async def test_builtin_ids_unchanged(
        self, project: SquadPaths, svc: service.Service, frozen_time
    ) -> None:
        """Built-in items still render TASK-1, FEAT-2, etc. — no regression."""
        task = await svc.create("task", "A task", author="manager")
        feat = await svc.create("feature", "A feature", author="manager")
        bug = await svc.create("bug", "A bug", author="manager")

        assert task.item.id.startswith("TASK-")
        assert feat.item.id.startswith("FEAT-")
        assert bug.item.id.startswith("BUG-")
        assert not task.item.id.startswith("TASK-0")  # unpadded — never a leading zero


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
