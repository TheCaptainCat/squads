import pytest

from squads.errors import InvalidTransitionError, ItemNotFoundError
from squads.itemfile import read_frontmatter
from squads.models import ItemType, Status


def test_create_allocates_id_and_writes_file(svc):
    res = svc.create(ItemType.FEATURE, "User authentication", description="Login")
    assert res.item.id == "FEAT-000002"  # ROLE-000001 took the first number
    assert res.path.exists()
    assert res.path.name == "FEAT-000002-user-authentication.md"
    fm = read_frontmatter(res.path)
    assert fm["status"] == "Draft"
    assert fm["id"] == "FEAT-000002"


def test_create_rejects_missing_parent(svc):
    with pytest.raises(ItemNotFoundError):
        svc.create(ItemType.TASK, "x", parent="FEAT-999999")


def test_status_transition_and_validation(svc):
    res = svc.create(ItemType.TASK, "t")
    with pytest.raises(InvalidTransitionError):
        svc.set_status(res.item.id, Status.DONE)  # Draft -> Done illegal
    svc.set_status(res.item.id, Status.IN_PROGRESS)
    forced = svc.set_status(res.item.id, Status.DONE, force=False)  # InProgress -> Done legal
    assert forced.status is Status.DONE
    # frontmatter mirrors the index
    assert read_frontmatter(svc.paths.abspath(forced.path))["status"] == "Done"


def test_update_title_renames_file(svc):
    res = svc.create(ItemType.TASK, "Fix login")
    old = res.path
    updated = svc.update(res.item.id, title="Fix login loop")
    assert updated.slug == "fix-login-loop"
    assert not old.exists()
    assert svc.paths.abspath(updated.path).exists()
    assert updated.path.endswith("TASK-000002-fix-login-loop.md")


def test_link_unlink(svc):
    feat = svc.create(ItemType.FEATURE, "f").item
    task = svc.create(ItemType.TASK, "t").item
    svc.link(task.id, feat.id)
    assert svc.get(task.id).parent == feat.id
    svc.unlink(task.id)
    assert svc.get(task.id).parent is None


def test_repair_rebuilds_index_from_frontmatter(svc):
    svc.create(ItemType.FEATURE, "f")
    svc.create(ItemType.TASK, "t")
    # frontmatter is the durable truth: nuke the index and rebuild
    svc.paths.index_path.unlink()
    db = svc.repair()
    assert set(db.items) == {"ROLE-000001", "FEAT-000002", "TASK-000003"}
    assert db.counter == 3
