"""A role override's resolved ``full_name``/``mission`` reaches the item's own top-level
``title``/``description`` — not only their ``extra`` mirror — via the projection table
declared on ``RoleDef`` (``title`` from ``full_name``, ``description`` from ``mission``) and
looped by ``_refresh_catalog_extra``.

Every assertion here checks the *declared string* itself, never agreement between the
top-level field and its ``extra`` copy — a projection that writes the stale bundled value into
both would pass an agreement-only check and prove nothing.
"""

from pathlib import Path

import pytest

from squads import __version__
from squads import _itemfile as itemfile
from squads._errors import SquadsError
from squads._models._extras import ExtraKey as X
from squads._roles._catalog import PREDEFINED
from squads._services import _maintenance as maintenance
from squads._workflow import ROSTER_ROLE

pytestmark = pytest.mark.anyio

_BUNDLED_ARCHITECT = next(r for r in PREDEFINED if r.slug == "architect")


def _place_override(squad_dir: Path, slug: str, content: str) -> None:
    """Write a stamped ``.overrides/roles/<slug>.toml`` — the stamp matters here because
    ``sq check`` warns on an unstamped override, and several tests below assert a clean
    ``sq check`` around the sync that applies the projection."""
    target = squad_dir / ".overrides" / "roles" / f"{slug}.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"# squads:override-base:{__version__}\n{content}", encoding="utf-8")


def _on_disk_frontmatter(svc, item) -> dict[str, object]:
    from squads._index._resolver import item_file

    return itemfile.read_frontmatter(text=item_file(svc.paths, item).read_text(encoding="utf-8"))


def _claude_md(project) -> str:
    return (project.root / "CLAUDE.md").read_text(encoding="utf-8")


def _pointer_text(project, slug: str) -> str:
    return (project.root / ".claude" / "agents" / f"{slug}.md").read_text(encoding="utf-8")


async def _list_title(svc, item_id: str) -> str:
    items = await svc.list_items(item_type=ROSTER_ROLE)
    return next(it.title for it in items if it.id == item_id)


# --------------------------------------------------------------------------------------------
# Pair 1: full_name -> title, bundled role.
# --------------------------------------------------------------------------------------------


async def test_bundled_role_declared_full_name_reaches_title_on_every_surface(project, svc):
    role = await svc.activate_role("architect")
    _place_override(project.squad_dir, "architect", 'full_name = "Ada Lovelace"\n')

    skipped = await svc.sync()
    assert not skipped

    on_disk = _on_disk_frontmatter(svc, role)
    assert on_disk["title"] == "Ada Lovelace"  # declared string, not "agrees with extra"

    reloaded = await svc.get(role.id)
    assert reloaded.title == "Ada Lovelace"
    assert await _list_title(svc, role.id) == "Ada Lovelace"  # `sq list -t role`
    assert "Ada Lovelace" in _claude_md(project)  # compiled roster line


async def test_dev_role_declared_full_name_reaches_title_on_every_surface(project, svc):
    dev = await svc.add_dev("python")
    _place_override(project.squad_dir, "python-dev", 'full_name = "Grace Hopper"\n')

    skipped = await svc.sync()
    assert not skipped

    on_disk = _on_disk_frontmatter(svc, dev)
    assert on_disk["title"] == "Grace Hopper"

    reloaded = await svc.get(dev.id)
    assert reloaded.title == "Grace Hopper"
    assert await _list_title(svc, dev.id) == "Grace Hopper"
    assert "Grace Hopper" in _claude_md(project)


# --------------------------------------------------------------------------------------------
# Pair 2: mission -> description, bundled role. Covers the card AND the `## Mission` body.
# --------------------------------------------------------------------------------------------


async def test_bundled_role_declared_mission_reaches_description_and_the_mission_body(project, svc):
    role = await svc.activate_role("architect")
    _place_override(project.squad_dir, "architect", 'mission = "Secure the whole system."\n')

    skipped = await svc.sync()
    assert not skipped

    on_disk = _on_disk_frontmatter(svc, role)
    assert on_disk["description"] == "Secure the whole system."

    reloaded = await svc.get(role.id)
    assert reloaded.description == "Secure the whole system."

    body = await svc.role_body("architect")
    assert body is not None
    assert "Secure the whole system." in body
    assert _BUNDLED_ARCHITECT.mission not in body  # the stale bundled mission is gone


