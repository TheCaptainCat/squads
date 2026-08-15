"""Renaming a sub-entity kind's ``plural`` against an existing corpus is reported, in both
directions, and the heading follows the declaration.

``subentity_kinds.<kind>.plural`` is the persisted container-marker name, which makes it a
corpus-alignment field exactly like a type's ``prefix`` or ``folder``. Unlike those two it
leaves no witness in the index — nothing about a stored item says which plural its file was
written under — so the loader's live-index cross-check cannot see it and ``sq workflow lint``,
which never opens an item file, has no way to. ``sq check`` does hold each item's on-disk text,
and it said nothing.

What that cost is worse than a plain break: the corpus is left *half* usable. ``add-<kind>``
fails looking for a container the files do not carry, while sub-entity body writes keep working
because those address their own per-block markers — so the squad looks fine right up until
someone adds a story. Both directions are driven, because the plural can move either way:
declared over an existing corpus, and un-declared afterwards.
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


async def test_declaring_a_new_plural_over_an_existing_corpus_is_reported(
    project, svc, invoke
) -> None:
    feature = (await svc.create("feature", "Existing", author="manager")).item
    _write_override(project.squad_dir, _RENAME_STORY_PLURAL)

    result = await invoke(["check"])

    assert result.exit_code == 3
    assert feature.id in result.output
    flat = result.output.replace("\n", " ")
    assert "outcomes" in flat
    assert "stories" in flat  # names what the file actually carries, not only what is missing


async def test_removing_the_declaration_afterwards_is_reported_too(project, svc, invoke) -> None:
    """The direction the finding was driven in: the override is *gone*, so lint has nothing to
    look at and reports clean, and every load takes the no-override fast path. The corpus is
    still written under the old plural."""
    from squads._services import _service as service

    _write_override(project.squad_dir, _RENAME_STORY_PLURAL)
    reopened = service.open_service()  # the fixture's spec predates the override
    feature = (await reopened.create("feature", "Written as outcomes", author="manager")).item
    assert "<!-- sq:outcomes -->" in (project.squad_dir / feature.path).read_text(encoding="utf-8")
    (project.squad_dir / ".overrides" / "workflow.toml").unlink()

    lint = await invoke(["workflow", "lint"])
    assert lint.exit_code == 0  # no override file — nothing for lint to judge

    result = await invoke(["check"])
    assert result.exit_code == 3
    assert feature.id in result.output
    flat = result.output.replace("\n", " ")
    assert "stories" in flat  # the bundled plural is what add-story now looks for
    assert "outcomes" in flat  # …and the file still carries the old one, so both are named


async def test_the_half_broken_state_is_what_makes_it_worth_reporting(project, svc, invoke) -> None:
    """Pins the asymmetry itself, so the report cannot be dismissed as cosmetic: adding fails
    while the item stays otherwise perfectly usable."""
    feature = (await svc.create("feature", "Existing", author="manager")).item
    _write_override(project.squad_dir, _RENAME_STORY_PLURAL)

    add = await invoke(["feature", str(feature.sequence_id), "add-story", "A story"])
    assert add.exit_code != 0

    show = await invoke(["feature", str(feature.sequence_id), "show"])
    assert show.exit_code == 0  # still readable — which is why nothing else notices


async def test_a_fresh_corpus_under_the_declared_plural_is_clean(project, svc, invoke) -> None:
    """The control. The report must be caused by the *mismatch*, not by declaring a plural at
    all — a squad that declared it before creating anything is correct and must stay silent."""
    from squads._services import _service as service

    _write_override(project.squad_dir, _RENAME_STORY_PLURAL)
    reopened = service.open_service()  # the fixture's spec predates the override
    feature = (await reopened.create("feature", "Fresh", author="manager")).item

    add = await invoke(["feature", str(feature.sequence_id), "add-story", "A story"])
    assert add.exit_code == 0, add.output

    result = await invoke(["check"])
    assert "container section" not in result.output


async def test_the_container_heading_follows_the_declared_plural(project, svc) -> None:
    """The related half: the heading is rendered from the same declaration as the marker, so a
    renamed kind can never get the bundled wording over a differently-named container."""
    _write_override(project.squad_dir, _RENAME_STORY_PLURAL)
    from squads._services import _service as service

    reopened = service.open_service()
    feature = (await reopened.create("feature", "Fresh", author="manager")).item
    text = (project.squad_dir / feature.path).read_text(encoding="utf-8")

    assert "<!-- sq:outcomes -->" in text
    assert "## Outcomes" in text
    assert "User Stories" not in text
