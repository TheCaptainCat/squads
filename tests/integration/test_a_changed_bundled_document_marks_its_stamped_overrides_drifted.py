"""An override stamped at an earlier release reports ``drifted`` once the bundled document it
overrides has changed since, and stays ``current`` when stamped at the running version.

One table: the overridden document by the version its override is stamped at.
"""

from pathlib import Path

import pytest

from squads import __version__
from squads._overrides._service import STATE_CURRENT, STATE_DRIFTED, scan_overrides

pytestmark = pytest.mark.anyio

_PREVIOUS_RELEASE = "0.15.0"


def _catalog(squad_dir: Path, stamp: str) -> None:
    overrides = squad_dir / ".overrides"
    overrides.mkdir(exist_ok=True)
    (overrides / "roles.toml").write_text(
        f'# squads:override-base:{stamp}\n[dev]\ncolor = "pink"\n', encoding="utf-8"
    )


def _role_file(squad_dir: Path, stamp: str) -> None:
    roles = squad_dir / ".overrides" / "roles"
    roles.mkdir(parents=True, exist_ok=True)
    (roles / "architect.toml").write_text(
        f'# squads:override-base:{stamp}\nfull_name = "Ada"\n', encoding="utf-8"
    )


def _playbook(squad_dir: Path, stamp: str) -> None:
    overrides = squad_dir / ".overrides"
    overrides.mkdir(exist_ok=True)
    (overrides / "playbook.toml").write_text(
        f"# squads:override-base:{stamp}\n"
        '[types.task]\nroles = ["$(*self)", { slug = "architect", do = ["review the design"] }]\n',
        encoding="utf-8",
    )


def _template(squad_dir: Path, stamp: str) -> None:
    from squads._overrides._manifest import bundled_template_content
    from squads._overrides._stamp import write_template_stamp

    path = squad_dir / ".overrides" / "templates" / "claude" / "claude_section.md.j2"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        write_template_stamp(bundled_template_content("claude/claude_section.md.j2") or "", stamp),
        encoding="utf-8",
    )


_DOCUMENTS = {
    "role-catalog": (_catalog, "roles"),
    "per-slug-role-file": (_role_file, "architect"),
    "playbook": (_playbook, "playbook"),
    "template": (_template, "claude/claude_section.md.j2"),
}


_CHECK_LABEL = {
    "role-catalog": ".overrides/roles.toml: role catalog override",
    "per-slug-role-file": ".overrides/roles/architect.toml: role override",
    "playbook": ".overrides/playbook.toml: playbook override",
    "template": ".overrides/templates/claude/claude_section.md.j2: override",
}


@pytest.mark.parametrize(
    ("stamp", "expected"),
    [(_PREVIOUS_RELEASE, STATE_DRIFTED), (__version__, STATE_CURRENT)],
    ids=["stamped-at-the-previous-release", "stamped-at-the-running-version"],
)
@pytest.mark.parametrize("document", list(_DOCUMENTS))
async def test_the_state_follows_whether_the_bundled_document_changed_since_the_stamp(
    document: str, stamp: str, expected: str, project, invoke
) -> None:
    write, name = _DOCUMENTS[document]
    write(project.squad_dir, stamp)
    entries = {e.name: e for e in scan_overrides(project.squad_dir)}
    assert entries[name].state == expected

    listed = await invoke(["override", "list"])
    assert listed.exit_code == 0, listed.output
    row = next(line for line in listed.output.splitlines() if name in line.split())
    assert expected in row
    checked = await invoke(["check"])
    assert checked.exit_code == 0, checked.output
    text = " ".join(checked.output.split())
    assert (f"{_CHECK_LABEL[document]} may be stale" in text) is (expected == STATE_DRIFTED), text
