"""`sq role …`: the catalog, activating and adding roles, and the addressed verbs (show, update,
status, set-default, regen, remove, body, views and the comment listing)."""

from pathlib import Path
from typing import Any

import pytest

from tests._profile import selected
from tests.cli._output import entry_text, json_text, printed, read_json
from tests.cli._roster import actors_of, body_of, forced_terminal, usage_error

P = selected()

pytestmark = pytest.mark.anyio

SCOUT = [
    "--name",
    "Sam Scout",
    "--job-title",
    "Scout",
    "--desc",
    "Scouts ahead",
    "--mission",
    "Find things",
]
VIEW_REFUSAL = (
    "error: ROLE-2's body renders through its declared sq:view:role_definition tag, and its "
    "content already has one validated authoring surface: `.overrides/roles.toml` (or "
    "`.overrides/roles/<slug>.toml`), or `sq role scout update` for a role that defines "
    "itself. A view edit is refused — `--force` does not lift this. To add prose beside the "
    "definition, use `sq role scout body`. To replace the generated definition itself, drop "
    "the view from `[selected]`, then clear its leftover tag with `sq role scout view disable "
    "role_definition`.\n"
)


async def _add_scout(invoke, *extra: str) -> None:
    result = await invoke(["role", "add", "scout", *SCOUT, *extra])
    assert result.exit_code == 0, result.output


async def _activate(invoke, slug: str = "architect", *extra: str) -> None:
    result = await invoke(["role", "activate", slug, *extra])
    assert result.exit_code == 0, result.output


#: The definition `role add scout` with the `SCOUT` flags renders, as `show --json` prints it.
SCOUT_BODY = (
    "# Sam Scout\n"
    "\n"
    "**Role:** Scout  ·  **Slug:** `scout`\n"
    "\n"
    "## Mission\n"
    "\n"
    "Find things\n"
    "\n"
    "## Working agreements\n"
    "\n"
    "Operate as **Sam Scout** for the duration of the conversation.\n"
    "Track all work with the `sq` CLI; never alter the `<!-- sq:* -->` marker lines.\n"
    "The `.md` files are sq-managed — read them through `sq <type> <n> show`, never "
    "by opening the file.\n"
    "For your part on each item type, follow your `sq-<type>` skill's **For Sam "
    "Scout**\n"
    "section — it tells you what to check, do, and hand off.\n"
    "When commenting, scope to the right discussion: `sq <type> <n> <kind> <k> "
    "comment` for sub-entity-scoped\n"
    "notes, `sq <type> <n> comment` for cross-cutting material — see the `squads` "
    "skill's **comment-scoping\n"
    "convention** for the full rule and examples. Correct or withdraw your own "
    "comment by its hash:\n"
    "`sq <type> <n> [<kind> <k>] comment <hash> show|edit|remove`; if a hash stops "
    "resolving, read the\n"
    "discussion again.\n"
    "\n"
    "### Spawned as a subagent\n"
    "\n"
    "You were invoked to do a specific, scoped job. Your chat does not survive past "
    "this invocation, so\n"
    "the record you leave in `sq` is the only thing the loop has.\n"
    "\n"
    "- Skip the greeting — go straight to the work.\n"
    "- Keep each item's **status** current as you go.\n"
    "- Before you return, leave the **full record**:\n"
    '  - `sq <type> <n> comment --as scout -m "…"` summarising what changed\n'
    "    (repeat `-m` for separate points);\n"
    "  - `@mention` the next role that needs to act — this is your handoff, because "
    "the chat will not\n"
    "    survive.\n"
    "\n"
    "### Live with the operator\n"
    "\n"
    "A human has opened a session directly with you. Follow the `greeting` skill, "
    "then follow the\n"
    "`squads` skill's **Working directly with the operator** section throughout. "
    "Beyond those, apply the\n"
    "shared principle:\n"
    "\n"
    "**Record what the next reader needs, when it becomes true.**\n"
    "\n"
    "- **Decisions** go on the record when they are made — attribute with `--as` "
    "immediately.\n"
    "- **Handoffs** (`@mention`) only when work actually moves to that role. Never "
    "signal a handoff for\n"
    "  work nobody has greenlit — a mention is a real call-to-action, not ceremony.\n"
    "- Keep status honest: move an item to its lifecycle's first working state when "
    "you actually\n"
    "  start (`sq <type> <n> update --status <status>`; see `sq <type> <n> show` for "
    "the current\n"
    "  one and `sq workflow` for the full lifecycle), not before."
)


#: The pointer `role add scout` writes for the role.
SCOUT_POINTER = (
    "---\n"
    "name: scout\n"
    'description: "Scouts ahead"\n'
    "disallowedTools: Agent\n"
    "skills:\n"
    "  - squads\n"
    "  - greeting\n"
    "  - sq-memory\n"
    "---\n"
    "\n"
    "You are **Sam Scout**, the Scout on this project.\n"
    "\n"
    "Load your full role definition:\n"
    "\n"
    "`sq role scout show`\n"
    "\n"
    "Then, at the start of a run:\n"
    "- `sq memory scout list`\n"
    "- `sq memory scout show <slug>`\n"
    "- `sq board list`\n"
    "- `sq mine scout`\n"
    "- `sq inbox scout`\n"
    "\n"
    "Operate as **Sam Scout** for the rest of the conversation. Track all work with "
    "the `sq`\n"
    "CLI and follow the squads process described in `CLAUDE.md`. Never edit the "
    "`<!-- sq:* -->`\n"
    "marker lines in managed files.\n"
    "\n"
    "This pointer file itself is regenerated by `sq sync` — hand-edits here are "
    "overwritten on the\n"
    "next sync; run `sq role scout show` for the current definition instead.\n"
)


async def _role(invoke, address: str) -> dict[str, Any]:
    return await read_json(invoke, ["role", address, "show", "--json"])


async def _roles(invoke) -> dict[str, dict[str, Any]]:
    return {r["slug"]: r for r in await read_json(invoke, ["role", "list", "--json"])}


def _claude_md(project) -> list[str]:
    """The lines of the managed CLAUDE.md, where the roster is listed."""
    return (project.root / "CLAUDE.md").read_text(encoding="utf-8").splitlines()


def _pointer(project, slug: str):
    return project.root / ".claude" / "agents" / f"{slug}.md"


# ---------------------------------------------------------------------------------- catalog


@pytest.mark.covers("role catalog", "--json")
async def test_catalog_json_lists_the_catalog_with_the_roster_default_marked(
    project, invoke
) -> None:
    rows = await read_json(invoke, ["role", "catalog", "--json"])
    assert [r["slug"] for r in rows] == [
        "manager",
        "architect",
        "tech-lead",
        "reviewer",
        "qa",
        "devops",
        "product-owner",
        "tech-writer",
    ]
    assert rows[0] == {
        "slug": "manager",
        "full_name": "Catherine Manager",
        "title": "manager",
        "is_default": True,
        "origin": "system",
        "capabilities": [],
        "default_role": "manager",
        "default_role_source": "roster",
    }
    assert [r["is_default"] for r in rows[1:]] == [False] * 7