async def test_dev_role_declared_mission_reaches_description_and_the_mission_body(project, svc):
    dev = await svc.add_dev("python")
    _place_override(project.squad_dir, "python-dev", 'mission = "Own the whole backend."\n')

    skipped = await svc.sync()
    assert not skipped

    reloaded = await svc.get(dev.id)
    assert reloaded.description == "Own the whole backend."

    body = await svc.role_body("python-dev")
    assert body is not None
    assert "Own the whole backend." in body


# --------------------------------------------------------------------------------------------
# The dropped `description` (RoleDef's Claude-pointer one-liner) now reaches the pointer, for
# both role kinds -- landed as a reconciled-but-non-exempt key (see the PERMITTED_EXTRA_SKEW
# tests) rather than a member of `_EXTRA_FIELD_KEYS`.
# --------------------------------------------------------------------------------------------


async def test_bundled_role_declared_description_reaches_the_generated_pointer(project, svc):
    await svc.activate_role("architect")
    _place_override(project.squad_dir, "architect", 'description = "Draws the system diagrams."\n')

    skipped = await svc.sync()
    assert not skipped

    assert "Draws the system diagrams." in _pointer_text(project, "architect")


async def test_dev_role_declared_description_reaches_the_generated_pointer(project, svc):
    await svc.add_dev("python")
    _place_override(project.squad_dir, "python-dev", 'description = "Ships the Python stack."\n')

    skipped = await svc.sync()
    assert not skipped

    assert "Ships the Python stack." in _pointer_text(project, "python-dev")


# --------------------------------------------------------------------------------------------
# The `if not previous` gate: no declaration -> byte-identical fields; a value equal to the
# current one -> the same no-op path (asserted directly, not assumed).
# --------------------------------------------------------------------------------------------


async def test_an_override_declaring_neither_field_leaves_title_and_description_untouched(
    project, svc
):
    role = await svc.activate_role("architect")
    before = await svc.get(role.id)
    _place_override(project.squad_dir, "architect", 'model = "opus"\n')

    skipped = await svc.sync()
    assert not skipped

    after = await svc.get(role.id)
    assert after.title == before.title
    assert after.description == before.description


async def test_a_declared_full_name_equal_to_the_current_value_takes_the_no_op_path(
    project, svc, monkeypatch
):
    role = await svc.activate_role("architect")
    current_title = role.title
    _place_override(project.squad_dir, "architect", f'full_name = "{current_title}"\n')

    calls: list[str] = []
    real = maintenance.update_frontmatter

    async def _spy(path, item, base, *, default_kind):
        calls.append(item.id)
        return await real(path, item, base, default_kind=default_kind)

    monkeypatch.setattr(maintenance, "update_frontmatter", _spy)

    skipped = await svc.sync()
    assert not skipped
    assert role.id not in calls  # no write at all -- the true no-op path, not a same-value write


# --------------------------------------------------------------------------------------------
# The data-loss hazard: the projection must never route through the title-rename path, so the
# item's own path (its role-slug filename) is unchanged across a full_name rename.
# --------------------------------------------------------------------------------------------


async def test_the_items_path_is_unchanged_across_a_full_name_rename(project, svc):
    role = await svc.activate_role("architect")
    original_path = role.path
    assert "architect" in Path(role.path).name  # the role slug, stamped into the filename

    _place_override(project.squad_dir, "architect", 'full_name = "Ada Lovelace"\n')
    await svc.sync()

    reloaded = await svc.get(role.id)
    assert reloaded.path == original_path
    assert (project.squad_dir / original_path).is_file()
    assert reloaded.slug == "architect"  # the role slug, never a slug of the new title


