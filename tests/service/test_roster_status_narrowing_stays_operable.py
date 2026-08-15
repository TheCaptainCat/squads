"""A squad that reached a roster item at the now-dropped ``Draft`` status before the bundled
role/skill/operator lifecycle collapsed to ``Active`` ⇄ ``Archived`` (reachable, before the
collapse, only via ``--force``) stays fully operable: the two load-path claims below are
asserted directly rather than assumed.

Claim 1: no squad hard-stops on load. ``validate_against_index`` compares an item's status
against the spec's *global* status set, and ``Draft`` stays declared there (the work/guide
lifecycles own it) — narrowing only the roster machine cannot trip the fail-closed check.
Separately, the cross-check itself only runs when a workflow override file is present at all.

Claim 2: the remap is reachable. ``_apply_status`` validates only the *target* status against
the addressed type's own declared vocabulary, and ``force=True`` skips the transition-edge
check entirely — so ``sq role|skill|operator <addr> status Active --force`` moves an item off
a status no longer declared for its type.

``sq check``'s existing ``item_status_valid`` validator reports the affected item in the
interim (one error per item, same shape every other status-vocabulary violation gets) — no
second validator is added for this.
"""

import json
from pathlib import Path

import pytest

from squads._errors import SquadsError, StatusNotInWorkflowError
from squads._services import _service as service

pytestmark = pytest.mark.anyio


def _patch_index_item_field(index_path: Path, seq: int, field: str, value: str) -> None:
    data = json.loads(index_path.read_text(encoding="utf-8"))
    key = str(seq)
    data["items"][key] = {**data["items"][key], field: value}
    index_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _patch_md_frontmatter_field(md_path: Path, field: str, value: str) -> None:
    lines = md_path.read_text(encoding="utf-8").splitlines(keepends=True)
    patched = [f"{field}: {value}\n" if line.startswith(f"{field}:") else line for line in lines]
    md_path.write_text("".join(patched), encoding="utf-8")


def _drop_role_to_draft(project, role) -> None:
    """Simulate a role item that reached ``Draft`` before the roster lifecycle collapse —
    patches both the index and the frontmatter file so `sq check`/`repair` see a coherent
    (if invalid-for-its-type) squad, not a skew artifact of the test setup itself."""
    _patch_index_item_field(project.index_path, role.sequence_id, "status", "Draft")
    _patch_md_frontmatter_field(project.squad_dir / role.path, "status", "Draft")


# --------------------------------------------------------------------------- claim 1: no hard stop


async def test_a_role_at_the_dropped_draft_status_does_not_hard_stop_a_plain_squad(
    project, svc
) -> None:
    role = await svc.activate_role("qa")
    _drop_role_to_draft(project, role)

    items = await svc.list_items()  # would raise if the load boundary flagged it
    got = next(i for i in items if i.id == role.id)
    assert got.status == "Draft"


async def test_a_role_at_the_dropped_draft_status_does_not_hard_stop_open_service_with_an_override(
    project, svc
) -> None:
    """The cross-check DOES run once an override file exists (unlike the plain-squad fast
    path) — proving Draft still passes it because it stays declared in the spec's global
    status set, not merely because the check was skipped."""
    role = await svc.activate_role("qa")
    _drop_role_to_draft(project, role)

    override_dir = project.squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        '[items.incident]\nprefix = "INC"\nfolder = "incidents"\nlifecycle = "work"\n',
        encoding="utf-8",
    )

    reopened = service.open_service()  # would raise SquadsError if Draft were flagged
    got = await reopened.get(role.id)
    assert got.status == "Draft"


# --------------------------------------------------------------------------- claim 2: the remap


async def test_forcing_a_role_off_the_dropped_draft_status_succeeds(project, svc) -> None:
    role = await svc.activate_role("qa")
    _drop_role_to_draft(project, role)

    # Without --force: the transition-edge check rejects it (Draft isn't even a transition
    # source in the two-state machine's own table) rather than an IndexError/KeyError.
    with pytest.raises(SquadsError):
        await svc.set_status(role.id, "Active")

    remapped = await svc.set_status(role.id, "Active", force=True)
    assert remapped.status == "Active"


async def test_forcing_a_role_from_draft_to_an_undeclared_status_still_fails_the_vocabulary(
    project, svc
) -> None:
    """The remap only works because 'Active' is itself declared for role — force still never
    bypasses the target-status vocabulary check."""
    role = await svc.activate_role("qa")
    _drop_role_to_draft(project, role)

    with pytest.raises(StatusNotInWorkflowError, match="not a valid status for role"):
        await svc.set_status(role.id, "Done", force=True)


# --------------------------------------------------------------------------- sq check + recovery


async def test_check_reports_the_affected_role_and_is_clean_again_after_the_remap(
    project, svc
) -> None:
    role = await svc.activate_role("qa")
    _drop_role_to_draft(project, role)

    issues = await svc.check()
    assert any(i.item == role.id and "Draft" in i.message and "role" in i.message for i in issues)

    await svc.set_status(role.id, "Active", force=True)

    issues_after = await svc.check()
    assert not any(i.item == role.id for i in issues_after)
