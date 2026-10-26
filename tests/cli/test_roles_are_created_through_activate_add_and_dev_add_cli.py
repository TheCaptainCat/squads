"""``sq role activate`` (a catalog role, or ``--from <template>``), ``sq role add`` (a role that
defines itself) and ``sq dev add`` (an alias of ``activate --from dev``) all end in one creation
path: one reserved-slug check, one duplicate check, one materialisation.

One table per behaviour, driven at the CLI and read back from the stored frontmatter.
"""

import json

import pytest

from squads._sections import split_frontmatter

pytestmark = pytest.mark.anyio

_AUDITOR = (
    '[templates.auditor]\ntitle = "{Tech} auditor"\ndescription = "Audits {Tech}."\n'
    'mission = "Audit {Tech}."\nslug = "{tech}-aud"\nname = "{first} {Tech}"\n'
    'name_pool = ["Ann", "Bo", "Cy"]\ncapabilities = ["audit"]\n'
)
_NO_PATTERNS = '[templates.scribe]\ntitle = "Scribe"\ndescription = "Writes."\nmission = "Write."\n'
_FIELDS = [
    "--name",
    "Sam Sre",
    "--job-title",
    "SRE",
    "--desc",
    "Keeps it up.",
    "--mission",
    "Run it.",
]


def _templates(project, *tables: str) -> None:
    path = project.squad_dir / ".overrides" / "roles.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(tables), encoding="utf-8")


def _front(project, slug: str) -> dict[str, object]:
    path = next((project.squad_dir / "agents" / "roles").glob(f"*-{slug}.md"))
    return split_frontmatter(path.read_text(encoding="utf-8"))[0]


def _tree(project) -> dict[str, bytes]:
    return {
        str(p.relative_to(project.root)): p.read_bytes()
        for p in sorted(project.root.rglob("*"))
        if p.is_file() and ".git" not in p.parts
    }


# ------------------------------------------------------------------------------- creation

#: (id, templates declared, argv, exit code, slug, name, stored attributes, message fragment)
CREATION = [
    ("catalog", [], ["role", "activate", "architect"], 0, "architect", "Robert Architect", {}, ""),
    (
        "catalog-with-model-and-name",
        [],
        ["role", "activate", "qa", "--name", "Quinn Qa", "--model", "haiku"],
        0,
        "qa",
        "Quinn Qa",
        {"model": "haiku"},
        "",
    ),
    (
        "dev-template",
        [],
        ["role", "activate", "--from", "dev", "--tech", "python"],
        0,
        "python-dev",
        "Elias Python",
        {"template": "dev", "tech": "python"},
        "",
    ),
    (
        "template-with-an-explicit-slug",
        [],
        ["role", "activate", "snake", "--from", "dev", "--tech", "python"],
        0,
        "snake",
        "Elias Python",
        {"template": "dev", "tech": "python"},
        "",
    ),
    (
        "template-with-a-slug-pattern-and-no-slug-given",
        [_AUDITOR],
        ["role", "activate", "--from", "auditor", "--tech", "go"],
        0,
        "go-aud",
        "Ann Go",
        {"template": "auditor", "tech": "go"},
        "",
    ),
    (
        "template-with-no-slug-pattern-and-a-slug-given",
        [_NO_PATTERNS],
        ["role", "activate", "writer", "--from", "scribe", "--name", "Wren Writer"],
        0,
        "writer",
        "Wren Writer",
        {"template": "scribe"},
        "",
    ),
    (
        "template-with-no-slug-pattern-and-no-slug",
        [_NO_PATTERNS],
        ["role", "activate", "--from", "scribe", "--name", "Wren"],
        1,
        None,
        None,
        None,
        "declares no slug pattern",
    ),
    (
        "template-with-no-name-pattern-and-no-name",
        [_NO_PATTERNS],
        ["role", "activate", "writer", "--from", "scribe"],
        1,
        None,
        None,
        None,
        "declares no name pattern: pass --name",
    ),
    (
        "tech-missing",
        [],
        ["role", "activate", "--from", "dev"],
        1,
        None,
        None,
        None,
        "takes a technology: pass --tech",
    ),
    (
        "tech-refused-on-a-template-without-a-parameter",
        [_NO_PATTERNS],
        ["role", "activate", "writer", "--from", "scribe", "--tech", "go", "--name", "W"],
        1,
        None,
        None,
        None,
        "takes no --tech",
    ),
    (
        "tech-refused-on-a-catalog-role",
        [],
        ["role", "activate", "architect", "--tech", "go"],
        1,
        None,
        None,
        None,
        "--tech applies to a role built with --from",
    ),
    (
        "unknown-template",
        [],
        ["role", "activate", "--from", "ghost", "--tech", "go"],
        1,
        None,
        None,
        None,
        "the declared templates are: dev",
    ),
    (
        "a-slug-the-catalog-declares",
        [],
        ["role", "activate", "architect", "--from", "dev", "--tech", "go"],
        1,
        None,
        None,
        None,
        "belongs to a role the catalog declares",
    ),
    (
        "invalid-model",
        [],
        ["role", "activate", "--from", "dev", "--tech", "go", "--model", "opuss"],
        1,
        None,
        None,
        None,
        "is not one of",
    ),
]