@pytest.mark.covers("role catalog", "--json")
async def test_catalog_json_outside_a_squad_marks_the_catalogs_own_default(invoke) -> None:
    rows = await read_json(invoke, ["role", "catalog", "--json"])
    assert {(r["default_role"], r["default_role_source"]) for r in rows} == {("manager", "catalog")}
    assert [r["slug"] for r in rows if r["is_default"]] == ["manager"]


# ------------------------------------------------------------------------------------ list


@pytest.mark.covers("role list", "--json")
async def test_list_json_describes_each_activated_role(project, invoke) -> None:
    await _activate(invoke, "architect", "--name", "Robert", "--pronouns", "he/him")
    assert await read_json(invoke, ["role", "list", "--json"]) == [
        {
            "id": "ROLE-1",
            "slug": "manager",
            "full_name": "Catherine Manager",
            "pronouns": None,
            "title": "manager",
            "description": "Default agent: triages the operator's request and routes it to the "
            "right specialist.",
            "is_default": True,
            "capabilities": [],
            "status": "Active",
            "origin": "system",
            "display": {"name": "Catherine Manager", "pronouns": None, "live": True},
        },
        {
            "id": "ROLE-2",
            "slug": "architect",
            "full_name": "Robert",
            "pronouns": "he/him",
            "title": "architect",
            "description": "System design and architecture decisions (ADRs).",
            "is_default": False,
            "capabilities": [],
            "status": "Active",
            "origin": "system",
            "display": {"name": "Robert (he/him)", "pronouns": "he/him", "live": True},
        },
    ]


# ------------------------------------------------------------------------------- activate


@pytest.mark.covers("role activate", "slug")
@pytest.mark.bundled_only("activates a catalog role whose text names the bundled workflow")
async def test_activate_adds_a_catalog_role_and_writes_its_pointer(project, invoke) -> None:
    result = await invoke(["role", "activate", "architect"])
    assert (result.exit_code, result.output) == (
        0,
        "activated Robert Architect (`architect`) ROLE-2\n",
    )
    assert (await _roles(invoke))["architect"]["id"] == "ROLE-2"
    head = _pointer(project, "architect").read_text(encoding="utf-8").split("\n---\n")[0]
    assert head.splitlines() == [
        "---",
        "name: architect",
        'description: "System design and architecture decisions (ADRs)."',
        "model: opus",
        "color: blue",
        "disallowedTools: Agent",
        "skills:",
        "  - squads",
        "  - greeting",
        "  - sq-memory",
        "  - sq-epic",
        "  - sq-decision",
        "  - sq-contract",
        "  - sq-guide",
    ]


@pytest.mark.covers("role activate", "slug")
async def test_activate_refuses_a_slug_the_catalog_does_not_declare(project, invoke) -> None:
    result = await invoke(["role", "activate", "nosuch"])
    assert (result.exit_code, result.output) == (
        1,
        "error: no role 'nosuch': the catalog does not declare it (known: manager, architect, "
        "tech-lead, reviewer, qa, devops, product-owner, tech-writer)\n",
    )


@pytest.mark.covers("role activate")
async def test_activate_needs_a_slug_when_no_template_is_given(project, invoke) -> None:
    result = await invoke(["role", "activate"])
    assert (result.exit_code, result.output) == (
        1,
        "error: name the role to activate: `sq role activate <slug>`\n",
    )


@pytest.mark.covers("role activate", "--name")
async def test_activate_name_replaces_the_catalogs_full_name(project, invoke) -> None:
    result = await invoke(["role", "activate", "architect", "--name", "Robert"])
    assert (result.exit_code, result.output) == (0, "activated Robert (`architect`) ROLE-2\n")
    assert (await _role(invoke, "architect"))["full_name"] == "Robert"


@pytest.mark.covers("role activate", "--pronouns")
async def test_activate_pronouns_are_stored_on_the_role(project, invoke) -> None:
    result = await invoke(["role", "activate", "architect", "--pronouns", "he/him"])
    assert (result.exit_code, result.output) == (
        0,
        "activated Robert Architect (he/him) (`architect`) ROLE-2\n",
    )
    assert (await _role(invoke, "architect"))["pronouns"] == "he/him"


@pytest.mark.covers("role activate", "--model")
async def test_activate_model_replaces_the_catalogs_model(project, invoke) -> None:
    await _activate(invoke, "architect", "--model", "haiku")
    assert (await _role(invoke, "architect"))["model"] == "haiku"
    assert "model: haiku\n" in _pointer(project, "architect").read_text(encoding="utf-8")


@pytest.mark.covers("role activate", "--from", "--tech")
async def test_activate_from_a_template_builds_a_role_for_the_technology(project, invoke) -> None:
    result = await invoke(["role", "activate", "--from", "dev", "--tech", "python"])
    assert (result.exit_code, result.output) == (0, "added Elias Python (`python-dev`) ROLE-2\n")
    shown = await _role(invoke, "python-dev")
    assert (shown["full_name"], shown["title"], shown["capabilities"]) == (
        "Elias Python",
        "Python developer",
        ["dev"],
    )


@pytest.mark.covers("role activate", "--from")
async def test_activate_from_a_template_files_the_role_under_the_given_slug(
    project, invoke
) -> None:
    result = await invoke(
        ["role", "activate", "snake", "--from", "dev", "--tech", "python", "--name", "Sam Snake"]
    )
    assert (result.exit_code, result.output) == (0, "added Sam Snake (`snake`) ROLE-2\n")
    assert (await _role(invoke, "snake"))["full_name"] == "Sam Snake"


@pytest.mark.covers("role activate", "--from")
async def test_activate_from_refuses_a_template_the_catalog_does_not_declare(
    project, invoke
) -> None:
    result = await invoke(["role", "activate", "--from", "nosuch", "--tech", "python"])
    assert (result.exit_code, result.output) == (
        1,
        "error: no role template 'nosuch'; the declared templates are: dev\n",
    )


@pytest.mark.covers("role activate", "--from")
async def test_activate_from_a_template_that_takes_a_technology_needs_tech(project, invoke) -> None:
    result = await invoke(["role", "activate", "--from", "dev"])
    assert (result.exit_code, result.output) == (
        1,
        "error: role template 'dev' takes a technology: pass --tech\n",
    )


@pytest.mark.covers("role activate", "--tech")
async def test_activate_tech_is_refused_without_a_template(project, invoke) -> None:
    result = await invoke(["role", "activate", "architect", "--tech", "go"])
    assert (result.exit_code, result.output) == (
        1,
        "error: --tech applies to a role built with --from <template>\n",
    )


@pytest.mark.covers("role activate", "--from")
async def test_activate_from_refuses_a_slug_the_catalog_declares(project, invoke) -> None:
    result = await invoke(["role", "activate", "architect", "--from", "dev", "--tech", "go"])
    assert (result.exit_code, result.output) == (
        1,
        "error: slug 'architect' belongs to a role the catalog declares; `sq role activate "
        "architect` activates it, or pick another slug\n",
    )


