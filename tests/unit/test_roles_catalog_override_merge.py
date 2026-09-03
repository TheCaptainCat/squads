"""``.overrides/roles.toml`` — the fourth spec override document: a whole-document override for
the role catalog, merged over the bundled ``roles.toml`` via the shared engine at
the raw-mapping layer, exactly like the workflow and playbook documents. Covers the shape
adaptation ``[[roles]]`` needs (a plain array re-keyed by ``slug`` so the engine can field-merge
and deselect it), the closed top-level key space, and the ``[selected]`` deselect running
through the existing floor (bundle referential integrity, at-most-one-default) with no
deselect-specific guard of its own.

Precedence against a per-slug ``.overrides/roles/<slug>.toml`` file lives in
``test_role_catalog_document_precedence.py`` — this file is the loader in isolation.
"""

from pathlib import Path

import pytest

from squads._errors import SquadsError
from squads._roles._loader import load_role_catalog


def _write_roles_override(squad_dir: Path, content: str) -> Path:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    dest = override_dir / "roles.toml"
    dest.write_text(content, encoding="utf-8")
    return dest


def _bundled_slugs() -> set[str]:
    return {r.slug for r in load_role_catalog().roles}


# --------------------------------------------------------------------------- no override: byte
# identity against the bundled catalog


def test_no_override_file_returns_a_catalog_identical_to_the_bundled_one(tmp_path: Path) -> None:
    bundled = load_role_catalog()
    merged = load_role_catalog(tmp_path)
    assert merged.model_dump(mode="json") == bundled.model_dump(mode="json")


def test_no_override_file_is_identical_even_when_squad_dir_exists_but_empty(
    tmp_path: Path,
) -> None:
    (tmp_path / ".overrides").mkdir()
    bundled = load_role_catalog()
    merged = load_role_catalog(tmp_path)
    assert merged.model_dump(mode="json") == bundled.model_dump(mode="json")


# --------------------------------------------------------------------------- [dev] and [bundles]
# merge field-wise, no reshaping needed — both are already dict-shaped in raw TOML


def test_dev_pool_field_merges_over_the_bundled_default_leaving_siblings_untouched(
    tmp_path: Path,
) -> None:
    _write_roles_override(tmp_path, '[dev]\nmodel = "opus"\n')
    catalog = load_role_catalog(tmp_path)
    bundled = load_role_catalog()
    assert catalog.dev.model == "opus"
    assert catalog.dev.color == bundled.dev.color
    assert catalog.dev.name_pool == bundled.dev.name_pool


def test_a_new_bundle_name_is_added_leaving_bundled_bundles_untouched(tmp_path: Path) -> None:
    _write_roles_override(tmp_path, '[bundles]\ncustom = ["manager", "architect"]\n')
    catalog = load_role_catalog(tmp_path)
    bundled = load_role_catalog()
    assert catalog.bundles["custom"] == ["manager", "architect"]
    assert catalog.bundles["core"] == bundled.bundles["core"]
    assert catalog.bundles["all"] == bundled.bundles["all"]


def test_redeclaring_a_bundled_bundle_name_replaces_it_wholesale_arrays_are_leaves(
    tmp_path: Path,
) -> None:
    _write_roles_override(tmp_path, '[bundles]\nminimal = ["manager", "architect"]\n')
    catalog = load_role_catalog(tmp_path)
    assert catalog.bundles["minimal"] == ["manager", "architect"]


# --------------------------------------------------------------------------- [[roles]]: the
# shape adaptation — field-merge onto an existing slug, or define a brand-new one


def test_a_roles_entry_naming_a_bundled_slug_field_merges_leaving_siblings_untouched(
    tmp_path: Path,
) -> None:
    _write_roles_override(tmp_path, '[[roles]]\nslug = "architect"\ntitle = "Chief Architect"\n')
    catalog = load_role_catalog(tmp_path)
    bundled = load_role_catalog()
    bundled_architect = next(r for r in bundled.roles if r.slug == "architect")
    merged_architect = next(r for r in catalog.roles if r.slug == "architect")

    assert merged_architect.title == "Chief Architect"
    assert merged_architect.mission == bundled_architect.mission
    assert merged_architect.responsibilities == bundled_architect.responsibilities

    # every other bundled role is untouched, same count, same order
    assert [r.slug for r in catalog.roles] == [r.slug for r in bundled.roles]
    for slug in _bundled_slugs() - {"architect"}:
        assert next(r for r in catalog.roles if r.slug == slug) == next(
            r for r in bundled.roles if r.slug == slug
        )


