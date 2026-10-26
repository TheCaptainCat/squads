"""An override that redeclares a lifecycle's transitions drops the bundled keys it never names
and nothing enters; a key the override names itself is the adopter's and stays reported."""

from pathlib import Path

from squads import __version__
from squads._workflow._loader import lint_workflow_spec


def _lint(squad_dir: Path, body: str) -> list[str]:
    override = squad_dir / ".overrides" / "workflow.toml"
    override.parent.mkdir(parents=True, exist_ok=True)
    override.write_text(f"# squads:override-base:{__version__}\n{body}", encoding="utf-8")
    return [finding[2] for finding in lint_workflow_spec(squad_dir)]


def test_an_open_redeclaring_override_with_one_unrelated_error_lints_only_that_error(
    tmp_path: Path,
) -> None:
    unrelated = '[items.task]\nparents = ["nonesuch"]\n'
    alone = _lint(tmp_path / "alone", unrelated)

    both = _lint(
        tmp_path / "both",
        '[lifecycles.finding.transitions]\nOpen = ["Fixed", "WontFix"]\n' + unrelated,
    )

    assert alone
    assert both == alone
    assert not any("unreachable" in m for m in both)


def test_a_bundled_key_the_override_names_is_still_reported_when_nothing_enters_it(
    tmp_path: Path,
) -> None:
    messages = _lint(
        tmp_path,
        '[lifecycles.finding.transitions]\nOpen = ["Fixed", "WontFix"]\nNoted = ["Deferred"]\n',
    )

    assert any("'Noted' unreachable" in m for m in messages), messages
