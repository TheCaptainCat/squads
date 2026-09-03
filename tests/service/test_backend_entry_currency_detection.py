"""The currency half of per-entry pointer detection: ``sq check`` compares a fresh render of
each declared live per-entry artifact against disk, and ``sq sync`` reports what it fixes.

Presence (an absent pointer) is a different, already-shipped finding
(``test_backend_reconciled_per_entry_pointers.py``); every test here starts from a pointer that
**exists** and drives a genuine content mismatch — the only shape currency's own comparison
covers, per its own docstring in ``squads._services._validators``.

Severity is keyed on the containment rule, never on a hard-coded field name: a drifted or
missing capability restriction (``disallowedTools`` on a leaf role, i.e. one with
``can_spawn=False``) is an **error**; any other content drift is a **warn**.
"""

from pathlib import Path

import pytest

from squads._services import _service as service

pytestmark = pytest.mark.anyio


@pytest.fixture
def tmp_squad(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _drift_issues(issues, rel_path: str):
    return [i for i in issues if rel_path in i.item and "drifted" in i.message]


# --------------------------------------------------------------------------- a current pointer


async def test_a_current_pointer_produces_no_finding(tmp_squad: Path) -> None:
    result = await service.init(root=tmp_squad, backend=["claude_code"], roles_spec="minimal")
    svc = service.Service(result.paths)
    await svc.activate_role("qa")

    issues = await svc.check()
    assert not _drift_issues(issues, "manager.md")
    assert not _drift_issues(issues, "qa.md")


# ------------------------------------------------------------------ warn: non-restriction drift


async def test_a_hand_edited_description_is_a_warn(tmp_squad: Path) -> None:
    """A role's frontmatter ``description`` restricts nothing — it only *supplies* selection
    text — so a hand-edit to it is a warn, never an error."""
    result = await service.init(root=tmp_squad, backend=["claude_code"], roles_spec="minimal")
    svc = service.Service(result.paths)
    pointer = tmp_squad / ".claude" / "agents" / "manager.md"
    text = pointer.read_text(encoding="utf-8")
    assert 'description: "' in text
    pointer.write_text(
        text.replace('description: "', 'description: "HAND-EDITED '), encoding="utf-8"
    )

    issues = await svc.check()
    hits = _drift_issues(issues, "manager.md")
    assert hits, issues
    hit = hits[0]
    assert hit.level == "warn"
    assert "claude_code" in hit.message


async def test_a_hand_edited_skill_pointer_is_a_warn(tmp_squad: Path) -> None:
    result = await service.init(root=tmp_squad, backend=["claude_code"], roles_spec="minimal")
    svc = service.Service(result.paths)
    await svc.sync()
    skills_dir = tmp_squad / ".claude" / "skills"
    one_skill = next(p for p in skills_dir.iterdir() if p.is_dir())
    pointer = one_skill / "SKILL.md"
    text = pointer.read_text(encoding="utf-8")
    pointer.write_text(text + "\nHAND-EDITED TRAILER\n", encoding="utf-8")

    issues = await svc.check()
    hits = _drift_issues(issues, f"{one_skill.name}/SKILL.md")
    assert hits, issues
    hit = hits[0]
    assert hit.level == "warn"


# ---------------------------------------------------------------------- error: restriction drift


async def test_a_missing_restriction_on_a_leaf_role_is_an_error(tmp_squad: Path) -> None:
    """``qa`` carries no ``can_spawn`` in the bundled catalog, so its pointer must render
    ``disallowedTools: Agent``. Deleting that line — as a stale, pre-revocation pointer would
    read — is the capability-escalation shape the error severity exists for."""
    result = await service.init(root=tmp_squad, backend=["claude_code"], roles_spec="minimal")
    svc = service.Service(result.paths)
    await svc.activate_role("qa")
    pointer = tmp_squad / ".claude" / "agents" / "qa.md"
    text = pointer.read_text(encoding="utf-8")
    assert "disallowedTools: Agent" in text
    pointer.write_text(text.replace("disallowedTools: Agent\n", ""), encoding="utf-8")

    issues = await svc.check()
    hits = _drift_issues(issues, "qa.md")
    assert hits, issues
    hit = hits[0]
    assert hit.level == "error"
    assert "claude_code" in hit.message


async def test_a_role_that_may_spawn_carries_no_restriction_to_drift(tmp_squad: Path) -> None:
    """``manager`` (``can_spawn = true`` in the bundled catalog) has no ``disallowedTools``
    line to begin with, so a content drift elsewhere on its pointer is a warn, never an error
    reached through the restriction fragment."""
    result = await service.init(root=tmp_squad, backend=["claude_code"], roles_spec="minimal")
    svc = service.Service(result.paths)
    pointer = tmp_squad / ".claude" / "agents" / "manager.md"
    text = pointer.read_text(encoding="utf-8")
    assert "disallowedTools" not in text
    # Drift the description line (present on every role's pointer) to force a mismatch with
    # nothing to do with the capability boundary.
    pointer.write_text(
        text.replace('description: "', 'description: "HAND-EDITED '), encoding="utf-8"
    )

    issues = await svc.check()
    hits = _drift_issues(issues, "manager.md")
    assert hits, issues
    hit = hits[0]
    assert hit.level == "warn"


# -------------------------------------------------------------- retire/reactivate stays clean


async def test_retire_reactivate_produces_no_drift_finding_at_any_point(tmp_squad: Path) -> None:
    """The same hard constraint presence's own cycle proves, for currency: the comparison's
    path set is roster-scoped to the *live* set, never a fixed or historical slug list, so a
    retired entry's (withdrawn, absent) pointer is never a candidate for a content comparison
    at any point in the cycle — driven end to end, not reasoned about."""
    result = await service.init(root=tmp_squad, backend=["claude_code"], roles_spec="minimal")
    svc = service.Service(result.paths)
    item = await svc.activate_role("qa")

    issues = await svc.check()
    assert not any("drifted" in i.message for i in issues), issues

    await svc.set_status(item.id, "Archived")
    issues = await svc.check()
    assert not any("qa" in i.item and "drifted" in i.message for i in issues), issues

    await svc.set_status(item.id, "Active")
    issues = await svc.check()
    assert not any("drifted" in i.message for i in issues), issues


# --------------------------------------------------------------------------- sq sync's own report


async def test_sync_reports_a_currency_fix_distinctly_from_a_presence_fix(tmp_squad: Path) -> None:
    result = await service.init(root=tmp_squad, backend=["claude_code"], roles_spec="minimal")
    svc = service.Service(result.paths)
    await svc.activate_role("qa")

    manager_pointer = tmp_squad / ".claude" / "agents" / "manager.md"
    text = manager_pointer.read_text(encoding="utf-8")
    manager_pointer.write_text(
        text.replace('description: "', 'description: "HAND-EDITED '), encoding="utf-8"
    )
    (tmp_squad / ".claude" / "agents" / "qa.md").unlink()

    skipped = await svc.sync()
    presence = [m for m in skipped if "was missing" in m]
    currency = [m for m in skipped if "had drifted" in m]
    assert any("qa.md" in m for m in presence), skipped
    assert any("manager.md" in m for m in currency), skipped
    assert not any("manager.md" in m for m in presence)
    assert not any("qa.md" in m for m in currency)

    assert not await svc.sync()  # converged; a further sync is silent


async def test_sync_fixes_the_content_a_hand_edit_broke(tmp_squad: Path) -> None:
    result = await service.init(root=tmp_squad, backend=["claude_code"], roles_spec="minimal")
    svc = service.Service(result.paths)
    pointer = tmp_squad / ".claude" / "agents" / "manager.md"
    text = pointer.read_text(encoding="utf-8")
    pointer.write_text(text.replace("Load your full", "TAMPERED your full"), encoding="utf-8")

    await svc.sync()
    assert "TAMPERED" not in pointer.read_text(encoding="utf-8")
    assert "Load your full" in pointer.read_text(encoding="utf-8")
