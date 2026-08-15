"""A role override that will not load is reported by `sq check`, not only by the commands that
need it.

Role overrides became refusable — an unknown key, a wrong type, a model outside the closed
vocabulary. The refusal reached `sq sync` and `sq role <slug> show`, both at exit 1, and
nothing else: a role resolves lazily at the point of use, so no reporter's path ever loaded
one. A squad could therefore sit at "no issues", exit 0, `--json` `[]`, while `sq sync` was
impossible — and `sq check` is the gate an adopter's CI runs, the surface whose whole job is
finding that state before the command that needs it does.

The workflow and playbook overrides are each reported this way already. This pins the same
statement for the one document class that had no reporter at all, plus the two properties that
keep the report honest: it agrees with the commands that refuse (same file, same cause), and a
valid override still reports nothing.
"""

import json
from pathlib import Path

import pytest

from squads import __version__

pytestmark = pytest.mark.anyio

#: A model outside the closed whitelist. Chosen because it is the shape an adopter actually
#: reaches — a typo in a legal-looking value — rather than malformed TOML, which every reader
#: already refuses at parse time and would prove nothing about validation.
_BAD_MODEL = 'model = "opuss"\n'

#: The same file, valid: the control. A check that reported every role override would pass
#: every assertion about the broken one.
_GOOD_MODEL = 'model = "opus"\n'


def _place_role_override(squad_dir: Path, slug: str, body: str, *, stamped: bool = True) -> None:
    """Write `.overrides/roles/<slug>.toml`, stamped by default so the stamp obligation's own
    warning never stands in for the finding under test."""
    d = squad_dir / ".overrides" / "roles"
    d.mkdir(parents=True, exist_ok=True)
    stamp = f"# squads:override-base:{__version__}\n" if stamped else ""
    (d / f"{slug}.toml").write_text(f"{stamp}{body}", encoding="utf-8")


def _assert_fixture_is_broken_as_intended(squad_dir: Path, slug: str) -> None:
    """Load the override eagerly. A fixture broken some other way (a TOML syntax error, a path
    typo that means no file is read at all) would otherwise read as the refusal under test and
    prove nothing — the silent-setup-failure trap this whole finding is an instance of."""
    from squads._errors import SquadsError
    from squads._roles._resolver import resolve_role

    with pytest.raises(SquadsError, match="opuss"):
        resolve_role(slug, squad_dir)


async def test_check_reports_a_role_override_that_will_not_load(project, invoke) -> None:
    _place_role_override(project.squad_dir, "reviewer", _BAD_MODEL)
    _assert_fixture_is_broken_as_intended(project.squad_dir, "reviewer")

    result = await invoke(["check"])

    assert result.exit_code == 3, result.output
    assert "reviewer.toml" in result.output


async def test_the_report_names_the_file_the_cause_and_the_commands_it_blocks(
    project, invoke
) -> None:
    """Three things, because a reporter that only says "invalid" costs the adopter the same
    investigation the report was supposed to save. Read off `--json`, not the table: the
    console wraps a long line mid-phrase, so asserting on the rendered text would pin the
    terminal width rather than the message."""
    _place_role_override(project.squad_dir, "reviewer", _BAD_MODEL)
    _assert_fixture_is_broken_as_intended(project.squad_dir, "reviewer")

    result = await invoke(["check", "--json"])
    (issue,) = [i for i in json.loads(result.output) if i["level"] == "error"]

    assert "reviewer.toml" in issue["item"]  # which file
    assert "opuss" in issue["message"]  # what is wrong, at value level
    assert "sq sync" in issue["message"]  # what it blocks


async def test_a_slug_the_roster_does_not_carry_is_reported_too(project, invoke) -> None:
    """Scoping the report to live roles would have been the smaller change and the wrong one:
    `sq role <slug> show` resolves an override for a bundled role that was never activated, so
    that file is reachable — and refusable — on a squad whose roster has never heard of it.
    This fixture's roster is `minimal` (manager only), so `reviewer` is exactly that case."""
    _place_role_override(project.squad_dir, "reviewer", _BAD_MODEL)

    checked = await invoke(["check"])
    shown = await invoke(["role", "reviewer", "show"])

    assert shown.exit_code == 1, shown.output
    assert checked.exit_code == 3, checked.output
    assert "opuss" in checked.output and "opuss" in shown.output


async def test_the_json_reporter_carries_it_too(project, invoke) -> None:
    """`--json` is the CI-facing surface, and it was the emptier lie: `[]` says checked and
    clean, where the table at least printed the stamp warning."""
    _place_role_override(project.squad_dir, "reviewer", _BAD_MODEL)
    _assert_fixture_is_broken_as_intended(project.squad_dir, "reviewer")

    result = await invoke(["check", "--json"])

    assert result.exit_code == 3, result.output
    issues = json.loads(result.output)
    errors = [i for i in issues if i["level"] == "error"]
    assert errors, issues
    assert any("reviewer.toml" in i["item"] for i in errors)


async def test_check_and_sync_agree_about_the_same_file(project, invoke) -> None:
    """The property that makes this a reporter rather than a second opinion: check must never
    claim a refusal `sq sync` does not make, nor stay silent on one it does. Both resolve
    through the same function, and this asserts the two answers name the same cause.

    The override targets `manager` — the one role this fixture's `minimal` roster carries — so
    sync actually reaches it. Written against a non-roster slug this passes for the wrong
    reason: sync never resolves the file at all."""
    _place_role_override(project.squad_dir, "manager", _BAD_MODEL)
    _assert_fixture_is_broken_as_intended(project.squad_dir, "manager")

    checked = await invoke(["check"])
    synced = await invoke(["sync"])

    assert checked.exit_code == 3
    assert synced.exit_code == 1
    assert "opuss" in checked.output and "opuss" in synced.output


async def test_a_valid_role_override_reports_nothing(project, invoke) -> None:
    """The control. Without it every assertion above is satisfied by a check that flags any
    role override at all — which would make the gate unusable for the adopters it is for."""
    _place_role_override(project.squad_dir, "reviewer", _GOOD_MODEL)

    result = await invoke(["check"])

    assert result.exit_code == 0, result.output
    assert "reviewer.toml" not in result.output


async def test_an_unknown_key_is_reported_as_well_as_a_bad_value(project, invoke) -> None:
    """The other half of what became refusable: a typo'd key used to vanish silently, so the
    adopter's edit had no effect and nothing said so. It is now a hard stop for `sq sync`, and
    therefore has to be visible here too."""
    _place_role_override(project.squad_dir, "reviewer", 'titel = "Chief Inspector"\n')

    result = await invoke(["check"])

    assert result.exit_code == 3, result.output
    assert "titel" in result.output


async def test_an_unstamped_broken_override_reports_both_facts(project, invoke) -> None:
    """The stamp warning and the load failure are independent obligations on one file. Reporting
    only the first is what the driven repro of this defect actually saw, and it reads as "your
    override is fine, just re-stamp it"."""
    _place_role_override(project.squad_dir, "reviewer", _BAD_MODEL, stamped=False)

    result = await invoke(["check", "--json"])
    issues = json.loads(result.output)
    messages = [i["message"] for i in issues if "reviewer.toml" in i["item"]]

    assert any("override-base" in m for m in messages), messages
    assert any("opuss" in m for m in messages), messages
