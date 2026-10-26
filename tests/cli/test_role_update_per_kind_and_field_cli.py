"""``sq role <slug> update`` edits a role: the name, pronouns and model on every kind, the
definition fields on a role that defines itself, and refuses the definition fields elsewhere
(exit 1, nothing written, the message naming the file that holds them).

One table over the three kinds and every flag, asserting the exit code, the stored frontmatter
before and after, and the message.
"""

import json
from pathlib import Path

import pytest

from squads._errors import SquadsError
from squads._sections import split_frontmatter

pytestmark = pytest.mark.anyio

_ADD = ["--name", "Sam Sre", "--job-title", "SRE", "--desc", "Keeps it up.", "--mission", "Run it."]

_KINDS = {
    "catalog": (["role", "activate", "architect"], "architect"),
    "template": (["dev", "add", "--tech", "rust"], "rust-dev"),
    "item": (["role", "add", "sre", *_ADD], "sre"),
}


def _front(project, slug: str) -> dict[str, object]:
    path = next((project.squad_dir / "agents" / "roles").glob(f"*-{slug}.md"))
    return split_frontmatter(path.read_text(encoding="utf-8"))[0]


def _tree(project) -> dict[str, bytes]:
    return {
        str(p.relative_to(project.root)): p.read_bytes()
        for p in sorted(project.root.rglob("*"))
        if p.is_file() and ".git" not in p.parts
    }


async def _make(invoke, kind: str) -> str:
    argv, slug = _KINDS[kind]
    result = await invoke(argv)
    assert result.exit_code == 0, result.output
    return slug


# ------------------------------------------------------- the three flags every kind accepts

#: (id, flags, key stored on the item, expected stored value)
EVERY_KIND = [
    ("title", ["--title", "Renamed Person"], "title", "Renamed Person"),
    ("pronouns", ["--pronouns", "she/her"], "pronouns", "she/her"),
    ("model", ["--model", "haiku"], "model", "haiku"),
]


@pytest.mark.parametrize("kind", list(_KINDS))
@pytest.mark.parametrize(
    ("flags", "key", "expected"), [r[1:] for r in EVERY_KIND], ids=[r[0] for r in EVERY_KIND]
)
async def test_the_name_pronouns_and_model_are_editable_on_every_kind(
    project, invoke, kind: str, flags: list[str], key: str, expected: str
) -> None:
    slug = await _make(invoke, kind)

    result = await invoke(["role", slug, "update", *flags])

    assert result.exit_code == 0, result.output
    assert _front(project, slug)[key] == expected


@pytest.mark.parametrize("kind", ["template", "item"])
async def test_a_blank_model_clears_the_stored_one_and_the_role_follows_its_base(
    project, invoke, kind: str
) -> None:
    slug = await _make(invoke, kind)
    assert (await invoke(["role", slug, "update", "--model", "haiku"])).exit_code == 0

    cleared = await invoke(["role", slug, "update", "--model", ""])

    assert cleared.exit_code == 0, cleared.output
    assert "model" not in _front(project, slug)
    shown = json.loads((await invoke(["role", slug, "show", "--json"])).output)
    assert shown["model"] == ("sonnet" if kind == "template" else None)


# ----------------------------------------------------------- the definition flags, per kind

#: (id, flags, key stored on a role that defines itself, expected stored value)
DEFINITION = [
    ("job-title", ["--job-title", "Lead SRE"], "job_title", "Lead SRE"),
    ("desc", ["--desc", "Pages first."], "description", "Pages first."),
    ("mission", ["--mission", "Own uptime."], "mission", "Own uptime."),
    ("capabilities", ["--capabilities", "ops, pager"], "capabilities", ["ops", "pager"]),
    ("color", ["--color", "teal"], "color", "teal"),
    ("can-spawn", ["--can-spawn", "yes"], "can_spawn", True),
]


@pytest.mark.parametrize(
    ("flags", "key", "expected"), [r[1:] for r in DEFINITION], ids=[r[0] for r in DEFINITION]
)
async def test_every_definition_flag_edits_a_role_that_defines_itself(
    project, invoke, flags: list[str], key: str, expected: object
) -> None:
    await _make(invoke, "item")

    result = await invoke(["role", "sre", "update", *flags])

    assert result.exit_code == 0, result.output
    assert _front(project, "sre")[key] == expected


