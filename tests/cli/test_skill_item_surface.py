"""The SKILL item's user-facing CLI surface: sq skill <n> show (text + JSON) and refs
to/from a skill round-trip through the forward-edges-only backref invariant.

Deferred from the migration chunk: these are agent-artifact facts, not migration-shaped.
"""

import json

import pytest

from squads._services import _service as service

pytestmark = pytest.mark.anyio


@pytest.fixture
async def seeded_paths(tmp_path, monkeypatch, frozen_time):
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal")
    return result.paths


async def test_skill_show_renders_id_slug_status_and_body(seeded_paths, invoke) -> None:
    svc = service.Service(seeded_paths)
    (sk,) = (await svc.list_items(item_type="skill"))[:1]

    r = await invoke(["skill", str(sk.sequence_id), "show"])
    assert r.exit_code == 0, r.output
    assert sk.id in r.output
    assert sk.slug in r.output
    assert "Active" in r.output


async def test_skill_show_json_carries_id_slug_and_status(seeded_paths, invoke) -> None:
    svc = service.Service(seeded_paths)
    (sk,) = (await svc.list_items(item_type="skill"))[:1]

    r = await invoke(["skill", str(sk.sequence_id), "show", "--json"])
    data = json.loads(r.output)
    assert data["id"] == sk.id
    assert data["slug"] == sk.slug
    assert data["status"] == "Active"


async def test_a_task_can_ref_a_skill_and_the_forward_ref_appears_in_its_refs(
    seeded_paths, invoke
) -> None:
    svc = service.Service(seeded_paths)
    task = (await svc.create("task", "Ref test task")).item
    (sk,) = (await svc.list_items(item_type="skill"))[:1]

    r = await invoke(["task", str(task.sequence_id), "ref", "add", sk.id, "--kind", "related"])
    assert r.exit_code == 0, r.output

    r = await invoke(["task", str(task.sequence_id), "refs"])
    assert sk.id in r.output


async def test_a_skills_backref_appears_via_refs_in_never_persisted(seeded_paths, invoke) -> None:
    """CLAUDE.md invariant #4: backrefs are computed by inversion, never persisted."""
    svc = service.Service(seeded_paths)
    task = (await svc.create("task", "Backref test task")).item
    (sk,) = (await svc.list_items(item_type="skill"))[:1]
    await svc.add_ref(task.id, sk.id, kind="related")

    r = await invoke(["skill", str(sk.sequence_id), "refs", "--in"])
    assert r.exit_code == 0, r.output
    assert task.id in r.output


async def test_a_feature_ref_to_a_skill_round_trips_forward_and_backward(
    seeded_paths, invoke
) -> None:
    svc = service.Service(seeded_paths)
    feat = (await svc.create("feature", "Ref test feature")).item
    (sk,) = (await svc.list_items(item_type="skill"))[:1]

    r = await invoke(["feature", str(feat.sequence_id), "ref", "add", sk.id, "--kind", "related"])
    assert r.exit_code == 0, r.output

    r = await invoke(["feature", str(feat.sequence_id), "refs"])
    assert sk.id in r.output
    r = await invoke(["skill", str(sk.sequence_id), "refs", "--in"])
    assert feat.id in r.output
