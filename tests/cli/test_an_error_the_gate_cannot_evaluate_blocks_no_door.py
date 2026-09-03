"""A catalog error the create/update gate has no context to evaluate blocks no gated door — by
declaration, and on every door rather than on whichever one was tried.

``subentity_container_marker`` reports at error level and is right to: a renamed
``subentity_kinds.<kind>.plural`` half-bricks a corpus, and ``sq check`` is the only plane that
can see it. But it reads the item's on-disk text, and the gate holds none — a create gates an
``Item`` built in memory before its file is written, so a widened gate could only ever be an
update-door gate, and the condition is a corpus/spec disagreement that no create or update
causes and none can cure. So it sits the gate out, its findings stay in the report, and
ordinary edits keep working on a corpus in that state.

That was already the behaviour; what it was not was a decision. It fell out of the gate handing
the member an absent text and the member returning nothing, which is why the engine could carry
a comment claiming no error-level member read that field at all. The outcome is pinned here so
the declaration cannot change it silently in either direction — and per door, because a gate
that started refusing would refuse on one door first.
"""

from pathlib import Path

import pytest

from squads import __version__

pytestmark = pytest.mark.anyio

_RENAME_STORY_PLURAL = '[subentity_kinds.story]\nplural = "outcomes"\n'


def _write_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{content}", encoding="utf-8"
    )
    from squads._workflow._loader import load_workflow_spec

    load_workflow_spec(squad_dir=squad_dir)  # a fixture that will not load proves nothing


async def _misaligned_corpus(project, svc, invoke) -> str:
    """A feature written under the bundled plural, then a spec that renames it — the state the
    integrity check exits 3 on. Returned as the CLI's own item argument."""
    feature = (await svc.create("feature", "Existing", author="manager")).item
    _write_override(project.squad_dir, _RENAME_STORY_PLURAL)

    check = await invoke(["check"])
    assert check.exit_code == 3, check.output  # precondition: the error is live and reported
    assert "container section" in check.output.replace("\n", " ")
    return str(feature.sequence_id)


@pytest.mark.parametrize(
    "door",
    [
        pytest.param(["update", "--title", "Renamed"], id="update-title"),
        pytest.param(["status", "Ready"], id="status"),
        pytest.param(["update", "--assignee", "manager"], id="update-assignee"),
    ],
)
async def test_a_gated_door_stays_open_on_a_corpus_the_check_reports(
    door: list[str], project, svc, invoke
) -> None:
    seq = await _misaligned_corpus(project, svc, invoke)

    result = await invoke(["feature", seq, *door])

    assert result.exit_code == 0, result.output


async def test_the_check_still_reports_it_after_the_edits(project, svc, invoke) -> None:
    """The other half, so "the doors stay open" can never be satisfied by the report going
    quiet: the condition is untouched by the edits that were allowed through."""
    seq = await _misaligned_corpus(project, svc, invoke)

    for door in (["update", "--title", "Renamed"], ["status", "Ready"]):
        assert (await invoke(["feature", seq, *door])).exit_code == 0

    check = await invoke(["check"])
    assert check.exit_code == 3, check.output
    assert "container section" in check.output.replace("\n", " ")
