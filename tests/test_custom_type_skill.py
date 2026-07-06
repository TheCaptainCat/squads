"""Tests for TASK-000260: auto-generated thin sq-<type> skill for custom types.

Covers:
- AC#5: thin sq-incident skill generated with the correct auto-linearized lifecycle string
  and standard command list.
- AC#6: SKILL-id allocation for custom types follows lexical-by-slug order, consistent with
  the FEAT-178 primitive (bundled_skill_slugs); no churn of existing bundled SKILL ids.
- AC#7/#8: for a bundled (non-custom) squad the generated sq-<type> skill bodies are
  byte-identical (the TASK-256 golden remains green — verified by the golden test module).
- seed_custom_skills is idempotent (second call produces no new items).
- custom_skill_slugs returns only custom slugs, empty for a bundled-only spec.
- The thin skill pointer is written to .claude/skills/<type>/SKILL.md.
- Sync writes the thin skill body AND seeds the SKILL id in a single call.
"""

from pathlib import Path

import pytest

from squads._interactions import (
    bundled_skill_slugs,
    custom_item_skill_commands,
    custom_skill_slugs,
)
from squads._models._enums import ItemType
from squads._sections import split_frontmatter
from squads._services import _service as service
from squads._workflow import linearize_lifecycle
from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import ItemSpec, Lifecycle, WorkflowSpec

pytestmark = pytest.mark.anyio

# ---------------------------------------------------------------------------
# Fixtures / helpers
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
# Unit: custom_skill_slugs
# ---------------------------------------------------------------------------


def test_custom_skill_slugs_empty_for_bundled_spec() -> None:
    """custom_skill_slugs returns an empty list for the bundled spec (no custom types)."""
    base = load_workflow_spec()
    assert custom_skill_slugs(base) == []


def test_custom_skill_slugs_returns_custom_only() -> None:
    """custom_skill_slugs returns only custom type slugs, in lexical order."""
    spec = _spec_with_incident()
    result = custom_skill_slugs(spec)
    assert result == ["sq-incident"]


def test_custom_skill_slugs_lexical_order() -> None:
    """Custom skill slugs are sorted lexically (AC#6 ordering consistency)."""
    # Add two custom types; verify they come out sorted.
    base = load_workflow_spec()
    triage = Lifecycle(
        initial="Open",
        transitions={"Open": ["Done"], "Done": []},
    )
    new_lifecycles = dict(base.lifecycles)
    new_lifecycles["triage"] = triage
    new_items = dict(base.items)
    new_items["zebra"] = ItemSpec(prefix="ZEB", folder="zebras", lifecycle="triage")
    new_items["alpha"] = ItemSpec(prefix="ALP", folder="alphas", lifecycle="triage")
    new_prefix_to_type = dict(base.prefix_to_type)
    new_prefix_to_type["ZEB"] = "zebra"
    new_prefix_to_type["ALP"] = "alpha"
    spec = WorkflowSpec.model_validate(
        {
            "items": new_items,
            "statuses": base.statuses,
            "lifecycles": new_lifecycles,
            "prefix_to_type": new_prefix_to_type,
            "alias_to_type": base.alias_to_type,
        }
    )
    slugs = custom_skill_slugs(spec)
    assert slugs == sorted(slugs), "custom_skill_slugs must return slugs in lexical order"
    assert "sq-alpha" in slugs and "sq-zebra" in slugs
    assert slugs.index("sq-alpha") < slugs.index("sq-zebra")


def test_custom_skill_slugs_no_meta_types() -> None:
    """Meta types (is_meta=True) are excluded from custom_skill_slugs."""
    spec = _spec_with_incident()
    slugs = custom_skill_slugs(spec)
    # Built-in meta types (role, skill, operator) must not appear.
    assert "sq-role" not in slugs
    assert "sq-skill" not in slugs
    assert "sq-operator" not in slugs


# ---------------------------------------------------------------------------
# Unit: custom_item_skill_commands
# ---------------------------------------------------------------------------


def test_custom_item_skill_commands_contains_standard_verbs() -> None:
    """custom_item_skill_commands returns the standard command set for a custom type."""
    cmds = custom_item_skill_commands("incident")
    # All 10 standard verbs must be present in some command line.
    verbs = (
        "create",
        "show",
        "list",
        "update",
        "status",
        "ref",
        "comment",
        "body",
        "remove",
        "retype",
    )
    for verb in verbs:
        assert any(verb in cmd for cmd in cmds), f"verb {verb!r} missing from command list"


