"""``sq role <slug> show`` on a ``<tech>-dev.toml`` with no roster entry yet previews against
the generated developer template (the documented, intentional pre-activation preview). That
template's ``full_name`` is a pool pick tied to how many developers exist *at the later point*
``sq dev add`` actually runs -- a fact this preview cannot know -- so printing it as the
developer's name states something ``sq dev add`` can immediately contradict.

The fix: an un-declared preview name is reported as unknown (``None`` in ``--json``, an
"unassigned" marker in the text card) rather than the fabricated pool pick; a name the override
*does* declare is still shown, exactly like any other role's declared ``full_name``.
"""

import json

import pytest

pytestmark = pytest.mark.anyio


def _place_dev_toml(project, slug: str, content: str) -> None:
    target = project.squad_dir / ".overrides" / "roles" / f"{slug}.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


async def test_an_unactivated_preview_does_not_name_a_developer_activation_will_contradict(
    project, svc, invoke
) -> None:
    await svc.add_dev("python")  # seq=0, so the fabricated pool pick below would be pool[1]
    _place_dev_toml(project, "rust-dev", 'title = "Senior Rust developer"\n')

    preview = await invoke(["role", "rust-dev", "show", "--json"])
    added = await svc.add_dev("rust")
    after = await invoke(["role", "rust-dev", "show", "--json"])

    preview_name = json.loads(preview.output)["full_name"]
    assert preview_name is None  # never a concrete, guessable name

    after_name = json.loads(after.output)["full_name"]
    assert after_name == added.extra["full_name"]


async def test_the_text_card_marks_an_unactivated_preview_as_unassigned_not_a_fabricated_name(
    project, svc, invoke
) -> None:
    _place_dev_toml(project, "rust-dev", 'title = "Senior Rust developer"\n')

    result = await invoke(["role", "rust-dev", "show"])

    assert result.exit_code == 0, result.output
    assert "unassigned" in result.output
    assert "sq dev add --tech rust" in result.output


async def test_a_declared_full_name_is_still_shown_before_activation(project, svc, invoke) -> None:
    _place_dev_toml(project, "rust-dev", 'full_name = "Priya Rust"\n')

    result = await invoke(["role", "rust-dev", "show", "--json"])

    assert json.loads(result.output)["full_name"] == "Priya Rust"
