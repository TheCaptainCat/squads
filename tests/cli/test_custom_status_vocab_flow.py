"""A project-declared custom lifecycle flows correctly through every status-classifying CLI
surface: ``sq list --status``/loose matching/unknown-value error, the default hide-closed
filter, ``sq blocked``, and ``sq inbox`` — all honoring the *custom* open/terminal boundary the
same way they honor the built-in one. Every one of these surfaces reads ``spec.is_open(status)``
/ ``spec.statuses`` already; this is an end-to-end proof against a real override, not a rewire.
"""

import json
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.anyio

_INCIDENT_OVERRIDE = """
[statuses.Triage]
[statuses.Mitigating]
[statuses.Resolved]
role = "done"

[lifecycles.incident_lc]
initial = "Triage"
[lifecycles.incident_lc.transitions]
Triage = ["Mitigating", "Resolved"]
Mitigating = ["Resolved"]
Resolved = []

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "incident_lc"
"""


def _write_override(squad_dir: Path) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(_INCIDENT_OVERRIDE, encoding="utf-8")


def _created_id(output: str) -> str:
    m = re.search(r"INC-(\d+)", output)
    assert m is not None, f"could not find an INC-N id in:\n{output}"
    return m.group(0)


def _num(item_id: str) -> str:
    return item_id.rsplit("-", 1)[-1]


@pytest.fixture
async def custom_squad(project, invoke):
    _write_override(project.squad_dir)
    return project


# --------------------------------------------------------------------------- parse_status /
# sq list --status


async def test_list_status_accepts_a_custom_value_case_and_underscore_insensitively(
    custom_squad, invoke
) -> None:
    created = await invoke(["create", "incident", "First incident", "--author", "manager"])
    inc_id = _created_id(created.output)

    exact = await invoke(["list", "--status", "Triage"])
    assert exact.exit_code == 0 and inc_id in exact.output

    loose = await invoke(["list", "--status", "triage"])
    assert loose.exit_code == 0 and inc_id in loose.output


async def test_list_status_rejects_an_unknown_value_naming_the_known_custom_statuses(
    custom_squad, invoke
) -> None:
    result = await invoke(["list", "--status", "Bogus"])
    assert result.exit_code == 1
    assert "unknown status" in result.output and "Bogus" in result.output
    for known in ("Triage", "Mitigating", "Resolved"):
        assert known in result.output


async def test_list_status_filter_returns_exactly_the_items_in_that_custom_status(
    custom_squad, invoke
) -> None:
    a = await invoke(["create", "incident", "Incident A", "--author", "manager"])
    b = await invoke(["create", "incident", "Incident B", "--author", "manager"])
    a_id, b_id = _created_id(a.output), _created_id(b.output)
    await invoke(["incident", _num(b_id), "update", "--status", "Resolved"])

    result = await invoke(["list", "--status", "Triage"])
    assert a_id in result.output and b_id not in result.output


# --------------------------------------------------------------------------- default filter
# honors custom terminality


@pytest.mark.parametrize(
    ("status_value", "expected_hidden"),
    [("Triage", False), ("Mitigating", False), ("Resolved", True)],
)
async def test_list_default_hides_a_custom_terminal_status_shows_a_custom_open_one(
    custom_squad, invoke, status_value: str, expected_hidden: bool
) -> None:
    created = await invoke(["create", "incident", "Incident", "--author", "manager"])
    inc_id = _created_id(created.output)
    await invoke(["incident", _num(inc_id), "update", "--status", status_value])

    default = await invoke(["list"])
    is_hidden = inc_id not in default.output
    assert is_hidden == expected_hidden

    with_all = await invoke(["list", "--all"])
    assert inc_id in with_all.output


# --------------------------------------------------------------------------- sq blocked honors
# custom terminality


async def test_blocked_treats_a_custom_non_terminal_blocker_as_still_blocking(
    custom_squad, invoke
) -> None:
    blocker = await invoke(["create", "incident", "Blocker", "--author", "manager"])
    dependent = await invoke(["create", "incident", "Dependent", "--author", "manager"])
    blocker_id, dependent_id = _created_id(blocker.output), _created_id(dependent.output)
    await invoke(["incident", _num(dependent_id), "ref", "add", blocker_id, "--kind", "depends-on"])

    r = await invoke(["blocked"])
    assert dependent_id in r.output and "blocked by" in r.output and blocker_id in r.output


async def test_blocked_clears_once_the_blocker_reaches_a_custom_terminal_status(
    custom_squad, invoke
) -> None:
    blocker = await invoke(["create", "incident", "Blocker", "--author", "manager"])
    dependent = await invoke(["create", "incident", "Dependent", "--author", "manager"])
    blocker_id, dependent_id = _created_id(blocker.output), _created_id(dependent.output)
    await invoke(["incident", _num(dependent_id), "ref", "add", blocker_id, "--kind", "depends-on"])
    await invoke(["incident", _num(blocker_id), "update", "--status", "Resolved"])

    r = await invoke(["blocked"])
    assert "nothing blocked" in r.output


async def test_blocked_json_reports_the_custom_status_string_verbatim(custom_squad, invoke) -> None:
    blocker = await invoke(["create", "incident", "Blocker", "--author", "manager"])
    dependent = await invoke(["create", "incident", "Dependent", "--author", "manager"])
    blocker_id, dependent_id = _created_id(blocker.output), _created_id(dependent.output)
    await invoke(["incident", _num(dependent_id), "ref", "add", blocker_id, "--kind", "depends-on"])

    r = await invoke(["blocked", "--json"])
    data = json.loads(r.output)
    assert data == [
        {
            "id": dependent_id,
            "title": "Dependent",
            "blockers": [{"id": blocker_id, "title": "Blocker", "status": "Triage"}],
        }
    ]


# --------------------------------------------------------------------------- sq inbox honors
# custom terminality


async def test_inbox_shows_a_mention_on_a_custom_non_terminal_item_but_not_a_terminal_one(
    custom_squad, invoke
) -> None:
    open_inc = await invoke(["create", "incident", "Open incident", "--author", "manager"])
    open_id = _created_id(open_inc.output)
    await invoke(["incident", _num(open_id), "comment", "--as", "manager", "-m", "look @manager"])

    resolved_inc = await invoke(["create", "incident", "Resolved incident", "--author", "manager"])
    resolved_id = _created_id(resolved_inc.output)
    await invoke(["incident", _num(resolved_id), "update", "--status", "Resolved"])
    await invoke(
        ["incident", _num(resolved_id), "comment", "--as", "manager", "-m", "look @manager"]
    )

    r = await invoke(["inbox", "manager"])
    assert open_id in r.output
    assert resolved_id not in r.output
