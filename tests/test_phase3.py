import pytest

from squads._errors import SquadsError
from squads._itemfile import read_frontmatter
from squads._models._enums import ItemType, Status

# --------------------------------------------------------------------------- refs


def test_refs_out_and_computed_backrefs(svc):
    task = svc.create(ItemType.TASK, "t").item
    guide = svc.create(ItemType.GUIDE, "g").item
    svc.add_ref(task.id, guide.id, kind="implements")
    assert svc.refs_out(task.id) == [(guide.id, "implements")]
    assert svc.refs_in(guide.id) == [(task.id, "implements")]
    # forward edge persisted in frontmatter; nothing backref-shaped stored
    fm = read_frontmatter(svc.paths.abspath(svc.get(task.id).path))
    assert fm["refs"] == [guide.id]
    assert "backrefs" not in svc.store.load().to_json()


def test_ref_rm_and_self_ref_rejected(svc):
    a = svc.create(ItemType.TASK, "a").item
    b = svc.create(ItemType.TASK, "b").item
    svc.add_ref(a.id, b.id)
    svc.rm_ref(a.id, b.id)
    assert svc.refs_out(a.id) == []
    with pytest.raises(SquadsError):
        svc.add_ref(a.id, a.id)


# --------------------------------------------------------------------------- renumber


def test_repair_renumber_resolves_collision(svc):
    # build a collision like a git merge would: two items sharing number 000003
    svc.create(ItemType.TASK, "real task")  # TASK-000002
    bug = svc.create(ItemType.BUG, "real bug").item  # BUG-000003
    # forge a feature file that also claims number 000003, referenced by the bug
    feat_dir = svc.paths.folder_for(ItemType.FEATURE)
    forged = feat_dir / "FEAT-000003-forged.md"
    forged.write_text(
        "---\nid: FEAT-000003\ntype: feature\ntitle: forged\nstatus: Draft\n"
        "created_at: '2026-01-01T00:00:00Z'\nupdated_at: '2026-01-01T00:00:00Z'\n---\n"
        "<!-- sq:body -->\n<!-- sq:body:end -->\n"
        "<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n",
        encoding="utf-8",
    )
    # rebuild so the forged item enters the index, then have the bug reference it
    svc.repair()
    svc.add_ref(bug.id, "FEAT-000003")

    db = svc.repair(renumber=True)

    numbers = [int(i.rsplit("-", 1)[-1]) for i in db.items]
    assert len(numbers) == len(set(numbers)), "no duplicate numbers remain"
    # BUG-000003 kept its number (sorts before FEAT-000003); FEAT got a fresh one
    assert bug.id in db.items
    new_feat = next(i for i in db.items if i.startswith("FEAT-"))
    assert new_feat != "FEAT-000003"
    # the bug's forward ref was rewritten to the new feature id
    assert db.items[bug.id].refs == [new_feat]
    # counter advanced past the reassigned number
    assert db.counter == max(numbers)


# --------------------------------------------------------------------------- dev


def test_dev_add_auto_name_and_slug(svc):
    d1 = svc.add_dev("dotnet")
    assert d1.extra["slug"] == "dotnet-dev"
    assert d1.extra["full_name"].endswith("Dotnet")
    assert d1.extra["is_dev"] is True
    d2 = svc.add_dev("python", name="Grace Hopper")
    assert d2.extra["full_name"] == "Grace Hopper"
    assert d2.extra["slug"] == "python-dev"
    with pytest.raises(SquadsError):
        svc.add_dev("dotnet")  # duplicate slug


def test_dev_pointer_generated(svc):
    svc.add_dev("rust")
    pointer = svc.paths.claude_dir / "agents" / "rust-dev.md"
    assert pointer.exists()
    assert "Rust" in pointer.read_text()


# --------------------------------------------------------------------------- skills


def test_skill_add_generates_pointer(svc):
    skill = svc.add_skill(
        "PDF extract", description="Pull text", when_to_use="when a pdf is attached"
    )
    assert skill.type is ItemType.SKILL
    assert skill.status is Status.ACTIVE
    pointer = svc.paths.claude_dir / "skills" / "pdf-extract" / "SKILL.md"
    assert pointer.exists()
    assert skill.path in pointer.read_text()


def test_skill_rm_purge_removes_pointer_and_file(svc):
    skill = svc.add_skill("Temp skill")
    path = svc.paths.abspath(skill.path)
    pointer_dir = svc.paths.claude_dir / "skills" / "temp-skill"
    assert path.exists() and pointer_dir.exists()
    svc.remove_item(skill.id, purge=True)
    assert skill.id not in svc.store.load().items
    assert not path.exists()
    assert not pointer_dir.exists()


# --------------------------------------------------------------------------- sync / version


def test_sync_stamps_version(svc, monkeypatch):
    import squads

    monkeypatch.setattr(squads, "__version__", "9.9.9", raising=False)
    monkeypatch.setattr("squads._service.__version__", "9.9.9", raising=False)
    svc.sync()
    import tomllib

    cfg = tomllib.loads(svc.paths.config_path.read_text())
    assert cfg["squads_version"] == "9.9.9"


def test_version_notice_triggers_when_newer(capsys, project, monkeypatch):
    from squads._cli import _common as common

    monkeypatch.setattr(common, "__version__", "9.9.9", raising=False)
    common.set_active_dir(None)
    monkeypatch.chdir(project.root)
    common.version_notice()
    err = capsys.readouterr().err
    assert "sq sync" in err
