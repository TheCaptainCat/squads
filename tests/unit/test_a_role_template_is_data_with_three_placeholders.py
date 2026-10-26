"""A ``[templates.<name>]`` table of the role catalog is data: a closed key space, three
placeholders (``{tech}``, ``{Tech}``, ``{first}`` in ``name`` only) with ``{{`` / ``}}`` as the
escape, and a refusal at load that names the template and the key for anything else.

Each table is one behaviour across the shapes its input can take.
"""

from pathlib import Path

import pytest

from squads._errors import SquadsError
from squads._roles._catalog import instantiate_template
from squads._roles._loader import LEGACY_DEV_TABLE_MESSAGE, load_role_catalog
from squads._roles._models import RoleTemplateSpec
from squads._roles._templates import (
    placeholder_problems,
    placeholders,
    proposed_name,
    proposed_slug,
    takes_parameter,
)

_REQUIRED = 'title = "T"\ndescription = "D"\nmission = "M"\n'


def _catalog(tmp_path: Path, body: str):
    overrides = tmp_path / ".overrides"
    overrides.mkdir(exist_ok=True)
    (overrides / "roles.toml").write_text(body, encoding="utf-8")
    return load_role_catalog(tmp_path)


# --------------------------------------------------------------------------- placeholder text

#: (id, text, names it uses)
SCANNED = [
    ("none", "Plain text", []),
    ("tech", "In {tech}", ["tech"]),
    ("upper-tech", "In {Tech}", ["Tech"]),
    ("first", "{first} {Tech}", ["first", "Tech"]),
    ("escaped-open", "{{tech}}", []),
    ("escaped-close", "a }} b", []),
    ("escape-beside-placeholder", "{{ {tech} }}", ["tech"]),
    ("unknown", "{x}", ["x"]),
    ("empty", "{}", [""]),
    ("lone-open", "a { b", ["{"]),
    ("lone-close", "a } b", ["}"]),
]


@pytest.mark.parametrize(("text", "names"), [r[1:] for r in SCANNED], ids=[r[0] for r in SCANNED])
def test_the_scanner_reads_placeholders_and_skips_escapes(text: str, names: list[str]) -> None:
    assert placeholders(text) == names


# ------------------------------------------------- instantiation: each placeholder, each position

#: (id, template body, tech, expected title, mission, name, slug)
INSTANTIATED = [
    (
        "tech-lowercase",
        'slug = "{tech}-aud"\nname = "{first} {Tech}"\nname_pool = ["Ada", "Bo"]\n'
        'title = "{tech} auditor"\ndescription = "D"\nmission = "Audit {tech}."\n',
        "go",
        "go auditor",
        "Audit go.",
        "Ada Go",
        "go-aud",
    ),
    (
        "tech-capitalised-keeps-the-rest",
        'slug = "{tech}-aud"\nname = "{first} {Tech}"\nname_pool = ["Ada", "Bo"]\n'
        'title = "{Tech} auditor"\ndescription = "D"\nmission = "Audit {Tech}."\n',
        "nodeJS",
        "NodeJS auditor",
        "Audit NodeJS.",
        "Ada NodeJS",
        "nodejs-aud",
    ),
    (
        "escaped-braces-stay-literal",
        'title = "Uses {{tech}}"\ndescription = "D"\nmission = "Braces }} stay."\n',
        None,
        "Uses {tech}",
        "Braces } stay.",
        None,
        None,
    ),
    (
        "slug-is-slugified",
        'slug = "{tech}-aud"\ntitle = "T"\ndescription = "D"\nmission = "M"\n',
        "Node.js",
        "T",
        "M",
        None,
        "node-js-aud",
    ),
]


@pytest.mark.parametrize(
    ("body", "tech", "title", "mission", "name", "slug"),
    [r[1:] for r in INSTANTIATED],
    ids=[r[0] for r in INSTANTIATED],
)
def test_a_template_instantiates_every_placeholder_where_it_is_written(
    tmp_path: Path,
    body: str,
    tech: str | None,
    title: str,
    mission: str,
    name: str | None,
    slug: str | None,
) -> None:
    template = _catalog(tmp_path, f"[templates.audit]\n{body}").templates["audit"]

    assert proposed_name(template, tech, 0) == name
    assert proposed_slug(template, tech) == slug
    role = instantiate_template(template, tech=tech, slug=slug or "x", full_name=name or "N")
    assert (role.title, role.mission) == (title, mission)


