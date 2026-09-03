"""A playbook guide the generated skill will silently drop must never validate silently.

The playbook loader's slug authority is deliberately permissive -- the bundled catalog union
whatever `.overrides/roles/*.toml` files exist, read by *filename*, because those files must be
readable before the index is. The renderer is not: it gates each guide on live roster membership and
drops the rest. Where the two disagree the adopter's guidance evaporated with nothing said anywhere,
which turned the previous loud (and wrong) refusal into a silent loss.

The rule this pins: `sq check` warns, and `sq sync` reports the same event on the run that dropped
it -- one shared wording, since both surfaces describe the same thing. Reported, not refused: unlike
the *skill* side of the same retirement (where `--unlink` is a step the operator can actually
perform), neither remedy here lives inside a single transition, and sq never rewrites an adopter's
override file, so a refusal would be a lock-out with no escape.

Both reachable triggers are driven, in both directions, plus the two exemptions -- the exemptions
matter as much as the rule: `--roles minimal` legitimately has bundled guides for roles it never
installed, and a rule that lit up for those would be noise an adopter learns to ignore.

The exemption keys on **who wrote the guide**, not on whether the squad has a roster entry for the
slug. That distinction is the whole difference between an actionable report and an unclearable one:
a guide the adopter declared in `.overrides/playbook.toml` is theirs, so the message can name the
file and the table and removing it genuinely clears the warning -- whereas the bundled playbook is
package data no adopter can edit, so a report on one of its guides names a file the squad may not
even have and leaves reactivating the role as the only way out. Retirement is a first-class,
documented, reversible operation and six bundled roles carry bundled guidance, so keying on the
roster entry meant retiring any of them minted a permanent warning with no remedy.
"""

from pathlib import Path

import pytest

from squads import __version__
from squads import _interactions as interactions
from squads._errors import SquadsError
from squads._overrides._service import scaffold_new_role
from squads._services import _service as service

pytestmark = pytest.mark.anyio


def _write_playbook_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "playbook.toml").write_text(
        f"# squads:override-base:{__version__}\n{content}", encoding="utf-8"
    )


def _guidance_for(slug: str, item_type: str = "task") -> str:
    return f"""
[types.{item_type}]
roles = [
    "$(*self)",
    {{ slug = "{slug}", enter = ["Read the incident timeline"], do = ["Do the ops thing"] }},
]
"""


def _restated_guidance_for(slug: str, item_type: str) -> str:
    """An override that **restates** a type's `roles` array with its own guide for *slug*, rather
    than spreading the bundled array and appending.

    The spelling matters for a *bundled* slug: `roles` is keyed by slug, so `["$(*self)", {slug =
    "<already-bundled>"}]` is refused as a duplicate. Restating the whole array is the sanctioned
    way to take a bundled guide over, and it is what makes the resulting guide the adopter's.
    """
    return f"""
[types.{item_type}]
roles = [{{ slug = "{slug}", enter = ["Read our house checklist"], do = ["Do it our way"] }}]
"""


