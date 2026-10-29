"""`sq skill …`: creating skills, and the addressed verbs (show, update, status, refs, role links,
regen, remove, body, views and the comment listing)."""

from typing import Any

import pytest

from tests.cli._output import entry_text, json_text, printed, read_json
from tests.cli._roster import actors_of, body_of, forced_terminal, usage_error

pytestmark = pytest.mark.anyio

SLUG = "deploy-notes"
TEMPLATE_BODY = (
    "# Deploy Notes\n\n_TODO: describe what this skill does and when to use it._\n\n## Instructions"
)
UNKNOWN_KIND = (
    "error: unknown ref kind 'bogus'. Valid kinds: addresses, blocks, depends-on, duplicates, "
    "fixes, implements, related, scopes, supersedes, targets\n"
)
GENERATED_BODY_REFUSAL = (
    "error: SKILL-2's body renders through its declared sq:view:greeting_skill tag, and its "
    "content already has one validated authoring surface: its "
    "`.overrides/templates/views/greeting_skill.md.j2` view template override (`sq override "
    "scaffold views/greeting_skill.md.j2` creates it). {refused} is refused — `--force` does not "
    "lift this. Drop the view from `[selected]` to author this directly instead, then clear its "
    "leftover tag with `sq skill greeting view disable greeting_skill`.\n"
)
NO_ITEM_99 = "error: no item with number 99 (use a full ID like TYPE-99 or bare 99)\n"


async def _add(invoke, name: str = "Deploy Notes", *extra: str) -> None:
    result = await invoke(["skill", "add", name, *extra])
    assert result.exit_code == 0, result.output


async def _skill(invoke, address: str = SLUG) -> dict[str, Any]:
    return await read_json(invoke, ["skill", address, "show", "--json"])


def _pointer(project, slug: str = SLUG):
    return project.root / ".claude" / "skills" / slug / "SKILL.md"


def _no_skill(slug: str) -> str:
    return f"error: no skill with slug, ID, or number '{slug}'\n"


# ------------------------------------------------------------------------------------- add


@pytest.mark.covers("skill add", "NAME")
async def test_add_creates_a_skill_with_the_scaffold_body_and_its_pointer(project, invoke) -> None:
    result = await invoke(["skill", "add", "Deploy Notes"])
    assert (result.exit_code, result.output) == (
        0,
        "created skill SKILL-2 → agents/skills/SKILL-000002-deploy-notes.md\n",
    )
    assert await _skill(invoke) == {
        "id": "SKILL-2",
        "slug": SLUG,
        "title": "Deploy Notes",
        "status": "Active",
        "description": "",
        "when_to_use": "",
        "allowed_tools": "",
        "operator_invocable": True,
        "operator_invocable_set": False,
        "path": "agents/skills/SKILL-000002-deploy-notes.md",
        "origin": "project",
        "body": TEMPLATE_BODY,
        "views": {},
        "display": {
            "body": TEMPLATE_BODY,
            "empty_hint": '(empty — write it with `sq skill deploy-notes body -m "…"`)',
            "discussion": [],
        },
    }
    assert _pointer(project).exists()


@pytest.mark.covers("skill add", "NAME")
async def test_add_refuses_a_name_whose_slug_a_skill_already_has(project, invoke) -> None:
    await _add(invoke)
    result = await invoke(["skill", "add", "Deploy Notes"])
    assert (result.exit_code, result.output) == (
        1,
        "error: a skill with slug 'deploy-notes' already exists\n",
    )


@pytest.mark.covers("skill add", "NAME")
async def test_add_needs_a_name(project, invoke) -> None:
    result = await invoke(["skill", "add"])
    assert (result.exit_code, result.output) == (
        2,
        usage_error(
            "Usage: sq skill add [OPTIONS] NAME",
            "sq skill add --help",
            "Missing argument 'NAME'.",
        ),
    )


@pytest.mark.covers("skill add", "--desc")
async def test_add_desc_sets_the_description(project, invoke) -> None:
    await _add(invoke, "Deploy Notes", "--desc", "How to deploy")
    assert (await _skill(invoke))["description"] == "How to deploy"


@pytest.mark.covers("skill add", "--when-to-use")
async def test_add_when_to_use_is_stored_on_the_skill(project, invoke) -> None:
    await _add(invoke, "Deploy Notes", "--when-to-use", "On release")
    assert (await _skill(invoke))["when_to_use"] == "On release"


@pytest.mark.covers("skill add", "--allowed-tools")
async def test_add_allowed_tools_are_stored_on_the_skill(project, invoke) -> None:
    await _add(invoke, "Deploy Notes", "--allowed-tools", "Bash, Read")
    assert (await _skill(invoke))["allowed_tools"] == "Bash, Read"