def test_the_name_pool_wraps_around() -> None:
    template = RoleTemplateSpec(
        name="{first} {Tech}", name_pool=["Ada", "Bo"], title="T", description="D", mission="M"
    )

    assert [proposed_name(template, "go", n) for n in range(5)] == [
        "Ada Go",
        "Bo Go",
        "Ada Go",
        "Bo Go",
        "Ada Go",
    ]


#: (id, template body, takes a parameter)
PARAMETERS = [
    ("none", 'title = "T"\ndescription = "D"\nmission = "M"\n', False),
    ("lowercase-in-mission", 'title = "T"\ndescription = "D"\nmission = "{tech}"\n', True),
    ("uppercase-in-title", 'title = "{Tech}"\ndescription = "D"\nmission = "M"\n', True),
    (
        "in-a-list-entry",
        'title = "T"\ndescription = "D"\nmission = "M"\nresponsibilities = ["Run {tech}"]\n',
        True,
    ),
    ("only-escaped", 'title = "{{tech}}"\ndescription = "D"\nmission = "M"\n', False),
    (
        "first-alone",
        'name = "{first}"\nname_pool = ["Ada"]\ntitle = "T"\ndescription = "D"\nmission = "M"\n',
        False,
    ),
]


@pytest.mark.parametrize(
    ("body", "takes"), [r[1:] for r in PARAMETERS], ids=[r[0] for r in PARAMETERS]
)
def test_a_template_takes_a_parameter_only_when_it_uses_tech_unescaped(
    tmp_path: Path, body: str, takes: bool
) -> None:
    template = _catalog(tmp_path, f"[templates.audit]\n{body}").templates["audit"]

    assert takes_parameter(template) is takes


# --------------------------------------------------------------------------- load refusals

#: (id, template body, fragments the refusal carries)
REFUSED = [
    (
        "unknown-placeholder",
        'title = "{x}"\ndescription = "D"\nmission = "M"\n',
        ["template 'audit'", "title", "{x}"],
    ),
    (
        "first-outside-name",
        'title = "T"\ndescription = "D"\nmission = "{first}"\n',
        ["template 'audit'", "mission", "{first} is valid in `name` only"],
    ),
    (
        "first-in-a-list-entry",
        'title = "T"\ndescription = "D"\nmission = "M"\nresponsibilities = ["{first}"]\n',
        ["template 'audit'", "responsibilities[0]"],
    ),
    (
        "unbalanced-brace",
        'title = "T"\ndescription = "D"\nmission = "a { b"\n',
        ["template 'audit'", "mission", "unbalanced brace"],
    ),
    (
        "first-with-an-empty-pool",
        'name = "{first}"\ntitle = "T"\ndescription = "D"\nmission = "M"\n',
        ["template 'audit'", "name_pool is empty"],
    ),
    (
        "duplicate-pool-entry",
        'name_pool = ["Ada", "Ada"]\ntitle = "T"\ndescription = "D"\nmission = "M"\n',
        ["template 'audit'", "name_pool has duplicates"],
    ),
    (
        "missing-title",
        'description = "D"\nmission = "M"\n',
        ["audit", "missing required key(s): title"],
    ),
    (
        "missing-description",
        'title = "T"\nmission = "M"\n',
        ["audit", "missing required key(s): description"],
    ),
    (
        "missing-mission",
        'title = "T"\ndescription = "D"\n',
        ["audit", "missing required key(s): mission"],
    ),
    ("blank-mission", 'title = "T"\ndescription = "D"\nmission = "  "\n', ["audit", "mission"]),
    (
        "full-name",
        'title = "T"\ndescription = "D"\nmission = "M"\nfull_name = "X"\n',
        ["audit", "'full_name' is not a template key", "--name"],
    ),
    (
        "is-default",
        'title = "T"\ndescription = "D"\nmission = "M"\nis_default = true\n',
        ["audit", "'is_default' is not a template key", "set-default"],
    ),
    (
        "unknown-key",
        'title = "T"\ndescription = "D"\nmission = "M"\nflavour = "x"\n',
        ["audit", "flavour"],
    ),
    (
        "bad-model",
        'title = "T"\ndescription = "D"\nmission = "M"\nmodel = "opuss"\n',
        ["audit", "model 'opuss'"],
    ),
    (
        "bad-capability",
        'title = "T"\ndescription = "D"\nmission = "M"\ncapabilities = ["Bad"]\n',
        ["audit", "capabilities entry 'Bad' must match"],
    ),
    (
        "blank-color",
        'title = "T"\ndescription = "D"\nmission = "M"\ncolor = " "\n',
        ["audit", "'color' is blank"],
    ),
    (
        "pronouns",
        'title = "T"\ndescription = "D"\nmission = "M"\npronouns = "they/them"\n',
        ["audit", "pronouns"],
    ),
]