@pytest.mark.parametrize(
    ("templates", "argv", "code", "slug", "name", "stored", "fragment"),
    [r[1:] for r in CREATION],
    ids=[r[0] for r in CREATION],
)
async def test_each_creation_shape_stores_what_it_says_or_refuses_and_writes_nothing(
    project, invoke, templates, argv, code, slug, name, stored, fragment
) -> None:
    if templates:
        _templates(project, *templates)
    before = _tree(project)

    result = await invoke(argv)

    assert result.exit_code == code, result.output
    if code == 1:
        assert fragment in " ".join(result.output.split())
        assert _tree(project) == before
        return
    front = _front(project, slug)
    assert front["title"] == name
    assert {k: front.get(k) for k in stored} == stored
    assert "description" not in front or not front["description"]


async def test_the_pool_position_counts_the_roles_that_store_the_same_template(
    project, invoke
) -> None:
    _templates(project, _AUDITOR)
    for argv in (
        ["dev", "add", "--tech", "rust"],
        ["dev", "add", "--tech", "go"],
        ["role", "activate", "--from", "auditor", "--tech", "go"],
        ["role", "activate", "--from", "auditor", "--tech", "rust"],
    ):
        assert (await invoke(argv)).exit_code == 0

    assert _front(project, "rust-dev")["title"] == "Elias Rust"
    assert _front(project, "go-dev")["title"] == "Ada Go"
    assert _front(project, "go-aud")["title"] == "Ann Go"
    assert _front(project, "rust-aud")["title"] == "Bo Rust"


#: (id, per-slug file body, --name, expected name)
NAMES = [
    ("name-flag", 'full_name = "File Name"\n', "Flag Name", "Flag Name"),
    ("per-slug-full-name", 'full_name = "File Name"\n', None, "File Name"),
    ("name-pattern", None, None, "Elias Rust"),
]


@pytest.mark.parametrize(
    ("file_body", "flag", "expected"), [r[1:] for r in NAMES], ids=[r[0] for r in NAMES]
)
async def test_the_name_is_the_flag_then_the_per_slug_name_then_the_pattern(
    project, invoke, file_body, flag, expected
) -> None:
    if file_body is not None:
        path = project.squad_dir / ".overrides" / "roles" / "rust-dev.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(file_body, encoding="utf-8")

    result = await invoke(
        ["role", "activate", "--from", "dev", "--tech", "rust", *(["--name", flag] if flag else [])]
    )

    assert result.exit_code == 0, result.output
    assert _front(project, "rust-dev")["title"] == expected


@pytest.mark.parametrize(
    "argv",
    [["dev", "add", "--tech", "rust"], ["role", "activate", "--from", "dev", "--tech", "rust"]],
)
async def test_a_second_role_under_a_taken_slug_is_refused_by_both_spellings(
    project, invoke, argv
) -> None:
    assert (await invoke(["dev", "add", "--tech", "rust"])).exit_code == 0
    before = _tree(project)

    result = await invoke(argv)

    assert result.exit_code == 1, result.output
    assert "a role with slug 'rust-dev' already exists" in result.output
    assert _tree(project) == before


# ------------------------------------------------------------------- the dev alias is exact


def _same_words(text: str) -> str:
    return " ".join(text.replace("Usage: sq dev add", "Usage: sq role activate").split())


#: (id, templates, dev-add argv, activate --from argv)
ALIASES = [
    ("success", [], ["--tech", "rust"], ["--tech", "rust"]),
    (
        "with-name-model-slug",
        [],
        ["--tech", "go", "--name", "Gus Go", "--model", "opus", "--slug", "gus"],
        ["gus", "--tech", "go", "--name", "Gus Go", "--model", "opus"],
    ),
    ("missing-tech", [], [], []),
    (
        "invalid-model",
        [],
        ["--tech", "go", "--model", "opuss"],
        ["--tech", "go", "--model", "opuss"],
    ),
]