@pytest.mark.parametrize("kind", ["catalog", "template"])
@pytest.mark.parametrize(
    ("flags", "flag_name"),
    [([*r[1]], r[1][0]) for r in DEFINITION] + [(["--file", "delta.toml"], "--file")],
    ids=[r[0] for r in DEFINITION] + ["file"],
)
async def test_a_definition_flag_is_refused_on_a_catalog_or_template_role_naming_the_file(
    project, invoke, kind: str, flags: list[str], flag_name: str
) -> None:
    slug = await _make(invoke, kind)
    if "--file" in flags:
        (project.root / "delta.toml").write_text('mission = "x"\n', encoding="utf-8")
        flags = ["--file", str(project.root / "delta.toml")]
    before = _tree(project)

    result = await invoke(["role", slug, "update", *flags])

    assert result.exit_code == 1, result.output
    message = " ".join(result.output.split())
    assert flag_name in message
    assert f".overrides/roles/{slug}.toml" in message
    assert f"sq override scaffold --role {slug}" in message
    if kind == "template":
        assert "[templates.dev] of .overrides/roles.toml" in message
    else:
        assert "comes from the role catalog" in message
    assert _tree(project) == before


async def test_a_refused_definition_flag_beside_an_accepted_one_writes_nothing(
    project, invoke
) -> None:
    await _make(invoke, "catalog")
    before = _tree(project)

    result = await invoke(["role", "architect", "update", "--title", "New Name", "--mission", "x"])

    assert result.exit_code == 1, result.output
    assert _tree(project) == before


# ------------------------------------------------------------------------- --file deltas


async def test_a_file_delta_edits_fields_and_the_append_idiom_resolves_against_the_item(
    project, invoke
) -> None:
    assert (await invoke(["role", "add", "sre", *_ADD, "--capabilities", "ops"])).exit_code == 0
    assert (await invoke(["role", "sre", "update", "--capabilities", "ops,pager"])).exit_code == 0
    delta = project.root / "delta.toml"
    delta.write_text(
        'mission = "Own uptime."\nresponsibilities = ["First"]\n'
        'capabilities = ["$(*self)", "oncall"]\n',
        encoding="utf-8",
    )

    result = await invoke(["role", "sre", "update", "--file", str(delta)])

    assert result.exit_code == 0, result.output
    front = _front(project, "sre")
    assert front["mission"] == "Own uptime."
    assert front["responsibilities"] == ["First"]
    assert front["capabilities"] == ["ops", "pager", "oncall"]
    assert front["job_title"] == "SRE"  # a field the delta does not name is kept
    assert front["title"] == "Sam Sre"


#: (id, delta body, fragments the refusal carries)
REFUSED_KEYS = [
    ("slug", 'slug = "other"\n', ["slug", "update --title", "set-default"]),
    ("full-name", 'full_name = "Other"\n', ["full_name", "update --title"]),
    ("is-default", "is_default = true\n", ["is_default", "set-default"]),
    ("tech", 'tech = "rust"\n', ["tech"]),
    ("template", 'template = "dev"\n', ["template"]),
    ("pronouns", 'pronouns = "she/her"\n', ["pronouns", "--pronouns"]),
    ("unknown-key", 'flavour = "x"\n', ["flavour"]),
    ("bad-model", 'model = "opuss"\n', ["model 'opuss'"]),
]


@pytest.mark.parametrize(
    ("body", "fragments"), [r[1:] for r in REFUSED_KEYS], ids=[r[0] for r in REFUSED_KEYS]
)
async def test_a_file_delta_naming_an_identity_or_base_key_is_refused_and_writes_nothing(
    project, invoke, body: str, fragments: list[str]
) -> None:
    await _make(invoke, "item")
    delta = project.root / "delta.toml"
    delta.write_text(body, encoding="utf-8")
    before = _tree(project)

    result = await invoke(["role", "sre", "update", "--file", str(delta)])

    assert result.exit_code == 1, result.output
    for fragment in fragments:
        assert fragment in result.output
    assert _tree(project) == before