def _fill_in_role_stub(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for placeholder, value in (
        (
            'full_name = "TODO: full name (e.g. \\"Sam Security\\")"',
            'full_name = "Sam Reliability"',
        ),
        ('title = "TODO: one-line title (e.g. \\"security analyst\\")"', 'title = "SRE"'),
        (
            'description = "TODO: one-line description for the Claude pointer frontmatter"',
            'description = "Keeps the lights on."',
        ),
        (
            'mission = "TODO: what this role is responsible for accomplishing"',
            'mission = "Own incident response and rollback."',
        ),
    ):
        text = text.replace(placeholder, value)
    path.write_text(text, encoding="utf-8")


def _dropped_guide_warnings(issues, slug: str) -> list[str]:
    return [i.message for i in issues if i.level == "warn" and f"{slug!r}" in i.message]


async def _task_skill_body(squad_dir: Path) -> str:
    path = squad_dir / "agents" / "skills" / f"{interactions.item_skill_name('task')}.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


# ------------------------------------------------------------------- trigger 1: never activated


async def test_a_guide_for_a_scaffolded_but_unactivated_role_is_warned_about(project):
    """`sq override scaffold --new <slug>` prints activation as its *next* step, so writing the
    role file and its guidance before activating is the natural order -- and everything reported
    clean while the guidance sat inert."""
    _fill_in_role_stub(scaffold_new_role(project.squad_dir, slug="sre"))
    _write_playbook_override(project.squad_dir, _guidance_for("sre"))

    svc = service.open_service(dir_override=str(project.squad_dir))
    issues = await svc.check()

    warnings = _dropped_guide_warnings(issues, "sre")
    assert warnings, [i.message for i in issues]
    assert "'task'" in warnings[0]
    assert "sq role activate sre" in warnings[0]
    assert ".overrides/playbook.toml" in warnings[0]


async def test_the_guidance_really_is_absent_from_the_generated_skill(project):
    """The other half of the same claim, so the warning is not asserted against an imagined drop:
    the guide text genuinely is not in the generated skill while the role is unactivated, and
    genuinely is once it is."""
    _fill_in_role_stub(scaffold_new_role(project.squad_dir, slug="sre"))
    _write_playbook_override(project.squad_dir, _guidance_for("sre"))

    svc = service.open_service(dir_override=str(project.squad_dir))
    await svc.refresh_managed()
    assert "Do the ops thing" not in await _task_skill_body(project.squad_dir)

    await svc.activate_role("sre")
    reopened = service.open_service(dir_override=str(project.squad_dir))
    await reopened.refresh_managed()
    assert "Do the ops thing" in await _task_skill_body(project.squad_dir)


async def test_no_warning_once_the_project_role_is_live(project):
    """The negative direction, and the one that makes the rule usable rather than noise: a live
    project role's guide reaches the skill, so there is nothing to report."""
    _fill_in_role_stub(scaffold_new_role(project.squad_dir, slug="sre"))
    svc = service.open_service(dir_override=str(project.squad_dir))
    await svc.activate_role("sre")
    _write_playbook_override(project.squad_dir, _guidance_for("sre"))

    reopened = service.open_service(dir_override=str(project.squad_dir))
    issues = await reopened.check()

    assert _dropped_guide_warnings(issues, "sre") == []


# --------------------------------------------------------------------- trigger 2: retired later


async def test_a_guide_for_a_retired_project_role_is_warned_about(project):
    """The trigger that bites in practice: nothing about the override changes, the role is simply
    retired, and the section quietly vanishes from the generated skill on the next sync."""
    _fill_in_role_stub(scaffold_new_role(project.squad_dir, slug="sre"))
    svc = service.open_service(dir_override=str(project.squad_dir))
    role = await svc.activate_role("sre")
    _write_playbook_override(project.squad_dir, _guidance_for("sre"))

    reopened = service.open_service(dir_override=str(project.squad_dir))
    assert _dropped_guide_warnings(await reopened.check(), "sre") == []

    await reopened.set_roster_status(role.id, "Archived")
    after = service.open_service(dir_override=str(project.squad_dir))
    issues = await after.check()

    assert _dropped_guide_warnings(issues, "sre"), [i.message for i in issues]


async def test_retiring_a_bundled_role_reports_nothing_while_its_guide_is_squads_own(project):
    """The shape that made the rule unclearable, and the reason the exemption keys on authorship.

    Retiring a bundled role is a documented, reversible operation, and six bundled roles carry
    bundled playbook guidance. Keying the exemption on "does this squad have a roster entry"
    reported this, and the report was unactionable in both of its halves: it named
    `.overrides/playbook.toml` for a guide that lives only in package data (a file this squad does
    not even have -- asserted, not assumed), and the only way to clear it was to undo the
    retirement. Bundled guidance dropping for a role the squad does not have is squads' own
    graceful degradation, and stays silent exactly as it does for a role never installed.
    """
    svc = service.open_service(dir_override=str(project.squad_dir))
    role = await svc.activate_role("qa")
    reopened = service.open_service(dir_override=str(project.squad_dir))
    assert _dropped_guide_warnings(await reopened.check(), "qa") == [], "live: nothing dropped"

    await reopened.set_roster_status(role.id, "Archived")
    after = service.open_service(dir_override=str(project.squad_dir))

    assert _dropped_guide_warnings(await after.check(), "qa") == [], "no remedy exists to name"
    assert not (project.squad_dir / ".overrides" / "playbook.toml").exists(), (
        "the shape is only unclearable because there is no override file to edit -- if this "
        "fixture ever grows one, this test stops covering the case it exists for"
    )


async def test_the_same_retirement_is_reported_once_the_adopter_restates_the_guide(project):
    """The other direction of the same rule, which is what keeps the exemption from being a blanket
    silence: an adopter who takes a bundled type's `roles` array over owns those guides, so the
    remedy the message names is real -- the file exists, the table is theirs, and removing the guide
    clears it. Same role, same retirement, same squad as the test above; the only difference is who
    wrote the guide.
    """
    svc = service.open_service(dir_override=str(project.squad_dir))
    role = await svc.activate_role("qa")
    _write_playbook_override(project.squad_dir, _restated_guidance_for("qa", "feature"))

    reopened = service.open_service(dir_override=str(project.squad_dir))
    assert _dropped_guide_warnings(await reopened.check(), "qa") == [], "live: nothing dropped"

    await reopened.set_roster_status(role.id, "Archived")
    after = service.open_service(dir_override=str(project.squad_dir))
    warnings = _dropped_guide_warnings(await after.check(), "qa")

    assert warnings, "a guide the adopter wrote is theirs to be told about"
    assert "'feature'" in warnings[0], warnings


async def test_a_splat_ref_does_not_make_the_bundled_guides_the_adopters(project):
    """The near-miss between the two tests above, and the one an implementation keying on "is this
    type in the override document" would get wrong.

    `roles = ["$(*self)"]` names no slug of its own -- it spreads the bundled array by reference, so
    the guides it pulls in are still squads' text and still unremovable one at a time. An adopter
    who touched a type's table for some other reason (an overview of their own) must not thereby
    acquire warnings for every bundled guide on it.
    """
    svc = service.open_service(dir_override=str(project.squad_dir))
    role = await svc.activate_role("qa")
    _write_playbook_override(
        project.squad_dir,
        '[types.feature]\noverview = "Our house features."\nroles = ["$(*self)"]\n',
    )

    reopened = service.open_service(dir_override=str(project.squad_dir))
    await reopened.set_roster_status(role.id, "Archived")
    after = service.open_service(dir_override=str(project.squad_dir))

    assert "Our house features." in after.playbook.types["feature"].overview, (
        "fixture assumption: the override must really be in force"
    )
    assert _dropped_guide_warnings(await after.check(), "qa") == []


# -------------------------------------------------------------- the remedy has to be performable


async def test_the_named_revival_command_is_the_one_that_works_for_each_shape(project):
    """Both reported shapes say "make the role live", but they do not do it with the same command.

    `activate` is a create verb: on a *retired* role it refuses outright — driven below on the
    retired shape — because reviving an existing entry is a transition, not a creation. A slug
    with no entry yet is the opposite: there is nothing to transition, and `sq role activate` is
    what creates and activates it. Naming one command for both would send half the readers to a
    command that cannot do what the message asks of it.
    """
    _fill_in_role_stub(scaffold_new_role(project.squad_dir, slug="sre"))
    _write_playbook_override(project.squad_dir, _guidance_for("sre"))

    svc = service.open_service(dir_override=str(project.squad_dir))
    unactivated = _dropped_guide_warnings(await svc.check(), "sre")
    assert unactivated, "fixture assumption: the unactivated shape must report"
    assert "sq role activate sre" in unactivated[0], unactivated

    role = await svc.activate_role("sre")
    reopened = service.open_service(dir_override=str(project.squad_dir))
    await reopened.set_roster_status(role.id, "Archived")
    after = service.open_service(dir_override=str(project.squad_dir))
    retired = _dropped_guide_warnings(await after.check(), "sre")

    assert retired, "fixture assumption: the retired shape must report"
    live = after.spec.live_initial("role")
    assert f"sq role sre status {live}" in retired[0], retired
    assert "sq role activate sre" not in retired[0], (
        "the retired shape must not be sent to a command that cannot perform the revival"
    )

    # Why: driven, so the claim above is behaviour rather than reading of the implementation.
    with pytest.raises(SquadsError, match=f"sq role sre status {live}"):
        await after.activate_role("sre")
    assert (await after.get(role.id)).status == "Archived", "and it changed nothing on the way out"

    # And the command the message does name clears the report.
    await after.set_roster_status(role.id, live)
    revived = service.open_service(dir_override=str(project.squad_dir))
    assert _dropped_guide_warnings(await revived.check(), "sre") == []


# ---------------------------------------- trigger 3: a stem that is not a role at all


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("broken.toml", "this is not = = valid toml\n"),
        ("NOTES.toml", "# just some notes an adopter dropped here\n"),
    ],
    ids=["malformed_toml", "stray_non_role_file"],
)
async def test_a_stem_the_loader_accepts_but_that_is_no_role_is_warned_about(
    project, filename, content
):
    """The loader globs filenames rather than parsing, so any `.toml` under `.overrides/roles/`
    contributes its stem as an acceptable playbook slug. Keeping the loader permissive is right (it
    must be readable before the index), so the same one rule covers this: the stem resolves to no
    live role, therefore the guide is dropped, therefore it is reported."""
    overrides = project.squad_dir / ".overrides" / "roles"
    overrides.mkdir(parents=True, exist_ok=True)
    (overrides / filename).write_text(content, encoding="utf-8")
    slug = Path(filename).stem
    _write_playbook_override(project.squad_dir, _guidance_for(slug))

    svc = service.open_service(dir_override=str(project.squad_dir))

    assert _dropped_guide_warnings(await svc.check(), slug), "a stem is not a role"