@pytest.mark.parametrize(
    ("dev_args", "from_args"), [r[2:] for r in ALIASES], ids=[r[0] for r in ALIASES]
)
async def test_dev_add_and_activate_from_dev_answer_identically(
    tmp_path_factory, invoke, frozen_time, dev_args: list[str], from_args: list[str]
) -> None:
    results = []
    stored = []
    for alias in (True, False):
        root = tmp_path_factory.mktemp("squad")
        assert (
            await invoke(["-C", str(root), "init", "--roles", "minimal", "--default-names"])
        ).exit_code == 0
        argv = (
            ["dev", "add", *dev_args]
            if alias
            else ["role", "activate", "--from", "dev", *from_args]
        )
        result = await invoke(["-C", str(root), *argv])
        results.append((result.exit_code, result.output))
        roles = sorted((root / "squads" / "agents" / "roles").glob("ROLE-*-*-dev.md"))
        stored.append(
            [p.read_text(encoding="utf-8").replace(p.name, "") for p in roles] + [str(len(roles))]
        )

    assert results[0][0] == results[1][0]
    assert _same_words(results[0][1]) == _same_words(results[1][1])
    assert stored[0] == stored[1]


async def test_dev_add_help_says_it_is_the_activate_alias(project, invoke) -> None:
    result = await invoke(["dev", "add", "--help"])

    assert result.exit_code == 0, result.output
    assert "sq role activate [<slug>] --from dev --tech <t>" in " ".join(result.output.split())


async def test_dev_add_with_the_dev_template_dropped_names_the_declared_templates(
    project, invoke
) -> None:
    _templates(project, '[selected]\ntemplates = ["scribe"]\n', _NO_PATTERNS)
    before = _tree(project)

    result = await invoke(["dev", "add", "--tech", "rust"])
    listed = await invoke(["dev", "list"])

    assert result.exit_code == 1, result.output
    assert "the declared templates are: scribe" in " ".join(result.output.split())
    assert _tree(project) == before
    assert listed.exit_code == 0 and "no developers" in listed.output
    assert "dev add" not in listed.output


async def test_dev_list_lists_the_live_roles_holding_a_capability_the_dev_template_declares(
    project, invoke
) -> None:
    assert (await invoke(["dev", "add", "--tech", "rust"])).exit_code == 0
    assert (
        await invoke(["role", "add", "builder", *_FIELDS, "--capabilities", "dev"])
    ).exit_code == 0
    assert (
        await invoke(["role", "add", "scout", *_FIELDS[:0], "--name", "Sid Scout", *_FIELDS[2:]])
    ).exit_code == 0

    listed = await invoke(["dev", "list"])

    assert listed.exit_code == 0, listed.output
    slugs = {line.split()[1] for line in listed.output.splitlines()[1:] if line.strip()}
    assert slugs == {"rust-dev", "builder"}


# ------------------------------------------------------------------------------ role add

_DEFINITION = (
    'full_name = "Wren Writer"\ntitle = "writer"\ndescription = "Writes."\nmission = "Write."\n'
    'capabilities = ["write"]\nmodel = "haiku"\ncolor = "teal"\n'
    'responsibilities = ["Draft", "Edit"]\n'
)


async def test_role_add_from_flags_alone_stores_the_definition_on_the_item(project, invoke) -> None:
    result = await invoke(["role", "add", "sre", *_FIELDS, "--capabilities", "ops, pager"])

    assert result.exit_code == 0, result.output
    front = _front(project, "sre")
    assert front["title"] == "Sam Sre"
    assert front["job_title"] == "SRE"
    assert front["description"] == "Keeps it up."
    assert front["mission"] == "Run it."
    assert front["capabilities"] == ["ops", "pager"]
    assert front["origin"] == "project"
    assert "template" not in front and "tech" not in front


async def test_role_add_from_a_file_alone_reads_the_override_grammar(project, invoke) -> None:
    file = project.root / "writer.toml"
    file.write_text(_DEFINITION, encoding="utf-8")

    result = await invoke(["role", "add", "writer", "--file", str(file)])

    assert result.exit_code == 0, result.output
    front = _front(project, "writer")
    assert front["title"] == "Wren Writer" and front["job_title"] == "writer"
    assert front["responsibilities"] == ["Draft", "Edit"]
    assert front["model"] == "haiku" and front["color"] == "teal"
    assert not (project.squad_dir / ".overrides" / "roles" / "writer.toml").exists()