@pytest.mark.covers("role activate", "--as")
async def test_activate_as_attributes_the_creation_to_the_actor(project, invoke) -> None:
    await _activate(invoke, "architect", "--as", "manager")
    assert await actors_of(invoke, "ROLE-2", "create") == ["manager"]


@pytest.mark.covers("role activate", "--as")
async def test_activate_as_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    result = await invoke(["role", "activate", "architect", "--as", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: manager\n",
    )


# ---------------------------------------------------------------------------------- add


@pytest.mark.covers("role add", "slug")
@pytest.mark.covers("role add", "--name")
@pytest.mark.covers("role add", "--job-title")
@pytest.mark.covers("role add", "--desc")
@pytest.mark.covers("role add", "--mission")
async def test_add_creates_a_role_that_defines_itself(project, invoke) -> None:
    result = await invoke(["role", "add", "scout", *SCOUT])
    assert (result.exit_code, result.output) == (0, "added Sam Scout (`scout`) ROLE-2\n")
    assert await _role(invoke, "scout") == {
        "slug": "scout",
        "id": "ROLE-2",
        "activated": True,
        "origin": "project",
        "full_name": "Sam Scout",
        "pronouns": None,
        "title": "Scout",
        "mission": "Find things",
        "model": None,
        "is_default": False,
        "can_spawn": False,
        "capabilities": [],
        "create_lane": [],
        "responsibilities": [],
        "skills": ["squads", "greeting", "sq-memory"],
        "display": {
            "name": "Sam Scout",
            "pronouns": None,
            "color": None,
            "body": SCOUT_BODY,
            "empty_hint": (
                "(empty — run `sq sync`; if it stays empty, declare the definition in "
                "`.overrides/roles.toml`, or `.overrides/roles/<slug>.toml`, or run "
                "`sq role scout view add role_definition`)"
            ),
            "definition_resolves": True,
            "change_hint": (
                "To change its definition: `sq role scout update --mission …` (or --file)."
            ),
            "discussion": [],
        },
    }
    assert (await _roles(invoke))["scout"]["description"] == "Scouts ahead"
    assert _pointer(project, "scout").read_text(encoding="utf-8") == SCOUT_POINTER


@pytest.mark.covers("role add", "--name")
@pytest.mark.covers("role add", "--job-title")
@pytest.mark.covers("role add", "--desc")
@pytest.mark.covers("role add", "--mission")
async def test_add_names_every_required_field_it_is_missing(project, invoke) -> None:
    result = await invoke(["role", "add", "scout"])
    assert (result.exit_code, result.output) == (
        1,
        "error: role 'scout' is missing required fields: --name (full_name), --job-title "
        "(title), --desc (description), --mission (mission); pass the flags, or a --file that "
        "sets them\n",
    )


@pytest.mark.covers("role add", "--mission")
async def test_add_names_the_one_field_it_is_missing(project, invoke) -> None:
    result = await invoke(
        ["role", "add", "scout", "--name", "Sam", "--job-title", "Scout", "--desc", "d"]
    )
    assert (result.exit_code, result.output) == (
        1,
        "error: role 'scout' is missing required fields: --mission (mission); pass the flags, "
        "or a --file that sets them\n",
    )


@pytest.mark.covers("role add", "slug")
async def test_add_refuses_a_slug_a_role_already_has(project, invoke) -> None:
    await _add_scout(invoke)
    result = await invoke(["role", "add", "scout", *SCOUT])
    assert (result.exit_code, result.output) == (
        1,
        "error: a role with slug 'scout' already exists\n",
    )


@pytest.mark.covers("role add", "slug")
async def test_add_needs_a_slug(project, invoke) -> None:
    result = await invoke(["role", "add"])
    assert (result.exit_code, result.output) == (
        2,
        usage_error(
            "Usage: sq role add [OPTIONS] {slug}",
            "sq role add --help",
            "Missing argument 'slug'.",
        ),
    )


@pytest.mark.covers("role add", "--capabilities")
async def test_add_capabilities_are_split_on_commas_and_trimmed(project, invoke) -> None:
    await _add_scout(invoke, "--capabilities", f"{P.third}, , dev")
    assert (await _role(invoke, "scout"))["capabilities"] == [P.third, "dev"]


@pytest.mark.covers("role add", "--model")
async def test_add_model_is_stored_on_the_role(project, invoke) -> None:
    await _add_scout(invoke, "--model", "haiku")
    assert (await _role(invoke, "scout"))["model"] == "haiku"


@pytest.mark.covers("role add", "--pronouns")
async def test_add_pronouns_are_stored_on_the_role(project, invoke) -> None:
    result = await invoke(["role", "add", "scout", *SCOUT, "--pronouns", "she/her"])
    assert (result.exit_code, result.output) == (
        0,
        "added Sam Scout (she/her) (`scout`) ROLE-2\n",
    )
    assert (await _role(invoke, "scout"))["pronouns"] == "she/her"


@pytest.mark.covers("role add", "--file")
async def test_add_file_supplies_the_definition(project, invoke, tmp_path) -> None:
    definition = tmp_path / "scout.toml"
    definition.write_text(
        'full_name = "Sam Scout"\ntitle = "Scout"\ndescription = "Scouts ahead"\n'
        'mission = "Find things"\nresponsibilities = ["Scout ahead", "Report back"]\n',
        encoding="utf-8",
    )
    result = await invoke(["role", "add", "scout", "--file", str(definition)])
    assert (result.exit_code, result.output) == (0, "added Sam Scout (`scout`) ROLE-2\n")
    assert (await _role(invoke, "scout"))["responsibilities"] == ["Scout ahead", "Report back"]


SCOUT_TOML = 'full_name = "{name}"\ntitle = "Scout"\ndescription = "d"\nmission = "m"\n'


def _write_scout(name: str, full_name: str = "", raw: bytes | None = None) -> None:
    path = Path(name)
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(raw if raw is not None else SCOUT_TOML.format(name=full_name).encode())


@pytest.mark.covers("role add", "--file")
async def test_add_file_is_read_under_the_directory_chosen_with_c(project, invoke) -> None:
    _write_scout("sub/scout.toml", "Sam Scout")
    _write_scout("scout.toml", "Decoy")
    result = await invoke(["-C", "sub", "role", "add", "scout", "--file", "scout.toml"])
    assert (result.exit_code, result.output) == (0, "added Sam Scout (`scout`) ROLE-2\n")
    assert (await _role(invoke, "scout"))["full_name"] == "Sam Scout"


@pytest.mark.covers("role add", "--file")
async def test_add_file_dash_reads_the_definition_from_standard_input(project, invoke) -> None:
    result = await invoke(
        ["role", "add", "scout", "--file", "-"], input=SCOUT_TOML.format(name="Sam Scout")
    )
    assert (result.exit_code, result.output) == (0, "added Sam Scout (`scout`) ROLE-2\n")
    assert (await _role(invoke, "scout"))["full_name"] == "Sam Scout"


@pytest.mark.covers("role add", "--file")
async def test_add_file_refuses_a_file_that_is_not_utf8(project, invoke) -> None:
    _write_scout("bad.toml", raw=b"full_name = \xff\xfe")
    result = await invoke(["role", "add", "scout", "--file", "bad.toml"])
    assert (result.exit_code, result.output) == (
        1,
        "error: cannot read role file 'bad.toml': "
        "not valid utf-8 (invalid start byte at byte 12)\n",
    )


@pytest.mark.covers("role add", "--file", "--name")
async def test_add_flags_win_over_the_file(project, invoke, tmp_path) -> None:
    definition = tmp_path / "scout.toml"
    definition.write_text(
        'full_name = "Sam Scout"\ntitle = "Scout"\ndescription = "d"\nmission = "m"\n',
        encoding="utf-8",
    )
    result = await invoke(["role", "add", "scout", "--file", str(definition), "--name", "Flag"])
    assert result.exit_code == 0, result.output
    assert (await _role(invoke, "scout"))["full_name"] == "Flag"


@pytest.mark.covers("role add", "--file")
async def test_add_file_refuses_a_path_that_cannot_be_read(project, invoke, tmp_path) -> None:
    missing = tmp_path / "missing.toml"
    result = await invoke(["role", "add", "scout", "--file", str(missing)])
    assert (result.exit_code, result.output) == (
        1,
        f"error: cannot read role file {str(missing)!r}: No such file or directory\n",
    )


@pytest.mark.covers("role add", "--file")
async def test_add_file_refuses_toml_that_does_not_parse(project, invoke, tmp_path) -> None:
    broken = tmp_path / "broken.toml"
    broken.write_text("full_name = \n", encoding="utf-8")
    result = await invoke(["role", "add", "scout", "--file", str(broken)])
    assert (result.exit_code, result.output) == (
        1,
        f"error: malformed role override {broken}: Invalid value (at line 1, column 13)\n",
    )


@pytest.mark.covers("role add", "--as")
async def test_add_as_attributes_the_creation_to_the_actor(project, invoke) -> None:
    await _add_scout(invoke, "--as", "manager")
    assert await actors_of(invoke, "ROLE-2", "create") == ["manager"]


@pytest.mark.covers("role add", "--as")
async def test_add_as_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    result = await invoke(["role", "add", "scout", *SCOUT, "--as", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: manager\n",
    )


# --------------------------------------------------------------------------------- address


@pytest.mark.covers("role", "<slug|id|n>")
async def test_address_resolves_a_slug_an_id_and_a_number_to_the_same_role(project, invoke) -> None:
    await _activate(invoke)
    by_slug = await _role(invoke, "architect")
    assert by_slug["id"] == "ROLE-2"
    assert await _role(invoke, "ROLE-2") == by_slug
    assert await _role(invoke, "2") == by_slug


@pytest.mark.covers("role", "<slug|id|n>")
async def test_address_refuses_a_number_no_role_has(project, invoke) -> None:
    result = await invoke(["role", "99", "show"])
    assert (result.exit_code, result.output) == (
        1,
        "error: no item with number 99 (use ROLE-99 or bare 99)\n",
    )


@pytest.mark.covers("role", "<slug|id|n>")
async def test_address_refuses_the_number_of_an_item_that_is_not_a_role(
    populated_project, invoke
) -> None:
    result = await invoke(["role", "3", "show"])
    assert (result.exit_code, result.output) == (
        1,
        f"error: 3 is {P.ref_prefix}-3 ({P.ref}), not of type role\n",
    )


# ----------------------------------------------------------------------------------- show


@pytest.mark.covers("role show", "--json")
async def test_show_json_of_a_catalog_role_that_is_not_activated_says_so(project, invoke) -> None:
    card = await _role(invoke, "architect")
    assert (card["slug"], card["id"], card["activated"], card["full_name"]) == (
        "architect",
        None,
        False,
        "Robert Architect",
    )


@pytest.mark.covers("role show", "--json")
async def test_show_refuses_a_slug_no_role_has_and_the_catalog_does_not_declare(
    project, invoke
) -> None:
    result = await invoke(["role", "nobody", "show", "--json"])
    assert (result.exit_code, result.output) == (
        1,
        "error: no role with slug, ID, or number 'nobody'\n",
    )


@pytest.mark.covers("role show", "--raw")
async def test_show_raw_prints_the_body_unrendered_where_a_terminal_would_render_it(
    project, invoke, monkeypatch
) -> None:
    await _add_scout(invoke)
    piped = await invoke(["role", "scout", "show"])
    forced_terminal(monkeypatch)
    raw = await invoke(["role", "scout", "show", "--raw"])
    rendered = await invoke(["role", "scout", "show"])
    assert (raw.exit_code, raw.output) == (0, piped.output)
    assert rendered.output != piped.output


@pytest.mark.covers("role show", "--comments")
async def test_show_comments_appends_the_discussion_before_the_closing_hint(
    project, invoke
) -> None:
    await _add_scout(invoke)
    await invoke(["role", "scout", "comment", "-m", "Welcome.", "--as", "manager"])
    without = await invoke(["role", "scout", "show"])
    listed = (await read_json(invoke, ["role", "scout", "comments", "--json"]))[0]
    with_comments = await invoke(["role", "scout", "show", "--comments"])
    block = (
        f"--- {listed['short_hash']} [{listed['ts']}] Catherine Manager (manager) ---\n"
        "- Welcome.\n\n"
    )
    hint = "To change its definition: `sq role scout update --mission …` (or --file).\n"
    assert (with_comments.exit_code, with_comments.output) == (
        0,
        without.output.replace(f"\n{hint}", f"{block}\n{hint}"),
    )


# ----------------------------------------------------------------------------------- body


async def _scout_body(invoke) -> str:
    return await body_of(invoke, 2)


@pytest.mark.covers("role body", "--message")
async def test_body_message_sets_the_prose_after_the_definition_view(project, invoke) -> None:
    await _add_scout(invoke)
    result = await invoke(["role", "scout", "body", "-m", "Hello.", "-m", "World."])
    assert (result.exit_code, result.output) == (0, "ROLE-2: body set\n")
    assert await _scout_body(invoke) == "<!-- sq:view:role_definition -->\n\nHello.\n\nWorld."


@pytest.mark.covers("role body", "--append")
async def test_body_append_adds_to_what_is_there(project, invoke) -> None:
    await _add_scout(invoke)
    await invoke(["role", "scout", "body", "-m", "Hello."])
    result = await invoke(["role", "scout", "body", "-m", "More.", "--append"])
    assert (result.exit_code, result.output) == (0, "ROLE-2: body appended\n")
    assert await _scout_body(invoke) == "<!-- sq:view:role_definition -->\n\nHello.\n\nMore."


@pytest.mark.covers("role body", "--force")
async def test_body_force_replaces_a_body_someone_wrote(project, invoke) -> None:
    await _add_scout(invoke)
    await invoke(["role", "scout", "body", "-m", "Hello."])
    result = await invoke(["role", "scout", "body", "-m", "Again.", "--force"])
    assert (result.exit_code, result.output) == (0, "ROLE-2: body set\n")
    assert await _scout_body(invoke) == "<!-- sq:view:role_definition -->\n\nAgain."


@pytest.mark.covers("role body", "--message")
async def test_body_refuses_to_replace_a_written_body_without_force(project, invoke) -> None:
    await _add_scout(invoke)
    await invoke(["role", "scout", "body", "-m", "Hello."])
    result = await invoke(["role", "scout", "body", "-m", "Again."])
    assert (result.exit_code, result.output) == (
        1,
        "error: ROLE-2 already has a body (1 line); setting one would discard it:\n\n"
        "    Hello.\n\n"
        "Nothing was written. Add to it with `--append`, or pass `--force` to replace it.\n",
    )
    assert await _scout_body(invoke) == "<!-- sq:view:role_definition -->\n\nHello."


@pytest.mark.covers("role body", "--file")
async def test_body_file_reads_the_prose_from_the_file(project, invoke, tmp_path) -> None:
    await _add_scout(invoke)
    source = tmp_path / "prose.md"
    source.write_text("From a file.\n", encoding="utf-8")
    result = await invoke(["role", "scout", "body", "--file", str(source)])
    assert (result.exit_code, result.output) == (0, "ROLE-2: body set\n")
    assert await _scout_body(invoke) == "<!-- sq:view:role_definition -->\n\nFrom a file."


@pytest.mark.covers("role body", "--as")
async def test_body_as_attributes_the_write_to_the_actor(project, invoke) -> None:
    await _add_scout(invoke)
    await invoke(["role", "scout", "body", "-m", "Hello.", "--as", "manager"])
    assert await actors_of(invoke, "ROLE-2", "body") == ["manager"]


@pytest.mark.covers("role body", "--as")
async def test_body_as_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    await _add_scout(invoke)
    result = await invoke(["role", "scout", "body", "-m", "Hello.", "--as", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: manager, scout\n",
    )


@pytest.mark.covers("role body")
async def test_body_needs_a_message_or_a_file(project, invoke) -> None:
    await _add_scout(invoke)
    result = await invoke(["role", "scout", "body"])
    assert (result.exit_code, result.output) == (
        1,
        "error: provide the body via -m (repeatable) or --file path ('-' for stdin)\n",
    )


# -------------------------------------------------------------------------------- comments


@pytest.mark.covers("role", "<slug|id|n>")
async def test_comments_refuses_a_role_that_is_not_activated(project, invoke) -> None:
    result = await invoke(["role", "architect", "comments", "--json"])
    assert (result.exit_code, result.output) == (
        1,
        "error: no role with slug, ID, or number 'architect' — activate it first\n",
    )


# ----------------------------------------------------------------------------------- remove


@pytest.mark.covers("role remove", "--purge")
async def test_remove_purge_deletes_the_role_and_its_pointer(project, invoke) -> None:
    await _activate(invoke)
    assert _pointer(project, "architect").exists()
    result = await invoke(["role", "architect", "remove", "--purge"])
    assert (result.exit_code, result.output) == (0, "removed ROLE-2\n")
    assert sorted(await _roles(invoke)) == ["manager"]
    assert not _pointer(project, "architect").exists()
    assert "- **Robert Architect** — architect (`architect`)" not in _claude_md(project)


@pytest.mark.covers("role remove")
async def test_remove_refuses_without_purge(project, invoke) -> None:
    await _activate(invoke)
    result = await invoke(["role", "architect", "remove"])
    assert (result.exit_code, result.output) == (
        1,
        "error: cannot remove ROLE-2 without --purge: the markdown file would stay on disk and "
        "`sq check` would flag it. To delete it for good, run `sq role ROLE-2 remove --purge`; to "
        "retire it and keep it on record, run `sq role ROLE-2 status Archived`.\n",
    )
    assert sorted(await _roles(invoke)) == ["architect", "manager"]


@pytest.mark.covers("role remove", "--purge")
async def test_remove_of_the_default_role_warns_that_no_role_holds_the_designation(
    project, invoke
) -> None:
    await _activate(invoke)
    result = await invoke(["role", "manager", "remove", "--purge"])
    assert (result.exit_code, result.output) == (
        0,
        "removed ROLE-1\n"
        "warning: ROLE-1 (manager) carried the default-role designation; no live role carries "
        "it now — designate another live role with `sq role <addr> set-default`\n",
    )


@pytest.mark.covers("role remove", "--as")
async def test_remove_as_attributes_the_removal_to_the_actor(project, invoke) -> None:
    await _activate(invoke)
    await invoke(["role", "architect", "remove", "--purge", "--as", "manager"])
    assert await actors_of(invoke, "ROLE-2", "remove") == ["manager"]


@pytest.mark.covers("role remove", "--as")
async def test_remove_as_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    await _activate(invoke)
    result = await invoke(["role", "architect", "remove", "--purge", "--as", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: architect, manager\n",
    )


@pytest.mark.covers("role rm")
async def test_rm_is_the_hidden_name_of_remove_and_refuses_without_purge(project, invoke) -> None:
    await _activate(invoke)
    result = await invoke(["role", "architect", "rm"])
    assert (result.exit_code, result.output) == (
        1,
        "error: cannot remove ROLE-2 without --purge: the markdown file would stay on disk and "
        "`sq check` would flag it. To delete it for good, run `sq role ROLE-2 remove --purge`; to "
        "retire it and keep it on record, run `sq role ROLE-2 status Archived`.\n",
    )
    assert sorted(await _roles(invoke)) == ["architect", "manager"]


@pytest.mark.covers("role rm", "--purge")
async def test_rm_purge_deletes_the_role(project, invoke) -> None:
    await _activate(invoke)
    result = await invoke(["role", "architect", "rm", "--purge"])
    assert (result.exit_code, result.output) == (0, "removed ROLE-2\n")
    assert sorted(await _roles(invoke)) == ["manager"]


@pytest.mark.covers("role rm", "--as")
async def test_rm_as_attributes_the_removal_to_the_actor(project, invoke) -> None:
    await _activate(invoke)
    await invoke(["role", "architect", "rm", "--purge", "--as", "manager"])
    assert await actors_of(invoke, "ROLE-2", "remove") == ["manager"]


@pytest.mark.covers("role rm", "--as")
async def test_rm_as_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    await _activate(invoke)
    result = await invoke(["role", "architect", "rm", "--purge", "--as", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: architect, manager\n",
    )
    assert sorted(await _roles(invoke)) == ["architect", "manager"]


# -------------------------------------------------------------------------------- set-default


@pytest.mark.covers("role set-default")
async def test_set_default_moves_the_designation_and_names_the_role_it_cleared(
    project, invoke
) -> None:
    await _activate(invoke)
    result = await invoke(["role", "architect", "set-default"])
    assert (result.exit_code, result.output) == (0, "ROLE-2 is now the default\n  cleared ROLE-1\n")
    assert {slug: r["is_default"] for slug, r in (await _roles(invoke)).items()} == {
        "manager": False,
        "architect": True,
    }
    assert "If no agent is named, default to **Robert Architect** (`architect`)," in _claude_md(
        project
    )


@pytest.mark.covers("role set-default")
async def test_set_default_on_the_holder_changes_nothing(project, invoke) -> None:
    result = await invoke(["role", "manager", "set-default"])
    assert (result.exit_code, result.output) == (0, "ROLE-1 already the default — no change\n")


@pytest.mark.covers("role set-default")
async def test_set_default_refuses_a_role_that_is_not_live(project, invoke) -> None:
    await _activate(invoke)
    await invoke(["role", "architect", "status", "Archived"])
    result = await invoke(["role", "architect", "set-default"])
    assert (result.exit_code, result.output) == (
        1,
        "error: ROLE-2 (architect) is not live — only a live role can be designated default\n",
    )


@pytest.mark.covers("role set-default")
async def test_set_default_refuses_a_role_that_is_not_activated(project, invoke) -> None:
    result = await invoke(["role", "architect", "set-default"])
    assert (result.exit_code, result.output) == (
        1,
        "error: no role with slug, ID, or number 'architect' — activate it first\n",
    )


@pytest.mark.covers("role set-default", "--as")
async def test_set_default_as_attributes_the_change_to_the_actor(project, invoke) -> None:
    await _activate(invoke)
    await invoke(["role", "architect", "set-default", "--as", "manager"])
    assert await actors_of(invoke, "ROLE-2", "default_role") == ["manager"]


@pytest.mark.covers("role set-default", "--as")
async def test_set_default_as_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    await _activate(invoke)
    result = await invoke(["role", "architect", "set-default", "--as", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: architect, manager\n",
    )


# ----------------------------------------------------------------------------------- status


@pytest.mark.covers("role status", "status")
async def test_status_archives_a_role_and_brings_it_back(project, invoke) -> None:
    await _activate(invoke)
    archived = await invoke(["role", "architect", "status", "Archived"])
    assert (archived.exit_code, archived.output) == (0, "ROLE-2 → Archived\n")
    assert (await _roles(invoke))["architect"]["status"] == "Archived"
    live = await invoke(["role", "architect", "status", "Active"])
    assert (live.exit_code, live.output) == (0, "ROLE-2 → Active\n")
    assert (await _roles(invoke))["architect"]["status"] == "Active"


@pytest.mark.covers("role status", "status")
async def test_status_refuses_a_status_the_workflow_does_not_declare(project, invoke) -> None:
    await _activate(invoke)
    result = await invoke(["role", "architect", "status", "Bogus"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown status 'Bogus' (one of: Accepted, Active, Approved, Archived, Blocked, "
        "Cancelled, ChangesRequested, Deferred, Deprecated, Done, Draft, Fixed, InProgress, "
        "InReview, Noted, Open, Proposed, Published, Ready, Rejected, Requested, Superseded, "
        "Todo, Verified, WontFix)\n",
    )


@pytest.mark.covers("role status", "--force")
async def test_status_force_does_not_lift_a_status_the_role_lifecycle_lacks(
    project, invoke
) -> None:
    """No effect is reachable under the bundled spec; the refusal is the case."""
    await _activate(invoke)
    result = await invoke(["role", "architect", "status", "Draft", "--force"])
    assert (result.exit_code, result.output) == (
        1,
        "error: 'Draft' is not a valid status for role (allowed: Active, Archived)\n",
    )


@pytest.mark.covers("role status", "status")
async def test_status_refuses_to_archive_the_last_live_role(project, invoke) -> None:
    result = await invoke(["role", "manager", "status", "Archived"])
    assert (result.exit_code, result.output) == (
        1,
        "error: cannot move ROLE-1 to 'Archived': the resulting projection would be "
        "structurally invalid:\n- ROLE-1: no role entry is live, but backend(s) claude_code "
        "are active — the generated config can present no agent — remedy: activate another "
        "role first\n",
    )


@pytest.mark.covers("role status", "status")
async def test_status_needs_a_status(project, invoke) -> None:
    result = await invoke(["role", "manager", "status"])
    assert (result.exit_code, result.output) == (
        2,
        usage_error(
            "Usage: sq role <slug|id|n> status [OPTIONS] {status}",
            "sq role <slug|id|n> status --help",
            "Missing argument 'status'.",
        ),
    )


@pytest.mark.covers("role status", "--unlink")
async def test_status_unlink_on_a_retirement_reports_it_had_nothing_to_sever(
    project, invoke
) -> None:
    await _activate(invoke)
    result = await invoke(["role", "architect", "status", "Archived", "--unlink"])
    assert (result.exit_code, result.output) == (
        0,
        "ROLE-2 → Archived\n  --unlink: no references severed (nothing was severable)\n",
    )


@pytest.mark.covers("role status", "--unlink")
async def test_status_unlink_is_refused_on_a_move_that_is_not_a_retirement(project, invoke) -> None:
    await _activate(invoke)
    result = await invoke(["role", "architect", "status", "Active", "--unlink"])
    assert (result.exit_code, result.output) == (
        1,
        "error: --unlink is meaningless here: ROLE-2 is moving from 'Active' to 'Active', "
        "which is not a move out of a live status — the flag only applies to a retirement\n",
    )


@pytest.mark.covers("role status", "--as")
async def test_status_as_attributes_the_move_to_the_actor(project, invoke) -> None:
    await _activate(invoke)
    await invoke(["role", "architect", "status", "Archived", "--as", "manager"])
    assert await actors_of(invoke, "ROLE-2", "status") == ["manager"]


@pytest.mark.covers("role status", "--as")
async def test_status_as_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    await _activate(invoke)
    result = await invoke(["role", "architect", "status", "Archived", "--as", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: architect, manager\n",
    )


# ----------------------------------------------------------------------------------- update


@pytest.mark.covers("role update", "--title")
async def test_update_title_renames_the_role_and_its_pointer(project, invoke) -> None:
    await _activate(invoke)
    result = await invoke(["role", "architect", "update", "--title", "Rob"])
    assert (result.exit_code, result.output) == (0, "updated ROLE-2\n")
    assert (await _role(invoke, "architect"))["full_name"] == "Rob"
    assert "- **Rob** — architect (`architect`)" in _claude_md(project)
    assert "You are **Rob**, the architect on this project." in _pointer(
        project, "architect"
    ).read_text(encoding="utf-8")


@pytest.mark.covers("role update", "--pronouns")
async def test_update_pronouns_sets_them_and_a_blank_value_clears_them(project, invoke) -> None:
    await _activate(invoke)
    await invoke(["role", "architect", "update", "--pronouns", "he/him"])
    assert (await _role(invoke, "architect"))["pronouns"] == "he/him"
    await invoke(["role", "architect", "update", "--pronouns", ""])
    assert (await _role(invoke, "architect"))["pronouns"] is None


@pytest.mark.covers("role update", "--model")
async def test_update_model_sets_it_and_a_blank_value_clears_it(project, invoke) -> None:
    await _activate(invoke)
    await invoke(["role", "architect", "update", "--model", "haiku"])
    assert (await _role(invoke, "architect"))["model"] == "haiku"
    assert "model: haiku\n" in _pointer(project, "architect").read_text(encoding="utf-8")
    await invoke(["role", "architect", "update", "--model", ""])
    assert (await _role(invoke, "architect"))["model"] == "opus"


@pytest.mark.covers("role update", "--job-title")
async def test_update_job_title_changes_the_title_of_a_role_that_defines_itself(
    project, invoke
) -> None:
    await _add_scout(invoke)
    await invoke(["role", "scout", "update", "--job-title", "Lead scout"])
    assert (await _role(invoke, "scout"))["title"] == "Lead scout"


@pytest.mark.covers("role update", "--desc")
async def test_update_desc_changes_the_description_of_a_role_that_defines_itself(
    project, invoke
) -> None:
    await _add_scout(invoke)
    await invoke(["role", "scout", "update", "--desc", "Scouts far ahead"])
    assert (await _roles(invoke))["scout"]["description"] == "Scouts far ahead"


@pytest.mark.covers("role update", "--mission")
async def test_update_mission_changes_the_mission_of_a_role_that_defines_itself(
    project, invoke
) -> None:
    await _add_scout(invoke)
    await invoke(["role", "scout", "update", "--mission", "Find everything"])
    assert (await _role(invoke, "scout"))["mission"] == "Find everything"


@pytest.mark.covers("role update", "--capabilities")
async def test_update_capabilities_replaces_them_and_a_blank_value_clears_them(
    project, invoke
) -> None:
    await _add_scout(invoke, "--capabilities", P.third)
    await invoke(["role", "scout", "update", "--capabilities", "dev, plan"])
    assert (await _role(invoke, "scout"))["capabilities"] == ["dev", "plan"]
    await invoke(["role", "scout", "update", "--capabilities", ""])
    assert (await _role(invoke, "scout"))["capabilities"] == []


@pytest.mark.covers("role update", "--color")
async def test_update_color_is_written_to_the_pointer(project, invoke) -> None:
    await _add_scout(invoke)
    await invoke(["role", "scout", "update", "--color", "red"])
    assert "color: red\n" in _pointer(project, "scout").read_text(encoding="utf-8")


@pytest.mark.covers("role update", "--can-spawn")
async def test_update_can_spawn_takes_yes_or_no(project, invoke) -> None:
    await _add_scout(invoke)
    await invoke(["role", "scout", "update", "--can-spawn", "yes"])
    assert (await _role(invoke, "scout"))["can_spawn"] is True
    await invoke(["role", "scout", "update", "--can-spawn", "no"])
    assert (await _role(invoke, "scout"))["can_spawn"] is False


@pytest.mark.covers("role update", "--can-spawn")
async def test_update_can_spawn_refuses_any_other_word(project, invoke) -> None:
    await _add_scout(invoke)
    result = await invoke(["role", "scout", "update", "--can-spawn", "maybe"])
    assert (result.exit_code, result.output) == (
        1,
        "error: --can-spawn takes yes or no, not 'maybe'\n",
    )


@pytest.mark.covers("role update", "--file")
async def test_update_file_merges_a_definition_delta(project, invoke, tmp_path) -> None:
    await _add_scout(invoke)
    delta = tmp_path / "delta.toml"
    delta.write_text(
        'mission = "From the file"\nresponsibilities = ["Scout ahead"]\n', encoding="utf-8"
    )
    result = await invoke(["role", "scout", "update", "--file", str(delta)])
    assert (result.exit_code, result.output) == (0, "updated ROLE-2\n")
    shown = await _role(invoke, "scout")
    assert (shown["mission"], shown["responsibilities"], shown["full_name"]) == (
        "From the file",
        ["Scout ahead"],
        "Sam Scout",
    )


@pytest.mark.covers("role update", "--file")
async def test_update_file_refuses_a_path_that_cannot_be_read(project, invoke, tmp_path) -> None:
    await _add_scout(invoke)
    missing = tmp_path / "missing.toml"
    result = await invoke(["role", "scout", "update", "--file", str(missing)])
    assert (result.exit_code, result.output) == (
        1,
        f"error: cannot read role file {str(missing)!r}: No such file or directory\n",
    )


@pytest.mark.covers("role update", "--job-title")
async def test_update_refuses_a_definition_flag_on_a_role_the_catalog_defines(
    project, invoke
) -> None:
    result = await invoke(["role", "manager", "update", "--job-title", "Boss"])
    assert (result.exit_code, result.output) == (
        1,
        "error: manager's definition (--job-title) comes from the role catalog; set it in "
        ".overrides/roles/manager.toml (sq override scaffold --role manager)\n",
    )


@pytest.mark.covers("role update")
async def test_update_needs_a_field_to_change(project, invoke) -> None:
    result = await invoke(["role", "manager", "update"])
    assert (result.exit_code, result.output) == (
        1,
        "error: nothing to update (pass at least one of --title, --pronouns, --model, "
        "--job-title, --desc, --mission, --capabilities, --color, --can-spawn, --file)\n",
    )


@pytest.mark.covers("role update", "--title")
async def test_update_refuses_a_role_that_is_not_activated(project, invoke) -> None:
    result = await invoke(["role", "architect", "update", "--title", "Rob"])
    assert (result.exit_code, result.output) == (
        1,
        "error: no role with slug, ID, or number 'architect' — activate it first\n",
    )


@pytest.mark.covers("role update", "--as")
async def test_update_as_attributes_the_edit_to_the_actor(project, invoke) -> None:
    await _activate(invoke)
    await invoke(["role", "architect", "update", "--title", "Rob", "--as", "manager"])
    assert await actors_of(invoke, "ROLE-2", "update") == ["manager"]


@pytest.mark.covers("role update", "--as")
async def test_update_as_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    await _activate(invoke)
    result = await invoke(["role", "architect", "update", "--title", "Rob", "--as", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: architect, manager\n",
    )


# ------------------------------------------------------------------------------------ regen


@pytest.mark.covers("role regen")
async def test_regen_rewrites_a_pointer_that_was_deleted(project, invoke) -> None:
    await _activate(invoke)
    pointer = _pointer(project, "architect")
    before = pointer.read_text(encoding="utf-8")
    pointer.unlink()
    result = await invoke(["role", "architect", "regen"])
    assert (result.exit_code, result.output) == (0, "regenerated pointer for ROLE-2\n")
    assert pointer.read_text(encoding="utf-8") == before


@pytest.mark.covers("role regen")
async def test_regen_refuses_a_role_that_is_not_activated(project, invoke) -> None:
    result = await invoke(["role", "architect", "regen"])
    assert (result.exit_code, result.output) == (
        1,
        "error: no role with slug, ID, or number 'architect' — activate it first\n",
    )


# ------------------------------------------------------------------------------------ views


@pytest.mark.covers("role view add", "name")
async def test_view_add_of_the_view_a_role_already_renders_changes_nothing(project, invoke) -> None:
    result = await invoke(["role", "manager", "view", "add", "role_definition"])
    assert (result.exit_code, result.output) == (
        0,
        "ROLE-1: view role_definition already present, unchanged\n",
    )


@pytest.mark.covers("role view add", "name")
async def test_view_add_is_refused_for_a_name_the_role_body_does_not_take(project, invoke) -> None:
    await _add_scout(invoke)
    result = await invoke(["role", "scout", "view", "add", "nosuch"])
    assert (result.exit_code, result.output) == (1, VIEW_REFUSAL)


@pytest.mark.covers("role view add", "--as")
async def test_view_add_as_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    """The bundled spec accepts no edit of the role definition view; the refusal is the case."""
    result = await invoke(["role", "manager", "view", "add", "role_definition", "--as", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: manager\n",
    )


@pytest.mark.covers("role view disable", "name")
async def test_view_disable_is_refused_while_the_spec_declares_the_view(project, invoke) -> None:
    """The bundled spec accepts no edit of the role definition view; the refusal is the case."""
    await _add_scout(invoke)
    result = await invoke(["role", "scout", "view", "disable", "role_definition"])
    assert (result.exit_code, result.output) == (1, VIEW_REFUSAL)


@pytest.mark.covers("role view disable", "--as")
async def test_view_disable_as_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    """The bundled spec accepts no edit of the role definition view; the refusal is the case."""
    result = await invoke(
        ["role", "manager", "view", "disable", "role_definition", "--as", "nobody"]
    )
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: manager\n",
    )


# ---------------------------------------------------------------------------- JSON of the writes

MANAGER_ROW = {
    "id": "ROLE-1",
    "slug": "manager",
    "full_name": "Catherine Manager",
    "pronouns": None,
    "title": "manager",
    "description": "Default agent: triages the operator's request and routes it to the right "
    "specialist.",
    "is_default": True,
    "capabilities": [],
    "status": "Active",
    "origin": "system",
    "display": {"name": "Catherine Manager", "pronouns": None, "live": True},
}
ARCHITECT_ROW = {
    "id": "ROLE-2",
    "slug": "architect",
    "full_name": "Robert Architect",
    "pronouns": None,
    "title": "architect",
    "description": "System design and architecture decisions (ADRs).",
    "is_default": False,
    "capabilities": [],
    "status": "Active",
    "origin": "system",
    "display": {"name": "Robert Architect", "pronouns": None, "live": True},
}


@pytest.mark.covers("role add", "--json")
async def test_add_json_prints_the_role_it_created(project, invoke) -> None:
    output = await printed(invoke, ["role", "add", "scout", *SCOUT, "--json"])
    assert output == entry_text(
        {
            "id": "ROLE-2",
            "slug": "scout",
            "full_name": "Sam Scout",
            "pronouns": None,
            "title": "Scout",
            "description": "Scouts ahead",
            "is_default": False,
            "capabilities": [],
            "status": "Active",
            "origin": "project",
            "display": {"name": "Sam Scout", "pronouns": None, "live": True},
        }
    )


@pytest.mark.covers("role activate", "--json")
async def test_activate_json_prints_the_role_it_activated(project, invoke) -> None:
    output = await printed(invoke, ["role", "activate", "architect", "--json"])
    assert output == entry_text(ARCHITECT_ROW)


@pytest.mark.covers("role update", "--json")
async def test_update_json_prints_the_role_after_the_update(project, invoke) -> None:
    output = await printed(
        invoke, ["role", "manager", "update", "--title", "Cat Manager", "--json"]
    )
    assert output == entry_text(
        {
            **MANAGER_ROW,
            "full_name": "Cat Manager",
            "display": {"name": "Cat Manager", "pronouns": None, "live": True},
        }
    )


@pytest.mark.covers("role body", "--json")
async def test_body_json_prints_the_role_it_wrote(project, invoke) -> None:
    output = await printed(invoke, ["role", "manager", "body", "-m", "Prose", "--json"])
    assert output == entry_text(MANAGER_ROW)


@pytest.mark.covers("role status", "--json")
async def test_status_json_prints_the_role_after_the_move_and_what_it_severed(
    project, invoke
) -> None:
    await _activate(invoke)
    output = await printed(invoke, ["role", "architect", "status", "Archived", "--json"])
    assert output == json_text(
        {
            "entry": {
                **ARCHITECT_ROW,
                "status": "Archived",
                "display": {"name": "Robert Architect", "pronouns": None, "live": False},
            },
            "severed": [],
        }
    )


@pytest.mark.covers("role set-default", "--json")
async def test_set_default_json_prints_the_holder_and_whether_it_moved(project, invoke) -> None:
    output = await printed(invoke, ["role", "manager", "set-default", "--json"])
    assert output == json_text({"entry": MANAGER_ROW, "changed": False, "cleared": []})


@pytest.mark.covers("role regen", "--json")
async def test_regen_json_prints_the_role(project, invoke) -> None:
    output = await printed(invoke, ["role", "manager", "regen", "--json"])
    assert output == entry_text(MANAGER_ROW)


@pytest.mark.covers("role remove", "--json")
async def test_remove_json_prints_the_role_it_removed(project, invoke) -> None:
    await _activate(invoke)
    output = await printed(invoke, ["role", "architect", "remove", "--purge", "--json"])
    assert output == entry_text(ARCHITECT_ROW)


@pytest.mark.covers("role rm", "--json")
async def test_rm_json_prints_the_role_it_removed(project, invoke) -> None:
    await _activate(invoke)
    output = await printed(invoke, ["role", "architect", "rm", "--purge", "--json"])
    assert output == entry_text(ARCHITECT_ROW)


@pytest.mark.covers("role view add", "--json")
async def test_view_add_json_prints_the_role_and_that_the_tag_was_there(project, invoke) -> None:
    output = await printed(invoke, ["role", "manager", "view", "add", "role_definition", "--json"])
    assert output == json_text(
        {"entry": MANAGER_ROW, "view": "role_definition", "changed": False, "was_present": True}
    )


@pytest.mark.covers("role view disable", "--json")
async def test_view_disable_json_is_refused_while_the_spec_declares_the_view(
    project, invoke
) -> None:
    """The bundled spec refuses the edit, so `--json` prints only the refusal."""
    await _add_scout(invoke)
    result = await invoke(["role", "scout", "view", "disable", "role_definition", "--json"])
    assert (result.exit_code, result.output) == (1, VIEW_REFUSAL)