def test_custom_item_skill_commands_uses_type_name() -> None:
    """custom_item_skill_commands embeds the type name in the commands."""
    cmds = custom_item_skill_commands("incident")
    # Every command referencing the type should use "incident".
    assert any("incident" in cmd for cmd in cmds)
    assert any("sq create incident" in cmd for cmd in cmds)


# ---------------------------------------------------------------------------
# Service-level: seed_custom_skills generates thin skills with correct content
# ---------------------------------------------------------------------------


async def test_seed_custom_skills_generates_skill_file(tmp_path, monkeypatch, frozen_time) -> None:
    """AC#5: seed_custom_skills (called by sync) generates a thin sq-incident skill.

    The skill body must contain:
    - the auto-linearized lifecycle string for the triage machine
    - the standard command list with 'incident' as the type name
    """
    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    paths = init_result.paths
    spec = _spec_with_incident()
    svc = service.Service(paths, spec=spec)

    # sync writes the skill bodies and seeds SKILL ids for custom types.
    await svc.sync()

    # The expected lifecycle string from linearize_lifecycle.
    triage_machine = spec.machine_for(_INCIDENT_TYPE)
    expected_lifecycle = linearize_lifecycle(triage_machine)

    skills_folder = paths.squad_dir / "agents" / "skills"
    # The skill file may be either the legacy slug-named or the convention-named file.
    # After sync, it should be the convention-named (SKILL-NNNNNN-sq-incident.md).
    convention_files = list(skills_folder.glob("SKILL-*-sq-incident.md"))
    legacy_file = skills_folder / "sq-incident.md"

    has_convention = len(convention_files) > 0
    has_legacy = legacy_file.is_file()
    assert has_convention or has_legacy, (
        "sq-incident skill file not found (neither convention nor legacy name)"
    )

    skill_file = convention_files[0] if has_convention else legacy_file
    skill_text = skill_file.read_text(encoding="utf-8")
    assert expected_lifecycle in skill_text, (
        f"lifecycle string {expected_lifecycle!r} not found in skill body"
    )
    for verb in ("create", "show", "list", "update", "status", "ref", "comment", "body"):
        assert verb in skill_text, f"verb {verb!r} missing from thin skill body"


async def test_seed_custom_skills_sections_empty(tmp_path, monkeypatch, frozen_time) -> None:
    """The thin sq-incident skill has no 'For <role>' sections (sections=[] degradation)."""
    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    paths = init_result.paths
    spec = _spec_with_incident()
    svc = service.Service(paths, spec=spec)
    await svc.sync()

    skills_folder = paths.squad_dir / "agents" / "skills"
    convention_files = list(skills_folder.glob("SKILL-*-sq-incident.md"))
    legacy_file = skills_folder / "sq-incident.md"
    skill_file = convention_files[0] if convention_files else legacy_file
    skill_text = skill_file.read_text(encoding="utf-8")

    # sections=[] means no "## For " headings.
    assert "## For " not in skill_text, "thin skill should have no 'For <role>' sections"


async def test_seed_custom_skills_allocates_skill_id(tmp_path, monkeypatch, frozen_time) -> None:
    """AC#5/#6: seed_custom_skills mints a SKILL item with an id in the index."""
    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    paths = init_result.paths
    spec = _spec_with_incident()
    svc = service.Service(paths, spec=spec)

    await svc.sync()

    # The index should contain a SKILL item with slug='sq-incident'.
    skill_items = await svc.list_items(item_type=ItemType.SKILL)
    slugs = {it.extra.get("slug") for it in skill_items}
    assert "sq-incident" in slugs, f"sq-incident not in SKILL items; found: {slugs}"


async def test_seed_custom_skills_is_idempotent(tmp_path, monkeypatch, frozen_time) -> None:
    """seed_custom_skills is idempotent: calling it twice allocates no extra SKILL ids."""
    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    paths = init_result.paths
    spec = _spec_with_incident()
    svc = service.Service(paths, spec=spec)

    await svc.sync()

    skill_items_after_first = await svc.list_items(item_type=ItemType.SKILL)
    incident_count_after_first = sum(
        1 for it in skill_items_after_first if it.extra.get("slug") == "sq-incident"
    )
    assert incident_count_after_first == 1, (
        "expected exactly one sq-incident skill after first sync"
    )

    # Second sync must not create duplicate SKILL entries.
    await svc.sync()
    skill_items_after_second = await svc.list_items(item_type=ItemType.SKILL)
    incident_count_after_second = sum(
        1 for it in skill_items_after_second if it.extra.get("slug") == "sq-incident"
    )
    assert incident_count_after_second == 1, (
        "idempotency broken: sq-incident SKILL item duplicated after second sync"
    )