async def test_flags_beside_a_file_win_over_its_keys(project, invoke) -> None:
    file = project.root / "writer.toml"
    file.write_text(_DEFINITION, encoding="utf-8")

    result = await invoke(
        ["role", "add", "writer", "--file", str(file), "--name", "Flag Name", "--model", "opus"]
    )

    assert result.exit_code == 0, result.output
    front = _front(project, "writer")
    assert front["title"] == "Flag Name" and front["model"] == "opus"
    assert front["mission"] == "Write."


#: (id, flags, fragments naming every missing field)
MISSING = [
    ("everything", [], ["--name", "--job-title", "--desc", "--mission"]),
    ("only-the-name", ["--job-title", "t", "--desc", "d", "--mission", "m"], ["--name"]),
    ("mission-and-desc", ["--name", "N", "--job-title", "t"], ["--desc", "--mission"]),
]


@pytest.mark.parametrize(
    ("flags", "fragments"), [r[1:] for r in MISSING], ids=[r[0] for r in MISSING]
)
async def test_role_add_names_every_missing_field_in_one_message_and_writes_nothing(
    project, invoke, flags, fragments
) -> None:
    before = _tree(project)

    result = await invoke(["role", "add", "sre", *flags])

    assert result.exit_code == 1, result.output
    for fragment in fragments:
        assert fragment in result.output
    assert _tree(project) == before


async def test_role_add_refuses_a_malformed_capability_and_writes_nothing(project, invoke) -> None:
    before = _tree(project)

    result = await invoke(["role", "add", "sre", *_FIELDS, "--capabilities", "Not Valid"])

    assert result.exit_code == 1, result.output
    assert "--capabilities entries must match" in result.output
    assert _tree(project) == before


async def test_role_add_refuses_default_designation_and_a_slug_the_catalog_declares(
    project, invoke
) -> None:
    file = project.root / "x.toml"
    file.write_text(_DEFINITION + "is_default = true\n", encoding="utf-8")
    before = _tree(project)

    designated = await invoke(["role", "add", "writer", "--file", str(file)])
    taken = await invoke(["role", "add", "architect", *_FIELDS])

    assert designated.exit_code == 1 and "set-default" in designated.output
    assert taken.exit_code == 1 and "belongs to a role the catalog declares" in taken.output
    assert _tree(project) == before


# ------------------------------------------------------------------------- reserved slugs

#: (id, slug, fragment of the refusal; ``None`` for the control that is created)
RESERVED = [
    ("squads", "squads", "reserved for system entries"),
    ("operator", "operator", "reserved for the anonymous author"),
    ("op-prefix", "op-foo", "reserved for operators"),
    ("group-verb", "list", "is a verb of `sq role`"),
    ("add-verb", "add", "is a verb of `sq role`"),
    ("control", "sre", None),
]


#: verb -> argv builder; the last two leave out what the verb would otherwise complain about
#: first, so only a reserved-slug check that runs before everything else answers them.
_VERBS = {
    "add": lambda slug: ["role", "add", slug, *_FIELDS],
    "activate-from": lambda slug: ["role", "activate", slug, "--from", "dev", "--tech", "go"],
    "add-without-fields": lambda slug: ["role", "add", slug],
    "activate-from-without-a-name": lambda slug: ["role", "activate", slug, "--from", "scribe"],
}


@pytest.mark.parametrize(
    ("slug", "fragment"), [r[1:] for r in RESERVED], ids=[r[0] for r in RESERVED]
)
@pytest.mark.parametrize("verb", list(_VERBS))
async def test_both_creation_verbs_share_the_reserved_slug_check(
    project, invoke, verb: str, slug: str, fragment
) -> None:
    _templates(project, _NO_PATTERNS)
    before = _tree(project)

    result = await invoke(_VERBS[verb](slug))

    if fragment is None:
        assert result.exit_code == (0 if verb in ("add", "activate-from") else 1), result.output
        return
    assert result.exit_code == 1, result.output
    assert fragment in result.output
    assert _tree(project) == before


# -------------------------------------------------------------------------------- pointers


async def test_activate_names_role_add_for_a_slug_only_a_file_declares(project, invoke) -> None:
    file = project.squad_dir / ".overrides" / "roles" / "writer.toml"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(_DEFINITION, encoding="utf-8")

    result = await invoke(["role", "activate", "writer"])

    assert result.exit_code == 1, result.output
    assert "sq role add writer --file squads/.overrides/roles/writer.toml" in " ".join(
        result.output.split()
    )


