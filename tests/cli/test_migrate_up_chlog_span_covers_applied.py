"""``sq migrate up``'s "manual steps remain" line must always name a span that
``sq migrate chlog`` itself resolves to every applied migration's manual text.

Table-driven over the shapes that could break the span: a single migration behind, a
multi-migration chain where only some entries carry manual text, and the edge where the very
first migration in the registry is the one applied (no preceding entry to anchor the lower
bound on).

Driven entirely through the CLI (``invoke``): read the span off ``migrate up``'s own
output, feed it straight back into ``migrate chlog``, and check every applied migration
with manual text is reported — the same round trip an operator following the tool's own
instruction performs.
"""

import re

import pytest

from squads import _aio
from squads._migrations._registry import MIGRATIONS, Migration

pytestmark = pytest.mark.anyio

_SPAN_RE = re.compile(r"`sq migrate chlog ([^`]+)`")


async def _downgrade_schema(project, schema: str) -> None:
    cfg_text = await _aio.read_text(project.config_path)
    cfg_text = cfg_text.replace(
        f'schema_version = "{project.config.schema_version}"', f'schema_version = "{schema}"'
    )
    await _aio.write_text(project.config_path, cfg_text)


def _applied_from(from_schema: str) -> list[Migration]:
    """The same filter ``run_pending_migrations`` applies, computed test-side to know what
    ``migrate up`` should have applied without re-deriving the fix under test."""
    from squads._models._schema import schema_tuple

    return [m for m in MIGRATIONS if schema_tuple(m.to_schema) > schema_tuple(from_schema)]


@pytest.mark.parametrize(
    "from_schema",
    [
        pytest.param("0.14", id="one-migration-behind"),
        # A multi-migration chain where only some applied entries carry manual text
        # (0.11.0 is a schema-stamp-only gate with no manual steps).
        pytest.param("0.10", id="multi-migration-chain-partial-manual"),
        # The first migration in the whole registry is the one applied — no preceding
        # registry entry to anchor the span's lower bound on.
        pytest.param("0.1", id="first-in-registry"),
    ],
)
async def test_migrate_up_span_reports_every_applied_manual_migration(project, invoke, from_schema):
    await _downgrade_schema(project, from_schema)

    up = await invoke(["migrate", "up"])
    assert up.exit_code == 0, up.output

    expected_manual = [m for m in _applied_from(from_schema) if m.manual]
    assert expected_manual, "test setup must exercise at least one manual migration"

    match = _SPAN_RE.search(up.output)
    assert match, f"no chlog span printed: {up.output}"
    span = match.group(1)

    chlog = await invoke(["migrate", "chlog", span])
    assert chlog.exit_code == 0, chlog.output
    assert "no manual steps" not in chlog.output, (
        f"span {span!r} reported by `migrate up` contains none: {chlog.output}"
    )
    for m in expected_manual:
        # Rich renders the `##` markdown heading as styled text rather than literal `##` —
        # match on the text content only.
        heading = f"v{m.version} — manual steps (schema v{m.from_schema}→v{m.to_schema})"
        assert heading in chlog.output, f"{heading!r} missing from chlog output for {span!r}"


@pytest.mark.parametrize(
    "lower_bound",
    [
        pytest.param("v0.14.0rc1", id="rc-of-the-release-that-ships-the-migration"),
        pytest.param("v0.14.0a1", id="alpha-of-that-release"),
        pytest.param("v0.13.1", id="previous-release"),
    ],
)
async def test_chlog_window_opened_at_a_prerelease_keeps_the_release_steps(invoke, lower_bound):
    chlog = await invoke(["migrate", "chlog", f"{lower_bound}..v0.15.0"])
    assert chlog.exit_code == 0, chlog.output
    assert "no manual steps" not in chlog.output
    assert "v0.14.0 — manual steps" in chlog.output
