"""Custom-status badge resolution.

`_discussion._status_badge` used to resolve a badge by parsing the status string back into the
built-in `Status` StrEnum, which raised `ValueError` for any status outside that enum — i.e.
every custom status a project might declare in `.overrides/workflow.toml`. This module pins the
fix: badges now resolve through the spec (`WorkflowSpec.status_badge`), with a graceful ``⚪``
default when a status declares none, and never raise.

This is deliberately a *separate* module from `tests/test_status_display_characterization.py`:
that file is the pure HEAD-baseline gate and must stay green against HEAD with no
forward-looking, post-rewire assertions. These tests describe the *new* custom-status behavior
the rewire adds, not the built-in baseline.
"""

from _helpers import EXPECTED_BUILTIN_STATUS_BADGES
from squads import _discussion as discussion
from squads._workflow import StatusSpec, WorkflowSpec, bundled_spec

# The exact badge *text* (emoji + spaced label) for the 9 built-in sub-entity statuses, derived
# from the shared bare-emoji map in tests/_helpers.py plus the "InProgress" -> "In Progress"
# label-spacing rule _status_badge applies.
_EXPECTED_BUILTIN_BADGE_TEXT: dict[str, str] = {
    "Todo": f"{EXPECTED_BUILTIN_STATUS_BADGES['Todo']} Todo",
    "InProgress": f"{EXPECTED_BUILTIN_STATUS_BADGES['InProgress']} In Progress",
    "Blocked": f"{EXPECTED_BUILTIN_STATUS_BADGES['Blocked']} Blocked",
    "Done": f"{EXPECTED_BUILTIN_STATUS_BADGES['Done']} Done",
    "Cancelled": f"{EXPECTED_BUILTIN_STATUS_BADGES['Cancelled']} Cancelled",
    "Open": f"{EXPECTED_BUILTIN_STATUS_BADGES['Open']} Open",
    "Fixed": f"{EXPECTED_BUILTIN_STATUS_BADGES['Fixed']} Fixed",
    "Verified": f"{EXPECTED_BUILTIN_STATUS_BADGES['Verified']} Verified",
    "WontFix": f"{EXPECTED_BUILTIN_STATUS_BADGES['WontFix']} Wont Fix",
}


class TestCustomStatusBadgeResolvesThroughSpec:
    """A custom status resolves its declared badge — or a graceful ``⚪`` default when none is
    declared — through the spec, instead of `_discussion._status_badge` raising on
    `Status(custom)`.

    Built the spec by extending the bundled one with extra statuses rather than hand-rolling a
    minimal `WorkflowSpec`, since `WorkflowSpec`'s validator requires the full reserved
    vocabulary to be present — extension is the natural way to add just a custom status for a
    unit test.
    """

    @staticmethod
    def _spec_with(**extra_statuses: StatusSpec) -> WorkflowSpec:
        base = bundled_spec()
        return base.model_copy(update={"statuses": {**base.statuses, **extra_statuses}})

    def test_custom_status_with_declared_badge_renders_it(self) -> None:
        spec = self._spec_with(Triage=StatusSpec(terminal=False, badge="🟠"))
        assert discussion._status_badge("Triage", spec) == "🟠 Triage"  # pyright: ignore[reportPrivateUsage]

    def test_custom_status_with_no_badge_renders_graceful_default(self) -> None:
        spec = self._spec_with(Mitigating=StatusSpec(terminal=False))
        assert discussion._status_badge("Mitigating", spec) == "⚪ Mitigating"  # pyright: ignore[reportPrivateUsage]

    def test_custom_status_never_raises(self) -> None:
        spec = self._spec_with(Triage=StatusSpec(terminal=False, badge="🟠"))
        # The historical bug: _discussion._status_badge parsed the status string back into the
        # built-in Status StrEnum, which raised ValueError for any status outside the enum.
        discussion._status_badge("Triage", spec)  # pyright: ignore[reportPrivateUsage]  # must not raise
        discussion._status_badge("SomeOtherCustomStatus", spec)  # pyright: ignore[reportPrivateUsage]

    def test_status_badge_without_a_spec_falls_back_to_bundled(self) -> None:
        """Call sites that don't thread a spec (e.g. the frozen migration runner) keep working."""
        assert discussion._status_badge("InProgress") == "🟡 In Progress"  # pyright: ignore[reportPrivateUsage]

    def test_built_in_badges_unaffected_by_spec_extension(self) -> None:
        """Extending the spec with a custom status must not perturb built-in badge text."""
        spec = self._spec_with(Triage=StatusSpec(terminal=False, badge="🟠"))
        for status_value, expected in _EXPECTED_BUILTIN_BADGE_TEXT.items():
            assert discussion._status_badge(status_value, spec) == expected  # pyright: ignore[reportPrivateUsage]