# --------------------------------------------------------------------------------------------
# File shapes: a second developer's title must be untouched by the first's override; an
# override on a retired role still reconciles the item's own record even though its backend
# projection stays withdrawn.
# --------------------------------------------------------------------------------------------


async def test_the_second_developers_override_never_touches_the_first_developers_title(
    project, svc
):
    first = await svc.add_dev("python")
    second = await svc.add_dev("typescript")
    _place_override(project.squad_dir, "typescript-dev", 'full_name = "Zara Typescript"\n')

    await svc.sync()

    reloaded_first = await svc.get(first.id)
    reloaded_second = await svc.get(second.id)
    assert reloaded_first.title == first.title  # untouched
    assert reloaded_second.title == "Zara Typescript"


async def test_an_override_on_a_retired_role_still_reconciles_the_items_own_record(project, svc):
    role = await svc.activate_role("architect")
    await svc.set_status(role.id, "Archived")
    _place_override(project.squad_dir, "architect", 'full_name = "Ada Lovelace"\n')

    skipped = await svc.sync()
    assert not skipped

    reloaded = await svc.get(role.id)
    assert reloaded.title == "Ada Lovelace"
    assert reloaded.status == "Archived"  # the transition itself is untouched by this call
    # withdrawn: no live pointer materialised for a retired role
    assert not (project.root / ".claude" / "agents" / "architect.md").is_file()


# --------------------------------------------------------------------------------------------
# A pre-split corpus -- an item already carrying a stale title/description from before this
# projection existed -- converges on the next sync, no migration and no manual step.
# --------------------------------------------------------------------------------------------


async def test_a_pre_split_corpus_converges_on_the_next_sync(project, svc):
    role = await svc.activate_role("architect")
    _place_override(
        project.squad_dir,
        "architect",
        'full_name = "Ada Lovelace"\nmission = "Secure the whole system."\n',
    )

    # Simulate the split this task fixes: extra already carries the declared values (an older
    # release's writer merged only `to_extra()`), but the item's own top-level fields still
    # hold what `create` stamped at activation.
    from squads._index._resolver import item_file
    from squads._itemfile import update_frontmatter

    current = await svc.get(role.id)
    base = current.model_copy(deep=True)
    stale = current.model_copy(deep=True)
    stale.extra[X.FULL_NAME] = "Ada Lovelace"
    stale.extra[X.MISSION] = "Secure the whole system."
    async with svc.store.transaction() as db:
        await update_frontmatter(
            item_file(svc.paths, stale), stale, base, default_kind=svc.spec.default_ref_kind()
        )
        db.add(stale)

    split = await svc.get(role.id)
    assert split.title == _BUNDLED_ARCHITECT.full_name  # still stale
    assert split.extra[X.FULL_NAME] == "Ada Lovelace"  # already correct

    skipped = await svc.sync()
    assert not skipped

    healed = await svc.get(role.id)
    assert healed.title == "Ada Lovelace"
    assert healed.description == "Secure the whole system."


# --------------------------------------------------------------------------------------------
# Rollback: a simulated write failure must leave BOTH the top-level fields and `extra` truthful
# to disk -- the property the `extra`-shaped rollback already held, now extended to `title`/
# `description`. Observed downstream, in the same sync pass, through the generated pointer and
# role body -- proving the in-memory item used by later steps was actually rolled back, not
# just theoretically restorable.
# --------------------------------------------------------------------------------------------


async def test_a_simulated_write_failure_leaves_the_item_truthful_to_disk_on_title_too(
    project, svc, monkeypatch
):
    role = await svc.activate_role("architect")
    original_title = role.title
    original_description = role.description
    _place_override(project.squad_dir, "architect", 'full_name = "Ada Lovelace"\n')

    real = maintenance.update_frontmatter

    async def _boom(path, item, base, *, default_kind):
        if item.id == role.id:
            raise SquadsError("simulated write failure")
        return await real(path, item, base, default_kind=default_kind)

    monkeypatch.setattr(maintenance, "update_frontmatter", _boom)

    skipped = await svc.sync()
    assert skipped == ["simulated write failure"]

    # Nothing committed: disk and index both still hold the original title.
    on_disk = _on_disk_frontmatter(svc, role)
    assert on_disk["title"] == original_title
    reloaded = await svc.get(role.id)
    assert reloaded.title == original_title
    assert reloaded.description == original_description

    # The downstream regen in the SAME sync pass used the rolled-back value, not the attempted
    # one -- proving the in-memory item the loop kept using was actually restored.
    assert "Ada Lovelace" not in _pointer_text(project, "architect")
    body = await svc.role_body("architect")
    assert body is not None