def test_a_roles_entry_naming_a_new_slug_adds_a_wholly_new_role(tmp_path: Path) -> None:
    # The 'all' bundle must equal the full slug set (_check_bundles's own floor), so a new
    # role is also added to 'all' here — the same thing a project would have to do by hand.
    all_with_new = [*load_role_catalog().bundles["all"], "security-analyst"]
    _write_roles_override(
        tmp_path,
        f"""
        [[roles]]
        slug = "security-analyst"
        full_name = "Sam Security"
        title = "security analyst"
        description = "Reviews the project for security issues."
        mission = "Find and report security issues before they ship."

        [bundles]
        all = {all_with_new!r}
        """,
    )
    catalog = load_role_catalog(tmp_path)
    assert "security-analyst" in {r.slug for r in catalog.roles}
    new_role = next(r for r in catalog.roles if r.slug == "security-analyst")
    assert new_role.full_name == "Sam Security"
    # bundled roles are all still present
    assert _bundled_slugs() <= {r.slug for r in catalog.roles}


def test_a_new_slug_missing_a_required_field_is_refused(tmp_path: Path) -> None:
    _write_roles_override(
        tmp_path, '[[roles]]\nslug = "incomplete-role"\nfull_name = "Iggy Incomplete"\n'
    )
    with pytest.raises(SquadsError):
        load_role_catalog(tmp_path)


def test_a_roles_entry_missing_slug_is_refused_naming_the_index(tmp_path: Path) -> None:
    _write_roles_override(tmp_path, '[[roles]]\ntitle = "no slug here"\n')
    with pytest.raises(SquadsError, match="slug"):
        load_role_catalog(tmp_path)


def test_the_same_slug_declared_twice_in_one_document_is_refused(tmp_path: Path) -> None:
    _write_roles_override(
        tmp_path,
        """
        [[roles]]
        slug = "architect"
        title = "First"

        [[roles]]
        slug = "architect"
        title = "Second"
        """,
    )
    with pytest.raises(SquadsError, match="architect"):
        load_role_catalog(tmp_path)


# --------------------------------------------------------------------------- closed top level


def test_an_unknown_top_level_key_is_refused_naming_it(tmp_path: Path) -> None:
    _write_roles_override(tmp_path, 'nonsense_key = "whatever"\n')
    with pytest.raises(SquadsError, match="nonsense_key"):
        load_role_catalog(tmp_path)


# --------------------------------------------------------------------------- [selected] deselect
# — no deselect-specific guard; the existing floor does the work


def test_selected_roles_drops_a_bundled_role_from_the_catalog(tmp_path: Path) -> None:
    # 'tech-writer' is only a member of the 'all' bundle (not core/minimal), so dropping it
    # cleanly also means dropping it from 'all' — the referential floor requires 'all' to
    # equal the surviving slug set exactly.
    all_without_tech_writer = [s for s in load_role_catalog().bundles["all"] if s != "tech-writer"]
    _write_roles_override(
        tmp_path,
        f"""
        [selected]
        roles = ["manager", "architect", "tech-lead", "reviewer", "qa", "devops", "product-owner"]

        [bundles]
        all = {all_without_tech_writer!r}
        """,
    )
    catalog = load_role_catalog(tmp_path)
    assert "tech-writer" not in {r.slug for r in catalog.roles}
    assert "tech-writer" not in catalog.bundles["all"]


def test_selected_bundles_drops_a_bundled_bundle_entry(tmp_path: Path) -> None:
    _write_roles_override(tmp_path, '[selected]\nbundles = ["all", "core"]\n')
    catalog = load_role_catalog(tmp_path)
    assert "minimal" not in catalog.bundles
    assert "all" in catalog.bundles
    assert "core" in catalog.bundles