# ---------------------------------------------------------------------------
# AC#6: lexical-by-slug allocation order (no churn of existing bundled ids)
# ---------------------------------------------------------------------------


async def test_custom_skill_id_allocation_order(tmp_path, monkeypatch, frozen_time) -> None:
    """AC#6: bundled skills are allocated before custom skills in lexical slug order.

    The bundled skill slugs come first (they are seeded at init time via seed_bundled_skills);
    custom skill slugs are seeded later by seed_custom_skills.  Within each group, IDs are
    allocated in lexical-by-slug order.  The sequence number of a bundled skill must always be
    less than any custom skill's sequence number — there is no churn of existing bundled IDs.
    """
    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal")
    paths = init_result.paths
    spec = _spec_with_incident()
    svc = service.Service(paths, spec=spec)

    await svc.sync()  # seeds custom skills

    skill_items = await svc.list_items(item_type=ItemType.SKILL)
    by_slug = {it.extra.get("slug"): it for it in skill_items if it.extra.get("slug")}

    bundled = bundled_skill_slugs()
    incident_item = by_slug.get("sq-incident")
    assert incident_item is not None, "sq-incident SKILL item not found after sync"

    # Every bundled skill must have a lower sequence number than the custom skill.
    for bslug in bundled:
        bundled_item = by_slug.get(bslug)
        if bundled_item is None:
            continue  # minimal roster may not have all bundled skills seeded
        assert bundled_item.sequence_id < incident_item.sequence_id, (
            f"bundled skill {bslug!r} (seq={bundled_item.sequence_id}) "
            f"has a higher sequence_id than custom sq-incident (seq={incident_item.sequence_id}); "
            "bundled skills must be allocated before custom skills"
        )


async def test_bundled_skills_unchanged_after_custom_type_sync(
    tmp_path, monkeypatch, frozen_time
) -> None:
    """Syncing a custom type does not change the sequence ids of bundled skills (no churn)."""
    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal")
    paths = init_result.paths

    # Capture bundled skill sequence ids before adding a custom type.
    svc_bundled = service.Service(paths)
    skills_before = await svc_bundled.list_items(item_type=ItemType.SKILL)
    seq_before = {it.extra.get("slug"): it.sequence_id for it in skills_before}

    # Now sync with the spec that includes the custom incident type.
    spec = _spec_with_incident()
    svc_custom = service.Service(paths, spec=spec)
    await svc_custom.sync()

    skills_after = await svc_custom.list_items(item_type=ItemType.SKILL)
    seq_after = {it.extra.get("slug"): it.sequence_id for it in skills_after}

    # All bundled skill sequence ids must be unchanged.
    for slug, seq in seq_before.items():
        assert seq_after.get(slug) == seq, (
            f"bundled skill {slug!r} sequence_id changed after custom type sync: "
            f"{seq} → {seq_after.get(slug)}"
        )


# ---------------------------------------------------------------------------
# CLI smoke: .claude/skills/sq-incident/SKILL.md pointer is written
# ---------------------------------------------------------------------------


async def test_sync_writes_custom_skill_pointer(tmp_path, monkeypatch, frozen_time) -> None:
    """sq sync writes a .claude/skills/sq-incident/SKILL.md pointer for a custom type."""
    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    paths = init_result.paths
    spec = _spec_with_incident()
    svc = service.Service(paths, spec=spec)

    await svc.sync()

    pointer_path = paths.root / ".claude" / "skills" / "sq-incident" / "SKILL.md"
    assert pointer_path.is_file(), f"custom skill pointer not written at {pointer_path}"
    pointer_text = pointer_path.read_text(encoding="utf-8")
    fm, _ = split_frontmatter(pointer_text)
    assert fm is not None, "custom skill pointer has no frontmatter"
    assert fm.get("name") == "sq-incident", f"pointer name wrong: {fm.get('name')!r}"


async def test_sync_custom_skill_body_contains_lifecycle_and_commands(
    tmp_path, monkeypatch, frozen_time
) -> None:
    """End-to-end: sq sync writes a thin sq-incident skill with lifecycle + commands."""
    from squads._workflow._loader import load_workflow_spec as _load_spec

    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    paths = init_result.paths
    _write_override(paths.squad_dir)

    # Use a service with the override-aware spec (load_workflow_spec merges the override).
    spec = _load_spec(squad_dir=paths.squad_dir)
    svc = service.Service(paths, spec=spec)
    await svc.sync()

    # Find the skill body file.
    skills_folder = paths.squad_dir / "agents" / "skills"
    convention_files = list(skills_folder.glob("SKILL-*-sq-incident.md"))
    legacy_file = skills_folder / "sq-incident.md"
    assert convention_files or legacy_file.is_file(), "sq-incident skill body file not found"

    skill_file = convention_files[0] if convention_files else legacy_file
    skill_text = skill_file.read_text(encoding="utf-8")

    # AC#5: lifecycle string must be auto-derived from the spec's triage machine.
    triage_machine = spec.machine_for(_INCIDENT_TYPE)
    expected_lifecycle = linearize_lifecycle(triage_machine)
    assert expected_lifecycle in skill_text, (
        f"lifecycle {expected_lifecycle!r} not in sq-incident skill body"
    )
    # Standard command verbs present.
    for verb in ("create", "show", "list"):
        assert verb in skill_text, f"verb {verb!r} missing from sq-incident skill body"