async def test_a_raised_write_rolls_back_in_memory_and_a_retry_from_a_clean_state_succeeds(
    project, svc, monkeypatch
):
    """Renamed from ``test_repair_and_a_further_sync_are_unaffected_by_the_interrupted_role_
    write``: that name promised the markdown-written / index-commit-not-reached shape, but
    patching the whole ``update_frontmatter`` function means its own last statement — the
    ``_aio.atomic_write_text`` call — is never reached, so nothing lands on either side. What
    this actually falsifies, and still must: a write that raises leaves ``item`` rolled back
    in memory to what disk still holds (not the attempted value), so a clean retry from that
    same, untouched state simply succeeds. The shape the old name promised — markdown ahead,
    index commit not reached, then ``svc.repair()`` and a further sync — gets its own test
    below, ``test_an_interrupted_index_commit_is_healed_by_repair_then_a_further_sync_is_
    silent``.
    """
    role = await svc.activate_role("architect")
    _place_override(project.squad_dir, "architect", 'full_name = "Ada Lovelace"\n')

    real = maintenance.update_frontmatter
    call_count = 0

    async def _boom_once(path, item, base, *, default_kind):
        nonlocal call_count
        if item.id == role.id and call_count == 0:
            call_count += 1
            raise SquadsError("simulated write failure")
        return await real(path, item, base, default_kind=default_kind)

    monkeypatch.setattr(maintenance, "update_frontmatter", _boom_once)
    first_sync = await svc.sync()
    assert first_sync == ["simulated write failure"]

    second_sync = await svc.sync()
    assert not second_sync
    healed = await svc.get(role.id)
    assert healed.title == "Ada Lovelace"


async def test_an_interrupted_index_commit_is_healed_by_repair_then_a_further_sync_is_silent(
    project, svc
):
    """The shape a real interrupted role-projection write actually takes: the ``.md`` file is
    ahead of the index (an interrupted write that landed on disk but whose index commit never
    happened — the sanctioned one-sided skew invariant 8 describes), not "nothing written on
    either side".

    Simulated directly — roll the index back on the role's own projected
    ``title``/``description`` (and their ``extra`` mirrors) to what it held before the
    override applied, leaving the ``.md`` file exactly as the earlier, real sync left it.
    """
    role = await svc.activate_role("architect")
    original_title = role.title
    original_description = role.description
    original_full_name = role.extra[X.FULL_NAME]
    original_mission = role.extra[X.MISSION]
    _place_override(
        project.squad_dir,
        "architect",
        'full_name = "Ada Lovelace"\nmission = "Secure the whole system."\n',
    )
    first_sync = await svc.sync()
    assert not first_sync
    applied = await svc.get(role.id)
    assert applied.title == "Ada Lovelace"

    # Roll the index back to the pre-override state -- INDEX ONLY, the `.md` file is
    # untouched (still "Ada Lovelace" / "Secure the whole system.").
    async with svc.store.transaction() as db:
        stale = db.get(role.id)
        assert stale is not None
        stale.title = original_title
        stale.description = original_description
        stale.extra[X.FULL_NAME] = original_full_name
        stale.extra[X.MISSION] = original_mission
        db.add(stale)

    on_disk_before = _on_disk_frontmatter(svc, role)
    assert on_disk_before["title"] == "Ada Lovelace"  # disk still ahead
    reloaded_before = await svc.get(role.id)
    assert reloaded_before.title == original_title  # index rolled back

    # Deliverable 1 evidence: one divergence on one item, one warning -- counted, not
    # substring-matched, so a silent regression to "two lines again" would redden this.
    second_sync = await svc.sync()
    matching = [msg for msg in second_sync if role.id in msg]
    assert len(matching) == 1, second_sync
    assert "title" in matching[0] and "description" in matching[0]
    assert "sq repair" in matching[0]

    # Nothing was overwritten by the refused attempt -- both sides exactly as before this sync.
    still_on_disk = _on_disk_frontmatter(svc, role)
    assert still_on_disk["title"] == "Ada Lovelace"
    still_index = await svc.get(role.id)
    assert still_index.title == original_title

    await svc.repair()
    healed = await svc.get(role.id)
    assert healed.title == "Ada Lovelace"
    assert healed.description == "Secure the whole system."

    third_sync = await svc.sync()
    assert not third_sync  # converged, and stays silent