# ------------------------------------------------------------------------------- the exemptions


async def test_the_bundled_playbook_alone_produces_no_warnings_in_a_minimal_squad(project):
    """The exemption that keeps the rule from being noise. The bundled playbook names all eight
    bundled roles, so a `--roles minimal` squad has guides for seven it never installed -- the
    pre-existing, intended degradation, not a loss of anything the adopter wrote. If this ever
    fails, every adopter sees seven warnings on a clean squad and learns to ignore the rule."""
    svc = service.open_service(dir_override=str(project.squad_dir))

    issues = await svc.check()

    assert [
        i.message for i in issues if i.level == "warn" and "names no live role" in i.message
    ] == []


async def test_the_dev_sentinel_is_never_reported(project):
    """`*dev` means "any `<tech>-dev` role" and its rendering is already conditioned on the roster
    having one, so it is not a slug that can resolve to a role at all. The bundled playbook carries
    `*dev` guides on several types and this squad has no dev role, so the shape is already present
    -- adding one would only duplicate a slug the bundled array already holds."""
    svc = service.open_service(dir_override=str(project.squad_dir))

    assert any(
        guide.slug == "*dev" for entry in svc.playbook.types.values() for guide in entry.roles
    ), "fixture assumption: the bundled playbook must carry at least one *dev guide"
    assert [i.message for i in await svc.check() if "*dev" in i.message] == []


