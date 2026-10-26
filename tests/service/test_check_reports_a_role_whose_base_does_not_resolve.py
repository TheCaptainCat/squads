"""``sq check`` reports a live role whose base does not resolve (``role_base_resolves``), a
per-slug file that shadows what a role stores in its item (``role_definition_shadowed``), and a
per-slug file with no role under it (``override_loads``); one rule per condition.

One table per rule: a squad state, and the finding or none, asserting rule, level, item and the
remedy text.
"""

import pytest

from _helpers import add_role_from_toml
from squads import __version__
from squads._itemfile import read_frontmatter
from squads._rendering._engine import invalidate_squad_dir
from squads._sections import replace_frontmatter

pytestmark = pytest.mark.anyio

_ALL = (
    '"manager", "architect", "tech-lead", "reviewer", "qa", "devops", "product-owner", '
    '"tech-writer"'
)
_ITEM = 'full_name = "Sam Sre"\ntitle = "SRE"\ndescription = "Keeps it up."\nmission = "Run it."\n'
_PLAIN_TEMPLATE = (
    '[templates.scribe]\ntitle = "Scribe"\ndescription = "Writes."\nmission = "Write."\n'
    'name = "Wren"\nslug = "scribe"\n'
)


def _write(project, relative: str, body: str) -> None:
    path = project.squad_dir / ".overrides" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    invalidate_squad_dir(project.squad_dir)


async def _edit(svc, item, *, drop=(), **put) -> None:
    """Edit the role's file by hand and rebuild the index from the files."""
    path = svc.paths.abspath(item.path)
    text = path.read_text(encoding="utf-8")
    data = read_frontmatter(text=text, source=str(path))
    for key in drop:
        data.pop(key, None)
    data.update(put)
    path.write_text(replace_frontmatter(text, data, source=str(path)), encoding="utf-8")
    await svc.repair()


async def _findings(svc, rule: str):
    return [i for i in await svc.check() if i.rule == rule]


# ---------------------------------------------------------------------------- role_base_resolves


async def _catalog_entry_gone(project, svc):
    item = await svc.activate_role("devops")
    _write(
        project,
        "roles.toml",
        f"[selected]\nroles = [{_ALL.replace(chr(34) + 'devops' + chr(34) + ', ', '')}]\n\n"
        f"[bundles]\nall = [{_ALL.replace(chr(34) + 'devops' + chr(34) + ', ', '')}]\n",
    )
    return item, "is backed by no catalog entry", "sq role devops update --job-title"


async def _template_undeclared(project, svc):
    item = await svc.activate_role(None, from_template="dev", tech="go")
    _write(project, "roles.toml", f'[selected]\ntemplates = ["scribe"]\n\n{_PLAIN_TEMPLATE}')
    return item, "names the role template 'dev', which the role catalog does not declare", "scribe"


async def _template_missing_tech(project, svc):
    item = await svc.activate_role(None, from_template="dev", tech="go")
    await _edit(svc, item, drop=("tech",))
    return item, "takes a technology, and stores no `tech`", None


async def _template_with_unwanted_tech(project, svc):
    _write(project, "roles.toml", _PLAIN_TEMPLATE)
    item = await svc.activate_role("scribe", from_template="scribe")
    await _edit(svc, item, tech="go")
    return item, "stores `tech`, which template 'scribe' does not take", None


async def _item_without_job_title(project, svc):
    item = await add_role_from_toml(svc, "sre", _ITEM)
    await _edit(svc, item, drop=("job_title",))
    return item, "defines itself but stores no job_title", "sq role sre update --job-title"


async def _item_without_description(project, svc):
    item = await add_role_from_toml(svc, "sre", _ITEM)
    await _edit(svc, item, drop=("description",))
    return item, "defines itself but stores no description", "sq role sre update"


async def _item_with_blank_job_title(project, svc):
    item = await add_role_from_toml(svc, "sre", _ITEM)
    await _edit(svc, item, job_title="   ")
    return item, "defines itself but stores no job_title", "sq role sre update --job-title"


async def _item_with_blank_mission(project, svc):
    item = await add_role_from_toml(svc, "sre", _ITEM)
    await _edit(svc, item, mission=" \t")
    return item, "defines itself but stores no mission", "sq role sre update"