def test_a_deselect_that_empties_a_bundle_fails_through_the_existing_referential_floor(
    tmp_path: Path,
) -> None:
    """Dropping 'reviewer' from roles without also dropping it from the bundles that name it
    (all, core) fails through `_check_bundles`'s existing referential-integrity check — no
    deselect-specific guard was written for this."""
    _write_roles_override(
        tmp_path,
        """
        [selected]
        roles = [
            "manager", "architect", "tech-lead", "qa", "devops", "product-owner", "tech-writer",
        ]
        """,
    )
    with pytest.raises(SquadsError, match="reviewer"):
        load_role_catalog(tmp_path)


def test_a_deselect_that_removes_the_default_agent_fails_through_the_existing_referential_floor(
    tmp_path: Path,
) -> None:
    """'manager' (is_default) is a member of every bundled bundle, so dropping it via
    [selected].roles without touching [selected].bundles fails the same referential floor —
    again with no deselect-specific guard."""
    _write_roles_override(
        tmp_path,
        """
        [selected]
        roles = [
            "architect", "tech-lead", "reviewer", "qa", "devops", "product-owner", "tech-writer",
        ]
        """,
    )
    with pytest.raises(SquadsError, match="manager"):
        load_role_catalog(tmp_path)


def test_malformed_toml_raises(tmp_path: Path) -> None:
    _write_roles_override(tmp_path, "this is not [ valid toml")
    with pytest.raises(SquadsError):
        load_role_catalog(tmp_path)


# --------------------------------------------------------------------------- validation-failure
# origin: a refusal must name the document actually at fault, never assert a cause the reader
# can open the other document and disprove


def test_a_selected_deselect_left_dangling_in_a_bundle_names_the_override_file_with_a_hint(
    tmp_path: Path,
) -> None:
    """`[selected].roles` dropping a slug without also updating the bundles that still name
    it is refused — but the refusal must name `.overrides/roles.toml` (the document an
    adopter actually wrote), never the bundled catalog they can open and see is fine, and
    must hint that the mechanism is `[selected]`."""
    override_path = _write_roles_override(
        tmp_path,
        """
        [selected]
        roles = ["manager", "architect", "tech-lead", "reviewer", "qa", "devops", "product-owner"]
        """,
    )
    with pytest.raises(SquadsError) as exc_info:
        load_role_catalog(tmp_path)
    message = str(exc_info.value)
    assert message.startswith(f"{override_path}: role catalog invalid after merge:")
    assert "Invalid bundled role catalog" not in message
    assert "tech-writer" in message
    assert "[selected].roles" in message


def test_a_genuinely_invalid_bundled_catalog_still_says_bundled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The inverse leg: when the bundled document itself is broken (no project override in
    play at all), the refusal must still say so — carrying the origin must never trade one
    wrong document name for the other."""
    from squads._roles import _loader

    bad_raw = {
        "roles": [],
        "bundles": {"all": ["ghost"]},
        "dev": {"name_pool": ["A"], "model": "sonnet", "color": "blue"},
    }
    monkeypatch.setattr(_loader, "_bundled_raw", lambda: bad_raw)
    with pytest.raises(SquadsError, match=r"^Invalid bundled role catalog:") as exc_info:
        load_role_catalog()
    assert "ghost" in str(exc_info.value)


def test_a_genuinely_invalid_bundled_catalog_still_says_bundled_even_with_squad_dir_given(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same inverse leg, with a *squad_dir* given but no override file present — the
    bundled-only path, which must still name the bundled catalog."""
    from squads._roles import _loader

    bad_raw = {
        "roles": [],
        "bundles": {"all": ["ghost"]},
        "dev": {"name_pool": ["A"], "model": "sonnet", "color": "blue"},
    }
    monkeypatch.setattr(_loader, "_bundled_raw", lambda: bad_raw)
    with pytest.raises(SquadsError, match=r"^Invalid bundled role catalog:"):
        load_role_catalog(tmp_path)