async def test_override_scaffold_new_points_at_role_add_and_writes_nothing(project, invoke) -> None:
    before = _tree(project)

    result = await invoke(["override", "scaffold", "--new", "sre"])

    assert result.exit_code == 1, result.output
    assert "sq role add sre" in " ".join(result.output.split())
    assert _tree(project) == before


async def test_a_created_role_lists_with_its_origin_and_description(project, invoke) -> None:
    assert (await invoke(["role", "add", "sre", *_FIELDS])).exit_code == 0

    listed = json.loads((await invoke(["role", "list", "--json"])).output)

    row = next(r for r in listed if r["slug"] == "sre")
    assert (row["origin"], row["description"]) == ("project", "Keeps it up.")


# ----------------------------------------------- activating a role that is already there


async def _live(invoke, kind: str, with_file: bool, project) -> str:
    if kind == "template":
        assert (await invoke(["dev", "add", "--tech", "rust"])).exit_code == 0
        slug = "rust-dev"
    elif kind == "item":
        assert (await invoke(["role", "add", "sre", *_FIELDS])).exit_code == 0
        slug = "sre"
    else:
        assert (await invoke(["role", "activate", "reviewer"])).exit_code == 0
        slug = "reviewer"
    if with_file:
        file = project.squad_dir / ".overrides" / "roles" / f"{slug}.toml"
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text('color = "teal"\n', encoding="utf-8")
    return slug


@pytest.mark.parametrize("with_file", [False, True], ids=["no-file", "per-slug-file"])
@pytest.mark.parametrize("kind", ["catalog", "template", "item"])
async def test_activating_a_live_role_of_any_kind_is_a_no_op(
    project, invoke, kind: str, with_file: bool
) -> None:
    slug = await _live(invoke, kind, with_file, project)
    before = _tree(project)

    result = await invoke(["role", "activate", slug])

    assert result.exit_code == 0, result.output
    assert _tree(project) == before


@pytest.mark.parametrize("kind", ["catalog", "template", "item"])
@pytest.mark.parametrize(
    ("flags", "named"),
    [
        (["--model", "haiku"], "--model"),
        (["--name", "Someone Else"], "--name"),
        (["--pronouns", "she/her"], "--pronouns"),
    ],
    ids=["model", "name", "pronouns"],
)
async def test_activating_a_live_role_with_a_flag_that_would_change_it_is_refused(
    project, invoke, kind: str, flags: list[str], named: str
) -> None:
    slug = await _live(invoke, kind, False, project)
    before = _tree(project)

    result = await invoke(["role", "activate", slug, *flags])

    assert result.exit_code == 1, result.output
    message = " ".join(result.output.split())
    assert f"already active; change {named}" in message
    assert f"sq role {slug} update {named}" in message
    assert _tree(project) == before


async def test_activating_a_live_role_with_the_values_it_already_has_is_a_no_op(
    project, invoke
) -> None:
    assert (await invoke(["role", "activate", "reviewer", "--model", "haiku"])).exit_code == 0
    before = _tree(project)

    result = await invoke(["role", "activate", "reviewer", "--model", "haiku"])

    assert result.exit_code == 0, result.output
    assert _tree(project) == before


# ----------------------------------------------- a refusal names the flag, not the override


async def test_role_add_names_a_blank_flag_without_override_vocabulary(project, invoke) -> None:
    before = _tree(project)

    result = await invoke(
        ["role", "add", "sre", "--name", "X", "--job-title", "", "--desc", "D", "--mission", "M"]
    )

    assert result.exit_code == 1, result.output
    assert "--job-title cannot be blank" in result.output
    assert "override" not in result.output
    assert _tree(project) == before


async def test_a_malformed_capabilities_flag_beside_a_valid_file_blames_the_flag(
    project, invoke
) -> None:
    file = project.root / "sre.toml"
    file.write_text(
        'full_name = "S"\ntitle = "t"\ndescription = "d"\nmission = "m"\n', encoding="utf-8"
    )
    before = _tree(project)

    result = await invoke(["role", "add", "sre", "--file", str(file), "--capabilities", "a,B c"])

    assert result.exit_code == 1, result.output
    assert "--capabilities" in result.output
    assert "sre.toml" not in result.output
    assert _tree(project) == before


async def test_role_add_refreshes_the_managed_roster(project, invoke) -> None:
    assert (await invoke(["role", "add", "sre", *_FIELDS])).exit_code == 0

    claude = (project.root / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Sam Sre" in claude
    assert (await invoke(["check"])).exit_code == 0