async def _item_with_a_malformed_capability(project, svc):
    item = await add_role_from_toml(svc, "sre", _ITEM)
    await _edit(svc, item, capabilities=["Audit Trail", "ok"])
    return item, "stores capabilities that do not match", "sq role sre update --capabilities"


async def _template_and_mission(project, svc):
    item = await svc.activate_role(None, from_template="dev", tech="go")
    await _edit(svc, item, mission="Own it.")
    return item, "stores both `template` and `mission`", None


BROKEN = {
    "a-catalog-slug-the-catalog-no-longer-declares": _catalog_entry_gone,
    "an-undeclared-template": _template_undeclared,
    "a-template-role-missing-the-tech-its-template-takes": _template_missing_tech,
    "a-template-role-carrying-a-tech-its-template-does-not-take": _template_with_unwanted_tech,
    "an-item-defined-role-missing-its-job-title": _item_without_job_title,
    "an-item-defined-role-missing-its-description": _item_without_description,
    "an-item-defined-role-with-a-blank-job-title": _item_with_blank_job_title,
    "an-item-defined-role-with-a-blank-mission": _item_with_blank_mission,
    "an-item-defined-role-with-a-malformed-capability": _item_with_a_malformed_capability,
    "a-role-storing-both-a-template-and-a-mission": _template_and_mission,
}


@pytest.mark.parametrize("state", list(BROKEN))
async def test_an_unresolved_base_is_reported_at_error_with_its_remedy(
    project, svc, state: str
) -> None:
    item, fragment, remedy = await BROKEN[state](project, svc)

    found = await _findings(svc, "role_base_resolves")

    assert [(f.level, f.item) for f in found] == [("error", item.id)], found
    assert fragment in found[0].message
    if remedy:
        assert remedy in found[0].message


async def _clean_catalog(project, svc):
    await svc.activate_role("architect")


async def _clean_template(project, svc):
    await svc.activate_role(None, from_template="dev", tech="go")


async def _clean_item(project, svc):
    await add_role_from_toml(svc, "sre", _ITEM)


async def _clean_retired_broken(project, svc):
    item = await svc.activate_role(None, from_template="dev", tech="go")
    await _edit(svc, item, drop=("tech",))
    await svc.set_roster_status(item.id, "Archived")


CLEAN = {
    "a-catalog-role": _clean_catalog,
    "a-template-role": _clean_template,
    "an-item-defined-role": _clean_item,
    "a-retired-role-with-a-broken-base": _clean_retired_broken,
}


@pytest.mark.parametrize("state", list(CLEAN))
async def test_a_role_whose_base_resolves_is_not_reported(project, svc, state: str) -> None:
    await CLEAN[state](project, svc)

    assert await _findings(svc, "role_base_resolves") == []


# ------------------------------------------------------------------- role_definition_shadowed

#: (id, per-slug file body, fields named in the finding; ``None`` for no finding)
SHADOWS = [
    ("one-field", 'mission = "From the file."\n', ["mission"]),
    (
        "several-fields",
        'mission = "m"\ncolor = "teal"\ntitle = "t"\ndescription = "d"\n',
        ["description", "mission", "title"],
    ),
    ("a-field-the-item-does-not-store", 'color = "teal"\n', None),
    ("the-model-which-the-item-value-already-beats", 'model = "haiku"\n', None),
    ("no-file", None, None),
]


@pytest.mark.parametrize(("body", "fields"), [r[1:] for r in SHADOWS], ids=[r[0] for r in SHADOWS])
async def test_a_file_setting_what_the_item_stores_is_reported(
    project, svc, body: str | None, fields: list[str] | None
) -> None:
    item = await add_role_from_toml(svc, "sre", _ITEM)
    if body is not None:
        _write(project, "roles/sre.toml", f"# squads:override-base:{__version__}\n{body}")

    found = await _findings(svc, "role_definition_shadowed")

    if fields is None:
        assert found == []
        return
    assert [(f.level, f.item) for f in found] == [("warn", item.id)]
    assert ".overrides/roles/sre.toml" in found[0].message
    assert f"sets {', '.join(fields)}," in found[0].message
    assert "delete the file or those keys" in found[0].message