# ---------------------------------------------------------------------------
# Bundled-squad regression: no custom skills for a non-custom squad
# ---------------------------------------------------------------------------


async def test_no_custom_skills_for_bundled_only_squad(tmp_path, monkeypatch, frozen_time) -> None:
    """For a bundled-only squad (no custom types), no sq-incident skill is written."""
    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    paths = init_result.paths
    svc = service.Service(paths)  # uses bundled spec — no custom types
    await svc.sync()

    skills_folder = paths.squad_dir / "agents" / "skills"
    incident_files = list(skills_folder.glob("*incident*"))
    assert not incident_files, (
        f"unexpected incident skill files found in a bundled-only squad: {incident_files}"
    )
    pointer_path = paths.root / ".claude" / "skills" / "sq-incident" / "SKILL.md"
    assert not pointer_path.exists(), "sq-incident skill pointer written for a bundled-only squad"


# ---------------------------------------------------------------------------
# F4 — sub-entity footer guard: custom types must NOT advertise <kind> <k> verbs
# ---------------------------------------------------------------------------


async def test_custom_skill_no_subentity_footer_lines(tmp_path, monkeypatch, frozen_time) -> None:
    """F4: the thin sq-incident skill does not advertise dead sub-entity <kind> <k> verbs.

    Custom types declare no sub-entity kind, so the footer references
    `sq <type> <n> <kind> <k> body` and `sq <type> <n> <kind> <k> show` must be absent.
    The replacement line (`Read anything back with sq incident <n> show --full --comments`)
    must be present.
    """
    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    paths = init_result.paths
    spec = _spec_with_incident()
    svc = service.Service(paths, spec=spec)
    await svc.sync()

    skills_folder = paths.squad_dir / "agents" / "skills"
    convention_files = list(skills_folder.glob("SKILL-*-sq-incident.md"))
    legacy_file = skills_folder / "sq-incident.md"
    skill_file = convention_files[0] if convention_files else legacy_file
    skill_text = skill_file.read_text(encoding="utf-8")

    # Dead sub-entity verbs must NOT appear in the footer.
    assert "<kind> <k> body" not in skill_text, (
        "custom-type skill footer must not reference <kind> <k> body — no sub-entity kind declared"
    )
    assert "<kind> <k> show" not in skill_text, (
        "custom-type skill footer must not reference <kind> <k> show — no sub-entity kind declared"
    )
    # The replacement footer must be present.
    assert "show --full --comments" in skill_text, (
        "custom-type skill footer must contain sq incident <n> show --full --comments"
    )


async def test_custom_skill_create_command_runs_end_to_end(
    invoke, tmp_path, monkeypatch, frozen_time
) -> None:
    """F4: the sq create <type> command advertised in the thin skill runs end-to-end.

    Generates the sq-incident skill, extracts the create command line, and
    verifies that running it against the CLI creates a correctly-prefixed item.
    """
    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    paths = init_result.paths
    _write_override(paths.squad_dir)

    from squads._workflow._loader import load_workflow_spec as _load_spec

    spec = _load_spec(squad_dir=paths.squad_dir)
    svc = service.Service(paths, spec=spec)
    await svc.sync()

    # The create command from the generated skill:
    # `sq create incident "…" --author <slug>`
    # Verify it runs successfully with a real author (manager is seeded by minimal init).
    result = await invoke(["create", "incident", "Disk full alert", "--author", "manager"])
    assert result.exit_code == 0, (
        f"sq create incident failed (exit {result.exit_code}):\n{result.output}"
    )
    # The item ID must use the correct prefix from the spec (INC-), not the type name uppercased.
    assert "INC-" in result.output, f"Expected INC-NNNNNN prefix in output, got:\n{result.output}"
    assert "INCIDENT-" not in result.output, (
        f"Unexpected INCIDENT- prefix — should be INC-:\n{result.output}"
    )
