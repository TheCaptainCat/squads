"""A role's pronouns resolve as its own value, else the role catalog document's declared default,
else unset; an operator's are its own value only. The resolved value is never written to an
item, and removing the declaration returns every role without a value of its own to unset. One
table crosses each roster shape with each declaration state and reads the resolved value, the
item's frontmatter and the roster ``--json``."""

import json
from typing import Any

import pytest

from _helpers import catalog_of
from squads import __version__
from squads._errors import SquadsError
from squads._models._attributes import AttributeKey
from squads._overrides._service import check_override_issues, scaffold_roles_catalog
from squads._rendering._engine import invalidate_squad_dir
from squads._roles._loader import bundled_roles_toml_text, load_role_catalog
from squads._sections import split_frontmatter
from squads._services._service import Service

pytestmark = pytest.mark.anyio

_ROLE_FILES = {
    "rustacean": 'full_name = "Rita Rust"\ntitle = "Rust developer"\ndescription = "Writes Rust."\n'
    'mission = "Write Rust."\ncapabilities = ["dev"]\n',
    "chef": 'full_name = "Charlie Chef"\ntitle = "Chef"\ndescription = "Cooks."\n'
    'mission = "Cook."\n',
}

_DEFAULT = '[defaults]\npronouns = "they/them"\n'

# (shape, kind, slug)
SHAPES: list[tuple[str, str, str]] = [
    ("bundled", "role", "architect"),
    ("templated-developer", "role", "python-dev"),
    ("declared-developer", "role", "rustacean"),
    ("project-role", "role", "chef"),
    ("operator", "operator", "op-alex"),
]
# (state, default declared, own value, removed again after a sync)
STATES: list[tuple[str, bool, str | None, bool]] = [
    ("no-default", False, None, False),
    ("default", True, None, False),
    ("default-and-own", True, "she/her", False),
    ("no-default-and-own", False, "she/her", False),
    ("default-removed-after-sync", True, None, True),
]


def _write_catalog(svc: Service, body: str | None) -> None:
    target = svc.paths.squad_dir / ".overrides" / "roles.toml"
    if body is None:
        target.unlink(missing_ok=True)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"# squads:override-base:{__version__}\n{body}", encoding="utf-8")
    invalidate_squad_dir(svc.paths.squad_dir)


def _write_role_files(svc: Service) -> None:
    folder = svc.paths.squad_dir / ".overrides" / "roles"
    folder.mkdir(parents=True, exist_ok=True)
    for slug, body in _ROLE_FILES.items():
        (folder / f"{slug}.toml").write_text(
            f"# squads:override-base:{__version__}\n{body}", encoding="utf-8"
        )
    invalidate_squad_dir(svc.paths.squad_dir)


async def _create(svc: Service, kind: str, slug: str, own: str | None) -> Any:
    if kind == "operator":
        return await svc.add_operator("Alex Rivera", pronouns=own)
    if slug == "python-dev":
        return await svc.add_dev("python", pronouns=own)
    return await svc.activate_role(slug, pronouns=own)


def _frontmatter(svc: Service, item: Any) -> dict[str, Any]:
    return split_frontmatter(svc.paths.abspath(item.path).read_text(encoding="utf-8"))[0]


@pytest.mark.parametrize("state", STATES, ids=[s[0] for s in STATES])
@pytest.mark.parametrize("shape", SHAPES, ids=[s[0] for s in SHAPES])
async def test_the_resolved_value_is_own_else_default_for_a_role_and_own_only_for_an_operator(
    svc: Service,
    invoke: Any,
    shape: tuple[str, str, str],
    state: tuple[str, bool, str | None, bool],
) -> None:
    _name, kind, slug = shape
    _state, declared, own, removed = state
    _write_role_files(svc)
    item = await _create(svc, kind, slug, own)
    before = (svc.paths.abspath(item.path).read_bytes(), _frontmatter(svc, item))
    if declared:
        _write_catalog(svc, _DEFAULT)
        assert (await invoke(["sync"])).exit_code == 0
    if removed:
        _write_catalog(svc, None)
        assert (await invoke(["sync"])).exit_code == 0

    if kind == "operator":
        expected = own
        view = next(o for o in await svc.operators_all() if o.slug == slug)
        listing = json.loads((await invoke(["operator", "list", "--json"])).output)
    else:
        expected = own or ("they/them" if declared and not removed else None)
        view = next(r for r in await svc.roster_all() if r.slug == slug)
        listing = json.loads((await invoke(["role", "list", "--json"])).output)
    row = next(r for r in listing if r["slug"] == slug)

    assert view.pronouns == expected
    assert row["pronouns"] == expected
    assert (AttributeKey.PRONOUNS in _frontmatter(svc, item)) is (own is not None)
    after = (svc.paths.abspath(item.path).read_bytes(), _frontmatter(svc, item))
    assert after[1].get(AttributeKey.PRONOUNS) == before[1].get(AttributeKey.PRONOUNS)
    if not declared and not removed:
        assert after[0] == before[0]


# (id, [defaults] body, fragment the refusal carries)
BAD_DEFAULTS: list[tuple[str, str, str]] = [
    ("forty-one-characters", f'[defaults]\npronouns = "{"a" * 41}"\n', "[defaults]"),
    ("embedded-newline", '[defaults]\npronouns = "a\\nb"\n', "[defaults]"),
    ("blank", '[defaults]\npronouns = "  "\n', "[defaults]"),
    ("integer", "[defaults]\npronouns = 5\n", "[defaults]"),
    ("unknown-key-beside-pronouns", '[defaults]\npronouns = "x"\nmodel = "opus"\n', "[defaults]"),
    ("defaults-is-not-a-table", "defaults = 5\n", "defaults"),
]


@pytest.mark.parametrize(
    ("shape", "body", "fragment"), BAD_DEFAULTS, ids=[b[0] for b in BAD_DEFAULTS]
)
async def test_a_default_that_fails_the_rule_is_refused_at_load_and_reported_by_check(
    svc: Service, shape: str, body: str, fragment: str
) -> None:
    await svc.activate_role("architect")
    _write_catalog(svc, body)

    with pytest.raises(SquadsError, match=fragment.replace("[", r"\[")):
        load_role_catalog(svc.paths.squad_dir)
    issues = await svc.check()

    assert any(i.level == "error" and fragment in i.message for i in issues)


async def test_a_default_with_surrounding_whitespace_resolves_trimmed(svc: Service) -> None:
    await svc.activate_role("architect")
    _write_catalog(svc, '[defaults]\npronouns = "  they/them "\n')

    assert next(r for r in await svc.roster_all() if r.slug == "architect").pronouns == "they/them"


async def test_the_bundled_catalog_declares_no_default_and_an_existing_override_reports_no_drift(
    svc: Service,
) -> None:
    scaffold_roles_catalog(svc.paths.squad_dir)

    assert "[defaults]" not in bundled_roles_toml_text()
    assert load_role_catalog().defaults.pronouns is None
    assert check_override_issues(svc.paths.squad_dir, catalog=catalog_of(svc.paths.squad_dir)) == []
