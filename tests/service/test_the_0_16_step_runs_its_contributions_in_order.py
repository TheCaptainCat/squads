"""The 0.16 step is a list of contributions: every one is planned before any is written, a
failure in any of them refuses the whole run with nothing written, and the writers then run in
order. Driven with stand-in contributions so the order is observable."""

import pytest

from _helpers import bundled_migration_context
from squads._errors import SquadsError
from squads._migrations import _registry
from squads._migrations import _v0_15_to_v0_16 as step
from squads._migrations._v0_15_to_v0_16 import Contribution, Planned, run_contributions
from squads._models._schema import SCHEMA_VERSION

pytestmark = pytest.mark.anyio


def _stand_in(name: str, calls: list[str], *, failures=(), writes: bool = True, report=()):
    async def plan(_ctx, _db):
        calls.append(f"plan {name}")

        async def write(_ctx):
            calls.append(f"write {name}")
            return 2

        return Planned(
            failures=tuple(failures),
            report=tuple(report),
            notes=(f"note {name}",) if failures else (),
            write=write if writes else None,
        )

    return Contribution(name, plan, manual=f"manual {name}", summary=f"summary {name}.")


async def _run(svc, contributions):
    ctx = bundled_migration_context(svc.paths)
    return await run_contributions(contributions, ctx, await svc.store.load())


async def test_every_plan_is_awaited_before_any_writer_and_writers_run_in_order(svc):
    calls: list[str] = []
    contributions = [
        _stand_in("a", calls, report=("ra",)),
        _stand_in("b", calls, writes=False, report=("rb",)),
        _stand_in("c", calls, report=("rc",)),
    ]

    outcome = await _run(svc, contributions)

    assert calls == ["plan a", "plan b", "plan c", "write a", "write c"]
    assert outcome.count == 4
    assert outcome.report == ("ra", "rb", "rc")


@pytest.mark.parametrize(
    "failing",
    [(0,), (1,), (2,), (0, 2), (0, 1, 2)],
    ids=["first", "middle", "last", "first-and-last", "all"],
)
async def test_a_failure_in_any_contribution_refuses_the_run_with_every_failure_and_no_write(
    svc, failing
):
    calls: list[str] = []
    contributions = [
        _stand_in(n, calls, failures=(f"problem {n}.1", f"problem {n}.2") if i in failing else ())
        for i, n in enumerate("abc")
    ]

    with pytest.raises(SquadsError) as raised:
        await _run(svc, contributions)

    message = str(raised.value)
    assert [c for c in calls if c.startswith("write")] == []
    assert calls == ["plan a", "plan b", "plan c"]
    for i, n in enumerate("abc"):
        assert (f"problem {n}.1" in message) == (i in failing)
    assert f"{2 * len(failing)} problem(s) found." in message
    assert message.rstrip().endswith("This step wrote nothing and the schema stamp is unchanged.")
    positions = [message.index(f"problem {'abc'[i]}.1") for i in failing]
    assert positions == sorted(positions)


def test_the_manual_and_the_summary_are_assembled_from_the_contributions_in_order():
    stand_ins = [_stand_in(n, []) for n in "xyz"]

    manual = step.assemble_manual(stand_ins)
    summary = step.assemble_summary(stand_ins)

    assert manual.startswith("This step checks every part before it writes any file")
    assert [manual.count(f"manual {n}") for n in "xyz"] == [1, 1, 1]
    assert manual.index("manual x") < manual.index("manual y") < manual.index("manual z")
    assert summary == "summary x. summary y. summary z."


def test_the_registry_has_one_0_16_entry_that_is_last_and_reads_the_module():
    entries = [m for m in _registry.MIGRATIONS if m.to_schema == "0.16"]

    assert len(entries) == 1
    (entry,) = entries
    assert _registry.MIGRATIONS[-1] is entry
    assert entry.to_schema == SCHEMA_VERSION
    assert (entry.version, entry.from_schema) == ("0.16.0", "0.15")
    assert entry.summary == step.SUMMARY and entry.manual == step.MANUAL
    assert entry.manual.strip() and entry.summary.strip()
