"""The crash this review round found: two of the three consumers gated the dev-role merge base
on the slug's ``-dev`` suffix alone, then read ``item.extra[X.TECH]`` with a bare subscript. An
activated role whose slug happens to end in ``-dev`` but is not a developer (e.g. a wholly
custom ``data-dev`` role) has no ``tech`` key, so that subscript raised an unhandled
``KeyError`` instead of resolving through the ordinary path every other role gets.

The rule (already correct in ``sq sync``'s own gate, ``_refresh_catalog_extra``) is a stored
fact first — ``extra.is_dev`` — and the ``-dev`` naming convention only when there is no item to
ask. This file proves the two consumers that diverged from it now follow the same order, across
the shape space: a non-dev ``-dev``-suffixed slug activated, the same unactivated, a genuine dev
role, and the two boundary slugs (``-dev`` exactly, and ``dev`` with no hyphen at all) that
exercise ``is_dev_slug``'s own edge.

CLI-level, driven-through-`sq` confirmation for the realistic shapes (an activated non-dev
``-dev`` role, a genuine dev role) lives in tests/integration/test_show_and_check_do_not_crash_
on_a_dev_suffixed_non_dev_slug.py. ``-dev``/``dev`` are exercised here only, at the pure-function
level: neither is a valid CLI positional token (click treats a leading ``-`` as an option), so
the CLI can never actually reach them with today's argument grammar — but the resolver functions
themselves must not crash if some other caller reaches them.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from squads import __version__
from squads._cli._role import _dev_preview_full_name, _role_base_for_show
from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._overrides._service import check_override_issues
from squads._roles._catalog import dev_role
from squads._roles._resolver import dev_base_for_slug, dev_base_from_item

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _item(slug: str, *, is_dev: bool, extra: dict[str, Any] | None = None) -> Item:
    extra = dict(extra or {})
    extra.setdefault(X.SLUG, slug)
    extra.setdefault(X.FULL_NAME, "Whoever Slug")
    if is_dev:
        extra[X.IS_DEV] = True
    return Item(
        sequence_id=1,
        type="role",
        title="Whoever Slug",
        slug=slug,
        status="Active",
        path=f"roles/ROLE-000001-{slug}.md",
        created_at=_NOW,
        updated_at=_NOW,
        extra=extra,
    )


def _place_role_toml(squad_dir: Path, slug: str, content: str) -> None:
    target = squad_dir / ".overrides" / "roles" / f"{slug}.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


# --------------------------------------------------------------------- shape 1: activated, non-dev


def test_an_activated_non_dev_role_whose_slug_ends_in_dev_gets_no_dev_base() -> None:
    """The exact crash shape: an item exists, ``extra.is_dev`` is absent (no ``extra.tech``
    either), and the slug ends in ``-dev``. Must resolve to ``None`` -- not attempt
    ``dev_base_from_item`` and KeyError on the missing ``tech`` key."""
    item = _item("data-dev", is_dev=False)
    assert X.TECH not in item.extra  # the fact that made the old gate crash
    assert _role_base_for_show("data-dev", item) is None


def test_check_override_issues_gives_the_same_role_no_dev_base(tmp_path: Path) -> None:
    """The other consumer that crashed: ``_check_role_override_resolves`` (via
    ``check_override_issues``), reached with the same shape through its own ``role_items_by_
    slug`` argument rather than ``_role_base_for_show``."""
    item = _item("data-dev", is_dev=False)
    _place_role_toml(
        tmp_path,
        "data-dev",
        f"# squads:override-base:{__version__}\n"
        'full_name = "Dana Analyst"\ntitle = "data steward"\n'
        'description = "Curates the datasets."\nmission = "Keep the catalog accurate."\n',
    )
    issues = check_override_issues(tmp_path, {"data-dev": item})
    assert issues == []  # loads cleanly through the ordinary (non-dev) path -- no crash, no report


# ----------------------------------------------------------------- shape 2: unactivated, non-dev


def test_an_unactivated_non_dev_slug_ending_in_dev_still_falls_back_to_the_dev_preview() -> None:
    """No item at all -- there is no stored fact to read, so the naming convention is the only
    signal available. Not itself a new failure mode: the merge
    still succeeds because the override supplies every field it needs (see the file-shape
    space more broadly at tests/integration/test_a_dev_shaped_slug_with_no_roster_entry_still_
    resolves.py)."""
    assert _role_base_for_show("data-dev", None) == dev_base_for_slug("data-dev")


# --------------------------------------------------------------------- shape 3: genuine dev role


def test_a_genuine_dev_role_still_gets_dev_base_from_item() -> None:
    role = dev_role("python", name="Elias Python", model="opus")
    item = _item(
        "python-dev",
        is_dev=True,
        extra={**role.to_extra(is_dev=True), X.TECH: "python"},
    )
    assert _role_base_for_show("python-dev", item) == dev_base_from_item(item)


# --------------------------------------------------------------------- shape 4/5: is_dev_slug edges


def test_a_slug_that_is_exactly_the_dev_suffix_does_not_crash() -> None:
    """``"-dev"`` (an empty tech) still matches the naming convention -- ``is_dev_slug`` is a
    bare ``str.endswith`` check -- so it must resolve to *some* base, not raise. The empty-tech
    slug it derives (``slugify("")`` falls back to ``"untitled"``) is its own pre-existing
    corner case, not this fix's contract; the fix's contract is only "does not crash"."""
    base = _role_base_for_show("-dev", None)
    assert base is not None
    assert base.full_name  # a name was produced, whatever it is -- no crash reaching it


def test_a_slug_that_is_dev_with_no_hyphen_is_not_dev_shaped_at_all() -> None:
    """``"dev"`` has no hyphen, so it does not end with ``"-dev"`` -- it must fall through to
    the ordinary (``None``) base exactly like any unrelated slug, whether or not an item
    exists."""
    assert _role_base_for_show("dev", None) is None
    assert _role_base_for_show("dev", _item("dev", is_dev=False)) is None


# --------------------------------------------------------------------- the full-name preview guard


def test_preview_full_name_is_blanked_only_for_an_undeclared_fabricated_name() -> None:
    unactivated_base = dev_base_for_slug("rust-dev")
    assert _dev_preview_full_name(unactivated_base, unactivated_base, None) is None


def test_preview_full_name_is_kept_when_the_override_declares_it() -> None:
    unactivated_base = dev_base_for_slug("rust-dev")
    declared = dev_role("rust", name="Priya Rust")
    assert _dev_preview_full_name(declared, unactivated_base, None) == "Priya Rust"


def test_preview_full_name_is_never_blanked_for_an_activated_role() -> None:
    item = _item("data-dev", is_dev=False)
    role = dev_role("data")  # whatever `resolve_role_with_base` would have returned
    assert _dev_preview_full_name(role, None, item) == role.full_name
