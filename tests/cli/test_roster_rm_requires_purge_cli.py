"""`rm` on a role, skill or operator refuses without `--purge`, names the command to run and
touches nothing; with `--purge` it deletes the file, the pointer and the roster line."""

import hashlib
from pathlib import Path

import pytest

from squads._models._item import DISPLAY_ID_PADDING, format_item_id
from squads._models._vocab import prefix_for

pytestmark = pytest.mark.anyio

# kind -> (item type, slug of the entry created by _make)
_ENTRIES = {
    "role": ("role", "qa"),
    "dev role": ("role", "python-dev"),
    "skill": ("skill", "temp-skill"),
    "operator": ("operator", "op-temp"),
}


async def _make(invoke, kind: str) -> None:
    if kind == "role":
        await invoke(["role", "activate", "qa"])
    elif kind == "dev role":
        await invoke(["dev", "add", "--tech", "python"])
    elif kind == "skill":
        await invoke(["skill", "add", "temp-skill"])
    else:
        await invoke(["operator", "add", "Temp User", "--slug", "op-temp"])


async def _by_slug(svc, slug: str):
    db = await svc.store.load()
    return next(i for i in db.items.values() if slug in (i.slug, i.slug))


def _snapshot(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and ".git" not in p.relative_to(root).parts
    }


@pytest.mark.parametrize("kind", list(_ENTRIES))
@pytest.mark.parametrize("purge", [False, True])
async def test_roster_rm_refuses_without_purge_and_deletes_with_it(
    project, svc, invoke, kind, purge
):
    item_type, slug = _ENTRIES[kind]
    await _make(invoke, kind)
    item = await _by_slug(svc, slug)
    assert item.type == item_type
    item_id = format_item_id(prefix_for(item_type, svc.spec), item.sequence_id, DISPLAY_ID_PADDING)
    assert item.id == item_id
    path = project.abspath(item.path)
    assert path.exists()
    before = _snapshot(project.root)
    pointers = [
        p for p in (project.root / ".claude").rglob("*") if slug in p.parts or p.stem == slug
    ]
    pointers = [p for p in pointers if p.is_file()]
    if item_type != "operator":
        assert pointers

    args = [item_type, item_id, "rm"] + (["--purge"] if purge else [])
    result = await invoke(args)

    if purge:
        assert result.exit_code == 0, result.output
        assert not path.exists()
        assert not any(p.exists() for p in pointers)
        claude_md = (project.root / "CLAUDE.md").read_text()
        assert f"`{slug}`" not in claude_md and f"({slug})" not in claude_md
    else:
        assert result.exit_code == 1, result.output
        flat = " ".join(result.output.split())
        assert f"sq {item_type} {item_id} remove --purge" in flat
        assert f"sq {item_type} {item_id} status Archived" in flat
        assert _snapshot(project.root) == before
    check = await invoke(["check"])
    assert check.exit_code == 0, check.output


async def test_refusal_omits_the_archive_route_when_it_would_not_apply(project, svc, invoke):
    await invoke(["role", "activate", "qa"])
    assert (await invoke(["role", "qa", "status", "Archived"])).exit_code == 0

    archived = await invoke(["role", "qa", "rm"])
    assert archived.exit_code == 1
    assert "status" not in archived.output and "remove --purge" in archived.output
