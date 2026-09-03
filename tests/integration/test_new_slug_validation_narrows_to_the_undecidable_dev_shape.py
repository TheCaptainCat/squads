"""``resolve_role_with_base``'s "new slug, all required fields must be present" check is skipped
whenever a caller supplies a base -- which the two roster-aware consumers (``sq role <slug>
show``, ``sq check``) do for any ``-dev``-shaped slug, so it could look like the check is off
for the whole ``-dev`` suffix space.

After the stored-fact-first fix (see tests/unit/test_dev_base_gating_reads_the_stored_fact_
first.py and tests/integration/test_show_and_check_do_not_crash_on_a_dev_suffixed_non_dev_
slug.py), that is no longer true for a slug with a roster entry: an activated non-dev role
gets no base at all, so an incomplete override for one is refused exactly like any other
unknown slug's would be -- the check is not skipped, it never applied a dev base to skip it
from in the first place.

What remains, and is not itself a further bug to fix, is the one case a project decision
and docs/overrides.md deliberately sanction: a ``<tech>-dev.toml`` with **no roster entry at all**
previews leniently against the generated developer template, so you can write the override
before running ``sq dev add --tech <tech>``. There is no roster item to consult in that case,
so the naming convention is the only signal there ever was -- narrowing the original "skipped
for the whole suffix space" finding down to this one documented, intentional shape. This file
pins both halves: the case that is now protected, and the narrow, sanctioned case that is not
trying to be.
"""

import pytest

from squads import __version__

pytestmark = pytest.mark.anyio


def _place_role_toml(project, slug: str, content: str, *, stamped: bool = False) -> None:
    target = project.squad_dir / ".overrides" / "roles" / f"{slug}.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    stamp = f"# squads:override-base:{__version__}\n" if stamped else ""
    target.write_text(f"{stamp}{content}", encoding="utf-8")


async def test_an_activated_non_dev_dev_suffixed_role_still_enforces_required_fields(
    project, svc, invoke
) -> None:
    """The half of the finding that the stored-fact-first fix actually closes: once the slug
    has a roster entry, an incomplete override for it is refused at the roster-aware consumers
    too -- not silently accepted through a dev base it was never entitled to (it has no
    ``extra.tech``, so it never gets one; see the crash-fix tests referenced above)."""
    _place_role_toml(
        project,
        "data-dev",
        'full_name = "Dana Analyst"\ntitle = "data steward"\n'
        'description = "Curates the datasets."\nmission = "Keep the catalog accurate."\n',
    )
    await svc.activate_role("data-dev")  # complete at activation time -- succeeds

    # An adopter edit later drops a required field. No dev base ever applies here, so this
    # must refuse exactly like any other role's now-incomplete override would.
    _place_role_toml(project, "data-dev", 'full_name = "Dana Analyst"\n')

    checked = await invoke(["check"])
    shown = await invoke(["role", "data-dev", "show"])

    assert checked.exit_code == 3, checked.output
    assert "missing required fields" in checked.output
    assert shown.exit_code == 1, shown.output
    assert "missing required fields" in shown.output
    assert "Traceback" not in checked.output and "Traceback" not in shown.output


async def test_a_dev_shaped_slug_with_no_roster_entry_still_previews_leniently_by_design(
    project, invoke
) -> None:
    """The narrow, sanctioned residual: no roster entry exists for ``rust-dev`` at all, so
    there is no stored fact to gate on, and the naming convention's lenient preview (documented
    in docs/overrides.md) is exactly what both `sq check` and `sq role <slug> show`
    are supposed to do here -- accept a partial file rather than demand every ``RoleDef``
    field a wholly-unrelated new role would need. Stamped: this fixture is not about the
    provenance obligation (a `<tech>-dev` override shadows the generated dev base, so an
    unstamped one is now an error under the uniform severity contract), only about field
    leniency."""
    _place_role_toml(project, "rust-dev", 'title = "Senior Rust developer"\n', stamped=True)

    checked = await invoke(["check"])
    shown = await invoke(["role", "rust-dev", "show"])

    assert checked.exit_code == 0, checked.output
    assert shown.exit_code == 0, shown.output
    assert "Senior Rust developer" in shown.output
