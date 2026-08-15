"""``sq init``/``sq adopt`` must scaffold against the MERGED spec, not the bundled default,
when a project override is already sitting at ``<squad_dir>/.overrides/workflow.toml`` before
either call runs (e.g. hand-placed, or carried over into a folder being adopted).

Two failure modes are covered, both driven end to end rather than asserted from reading the
loader: a dropped type still gets its folder scaffolded and an orphan skill seeded, and a
roster item gets activated at the BUNDLED lifecycle's initial status even when the merged
lifecycle declares a different one — which can leave a freshly-initialised squad unable to
load at all on the very next command.
"""

from pathlib import Path

import pytest

from squads._errors import SquadsError
from squads._services import _service as service
from squads._workflow import bundled_spec

pytestmark = pytest.mark.anyio


def _write_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(content, encoding="utf-8")


# --------------------------------------------------------------------------- no-override floor


async def test_init_with_no_override_present_still_uses_the_bundled_singleton(
    tmp_path, monkeypatch, frozen_time
) -> None:
    """The fast path must stay byte-identical: no override file -> the same cached bundled
    ``WorkflowSpec`` object, not a freshly rebuilt (functionally-equal-but-different) one."""
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    svc = service.Service(result.paths)
    assert svc.spec is bundled_spec()
    assert (tmp_path / "squads" / "guides").is_dir()  # every bundled folder still scaffolded


# --------------------------------------------------------------------------- a drop, driven


async def test_init_does_not_scaffold_a_type_the_preexisting_override_drops(
    tmp_path, monkeypatch, frozen_time
) -> None:
    squad_dir = tmp_path / "squads"
    squad_dir.mkdir(parents=True)
    kept = sorted(set(bundled_spec().items) - {"guide"})
    _write_override(squad_dir, f"[selected]\nitems = {kept!r}\n")

    result = await service.init(root=tmp_path, roles_spec="minimal")
    assert not (squad_dir / "guides").exists()

    from squads._services._service import open_service

    svc = open_service(dir_override=str(squad_dir))
    assert "guide" not in svc.spec.items
    skill_slugs = {i.extra.get("slug") for i in await svc.list_items(item_type="skill")}
    assert "sq-guide" not in skill_slugs  # no orphan skill seeded for a type that never existed
    assert result.paths.squad_dir == squad_dir


# --------------------------------------------------------------------------- a rename, driven


async def test_init_scaffolds_a_renamed_type_under_its_new_folder_only(
    tmp_path, monkeypatch, frozen_time
) -> None:
    squad_dir = tmp_path / "squads"
    squad_dir.mkdir(parents=True)
    kept = [*sorted(set(bundled_spec().items) - {"guide"}), "howto"]
    _write_override(
        squad_dir,
        f"""
[selected]
items = {kept!r}

[items.howto]
prefix = "$(items.guide.prefix)"
folder = "howtos"
lifecycle = "$(items.guide.lifecycle)"
""",
    )

    await service.init(root=tmp_path, roles_spec="minimal")
    assert not (squad_dir / "guides").exists()
    assert (squad_dir / "howtos").is_dir()

    from squads._services._service import open_service

    svc = open_service(dir_override=str(squad_dir))
    assert "howto" in svc.spec.items
    assert svc.spec.items["howto"].folder == "howtos"


# --------------------------------------------------------------------------- roster initial
# status: the wrong-spec bug, driven both as a status mismatch and as the severe crash it can
# cause


async def test_init_activates_a_role_at_the_merged_lifecycles_initial_not_the_bundled_one(
    tmp_path, monkeypatch, frozen_time
) -> None:
    squad_dir = tmp_path / "squads"
    squad_dir.mkdir(parents=True)
    # A field-mergeable shadow of the roster lifecycle's own `initial` — allowed under the
    # roster lock (the lock is the type-key set + category, never the lifecycle).
    _write_override(squad_dir, '[lifecycles.agent]\ninitial = "Archived"\n')

    result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    activated = {r.extra["slug"]: r.status for r in result.roles}
    assert activated  # at least one role activated
    assert set(activated.values()) == {"Archived"}, activated


async def test_init_does_not_strand_a_squad_when_the_override_renames_the_roster_lifecycle(
    tmp_path, monkeypatch, frozen_time
) -> None:
    """The severe half of the bug: seeding roster items against the bundled spec's initial
    status can leave a status on the item that the merged spec never declares at all, so the
    very next command (``open_service``, which every ``sq`` invocation goes through) fails
    closed and the squad can never load. Reproduced with a roster type rebound to a wholly
    new lifecycle and the old statuses fully retired via ``[selected]``."""
    squad_dir = tmp_path / "squads"
    squad_dir.mkdir(parents=True)
    kept_statuses = [
        *sorted(set(bundled_spec().statuses) - {"Active", "Archived"}),
        "Enabled",
        "Disabled",
    ]
    kept_lifecycles = [*sorted(set(bundled_spec().lifecycles) - {"agent"}), "custom_agent"]
    _write_override(
        squad_dir,
        f"""
[statuses.Enabled]
role = "active"

[statuses.Disabled]
role = "retired"

[lifecycles.custom_agent]
initial = "Enabled"

[lifecycles.custom_agent.transitions]
Enabled = ["Disabled"]
Disabled = ["Enabled"]

[items.role]
lifecycle = "custom_agent"

[items.skill]
lifecycle = "custom_agent"

[items.operator]
lifecycle = "custom_agent"

[selected]
statuses = {kept_statuses!r}
lifecycles = {kept_lifecycles!r}
""",
    )

    await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)

    from squads._services._service import open_service

    # Must not raise: every roster item this call activated has to carry a status the
    # merged spec actually declares.
    svc = open_service(dir_override=str(squad_dir))
    roles = await svc.list_items(item_type="role")
    assert roles
    for role in roles:
        assert role.status == "Enabled"


# --------------------------------------------------------------------------- adopt shares the
# same fix


async def test_adopt_does_not_scaffold_a_type_the_preexisting_override_drops(
    tmp_path, monkeypatch, frozen_time
) -> None:
    squad_dir = tmp_path / "squads"
    squad_dir.mkdir(parents=True)
    kept = sorted(set(bundled_spec().items) - {"guide"})
    _write_override(squad_dir, f"[selected]\nitems = {kept!r}\n")

    await service.adopt(root=tmp_path, roles_spec="minimal")
    assert not (squad_dir / "guides").exists()


async def test_a_floor_violating_preexisting_override_fails_closed_at_init_not_silently_bundled(
    tmp_path, monkeypatch, frozen_time
) -> None:
    squad_dir = tmp_path / "squads"
    squad_dir.mkdir(parents=True)
    # Roster type-key lock violation: dropping `role` via `[selected]`.
    kept = sorted(set(bundled_spec().items) - {"role"})
    _write_override(squad_dir, f"[selected]\nitems = {kept!r}\n")

    with pytest.raises(SquadsError, match="sq workflow lint"):
        await service.init(root=tmp_path, roles_spec="minimal")
