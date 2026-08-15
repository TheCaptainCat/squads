"""A project role override's title has to reach the *index*, because that is what every
generated roster is compiled from.

``sq sync`` merges the resolved role definition (bundled catalog + the project's
``.overrides/roles/<slug>.toml``) into the role item. The merge wrote the ``.md`` frontmatter
and stopped there, leaving ``.squads.json`` on the pre-override value — and ``roster()``, which
both backends compile ``CLAUDE.md`` and ``AGENTS.md`` from, reads the index. So the adopter's
renamed title was durable and simultaneously invisible: every generated file kept rendering the
bundled one, `sq check` reported no issues throughout, and only an unrelated `sq repair` (which
rebuilds the index from frontmatter) ever made the two agree — at which point the *next* sync
changed the rendered roster line for no reason the adopter could connect to anything.

That is invariant 1 read backwards: frontmatter stayed the source of truth, but the rebuildable
index was allowed to disagree with it indefinitely while everything downstream read the index.
"""

import json
from typing import Any

import pytest

from squads._services import _service as service

pytestmark = pytest.mark.anyio

_OVERRIDDEN_TITLE = "Chief Code Inspector"


def _write_role_override(squad_dir, slug: str, body: str) -> None:
    """Write a role override where the resolver actually looks — under the *squad* dir, not
    the cwd. An override written anywhere else is simply not found, and the resolver falls
    through to the bundled catalog with no error, which would make this test pass vacuously.
    """
    path = squad_dir / ".overrides" / "roles" / f"{slug}.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    assert path.is_file()


def _index_role_extra(paths, slug: str) -> dict[str, Any]:
    raw = json.loads(paths.index_path.read_text(encoding="utf-8"))
    for entry in raw["items"].values():
        extra = entry.get("extra", {})
        if extra.get("slug") == slug:
            return extra
    raise AssertionError(f"no role item for {slug!r} in the index")


async def test_an_overridden_title_reaches_the_index_the_frontmatter_and_both_backends(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    result = await service.init(
        root=tmp_path, backend=["claude_code", "agents_md"], roles_spec="all"
    )
    paths = result.paths
    svc = service.Service(paths)

    role = await svc.roster_item("role", "reviewer")
    assert role is not None
    bundled_title = role.extra["title"]
    assert bundled_title != _OVERRIDDEN_TITLE

    _write_role_override(paths.squad_dir, "reviewer", f'title = "{_OVERRIDDEN_TITLE}"\n')

    # A service opened after the override exists resolves it; sync is the merge point.
    synced = service.Service(paths)
    assert await synced.sync() == []

    on_disk = (paths.abspath(role.path)).read_text(encoding="utf-8")
    assert f"title: {_OVERRIDDEN_TITLE}" in on_disk
    # The index agrees with the file it was built from -- this is the half that used to lag.
    assert _index_role_extra(paths, "reviewer")["title"] == _OVERRIDDEN_TITLE
    # ... which is why the compiled rosters carry it, on this sync rather than a later one.
    assert _OVERRIDDEN_TITLE in (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert _OVERRIDDEN_TITLE in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")


async def test_a_repair_after_the_sync_changes_nothing_about_the_roster(tmp_path, monkeypatch):
    """The tell that the skew is gone: `sq repair` rebuilds the index from frontmatter, so it
    was what used to "fix" the title — and a sync straight afterwards then changed the
    generated roster. Now repair finds nothing to correct and the next sync is a no-op on the
    rendered files."""
    monkeypatch.chdir(tmp_path)
    result = await service.init(
        root=tmp_path, backend=["claude_code", "agents_md"], roles_spec="all"
    )
    paths = result.paths
    _write_role_override(paths.squad_dir, "reviewer", f'title = "{_OVERRIDDEN_TITLE}"\n')

    svc = service.Service(paths)
    await svc.sync()
    before_claude = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    before_agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    extra_before = _index_role_extra(paths, "reviewer")

    await service.Service(paths).repair()
    assert _index_role_extra(paths, "reviewer")["title"] == extra_before["title"]

    await service.Service(paths).sync()
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == before_claude
    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == before_agents


async def test_a_later_override_edit_propagates_on_the_very_next_sync(tmp_path, monkeypatch):
    """Not a one-shot: editing the override again moves every surface again, in one sync."""
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, backend=["agents_md"], roles_spec="all")
    paths = result.paths
    _write_role_override(paths.squad_dir, "reviewer", f'title = "{_OVERRIDDEN_TITLE}"\n')
    await service.Service(paths).sync()

    _write_role_override(paths.squad_dir, "reviewer", 'title = "Second Reader"\n')
    await service.Service(paths).sync()

    assert _index_role_extra(paths, "reviewer")["title"] == "Second Reader"
    agents_md = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "Second Reader" in agents_md
    assert _OVERRIDDEN_TITLE not in agents_md