@pytest.mark.parametrize(
    ("body", "fragments"), [r[1:] for r in REFUSED], ids=[r[0] for r in REFUSED]
)
def test_a_template_that_breaks_the_grammar_is_refused_at_load_naming_it(
    tmp_path: Path, body: str, fragments: list[str]
) -> None:
    with pytest.raises(SquadsError) as excinfo:
        _catalog(tmp_path, f"[templates.audit]\n{body}")

    for fragment in fragments:
        assert fragment in str(excinfo.value)
    assert ".overrides/roles.toml" in str(excinfo.value)


def test_the_validator_names_every_offending_key_in_one_pass() -> None:
    template = RoleTemplateSpec(title="{a}", description="{b}", mission="{c}")

    assert len(placeholder_problems(template)) == 3


# --------------------------------------------------------------------------- override shapes


def test_an_override_can_add_a_template(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path, f"[templates.audit]\n{_REQUIRED}capabilities = ['audit']\n")

    assert sorted(catalog.templates) == ["audit", "dev"]
    assert catalog.templates["audit"].capabilities == ["audit"]


def test_an_override_changes_one_field_of_the_bundled_template_leaving_the_rest(
    tmp_path: Path,
) -> None:
    bundled = load_role_catalog().templates["dev"]
    catalog = _catalog(tmp_path, '[templates.dev]\nmission = "Build {Tech} things."\n')

    changed = catalog.templates["dev"]
    assert changed.mission == "Build {Tech} things."
    assert changed.model_copy(update={"mission": bundled.mission}) == bundled


def test_the_append_idiom_extends_a_template_list_before_placeholders_resolve(
    tmp_path: Path,
) -> None:
    catalog = _catalog(
        tmp_path, '[templates.dev]\nresponsibilities = ["$(*self)", "Run the {Tech} linters"]\n'
    )

    template = catalog.templates["dev"]
    assert template.responsibilities[-1] == "Run the {Tech} linters"
    assert (
        len(template.responsibilities)
        == len(load_role_catalog().templates["dev"].responsibilities) + 1
    )
    role = instantiate_template(template, tech="go", slug="go-dev", full_name="Ada Go")
    assert role.responsibilities[-1] == "Run the Go linters"


def test_selected_can_drop_the_dev_template(tmp_path: Path) -> None:
    catalog = _catalog(
        tmp_path, '[selected]\ntemplates = ["audit"]\n\n[templates.audit]\n' + _REQUIRED
    )

    assert list(catalog.templates) == ["audit"]
    assert catalog.developer_capabilities() == frozenset()


def test_a_legacy_dev_table_is_refused_with_the_rename(tmp_path: Path) -> None:
    with pytest.raises(SquadsError) as excinfo:
        _catalog(tmp_path, '[dev]\nmodel = "opus"\n')

    assert str(excinfo.value) == LEGACY_DEV_TABLE_MESSAGE
    assert str(excinfo.value) == (
        ".overrides/roles.toml: [dev] is not a key of the role catalog; rename it to "
        "[templates.dev] (its name_pool, model, color and capabilities keys are unchanged)"
    )


def test_a_template_name_outside_the_slug_grammar_is_refused(tmp_path: Path) -> None:
    with pytest.raises(SquadsError, match="the name must match"):
        _catalog(tmp_path, f'[templates."Not Valid"]\n{_REQUIRED}')