@pytest.mark.parametrize("kind", ["catalog", "template"])
async def test_a_file_over_a_catalog_or_template_role_shadows_nothing(
    project, svc, kind: str
) -> None:
    if kind == "catalog":
        await svc.activate_role("architect")
        slug = "architect"
    else:
        await svc.activate_role(None, from_template="dev", tech="go")
        slug = "go-dev"
    _write(project, f"roles/{slug}.toml", f"# squads:override-base:{__version__}\nmission = 'x'\n")

    assert await _findings(svc, "role_definition_shadowed") == []


# ------------------------------------------------------------------------------ override_loads


@pytest.mark.parametrize(
    "body",
    ['full_name = "Gwen"\n', _ITEM],
    ids=["a-partial-file", "a-complete-file"],
)
async def test_a_file_with_no_role_under_it_is_a_layer_with_no_base(
    project, svc, body: str
) -> None:
    _write(project, "roles/ghost.toml", f"# squads:override-base:{__version__}\n{body}")

    found = await _findings(svc, "override_loads")

    assert [f.level for f in found] == ["error"]
    assert "no role under it" in found[0].message
    assert "sq role add ghost --file" in found[0].message


async def test_a_legacy_dev_table_is_reported_with_the_rename(project, svc) -> None:
    _write(project, "roles.toml", '[dev]\nmodel = "opus"\n')

    found = await _findings(svc, "override_loads")

    assert found and "rename it to [templates.dev]" in found[0].message
    assert ".overrides/roles.toml" in found[0].message


async def _over(project, svc, kind: str) -> str:
    if kind == "bundled-entry":
        await svc.activate_role("architect")
        return "architect"
    if kind == "bundled-template":
        await svc.activate_role(None, from_template="dev", tech="go")
        return "go-dev"
    if kind == "item-defined":
        await add_role_from_toml(svc, "sre", _ITEM)
        return "sre"
    if kind == "project-template":
        _write(project, "roles.toml", _PLAIN_TEMPLATE)
        await svc.activate_role("scribe", from_template="scribe")
        return "scribe"
    _write(
        project,
        "roles.toml",
        f'[bundles]\nall = [{_ALL}, "ops"]\n\n[[roles]]\nslug = "ops"\nfull_name = "Olga"\n'
        'title = "ops"\ndescription = "d"\nmission = "m"\n',
    )
    await svc.activate_role("ops")
    return "ops"


#: (id, kind, stamped, an `override_stamped` error is expected)
STAMPS = [
    ("bundled-entry-unstamped", "bundled-entry", False, True),
    ("bundled-entry-stamped", "bundled-entry", True, False),
    ("bundled-template-unstamped", "bundled-template", False, True),
    ("bundled-template-stamped", "bundled-template", True, False),
    ("item-defined-unstamped", "item-defined", False, False),
    ("project-template-unstamped", "project-template", False, False),
    ("project-catalog-entry-unstamped", "project-entry", False, False),
]


@pytest.mark.parametrize(
    ("kind", "stamped", "owed"), [r[1:] for r in STAMPS], ids=[r[0] for r in STAMPS]
)
async def test_the_stamp_is_owed_only_over_a_base_the_bundled_document_declares(
    project, svc, kind: str, stamped: bool, owed: bool
) -> None:
    slug = await _over(project, svc, kind)
    stamp = f"# squads:override-base:{__version__}\n" if stamped else ""
    _write(project, f"roles/{slug}.toml", f'{stamp}color = "teal"\n')

    found = [
        i
        for i in await svc.check()
        if i.rule == "override_stamped" and f"roles/{slug}.toml" in i.item
    ]

    assert bool(found) is owed, found


#: (id, role kind, the file's stamp, an `override_current` warning is expected)
STALE = [
    ("bundled-entry-stale", "bundled-entry", "0.16.0", True),
    ("bundled-entry-current", "bundled-entry", __version__, False),
    ("item-defined-stale", "item-defined", "0.16.0", False),
]


@pytest.mark.parametrize(
    ("kind", "stamp", "stale"), [r[1:] for r in STALE], ids=[r[0] for r in STALE]
)
async def test_a_stale_stamp_is_reported_only_over_a_base_the_bundled_document_declares(
    project, svc, kind: str, stamp: str, stale: bool
) -> None:
    slug = await _over(project, svc, kind)
    _write(project, f"roles/{slug}.toml", f'# squads:override-base:{stamp}\nmission = "x"\n')

    found = [
        i
        for i in await svc.check()
        if i.rule == "override_current" and f"roles/{slug}.toml" in i.item
    ]

    assert bool(found) is stale, found