@pytest.mark.covers("skill add", "--operator-invocable")
async def test_add_operator_invocable_no_withdraws_the_skill_from_the_operator(
    project, invoke
) -> None:
    await _add(invoke, "Deploy Notes", "--operator-invocable", "no")
    shown = await _skill(invoke)
    assert (shown["operator_invocable"], shown["operator_invocable_set"]) == (False, True)


@pytest.mark.covers("skill add", "--operator-invocable")
async def test_add_operator_invocable_default_follows_the_declared_default(project, invoke) -> None:
    await _add(invoke, "Deploy Notes", "--operator-invocable", "default")
    shown = await _skill(invoke)
    assert (shown["operator_invocable"], shown["operator_invocable_set"]) == (True, False)


@pytest.mark.covers("skill add", "--operator-invocable")
async def test_add_operator_invocable_refuses_any_other_word(project, invoke) -> None:
    result = await invoke(["skill", "add", "Deploy Notes", "--operator-invocable", "maybe"])
    assert (result.exit_code, result.output) == (
        1,
        "error: --operator-invocable takes yes, no or default, not 'maybe'\n",
    )


@pytest.mark.covers("skill add", "--parent")
async def test_add_parent_files_the_skill_under_the_item(project, invoke) -> None:
    await _add(invoke, "Deploy Notes", "--parent", "1")
    assert (await read_json(invoke, ["show", "2", "--json"]))["parent"] == "ROLE-1"


@pytest.mark.covers("skill add", "--parent")
async def test_add_parent_refuses_a_number_no_item_has(project, invoke) -> None:
    result = await invoke(["skill", "add", "Deploy Notes", "--parent", "99"])
    assert (result.exit_code, result.output) == (1, NO_ITEM_99)


@pytest.mark.covers("skill add", "--as")
async def test_add_as_attributes_the_creation_to_the_actor(project, invoke) -> None:
    await _add(invoke, "Deploy Notes", "--as", "manager")
    assert await actors_of(invoke, "SKILL-2", "create") == ["manager"]