async def test_a_second_genuinely_different_message_about_the_same_item_still_gets_through(
    project, svc
):
    """The dedup collapses only exact-text duplicates -- a second, textually different report
    about the *same* item (here: an unrenderable ``model`` the backend drops, reported on
    every sync by :meth:`_project_roster_item` regardless of any skew, alongside a real
    frontmatter skew caught by :meth:`_refresh_role_skills_extra`, both on one dev role in one
    sync) must not be swallowed alongside it.

    No role override is involved deliberately: an override on a role whose stored ``model``
    is already outside the whitelist is refused by ``_apply_override``'s own model check
    before it ever reaches this projection (a separate, pre-existing interaction, out of
    scope here) -- so the skew is manufactured directly on disk instead, bypassing the index,
    exactly the shape :meth:`_refresh_role_skills_extra` still catches on its own (it writes
    unconditionally every sync, so it reaches ``ensure_no_skew`` regardless of whether
    anything about the *skills* cache itself changed).
    """
    from squads._index._resolver import item_file
    from squads._itemfile import replace_frontmatter

    unrenderable_model = "claude-opus-4-5"
    dev = await svc.add_dev("python", model=unrenderable_model)

    path = item_file(svc.paths, dev)
    text = path.read_text(encoding="utf-8")
    mutated = dev.model_copy(deep=True)
    mutated.title = "A Disk-Only Title Nobody Told The Index About"
    path.write_text(
        replace_frontmatter(text, mutated.to_frontmatter_dict(), source=str(path)),
        encoding="utf-8",
    )

    skipped = await svc.sync()
    skew_lines = [msg for msg in skipped if dev.id in msg and "diverged" in msg]
    model_lines = [msg for msg in skipped if unrenderable_model in msg]
    assert len(skew_lines) == 1, skipped
    assert len(model_lines) == 1, skipped
    assert skew_lines[0] != model_lines[0]

    # And the write really was refused, not silently overwritten -- the disk-only title
    # this test manufactured still stands.
    on_disk = _on_disk_frontmatter(svc, dev)
    assert on_disk["title"] == "A Disk-Only Title Nobody Told The Index About"


# --------------------------------------------------------------------------------------------
# sq check stays clean both before and after the sync that applies the override -- op-pierre's
# ruling: no new check rule for the transient disagreement this projection heals.
# --------------------------------------------------------------------------------------------


async def test_sq_check_is_clean_before_and_after_the_sync_that_applies_a_full_name_override(
    project, svc
):
    role = await svc.activate_role("architect")
    _place_override(project.squad_dir, "architect", 'full_name = "Ada Lovelace"\n')

    before_issues = await svc.check()
    assert not before_issues

    await svc.sync()

    after_issues = await svc.check()
    assert not after_issues

    reloaded = await svc.get(role.id)
    assert reloaded.title == "Ada Lovelace"


async def test_repair_is_a_stable_no_op_after_a_full_name_projection(project, svc):
    role = await svc.activate_role("architect")
    _place_override(project.squad_dir, "architect", 'full_name = "Ada Lovelace"\n')
    await svc.sync()

    result = await svc.repair()
    assert result.missing_ids == []
    assert result.unreadable == []

    reloaded = await svc.get(role.id)
    assert reloaded.title == "Ada Lovelace"