@pytest.mark.parametrize("flag", ["--tech", "--template"])
async def test_tech_and_template_are_not_updatable(project, invoke, flag: str) -> None:
    slug = await _make(invoke, "template")
    before = _tree(project)

    result = await invoke(["role", slug, "update", flag, "go"])

    assert result.exit_code == 2, result.output
    assert _tree(project) == before


# ------------------------------------------------------------------------ nothing to update


async def test_an_update_naming_no_field_exits_1_and_writes_nothing(project, invoke) -> None:
    await _make(invoke, "item")
    before = _tree(project)

    result = await invoke(["role", "sre", "update"])

    assert result.exit_code == 1, result.output
    assert "nothing to update" in result.output
    assert _tree(project) == before


# ------------------------------------------------------------------- the shadowing warning


async def test_a_write_to_a_field_a_per_slug_file_also_sets_still_happens_and_warns(
    project, invoke
) -> None:
    await _make(invoke, "item")
    file = project.squad_dir / ".overrides" / "roles" / "sre.toml"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text('mission = "From the file."\ncolor = "teal"\n', encoding="utf-8")

    result = await invoke(
        ["role", "sre", "update", "--mission", "From the item.", "--desc", "New."]
    )

    assert result.exit_code == 0, result.output
    assert _front(project, "sre")["mission"] == "From the item."
    message = " ".join(result.output.split())
    assert ".overrides/roles/sre.toml also sets mission" in message
    assert "the file wins" in message
    assert "description" not in message.split("also sets")[1].split(":")[0]
    shown = json.loads((await invoke(["role", "sre", "show", "--json"])).output)
    assert shown["mission"] == "From the file."


# ----------------------------------------------------------------- an orphan made item-defined


async def _orphan(svc) -> None:
    await svc.create("role", "Gwen Ghost", description="A ghost.", slug="ghost", author="ghost")


async def test_job_title_desc_and_mission_together_make_an_orphan_role_define_itself(
    project, svc, invoke
) -> None:
    await _orphan(svc)

    result = await invoke(
        [
            *["role", "ghost", "update", "--job-title", "Haunter"],
            "--desc",
            "Haunts.",
            "--mission",
            "Haunt.",
        ]
    )

    assert result.exit_code == 0, result.output
    front = _front(project, "ghost")
    assert (front["job_title"], front["mission"], front["description"]) == (
        "Haunter",
        "Haunt.",
        "Haunts.",
    )
    shown = await invoke(["role", "ghost", "show"])
    assert "could not be resolved" not in shown.output


@pytest.mark.parametrize(
    "flags", [["--mission", "Haunt."], ["--job-title", "H", "--desc", "d"]], ids=["mission", "two"]
)
async def test_an_orphan_needs_all_three_to_define_itself(project, svc, invoke, flags) -> None:
    await _orphan(svc)
    before = _tree(project)

    result = await invoke(["role", "ghost", "update", *flags])

    assert result.exit_code == 1, result.output
    assert "missing required fields" in result.output
    assert _tree(project) == before


# --------------------------------------------------------------------------------- import


async def test_an_import_setting_a_definition_field_is_refused_on_the_same_terms(
    project, invoke, tmp_path: Path
) -> None:
    await _make(invoke, "item")
    target = json.loads((await invoke(["role", "sre", "show", "--json"])).output)["id"]
    events = tmp_path / "events.jsonl"
    events.write_text(
        json.dumps(
            {"op": "update", "target": target, "as": "manager", "fields": {"mission": "Sneaky."}}
        )
        + "\n",
        encoding="utf-8",
    )
    before = _tree(project)

    result = await invoke(["import", str(events)])

    assert result.exit_code == 1, result.output
    assert "authoring surface" in result.output
    assert _tree(project) == before


# ------------------------------------------------------------------ clearing a definition key

#: (id, set flags, clear flags, key that leaves the frontmatter)
CLEARING = [
    ("color", ["--color", "teal"], ["--color", ""], "color"),
    ("capabilities", ["--capabilities", "ops"], ["--capabilities", ""], "capabilities"),
    ("can-spawn", ["--can-spawn", "yes"], ["--can-spawn", "no"], "can_spawn"),
]