@pytest.mark.covers("skill add", "--as")
async def test_add_as_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    result = await invoke(["skill", "add", "Deploy Notes", "--as", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: manager\n",
    )


# --------------------------------------------------------------------------------- address


@pytest.mark.covers("skill", "<slug|id|n>")
async def test_address_resolves_a_slug_an_id_and_a_number_to_the_same_skill(
    project, invoke
) -> None:
    await _add(invoke)
    by_slug = await _skill(invoke, SLUG)
    assert by_slug["id"] == "SKILL-2"
    assert await _skill(invoke, "SKILL-2") == by_slug
    assert await _skill(invoke, "2") == by_slug


@pytest.mark.covers("skill", "<slug|id|n>")
async def test_address_refuses_a_slug_no_skill_has(project, invoke) -> None:
    result = await invoke(["skill", "nobody", "show"])
    assert (result.exit_code, result.output) == (1, _no_skill("nobody"))


@pytest.mark.covers("skill", "<slug|id|n>")
async def test_address_refuses_the_number_of_an_item_that_is_not_a_skill(
    populated_project, invoke
) -> None:
    result = await invoke(["skill", "3", "show"])
    assert (result.exit_code, result.output) == (1, "error: 3 is TASK-3 (task), not a skill\n")


# ------------------------------------------------------------------------------------ show


def _panel(rows: list[str]) -> str:
    width = max(len(r) for r in rows)
    lines = ["╭" + "─" * (width + 2) + "╮"]
    lines += [f"│ {r.ljust(width)} │" for r in rows]
    lines.append("╰" + "─" * (width + 2) + "╯")
    return "\n".join(lines) + "\n"


SHOWN_PANEL = _panel(
    [
        "SKILL-2 Deploy Notes",
        "slug: deploy-notes",
        "origin: project",
        "status: Active",
        "operator invocable: yes (declared default)",
        "file: agents/skills/SKILL-000002-deploy-notes.md",
    ]
)


@pytest.mark.covers("skill show", "--json")
async def test_show_json_refuses_a_skill_that_does_not_exist(project, invoke) -> None:
    result = await invoke(["skill", "nobody", "show", "--json"])
    assert (result.exit_code, result.output) == (1, _no_skill("nobody"))


@pytest.mark.covers("skill show", "--json")
async def test_show_json_of_a_system_skill_carries_its_view_data(seeded_project, invoke) -> None:
    shown = await _skill(invoke, "greeting")
    assert (shown["origin"], shown["body"]) == ("system", "<!-- sq:view:greeting_skill -->")


@pytest.mark.covers("skill show", "--raw")
async def test_show_raw_prints_the_body_unrendered_where_a_terminal_would_render_it(
    project, invoke, monkeypatch
) -> None:
    await _add(invoke)
    await invoke(["skill", SLUG, "body", "-m", "Run `make release`."])
    piped = await invoke(["skill", SLUG, "show"])
    assert (piped.exit_code, piped.output) == (0, SHOWN_PANEL + "\nRun `make release`.\n")
    forced_terminal(monkeypatch)
    raw = await invoke(["skill", SLUG, "show", "--raw"])
    rendered = await invoke(["skill", SLUG, "show"])
    assert (raw.exit_code, raw.output) == (0, piped.output)
    assert rendered.output != piped.output


@pytest.mark.covers("skill show", "--comments")
async def test_show_comments_appends_the_discussion(project, invoke) -> None:
    await _add(invoke)
    await invoke(["skill", SLUG, "body", "-m", "Run `make release`."])
    await invoke(["skill", SLUG, "comment", "-m", "Check the tag.", "--as", "manager"])
    listed = (await read_json(invoke, ["skill", SLUG, "comments", "--json"]))[0]
    result = await invoke(["skill", SLUG, "show", "--comments"])
    assert (result.exit_code, result.output) == (
        0,
        SHOWN_PANEL
        + "\nRun `make release`.\n"
        + f"--- {listed['short_hash']} [{listed['ts']}] Catherine Manager (manager) ---\n"
        "- Check the tag.\n\n",
    )


# ---------------------------------------------------------------------------------- update


@pytest.mark.covers("skill update", "--title")
async def test_update_title_renames_the_skill_and_rewrites_its_heading(project, invoke) -> None:
    await _add(invoke)
    result = await invoke(["skill", SLUG, "update", "--title", "Release Notes"])
    assert (result.exit_code, result.output) == (0, "updated SKILL-2\n")
    shown = await _skill(invoke)
    assert (shown["title"], shown["slug"], shown["body"].splitlines()[0]) == (
        "Release Notes",
        SLUG,
        "# Release Notes",
    )


@pytest.mark.covers("skill update", "--desc")
async def test_update_desc_sets_the_description(project, invoke) -> None:
    await _add(invoke)
    await invoke(["skill", SLUG, "update", "--desc", "How to deploy"])
    assert (await _skill(invoke))["description"] == "How to deploy"


@pytest.mark.covers("skill update", "--when-to-use")
async def test_update_when_to_use_is_stored_on_the_skill(project, invoke) -> None:
    await _add(invoke)
    await invoke(["skill", SLUG, "update", "--when-to-use", "On release"])
    assert (await _skill(invoke))["when_to_use"] == "On release"


@pytest.mark.covers("skill update", "--operator-invocable")
async def test_update_operator_invocable_sets_and_returns_to_the_declared_default(
    project, invoke
) -> None:
    await _add(invoke)
    await invoke(["skill", SLUG, "update", "--operator-invocable", "no"])
    shown = await _skill(invoke)
    assert (shown["operator_invocable"], shown["operator_invocable_set"]) == (False, True)
    await invoke(["skill", SLUG, "update", "--operator-invocable", "default"])
    shown = await _skill(invoke)
    assert (shown["operator_invocable"], shown["operator_invocable_set"]) == (True, False)


@pytest.mark.covers("skill update", "--operator-invocable")
async def test_update_operator_invocable_refuses_any_other_word(project, invoke) -> None:
    await _add(invoke)
    result = await invoke(["skill", SLUG, "update", "--operator-invocable", "maybe"])
    assert (result.exit_code, result.output) == (
        1,
        "error: --operator-invocable takes yes, no or default, not 'maybe'\n",
    )


@pytest.mark.covers("skill update")
async def test_update_needs_a_field_to_change(project, invoke) -> None:
    await _add(invoke)
    result = await invoke(["skill", SLUG, "update"])
    assert (result.exit_code, result.output) == (
        1,
        "error: nothing to update (pass at least one of --title, --desc, --when-to-use, "
        "--operator-invocable)\n",
    )


@pytest.mark.covers("skill update", "--as")
async def test_update_as_attributes_the_edit_to_the_actor(project, invoke) -> None:
    await _add(invoke)
    await invoke(["skill", SLUG, "update", "--title", "Release Notes", "--as", "manager"])
    assert await actors_of(invoke, "SKILL-2", "update") == ["manager"]


@pytest.mark.covers("skill update", "--as")
async def test_update_as_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    await _add(invoke)
    result = await invoke(["skill", SLUG, "update", "--title", "Release Notes", "--as", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: manager\n",
    )


# ------------------------------------------------------------------------------------ body


@pytest.mark.covers("role body", "--force")
async def test_body_refuses_a_system_skill_whose_body_is_generated(seeded_project, invoke) -> None:
    result = await invoke(["skill", "greeting", "body", "-m", "Mine.", "--force"])
    assert (result.exit_code, result.output) == (
        1,
        GENERATED_BODY_REFUSAL.format(refused="A replace"),
    )


# ------------------------------------------------------------------------------------ refs


async def _two_skills_with_a_ref(invoke) -> None:
    """The skill `deploy-notes` carries a `related` ref to the skill `other`."""
    await _add(invoke)
    await _add(invoke, "Other")
    result = await invoke(["skill", SLUG, "ref", "add", "3"])
    assert result.exit_code == 0, result.output


@pytest.mark.covers("skill refs", "--json")
async def test_refs_json_lists_the_refs_the_skill_carries(project, invoke) -> None:
    await _two_skills_with_a_ref(invoke)
    assert await read_json(invoke, ["skill", SLUG, "refs", "--json"]) == {
        "out": [{"id": "SKILL-3", "kind": "related"}]
    }


@pytest.mark.covers("skill refs")
async def test_refs_prints_one_line_per_ref_the_skill_carries(project, invoke) -> None:
    await _two_skills_with_a_ref(invoke)
    result = await invoke(["skill", SLUG, "refs"])
    assert (result.exit_code, result.output) == (0, "→ refs  SKILL-3  related\n")


@pytest.mark.covers("skill refs", "--out")
async def test_refs_out_shows_only_the_refs_the_skill_carries(project, invoke) -> None:
    await _two_skills_with_a_ref(invoke)
    assert await read_json(invoke, ["skill", "other", "refs", "--out", "--json"]) == {"out": []}
    assert await read_json(invoke, ["skill", SLUG, "refs", "--out", "--json"]) == {
        "out": [{"id": "SKILL-3", "kind": "related"}]
    }


@pytest.mark.covers("skill refs", "--in")
async def test_refs_in_shows_the_refs_other_items_carry_to_the_skill(project, invoke) -> None:
    await _two_skills_with_a_ref(invoke)
    assert await read_json(invoke, ["skill", "other", "refs", "--in", "--json"]) == {
        "in": [{"id": "SKILL-2", "kind": "related"}]
    }
    result = await invoke(["skill", "other", "refs", "--in"])
    assert (result.exit_code, result.output) == (0, "← backrefs  SKILL-2  related\n")


@pytest.mark.covers("skill refs", "--in", "--out")
async def test_refs_in_and_out_together_show_both_directions(project, invoke) -> None:
    await _two_skills_with_a_ref(invoke)
    assert await read_json(invoke, ["skill", SLUG, "refs", "--in", "--out", "--json"]) == {
        "out": [{"id": "SKILL-3", "kind": "related"}],
        "in": [],
    }


# ------------------------------------------------------------------------------- ref add/rm


@pytest.mark.covers("skill ref add", "TARGET")
async def test_ref_add_links_the_skill_to_the_item_with_the_default_kind(project, invoke) -> None:
    await _add(invoke)
    result = await invoke(["skill", SLUG, "ref", "add", "1"])
    assert (result.exit_code, result.output) == (0, "SKILL-2 → ROLE-1 (related)\n")
    assert await read_json(invoke, ["skill", SLUG, "refs", "--json"]) == {
        "out": [{"id": "ROLE-1", "kind": "related"}]
    }


@pytest.mark.covers("skill ref add", "TARGET")
async def test_ref_add_takes_the_kind_after_a_colon(project, invoke) -> None:
    await _add(invoke)
    result = await invoke(["skill", SLUG, "ref", "add", "1:blocks"])
    assert (result.exit_code, result.output) == (0, "SKILL-2 → ROLE-1 (blocks)\n")
    assert (await read_json(invoke, ["skill", SLUG, "refs", "--json"]))["out"] == [
        {"id": "ROLE-1", "kind": "blocks"}
    ]


@pytest.mark.covers("skill ref add", "TARGET")
async def test_ref_add_refuses_a_number_no_item_has(project, invoke) -> None:
    await _add(invoke)
    result = await invoke(["skill", SLUG, "ref", "add", "99"])
    assert (result.exit_code, result.output) == (1, NO_ITEM_99)


@pytest.mark.covers("skill ref add", "--kind")
async def test_ref_add_kind_sets_the_kind_of_the_ref(project, invoke) -> None:
    await _add(invoke)
    result = await invoke(["skill", SLUG, "ref", "add", "1", "--kind", "depends-on"])
    assert (result.exit_code, result.output) == (0, "SKILL-2 → ROLE-1 (depends-on)\n")
    assert (await read_json(invoke, ["skill", SLUG, "refs", "--json"]))["out"] == [
        {"id": "ROLE-1", "kind": "depends-on"}
    ]


@pytest.mark.covers("skill ref add", "--kind")
async def test_ref_add_kind_refuses_a_kind_the_workflow_does_not_declare(project, invoke) -> None:
    await _add(invoke)
    result = await invoke(["skill", SLUG, "ref", "add", "1", "--kind", "bogus"])
    assert (result.exit_code, result.output) == (1, UNKNOWN_KIND)


@pytest.mark.covers("skill ref add", "--as")
async def test_ref_add_as_attributes_the_link_to_the_actor(project, invoke) -> None:
    await _add(invoke)
    await invoke(["skill", SLUG, "ref", "add", "1", "--as", "manager"])
    assert await actors_of(invoke, "SKILL-2", "ref") == ["manager"]


@pytest.mark.covers("skill ref add", "--as")
async def test_ref_add_as_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    await _add(invoke)
    result = await invoke(["skill", SLUG, "ref", "add", "1", "--as", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: manager\n",
    )


@pytest.mark.covers("skill ref rm", "TARGET")
async def test_ref_rm_drops_every_ref_to_the_item(project, invoke) -> None:
    await _two_skills_with_a_ref(invoke)
    result = await invoke(["skill", SLUG, "ref", "rm", "3"])
    assert (result.exit_code, result.output) == (0, "removed SKILL-2 → SKILL-3\n")
    assert await read_json(invoke, ["skill", SLUG, "refs", "--json"]) == {"out": []}


@pytest.mark.covers("skill ref rm", "TARGET")
async def test_ref_rm_refuses_a_number_no_item_has(project, invoke) -> None:
    await _add(invoke)
    result = await invoke(["skill", SLUG, "ref", "rm", "99"])
    assert (result.exit_code, result.output) == (1, NO_ITEM_99)


@pytest.mark.covers("skill ref rm", "--as")
async def test_ref_rm_as_attributes_the_removal_to_the_actor(project, invoke) -> None:
    await _two_skills_with_a_ref(invoke)
    await invoke(["skill", SLUG, "ref", "rm", "3", "--as", "manager"])
    assert (await actors_of(invoke, "SKILL-2", "ref"))[-1] == "manager"


@pytest.mark.covers("skill ref rm", "--as")
async def test_ref_rm_as_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    await _two_skills_with_a_ref(invoke)
    result = await invoke(["skill", SLUG, "ref", "rm", "3", "--as", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: manager\n",
    )


# ------------------------------------------------------------------------- link/unlink role


@pytest.mark.covers("skill link-role", "ROLE")
async def test_link_role_scopes_the_skill_to_the_role_and_updates_its_pointer(
    project, invoke
) -> None:
    await _add(invoke)
    result = await invoke(["skill", SLUG, "link-role", "manager"])
    assert (result.exit_code, result.output) == (0, "SKILL-2 scoped to ROLE-1 (role resynced)\n")
    assert (await read_json(invoke, ["skill", SLUG, "refs", "--json"]))["out"] == [
        {"id": "ROLE-1", "kind": "scopes"}
    ]
    assert "  - deploy-notes\n" in (project.root / ".claude/agents/manager.md").read_text(
        encoding="utf-8"
    )


@pytest.mark.covers("skill link-role", "ROLE")
async def test_link_role_refuses_a_role_that_does_not_exist(project, invoke) -> None:
    await _add(invoke)
    result = await invoke(["skill", SLUG, "link-role", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "error: no role with slug, ID, or number 'nobody'\n",
    )


@pytest.mark.covers("skill link-role", "ROLE")
async def test_link_role_refuses_the_number_of_an_item_that_is_not_a_role(project, invoke) -> None:
    await _add(invoke)
    result = await invoke(["skill", SLUG, "link-role", "2"])
    assert (result.exit_code, result.output) == (1, "error: 2 is SKILL-2 (skill), not a role\n")


@pytest.mark.covers("skill link-role", "--as")
async def test_link_role_as_attributes_the_link_to_the_actor(project, invoke) -> None:
    await _add(invoke)
    await invoke(["skill", SLUG, "link-role", "manager", "--as", "manager"])
    assert await actors_of(invoke, "SKILL-2", "ref") == ["manager"]


@pytest.mark.covers("skill link-role", "--as")
async def test_link_role_as_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    await _add(invoke)
    result = await invoke(["skill", SLUG, "link-role", "manager", "--as", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: manager\n",
    )


@pytest.mark.covers("skill unlink-role", "ROLE")
async def test_unlink_role_unscopes_the_skill_and_updates_the_pointer(project, invoke) -> None:
    await _add(invoke)
    await invoke(["skill", SLUG, "link-role", "manager"])
    result = await invoke(["skill", SLUG, "unlink-role", "manager"])
    assert (result.exit_code, result.output) == (
        0,
        "SKILL-2 unscoped from ROLE-1 (role resynced)\n",
    )
    assert (await read_json(invoke, ["skill", SLUG, "refs", "--json"]))["out"] == []
    assert "deploy-notes" not in (project.root / ".claude/agents/manager.md").read_text(
        encoding="utf-8"
    )


@pytest.mark.covers("skill unlink-role", "ROLE")
async def test_unlink_role_refuses_a_role_that_does_not_exist(project, invoke) -> None:
    await _add(invoke)
    result = await invoke(["skill", SLUG, "unlink-role", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "error: no role with slug, ID, or number 'nobody'\n",
    )


@pytest.mark.covers("skill unlink-role", "ROLE")
async def test_unlink_role_refuses_a_role_the_skill_is_not_scoped_to(project, invoke) -> None:
    await _add(invoke)
    result = await invoke(["skill", SLUG, "unlink-role", "manager"])
    assert (result.exit_code, result.output) == (1, "error: SKILL-2 has no scopes ref to ROLE-1\n")


@pytest.mark.covers("skill unlink-role", "--as")
async def test_unlink_role_as_attributes_the_unlink_to_the_actor(project, invoke) -> None:
    await _add(invoke)
    await invoke(["skill", SLUG, "link-role", "manager"])
    await invoke(["skill", SLUG, "unlink-role", "manager", "--as", "manager"])
    assert (await actors_of(invoke, "SKILL-2", "ref"))[-1] == "manager"


@pytest.mark.covers("skill unlink-role", "--as")
async def test_unlink_role_as_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    await _add(invoke)
    result = await invoke(["skill", SLUG, "unlink-role", "manager", "--as", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: manager\n",
    )


# ------------------------------------------------------------------------------------ regen


@pytest.mark.covers("skill regen")
async def test_regen_rewrites_a_pointer_that_was_deleted(project, invoke) -> None:
    await _add(invoke)
    pointer = _pointer(project)
    before = pointer.read_text(encoding="utf-8")
    pointer.unlink()
    result = await invoke(["skill", SLUG, "regen"])
    assert (result.exit_code, result.output) == (0, "regenerated pointer for SKILL-2\n")
    assert pointer.read_text(encoding="utf-8") == before


@pytest.mark.covers("skill regen")
async def test_regen_refuses_a_skill_that_does_not_exist(project, invoke) -> None:
    result = await invoke(["skill", "nobody", "regen"])
    assert (result.exit_code, result.output) == (1, _no_skill("nobody"))


# ----------------------------------------------------------------------------------- status


@pytest.mark.covers("role status", "STATUS")
async def test_status_refuses_to_retire_a_skill_still_scoped_to_a_live_role(
    project, invoke
) -> None:
    await _add(invoke)
    await invoke(["skill", SLUG, "link-role", "manager"])
    result = await invoke(["skill", SLUG, "status", "Archived"])
    assert (result.exit_code, result.output) == (
        1,
        "error: cannot move SKILL-2 to 'Archived': the resulting projection would be "
        "structurally invalid:\n- SKILL-2: not live but still scoped to live role(s): manager "
        "— remedy: pass --unlink, or run `sq skill <addr> unlink-role <role>` first\n",
    )


@pytest.mark.covers("role status", "--unlink")
async def test_status_unlink_severs_the_role_link_and_retires_the_skill(project, invoke) -> None:
    await _add(invoke)
    await invoke(["skill", SLUG, "link-role", "manager"])
    result = await invoke(["skill", SLUG, "status", "Archived", "--unlink"])
    assert (result.exit_code, result.output) == (
        0,
        "SKILL-2 → Archived\n  severed SKILL-2 → ROLE-1 (scopes)\n",
    )
    assert (await read_json(invoke, ["skill", SLUG, "refs", "--json"]))["out"] == []


# ---------------------------------------------------------------------------------- remove


@pytest.mark.covers("role remove", "--purge")
async def test_remove_purge_deletes_the_skill_and_its_pointer(project, invoke) -> None:
    await _add(invoke)
    result = await invoke(["skill", SLUG, "remove", "--purge"])
    assert (result.exit_code, result.output) == (0, "removed SKILL-2\n")
    assert not _pointer(project).exists()
    missing = await invoke(["skill", SLUG, "show"])
    assert (missing.exit_code, missing.output) == (1, _no_skill(SLUG))


# ------------------------------------------------------------------------------------ views


@pytest.mark.covers("skill view add", "NAME")
async def test_view_add_places_a_declared_view_in_the_body_and_a_repeat_changes_nothing(
    project, invoke
) -> None:
    await _add(invoke)
    placed = await invoke(["skill", SLUG, "view", "add", "greeting_skill"])
    assert (placed.exit_code, placed.output) == (
        0,
        "SKILL-2: view greeting_skill placed in sq:body\n",
    )
    assert "<!-- sq:view:greeting_skill -->" in await body_of(invoke, 2)
    again = await invoke(["skill", SLUG, "view", "add", "greeting_skill"])
    assert (again.exit_code, again.output) == (
        0,
        "SKILL-2: view greeting_skill already present, unchanged\n",
    )


@pytest.mark.covers("skill view add", "NAME")
async def test_view_add_refuses_a_view_the_spec_does_not_declare(project, invoke) -> None:
    await _add(invoke)
    result = await invoke(["skill", SLUG, "view", "add", "nosuch"])
    assert (result.exit_code, result.output) == (
        1,
        "error: no declared view 'nosuch' with a resolvable presentation template; see `sq "
        "workflow views` for the declared set\n",
    )


@pytest.mark.covers("skill view add", "--as")
async def test_view_add_as_attributes_the_edit_to_the_actor(project, invoke) -> None:
    await _add(invoke)
    await invoke(["skill", SLUG, "view", "add", "greeting_skill", "--as", "manager"])
    assert await actors_of(invoke, "SKILL-2", "view") == ["manager"]


@pytest.mark.covers("skill view add", "--as")
async def test_view_add_as_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    await _add(invoke)
    result = await invoke(["skill", SLUG, "view", "add", "greeting_skill", "--as", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: manager\n",
    )


@pytest.mark.covers("skill view disable", "NAME")
async def test_view_disable_keeps_the_tag_disabled_and_a_repeat_changes_nothing(
    project, invoke
) -> None:
    await _add(invoke)
    await invoke(["skill", SLUG, "view", "add", "greeting_skill"])
    disabled = await invoke(["skill", SLUG, "view", "disable", "greeting_skill"])
    assert (disabled.exit_code, disabled.output) == (
        0,
        "SKILL-2: view greeting_skill disabled in sq:body\n",
    )
    again = await invoke(["skill", SLUG, "view", "disable", "greeting_skill"])
    assert (again.exit_code, again.output) == (
        0,
        "SKILL-2: view greeting_skill already disabled, unchanged\n",
    )


@pytest.mark.covers("skill view disable", "NAME")
async def test_view_disable_of_a_name_without_a_tag_places_it_disabled(project, invoke) -> None:
    await _add(invoke)
    result = await invoke(["skill", SLUG, "view", "disable", "nosuch"])
    assert (result.exit_code, result.output) == (
        0,
        "SKILL-2: view nosuch had no existing tag — placed disabled in sq:body\n",
    )


@pytest.mark.covers("skill view disable", "NAME")
async def test_view_disable_is_refused_on_a_system_skill_whose_view_is_declared(
    seeded_project, invoke
) -> None:
    result = await invoke(["skill", "greeting", "view", "disable", "greeting_skill"])
    assert (result.exit_code, result.output) == (
        1,
        GENERATED_BODY_REFUSAL.format(refused="A view edit"),
    )


@pytest.mark.covers("skill view disable", "--as")
async def test_view_disable_as_attributes_the_edit_to_the_actor(project, invoke) -> None:
    await _add(invoke)
    await invoke(["skill", SLUG, "view", "disable", "nosuch", "--as", "manager"])
    assert await actors_of(invoke, "SKILL-2", "view") == ["manager"]


@pytest.mark.covers("skill view disable", "--as")
async def test_view_disable_as_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    await _add(invoke)
    result = await invoke(["skill", SLUG, "view", "disable", "nosuch", "--as", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: manager\n",
    )


# ------------------------------------------------------------------------------- comments


@pytest.mark.covers("skill", "<slug|id|n>")
async def test_comments_refuses_a_skill_that_does_not_exist(project, invoke) -> None:
    result = await invoke(["skill", "nobody", "comments", "--json"])
    assert (result.exit_code, result.output) == (1, _no_skill("nobody"))


# --------------------------------------------------------------------- shared verbs' address


@pytest.mark.covers("skill", "<slug|id|n>")
async def test_body_status_and_remove_act_on_the_skill_they_address(project, invoke) -> None:
    """The shared roster verbs resolve the address of a skill, never another roster entry."""
    await _add(invoke)
    body = await invoke(["skill", SLUG, "body", "-m", "Ship it."])
    assert (body.exit_code, body.output) == (0, "SKILL-2: body set\n")
    assert await body_of(invoke, 2) == "Ship it."
    assert await body_of(invoke, 1) != "Ship it."
    moved = await invoke(["skill", SLUG, "status", "Archived"])
    assert (moved.exit_code, moved.output) == (0, "SKILL-2 → Archived\n")
    assert (await _skill(invoke))["status"] == "Archived"
    roles = await read_json(invoke, ["role", "list", "--json"])
    assert [r["status"] for r in roles] == ["Active"]
    removed = await invoke(["skill", SLUG, "remove", "--purge"])
    assert (removed.exit_code, removed.output) == (0, "removed SKILL-2\n")
    assert [r["slug"] for r in await read_json(invoke, ["role", "list", "--json"])] == ["manager"]


# ---------------------------------------------------------------------------- JSON of the writes

SKILL_ROW = {
    "id": "SKILL-2",
    "slug": SLUG,
    "title": "Deploy Notes",
    "status": "Active",
    "description": "",
    "when_to_use": "",
    "allowed_tools": "",
    "operator_invocable": True,
    "operator_invocable_set": False,
    "path": "agents/skills/SKILL-000002-deploy-notes.md",
    "origin": "project",
}


@pytest.mark.covers("skill add", "--json")
async def test_add_json_prints_the_skill_it_created(project, invoke) -> None:
    output = await printed(invoke, ["skill", "add", "Deploy Notes", "--json"])
    assert output == entry_text(SKILL_ROW)


@pytest.mark.covers("skill update", "--json")
async def test_update_json_prints_the_skill_after_the_update(project, invoke) -> None:
    await _add(invoke)
    output = await printed(invoke, ["skill", SLUG, "update", "--title", "Deploy", "--json"])
    assert output == entry_text({**SKILL_ROW, "title": "Deploy"})


@pytest.mark.covers("skill link-role", "--json")
async def test_link_role_json_prints_the_skill_and_the_role(project, invoke) -> None:
    await _add(invoke)
    output = await printed(invoke, ["skill", SLUG, "link-role", "manager", "--json"])
    assert output == json_text({"entry": SKILL_ROW, "role": "ROLE-1"})


@pytest.mark.covers("skill unlink-role", "--json")
async def test_unlink_role_json_prints_the_skill_and_the_role(project, invoke) -> None:
    await _add(invoke)
    await invoke(["skill", SLUG, "link-role", "manager"])
    output = await printed(invoke, ["skill", SLUG, "unlink-role", "manager", "--json"])
    assert output == json_text({"entry": SKILL_ROW, "role": "ROLE-1"})


@pytest.mark.covers("skill ref add", "--json")
async def test_ref_add_json_prints_the_skill_the_target_and_the_kind(project, invoke) -> None:
    await _add(invoke)
    output = await printed(invoke, ["skill", SLUG, "ref", "add", "1", "--json"])
    assert output == json_text({"entry": SKILL_ROW, "target": "ROLE-1", "kind": "related"})


@pytest.mark.covers("skill ref rm", "--json")
async def test_ref_rm_json_prints_the_skill_and_the_target(project, invoke) -> None:
    await _add(invoke)
    await invoke(["skill", SLUG, "ref", "add", "1"])
    output = await printed(invoke, ["skill", SLUG, "ref", "rm", "1", "--json"])
    assert output == json_text({"entry": SKILL_ROW, "target": "ROLE-1", "kind": None})


@pytest.mark.covers("skill regen", "--json")
async def test_regen_json_prints_the_skill(project, invoke) -> None:
    await _add(invoke)
    output = await printed(invoke, ["skill", SLUG, "regen", "--json"])
    assert output == entry_text(SKILL_ROW)


@pytest.mark.covers("skill view add", "--json")
async def test_view_add_json_prints_the_skill_and_the_tag_it_placed(project, invoke) -> None:
    await _add(invoke)
    output = await printed(invoke, ["skill", SLUG, "view", "add", "greeting_skill", "--json"])
    assert output == json_text(
        {"entry": SKILL_ROW, "view": "greeting_skill", "changed": True, "was_present": False}
    )


@pytest.mark.covers("skill view disable", "--json")
async def test_view_disable_json_prints_the_skill_and_the_tag_it_placed_disabled(
    project, invoke
) -> None:
    await _add(invoke)
    output = await printed(invoke, ["skill", SLUG, "view", "disable", "greeting_skill", "--json"])
    assert output == json_text(
        {"entry": SKILL_ROW, "view": "greeting_skill", "changed": True, "was_present": False}
    )


@pytest.mark.covers("skill unlink-role", "ROLE")
async def test_unlink_role_refuses_a_skill_whose_only_ref_to_the_role_is_another_kind(
    project, invoke
) -> None:
    await _add(invoke)
    await invoke(["skill", SLUG, "ref", "add", "1", "--kind", "related"])
    result = await invoke(["skill", SLUG, "unlink-role", "manager"])
    assert (result.exit_code, result.output) == (1, "error: SKILL-2 has no scopes ref to ROLE-1\n")
    assert (await read_json(invoke, ["skill", SLUG, "refs", "--json"]))["out"] != []