async def test_a_guide_on_a_type_the_spec_has_dropped_is_not_reported_per_role(project):
    """A dropped *type* withdraws its whole `sq-<type>` skill, which the orphaned-skill rule already
    reports as one line. Re-reporting each of that type's guides would bury that line under a
    per-role pile -- and it never happens, by two independent mechanisms, both driven here rather
    than attributed to the predicate's own `item_type not in spec.items` guard (removing that guard
    reddens neither half, which is why the property is asserted at the behaviour instead).

    Bundled guides on the dropped type: the merged playbook is already spec-filtered, so they are
    gone before the reporter runs -- and bundled guides are exempt regardless. Adopter-written
    guides on the dropped type: the loader refuses the document outright, fail-closed, so they never
    reach the reporter either. Between them there is no path by which a dropped type contributes a
    single per-role line.
    """
    svc = service.open_service(dir_override=str(project.squad_dir))
    role = await svc.activate_role("qa")
    await svc.set_roster_status(role.id, "Archived")

    kept = [
        "epic",
        "feature",
        "task",
        "decision",
        "contract",
        "review",
        "guide",
        "role",
        "skill",
        "operator",
    ]
    (project.squad_dir / ".overrides").mkdir(parents=True, exist_ok=True)
    (project.squad_dir / ".overrides" / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n[selected]\nitems = {kept!r}\n", encoding="utf-8"
    )

    after = service.open_service(dir_override=str(project.squad_dir))
    assert "bug" not in after.playbook.types, "the merged playbook is spec-filtered"
    assert _dropped_guide_warnings(await after.check(), "qa") == []

    # The adopter-written half: an override that declares a guide on the dropped type cannot load
    # at all, so there is nothing for the reporter to pile up.
    _write_playbook_override(project.squad_dir, _restated_guidance_for("qa", "bug"))
    with pytest.raises(SquadsError):
        service.open_service(dir_override=str(project.squad_dir))