@pytest.mark.parametrize(
    ("set_flags", "clear_flags", "key"), [r[1:] for r in CLEARING], ids=[r[0] for r in CLEARING]
)
async def test_a_definition_key_set_then_cleared_leaves_the_frontmatter_and_the_pointer(
    project, invoke, set_flags: list[str], clear_flags: list[str], key: str
) -> None:
    await _make(invoke, "item")
    assert (await invoke(["role", "sre", "update", *set_flags])).exit_code == 0
    assert key in _front(project, "sre")
    pointer = (project.root / ".claude" / "agents" / "sre.md").read_text(encoding="utf-8")

    result = await invoke(["role", "sre", "update", *clear_flags])

    assert result.exit_code == 0, result.output
    assert key not in _front(project, "sre")
    after = (project.root / ".claude" / "agents" / "sre.md").read_text(encoding="utf-8")
    assert after != pointer or key == "capabilities"


# ------------------------------------------------------- origin follows the base after update


async def test_an_orphan_made_self_defining_takes_the_project_origin(project, svc, invoke) -> None:
    await svc.create(
        "role",
        "Gwen Ghost",
        description="A ghost.",
        slug="ghost",
        author="ghost",
        attributes={"origin": "system"},
    )
    assert _front(project, "ghost")["origin"] == "system"

    result = await invoke(
        [*["role", "ghost", "update", "--job-title", "Haunter"], "--desc", "H.", "--mission", "M."]
    )

    assert result.exit_code == 0, result.output
    assert _front(project, "ghost")["origin"] == "project"


# ---------------------------------------------------- hints that depend on the base resolving


async def test_a_deselected_bundled_role_is_not_sent_to_a_per_slug_scaffold(
    project, invoke
) -> None:
    assert (await invoke(["role", "activate", "devops"])).exit_code == 0
    path = project.squad_dir / ".overrides" / "roles.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '[selected]\nroles = ["manager", "architect", "tech-lead", "reviewer", "qa", '
        '"product-owner", "tech-writer"]\n\n[bundles]\nall = ["manager", "architect", '
        '"tech-lead", "reviewer", "qa", "product-owner", "tech-writer"]\n',
        encoding="utf-8",
    )

    result = await invoke(["role", "devops", "show"])

    tail = " ".join(result.output.split())
    assert "could not be resolved" in tail
    assert "Nothing backs its definition" in tail
    assert "sq override scaffold --role devops" not in tail


async def test_the_title_of_a_role_is_refused_as_a_generic_attribute_with_the_update_verb(
    project, invoke
) -> None:
    from squads._models._metadata import require_settable

    with pytest.raises(SquadsError, match="update --title"):
        require_settable("role", "title", {})


# ------------------------------------------------------------ an unrenderable stored model


async def test_a_stored_model_that_is_not_a_known_model_is_reported_and_read_as_unset(
    project, invoke
) -> None:
    assert (await invoke(["role", "activate", "reviewer"])).exit_code == 0
    path = next((project.squad_dir / "agents" / "roles").glob("*-reviewer.md"))
    path.write_text(
        path.read_text(encoding="utf-8").replace("\norigin:", "\nmodel: gpt-5\norigin:", 1),
        encoding="utf-8",
    )
    assert (await invoke(["repair"])).exit_code == 0

    shown = json.loads((await invoke(["role", "reviewer", "show", "--json"])).output)
    checked = await invoke(["check"])

    assert shown["model"] == "opus"
    assert checked.exit_code == 3, checked.output
    assert "attribute 'model'" in checked.output and "gpt-5" in checked.output


async def test_a_hand_written_unknown_model_on_a_role_that_defines_itself_reads_as_unset(
    project, invoke
) -> None:
    await _make(invoke, "item")
    path = next((project.squad_dir / "agents" / "roles").glob("*-sre.md"))
    path.write_text(
        path.read_text(encoding="utf-8").replace("\norigin:", "\nmodel: gpt-5\norigin:", 1),
        encoding="utf-8",
    )
    assert (await invoke(["repair"])).exit_code == 0

    shown = json.loads((await invoke(["role", "sre", "show", "--json"])).output)
    checked = await invoke(["check"])

    assert shown["model"] is None
    assert "gpt-5" in checked.output
