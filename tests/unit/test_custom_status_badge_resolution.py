"""A custom status resolves its badge — or a graceful default when it declares none — through
the spec, never by parsing the status string back into a fixed enum (the historical bug: any
status outside the built-in domain used to raise ``ValueError``).
"""

from squads import _badges as badges
from squads._workflow import StatusSpec, WorkflowSpec, bundled_spec


def _spec_with(**extra_statuses: StatusSpec) -> WorkflowSpec:
    base = bundled_spec()
    return base.model_copy(update={"statuses": {**base.statuses, **extra_statuses}})


def test_a_custom_status_with_a_declared_badge_renders_it() -> None:
    spec = _spec_with(Triage=StatusSpec(terminal=False, badge="🟠"))
    assert badges.status_badge("Triage", spec) == "🟠 Triage"


def test_a_custom_status_with_no_declared_badge_renders_a_graceful_default() -> None:
    spec = _spec_with(Mitigating=StatusSpec(terminal=False))
    assert badges.status_badge("Mitigating", spec) == "⚪ Mitigating"


def test_status_badge_never_raises_for_a_status_outside_any_fixed_domain() -> None:
    spec = _spec_with(Triage=StatusSpec(terminal=False, badge="🟠"))
    badges.status_badge("Triage", spec)
    badges.status_badge("SomeOtherCustomStatus", spec)  # must not raise either


def test_status_badge_with_no_spec_threaded_falls_back_to_the_bundled_one() -> None:
    """Call sites that don't thread a spec (e.g. the frozen migration runner) keep working."""
    assert badges.status_badge("InProgress") == "🟡 In Progress"


def test_extending_the_spec_with_a_custom_status_does_not_perturb_builtin_badge_text() -> None:
    spec = _spec_with(Triage=StatusSpec(terminal=False, badge="🟠"))
    assert badges.status_badge("Done", spec) == "🟢 Done"
    assert badges.status_badge("WontFix", spec) == "⚫ Wont Fix"