# ------------------------------------------------------------------------------- sq sync's channel


async def test_sync_reports_the_guide_it_just_dropped(project):
    """`sq sync` is the run that actually removes the section from the file, so it carries the news
    too -- the same channel the orphaned `sq-<type>` skill notice already uses, and the same wording
    as `check`, so the two surfaces cannot drift into describing one event two ways."""
    _fill_in_role_stub(scaffold_new_role(project.squad_dir, slug="sre"))
    _write_playbook_override(project.squad_dir, _guidance_for("sre"))

    svc = service.open_service(dir_override=str(project.squad_dir))
    skipped = await svc.sync()

    assert any("'sre'" in msg and "names no live role" in msg for msg in skipped), skipped
    check_messages = [i.message for i in await svc.check()]
    assert any(msg in check_messages for msg in skipped if "'sre'" in msg), (
        "sync and check must report the identical wording for the same event"
    )


async def test_sync_reports_nothing_once_the_role_is_live(project):
    _fill_in_role_stub(scaffold_new_role(project.squad_dir, slug="sre"))
    svc = service.open_service(dir_override=str(project.squad_dir))
    await svc.activate_role("sre")
    _write_playbook_override(project.squad_dir, _guidance_for("sre"))

    reopened = service.open_service(dir_override=str(project.squad_dir))

    assert [msg for msg in await reopened.sync() if "names no live role" in msg] == []


# -------------------------------------------------- what the new report made newly reachable


async def test_the_new_report_does_not_change_check_or_sync_exit_codes(invoke, project):
    """The question a new report always has to answer: whose build does it break?

    Nobody's. It is warn-level, and `sq check` exits 3 only on error-level issues while `sq sync`
    stays 0 for anything on its skip channel -- so an adopter mid-scaffold gets told about the
    dropped guide without their pipeline turning red for it. Driven at the CLI, since the exit code
    is the CLI's contract and no service-level assertion can observe it.
    """
    _fill_in_role_stub(scaffold_new_role(project.squad_dir, slug="sre"))
    _write_playbook_override(project.squad_dir, _guidance_for("sre"))

    check = await invoke(["check"])
    assert check.exit_code == 0, check.output
    assert "names no live role" in check.output

    sync = await invoke(["sync"])
    assert sync.exit_code == 0, sync.output
    assert "names no live role" in sync.output


async def test_retiring_a_bundled_role_leaves_both_cli_surfaces_silent(invoke, project):
    """The CLI smoke for the shape the exemption exists for, driven the way an adopter meets it:
    retire a bundled role on a squad with no playbook override, and neither surface says anything
    about a dropped guide. This is the one that was reported at the CLI, so it is pinned there."""
    activate = await invoke(["role", "activate", "qa"])
    assert activate.exit_code == 0, activate.output
    retire = await invoke(["role", "qa", "status", "Archived"])
    assert retire.exit_code == 0, retire.output

    check = await invoke(["check"])
    assert "names no live role" not in check.output, check.output

    sync = await invoke(["sync"])
    assert "names no live role" not in sync.output, sync.output
